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

        const label = document.createElement('span');
        label.className = 'lobby-name';
        label.textContent = name;
        const players = document.createElement('span');
        players.className = 'lobby-players';
        players.textContent = `${count} ${count === 1 ? 'player' : 'players'}`;
        item.append(label, players);

        item.addEventListener('click', () => {
            selectedLobby = name;
            selectedLobbyID = lobbies[name].id;
            for (const el of lobbyListEl.children) el.classList.remove('selected');
            item.classList.add('selected');
        });
        lobbyListEl.appendChild(item);
    }
}

async function loadLobbies() {
    messageEl.textContent = '';
    try {
        renderLobbies(await request('GET', '/lobbies'));
    } catch (e) {
        console.error(e);
        messageEl.textContent = 'Could not load lobbies.';
    }
}

document.getElementById('lobby-refresh').addEventListener('click', loadLobbies);

document.getElementById('join-submit').addEventListener('click', async () => {
    const name = document.getElementById('join-name').value.trim();
    if (!name) {
        messageEl.textContent = 'Enter your name.';
        return;
    }
    if (!selectedLobby) {
        messageEl.textContent = 'Select a lobby.';
        return;
    }
    debugger;
    const r = await request('POST', `/join_lobby/${selectedLobbyID}`, {'user_name': name});
    if (!r.ok) {
        messageEl.textContent = r.message;
        return;
    }
    sessionStorage.setItem('diplomacyGameCode', selectedLobby);
    sessionStorage.setItem('diplomacyGameID', selectedLobbyID);
    sessionStorage.setItem('diplomacyPlayerName', name);
    location.href = 'lobby.html';
});

document.getElementById('join-back').addEventListener('click', () => { location.href = 'index.html'; });

loadLobbies();