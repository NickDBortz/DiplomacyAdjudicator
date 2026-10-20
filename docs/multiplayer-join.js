// Server-side joining is not implemented yet; this only collects the player's details.
document.getElementById('join-submit').addEventListener('click', () => {
    const code = document.getElementById('join-code').value.trim();
    const name = document.getElementById('join-name').value.trim();
    const message = document.getElementById('menu-message');
    if (!code || !name) {
        message.textContent = 'Enter a game code and your name.';
        return;
    }
    sessionStorage.setItem('diplomacyGameCode', code);
    sessionStorage.setItem('diplomacyPlayerName', name);
    location.href = 'multiplayer-client.html';
});

document.getElementById('join-back').addEventListener('click', () => { location.href = 'index.html'; });
