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
            appendChild() {},
        };
    }
    const elements = {
        'diplomacy-timer-section': element(true),
        'timer-display': element(true),
        'timer-countdown': element(),
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
    vm.runInContext(source.slice(source.indexOf('function formatSeconds('), source.indexOf('function formatDuration(')), context);
    vm.runInContext(source.slice(source.indexOf('function updateTimerDisplay('), source.indexOf('// Tells the server this is a deliberate exit')), context);
    return { context, elements, gameInfo, tick: () => interval() };
}

function hidden(elements, id) {
    return elements[id].classList.contains('hidden');
}

test('host can see start form before a timer and after it ends', () => {
    const { context, elements, gameInfo, tick } = createScreen(true);
    context.applyGameState({ valid_orders: [] });
    assert.equal(hidden(elements, 'diplomacy-timer-section'), false);
    assert.equal(hidden(elements, 'timer-start'), false);
    assert.equal(hidden(elements, 'timer-display'), true);

    const timer = { active: true, start_time: Date.now() / 1000, duration: 1800, player_ready: {} };
    context.handleGameMessage({ type: 'lobby_update', host: 'Alice', timer });
    assert.equal(gameInfo.state.diplomacy_timer, timer);
    assert.equal(hidden(elements, 'timer-start'), true);
    assert.equal(hidden(elements, 'timer-display'), false);
    tick();
    assert.match(elements['timer-countdown'].textContent, /^30:00$|^29:59$/);

    context.handleGameMessage({ type: 'lobby_update', host: 'Alice', timer: { ...timer, active: false } });
    assert.equal(hidden(elements, 'timer-start'), false);
    assert.equal(hidden(elements, 'timer-display'), true);
    assert.equal(hidden(elements, 'diplomacy-timer-section'), false);
});

test('player timer appears on broadcast and hides when the timer ends', () => {
    const { context, elements } = createScreen(false);
    context.applyGameState({ valid_orders: [] });
    assert.equal(hidden(elements, 'diplomacy-timer-section'), true);

    const timer = { active: true, start_time: Date.now() / 1000, duration: 300, player_ready: {} };
    context.handleGameMessage({ type: 'lobby_update', host: 'Alice', timer });
    assert.equal(hidden(elements, 'diplomacy-timer-section'), false);
    assert.equal(hidden(elements, 'timer-display'), false);

    context.applyGameState({ valid_orders: [], diplomacy_timer: { ...timer, active: false } });
    assert.equal(hidden(elements, 'diplomacy-timer-section'), true);
    assert.equal(hidden(elements, 'timer-display'), true);
});
