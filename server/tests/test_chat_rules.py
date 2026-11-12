import asyncio
import json

import app as server


def make_lobby(ruleset):
    return {
        'id': 'test-lobby',
        'host': 'Alice',
        'ruleset': ruleset,
        'started': True,
        'settings': {'map': 'classic_map'},
        'players': [
            {'user_name': 'Alice', 'selected_power': 'France'},
            {'user_name': 'Bob', 'selected_power': 'England'},
        ],
        'diplomacy_timer': {'active': True},
        'chat': {
            'next_id': 3,
            'lobby': [{'id': 1, 'channel': 'lobby', 'from': 'Alice', 'text': 'Public'}],
            'private': {
                ('Alice', 'Bob'): [{'id': 2, 'channel': 'private', 'from': 'Alice', 'to': 'Bob', 'text': 'Private'}],
            },
            'recent': {},
        },
    }


def send(lobby, channel):
    return server._send_chat(lobby, 'Alice', {'channel': channel, 'to': 'Bob', 'text': 'Hello'})


def test_normal_mode_allows_public_and_timer_private_chat():
    lobby = make_lobby('normal')

    public_reply, public_recipients, _ = send(lobby, 'lobby')
    private_reply, private_recipients, _ = send(lobby, 'private')

    assert public_reply['ok']
    assert public_recipients is None
    assert private_reply['ok']
    assert private_recipients == {'Alice', 'Bob'}
    assert [message['text'] for message in server._chat_history(lobby, 'Alice')] == [
        'Public', 'Private', 'Hello', 'Hello',
    ]


def test_gunboard_disables_chat_and_hides_chat_history():
    lobby = make_lobby('gunboard')

    for channel in ('lobby', 'private'):
        reply, recipients, payload = send(lobby, channel)
        assert not reply['ok']
        assert recipients is None
        assert payload is None
    assert server._chat_history(lobby, 'Alice') == []


def test_public_press_allows_public_chat_but_disables_private_chat():
    lobby = make_lobby('public_press')

    public_reply, recipients, _ = send(lobby, 'lobby')
    private_reply, private_recipients, payload = send(lobby, 'private')

    assert public_reply['ok']
    assert recipients is None
    assert not private_reply['ok']
    assert private_recipients is None
    assert payload is None
    assert [message['text'] for message in server._chat_history(lobby, 'Alice')] == ['Public', 'Hello']


def test_private_chat_reports_when_diplomacy_timer_is_inactive():
    lobby = make_lobby('normal')
    lobby['diplomacy_timer'] = {'active': False}

    reply, recipients, payload = send(lobby, 'private')

    assert not reply['ok']
    assert reply['error'] == 'Private messages are only available during an active Diplomacy timer.'
    assert recipients is None
    assert payload is None


def test_host_ruleset_selection_is_broadcast_and_non_host_cannot_change_it(monkeypatch):
    class Socket:
        def __init__(self):
            self.messages = []

        async def send_json(self, message):
            self.messages.append(message)

    lobby = make_lobby('normal')
    lobby['started'] = False
    host_socket = Socket()
    player_socket = Socket()
    monkeypatch.setattr(server, '_lobbies', {'Game': lobby})
    monkeypatch.setitem(server._lobby_sockets, lobby['id'], {
        'Alice': host_socket,
        'Bob': player_socket,
    })

    asyncio.run(server._handle_message(
        lobby['id'], 'Alice', json.dumps({'type': 'set_ruleset', 'ruleset': 'public_press'})))
    assert lobby['ruleset'] == 'public_press'
    assert host_socket.messages[-1]['ruleset'] == 'public_press'
    assert player_socket.messages[-1]['ruleset'] == 'public_press'

    asyncio.run(server._handle_message(
        lobby['id'], 'Bob', json.dumps({'type': 'set_ruleset', 'ruleset': 'gunboard'})))
    assert lobby['ruleset'] == 'public_press'
