const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'docs', 'shared.js'), 'utf8');

function createScreen(host) {
    function element(hidden = false) {
        const classes = new Set(hidden ? ['hidden'] : []);
        return {
            classList: {
                toggle(name, force) {
                    if (force) classes.add(name);
                    else classes.delete(name);
                },
                contains: name => classes.has(name),
            },
            textContent: '',
            innerHTML: '',
            children: [],
            appendChild(child) { this.children.push(child); },
        };
    }
    const elements = {
        'diplomacy-timer-section': element(true),
        'timer-display': element(true),
        'timer-countdown': element(),
        'sidebar-timer-countdown': element(),
        'main-timer-banner': element(true),
        'sidebar-timer-banner': element(true),
        'timer-player-status': element(),
        'resolve': element(),
    };
    if (host) elements['timer-start'] = element();
    const window = { diplomacy: { state: null, timerInterval: null } };
    const gameInfo = { state: null, userName: host ? 'Alice' : 'Bob', host: 'Alice' };
    let interval;
    const context = vm.createContext({
        window, gameInfo, document: {
            getElementById: id => elements[id] || null,
            createElement: () => element(),
        },
        sessionStorage: { setItem() {} },
        render(state) { window.diplomacy.state = state; },
        renderHostTools() {}, renderSubmittedOrders() {}, updateGameRole() {}, renderGameInfo() {},
        setOrderPicker() {}, resetOrderFilters() {}, renderPlayerList() {},
        setInterval(fn) { interval = fn; return 1; },
        clearInterval() { interval = null; },
    });
    vm.runInContext(source.slice(source.indexOf('function applyGameState('), source.indexOf('let availableOrders = [];')), context);
    vm.runInContext(source.slice(source.indexOf('function handleGameMessage('), source.indexOf('// Host tools during a game:')), context);
    vm.runInContext(source.slice(source.indexOf('function formatSeconds('), source.indexOf('function initTimerDial(')), context);
    vm.runInContext(source.slice(source.indexOf('function updateTimerDisplay('), source.indexOf('// Tells the server this is a deliberate exit')), context);
    return { context, elements, gameInfo, tick: () => interval() };
}

function hidden(elements, id) {
    return elements[id].classList.contains('hidden');
}

test('both game pages place timer banners above the map and sidebar content', () => {
    for (const file of ['multiplayer-host.html', 'multiplayer-client.html']) {
        const html = fs.readFileSync(path.join(__dirname, '..', 'docs', file), 'utf8');
        const sidebarTimer = html.indexOf('id="sidebar-timer-banner"');
        const hostControls = html.indexOf('id="host-controls"');
        const main = html.indexOf('id="main"');
        const mainTimer = html.indexOf('id="main-timer-banner"');
        const map = html.indexOf('id="map"');
        assert.ok(sidebarTimer > 0 && sidebarTimer < html.indexOf('id="info"'));
        assert.ok(sidebarTimer < hostControls && hostControls < main);
        assert.ok(main < mainTimer && mainTimer < map);
    }
});

test('host can see start form before a timer and after it ends', () => {
    const { context, elements, gameInfo, tick } = createScreen(true);
    context.applyGameState({ valid_orders: [], selected_powers: { Alice: 'France', Bob: 'England' } });
    assert.equal(hidden(elements, 'diplomacy-timer-section'), false);
    assert.equal(hidden(elements, 'timer-start'), false);
    assert.equal(hidden(elements, 'timer-display'), true);
    assert.equal(hidden(elements, 'main-timer-banner'), true);
    assert.equal(hidden(elements, 'sidebar-timer-banner'), true);

    const timer = { active: true, start_time: Date.now() / 1000, duration: 1800, player_ready: { Alice: true, Bob: false } };
    context.handleGameMessage({ type: 'lobby_update', host: 'Alice', timer });
    assert.equal(gameInfo.state.diplomacy_timer, timer);
    assert.equal(hidden(elements, 'timer-start'), true);
    assert.equal(hidden(elements, 'timer-display'), false);
    assert.equal(hidden(elements, 'main-timer-banner'), false);
    assert.equal(hidden(elements, 'sidebar-timer-banner'), false);
    assert.deepEqual(elements['timer-player-status'].children.map(item => item.textContent), ['Bob: ○']);
    tick();
    assert.match(elements['timer-countdown'].textContent, /^30:00$|^29:59$/);
    assert.equal(elements['sidebar-timer-countdown'].textContent, elements['timer-countdown'].textContent);

    context.handleGameMessage({ type: 'lobby_update', host: 'Alice', timer: { ...timer, active: false } });
    assert.equal(hidden(elements, 'timer-start'), false);
    assert.equal(hidden(elements, 'timer-display'), true);
    assert.equal(hidden(elements, 'diplomacy-timer-section'), false);
    assert.equal(hidden(elements, 'main-timer-banner'), true);
    assert.equal(hidden(elements, 'sidebar-timer-banner'), true);
});

test('player timer appears on broadcast and hides when the timer ends', () => {
    const { context, elements } = createScreen(false);
    context.applyGameState({ valid_orders: [] });
    assert.equal(hidden(elements, 'diplomacy-timer-section'), true);
    assert.equal(hidden(elements, 'main-timer-banner'), true);
    assert.equal(hidden(elements, 'sidebar-timer-banner'), true);

    const timer = { active: true, start_time: Date.now() / 1000, duration: 300, player_ready: {} };
    context.handleGameMessage({ type: 'lobby_update', host: 'Alice', timer });
    assert.equal(hidden(elements, 'diplomacy-timer-section'), false);
    assert.equal(hidden(elements, 'timer-display'), false);
    assert.equal(hidden(elements, 'main-timer-banner'), false);
    assert.equal(hidden(elements, 'sidebar-timer-banner'), false);
    assert.equal(elements['sidebar-timer-countdown'].textContent, elements['timer-countdown'].textContent);

    context.applyGameState({ valid_orders: [], diplomacy_timer: { ...timer, active: false } });
    assert.equal(hidden(elements, 'diplomacy-timer-section'), true);
    assert.equal(hidden(elements, 'timer-display'), true);
    assert.equal(hidden(elements, 'main-timer-banner'), true);
    assert.equal(hidden(elements, 'sidebar-timer-banner'), true);
});

function createDurationControls() {
    const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'multiplayer-host.html'), 'utf8');
    function element() {
        return {
            listeners: {},
            addEventListener(type, handler) { this.listeners[type] = handler; },
            fire(type, event = {}) { return this.listeners[type](event); },
        };
    }
    const inputs = {};
    const dials = {};
    for (const unit of ['hours', 'minutes', 'seconds']) {
        const tag = html.match(new RegExp(`<input id="timer-${unit}"[^>]+>`))[0];
        const attr = name => tag.match(new RegExp(`\\b${name}="([^"]+)"`))[1];
        const input = Object.assign(element(), {
            value: attr('value'), min: attr('min'), max: attr('max'),
            setPointerCapture() {},
        });
        Object.defineProperty(input, 'validity', {
            get() {
                const value = Number(this.value);
                return { valid: this.value !== '' && Number.isInteger(value) && value >= Number(this.min) && value <= Number(this.max) };
            },
        });
        const up = Object.assign(element(), { dataset: { step: '1' } });
        const down = Object.assign(element(), { dataset: { step: '-1' } });
        inputs[`timer-${unit}`] = input;
        dials[unit] = { input, up, down, querySelector: () => input, querySelectorAll: () => [up, down] };
    }
    const start = element();
    const end = element();
    const section = {};
    const timerStart = { querySelectorAll: () => Object.values(dials) };
    const elements = {
        ...inputs,
        'timer-start': timerStart,
        'timer-start-btn': start,
        'timer-end-early': end,
        'diplomacy-timer-section': section,
    };
    const calls = [];
    const alerts = [];
    const confirmations = [];
    const context = vm.createContext({
        document: { getElementById: id => elements[id] || null },
        sendHostAction: async (button, payload) => { calls.push(payload); return { ok: true }; },
        alert: message => alerts.push(message),
        confirmAction: (title, message, callback) => confirmations.push({ title, message, callback }),
    });
    vm.runInContext(source.slice(source.indexOf('function initTimerDial('), source.indexOf('function updateTimerDisplay(')), context);
    context.initTimerControls();
    return { dials, start, end, calls, alerts, confirmations };
}

test('duration defaults to 15 minutes and submits exact hours, minutes, and seconds', async () => {
    const { dials, start, calls } = createDurationControls();
    await start.fire('click');
    assert.equal(calls[0].duration, 900);
    dials.hours.input.value = '1';
    dials.minutes.input.value = '2';
    dials.seconds.input.value = '3';
    await start.fire('click');
    assert.equal(calls[1].duration, 3723);
});

test('dial arrows and vertical dragging adjust values within each dial range', () => {
    const { dials } = createDurationControls();
    const { input, up, down } = dials.minutes;
    up.fire('click');
    assert.equal(input.value, '16');
    down.fire('click');
    assert.equal(input.value, '15');
    input.fire('pointerdown', { button: 0, pointerId: 1, clientY: 100 });
    input.fire('pointermove', { pointerId: 1, clientY: 64 });
    assert.equal(input.value, '18');
    input.fire('pointermove', { pointerId: 1, clientY: 112 });
    assert.equal(input.value, '14');
    input.fire('pointermove', { pointerId: 1, clientY: 100 });
    assert.equal(input.value, '15');
    input.fire('lostpointercapture');
    input.fire('pointermove', { pointerId: 1, clientY: 0 });
    assert.equal(input.value, '15');
    input.value = '59';
    up.fire('click');
    assert.equal(input.value, '59');
    dials.hours.input.value = '0';
    dials.hours.down.fire('click');
    assert.equal(dials.hours.input.value, '00');
    dials.hours.input.value = '24';
    dials.hours.up.fire('click');
    assert.equal(dials.hours.input.value, '24');
});

test('duration validation accepts the bounds and rejects incomplete or excessive values', async () => {
    const { dials, start, calls, alerts } = createDurationControls();
    dials.minutes.input.value = '5';
    await start.fire('click');
    assert.equal(calls[0].duration, 300);
    dials.hours.input.value = '24';
    dials.minutes.input.value = '0';
    await start.fire('click');
    assert.equal(calls[1].duration, 86400);
    dials.seconds.input.value = '1';
    await start.fire('click');
    dials.hours.input.value = '0';
    dials.minutes.input.value = '4';
    dials.seconds.input.value = '59';
    await start.fire('click');
    dials.minutes.input.value = '';
    await start.fire('click');
    dials.minutes.input.value = '60';
    await start.fire('click');
    assert.equal(calls.length, 2);
    assert.equal(alerts.length, 4);
});

test('ending the timer uses the shared confirmation modal', async () => {
    const { end, calls, confirmations } = createDurationControls();
    await end.fire('click');
    assert.equal(confirmations.length, 1);
    assert.equal(confirmations[0].title, 'End Timer');
    assert.equal(confirmations[0].message, 'End the Diplomacy phase timer?');
    assert.equal(calls.length, 0);

    await confirmations[0].callback();
    assert.equal(calls.length, 1);
    assert.equal(calls[0].type, 'end_diplomacy_timer');
});
