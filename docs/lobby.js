const playerName = sessionStorage.getItem('diplomacyPlayerName');
const lobbyId = sessionStorage.getItem('diplomacyGameID');
const lobbyName = sessionStorage.getItem('diplomacyGameName') || sessionStorage.getItem('diplomacyGameCode');
const secretToken = sessionStorage.getItem('secretToken');

const powerSelect = document.getElementById('power-select');
const mapSelect = document.getElementById('map-select');
const ruleVariantSelect = document.getElementById('rule-variant-select');
const rulesetControls = document.getElementById('ruleset-controls');
const startBtn = document.getElementById('start-game');
const waitEl = document.getElementById('lobby-wait');
const savedGameFile = document.getElementById('saved-game-file');
const loadSavedGameBtn = document.getElementById('load-saved-game');
const savedGameStatus = document.getElementById('saved-game-status');

let ws;
let currentMap = null;
let lastSnapshot = null;
let powerRefreshSeq = 0;
playerListKickEnabled = true;

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
    if (lastSnapshot) renderPlayerList(lastSnapshot.players, playerName, lastSnapshot.selected_powers, lastSnapshot.connected_players);
}

function updateRulesetSelection(ruleset) {
    const selectedRuleset = ruleset || 'normal';
    for (const radio of rulesetControls.querySelectorAll('input[name="ruleset"]')) {
        radio.checked = radio.value === selectedRuleset;
        radio.closest('.ruleset-option').classList.toggle('selected', radio.checked);
    }
}

function updateVariantSelection(variant) {
    ruleVariantSelect.value = variant ? variant : 'standard';
}

function applySnapshot(snapshot) {
    lastSnapshot = snapshot;
    gameInfo.host = snapshot.host;
    const isHost = snapshot.host === playerName;
    mapSelect.disabled = !isHost;
    ruleVariantSelect.disabled = !isHost;
    rulesetControls.disabled = !isHost || snapshot.started;
    powerSelect.disabled = Boolean(snapshot.prepared_save);
    updateRulesetSelection(snapshot.ruleset);
    updateVariantSelection(snapshot.variant);
    startBtn.classList.toggle('hidden', !isHost);
    document.getElementById('host-load-controls').classList.toggle('hidden', !isHost);
    const allReady = snapshot.players.every(p => snapshot.selected_powers[p]);
    const hasGreatPower = snapshot.players.some(p => snapshot.selected_powers[p] !== 'Spectator');
    startBtn.disabled = !allReady || !hasGreatPower;
    startBtn.title = !allReady
        ? 'Every player must select a Great Power or Spectator first'
        : !hasGreatPower ? 'At least one player must select a Great Power' : '';
    waitEl.classList.toggle('hidden', isHost);
    document.getElementById('info').textContent = `Lobby: ${lobbyName}\nHost: ${snapshot.host}`;
    if (snapshot.prepared_save) {
        savedGameStatus.textContent = `${snapshot.prepared_save.name} loaded: ${snapshot.prepared_save.phase} ${snapshot.prepared_save.year}. Click Start Game when ready.`;
    } else {
        savedGameStatus.textContent = 'Choose a save file downloaded by the host.';
    }
    mapSelect.value = snapshot.settings.map;
    showPreview(snapshot.settings.map).catch(e => { setStatus('Error: ' + e); console.error(e); });
}

function enterGame(snapshot) {
    sessionStorage.setItem('diplomacyMap', snapshot.settings.map);
    sessionStorage.setItem('diplomacyVariant', snapshot.settings.variant ? snapshot.settings.variant : 'standard');
    sessionStorage.setItem('diplomacyGameName', lobbyName);
    sessionStorage.setItem('diplomacyGameCode', lobbyName);
    sessionStorage.setItem('power', snapshot.selected_powers?.[playerName] ?? powerSelect.value);
    goTo(snapshot.host === playerName ? 'multiplayer-host.html' : 'multiplayer-client.html');
}

powerSelect.addEventListener('change', () => {
    ws.send(JSON.stringify({ type: 'set_power', settings: { power: powerSelect.value } }));
});

mapSelect.addEventListener('change', () => {
    ws.send(JSON.stringify({ type: 'set_map', settings: { map: mapSelect.value } }));
});

ruleVariantSelect.addEventListener('change', () => {
    ws.send(JSON.stringify({ type: 'set_variant', settings: { variant: ruleVariantSelect.value } }));
});

rulesetControls.addEventListener('change', event => {
    if (event.target.name === 'ruleset') {
        ws.send(JSON.stringify({ type: 'set_ruleset', ruleset: event.target.value }));
    }
});

function startGame() {
    const selectedRuleset = rulesetControls.querySelector('input[name="ruleset"]:checked');
    const variant = ruleVariantSelect.value;
    ws.send(JSON.stringify({
        type: 'start_game',
        ruleset: selectedRuleset ? selectedRuleset.value : 'normal',
        variant: variant
    }));
}

startBtn.addEventListener('click', () => {
    confirmAction('Start Game', 'Start the game? Ensure all players have selected the correct Great Power.', startGame);
});

loadSavedGameBtn.addEventListener('click', async () => {
    const file = savedGameFile.files[0];
    if (!file) {
        savedGameStatus.textContent = 'Choose a save file first.';
        return;
    }
    if (file.size > 2_000_000) {
        savedGameStatus.textContent = 'Save file is too large.';
        return;
    }
    try {
        const saveData = JSON.parse(await file.text());
        if (saveData.format !== 'diplomacy-game-save' || saveData.version !== 1) {
            throw new Error('Unsupported save file.');
        }
        savedGameStatus.textContent = 'Loading saved game...';
        ws.send(JSON.stringify({ type: 'load_saved_game', save_data: saveData }));
    } catch (e) {
        savedGameStatus.textContent = e.message || 'Could not read that save file.';
    }
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

    for (const v of await request('GET', `/maps/${encodeURIComponent(mapSelect.value)}/variants`)) {
        const option = document.createElement('option');
        option.value = v.id;
        option.textContent = v.name;
        ruleVariantSelect.appendChild(option);
    }

    savedGameStatus.textContent = 'Choose a save file downloaded by the host.';

    ws = watchLobby(lobbyId, playerName, secretToken, msg => {
        if (msg.type === 'game_started' || (msg.type === 'lobby_update' && msg.started)) {
            enterGame(msg);  // the second case is a player rejoining a game that is already running
        } else if (msg.type === 'error') {
            savedGameStatus.textContent = msg.message;
            setStatus(msg.message);
        } else if (msg.type === 'lobby_update') {
            applySnapshot(msg);
            refreshPowers(msg).catch(e => console.error(e));
            if (msg.event === 'save_loaded') {
                setStatus('Save prepared. The host can start the game when everyone is ready.');
            } else if (msg.event === 'map_change' && msg.user_name !== playerName) {
                setStatus(`${msg.user_name} changed the map`);
            } else if (msg.event === 'power_change' && msg.user_name !== playerName) {
                setStatus(`${msg.user_name} picked ${msg.power || 'no power'}`);
            }
        }
    });
    gameSocket = ws;  // lets the shared Kick button send through this socket
}

init().catch(e => { setStatus('Error: ' + e); console.error(e); });
