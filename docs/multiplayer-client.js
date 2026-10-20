const playerName = sessionStorage.getItem('diplomacyPlayerName');
const gameCode = sessionStorage.getItem('diplomacyGameCode');
const gameID = sessionStorage.getItem('diplomacyGameID');

document.getElementById('leave-game').addEventListener('click', () => {
    confirmAction('Leave Game', 'Leave this game and return to the main menu?', () => goTo('index.html'));
});

async function init() {
    if (!playerName || !gameCode || !gameID) {
        goTo('multiplayer-join.html');
        return;
    }
    initSidebar();
    await loadMap(sessionStorage.getItem('diplomacyMap') || undefined);
    document.getElementById('info').textContent = `Player: ${playerName}\nGame code: ${gameCode}`;
    setStatus('Connecting to lobby...');
    watchLobby(gameID, playerName);
}

init().catch(e => { setStatus('Error: ' + e); console.error(e); });
