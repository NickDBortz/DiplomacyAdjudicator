const playerName = sessionStorage.getItem('diplomacyPlayerName');
const lobbyId = sessionStorage.getItem('diplomacyGameID');
const lobbyName = sessionStorage.getItem('diplomacyGameName') || sessionStorage.getItem('diplomacyGameCode');

const powerSelect = document.getElementById('power-select');
const mapSelect = document.getElementById('map-select');
const startBtn = document.getElementById('start-game');
const waitEl = document.getElementById('lobby-wait');

let ws;
let currentMap = null;
let lastSnapshot = null;
let powerRefreshSeq = 0;

// Options are your own pick plus every power nobody has taken.
async function refreshPowers(snapshot) {
    const seq = ++powerRefreshSeq;
    const own = snapshot.selected_powers[playerName] || '';
    const available = await request('GET', `/lobbies/${encodeURIComponent(lobbyId)}/powers`);
    if (seq !== powerRefreshSeq) return;

    powerSelect.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Select a power';
    powerSelect.appendChild(placeholder);
    for (const power of [...new Set([own, ...available])].filter(Boolean).sort()) {
        const option = document.createElement('option');
        option.value = power;
        option.textContent = power === 'Spectator' ? 'Spectator (no Great Power)' : power;
        powerSelect.appendChild(option);
    }
    if (!own) {
        const spectator = document.createElement('option');
        spectator.value = 'Spectator';
        spectator.textContent = 'Spectator (no Great Power)';
        powerSelect.appendChild(spectator);
    }
    powerSelect.value = own;
}

async function showPreview(mapId) {
    if (mapId === currentMap) return;
    currentMap = mapId;
    await loadMap(mapId);
    for (const t of mapData.territories) {
        document.getElementById('terr-' + t.abbr).setAttribute('fill', t.land ? '#DDD' : mapData.water_color);
    }
    // Power colors come from the map, so redraw the list once it has loaded.
    if (lastSnapshot) renderPlayerList(lastSnapshot.players, playerName, lastSnapshot.selected_powers);
}

function applySnapshot(snapshot) {
    lastSnapshot = snapshot;
    const isHost = snapshot.host === playerName;
    mapSelect.disabled = !isHost;
    startBtn.classList.toggle('hidden', !isHost);
    const allReady = snapshot.players.every(p => snapshot.selected_powers[p]);
    const hasGreatPower = snapshot.players.some(p => snapshot.selected_powers[p] !== 'Spectator');
    startBtn.disabled = !allReady || !hasGreatPower;
    startBtn.title = !allReady
        ? 'Every player must select a Great Power or Spectator first'
        : !hasGreatPower ? 'At least one player must select a Great Power' : '';
    waitEl.classList.toggle('hidden', isHost);
    document.getElementById('info').textContent = `Lobby: ${lobbyName}\nHost: ${snapshot.host}`;
    mapSelect.value = snapshot.settings.map;
    showPreview(snapshot.settings.map).catch(e => { setStatus('Error: ' + e); console.error(e); });
}

function enterGame(snapshot) {
    sessionStorage.setItem('diplomacyMap', snapshot.settings.map);
    sessionStorage.setItem('diplomacyGameName', lobbyName);
    sessionStorage.setItem('diplomacyGameCode', lobbyName);
    sessionStorage.setItem('power', powerSelect.value);
    goTo(snapshot.host === playerName ? 'multiplayer-host.html' : 'multiplayer-client.html');
}

powerSelect.addEventListener('change', () => {
    ws.send(JSON.stringify({ type: 'set_power', settings: { power: powerSelect.value } }));
});

mapSelect.addEventListener('change', () => {
    ws.send(JSON.stringify({ type: 'set_map', settings: { map: mapSelect.value } }));
});

startBtn.addEventListener('click', () => {
    ws.send(JSON.stringify({ type: 'start_game' }));
});

document.getElementById('leave-game').addEventListener('click', () => {
    confirmAction('Leave Lobby', 'Leave this lobby and return to the main menu?', () => leaveLobby(ws));
});

async function init() {
    if (!playerName || !lobbyId || !lobbyName) {
        goTo('index.html');
        return;
    }
    initSidebar();
    setStatus('Connecting to lobby...');

    for (const m of await request('GET', '/maps')) {
        const option = document.createElement('option');
        option.value = m.id;
        option.textContent = m.name;
        mapSelect.appendChild(option);
    }

    ws = watchLobby(lobbyId, playerName, msg => {
        if (msg.type === 'game_started') {
            enterGame(msg);
        } else if (msg.type === 'error') {
            setStatus(msg.message);
        } else if (msg.type === 'lobby_update') {
            applySnapshot(msg);
            refreshPowers(msg).catch(e => console.error(e));
            if (msg.event === 'map_change' && msg.user_name !== playerName) {
                setStatus(`${msg.user_name} changed the map`);
            } else if (msg.event === 'power_change' && msg.user_name !== playerName) {
                setStatus(`${msg.user_name} picked ${msg.power || 'no power'}`);
            }
        }
    });
}

init().catch(e => { setStatus('Error: ' + e); console.error(e); });
