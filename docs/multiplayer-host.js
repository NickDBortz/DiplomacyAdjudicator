const playerName = sessionStorage.getItem('diplomacyPlayerName');
const gameName = sessionStorage.getItem('diplomacyGameName');
const gameID = sessionStorage.getItem('diplomacyGameID');

document.getElementById('leave-game').addEventListener('click', () => {
    confirmAction('Leave Game', 'Stop hosting and return to the main menu?', () => goTo('index.html'));
});

async function init() {
    if (!playerName || !gameName || !gameID) {
        goTo('multiplayer-create.html');
        return;
    }
    initSidebar();
    await loadMap(sessionStorage.getItem('diplomacyMap') || undefined);
    document.getElementById('info').textContent = `Host: ${playerName}\nGame code: ${gameName}`;
    setStatus('Connecting to lobby...');
    watchLobby(gameID, playerName);
}

init().catch(e => { setStatus('Error: ' + e); console.error(e); });
