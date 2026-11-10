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
    const context = vm.createContext({ mapData, Option, document: { getElementById: id => elements[id] } });
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
    const context = vm.createContext({ document: { getElementById: id => elements[id] } });
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
