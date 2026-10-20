const playerName = sessionStorage.getItem('diplomacyPlayerName');
const lobbyId = sessionStorage.getItem('diplomacyGameID');
const lobbyName = sessionStorage.getItem('diplomacyGameName') || sessionStorage.getItem('diplomacyGameCode');

const mapSelect = document.getElementById('map-select');
const startBtn = document.getElementById('start-game');
const waitEl = document.getElementById('lobby-wait');

let ws;
let currentMap = null;

async function showPreview(mapId) {
    if (mapId === currentMap) return;
    currentMap = mapId;
    await loadMap(mapId);
    for (const t of mapData.territories) {
        document.getElementById('terr-' + t.abbr).setAttribute('fill', t.land ? '#DDD' : mapData.water_color);
    }
}

function applySnapshot(snapshot) {
    const isHost = snapshot.host === playerName;
    mapSelect.disabled = !isHost;
    startBtn.classList.toggle('hidden', !isHost);
    waitEl.classList.toggle('hidden', isHost);
    document.getElementById('info').textContent = `Lobby: ${lobbyName}\nHost: ${snapshot.host}`;
    mapSelect.value = snapshot.settings.map;
    showPreview(snapshot.settings.map).catch(e => { setStatus('Error: ' + e); console.error(e); });
}

function enterGame(snapshot) {
    sessionStorage.setItem('diplomacyMap', snapshot.settings.map);
    sessionStorage.setItem('diplomacyGameName', lobbyName);
    sessionStorage.setItem('diplomacyGameCode', lobbyName);
    goTo(snapshot.host === playerName ? 'multiplayer-host.html' : 'multiplayer-client.html');
}

mapSelect.addEventListener('change', () => {
    ws.send(JSON.stringify({ type: 'set_settings', settings: { map: mapSelect.value } }));
});

startBtn.addEventListener('click', () => {
    ws.send(JSON.stringify({ type: 'start_game' }));
});

document.getElementById('leave-game').addEventListener('click', () => {
    confirmAction('Leave Lobby', 'Leave this lobby and return to the main menu?', () => goTo('index.html'));
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
        } else if (msg.type === 'lobby_update') {
            applySnapshot(msg);
            if (msg.event === 'settings' && msg.user_name !== playerName) {
                setStatus(`${msg.user_name} changed the map`);
            }
        }
    });
}

init().catch(e => { setStatus('Error: ' + e); console.error(e); });
