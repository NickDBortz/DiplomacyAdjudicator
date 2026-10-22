// Server-side joining is not implemented yet; this only picks a lobby and collects the player's name.
let selectedLobby = null;
let selectedLobbyID = null;

const lobbyListEl = document.getElementById('lobby-list');
const messageEl = document.getElementById('menu-message');

function renderLobbies(lobbies) {
    lobbyListEl.innerHTML = '';
    const names = Object.keys(lobbies);
    if (!names.includes(selectedLobby)) {
        selectedLobby = null;
        selectedLobbyID = null;
    }

    if (names.length === 0) {
        const empty = document.createElement('li');
        empty.className = 'lobby-empty';
        empty.textContent = 'No lobbies available.';
        lobbyListEl.appendChild(empty);
        return;
    }

    for (const name of names) {
        const count = lobbies[name].Players;
        const item = document.createElement('li');
        item.className = 'lobby-item' + (name === selectedLobby ? ' selected' : '');

        const header = document.createElement('div');
        header.className = 'lobby-header';

        const label = document.createElement('span');
        label.className = 'lobby-name';
        label.textContent = name;

        header.appendChild(label);

        if (lobbies[name].needs_password) {
            const lock = document.createElement('span');
            lock.className = 'lobby-lock';
            lock.title = 'Password required';
            lock.setAttribute('aria-label', 'Password required');
            lock.innerHTML = '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="currentColor" aria-hidden="true">'
                + '<path d="M12 1a5 5 0 0 0-5 5v4H6a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-9a2 2 0 0 0-2-2h-1V6a5 5 0 0 0-5-5zm-3 9V6a3 3 0 0 1 6 0v4H9z"/>'
                + '</svg>';
            header.appendChild(lock);
        }

        const players = document.createElement('span');
        players.className = 'lobby-players';
        players.textContent = `${count} ${count === 1 ? 'player' : 'players'}`;
        if (lobbies[name].in_progress) {
            const vacant = lobbies[name].vacant_powers.length;
            const tag = document.createElement('span');
            tag.className = 'lobby-tag';
            tag.textContent = 'In progress';
            header.appendChild(tag);
            players.textContent += vacant ? ` · ${vacant} vacant ${vacant === 1 ? 'power' : 'powers'}` : ' · spectators only';
        }

        item.append(header, players);

        item.addEventListener('click', () => {
            selectedLobby = name;
            selectedLobbyID = lobbies[name].id;
            needsPassword = lobbies[name].needs_password;
            if (needsPassword)
                document.getElementById('lobby-password').disabled = false;
            else
                document.getElementById('lobby-password').disabled = true;
            for (const el of lobbyListEl.children) el.classList.remove('selected');
            item.classList.add('selected');
        });
        lobbyListEl.appendChild(item);
    }
}

async function loadLobbies() {
    messageEl.textContent = '';
    try {
        renderLobbies(await request('GET', '/lobbies', null, true));
    } catch (e) {
        console.error(e);
        messageEl.textContent = 'Could not load lobbies.';
    }
}

document.getElementById('lobby-refresh').addEventListener('click', loadLobbies);

// Joining a game that is already running needs the host's approval: wait on the request socket for the answer.
let joinWaiter = null;

function waitForApproval(lobbyId, lobbyName, request) {
    const submit = document.getElementById('join-submit');
    submit.disabled = true;
    messageEl.textContent = 'Waiting for the host to let you in...';
    const url = `${API_BASE.replace(/^http/, 'ws')}/ws/lobbies/${encodeURIComponent(lobbyId)}/requests/${encodeURIComponent(request.request_id)}`;
    const ws = new WebSocket(url);
    joinWaiter = ws;
    let ping;
    let answer = null;
    ws.onopen = () => { ws.send(request.request_token); ping = setInterval(() => ws.send('ping'), 25000); };
    ws.onmessage = e => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'join_accepted') {
            answer = msg;
            rememberSeat(msg.lobby_id, msg.lobby_name, msg.user_name, msg.secret_token);
            sessionStorage.setItem('power', msg.power);
            sessionStorage.setItem('diplomacyMap', msg.map);
            location.href = 'multiplayer-client.html';
        } else if (msg.type === 'join_rejected') {
            answer = msg;
        }
    };
    ws.onclose = e => {
        clearInterval(ping);
        joinWaiter = null;
        if (answer?.type === 'join_accepted') return;
        messageEl.textContent = answer?.message || LOBBY_CLOSE_MESSAGES[e.code] || 'Lost connection while waiting for the host.';
        submit.disabled = false;
        loadLobbies();
    };
}

document.getElementById('join-submit').addEventListener('click', async () => {
    const name = document.getElementById('join-name').value.trim();
    let password = document.getElementById('lobby-password').value.trim();
    if (!name) {
        messageEl.textContent = 'Enter your name.';
        return;
    }
    if (!selectedLobby) {
        messageEl.textContent = 'Select a lobby.';
        return;
    }
    const r = await request('POST', `/join_lobby/${selectedLobbyID}`, {'user_name': name, 'lobby_password': password}, true);
    if (!r.ok) {
        messageEl.textContent = r.message;
        return;
    }
    if (r.pending) {
        waitForApproval(selectedLobbyID, selectedLobby, r);
        return;
    }
    rememberSeat(selectedLobbyID, selectedLobby, name, r.secret_token);
    location.href = 'lobby.html';
});

document.getElementById('join-back').addEventListener('click', () => {
    if (joinWaiter) joinWaiter.close();
    location.href = 'index.html';
});

loadLobbies();