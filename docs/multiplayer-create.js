// Server-side game creation is not implemented yet; this only collects the host's details.
document.getElementById('host-create').addEventListener('click', async () => {
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
    const r = await request('POST', `/open_lobby`, {'user_name': name, 'lobby_name': gameName}, true);
    if (!r.ok) {
        document.getElementById('menu-message').textContent = r.message;
        return;
    }
    sessionStorage.setItem('diplomacyPlayerName', name);
    sessionStorage.setItem('diplomacyGameName', gameName);
    sessionStorage.setItem('diplomacyGameID', r.lobby.id);
    location.href = 'lobby.html';
});

document.getElementById('host-back').addEventListener('click', () => { location.href = 'index.html'; });
