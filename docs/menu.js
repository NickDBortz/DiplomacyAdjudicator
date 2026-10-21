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

// Send a ping to the server to get it spinning up in the background 
request('GET', '/health');