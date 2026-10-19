const playerName = sessionStorage.getItem('diplomacyPlayerName');
const gameCode = sessionStorage.getItem('diplomacyGameCode');

document.getElementById('leave-game').addEventListener('click', () => {
  confirmAction('Leave Game', 'Leave this game and return to the main menu?', () => goTo('index.html'));
});

async function init() {
  if (!playerName || !gameCode) {
    goTo('multiplayer-join.html');
    return;
  }
  initSidebar();
  await loadMap();
  document.getElementById('info').textContent = `Player: ${playerName}\nGame code: ${gameCode}`;
  setStatus('Waiting for server support for multiplayer games');
}

init().catch(e => { setStatus('Error: ' + e); console.error(e); });
