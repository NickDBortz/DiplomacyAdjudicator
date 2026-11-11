const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'docs', 'radial-menu.js'), 'utf8');

function createContext() {
    function element() {
        return {
            children: [],
            attributes: {},
            style: { setProperty(name, value) { this[name] = value; } },
            setAttribute(name, value) { this.attributes[name] = value; },
            appendChild(child) { this.children.push(child); },
            addEventListener() {},
            set innerHTML(value) { this.children = []; },
        };
    }
    const context = vm.createContext({
        SVG_NS: 'svg',
        console: { log() {} },
        document: { createElementNS: () => element() },
    });
    vm.runInContext(source, context);
    return { context, element };
}

test('unit click positions menu in SVG coordinates and enables available moves', () => {
    const { context, element } = createContext();
    const svg = element();
    svg.createSVGPoint = () => ({
        matrixTransform(matrix) {
            return { x: (this.x - matrix.x) / matrix.scale, y: (this.y - matrix.y) / matrix.scale };
        },
    });
    svg.getScreenCTM = () => ({ inverse: () => ({ x: 100, y: 200, scale: 0.5 }) });
    context.svg = svg;
    context.initRadialMenu(svg);
    const unit = { territory: 'PAR', owner: 'France', type: 'A' };
    const marker = {
        dataset: unit,
        getBoundingClientRect: () => ({ left: 140, top: 245, width: 20, height: 10 }),
    };
    context.handleMapClickWithRadialMenu(
        { target: { closest: selector => selector === '.unit' ? marker : null } },
        [{ text: 'A PAR H' }, { text: 'A PAR - BUR' }, { text: 'A MAR S A PAR H' }],
        { units: [unit] }, 'France', 'Spring',
    );
    const menu = svg.children[0];
    const items = menu.children.filter(child => child.attributes['data-type']);
    assert.deepEqual(items.map(item => [item.attributes['data-type'], item.attributes.class]), [
        ['Hold', 'radial-menu-item available'],
        ['Advance', 'radial-menu-item available'],
        ['Support', 'radial-menu-item disabled'],
        ['Transform', 'radial-menu-item disabled'],
        ['Convoy', 'radial-menu-item disabled'],
    ]);
    const center = menu.children[menu.children.length - 1];
    assert.equal(center.attributes.cx, 100);
    assert.equal(center.attributes.cy, 100);
});

test('rebuilding the map attaches a fresh menu to the new SVG', () => {
    const { context, element } = createContext();
    const first = element();
    const second = element();
    const oldMenu = context.initRadialMenu(first);
    const newMenu = context.initRadialMenu(second);
    assert.notEqual(newMenu, oldMenu);
    assert.equal(newMenu.svg, second);
    assert.equal(second.children.length, 1);
    assert.equal(context.initRadialMenu(second), newMenu);
});

test('multiplayer menu submits through the game socket and reports rejection', async () => {
    const { context, element } = createContext();
    const messages = [];
    const orders = [];
    context.window = { diplomacy: {} };
    context.document.getElementById = () => null;
    context.setPickerStatus = message => messages.push(message);
    context.submitMultiplayerOrder = async order => {
        orders.push(order);
        return orders.length === 1 ? { ok: true } : { ok: false, error: 'Invalid order' };
    };
    const menu = context.initRadialMenu(element());
    menu.selectedPower = 'France';
    assert.equal(await menu.submitOrder('A PAR H'), true);
    assert.equal(await menu.submitOrder('A PAR - XYZ'), false);
    assert.deepEqual(orders, ['A PAR H', 'A PAR - XYZ']);
    assert.deepEqual(messages, ['Order submitted: A PAR H', 'Order rejected: Invalid order']);
});

test('singleplayer menu submits with the selected power', async () => {
    const { context, element } = createContext();
    const calls = [];
    context.window = { diplomacy: { order: async (...args) => { calls.push(args); return { ok: true }; } } };
    context.document.getElementById = id => id === 'greatpower' ? { value: 'France' } : null;
    context.setPickerStatus = () => {};
    const menu = context.initRadialMenu(element());
    assert.equal(await menu.submitOrder('A PAR H'), true);
    assert.deepEqual(calls, [['A PAR H', 'France']]);
});

test('both multiplayer pages load the radial menu before their game scripts', () => {
    for (const role of ['host', 'client']) {
        const html = fs.readFileSync(path.join(__dirname, '..', 'docs', `multiplayer-${role}.html`), 'utf8');
        const radial = html.indexOf('<script src="radial-menu.js"></script>');
        assert.ok(radial > html.indexOf('<script src="shared.js"></script>'));
        assert.ok(radial < html.indexOf(`<script src="multiplayer-${role}.js"></script>`));
    }
});
