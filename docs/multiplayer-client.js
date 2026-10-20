const playerName = sessionStorage.getItem('diplomacyPlayerName');
const gameCode = sessionStorage.getItem('diplomacyGameCode');
const gameID = sessionStorage.getItem('diplomacyGameID');

document.getElementById('leave-game').addEventListener('click', () => {
    confirmAction('Leave Game', 'Leave this game and return to the main menu?', () => leaveLobby(gameSocket));
});

async function init() {
    if (!playerName || !gameCode || !gameID) {
        goTo('multiplayer-join.html');
        return;
    }
    initSidebar();
    initOrderControls(
        submitOrder,
        submitDraw
    );
    initResolveControl();
    await refreshMap(sessionStorage.getItem('diplomacyMap') || undefined);
    setStatus('Connecting to game...');
    joinGame(gameID, playerName, `Player: ${playerName}\nGame code: ${gameCode}`);
}

init().catch(e => { setStatus('Error: ' + e); console.error(e); });
