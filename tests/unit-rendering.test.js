const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'docs', 'shared.js'), 'utf8');
const renderingSource = source.slice(source.indexOf('function unitPosition('));

class Element {
    constructor(tag) {
        this.tag = tag;
        this.attributes = {};
        this.children = [];
        this.dataset = {};
        this.style = {};
    }
    setAttribute(name, value) { this.attributes[name] = String(value); }
    appendChild(child) { this.children.push(child); }
    replaceChildren(...children) { this.children = children; }
    set innerHTML(value) { if (value === '') this.children = []; }
}

test('unit icons use the correct type, color and position across redraws', () => {
    const elements = {
        units: new Element('g'),
        'map-orders': new Element('g'),
        'terr-PAR': new Element('path'),
        'terr-LON': new Element('path'),
    };
    const context = vm.createContext({
        SVG_NS: 'http://www.w3.org/2000/svg',
        mapData: { water_color: '#abc', territories: [
            { abbr: 'PAR', land: true, army_pos: [20, 30], coast_pos: [25, 35] },
            { abbr: 'LON', land: true, army_pos: [40, 50], coast_pos: [45, 55] },
        ] },
        document: {
            createElementNS: (_, tag) => new Element(tag),
            getElementById: id => elements[id] || null,
        },
        window: { diplomacy: {} },
        setStatus() {},
        updateOrderHighlights() {},
    });
    vm.runInContext(renderingSource, context);
    const state = {
        players: [{ name: 'France', color: '#123456' }, { name: 'England', color: '#abcdef' }],
        territories: [{ abbr: 'PAR', owner: 'France' }, { abbr: 'LON', owner: 'England' }],
        units: [
            { type: 'A', territory: 'PAR', owner: 'France' },
            { type: 'F', territory: 'LON', owner: 'England' },
        ],
        orders: [{ type: 'Advance', territory: 'PAR', dest_territory: 'LON' }],
        phase: 'Spring', year: 1901,
    };
    for (let i = 0; i < 2; i++) {
        context.render(state);
        const [army, fleet] = elements.units.children;
        assert.equal(army.attributes.transform, 'translate(20, 30)');
        assert.equal(army.children[0].attributes.href, 'army.svg#army');
        assert.equal(army.children[0].style.color, '#123456');
        assert.equal(fleet.attributes.transform, 'translate(45, 55)');
        assert.equal(fleet.children[0].attributes.href, 'fleet.svg#fleet');
        assert.equal(fleet.children[0].style.color, '#abcdef');
        assert.deepEqual(elements['map-orders'].children.map(child => child.tag), ['line', 'polygon']);
    }
});
