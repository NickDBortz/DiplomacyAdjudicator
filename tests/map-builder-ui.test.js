const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const model = require('../tools/map_builder_model.js');

function createEditor() {
    class Element {
        constructor() {
            this.value = '';
            this.files = [];
            this.children = [];
            this.listeners = {};
            this.style = {};
            this.classList = { add() {} };
        }
        addEventListener(type, callback) { this.listeners[type] = callback; }
        dispatch(type, data = {}) { this.listeners[type]({ target: this, ...data }); }
        append(...children) { this.children.push(...children); }
        replaceChildren(...children) { this.children = children; }
        setAttribute(name, value) { this[name] = value; }
        createSVGPoint() { return { matrixTransform() { return this; } }; }
        getScreenCTM() { return { inverse() { return {}; } }; }
        click() {}
    }

    const elements = {};
    const html = fs.readFileSync(path.join(__dirname, '../tools/map_builder.html'), 'utf8');
    for (const match of html.matchAll(/id="([^"]+)"/g)) elements[match[1]] = new Element();
    elements.mode.value = 'select';
    elements.zoom.value = '100';
    elements.threshold.value = '200';
    let download;
    const document = {
        getElementById: id => elements[id],
        createElement(tag) {
            const element = new Element();
            if (tag === 'canvas') element.getContext = () => ({
                drawImage() {},
                getImageData() {
                    const data = new Uint8ClampedArray(8 * 8 * 4);
                    for (let y = 1; y < 7; y++) for (let x = 1; x < 7; x++) {
                        const i = (y * 8 + x) * 4;
                        data.fill(255, i, i + 4);
                    }
                    return { width: 8, height: 8, data };
                }
            });
            return element;
        },
        createElementNS() { return new Element(); }
    };
    class Image {
        constructor() { this.width = 8; this.height = 8; }
        set src(value) { this.onload(); }
    }
    const url = {
        createObjectURL(value) {
            if (value instanceof Blob) download = value;
            return 'blob:test';
        },
        revokeObjectURL() {}
    };
    const script = fs.readFileSync(path.join(__dirname, '../tools/map_builder.js'), 'utf8');
    vm.runInNewContext(script, {
        MapBuilderModel: model, document, Image, URL: url, Blob, setTimeout() {}, confirm: () => true
    });
    elements.image.files = [{}];
    elements.image.dispatch('change');
    elements['add-territory'].dispatch('click');
    return {
        elements,
        clickMap(x, y) { elements.map.dispatch('click', { clientX: x, clientY: y }); },
        async draft() {
            elements['save-draft'].dispatch('click');
            return JSON.parse(await download.text());
        }
    };
}

test('a detected polygon is already saved when Finish polygon is clicked', async () => {
    const editor = createEditor(), { elements } = editor;
    elements.mode.value = 'region';
    editor.clickMap(3, 3);
    assert.match(elements.message.textContent, /added automatically/);
    elements.finish.dispatch('click');
    assert.match(elements.message.textContent, /added automatically/);
    elements.mode.value = 'trace';
    elements.finish.dispatch('click');
    assert.match(elements.message.textContent, /added automatically/);
    const map = await editor.draft();
    assert.equal(map.territories[0].polygons.length, 1);
    assert.equal(map.territories[0].polygons[0].length, 4);
    elements['remove-polygon'].dispatch('click');
    assert.equal((await editor.draft()).territories[0].polygons.length, 0);
});

test('manual points remain finishable and prevent accidental region mixing', async () => {
    const editor = createEditor(), { elements } = editor;
    elements.mode.value = 'trace';
    editor.clickMap(1, 1);
    elements.finish.dispatch('click');
    assert.match(elements.message.textContent, /at least three points/);
    editor.clickMap(6, 1);
    elements.mode.value = 'region';
    editor.clickMap(3, 3);
    assert.match(elements.message.textContent, /Finish or undo/);
    elements.mode.value = 'trace';
    editor.clickMap(6, 6);
    elements.finish.dispatch('click');
    assert.equal(elements.message.textContent, 'Polygon added.');
    assert.equal((await editor.draft()).territories[0].polygons[0].length, 3);
});
