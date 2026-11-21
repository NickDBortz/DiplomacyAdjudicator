const test = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const builder = require('../tools/map_builder_model.js');

function fixture() {
    const map = builder.newMap(100, 100);
    map.players.push({ name: 'Red', color: builder.palette[0] });
    const land = builder.newTerritory('Coast', 'COA');
    const north = builder.newTerritory('North Sea', 'NTH');
    const south = builder.newTerritory('South Sea', 'STH');
    Object.assign(land, {
        owner: 'Red', supply_center: true, label_pos: [20, 20], army_pos: [20, 25],
        coast_pos: [15, 20], south_coast_pos: [25, 20], supply_center_pos: [20, 15]
    });
    for (const [t, pos] of [[north, [60, 20]], [south, [60, 60]]]) {
        Object.assign(t, { land: false, label_pos: pos, fleet_pos: pos });
    }
    map.territories.push(land, north, south);
    for (const [t, x] of [[land, 10], [north, 40], [south, 70]]) {
        builder.addPolygon(map, t, [[x, 10], [x + 10, 10], [x + 10, 20], [x, 20]]);
    }
    builder.setAdjacency(map, land, north, true);
    builder.setAdjacency(map, land, south, true);
    land.north_coast.push(north.name);
    land.south_coast.push(south.name);
    return { map, land, north, south };
}

test('complete two-coast map validates and contains the game format', () => {
    const { map, land, north } = fixture();
    land.south_coast.push(north.name);
    assert.deepEqual(builder.validate(map), []);
    assert.deepEqual(land.north_coast, ['North Sea']);
    assert.deepEqual(north.adjacents, ['Coast']);
    assert.equal(map.vertices.length, 12);
});

test('the existing classic map remains valid', () => {
    const classic = require('../server/data/maps/classic_map.json');
    assert.deepEqual(builder.validate(classic), []);
});

test('renaming and removing adjacency updates references on both sides', () => {
    const { map, land, north } = fixture();
    builder.renameTerritory(map, north, 'Northern Sea');
    assert.deepEqual(land.north_coast, ['Northern Sea']);
    assert.ok(land.adjacents.includes('Northern Sea'));
    builder.setAdjacency(map, land, north, false);
    assert.ok(!north.adjacents.includes('Coast'));
    assert.ok(!land.north_coast.includes('Northern Sea'));
    assert.ok(builder.validate(map).some(error => error.includes('both coast')));
});

test('validation catches missing positions, bad references and impossible win counts', () => {
    const { map, land } = fixture();
    delete land.south_coast_pos;
    land.owner = 'Unknown';
    land.adjacents.push('Missing');
    map.win_count = 2;
    const errors = builder.validate(map).join('\n');
    assert.match(errors, /south_coast_pos/);
    assert.match(errors, /unknown owner/);
    assert.match(errors, /invalid adjacents/);
    assert.match(errors, /exceeds/);
});

test('region tracing follows a bounded light region and rejects borders', () => {
    const width = 8, height = 8, data = new Uint8ClampedArray(width * height * 4);
    for (let y = 1; y < 7; y++) for (let x = 1; x < 7; x++) {
        const i = (y * width + x) * 4;
        data[i] = data[i + 1] = data[i + 2] = data[i + 3] = 255;
    }
    const polygon = builder.traceRegion({ width, height, data }, 3, 3, 200);
    assert.deepEqual(polygon, [[1, 1], [7, 1], [7, 7], [1, 7]]);
    assert.throws(() => builder.traceRegion({ width, height, data }, 0, 0, 200), /dark border/);
});

test('manual polygons reuse shared vertices and reject incomplete shapes', () => {
    const map = builder.newMap(10, 10), a = builder.newTerritory('A', 'A'), b = builder.newTerritory('B', 'B');
    builder.addPolygon(map, a, [[0, 0], [5, 0], [5, 5]]);
    builder.addPolygon(map, b, [[5, 0], [10, 0], [5, 5]]);
    assert.equal(map.vertices.length, 4);
    assert.throws(() => builder.addPolygon(map, a, [[0, 0], [1, 1]]), /three points/);
});

test('generated map loads into the game with owners and separate coasts', () => {
    const { map } = fixture();
    const code = `
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from game.game import Game
with tempfile.TemporaryDirectory() as directory:
    filename = Path(directory) / 'map.json'
    filename.write_text(sys.stdin.read(), encoding='utf-8')
    game = Game(json_file=str(filename), render=False)
    territories = {t.name: t for t in game.game_state.territory_list}
    coast = territories['Coast']
    assert coast.owner.name == 'Red'
    assert coast.is_supply_center
    assert [t.name for t in coast.north_coast] == ['North Sea']
    assert [t.name for t in coast.south_coast] == ['South Sea']
    assert coast in territories['North Sea'].adjacents
`;
    const result = spawnSync(process.env.PYTHON || 'python', ['-c', code, path.resolve(__dirname, '../server')], {
        input: JSON.stringify(map), encoding: 'utf8'
    });
    assert.equal(result.status, 0, result.stderr || String(result.error));
});
