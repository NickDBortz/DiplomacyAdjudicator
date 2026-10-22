function showMenuView(id) {
    for (const view of document.querySelectorAll('.menu-view')) {
        view.classList.toggle('hidden', view.id !== id);
    }
}

document.getElementById('menu-singleplayer').addEventListener('click', () => { location.href = 'singleplayer.html'; });
document.getElementById('menu-multiplayer').addEventListener('click', () => showMenuView('menu-multi'));
document.getElementById('menu-host').addEventListener('click', () => { location.href = 'multiplayer-create.html'; });
document.getElementById('menu-join').addEventListener('click', () => { location.href = 'multiplayer-join.html'; });
document.getElementById('menu-back').addEventListener('click', () => showMenuView('menu-main'));

// A seat saved from an earlier visit; the lobby page forwards to the game if it has already started.
const savedSession = loadSession();
if (savedSession) {
    const rejoin = document.getElementById('menu-rejoin');
    rejoin.textContent = `Rejoin ${savedSession.lobbyName} as ${savedSession.userName}`;
    rejoin.classList.remove('hidden');
    rejoin.addEventListener('click', () => {
        rememberSeat(savedSession.lobbyId, savedSession.lobbyName, savedSession.userName, savedSession.secretToken);
        location.href = 'lobby.html';
    });
}

// Send a ping to the server to get it spinning up in the background 
request('GET', '/health');