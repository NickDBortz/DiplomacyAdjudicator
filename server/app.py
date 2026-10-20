"""FastAPI backend exposing the Diplomacy adjudicator to the GitHub Pages frontend."""
import json
import os
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from game import web_api

MAX_LOBBIES = 200
MAX_GAMES = 200
MAPS_DIR = Path(__file__).resolve().parent / 'data' / 'maps'
DEFAULT_MAP = 'classic_map'

app = FastAPI(title='Diplomacy Adjudicator')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get('ALLOWED_ORIGINS', '*').split(',')],
    allow_methods=['*'],
    allow_headers=['*'],
)

_lobbies = {}
_lobby_sockets = {}  # lobby id -> {user_name: WebSocket}
_games = {}
_lock = threading.Lock()


class OrderRequest(BaseModel):
    order: str
    power: str


class DrawRequest(BaseModel):
    power: str

class LobbyRequest(BaseModel):
    user_name: str
    lobby_name: str

class JoinRequest(BaseModel):
    user_name: str


def _get(game_id):
    game = _games.get(game_id)
    if game is None:
        raise HTTPException(404, 'Unknown game id')
    return game


def _check_power(game, power):
    if game.game_state.get_player(power) is None:
        raise HTTPException(400, f'Unknown power: {power}')


@app.get('/health')
def health():
    return {'ok': True}

@app.post('/open_lobby')
def open_lobby(lobby_request: LobbyRequest):
    with _lock:
        lobby_name = lobby_request.lobby_name
        user_name = lobby_request.user_name
        if len(_lobbies) >= MAX_LOBBIES:
            _lobbies.pop(next(iter(_lobbies)))
        if lobby_name in _lobbies:
            return {'ok': False, 'message': 'Lobby name already in use.'}
        lobby_id = uuid.uuid4().hex
        _lobbies[lobby_name] = {
            'id': lobby_id,
            'host': user_name,
            'started': False,
            'settings': {'map': DEFAULT_MAP},
            'players': [{'user_name': user_name, 'selected_power': None}],
        }
    return {'ok': True, 'lobby': _lobbies[lobby_name]}

@app.get('/maps')
def get_maps():
    return [{'id': m, 'name': m.removesuffix('_map').replace('_', ' ').title()} for m in _available_maps()]

@app.get('/lobbies')
def get_lobbies():
    lobbies = {}
    for key, value in _lobbies.items():
        if not value['started']:
            lobbies[key] = {'id': value['id'], 'Players': len(value['players'])}
    return lobbies

@app.post('/join_lobby/{lobby_id}')
def join_lobby(lobby_id: str, req: JoinRequest):
    with _lock:
        for key, value in _lobbies.items():
            if value['id'] == lobby_id:
                if value['started']:
                    return {'ok': False, 'message': 'Game already started.'}
                if any(p['user_name'] == req.user_name for p in value['players']):
                    return {'ok': False, 'message': 'Name already taken in this lobby.'}
                _lobbies[key]['players'].append({'user_name': req.user_name, 'selected_power': None})
                return {'ok': True, 'lobby': _lobbies[key]}
    return {'ok': False, 'message': 'Lobby does not exist.'}


def _find_lobby(lobby_id):
    for name, lobby in _lobbies.items():
        if lobby['id'] == lobby_id:
            return name, lobby
    return None, None


def _available_maps():
    return sorted(p.stem for p in MAPS_DIR.glob('*.json'))


def _snapshot(lobby):
    return {
        'players': [p['user_name'] for p in lobby['players']],
        'host': lobby['host'],
        'settings': lobby['settings'],
    }


async def _broadcast(lobby_id, payload):
    for ws in list(_lobby_sockets.get(lobby_id, {}).values()):
        try:
            await ws.send_json(payload)
        except Exception:
            pass  # a dead socket is cleaned up by its own handler


async def _handle_host_message(lobby_id, user_name, raw):
    try:
        msg = json.loads(raw)
    except ValueError:
        return
    kind = msg.get('type') if isinstance(msg, dict) else None
    if kind not in ('set_settings', 'start_game'):
        return

    with _lock:
        _, lobby = _find_lobby(lobby_id)
        if lobby is None or lobby['host'] != user_name or lobby['started']:
            return
        if kind == 'set_settings':
            settings = msg.get('settings')
            map_id = settings.get('map') if isinstance(settings, dict) else None
            if map_id not in _available_maps():
                return
            lobby['settings']['map'] = map_id
            payload = {'type': 'lobby_update', 'event': 'settings', 'user_name': user_name, **_snapshot(lobby)}
        else:
            lobby['started'] = True
            payload = {'type': 'game_started', **_snapshot(lobby)}
    await _broadcast(lobby_id, payload)


@app.websocket('/ws/lobbies/{lobby_id}')
async def lobby_socket(websocket: WebSocket, lobby_id: str, user_name: str):
    await websocket.accept()

    # No awaits between these checks and registering the socket, so they are atomic on the event loop.
    replaced = None
    with _lock:
        _, lobby = _find_lobby(lobby_id)
        is_member = lobby is not None and any(p['user_name'] == user_name for p in lobby['players'])
        sockets = _lobby_sockets.get(lobby_id, {})
        already_connected = user_name in sockets
        # After the start, players reconnect from the game page and supersede their lobby-page socket.
        can_register = is_member and (not already_connected or lobby['started'])
        if can_register:
            replaced = sockets.get(user_name)
            _lobby_sockets.setdefault(lobby_id, {})[user_name] = websocket
            snapshot = _snapshot(lobby)
    if lobby is None:
        await websocket.close(code=4404)
        return
    if not is_member:
        await websocket.close(code=4403)
        return
    if not can_register:
        await websocket.close(code=4409)
        return
    if replaced is not None:
        try:
            await replaced.close()
        except Exception:
            pass

    await _broadcast(lobby_id, {'type': 'lobby_update', 'event': 'joined', 'user_name': user_name, **snapshot})
    try:
        while True:
            # Pings keep proxies from idling the connection out; host commands are JSON.
            await _handle_host_message(lobby_id, user_name, await websocket.receive_text())
    except WebSocketDisconnect:
        pass
    finally:
        snapshot = None
        with _lock:
            sockets = _lobby_sockets.get(lobby_id, {})
            if sockets.get(user_name) is websocket:
                del sockets[user_name]
            if not sockets:
                _lobby_sockets.pop(lobby_id, None)
            name, lobby = _find_lobby(lobby_id)
            # Once started, players stay in the lobby so they can reconnect from the game page.
            if lobby is not None and not lobby['started']:
                lobby['players'] = [p for p in lobby['players'] if p['user_name'] != user_name]
                if lobby['players']:
                    if lobby['host'] == user_name:
                        lobby['host'] = lobby['players'][0]['user_name']
                    snapshot = _snapshot(lobby)
                else:
                    del _lobbies[name]
        if snapshot is not None:
            await _broadcast(lobby_id, {'type': 'lobby_update', 'event': 'left', 'user_name': user_name, **snapshot})

@app.post('/games')
def create_game():
    with _lock:
        if len(_games) >= MAX_GAMES:
            _games.pop(next(iter(_games)))
        game_id = uuid.uuid4().hex
        _games[game_id] = web_api.new_game()
    return {'game_id': game_id, 'state': web_api.get_state(_games[game_id])}


@app.get('/games/{game_id}')
def get_state(game_id: str):
    return web_api.get_state(_get(game_id))


@app.post('/games/{game_id}/orders')
def submit_order(game_id: str, req: OrderRequest):
    game = _get(game_id)
    with _lock:
        result = web_api.submit_order(game, req.order, req.power)
        result['state'] = web_api.get_state(game)
    return result


@app.post('/games/{game_id}/resolve')
def resolve(game_id: str):
    game = _get(game_id)
    with _lock:
        return web_api.resolve(game)


@app.post('/games/{game_id}/draw')
def draw(game_id: str, req: DrawRequest):
    game = _get(game_id)
    _check_power(game, req.power)
    with _lock:
        return web_api.draw(game, req.power)
