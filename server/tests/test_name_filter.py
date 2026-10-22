import pytest
from fastapi.testclient import TestClient

import app as server
from name_filter import clean_name


@pytest.mark.parametrize('name', [
    'fuck', 'FUCK you', 'xXfuckXx', 'Sh1t', 'f.u.c.k', 'bitchface', 'Fück', 'cunt', 'big cock',
])
def test_obscene_names_are_rejected(name):
    assert clean_name(name, 'name')[1] is not None


@pytest.mark.parametrize('name', [
    'Nick', 'Scunthorpe', 'Cocktail Hour', 'Analysis', 'Hello', 'Kaiser Wilhelm', 'xXSniperXx',
    'Classic Game', 'Turkey', 'Assassin', 'Grape Juice',
])
def test_normal_names_are_allowed(name):
    assert clean_name(name, 'name') == (name, None)


def test_whitespace_and_length():
    assert clean_name('  Big   Game ', 'game name') == ('Big Game', None)
    assert clean_name('   ', 'name')[1] == 'Enter a name.'
    assert clean_name('x' * 25, 'name')[1] is not None
    assert clean_name('a\u200bb', 'name')[1] is not None


def test_endpoints_reject_obscene_names():
    client = TestClient(server.app)
    r = client.post('/open_lobby', json={'user_name': 'Host', 'lobby_name': 'shit game', 'lobby_password': ''}).json()
    assert not r['ok'] and 'game name' in r['message']
    r = client.post('/open_lobby', json={'user_name': 'Host', 'lobby_name': 'Name Filter Test', 'lobby_password': ''}).json()
    assert r['ok']
    lobby_id = r['lobby']['id']
    r = client.post(f'/join_lobby/{lobby_id}', json={'user_name': 'fuckface', 'lobby_password': ''}).json()
    assert not r['ok']
    r = client.post(f'/join_lobby/{lobby_id}', json={'user_name': 'Guest', 'lobby_password': ''}).json()
    assert r['ok']
    server._lobbies.pop('Name Filter Test', None)
