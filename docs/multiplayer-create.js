// Server-side game creation is not implemented yet; this only collects the host's details.
document.getElementById('host-create').addEventListener('click', () => {
  const name = document.getElementById('host-name').value.trim();
  const gameName = document.getElementById('host-game-name').value.trim();
  if (!name) {
    document.getElementById('menu-message').textContent = 'Enter your name.';
    return;
  }
  if (!gameName) {
    document.getElementById('menu-message').textContent = 'Enter a game name.';
    return;
  }
  sessionStorage.setItem('diplomacyPlayerName', name);
  sessionStorage.setItem('diplomacyGameName', gameName);
  location.href = 'multiplayer-host.html';
});

document.getElementById('host-back').addEventListener('click', () => { location.href = 'index.html'; });
