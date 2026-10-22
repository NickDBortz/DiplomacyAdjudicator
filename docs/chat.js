// Lobby and in-game chat. The lobby channel is visible to everyone in the lobby or game; private conversations
// exist only during a game, between two players who control powers. The server sends chat_history on every
// (re)connect and chat_message as messages arrive.
const CHAT_MAX_LENGTH = 500;
const LOBBY_CONVERSATION = 'lobby';

const chatState = {
    userName: '',
    lobbyId: '',
    messages: [],  // every message this player can see, oldest first
    seenIds: new Set(),
    active: LOBBY_CONVERSATION,
    open: false,
    opened: new Set(),  // private conversations started this session, shown as tabs before the first message
    lastRead: {},  // conversation -> highest read message id; kept per tab so page changes do not re-notify
    players: [],
    powers: {},
    started: false,
    el: null,
};

function chatStorageKey(kind) {
    return `diplomacyChat${kind}:${chatState.lobbyId}`;
}

function conversationOf(message) {
    if (message.channel !== 'private') return LOBBY_CONVERSATION;
    return 'pm:' + (message.from === chatState.userName ? message.to : message.from);
}

function conversationPartner(conversation) {
    return conversation.startsWith('pm:') ? conversation.slice(3) : null;
}

function holdsPower(name) {
    const power = chatState.powers[name];
    return Boolean(power) && power !== 'Spectator';
}

function canPrivateChat() {
    return chatState.started && holdsPower(chatState.userName);
}

function unreadCount(conversation) {
    const lastRead = chatState.lastRead[conversation] || 0;
    return chatState.messages.filter(m => conversationOf(m) === conversation
        && m.from !== chatState.userName && m.id > lastRead).length;
}

function totalUnread() {
    return chatConversations().reduce((sum, c) => sum + unreadCount(c), 0);
}

function chatConversations() {
    const privates = new Set(chatState.opened);
    for (const m of chatState.messages) {
        if (m.channel === 'private') privates.add(conversationOf(m));
    }
    return [LOBBY_CONVERSATION, ...[...privates].sort()];
}

function markRead(conversation) {
    const ids = chatState.messages.filter(m => conversationOf(m) === conversation).map(m => m.id);
    if (ids.length === 0) return;
    chatState.lastRead[conversation] = Math.max(chatState.lastRead[conversation] || 0, ...ids);
    sessionStorage.setItem(chatStorageKey('Read'), JSON.stringify(chatState.lastRead));
}

function isViewing(conversation) {
    return chatState.open && chatState.active === conversation && !document.hidden;
}

function powerColor(power) {
    return (mapData?.players ?? []).find(p => p.name === power)?.color;
}

function chatElement(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
}

function buildChatWidget() {
    const root = chatElement('div', 'chat');
    root.id = 'chat';

    const toggle = chatElement('button', 'chat-toggle');
    toggle.type = 'button';
    toggle.setAttribute('aria-label', 'Open chat');
    const badge = chatElement('span', 'chat-badge hidden');
    toggle.append('Chat ', badge);
    toggle.addEventListener('click', () => setChatOpen(true));

    const panel = chatElement('div', 'chat-panel');
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Chat');
    const header = chatElement('div', 'chat-header');
    const title = chatElement('span', 'chat-title', 'Chat');
    const collapse = chatElement('button', 'chat-collapse', '–');
    collapse.type = 'button';
    collapse.title = 'Collapse chat';
    collapse.setAttribute('aria-label', 'Collapse chat');
    collapse.addEventListener('click', () => setChatOpen(false));
    header.append(title, collapse);

    const tabs = chatElement('div', 'chat-tabs');
    tabs.setAttribute('role', 'tablist');
    const newPrivate = chatElement('select', 'chat-new');
    newPrivate.setAttribute('aria-label', 'Start a private conversation');
    newPrivate.addEventListener('change', () => {
        if (!newPrivate.value) return;
        const conversation = 'pm:' + newPrivate.value;
        chatState.opened.add(conversation);
        newPrivate.value = '';
        selectConversation(conversation);
    });

    const messages = chatElement('ul', 'chat-messages');
    messages.setAttribute('aria-live', 'polite');
    const note = chatElement('p', 'chat-note hidden');

    const form = chatElement('form', 'chat-form');
    const input = chatElement('input', 'chat-input');
    input.type = 'text';
    input.maxLength = CHAT_MAX_LENGTH;
    input.placeholder = 'Message';
    input.setAttribute('aria-label', 'Chat message');
    const send = chatElement('button', 'chat-send', 'Send');
    send.type = 'submit';
    form.append(input, send);
    form.addEventListener('submit', e => {
        e.preventDefault();
        sendChat();
    });

    panel.append(header, tabs, newPrivate, messages, note, form);
    const toasts = chatElement('div', 'chat-toasts');
    root.append(toasts, panel, toggle);
    document.body.appendChild(root);
    chatState.el = { root, toggle, badge, panel, title, tabs, newPrivate, messages, note, form, input, send, toasts };
}

function setChatOpen(open) {
    chatState.open = open;
    sessionStorage.setItem(chatStorageKey('Open'), open ? '1' : '');
    chatState.el.root.classList.toggle('chat-open', open);
    if (open) {
        markRead(chatState.active);
        chatState.el.toasts.innerHTML = '';
        renderChat();
        chatState.el.input.focus();
    } else {
        renderChat();
    }
}

function selectConversation(conversation) {
    chatState.active = conversation;
    markRead(conversation);
    renderChat();
    if (chatState.open) chatState.el.input.focus();
}

function renderChat() {
    const el = chatState.el;
    if (!el) return;
    const conversations = chatConversations();
    if (!conversations.includes(chatState.active)) chatState.active = LOBBY_CONVERSATION;

    const unread = totalUnread();
    el.badge.textContent = unread > 99 ? '99+' : String(unread);
    el.badge.classList.toggle('hidden', unread === 0);
    el.toggle.setAttribute('aria-label', unread ? `Open chat, ${unread} unread` : 'Open chat');
    document.title = (unread ? `(${unread}) ` : '') + document.title.replace(/^\(\d+\+?\) /, '');

    el.tabs.innerHTML = '';
    for (const conversation of conversations) {
        const partner = conversationPartner(conversation);
        const tab = chatElement('button', 'chat-tab' + (conversation === chatState.active ? ' active' : ''));
        tab.type = 'button';
        tab.setAttribute('role', 'tab');
        tab.setAttribute('aria-selected', String(conversation === chatState.active));
        tab.textContent = partner ?? (chatState.started ? 'Everyone' : 'Lobby');
        const color = partner && powerColor(chatState.powers[partner]);
        if (color) tab.style.borderBottomColor = color;
        const count = unreadCount(conversation);
        if (count && conversation !== chatState.active) {
            tab.append(' ', chatElement('span', 'chat-tab-badge', String(count)));
        }
        tab.addEventListener('click', () => selectConversation(conversation));
        el.tabs.appendChild(tab);
    }

    // Private messages are part of the game: only players who control a power can start or answer them.
    const partners = canPrivateChat()
        ? chatState.players.filter(p => p !== chatState.userName && holdsPower(p)) : [];
    el.newPrivate.classList.toggle('hidden', partners.length === 0);
    el.newPrivate.innerHTML = '';
    el.newPrivate.appendChild(new Option('Private message…', ''));
    for (const p of partners) el.newPrivate.appendChild(new Option(`${p} (${chatState.powers[p]})`, p));

    const partner = conversationPartner(chatState.active);
    el.title.textContent = partner ? `Private: ${partner}` : (chatState.started ? 'Chat with everyone' : 'Lobby chat');
    let blocked = '';
    if (partner && !canPrivateChat()) blocked = 'Only players who control a power can send private messages.';
    else if (partner && !chatState.players.includes(partner)) blocked = `${partner} has left the game.`;
    else if (partner && !holdsPower(partner)) blocked = `${partner} no longer controls a power.`;
    el.note.textContent = blocked;
    el.note.classList.toggle('hidden', !blocked);
    el.input.disabled = Boolean(blocked);
    el.send.disabled = Boolean(blocked);
    el.input.placeholder = partner ? `Message ${partner} privately` : 'Message everyone';

    const list = el.messages;
    const atBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 40;
    list.innerHTML = '';
    const shown = chatState.messages.filter(m => conversationOf(m) === chatState.active);
    if (shown.length === 0) {
        list.appendChild(chatElement('li', 'chat-empty', partner
            ? `Only you and ${partner} can see this conversation.` : 'No messages yet.'));
    }
    for (const m of shown) {
        const mine = m.from === chatState.userName;
        const item = chatElement('li', 'chat-message' + (mine ? ' mine' : ''));
        const meta = chatElement('div', 'chat-meta');
        const sender = chatElement('span', 'chat-sender', mine ? 'You' : m.from);
        const color = powerColor(m.power);
        if (color) sender.style.color = color;
        if (m.power) sender.title = m.power;
        const time = chatElement('span', 'chat-time',
            new Date(m.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
        meta.append(sender, time);
        item.append(meta, chatElement('div', 'chat-text', m.text));
        list.appendChild(item);
    }
    if (atBottom || chatState.scrollToEnd) list.scrollTop = list.scrollHeight;
    chatState.scrollToEnd = false;
}

function showChatToast(message) {
    const conversation = conversationOf(message);
    const toast = chatElement('button', 'chat-toast');
    toast.type = 'button';
    const sender = chatElement('span', 'chat-sender', message.from + (message.channel === 'private' ? ' (private)' : ''));
    const color = powerColor(message.power);
    if (color) sender.style.color = color;
    const preview = message.text.length > 80 ? message.text.slice(0, 80) + '…' : message.text;
    toast.append(sender, chatElement('span', 'chat-toast-text', preview));
    toast.addEventListener('click', () => {
        chatState.active = conversation;
        chatState.scrollToEnd = true;
        setChatOpen(true);
    });
    const toasts = chatState.el.toasts;
    toasts.appendChild(toast);
    while (toasts.children.length > 3) toasts.firstChild.remove();
    setTimeout(() => toast.remove(), 6000);
}

function addChatMessage(message, notify) {
    if (chatState.seenIds.has(message.id)) return;
    chatState.seenIds.add(message.id);
    chatState.messages.push(message);
    const conversation = conversationOf(message);
    if (message.from === chatState.userName || isViewing(conversation)) {
        markRead(conversation);
        if (message.from === chatState.userName) chatState.scrollToEnd = true;
    } else if (notify) {
        showChatToast(message);
    }
}

async function sendChat() {
    const el = chatState.el;
    const text = el.input.value.trim();
    if (!text) return;
    const partner = conversationPartner(chatState.active);
    const payload = partner
        ? { type: 'chat_send', channel: 'private', to: partner, text }
        : { type: 'chat_send', channel: 'lobby', text };
    el.send.disabled = true;
    try {
        const reply = await sendForReply(payload, 'chat_result');
        if (reply.ok) {
            el.input.value = '';
            el.note.classList.add('hidden');
        } else {
            el.note.textContent = reply.error;
            el.note.classList.remove('hidden');
        }
    } catch (e) {
        el.note.textContent = e.message;
        el.note.classList.remove('hidden');
    } finally {
        el.send.disabled = false;
        el.input.focus();
    }
}

// Called by watchLobby for every server message.
function chatReceive(msg) {
    if (!chatState.el) return;
    if (msg.type === 'chat_history') {
        // Replaces everything: after a reconnect the server's copy is complete, and departed players'
        // private conversations are gone.
        chatState.messages = [];
        chatState.seenIds.clear();
        for (const m of msg.messages) addChatMessage(m, false);
        chatState.scrollToEnd = true;
    } else if (msg.type === 'chat_message') {
        addChatMessage(msg.message, true);
    } else if (msg.type === 'lobby_update') {
        chatState.players = msg.players || chatState.players;
        chatState.powers = msg.selected_powers || chatState.powers;
        chatState.started = Boolean(msg.started);
    } else if (msg.type === 'game_state') {
        chatState.players = msg.state.lobby_players || chatState.players;
        chatState.powers = msg.state.selected_powers || chatState.powers;
        chatState.started = true;
    } else {
        return;
    }
    renderChat();
}

function initChat(lobbyId, userName) {
    chatState.lobbyId = lobbyId;
    chatState.userName = userName;
    try {
        chatState.lastRead = JSON.parse(sessionStorage.getItem(chatStorageKey('Read'))) || {};
    } catch {
        chatState.lastRead = {};
    }
    buildChatWidget();
    setChatOpen(Boolean(sessionStorage.getItem(chatStorageKey('Open'))));
    // Returning to the tab counts as reading the conversation that is on screen.
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden && chatState.open) {
            markRead(chatState.active);
            renderChat();
        }
    });
}
