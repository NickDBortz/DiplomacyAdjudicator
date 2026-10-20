const SVG_NS = 'http://www.w3.org/2000/svg';

// Backend base URL; override with ?api=<url> or localStorage 'diplomacyApi'.
const API_BASE = (new URLSearchParams(location.search).get('api')
    || localStorage.getItem('diplomacyApi')
    || (['localhost', '127.0.0.1'].includes(location.hostname) ? 'http://localhost:8001' : 'https://YOUR-SERVICE.onrender.com')
).replace(/\/$/, '');

let mapData, svg;
window.diplomacy = window.diplomacy || { state: null };

function setStatus(text) {
    document.getElementById('status').textContent = text;
}

async function request(method, path, body) {
    const res = await fetch(API_BASE + path, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`${method} ${path} failed: ${res.status} ${await res.text()}`);
    return res.json();
}

function goTo(page) {
    location.href = page;
}

// Opens the lobby socket; the server pushes lobby_update on joins, leaves and settings changes, and game_started on start.
function connectLobby(lobbyId, userName, onMessage, onClose) {
    const url = `${API_BASE.replace(/^http/, 'ws')}/ws/lobbies/${encodeURIComponent(lobbyId)}?user_name=${encodeURIComponent(userName)}`;
    const ws = new WebSocket(url);
    let ping;
    ws.onopen = () => { ping = setInterval(() => ws.send('ping'), 25000); };
    ws.onmessage = e => onMessage(JSON.parse(e.data));
    ws.onclose = e => { clearInterval(ping); onClose(e.code); };
    return ws;
}

const LOBBY_CLOSE_MESSAGES = {
    4404: 'This lobby no longer exists.',
    4403: 'You are not a member of this lobby.',
    4409: 'You are already connected to this lobby.',
};

function renderPlayerList(players, selfName, powers = {}) {
    const colors = Object.fromEntries((mapData?.players ?? []).map(p => [p.name, p.color]));
    const list = document.getElementById('player-list');
    list.innerHTML = '';
    for (const name of players) {
        const item = document.createElement('li');
        item.className = 'player-item';
        const color = colors[powers[name]];
        if (color) item.style.borderLeftColor = color;
        const label = document.createElement('span');
        label.textContent = name === selfName ? `${name} (you)` : name;
        if (color) label.style.color = color;
        const power = document.createElement('span');
        power.className = 'player-power';
        power.textContent = powers[name] || 'No power selected';
        item.append(label, power);
        list.appendChild(item);
    }
}

// Shared by the lobby and game pages; onMessage sees every server message first.
function watchLobby(lobbyId, userName, onMessage = () => {}) {
    return connectLobby(lobbyId, userName, msg => {
        onMessage(msg);
        if (msg.type !== 'lobby_update') return;
        renderPlayerList(msg.players, userName, msg.selected_powers);
        if (msg.user_name !== userName && (msg.event === 'joined' || msg.event === 'left')) {
            setStatus(`${msg.user_name} ${msg.event === 'joined' ? 'joined' : 'left'} the lobby`);
        }
    }, code => {
        renderPlayerList([], userName);
        setStatus(LOBBY_CLOSE_MESSAGES[code] || 'Connection to the lobby was lost.');
    });
}

// In-game state: the lobby socket doubles as the game socket once the game has started.
let gameSocket = null;
const pendingReplies = {};
const gameInfo = { base: '', host: '', userName: '', power: sessionStorage.getItem('power') || '', state: null };

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
        if (state.orders.length > 0) {
            lines.push('', state.orders_revealed ? 'All orders:' : 'Your orders:', ...state.orders.map(o => `- ${o.text}`));
        }
        if (state.draw_votes && state.draw_votes.length > 0) {
            lines.push('', 'Draw votes:', ...state.draw_votes.map(v => `- ${v}`));
        }
    }
    document.getElementById('info').textContent = lines.join('\n');
}

// The server sends every unit and territory, plus this player's orders (everyone's once revealed).
function applyGameState(state) {
    render(state);
    gameInfo.state = state;
    const resolveBtn = document.getElementById('resolve');
    if (resolveBtn) resolveBtn.textContent = state.orders_revealed ? 'Resolve Orders' : 'Render Orders';
    renderGameInfo();
}

function handleGameMessage(msg) {
    if (msg.type === 'lobby_update') {
        // The host can change when the host leaves, and only the current host may render and resolve.
        gameInfo.host = msg.host;
        const resolveBtn = document.getElementById('resolve');
        if (resolveBtn) resolveBtn.classList.toggle('hidden', msg.host !== gameInfo.userName);
        renderGameInfo();
    } else if (msg.type === 'game_state') {
        applyGameState(msg.state);
    } else if (['order_result', 'draw_result', 'reveal_result', 'resolve_result'].includes(msg.type)) {
        if (msg.state) applyGameState(msg.state);
        const done = pendingReplies[msg.type];
        if (done) {
            delete pendingReplies[msg.type];
            done(msg);
        }
    } else if (msg.type === 'error') {
        setStatus(msg.message);
    }
}

// Tells the server this is a deliberate exit so it can hand over the host and close the lobby right away.
function leaveLobby(socket) {
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
    renderGameInfo();
    gameSocket = watchLobby(lobbyId, userName, handleGameMessage);
}

function sendForReply(payload, replyType) {
    return new Promise((resolve, reject) => {
        if (!gameSocket || gameSocket.readyState !== WebSocket.OPEN) {
            reject(new Error('Not connected to the game.'));
            return;
        }
        const timer = setTimeout(() => {
            delete pendingReplies[replyType];
            reject(new Error('The server did not respond.'));
        }, 10000);
        pendingReplies[replyType] = msg => {
            clearTimeout(timer);
            resolve(msg);
        };
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
    const messageEl = document.getElementById('order-error');

    const send = async (type, replyType) => {
        try {
            const r = await sendForReply({ type }, replyType);
            messageEl.textContent = r.ok ? '' : r.error;
        } catch (e) {
            messageEl.textContent = e.message;
        }
    };

    button.addEventListener('click', () => {
        if (gameInfo.state && gameInfo.state.orders_revealed) {
            confirmAction('Resolve Orders', 'Are you sure you want to resolve all orders?', () => send('resolve', 'resolve_result'));
        } else {
            send('reveal_orders', 'reveal_result');
        }
    });
}

// Wires the order box and draw button; each callback returns the message to show (or a promise of it).
function initOrderControls(onSubmit, onDraw) {
    const orderEl = document.getElementById('order');
    const messageEl = document.getElementById('order-error');

    document.getElementById('submit-order').addEventListener('click', async () => {
        const order = orderEl.value.trim();
        if (!order) {
            messageEl.textContent = 'Enter an order.';
            return;
        }
        try {
            messageEl.textContent = await onSubmit(order);
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
        path.addEventListener('click', () => console.log(`${t.name} (${t.abbr})`));
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
        c.setAttribute('fill', '#000');
        svg.appendChild(c);
        }
    }
    const unitLayer = document.createElementNS(SVG_NS, 'g');
    unitLayer.setAttribute('id', 'units');
    svg.appendChild(unitLayer);
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
        el.setAttribute('fill', t.owner ? colors[t.owner] : (def.land ? '#DDD' : mapData.water_color));
    }
    const layer = document.getElementById('units');
    layer.innerHTML = '';
    for (const u of state.units) {
        if (!u.territory || u.dislodged) continue;
        const [x, y] = unitPosition(byAbbr[u.territory], u);
        const g = document.createElementNS(SVG_NS, 'g');
        g.setAttribute('class', 'unit');
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
