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
    sessionStorage.setItem('diplomacyGameCode', selectedLobby);
    sessionStorage.setItem('diplomacyGameID', selectedLobbyID);
    sessionStorage.setItem('diplomacyPlayerName', name);
    sessionStorage.setItem('secretToken', r.secret_token);
    location.href = 'lobby.html';
});

document.getElementById('join-back').addEventListener('click', () => { location.href = 'index.html'; });

loadLobbies();