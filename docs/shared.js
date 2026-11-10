const SVG_NS = 'http://www.w3.org/2000/svg';

// Backend base URL; override with ?api=<url> or localStorage 'diplomacyApi'.
const API_BASE = (new URLSearchParams(location.search).get('api')
    || localStorage.getItem('diplomacyApi')
    || (['localhost', '127.0.0.1'].includes(location.hostname) ? 'http://localhost:8001' : 'https://diplomacyadjudicator.onrender.com')
).replace(/\/$/, '');

let mapData, svg;
window.diplomacy = window.diplomacy || { state: null };

function setStatus(text) {
    document.getElementById('status').textContent = text;
}

// Transient popup for server events; leaves the phase banner (#status) untouched.
let notifyTimer = null;
function notify(text, sticky = false) {
    let el = document.getElementById('notification');
    if (!el) {
        el = document.createElement('div');
        el.id = 'notification';
        el.setAttribute('role', 'status');
        document.body.appendChild(el);
    }
    clearTimeout(notifyTimer);
    el.textContent = text;
    el.classList.add('visible');
    if (!sticky) notifyTimer = setTimeout(() => el.classList.remove('visible'), 4000);
}

const loadingPopup = document.getElementById('loading-popup');

function showLoading() {
    loadingPopup.classList.remove('popup-hidden');
}

function hideLoading() {
    loadingPopup.classList.add('popup-hidden');
}

window.addEventListener('load', hideLoading);

async function request(method, path, body, loading_screen = false) {
    if (loading_screen) showLoading();
    const res = await fetch(API_BASE + path, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
    });
    if (loading_screen) hideLoading();
    if (!res.ok) throw new Error(`${method} ${path} failed: ${res.status} ${await res.text()}`);
    return res.json();
}

function goTo(page) {
    location.href = page;
}

// Opens the lobby socket; the server pushes lobby_update on joins, leaves and settings changes, and game_started on start.
function connectLobby(lobbyId, userName, secretToken, onMessage, onClose) {
    const url = `${API_BASE.replace(/^http/, 'ws')}/ws/lobbies/${encodeURIComponent(lobbyId)}?user_name=${encodeURIComponent(userName)}`;
    const ws = new WebSocket(url);
    let ping;
    ws.onopen = () => { ws.send(secretToken); ping = setInterval(() => ws.send('ping'), 25000); };
    ws.onmessage = e => onMessage(JSON.parse(e.data));
    ws.onclose = e => { clearInterval(ping); onClose(e.code); };
    return ws;
}

const LOBBY_CLOSE_MESSAGES = {
    4404: 'This lobby no longer exists.',
    4401: 'Could not verify your identity. Please rejoin the lobby.',
    4403: 'You are not a member of this lobby.',
    4409: 'This seat was opened in another tab or window.',
    4410: 'You were kicked from the lobby by the host.',
    4408: 'The host did not answer your request in time.',
    4412: 'The host declined your request to join.',
};
// Closes that mean the seat is gone (or in use elsewhere), so reconnecting would not help.
const FINAL_CLOSE_CODES = [4401, 4403, 4404, 4409, 4410];
const SEAT_LOST_CLOSE_CODES = [4403, 4404, 4410];

// The seat survives in localStorage so a player who closes the tab or loses connection can rejoin from the menu.
const SESSION_KEY = 'diplomacySession';

function rememberSeat(lobbyId, lobbyName, userName, secretToken) {
    sessionStorage.setItem('diplomacyGameID', lobbyId);
    sessionStorage.setItem('diplomacyGameName', lobbyName);
    sessionStorage.setItem('diplomacyGameCode', lobbyName);
    sessionStorage.setItem('diplomacyPlayerName', userName);
    sessionStorage.setItem('secretToken', secretToken);
    localStorage.setItem(SESSION_KEY, JSON.stringify({ lobbyId, lobbyName, userName, secretToken }));
}

function loadSession() {
    try {
        const session = JSON.parse(localStorage.getItem(SESSION_KEY));
        return session && session.lobbyId && session.userName && session.secretToken ? session : null;
    } catch {
        return null;
    }
}

function clearSession() {
    localStorage.removeItem(SESSION_KEY);
}

// Set by the lobby and game pages so the current host gets Kick and Make host buttons next to other players.
let playerListKickEnabled = false;

function renderPlayerList(players, selfName, powers = {}, connected = null) {
    if (connected) gameInfo.connected = connected;
    const online = gameInfo.connected;
    const inGame = Boolean(gameInfo.state);
    const canManage = playerListKickEnabled && gameInfo.host === selfName;
    const colors = Object.fromEntries((mapData?.players ?? []).map(p => [p.name, p.color]));
    const list = document.getElementById('player-list');
    list.innerHTML = '';
    for (const name of players) {
        const isOnline = !online || online.includes(name);
        const item = document.createElement('li');
        item.className = 'player-item' + (isOnline ? '' : ' player-offline');
        const color = colors[powers[name]];
        if (color) item.style.borderLeftColor = color;
        const label = document.createElement('span');
        label.textContent = name === selfName ? `${name} (you)` : name;
        if (color) label.style.color = color;
        if (name === gameInfo.host) {
            const tag = document.createElement('span');
            tag.className = 'player-tag';
            tag.textContent = 'host';
            label.append(' ', tag);
        }
        const power = document.createElement('span');
        power.className = 'player-power';
        power.textContent = (powers[name] || 'No power selected') + (isOnline ? '' : ' · disconnected');
        const details = document.createElement('div');
        details.className = 'player-details';
        details.append(label, power);
        item.appendChild(details);

        if (canManage && name !== selfName) {
            const buttons = document.createElement('div');
            buttons.className = 'player-buttons';
            // During a game the host has to control a power, so spectators cannot take the role.
            if (isOnline && !(inGame && (!powers[name] || powers[name] === 'Spectator'))) {
                buttons.appendChild(playerActionButton('Make host', 'player-action', `Make ${name} the host`, button => {
                    confirmAction('Hand Over Host', `Make ${name} the host? They can hand it back to you later.`,
                        () => sendHostAction(button, { type: 'transfer_host', user_name: name }, 'host_transfer_result'));
                }));
            }
            buttons.appendChild(playerActionButton('Kick', 'order-delete', `Kick player: ${name}`, button => {
                const held = inGame && powers[name] && powers[name] !== 'Spectator';
                const message = held
                    ? `Remove ${name} from the game? ${powers[name]} will become vacant: its units hold until you give it to someone else.`
                    : `Remove ${name} from the game?`;
                confirmAction('Kick Player', message,
                    () => sendHostAction(button, { type: 'kick_player', user_name: name }, 'kick_result'));
            }));
            item.appendChild(buttons);
        }
        list.appendChild(item);
    }
}

function playerActionButton(text, className, label, onClick) {
    const button = document.createElement('button');
    button.className = className;
    button.type = 'button';
    button.textContent = text;
    button.title = label;
    button.setAttribute('aria-label', label);
    button.addEventListener('click', () => onClick(button));
    return button;
}

// Sends a host-only command; the button is re-enabled if the server refuses it.
async function sendHostAction(button, payload, replyType) {
    if (button) button.disabled = true;
    try {
        const reply = await sendForReply(payload, replyType);
        if (!reply.ok) {
            notify(reply.error);
            if (button) button.disabled = false;
        }
        return reply;
    } catch (e) {
        notify(e.message);
        if (button) button.disabled = false;
        return { ok: false, error: e.message };
    }
}

function lobbyEventMessage(msg, userName) {
    const who = msg.user_name;
    const self = who === userName;
    const inGame = msg.started;
    switch (msg.event) {
        case 'joined':
            return self ? null : `${who} ${inGame ? 'connected' : 'joined the lobby'}`;
        case 'left':
            return self ? null : `${who} left the ${inGame ? 'game' : 'lobby'}`;
        case 'kicked':
            return `${who} was kicked by the host`;
        case 'disconnected':
            return `${who} lost connection. Their seat is kept until they return or the host kicks them.`;
        case 'host_changed':
            return self ? 'You are now the host.' : `${who} is now the host`;
        case 'power_assigned':
            return self ? `You now control ${msg.power}.` : `${who} now controls ${msg.power}`;
        case 'admitted':
            return `${who} joined the game as ${msg.power === 'Spectator' ? 'a spectator' : msg.power}`;
        case 'join_request':
            return msg.host === userName ? `${who} is asking to join. Answer in Host Controls.` : null;
        case 'joins_toggled':
            return `The game is ${msg.accepting_joins ? 'now open' : 'closed'} to new players`;
        default:
            return null;
    }
}

// Shared by the lobby and game pages; onMessage sees every server message first. The returned connection
// reconnects on its own after a dropped connection, so callers keep using the same object.
function watchLobby(lobbyId, userName, secretToken, onMessage = () => {}) {
    const mainDiv = document.getElementById('main');
    const conn = {
        socket: null,
        leaving: false,
        get readyState() { return this.socket ? this.socket.readyState : WebSocket.CLOSED; },
        send(data) { this.socket.send(data); },
        addEventListener(type, listener) { this.socket.addEventListener(type, listener); },
    };
    let retryDelay = 1000;
    let retryTimer = null;
    let reconnecting = false;
    const hasChat = typeof initChat === 'function';
    if (hasChat) initChat(lobbyId, userName);

    const open = () => {
        retryTimer = null;
        conn.socket = connectLobby(lobbyId, userName, secretToken, msg => {
            if (reconnecting) {
                reconnecting = false;
                mainDiv.classList.remove('disabled-div');
                notify('Reconnected.');
            }
            retryDelay = 1000;
            onMessage(msg);
            if (hasChat) chatReceive(msg);
            const pending = pendingReplies[msg.type];
            if (pending && pending.length > 0) {
                pending.shift()(msg);
                if (pending.length === 0) delete pendingReplies[msg.type];
            }
            if (msg.type !== 'lobby_update') return;
            renderPlayerList(msg.players, userName, msg.selected_powers, msg.connected_players);
            const status = lobbyEventMessage(msg, userName);
            if (status) notify(status);
        }, code => {
            if (conn.leaving) return;
            if (SEAT_LOST_CLOSE_CODES.includes(code)) clearSession();
            mainDiv.classList.add('disabled-div');
            if (FINAL_CLOSE_CODES.includes(code)) {
                renderPlayerList([], userName);
                notify(LOBBY_CLOSE_MESSAGES[code] || 'Connection to the lobby was lost.', true);
                return;
            }
            reconnecting = true;
            notify(`Connection lost. Reconnecting in ${Math.round(retryDelay / 1000)}s...`, true);
            retryTimer = setTimeout(open, retryDelay);
            retryDelay = Math.min(retryDelay * 2, 30000);
        });
    };
    // Retry right away when the browser reports the network is back.
    window.addEventListener('online', () => {
        if (retryTimer !== null) {
            clearTimeout(retryTimer);
            open();
        }
    });
    open();
    return conn;
}

// In-game state: the lobby socket doubles as the game socket once the game has started.
let gameSocket = null;
const pendingReplies = {};
const gameInfo = { base: '', host: '', userName: '', power: sessionStorage.getItem('power') || '', state: null, latestSave: null, connected: null, lobby: null };

// What this power can act on in the current phase.
function phaseInfoLines(state, power) {
    const player = state.players.find(p => p.name === power);
    if (!player) return [];
    const mine = state.units.filter(u => u.owner === power);
    const lines = [];

    if (state.phase === 'Spring' || state.phase === 'Fall') {
        lines.push(`Units for ${power}:`, ...mine.map(u => `- ${u.type} in ${u.territory}`));
    } else if (state.phase === 'Spring Retreat' || state.phase === 'Fall Retreat') {
        lines.push(`Dislodged units for ${power}:`,
            ...mine.filter(u => u.dislodged).map(u => `- ${u.type} in ${u.dislodged_from}`));
    } else if (state.phase === 'Adjustment') {
        const toBuild = player.units_to_build;
        lines.push(`Adjustment for ${power}:`);
        if (toBuild > 0) {
            lines.push(`- Units to build: ${toBuild}`, '', `Available supply centers for ${power}:`,
                ...player.supply_centers.map(c => `- ${c}`));
        } else if (toBuild < 0) {
            lines.push(`- Units to disband: ${-toBuild}`, '', `Current units for ${power} that can be disbanded:`,
                ...mine.map(u => `- ${u.type} in ${u.territory}`));
        } else {
            lines.push('- Nothing to build or disband');
        }
    }
    return lines;
}

function renderGameInfo() {
    const state = gameInfo.state;
    const lines = [gameInfo.base];
    if (gameInfo.host) lines.push(`Host: ${gameInfo.host}`);
    lines.push(`Power: ${gameInfo.power || 'none (spectating)'}`);
    if (state) {
        const phase = phaseInfoLines(state, gameInfo.power);
        if (phase.length > 0) lines.push('', ...phase);
        if (state.draw_votes && state.draw_votes.length > 0) {
            lines.push('', 'Draw votes:', ...state.draw_votes.map(v => `- ${v}`));
        }
    }
    document.getElementById('info').textContent = lines.join('\n');
}

function updateGameRole() {
    const spectator = gameInfo.power === 'Spectator';
    const actions = document.getElementById('player-actions');
    const spectatorMessage = document.getElementById('spectator-message');
    const hostControls = document.getElementById('host-controls');
    if (actions) actions.classList.toggle('hidden', spectator || gameInfo.state?.orders_revealed);
    if (spectatorMessage) {
        spectatorMessage.classList.toggle('hidden', !spectator);
        spectatorMessage.textContent = gameInfo.state?.player_eliminated
            ? 'Your power has been eliminated. You are now spectating.'
            : 'You are spectating. Orders appear after the host renders them.';
    }
    if (hostControls) hostControls.classList.toggle('hidden', spectator || gameInfo.host !== gameInfo.userName);
}

// The server sends every unit and territory, plus this player's orders (everyone's once revealed).
function applyGameState(state) {
    const previous = gameInfo.state;
    if (previous && (previous.phase !== state.phase || previous.year !== state.year ||
        previous.player_power !== state.player_power || state.orders_revealed)) {
        resetOrderFilters();
    }
    render(state);
    gameInfo.state = state;
    gameInfo.power = state.player_power ?? gameInfo.power;
    gameInfo.host = state.host ?? gameInfo.host;
    sessionStorage.setItem('power', gameInfo.power);
    if (state.lobby_players) renderPlayerList(state.lobby_players, gameInfo.userName, state.selected_powers, state.connected_players);
    renderHostTools(state);
    const resolveBtn = document.getElementById('resolve');
    if (resolveBtn) resolveBtn.textContent = state.orders_revealed ? 'Resolve Orders' : 'Render Orders';
    renderSubmittedOrders(state);
    updateGameRole();
    renderGameInfo();
    if (!Array.isArray(state.valid_orders)) {
        setOrderPicker([], 'Available orders were not provided by the server.');
    } else {
        setOrderPicker(state.valid_orders, state.orders_revealed
            ? 'Orders are revealed; wait for the host to resolve them.'
            : 'No available orders for this power.');
    }
}

let availableOrders = [];
let mapOrderTargets = [];

function orderMapTargets(order) {
    const parts = order.text.split(' ');
    const territory = value => value.replace(/\([^)]*\)$/, '');
    if (parts[2] === '-') return [territory(parts[3])];
    if (parts[2] === 'S' || parts[2] === 'C') {
        const targets = [territory(parts[4])];
        if (parts[5] === '-' && parts[6]) targets.push(territory(parts[6]));
        return targets;
    }
    return [];
}

function setPickerStatus(message) {
    document.getElementById('order-picker-status').textContent = message;
    const mapStatus = document.getElementById('map-order-status');
    if (mapStatus) mapStatus.textContent = message;
}

function matchingOrderTargets(order) {
    const targets = orderMapTargets(order);
    return mapOrderTargets.every((target, index) => targets[index] === target);
}

function orderDetails(text) {
    const parts = text.split(' ');
    const adjustment = parts[0] === 'Build' || parts[0] === 'Remove';
    const unit = adjustment ? parts[2].replace(/\([^)]*\)$/, '')
        : `${parts[0]} ${parts[1]}`;
    const action = adjustment ? parts[0] : parts[2].split('(')[0];
    const types = { H: 'Hold', '-': 'Move', S: 'Support', C: 'Convoy', T: 'Transform',
        Build: 'Build', Remove: 'Remove' };
    return { text, unit, type: types[action] || action };
}

function replaceOptions(select, placeholder, values, label = value => value) {
    const previous = select.value;
    select.replaceChildren(new Option(placeholder, ''));
    for (const value of values) select.add(new Option(label(value), value));
    select.value = values.includes(previous) ? previous : '';
}

function unitFilterLabel(unit) {
    const parts = unit.split(' ');
    const abbr = parts.length === 2 ? parts[1] : parts[0];
    const territory = mapData.territories.find(t => t.abbr === abbr);
    const name = territory ? territory.name : abbr;
    if (parts.length === 1) return name;
    return `${parts[0] === 'A' ? 'Army' : 'Fleet'} ${name}`;
}

function setOrderPicker(orders, emptyMessage = 'No available orders for this power.') {
    const unitSelect = document.getElementById('order-unit');
    if (!unitSelect) return;
    if (orders.length !== availableOrders.length || orders.some((text, i) => text !== availableOrders[i].text)) {
        mapOrderTargets = [];
    }
    availableOrders = orders.map(orderDetails);
    const typeSelect = document.getElementById('order-type');
    const units = [...new Set(availableOrders.map(o => o.unit))]
        .sort((a, b) => unitFilterLabel(a).localeCompare(unitFilterLabel(b)));
    replaceOptions(unitSelect, 'All units and locations', units, unitFilterLabel);
    replaceOptions(typeSelect, 'All order types', [...new Set(availableOrders.map(o => o.type))].sort());
    unitSelect.disabled = availableOrders.length === 0;
    typeSelect.disabled = availableOrders.length === 0;
    renderOrderChoices(emptyMessage);
}

function renderOrderChoices(emptyMessage = 'No available orders for this power.') {
    const unit = document.getElementById('order-unit').value;
    const type = document.getElementById('order-type').value;
    const matching = availableOrders.filter(o => (!unit || o.unit === unit) && (!type || o.type === type) &&
        matchingOrderTargets(o));
    const select = document.getElementById('order-choice');
    replaceOptions(select, matching.length ? 'Select an order' : 'No matching orders', matching.map(o => o.text));
    select.disabled = matching.length === 0;
    setPickerStatus(availableOrders.length
        ? `${matching.length} of ${availableOrders.length} available orders. Select one to submit.`
        : emptyMessage);
    updateOrderHighlights();
}

function resetOrderFilters() {
    mapOrderTargets = [];
    for (const id of ['order-unit', 'order-type', 'order-choice']) {
        const select = document.getElementById(id);
        if (select) select.value = '';
    }
}

function clearOrderSelection() {
    resetOrderFilters();
    renderOrderChoices();
}

function orderHighlightData(unit, type, selected, orders, showTargets = false) {
    const sources = new Set();
    const targets = new Set();
    const actors = new Set();
    const related = new Set();
    const addUnit = (set, kind, territory) => set.add(`${kind} ${territory}`);
    const sourceUnit = unit.split(' ');
    if (unit) {
        sources.add(sourceUnit.length === 2 ? sourceUnit[1] : sourceUnit[0]);
        if (sourceUnit.length === 2) addUnit(actors, sourceUnit[0], sourceUnit[1]);
        else {
            for (const order of orders) {
                if (order.unit === unit && order.type === 'Remove') {
                    const parts = order.text.split(' ');
                    addUnit(actors, parts[1], unit);
                }
            }
        }
    }
    if (!selected && !type && !showTargets) return { sources, targets, actors, related };

    const matches = orders.filter(o => (!unit || o.unit === unit) && (!type || o.type === type) &&
        (!selected || o.text === selected));
    for (const order of matches) {
        const parts = order.text.split(' ');
        const adjustment = parts[0] === 'Build' || parts[0] === 'Remove';
        const origin = (adjustment ? parts[2] : parts[1]).replace(/\([^)]*\)$/, '');
        sources.add(origin);
        if (!adjustment || parts[0] === 'Remove') {
            addUnit(actors, adjustment ? parts[1] : parts[0], origin);
        }
        if (adjustment) continue;
        if (parts[2] === '-') {
            targets.add(parts[3].replace(/\([^)]*\)$/, ''));
        } else if (parts[2] === 'S' || parts[2] === 'C') {
            const other = parts[4].replace(/\([^)]*\)$/, '');
            targets.add(other);
            addUnit(related, parts[3], other);
            if (parts[5] === '-' && parts[6]) targets.add(parts[6].replace(/\([^)]*\)$/, ''));
        }
    }
    return { sources, targets, actors, related };
}

function updateOrderHighlights() {
    if (!svg || !window.diplomacy.state) return;
    const unitSelect = document.getElementById('order-unit');
    const typeSelect = document.getElementById('order-type');
    const choiceSelect = document.getElementById('order-choice');
    if (!unitSelect || !typeSelect || !choiceSelect) return;
    const highlights = orderHighlightData(unitSelect.value, typeSelect.value, choiceSelect.value,
        availableOrders.filter(matchingOrderTargets), mapOrderTargets.length > 0);
    svg.querySelectorAll('.order-highlight-source, .order-highlight-target').forEach(el => {
        el.classList.remove('order-highlight-source', 'order-highlight-target');
    });
    const preview = svg.querySelector('#dislodged-preview');
    preview.replaceChildren();
    for (const abbr of highlights.targets) {
        const territory = document.getElementById(`terr-${abbr}`);
        if (territory) territory.classList.add('order-highlight-target');
    }
    for (const abbr of highlights.sources) {
        const territory = document.getElementById(`terr-${abbr}`);
        if (territory) {
            territory.classList.remove('order-highlight-target');
            territory.classList.add('order-highlight-source');
        }
    }
    const state = window.diplomacy.state;
    const powerSelect = document.getElementById('greatpower');
    const power = powerSelect ? powerSelect.value : state.player_power;
    for (const unit of state.units) {
        const abbr = unit.dislodged ? unit.dislodged_from : unit.territory;
        const key = `${unit.type} ${abbr}`;
        const actor = unit.owner === power && highlights.actors.has(key);
        const related = !unit.dislodged && highlights.related.has(key);
        if (!actor && !related) continue;
        if (unit.dislodged) {
            const territory = mapData.territories.find(t => t.abbr === abbr);
            if (!territory) continue;
            const [x, y] = unitPosition(territory, unit);
            const marker = document.createElementNS(SVG_NS, 'g');
            marker.setAttribute('class', 'unit dislodged-preview order-highlight-source');
            marker.dataset.territory = abbr;
            const circle = document.createElementNS(SVG_NS, 'circle');
            circle.setAttribute('cx', x + 17);
            circle.setAttribute('cy', y + 17);
            circle.setAttribute('r', 10);
            const player = state.players.find(p => p.name === unit.owner);
            if (!player) continue;
            circle.setAttribute('fill', player.color);
            const text = document.createElementNS(SVG_NS, 'text');
            text.setAttribute('x', x + 17);
            text.setAttribute('y', y + 17);
            text.textContent = unit.type;
            const title = document.createElementNS(SVG_NS, 'title');
            title.textContent = `Dislodged ${unit.type === 'A' ? 'army' : 'fleet'} from ${territory.name}`;
            marker.append(circle, text, title);
            preview.appendChild(marker);
        } else {
            for (const marker of svg.querySelectorAll('#units .unit')) {
                if (marker.dataset.territory === abbr && marker.dataset.owner === unit.owner &&
                    marker.dataset.type === unit.type) {
                    marker.classList.add(actor ? 'order-highlight-source' : 'order-highlight-target');
                }
            }
        }
    }
}

function initOrderPicker() {
    const unit = document.getElementById('order-unit');
    if (!unit) return;
    unit.addEventListener('change', () => { mapOrderTargets = []; renderOrderChoices(); });
    document.getElementById('order-type').addEventListener('change', () => { mapOrderTargets = []; renderOrderChoices(); });
    document.getElementById('order-choice').addEventListener('change', updateOrderHighlights);
    document.getElementById('clear-order-selection').addEventListener('click', clearOrderSelection);
}

function selectMapTerritory(abbr) {
    const unitSelect = document.getElementById('order-unit');
    if (!unitSelect || !availableOrders.length) return;
    const typeSelect = document.getElementById('order-type');
    const choiceSelect = document.getElementById('order-choice');
    const selectedUnit = unitSelect.value;
    const sourceOptions = [...unitSelect.options].filter(option =>
        option.value && option.value.split(' ').pop().replace(/\([^)]*\)$/, '') === abbr);
    const currentOrders = availableOrders.filter(order => order.unit === selectedUnit &&
        (!typeSelect.value || order.type === typeSelect.value));
    let nextTargets = [...mapOrderTargets, abbr];
    let matches = currentOrders.filter(order => {
        const targets = orderMapTargets(order);
        return nextTargets.every((target, index) => targets[index] === target);
    });
    if (!matches.length && mapOrderTargets.length && !sourceOptions.length) {
        nextTargets = [...mapOrderTargets.slice(0, -1), abbr];
        matches = currentOrders.filter(order => {
            const targets = orderMapTargets(order);
            return nextTargets.every((target, index) => targets[index] === target);
        });
    }

    if (selectedUnit && matches.length) {
        mapOrderTargets = nextTargets;
        choiceSelect.value = '';
        renderOrderChoices();
        if (matches.length === 1) {
            choiceSelect.value = matches[0].text;
            updateOrderHighlights();
            setPickerStatus(`Order selected: ${matches[0].text}. Submit to confirm.`);
        } else {
            setPickerStatus(`${matches.length} matching orders. Select an order or tap the next territory.`);
        }
        return;
    }

    if (sourceOptions.length === 1) {
        unitSelect.value = sourceOptions[0].value;
        mapOrderTargets = [];
        choiceSelect.value = '';
        if (!availableOrders.some(order => order.unit === unitSelect.value &&
            (!typeSelect.value || order.type === typeSelect.value))) typeSelect.value = '';
        renderOrderChoices();
        setPickerStatus(`Selected ${sourceOptions[0].text}. Select an order or tap a related territory.`);
    } else if (sourceOptions.length > 1) {
        setPickerStatus('Multiple units are available here. Select one from the unit dropdown.');
    } else {
        setPickerStatus('No matching order for that territory. Choose another territory or use the dropdowns.');
    }
}

function downloadGameSave(saveData) {
    const safeName = (saveData.name || 'diplomacy-game').toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '') || 'diplomacy-game';
    const game = saveData.game;
    const filename = `${safeName}-${game.year}-${game.phase.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.json`;
    const blob = new Blob([JSON.stringify(saveData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    return filename;
}

function renderSubmittedOrders(state) {
    const list = document.getElementById('order-list');
    if (!list) return;
    list.innerHTML = '';
    if (state.orders.length === 0) {
        const empty = document.createElement('li');
        empty.className = 'orders-empty';
        empty.textContent = state.orders_revealed ? 'No orders submitted.' : 'You have no orders yet.';
        list.appendChild(empty);
        return;
    }

    for (const order of state.orders) {
        const item = document.createElement('li');
        item.className = 'submitted-order';
        const text = document.createElement('span');
        text.className = 'order-text';
        text.textContent = state.orders_revealed && order.owner !== gameInfo.power
            ? `${order.owner}: ${order.text}` : order.text;
        item.appendChild(text);

        const remove = document.createElement('button');
        remove.className = 'order-delete';
        remove.type = 'button';
        remove.textContent = 'Delete';
        remove.title = 'Delete this order';
        remove.setAttribute('aria-label', `Delete order: ${order.text}`);
        remove.disabled = state.orders_revealed || gameInfo.power === 'Spectator';
        remove.addEventListener('click', async () => {
            remove.disabled = true;
            try {
                const reply = await sendForReply({
                    type: 'delete_order',
                    queue_id: order.queue_id,
                    power: gameInfo.power,
                }, 'order_delete_result');
                if (!reply.ok) {
                    document.getElementById('order-error').textContent = reply.error;
                    remove.disabled = false;
                }
            } catch (e) {
                document.getElementById('order-error').textContent = e.message;
                remove.disabled = false;
            }
        });
        item.appendChild(remove);
        list.appendChild(item);
    }
}

function handleGameMessage(msg) {
    if (msg.type === 'lobby_update') {
        // The host can change when the host leaves, and only the current host may render and resolve.
        gameInfo.host = msg.host;
        if (msg.selected_powers && gameInfo.userName in msg.selected_powers) {
            gameInfo.power = msg.selected_powers[gameInfo.userName] || '';
            sessionStorage.setItem('power', gameInfo.power);
        }
        updateGameRole();
        renderGameInfo();
        renderHostTools(msg);
    } else if (msg.type === 'game_state') {
        applyGameState(msg.state);
    } else if (['order_result', 'order_delete_result', 'draw_result', 'reveal_result', 'resolve_result', 'kick_result'].includes(msg.type)) {
        if (msg.state) applyGameState(msg.state);
        if (msg.ok && msg.save_data && gameInfo.userName === gameInfo.host) {
            gameInfo.latestSave = msg.save_data;
            const downloadButton = document.getElementById('download-save');
            if (downloadButton) downloadButton.disabled = false;
            const filename = downloadGameSave(msg.save_data);
            const message = document.getElementById('order-error');
            if (message) message.textContent = `Save download started: ${filename}`;
        }
    } else if (msg.type === 'error') {
        notify(msg.message);
    }
}

// Host tools during a game: open the game to newcomers, answer join requests, and fill vacant powers.
// Selections survive re-renders, which happen on every lobby update and game state.
const joinRequestChoices = {};

function optionList(select, values, labels = {}) {
    const previous = select.value;
    select.innerHTML = '';
    for (const value of values) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = labels[value] || value;
        select.appendChild(option);
    }
    if (values.includes(previous)) select.value = previous;
}

function renderHostTools(source) {
    const tools = document.getElementById('host-tools');
    if (!tools || !source) return;
    const players = source.players || source.lobby_players || [];
    gameInfo.lobby = {
        vacant: source.vacant_powers || [],
        accepting: Boolean(source.accepting_joins),
        requests: source.join_requests || [],
        spectators: players.filter(p => source.selected_powers?.[p] === 'Spectator'),
    };
    const { vacant, accepting, requests, spectators } = gameInfo.lobby;

    document.getElementById('toggle-joins').textContent = accepting
        ? 'Stop Accepting New Players' : 'Open Game to New Players';
    document.getElementById('vacant-powers').textContent = vacant.length
        ? `Vacant powers: ${vacant.join(', ')}` : 'No vacant powers.';

    const requestSection = document.getElementById('join-requests');
    const requestList = document.getElementById('join-request-list');
    requestSection.classList.toggle('hidden', requests.length === 0);
    requestList.innerHTML = '';
    for (const id of Object.keys(joinRequestChoices)) {
        if (!requests.some(r => r.request_id === id)) delete joinRequestChoices[id];
    }
    for (const req of requests) {
        const item = document.createElement('li');
        item.className = 'join-request';
        const label = document.createElement('span');
        label.className = 'join-request-name';
        label.textContent = `${req.user_name} wants to join`;
        const choice = document.createElement('select');
        optionList(choice, ['Spectator', ...vacant], { Spectator: 'As a spectator' });
        if (joinRequestChoices[req.request_id] && [...choice.options].some(o => o.value === joinRequestChoices[req.request_id])) {
            choice.value = joinRequestChoices[req.request_id];
        }
        choice.addEventListener('change', () => { joinRequestChoices[req.request_id] = choice.value; });
        const buttons = document.createElement('div');
        buttons.className = 'player-buttons';
        const accept = playerActionButton('Accept', 'player-action', `Let ${req.user_name} in`, button => {
            const power = choice.value;
            const payload = power === 'Spectator'
                ? { type: 'answer_join', request_id: req.request_id, decision: 'spectator' }
                : { type: 'answer_join', request_id: req.request_id, decision: 'power', power };
            sendHostAction(button, payload, 'join_answer_result');
        });
        const reject = playerActionButton('Reject', 'order-delete', `Turn ${req.user_name} away`, button => {
            sendHostAction(button, { type: 'answer_join', request_id: req.request_id, decision: 'reject' }, 'join_answer_result');
        });
        buttons.append(accept, reject);
        item.append(label, choice, buttons);
        requestList.appendChild(item);
    }

    const assignSection = document.getElementById('assign-power');
    assignSection.classList.toggle('hidden', vacant.length === 0 || spectators.length === 0);
    optionList(document.getElementById('assign-player'), spectators);
    optionList(document.getElementById('assign-power-select'), vacant);
}

function initHostTools() {
    const toggle = document.getElementById('toggle-joins');
    if (!toggle) return;
    toggle.addEventListener('click', async () => {
        const value = !gameInfo.lobby?.accepting;
        const reply = await sendHostAction(toggle, { type: 'set_accepting_joins', value }, 'accepting_joins_result');
        if (reply.ok) toggle.disabled = false;
    });
    const assign = document.getElementById('assign-power-btn');
    assign.addEventListener('click', async () => {
        const userName = document.getElementById('assign-player').value;
        const power = document.getElementById('assign-power-select').value;
        if (!userName || !power) return;
        const reply = await sendHostAction(assign, { type: 'assign_power', user_name: userName, power }, 'assign_power_result');
        if (reply.ok) assign.disabled = false;
    });
}

// Tells the server this is a deliberate exit so it can hand over the host and close the lobby right away.
function leaveLobby(socket) {
    clearSession();
    if (socket) socket.leaving = true;
    return new Promise(resolve => {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            resolve();
            return;
        }
        socket.addEventListener('close', resolve);
        setTimeout(resolve, 1500);
        socket.send(JSON.stringify({ type: 'leave' }));
    }).then(() => goTo('index.html'));
}

function joinGame(lobbyId, userName, baseInfo) {
    gameInfo.base = baseInfo;
    gameInfo.userName = userName;
    updateGameRole();
    renderGameInfo();
    gameSocket = watchLobby(lobbyId, userName, sessionStorage.getItem('secretToken') || '', handleGameMessage);
}

function sendForReply(payload, replyType) {
    return new Promise((resolve, reject) => {
        if (!gameSocket || gameSocket.readyState !== WebSocket.OPEN) {
            reject(new Error('Not connected to the game.'));
            return;
        }
        const pending = pendingReplies[replyType] || (pendingReplies[replyType] = []);
        const resolveReply = msg => {
            clearTimeout(timer);
            resolve(msg);
        };
        const timer = setTimeout(() => {
            const index = pending.indexOf(resolveReply);
            if (index !== -1) pending.splice(index, 1);
            if (pending.length === 0) delete pendingReplies[replyType];
            reject(new Error('The server did not respond.'));
        }, 10000);
        pending.push(resolveReply);
        gameSocket.send(JSON.stringify(payload));
    });
}

async function submitOrder(order) {
    const r = await sendForReply({ type: 'submit_order', order, power: gameInfo.power }, 'order_result');
    return r.ok ? 'Order submitted.' : `Order rejected: ${r.error}`;
}

async function submitDraw() {
    const r = await sendForReply({ type: 'draw', power: gameInfo.power }, 'draw_result');
    return r.ok ? 'You voted to draw.' : `Draw rejected: ${r.error}`;
}

// Host only: the first press shows everyone's orders to all players, the second resolves them.
function initResolveControl() {
    const button = document.getElementById('resolve');
    const downloadButton = document.getElementById('download-save');
    const messageEl = document.getElementById('order-error');

    if (downloadButton) {
        downloadButton.disabled = !gameInfo.latestSave;
        downloadButton.addEventListener('click', () => {
            if (!gameInfo.latestSave) return;
            const filename = downloadGameSave(gameInfo.latestSave);
            messageEl.textContent = `Save download started: ${filename}`;
        });
    }

    const send = async (type, replyType) => {
        try {
            const r = await sendForReply({ type }, replyType);
            messageEl.textContent = !r.ok ? r.error : r.save_data ? 'Game save downloaded.' : '';
        } catch (e) {
            messageEl.textContent = e.message;
        }
    };

    button.addEventListener('click', () => {
        if (gameInfo.state && gameInfo.state.orders_revealed) {
            confirmAction('Resolve Orders', 'Are you sure you want to resolve all orders?', () => send('resolve', 'resolve_result'));
        } else {
            confirmAction('Render Orders', 'Show all orders (This will block further order submissions)?', () => send('reveal_orders', 'reveal_result'));
        }
    });
}

// Wires the order selector and draw button; callbacks return the message to show.
function initOrderControls(onSubmit, onDraw) {
    const orderEl = document.getElementById('order-choice');
    const messageEl = document.getElementById('order-error');

    document.getElementById('submit-order').addEventListener('click', async () => {
        const order = orderEl.value;
        if (!order) {
            messageEl.textContent = 'Select an order.';
            return;
        }
        try {
            messageEl.textContent = await onSubmit(order);
            if (messageEl.textContent === 'Order submitted.') clearOrderSelection();
        } catch (e) {
            messageEl.textContent = e.message;
        }
    });

    document.getElementById('draw').addEventListener('click', () => {
        confirmAction('Draw Game', 'Are you sure you want to vote to draw?', async () => {
            try {
                messageEl.textContent = await onDraw();
            } catch (e) {
                messageEl.textContent = e.message;
            }
        });
    });
}

function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main');
    document.getElementById('toggleBtn').addEventListener('click', () => {
        const collapsed = sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('shifted', collapsed);
    });
    initOrderPicker();

    const gameTab = document.getElementById('game-tab');
    const helpTab = document.getElementById('help-tab');
    const gamePanel = document.getElementById('game-panel');
    const helpPanel = document.getElementById('help-panel');
    if (!gameTab || !helpTab || !gamePanel || !helpPanel) return;

    helpPanel.innerHTML = `
        <h2>How to play</h2>
        <p>Negotiate with the other powers and compete for supply centers. The first power to reach the map's winning count wins. All orders for a phase resolve at the same time.</p>
        <p>Armies move on land; fleets move through water and coastal territories. A unit can hold, move, support another unit, or convoy an army. Support adds strength; equal opposing forces can bounce. Attacks can cut support.</p>
        <h3>Movement: Spring and Fall</h3>
        <p>Select one order for each unit. A unit without an order holds. Filter the available orders by unit and type to narrow the list.</p>
        <ul>
            <li>Hold keeps a unit in its current territory.</li>
            <li>Move sends a unit to a neighboring territory or an army along a convoy route.</li>
            <li>Support strengthens another unit's hold or move.</li>
            <li>Convoy transports an army by sea. Each fleet in the route needs a matching convoy order and the army needs a matching move.</li>
        </ul>
        <p>Support must be to a territory the supporting unit can reach. Convoys use fleets at sea to move an army between coastal territories.</p>
        <h3>Retreats</h3>
        <p>A dislodged unit can retreat to a legal, unoccupied destination; a unit without a valid retreat is disbanded.</p>
        <h3>Adjustment</h3>
        <p>Build or remove units to match your supply-center count. Build only in an empty home supply center you control. The classic game starts with an adjustment for the initial builds.</p>
        <h3>Order tips</h3>
        <p>For a fleet moving, retreating, or building in a territory with multiple coasts, choose the appropriate coast when available. Available orders can still fail when resolved because all players' orders are simultaneous.</p>
        <p>In multiplayer, the host renders orders before resolving them. Players can also vote for a draw.</p>`;

    const tabs = [gameTab, helpTab];
    const panels = [gamePanel, helpPanel];
    function selectTab(index, focus = false) {
        tabs.forEach((tab, i) => {
            const selected = i === index;
            tab.setAttribute('aria-selected', String(selected));
            tab.tabIndex = selected ? 0 : -1;
            panels[i].hidden = !selected;
        });
        if (focus) tabs[index].focus();
    }
    tabs.forEach((tab, index) => {
        tab.addEventListener('click', () => selectTab(index));
        tab.addEventListener('keydown', event => {
            let next;
            if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') next = 1 - index;
            else if (event.key === 'Home') next = 0;
            else if (event.key === 'End') next = tabs.length - 1;
            else return;
            event.preventDefault();
            selectTab(next, true);
        });
    });
}

function confirmAction(title, message, callback) {
    const modal = document.getElementById('confirm-modal');

    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-message').textContent = message;

    modal.classList.remove('hidden');

    const confirmBtn = document.getElementById('modal-confirm');
    const cancelBtn = document.getElementById('modal-cancel');

    const close = () => {
        modal.classList.add('hidden');
        confirmBtn.onclick = null;
        cancelBtn.onclick = null;
    };

    cancelBtn.onclick = close;

    confirmBtn.onclick = () => {
        close();
        callback();
    };
}

function smoothPolygons(polygons) {
    const edgeEpsilon = 10;
    function isEdgePoint(p, width, height) {
        const [x, y] = p;
        return (
        x <= edgeEpsilon ||
        y <= edgeEpsilon ||
        x >= width - edgeEpsilon ||
        y >= height - edgeEpsilon
        );
    }

    for (const poly of polygons) {
        for (let x = 0; x < 2; x++) {
        const next = [];
        for (let i = 0; i < poly.length; i++) {
            const p0 = poly[i];
            const p1 = poly[(i + 1) % poly.length];
            if (isEdgePoint(p0, mapData.width, mapData.height) || isEdgePoint(p1, mapData.width, mapData.height)) {
            next.push(p0);
            continue;
            }
            const q = [0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1]];
            const r = [0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1]];
            next.push(q, r);
        }
        poly.splice(0, poly.length, ...next);
        }
    }
    return polygons;
}

function buildMap() {
    const container = document.getElementById('map');
    container.innerHTML = '';
    svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${mapData.width} ${mapData.height}`);
    if (document.getElementById('order-unit')) {
        svg.addEventListener('click', event => {
            const unit = event.target.closest('.unit');
            const territory = event.target.closest('.territory');
            if (unit && unit.dataset.territory) selectMapTerritory(unit.dataset.territory);
            else if (territory) selectMapTerritory(territory.id.slice(5));
        });
    }
    const bg = document.createElementNS(SVG_NS, 'rect');
    bg.setAttribute('width', mapData.width);
    bg.setAttribute('height', mapData.height);
    bg.setAttribute('fill', 'black');
    svg.appendChild(bg);

    for (const t of mapData.territories) {
        const polygons = smoothPolygons(t.polygons.map(poly => poly.map(i => mapData.vertices[i])));
        const d = polygons
        .map(poly => 'M' + poly.map(v => v.join(',')).join('L') + 'Z')
        .join(' ');
        const path = document.createElementNS(SVG_NS, 'path');
        path.setAttribute('d', d);
        path.setAttribute('class', 'territory');
        path.setAttribute('id', 'terr-' + t.abbr);
        path.setAttribute('fill-rule', 'evenodd');
        const title = document.createElementNS(SVG_NS, 'title');
        title.textContent = `${t.name} (${t.abbr})`;
        path.appendChild(title);
        svg.appendChild(path);
    }
    for (const t of mapData.territories) {
        const [x, y] = t.label_pos;
        const label = document.createElementNS(SVG_NS, 'text');
        label.setAttribute('class', 'label');
        label.setAttribute('x', x);
        label.setAttribute('y', y);
        label.textContent = t.abbr;
        svg.appendChild(label);
        if (t.land && t.supply_center) {
            const [sx, sy] = t.supply_center_pos;
            const c = document.createElementNS(SVG_NS, 'circle');
            c.setAttribute('cx', sx);
            c.setAttribute('cy', sy);
            c.setAttribute('r', 4);
            c.setAttribute('fill', '#f5bf1b');
            c.setAttribute('stroke', '#000');
            c.setAttribute('stroke-width', 1);
            c.setAttribute('pointer-events', 'none');
            svg.appendChild(c);
        }
    }
    const unitLayer = document.createElementNS(SVG_NS, 'g');
    unitLayer.setAttribute('id', 'units');
    svg.appendChild(unitLayer);
    const previewLayer = document.createElementNS(SVG_NS, 'g');
    previewLayer.setAttribute('id', 'dislodged-preview');
    svg.appendChild(previewLayer);
    container.appendChild(svg);
}

async function loadMap(mapId = 'classic_map') {
    mapData = await (await fetch(`data/${encodeURIComponent(mapId)}.json`)).json();
    buildMap();
}

async function refreshMap(mapId) {
    await loadMap(mapId);
    for (const t of mapData.territories) {
        document.getElementById('terr-' + t.abbr).setAttribute('fill', t.land ? '#DDD' : mapData.water_color);
    }
}

function unitPosition(t, unit) {
    if (!t.land) return t.fleet_pos;
    if (unit.type === 'A') return t.army_pos;
    const coast = unit.coast;
    if (coast == 'nc')
        return t.coast_pos;
    else if (coast == 'sc')
        return t.south_coast_pos;
    return unit.type === 'A' ? t.army_pos : t.coast_pos;
}

function render(state) {
    const colors = Object.fromEntries(state.players.map(p => [p.name, p.color]));
    const byAbbr = Object.fromEntries(mapData.territories.map(t => [t.abbr, t]));
    for (const t of state.territories) {
        const el = document.getElementById('terr-' + t.abbr);
        const def = byAbbr[t.abbr];
        el.setAttribute('fill', def.land ? (t.owner ? colors[t.owner] : '#DDD') : mapData.water_color);
    }
    const layer = document.getElementById('units');
    layer.innerHTML = '';
    for (const u of state.units) {
        if (!u.territory || u.dislodged) continue;
        const [x, y] = unitPosition(byAbbr[u.territory], u);
        const g = document.createElementNS(SVG_NS, 'g');
        g.setAttribute('class', 'unit');
        g.dataset.territory = u.territory;
        g.dataset.owner = u.owner;
        g.dataset.type = u.type;
        const c = document.createElementNS(SVG_NS, 'circle');
        c.setAttribute('cx', x);
        c.setAttribute('cy', y);
        c.setAttribute('r', 10);
        c.setAttribute('fill', colors[u.owner]);
        const txt = document.createElementNS(SVG_NS, 'text');
        txt.setAttribute('x', x);
        txt.setAttribute('y', y);
        txt.textContent = u.type;
        g.append(c, txt);
        layer.appendChild(g);
    }

    // Remove old orders
    const oldOrders = document.querySelectorAll('line, polygon');
    oldOrders.forEach(el => el.remove());

    for (const o of state.orders) {
        if (o.type == 'Advance') {
            const from = byAbbr[o.territory];
            const to = byAbbr[o.dest_territory];
            const unit = state.units.find(u => u.territory === o.territory && !u.dislodged);
            if (unit) {
                const [fromX, fromY] = unitPosition(from, unit);
                const [toX, toY] = unitPosition(to, {'type': unit.type, 'coast': o.dest_coast});
                drawArrow(fromX, fromY, toX, toY, '#F00');
            }
        } else if (o.type == 'Support') {
            const from = byAbbr[o.territory];
            let [toX, toY] = [0, 0];
            // The supported order may belong to another power, so the server inlines what is needed.
            let supported = o.supported_order_id != null ? state.orders[o.supported_order_id] : null;
            if (!supported && o.supported_territory) {
                supported = {type: o.supported_type, territory: o.supported_territory, dest_territory: o.supported_dest, dest_coast: o.supported_coast};
            }
            if (supported) {
                if (supported && supported.type == 'Advance') {
                    const adv_from = byAbbr[supported.territory];
                    const adv_to = byAbbr[supported.dest_territory];

                    const unit = state.units.find(u => u.territory === supported.territory && !u.dislodged);
                    if (unit) {
                        const [adv_fromX, adv_fromY] = unitPosition(adv_from, unit);
                        const [adv_toX, adv_toY] = unitPosition(adv_to, {'type': unit.type, 'coast': supported.dest_coast});
                        // to points to halfway between from and to for visual clarity
                        toX = (adv_fromX + adv_toX) / 2;
                        toY = (adv_fromY + adv_toY) / 2;
                    }
                } else if (supported) {
                    const loc = byAbbr[supported.territory];
                    const unit = state.units.find(u => u.territory === supported.territory && !u.dislodged);
                    if (unit) {
                        [toX, toY] = unitPosition(loc, unit);
                    }
                }

                if (supported) {
                    const unit = state.units.find(u => u.territory === o.territory && !u.dislodged);
                    if (unit) {
                        const [fromX, fromY] = unitPosition(from, unit);
                        drawArrow(fromX, fromY, toX, toY, '#0F0');
                    }
                }
            }
        }
    }

    setStatus(`${state.phase} phase, ${state.year}`);
    const popup = document.getElementById('outcome-popup');
    if (popup && (state.winner || state.draw)) {
        popup.classList.remove('hidden');
        document.getElementById('outcome-title').textContent = state.winner ? 'Victory!' : 'Draw!';
        document.getElementById('outcome-message').textContent = state.winner
        ? `${state.winner} controls 18 supply centers and wins the game!`
        : 'All players chose to draw. The game ends in a draw.';
    }
    window.diplomacy.state = state;
    updateOrderHighlights();
}

function drawArrow(fromX, fromY, toX, toY, color) {
    const line = document.createElementNS(SVG_NS, 'line');
    line.setAttribute('x1', fromX);
    line.setAttribute('y1', fromY);
    line.setAttribute('x2', toX);
    line.setAttribute('y2', toY);
    line.setAttribute('stroke', color);
    line.setAttribute('stroke-width', '2');
    svg.appendChild(line);
    const arrow = document.createElementNS(SVG_NS, 'polygon');
    const arrowSize = 10;
    const angle = Math.atan2(toY - fromY, toX - fromX);
    const arrowPoints = [
        [toX, toY],
        [toX - arrowSize * Math.cos(angle - Math.PI / 6), toY - arrowSize * Math.sin(angle - Math.PI / 6)],
        [toX - arrowSize * Math.cos(angle + Math.PI / 6), toY - arrowSize * Math.sin(angle + Math.PI / 6)]
    ].map(p => p.join(',')).join(' ');
    arrow.setAttribute('points', arrowPoints);
    arrow.setAttribute('fill', color);
    svg.appendChild(arrow);
}
