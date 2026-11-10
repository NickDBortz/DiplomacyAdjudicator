const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'docs', 'shared.js'), 'utf8');
const pickerSource = source.slice(source.indexOf('let availableOrders = [];'), source.indexOf('function downloadGameSave('));
const mapData = JSON.parse(fs.readFileSync(path.join(root, 'docs', 'data', 'classic_map.json'), 'utf8'));

function createPicker() {
    class Option {
        constructor(text, value) {
            this.text = text;
            this.value = value;
        }
    }
    function select() {
        return {
            value: '',
            options: [],
            replaceChildren(option) { this.options = [option]; },
            add(option) { this.options.push(option); },
        };
    }
    const elements = {
        'order-unit': select(),
        'order-type': select(),
        'order-choice': select(),
        'order-picker-status': {},
    };
    const context = vm.createContext({ mapData, Option, svg: null, document: { getElementById: id => elements[id] } });
    vm.runInContext(pickerSource, context);
    return { context, elements };
}

test('adjustment options group builds and removals by full territory name', () => {
    const { context, elements } = createPicker();
    context.setOrderPicker(['Build A STP', 'Build F STP(nc)', 'Build F STP(sc)', 'Remove F BRE']);
    const units = elements['order-unit'];
    assert.deepEqual(units.options.map(o => [o.text, o.value]), [
        ['All units and locations', ''],
        ['Brest', 'BRE'],
        ['St Petersburg', 'STP'],
    ]);
    units.value = 'STP';
    context.renderOrderChoices();
    assert.deepEqual(elements['order-choice'].options.map(o => o.value), [
        '', 'Build A STP', 'Build F STP(nc)', 'Build F STP(sc)',
    ]);
    elements['order-type'].value = 'Build';
    context.renderOrderChoices();
    assert.equal(elements['order-picker-status'].textContent, '3 of 4 available orders. Select one to submit.');
});

test('movement and retreat options show the unit and full territory name', () => {
    const { context, elements } = createPicker();
    context.setOrderPicker(['A BUD H', 'A BUD - VIE', 'F MAO - SPA(nc)', 'F MAO - SPA(sc)']);
    const units = elements['order-unit'];
    assert.deepEqual(units.options.map(o => [o.text, o.value]), [
        ['All units and locations', ''],
        ['Army Budapest', 'A BUD'],
        ['Fleet Mid-Atlantic Ocean', 'F MAO'],
    ]);
    units.value = 'F MAO';
    elements['order-type'].value = 'Move';
    context.renderOrderChoices();
    assert.deepEqual(elements['order-choice'].options.map(o => o.value), [
        '', 'F MAO - SPA(nc)', 'F MAO - SPA(sc)',
    ]);
    context.setOrderPicker(['F MAO - SPA(nc)', 'F MAO - SPA(sc)']);
    assert.equal(units.value, 'F MAO');
    assert.equal(elements['order-type'].value, 'Move');
    assert.equal(elements['order-choice'].options.length, 3);
});

test('multiplayer submits the selected order and rejects an empty selection', async () => {
    function button() {
        return { addEventListener(type, handler) { this[type] = handler; } };
    }
    const elements = {
        'order-choice': { value: '' },
        'order-error': { textContent: '' },
        'submit-order': button(),
        draw: button(),
    };
    const context = vm.createContext({
        document: { getElementById: id => elements[id] },
        clearOrderSelection() { elements['order-choice'].value = ''; },
    });
    const controlsSource = source.slice(source.indexOf('function initOrderControls('), source.indexOf('function initSidebar('));
    vm.runInContext(controlsSource, context);
    const submitted = [];
    context.initOrderControls(async order => {
        submitted.push(order);
        return 'Order submitted.';
    }, () => '');

    await elements['submit-order'].click();
    assert.equal(elements['order-error'].textContent, 'Select an order.');
    assert.deepEqual(submitted, []);

    elements['order-choice'].value = 'Build F BRE';
    await elements['submit-order'].click();
    assert.deepEqual(submitted, ['Build F BRE']);
    assert.equal(elements['order-choice'].value, '');
    assert.equal(elements['order-error'].textContent, 'Order submitted.');
});

test('highlights follow filters and narrow to the selected support or convoy', () => {
    const { context } = createPicker();
    const details = [
        'A MAR S A PAR - BUR',
        'A MAR S A PAR H',
        'A MAR - BUR',
        'F NTH C A LON - BEL',
    ].map(order => context.orderDetails(order));
    const asArray = set => [...set].sort();
    let result = context.orderHighlightData('', '', '', details);
    assert.deepEqual(asArray(result.sources), []);
    assert.deepEqual(asArray(result.targets), []);

    result = context.orderHighlightData('A MAR', '', '', details);
    assert.deepEqual(asArray(result.sources), ['MAR']);
    assert.deepEqual(asArray(result.actors), ['A MAR']);
    assert.deepEqual(asArray(result.targets), []);

    result = context.orderHighlightData('A MAR', 'Support', '', details);
    assert.deepEqual(asArray(result.sources), ['MAR']);
    assert.deepEqual(asArray(result.targets), ['BUR', 'PAR']);
    assert.deepEqual(asArray(result.related), ['A PAR']);

    result = context.orderHighlightData('A MAR', 'Support', 'A MAR S A PAR H', details);
    assert.deepEqual(asArray(result.targets), ['PAR']);
    assert.deepEqual(asArray(result.related), ['A PAR']);

    result = context.orderHighlightData('', '', 'F NTH C A LON - BEL', details);
    assert.deepEqual(asArray(result.sources), ['NTH']);
    assert.deepEqual(asArray(result.targets), ['BEL', 'LON']);
    assert.deepEqual(asArray(result.actors), ['F NTH']);
    assert.deepEqual(asArray(result.related), ['A LON']);
});

test('highlights handle build, remove, coasts, retreat and unmatched filters', () => {
    const { context } = createPicker();
    const details = [
        'Build A STP',
        'Build F STP(nc)',
        'Remove F BRE',
        'F MAO - SPA(sc)',
        'A PAR - PIC',
    ].map(order => context.orderDetails(order));
    const asArray = set => [...set].sort();
    let result = context.orderHighlightData('STP', '', '', details);
    assert.deepEqual(asArray(result.sources), ['STP']);
    assert.deepEqual(asArray(result.actors), []);
    result = context.orderHighlightData('BRE', '', '', details);
    assert.deepEqual(asArray(result.sources), ['BRE']);
    assert.deepEqual(asArray(result.actors), ['F BRE']);
    result = context.orderHighlightData('F MAO', 'Move', 'F MAO - SPA(sc)', details);
    assert.deepEqual(asArray(result.targets), ['SPA']);
    result = context.orderHighlightData('A PAR', 'Move', 'A PAR - PIC', details);
    assert.deepEqual(asArray(result.actors), ['A PAR']);
    assert.deepEqual(asArray(result.targets), ['PIC']);
    result = context.orderHighlightData('A PAR', 'Support', '', details);
    assert.deepEqual(asArray(result.sources), ['PAR']);
    assert.deepEqual(asArray(result.targets), []);
});
