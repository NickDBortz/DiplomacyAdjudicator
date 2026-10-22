const playerName = sessionStorage.getItem('diplomacyPlayerName');
const gameCode = sessionStorage.getItem('diplomacyGameCode');
const gameID = sessionStorage.getItem('diplomacyGameID');
const power = sessionStorage.getItem('power');
playerListKickEnabled = true;  // takes effect only while this player is the host

document.getElementById('leave-game').addEventListener('click', () => {
    confirmAction('Leave Game', 'Leave this game and return to the main menu?', () => leaveLobby(gameSocket));
});

async function init() {
    if (!playerName || !gameCode || !gameID) {
        goTo('multiplayer-join.html');
        return;
    }
    initSidebar();
    const isSpectator = power === 'Spectator';
    document.getElementById('player-actions').classList.toggle('hidden', isSpectator);
    document.getElementById('spectator-message').classList.toggle('hidden', !isSpectator);
    // Always wired: a spectator can be given a vacant power, and anyone with a power can become host.
    initOrderControls(submitOrder, submitDraw);
    initResolveControl();
    initHostTools();
    await refreshMap(sessionStorage.getItem('diplomacyMap') || undefined);
    setStatus('Connecting to game...');
    joinGame(gameID, playerName, `Player: ${playerName}\nGame code: ${gameCode}`);
}

init().catch(e => { setStatus('Error: ' + e); console.error(e); });
