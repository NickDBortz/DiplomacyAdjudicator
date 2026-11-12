const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'docs', 'chat.js'), 'utf8');

function createEligibilityContext() {
    const context = vm.createContext({
        LOBBY_CONVERSATION: 'lobby',
        sessionStorage: {},
        renderChat() {},
    });
    vm.runInContext(source.slice(source.indexOf('const chatState ='), source.indexOf('function unreadCount(')), context);
    return context;
}

test('private chat eligibility requires a game, an active timer, and a power', () => {
    const context = createEligibilityContext();
    const canChat = values => vm.runInContext(`
        Object.assign(chatState, ${JSON.stringify(values)});
        canPrivateChat();
    `, context);

    assert.equal(canChat({ started: true, timerActive: false, userName: 'Alice', powers: { Alice: 'France' } }), false);
    assert.equal(canChat({ started: true, timerActive: true, userName: 'Alice', powers: { Alice: 'France' } }), true);
    assert.equal(canChat({ started: true, timerActive: true, userName: 'Alice', powers: { Alice: 'Spectator' } }), false);
});

test('chat timer updates control private chat eligibility', () => {
    const context = createEligibilityContext();
    vm.runInContext(`
        chatState.el = {};
        chatState.userName = 'Alice';
        chatState.powers = { Alice: 'France' };
        chatState.started = true;
    `, context);
    const start = source.indexOf('function chatReceive(');
    const end = source.indexOf('\nfunction initChat(', start);
    vm.runInContext(source.slice(start, end), context);

    vm.runInContext("chatReceive({ type: 'lobby_update', started: true, timer: { active: true } })", context);
    assert.equal(vm.runInContext('canPrivateChat()', context), true);

    vm.runInContext("chatReceive({ type: 'lobby_update', started: true, timer: { active: false } })", context);
    assert.equal(vm.runInContext('canPrivateChat()', context), false);

    vm.runInContext("chatReceive({ type: 'game_state', state: { diplomacy_timer: { active: true } } })", context);
    assert.equal(vm.runInContext('canPrivateChat()', context), true);
});
