const playerName = sessionStorage.getItem('diplomacyPlayerName');
const gameName = sessionStorage.getItem('diplomacyGameName');

document.getElementById('leave-game').addEventListener('click', () => {
  confirmAction('Leave Game', 'Stop hosting and return to the main menu?', () => goTo('index.html'));
});

async function init() {
  if (!playerName) {
    goTo('multiplayer-create.html');
    return;
  }
  if (!gameName) {
    goTo('multiplayer-create.html');
    return;
  }
  initSidebar();
  await loadMap();
  document.getElementById('info').textContent = `Host: ${playerName}\nGame code: ${gameName}`;
  setStatus('Waiting for server support for multiplayer games');
}

init().catch(e => { setStatus('Error: ' + e); console.error(e); });
