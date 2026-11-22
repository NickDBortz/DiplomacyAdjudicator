(function (root) {
    'use strict';

    const palette = ['#A87E9F', '#EFC4E4', '#79AFC6', '#A4C499', '#A08A75', '#C48F85', '#EAEAAF', '#D6A96A'];
    const colorPattern = /^#[0-9a-f]{6}$/i;

    function newMap(width, height) {
        return { players: [], win_count: 1, water_color: '#C5DFEA', width, height, vertices: [], territories: [] };
    }

    function newTerritory(name, abbr) {
        return {
            name, abbr, owner: '', land: true, supply_center: false,
            adjacents: [], north_coast: [], south_coast: [], polygons: []
        };
    }

    function renameTerritory(map, territory, name) {
        const old = territory.name;
        territory.name = name;
        for (const other of map.territories) {
            for (const field of ['adjacents', 'north_coast', 'south_coast']) {
                other[field] = other[field].map(value => value === old ? name : value);
            }
        }
    }

    function setAdjacency(map, territory, other, enabled) {
        for (const [a, b] of [[territory, other], [other, territory]]) {
            a.adjacents = a.adjacents.filter(name => name !== b.name);
            if (enabled) a.adjacents.push(b.name);
            else {
                a.north_coast = a.north_coast.filter(name => name !== b.name);
                a.south_coast = a.south_coast.filter(name => name !== b.name);
            }
        }
    }

    function addPolygon(map, territory, points) {
        if (points.length < 3) throw new Error('A polygon needs at least three points.');
        const indices = points.map(point => {
            let index = map.vertices.findIndex(vertex => vertex[0] === point[0] && vertex[1] === point[1]);
            if (index < 0) {
                index = map.vertices.length;
                map.vertices.push(point);
            }
            return index;
        });
        territory.polygons.push(indices);
    }

    function mainPolygonCenter(map, territory) {
        let main = null, largestArea = 0, center = null;
        for (const polygon of territory.polygons) {
            if (polygon.length < 3) continue;
            const vertices = polygon.map(index => map.vertices[index]);
            if (vertices.some(point => !Array.isArray(point) || point.length !== 2 || !point.every(Number.isFinite))) continue;
            let area = 0, x = 0, y = 0;
            for (let i = 0; i < vertices.length; i++) {
                const a = vertices[i], b = vertices[(i + 1) % vertices.length];
                const cross = a[0] * b[1] - b[0] * a[1];
                area += cross;
                x += (a[0] + b[0]) * cross;
                y += (a[1] + b[1]) * cross;
            }
            if (Math.abs(area) > largestArea) {
                largestArea = Math.abs(area);
                main = vertices;
                center = [x / (3 * area), y / (3 * area)];
            }
        }
        if (!main) return null;

        // A concave polygon's centroid may lie outside; choose an interior point on its horizontal scanline.
        const intersections = [];
        for (let i = 0; i < main.length; i++) {
            const a = main[i], b = main[(i + 1) % main.length];
            if ((a[1] > center[1]) !== (b[1] > center[1])) {
                intersections.push(a[0] + (center[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1]));
            }
        }
        intersections.sort((a, b) => a - b);
        let widest = null;
        for (let i = 0; i + 1 < intersections.length; i += 2) {
            const left = intersections[i], right = intersections[i + 1];
            if (center[0] >= left && center[0] <= right) return center.map(Math.round);
            if (!widest || right - left > widest[1] - widest[0]) widest = [left, right];
        }
        return widest ? [Math.round((widest[0] + widest[1]) / 2), Math.round(center[1])] : null;
    }

    // Extract the outside boundary of a connected region of light pixels.
    function traceRegion(image, x, y, threshold) {
        const { width, height, data } = image;
        x = Math.floor(x); y = Math.floor(y);
        if (x < 0 || y < 0 || x >= width || y >= height) throw new Error('Click inside the image.');
        const light = index => {
            const i = index * 4;
            return data[i + 3] > 0 && (data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114) >= threshold;
        };
        const start = y * width + x;
        if (!light(start)) throw new Error('Click a light region, not a dark border. Adjust the threshold if needed.');
        const selected = new Uint8Array(width * height);
        const queue = new Int32Array(width * height);
        let head = 0, tail = 0;
        selected[start] = 1; queue[tail++] = start;
        while (head < tail) {
            const index = queue[head++], px = index % width, py = Math.floor(index / width);
            for (const next of [px > 0 ? index - 1 : -1, px + 1 < width ? index + 1 : -1,
                py > 0 ? index - width : -1, py + 1 < height ? index + width : -1]) {
                if (next >= 0 && !selected[next] && light(next)) {
                    selected[next] = 1; queue[tail++] = next;
                }
            }
        }
        const edges = new Map();
        function edge(ax, ay, bx, by) {
            const key = `${ax},${ay}`;
            if (!edges.has(key)) edges.set(key, []);
            edges.get(key).push([bx, by]);
        }
        for (let i = 0; i < tail; i++) {
            const index = queue[i], px = index % width, py = Math.floor(index / width);
            if (py === 0 || !selected[index - width]) edge(px, py, px + 1, py);
            if (px === width - 1 || !selected[index + 1]) edge(px + 1, py, px + 1, py + 1);
            if (py === height - 1 || !selected[index + width]) edge(px + 1, py + 1, px, py + 1);
            if (px === 0 || !selected[index - 1]) edge(px, py + 1, px, py);
        }
        const loops = [];
        while (edges.size) {
            const first = edges.keys().next().value;
            let point = first.split(',').map(Number);
            const loop = [];
            do {
                loop.push(point);
                const key = point.join(',');
                const options = edges.get(key);
                if (!options || !options.length) throw new Error('Could not trace this region; try manual tracing.');
                point = options.pop();
                if (!options.length) edges.delete(key);
            } while (point.join(',') !== first);
            if (loop.length >= 3) loops.push(loop);
        }
        const area = loop => Math.abs(loop.reduce((sum, p, i) => {
            const next = loop[(i + 1) % loop.length];
            return sum + p[0] * next[1] - next[0] * p[1];
        }, 0));
        loops.sort((a, b) => area(b) - area(a));
        if (!loops.length) throw new Error('No polygon found; try manual tracing.');
        const loop = loops[0];
        return loop.filter((p, i) => {
            const prev = loop[(i + loop.length - 1) % loop.length], next = loop[(i + 1) % loop.length];
            return (p[0] - prev[0]) * (next[1] - p[1]) !== (p[1] - prev[1]) * (next[0] - p[0]);
        });
    }

    function validate(map) {
        const errors = [];
        if (!Number.isInteger(map.width) || map.width < 1 || !Number.isInteger(map.height) || map.height < 1) errors.push('Image dimensions must be positive integers.');
        if (!colorPattern.test(map.water_color)) errors.push('Water color must be a six-digit hex color.');
        if (!Number.isInteger(map.win_count) || map.win_count < 1) errors.push('Win count must be a positive integer.');
        if (!map.players.length) errors.push('Add at least one power.');
        if (!map.territories.length) errors.push('Add at least one province.');
        const names = new Set(), abbrs = new Set(), powers = new Set();
        for (const player of map.players) {
            if (!player.name || powers.has(player.name)) errors.push(`Power names must be nonempty and unique: ${player.name}`);
            powers.add(player.name);
            if (!colorPattern.test(player.color)) errors.push(`Invalid color for power ${player.name}.`);
        }
        for (const t of map.territories) {
            if (!t.name || names.has(t.name)) errors.push(`Province names must be nonempty and unique: ${t.name}`);
            if (!t.abbr || abbrs.has(t.abbr)) errors.push(`Province abbreviations must be nonempty and unique: ${t.abbr}`);
            names.add(t.name); abbrs.add(t.abbr);
        }
        const pointValid = point => Array.isArray(point) && point.length === 2 &&
            point.every(Number.isFinite) && point[0] >= 0 && point[0] <= map.width && point[1] >= 0 && point[1] <= map.height;
        for (const t of map.territories) {
            if (t.owner && !powers.has(t.owner)) errors.push(`${t.name}: unknown owner ${t.owner}.`);
            if (!t.land && t.supply_center) errors.push(`${t.name}: water cannot be a supply center.`);
            if (!t.polygons.length || t.polygons.some(poly => poly.length < 3 || poly.some(i => !Number.isInteger(i) || !pointValid(map.vertices[i])))) errors.push(`${t.name}: add valid polygons.`);
            const positions = ['label_pos', ...(t.land ? ['army_pos', 'coast_pos'] : ['fleet_pos']),
                ...(t.land && t.supply_center ? ['supply_center_pos'] : []),
                ...(t.south_coast.length ? ['south_coast_pos'] : [])];
            for (const key of positions) if (!pointValid(t[key])) errors.push(`${t.name}: select ${key}.`);
            for (const field of ['adjacents', 'north_coast', 'south_coast']) {
                for (const name of t[field]) {
                    if (!names.has(name) || name === t.name) errors.push(`${t.name}: invalid ${field} neighbor ${name}.`);
                    if (field !== 'adjacents' && !t.adjacents.includes(name)) errors.push(`${t.name}: coast neighbor ${name} must be adjacent.`);
                }
            }
            if (!t.land && (t.north_coast.length || t.south_coast.length)) errors.push(`${t.name}: water cannot have separate coasts.`);
            if (Boolean(t.north_coast.length) !== Boolean(t.south_coast.length)) errors.push(`${t.name}: both coast neighbor lists must be populated for a two-coast province.`);
        }
        if (map.win_count > map.territories.filter(t => t.land && t.supply_center).length) errors.push('Win count exceeds the number of supply centers.');
        return errors;
    }

    const api = { palette, newMap, newTerritory, renameTerritory, setAdjacency, addPolygon, mainPolygonCenter, traceRegion, validate };
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    else root.MapBuilderModel = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
