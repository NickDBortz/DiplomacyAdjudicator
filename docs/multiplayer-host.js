const playerName = sessionStorage.getItem('diplomacyPlayerName');
const gameName = sessionStorage.getItem('diplomacyGameName');
const gameID = sessionStorage.getItem('diplomacyGameID');
const power = sessionStorage.getItem('power');

document.getElementById('leave-game').addEventListener('click', () => {
    confirmAction('Leave Game', 'Stop hosting and return to the main menu?', () => leaveLobby(gameSocket));
});

async function init() {
    if (!playerName || !gameName || !gameID) {
        goTo('multiplayer-create.html');
        return;
    }
    initSidebar();
    const isSpectator = power === 'Spectator';
    document.getElementById('player-actions').classList.toggle('hidden', isSpectator);
    document.getElementById('spectator-message').classList.toggle('hidden', !isSpectator);
    if (!isSpectator) {
        initOrderControls(submitOrder, submitDraw);
        initResolveControl();
    }
    await refreshMap(sessionStorage.getItem('diplomacyMap') || undefined);
    setStatus('Connecting to game...');
    joinGame(gameID, playerName, `Player: ${playerName}\nGame code: ${gameName}`);
}

init().catch(e => { setStatus('Error: ' + e); console.error(e); });
