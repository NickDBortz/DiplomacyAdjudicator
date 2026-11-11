const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.join(__dirname, '..');
const shared = fs.readFileSync(path.join(root, 'docs', 'shared.js'), 'utf8');
const pickerSource = shared.slice(shared.indexOf('let availableOrders = [];'), shared.indexOf('function downloadGameSave('));
const radialSource = fs.readFileSync(path.join(root, 'docs', 'radial-menu.js'), 'utf8');

function createGame(orderTexts) {
    class Element {
        constructor() {
            this.children = [];
            this.attributes = {};
            this.dataset = {};
            this.classes = new Set();
            this.classList = {
                add: name => this.classes.add(name),
                remove: name => this.classes.delete(name),
                contains: name => this.classes.has(name),
            };
            this.style = { setProperty(name, value) { this[name] = value; } };
        }
        setAttribute(name, value) { this.attributes[name] = value; }
        appendChild(child) { this.children.push(child); }
        insertBefore(child) { this.children.unshift(child); }
        addEventListener(type, handler) { this[type] = handler; }
        replaceChildren(...children) { this.children = children; }
        set innerHTML(value) { this.children = []; }
    }
    class Option {
        constructor(text, value) { this.text = text; this.value = value; }
    }
    function select() {
        const el = new Element();
        el.value = '';
        el.options = [];
        el.replaceChildren = option => { el.options = [option]; };
        el.add = option => el.options.push(option);
        return el;
    }
    const units = [
        { type: 'A', territory: 'PAR', owner: 'France' },
        { type: 'F', territory: 'BRE', owner: 'France' },
        { type: 'A', territory: 'BUR', owner: 'Germany' },
    ];
    const markers = units.map(unit => {
        const marker = new Element();
        marker.dataset = unit;
        marker.getBoundingClientRect = () => ({ left: 140, top: 245, width: 20, height: 10 });
        return marker;
    });
    const territories = ['PAR', 'BRE', 'BUR', 'PIC', 'LON', 'GAS'].map(abbr => {
        const element = new Element();
        element.id = `terr-${abbr}`;
        return element;
    });
    const elements = Object.fromEntries(territories.map(element => [element.id, element]));
    Object.assign(elements, {
        'order-unit': select(),
        'order-type': select(),
        'order-choice': select(),
        'order-picker-status': new Element(),
        'map-order-status': new Element(),
        'clear-order-selection': new Element(),
    });
    const preview = new Element();
    const svg = new Element();
    svg.createSVGPoint = () => ({
        matrixTransform(matrix) {
            return { x: (this.x - matrix.x) / matrix.scale, y: (this.y - matrix.y) / matrix.scale };
        },
    });
    svg.getScreenCTM = () => ({ inverse: () => ({ x: 100, y: 200, scale: 0.5 }) });
    svg.querySelector = selector => selector === '#dislodged-preview' ? preview : null;
    svg.querySelectorAll = selector => selector === '#units .unit' ? markers
        : selector === '.order-highlight-source, .order-highlight-target'
            ? [...markers, ...territories].filter(el => el.classes.has('order-highlight-source') || el.classes.has('order-highlight-target'))
            : [];
    const state = { phase: 'Spring', player_power: 'France', units, players: [] };
    const mapData = { territories: [
        { abbr: 'PAR', name: 'Paris', adjacents: ['Brest', 'Burgundy', 'Picardy'] },
        { abbr: 'BRE', name: 'Brest', adjacents: ['Paris'] },
        { abbr: 'BUR', name: 'Burgundy', adjacents: ['Paris'] },
        { abbr: 'PIC', name: 'Picardy', adjacents: ['Paris'] },
        { abbr: 'LON', name: 'London', adjacents: [] },
        { abbr: 'GAS', name: 'Gascony', adjacents: [] },
    ] };
    let submissions = 0;
    const context = vm.createContext({
        SVG_NS: 'svg', Option, mapData, svg, unitPosition: () => [0, 0],
        document: { createElementNS: () => new Element(), getElementById: id => elements[id] || null },
        window: { diplomacy: { state, order: () => { submissions++; } } },
        submitMultiplayerOrder: () => { submissions++; },
        setOrderMessage: () => {},
    });
    vm.runInContext(pickerSource, context);
    vm.runInContext(radialSource, context);
    context.initOrderPicker();
    context.initRadialMenu(svg);
    context.setOrderPicker(orderTexts);
    const menu = svg.children.find(child => child.attributes.id === 'radial-menu');
    function clickMap(abbr, useMarker = false) {
        const marker = markers.find(item => item.dataset.territory === abbr);
        const territory = elements[`terr-${abbr}`];
        const target = { closest: selector => selector === '.unit' && useMarker ? marker
            : selector === '.territory' && !useMarker ? territory : null };
        context.handleMapClickWithRadialMenu({ target }, vm.runInContext('availableOrders', context), state, 'France', state.phase);
    }
    function choose(type) {
        const item = menu.children.find(child => child.attributes['data-type'] === type);
        assert.ok(item && item.click, `${type} must be available`);
        item.click({ stopPropagation() {} });
    }
    const values = () => [elements['order-unit'].value, elements['order-type'].value, elements['order-choice'].value];
    return { context, svg, menu, elements, markers, state, clickMap, choose, values, submissions: () => submissions };
}

test('unit and territory clicks open the menu; hold fills the picker without submitting', () => {
    for (const useMarker of [true, false]) {
        const game = createGame(['A PAR H', 'A PAR - BUR']);
        game.clickMap('PAR', useMarker);
        assert.equal(game.menu.children.length, 6);
        const center = game.menu.children[5];
        assert.equal(center.attributes.cx, 100);
        assert.equal(center.attributes.cy, 100);
        game.choose('Hold');
        assert.equal(game.menu.children.length, 0);
        assert.deepEqual(game.values(), ['A PAR', 'Hold', 'A PAR H']);
        assert.equal(game.submissions(), 0);
    }
});

test('advance hides the menu, highlights only legal destinations, and selects a clicked unit destination', () => {
    const game = createGame(['A PAR H', 'A PAR - BUR', 'A PAR - PIC', 'A PAR - LON']);
    game.clickMap('PAR', true);
    game.choose('Advance');
    assert.equal(game.menu.children.length, 0);
    assert.deepEqual(game.values(), ['A PAR', 'Move', '']);
    assert.ok(game.elements['terr-BUR'].classes.has('advance-target'));
    assert.ok(game.elements['terr-LON'].classes.has('convoy-target'));
    assert.ok(!game.elements['terr-BRE'].classes.has('advance-target'));
    game.clickMap('BRE');
    assert.equal(game.elements['order-choice'].value, '');
    game.clickMap('BUR', true);
    assert.deepEqual(game.values(), ['A PAR', 'Move', 'A PAR - BUR']);
    assert.ok(!game.elements['terr-BUR'].classes.has('advance-target'));
    assert.equal(game.submissions(), 0);
});

test('support highlights valid units including opponents and selects hold or a destination', () => {
    const game = createGame(['A PAR H', 'A PAR S A BUR H', 'A PAR S A BUR - PIC', 'A PAR S F BRE - GAS']);
    game.clickMap('PAR');
    game.choose('Support');
    assert.equal(game.menu.children.length, 0);
    assert.deepEqual(game.values(), ['A PAR', 'Support', '']);
    assert.ok(game.markers[2].classes.has('support-target'));
    assert.ok(game.elements['terr-BUR'].classes.has('support-target'));
    game.clickMap('BUR');
    assert.deepEqual(game.values(), ['A PAR', 'Support', 'A PAR S A BUR H']);
    assert.ok(game.elements['terr-PIC'].classes.has('support-target'));
    assert.ok(!game.elements['terr-GAS'].classes.has('support-target'));
    game.clickMap('PIC');
    assert.deepEqual(game.values(), ['A PAR', 'Support', 'A PAR S A BUR - PIC']);
    assert.ok(!game.elements['terr-PIC'].classes.has('support-target'));
    assert.equal(game.submissions(), 0);
});

test('convoy highlights an army and its valid destinations without submitting', () => {
    const game = createGame(['F BRE H', 'F BRE C A BUR - PIC', 'F BRE C A BUR - GAS']);
    game.clickMap('BRE');
    game.choose('Convoy');
    assert.equal(game.menu.children.length, 0);
    assert.ok(game.markers[2].classes.has('convoy-target'));
    game.clickMap('BUR', true);
    assert.ok(game.elements['terr-PIC'].classes.has('convoy-target'));
    assert.ok(game.elements['terr-GAS'].classes.has('convoy-target'));
    game.clickMap('GAS');
    assert.deepEqual(game.values(), ['F BRE', 'Convoy', 'F BRE C A BUR - GAS']);
    assert.equal(game.submissions(), 0);
});

test('convoy alternatives remain available in the picker', () => {
    const game = createGame(['A PAR H', 'A PAR - PIC', 'A PAR - PIC via convoy']);
    game.clickMap('PAR');
    game.choose('Advance');
    assert.ok(game.elements['terr-PIC'].classes.has('checkerboard-convoy'));
    game.clickMap('PIC');
    assert.deepEqual(game.values(), ['A PAR', 'Move', '']);
    assert.deepEqual(game.elements['order-choice'].options.map(option => option.value),
        ['', 'A PAR - PIC', 'A PAR - PIC via convoy']);
    assert.equal(game.submissions(), 0);
});

test('ambiguous destination coasts remain available in the picker', () => {
    const game = createGame(['F BRE H', 'F BRE - GAS(nc)', 'F BRE - GAS(sc)']);
    game.clickMap('BRE');
    game.choose('Advance');
    game.clickMap('GAS');
    assert.deepEqual(game.values(), ['F BRE', 'Move', '']);
    assert.deepEqual(game.elements['order-choice'].options.map(option => option.value),
        ['', 'F BRE - GAS(nc)', 'F BRE - GAS(sc)']);
    assert.equal(game.submissions(), 0);
});

test('transform selects a unique order and leaves ambiguous coasts for the picker', () => {
    const single = createGame(['F BRE H', 'F BRE T']);
    single.clickMap('BRE');
    single.choose('Transform');
    assert.deepEqual(single.values(), ['F BRE', 'Transform', 'F BRE T']);
    assert.equal(single.submissions(), 0);

    const multiple = createGame(['F BRE H', 'F BRE T(nc)', 'F BRE T(sc)']);
    multiple.clickMap('BRE');
    multiple.choose('Transform');
    assert.deepEqual(multiple.values(), ['F BRE', 'Transform', '']);
    assert.deepEqual(multiple.elements['order-choice'].options.map(option => option.value),
        ['', 'F BRE T(nc)', 'F BRE T(sc)']);
    assert.equal(multiple.submissions(), 0);
});

test('retreats select the dislodged unit by territory and highlight only valid destinations', () => {
    const game = createGame(['A PAR - PIC', 'A PAR - GAS']);
    game.state.phase = 'Spring Retreat';
    game.state.units = [
        { type: 'A', territory: null, dislodged: true, dislodged_from: 'PAR', owner: 'France' },
        { type: 'A', territory: 'PAR', dislodged: false, owner: 'Germany' },
    ];
    game.clickMap('PAR');
    assert.equal(game.menu.children.length, 0);
    assert.deepEqual(game.values(), ['A PAR', 'Move', '']);
    assert.ok(game.elements['terr-PIC'].classes.has('retreat-target'));
    assert.ok(!game.elements['terr-BRE'].classes.has('retreat-target'));
    game.clickMap('PIC');
    assert.deepEqual(game.values(), ['A PAR', 'Move', 'A PAR - PIC']);
    assert.ok(!game.elements['terr-PIC'].classes.has('retreat-target'));
    assert.equal(game.submissions(), 0);
});

test('clear selection cancels highlights and allows another unit to be selected', () => {
    const game = createGame(['A PAR H', 'A PAR - BUR', 'F BRE H']);
    game.clickMap('PAR');
    game.choose('Advance');
    game.elements['clear-order-selection'].click();
    assert.ok(!game.elements['terr-BUR'].classes.has('advance-target'));
    game.clickMap('BRE');
    game.choose('Hold');
    assert.deepEqual(game.values(), ['F BRE', 'Hold', 'F BRE H']);
});

test('refreshing available orders cancels an incomplete map selection', () => {
    const game = createGame(['A PAR H', 'A PAR - BUR', 'F BRE H']);
    game.clickMap('PAR');
    game.choose('Advance');
    game.context.setOrderPicker(['F BRE H']);
    assert.ok(!game.elements['terr-BUR'].classes.has('advance-target'));
    game.clickMap('BRE');
    game.choose('Hold');
    assert.deepEqual(game.values(), ['F BRE', 'Hold', 'F BRE H']);
});

test('both multiplayer pages load the radial menu before their game scripts', () => {
    for (const role of ['host', 'client']) {
        const html = fs.readFileSync(path.join(root, 'docs', `multiplayer-${role}.html`), 'utf8');
        const radial = html.indexOf('<script src="radial-menu.js"></script>');
        assert.ok(radial > html.indexOf('<script src="shared.js"></script>'));
        assert.ok(radial < html.indexOf(`<script src="multiplayer-${role}.js"></script>`));
    }
});
