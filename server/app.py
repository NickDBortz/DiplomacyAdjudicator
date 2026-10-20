"""FastAPI backend exposing the Diplomacy adjudicator to the GitHub Pages frontend."""
import asyncio
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
MAX_ORDER_LENGTH = 200
REJOIN_GRACE_SECONDS = 10  # players moving from the lobby page to the game page reconnect within this
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
_lobby_games = {}  # lobby id -> Game, created when the host starts the lobby
_background_tasks = set()
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
            evicted = _lobbies.pop(next(iter(_lobbies)))
            _lobby_games.pop(evicted['id'], None)
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

@app.get('/lobbies/{lobby_id}/powers')
def get_lobby_powers(lobby_id: str):
    """Powers on the lobby's map that no player has picked yet."""
    with _lock:
        _, lobby = _find_lobby(lobby_id)
        if lobby is None:
            raise HTTPException(404, 'Lobby does not exist.')
        taken = {p['selected_power'] for p in lobby['players'] if p['selected_power']}
        return [p for p in _available_powers(lobby['settings']['map']) if p not in taken]

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

def _available_powers(map_id):
    try:
        with open(MAPS_DIR / f'{map_id}.json', 'r', encoding='utf-8') as file:
            return sorted(player['name'] for player in json.load(file)['players'])
    except (OSError, ValueError, KeyError):
        return []


def _snapshot(lobby):
    return {
        'players': [p['user_name'] for p in lobby['players']],
        'selected_powers': {p['user_name']: p['selected_power'] for p in lobby['players']},
        'host': lobby['host'],
        'settings': lobby['settings'],
    }


def _remove_player(lobby_id, user_name):
    """Drops a player, hands the host role to the next in line, and closes the lobby when empty.

    Returns the new snapshot, or None if nothing changed or the lobby closed. Call with _lock held.
    """
    name, lobby = _find_lobby(lobby_id)
    if lobby is None or not any(p['user_name'] == user_name for p in lobby['players']):
        return None
    lobby['players'] = [p for p in lobby['players'] if p['user_name'] != user_name]
    if not lobby['players']:
        del _lobbies[name]
        _lobby_games.pop(lobby_id, None)
        return None
    if lobby['host'] == user_name:
        lobby['host'] = lobby['players'][0]['user_name']
    return _snapshot(lobby)


async def _drop_after_grace(lobby_id, user_name):
    await asyncio.sleep(REJOIN_GRACE_SECONDS)
    with _lock:
        if user_name in _lobby_sockets.get(lobby_id, {}):
            return  # reconnected
        snapshot = _remove_player(lobby_id, user_name)
    if snapshot is not None:
        await _broadcast(lobby_id, {'type': 'lobby_update', 'event': 'left', 'user_name': user_name, **snapshot})


async def _broadcast(lobby_id, payload):
    for ws in list(_lobby_sockets.get(lobby_id, {}).values()):
        try:
            await ws.send_json(payload)
        except Exception:
            pass  # a dead socket is cleaned up by its own handler


async def _send_game_views(lobby_id, views):
    for name, ws in list(_lobby_sockets.get(lobby_id, {}).items()):
        if name in views:
            try:
                await ws.send_json({'type': 'game_state', 'state': views[name]})
            except Exception:
                pass


def _power_of(lobby, user_name):
    return next((p['selected_power'] for p in lobby['players'] if p['user_name'] == user_name), None)


def _view(lobby, power):
    """Own orders only, or everyone's once the host has revealed them."""
    revealed = lobby.get('orders_revealed', False)
    state = web_api.get_state(_lobby_games[lobby['id']], power=web_api.ALL_ORDERS if revealed else power)
    state['orders_revealed'] = revealed
    return state


def _game_views(lobby):
    """Each player sees every unit and territory, plus their own orders until the host reveals all."""
    return {p['user_name']: _view(lobby, p['selected_power']) for p in lobby['players']}


GAME_REPLY_TYPES = {
    'submit_order': 'order_result',
    'draw': 'draw_result',
    'reveal_orders': 'reveal_result',
    'resolve': 'resolve_result',
}


def _handle_game_message(lobby, user_name, kind, msg):
    """Returns (reply for the sender, per-player views to push to everyone or None)."""
    reply_type = GAME_REPLY_TYPES[kind]

    def fail(error):
        return {'type': reply_type, 'ok': False, 'error': error}, None

    game = _lobby_games.get(lobby['id'])
    power = _power_of(lobby, user_name)
    if game is None:
        return fail('The game has not started.')
    if game.game_state.winner is not None or game.game_state.draw:
        return fail('The game is over.')

    if kind in ('reveal_orders', 'resolve'):
        if lobby['host'] != user_name:
            return fail('Only the host can do that.')
        if kind == 'reveal_orders':
            lobby['orders_revealed'] = True
        else:
            if not lobby.get('orders_revealed'):
                return fail('Render the orders first.')
            game.adjudicator.resolve_orders()
            lobby['orders_revealed'] = False
        return {'type': reply_type, 'ok': True, 'error': None}, _game_views(lobby)

    if power is None:
        return fail('You have not been assigned a power.')
    if msg.get('power') != power:
        return fail(f'You cannot act for {msg.get("power")}.')

    player = game.game_state.get_player(power)
    if kind == 'submit_order':
        if lobby.get('orders_revealed'):
            return fail('Orders are revealed; waiting for the host to resolve.')
        order = msg.get('order')
        if not isinstance(order, str) or not order.strip() or len(order) > MAX_ORDER_LENGTH:
            return fail('Invalid order.')
        try:
            ok = bool(game.submit_order(order.strip(), player))
        except Exception:
            ok = False  # the parser can raise on malformed text
        if not ok:
            return fail('Invalid order.')
        view = _view(lobby, power)
        return {'type': 'order_result', 'ok': True, 'error': None, 'orders': view['orders'], 'state': view}, None

    game.game_state.vote_draw(player)
    reply = {'type': 'draw_result', 'ok': True, 'error': None, 'draw_votes': [p.name for p in game.game_state.draw_votes]}
    return reply, _game_views(lobby)


async def _handle_message(lobby_id, user_name, raw):
    try:
        msg = json.loads(raw)
    except ValueError:
        return
    kind = msg.get('type') if isinstance(msg, dict) else None
    if kind not in ('set_map', 'set_power', 'start_game', 'submit_order', 'draw', 'reveal_orders', 'resolve'):
        return

    reply = None
    payload = None
    views = None
    with _lock:
        _, lobby = _find_lobby(lobby_id)
        if lobby is None:
            return
        if kind in GAME_REPLY_TYPES:
            reply, views = _handle_game_message(lobby, user_name, kind, msg)
        elif lobby['started']:
            return
        elif kind == 'set_power':  # any player may pick their own power
            settings = msg.get('settings')
            power = (settings.get('power') or None) if isinstance(settings, dict) else None
            taken = power is not None and any(
                p['selected_power'] == power and p['user_name'] != user_name for p in lobby['players'])
            if power is not None and power not in _available_powers(lobby['settings']['map']):
                reply = {'type': 'error', 'message': 'Unknown power.'}
            elif taken:
                reply = {'type': 'error', 'message': 'That power is already taken.'}
            else:
                for player in lobby['players']:
                    if player['user_name'] == user_name:
                        player['selected_power'] = power
                payload = {'type': 'lobby_update', 'event': 'power_change', 'user_name': user_name, 'power': power, **_snapshot(lobby)}
        elif lobby['host'] != user_name:
            return
        elif kind == 'set_map':
            settings = msg.get('settings')
            map_id = settings.get('map') if isinstance(settings, dict) else None
            if map_id not in _available_maps():
                return
            lobby['settings']['map'] = map_id
            # Powers differ per map, so picks are cleared.
            for player in lobby['players']:
                player['selected_power'] = None
            payload = {'type': 'lobby_update', 'event': 'map_change', 'user_name': user_name, **_snapshot(lobby)}
        else:
            _lobby_games[lobby['id']] = web_api.new_game(str(MAPS_DIR / f"{lobby['settings']['map']}.json"))
            lobby['started'] = True
            payload = {'type': 'game_started', **_snapshot(lobby)}

    if reply is not None:
        ws = _lobby_sockets.get(lobby_id, {}).get(user_name)
        if ws is not None:
            await ws.send_json(reply)
    if views is not None:
        await _send_game_views(lobby_id, views)
    elif payload is not None:
        await _broadcast(lobby_id, payload)


@app.websocket('/ws/lobbies/{lobby_id}')
async def lobby_socket(websocket: WebSocket, lobby_id: str, user_name: str):
    await websocket.accept()

    # No awaits between these checks and registering the socket, so they are atomic on the event loop.
    replaced = None
    game_view = None
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
            if lobby['id'] in _lobby_games:
                game_view = _view(lobby, _power_of(lobby, user_name))
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
    if game_view is not None:
        await websocket.send_json({'type': 'game_state', 'state': game_view})
    left = False
    try:
        while True:
            # Pings keep proxies from idling the connection out; other messages are JSON commands.
            raw = await websocket.receive_text()
            try:
                is_leave = json.loads(raw).get('type') == 'leave'
            except (ValueError, AttributeError):
                is_leave = False
            if is_leave:
                left = True  # deliberate exit: skip the reconnect grace period
                break
            await _handle_message(lobby_id, user_name, raw)
    except WebSocketDisconnect:
        pass
    finally:
        snapshot = None
        grace = False
        with _lock:
            sockets = _lobby_sockets.get(lobby_id, {})
            if sockets.get(user_name) is websocket:
                del sockets[user_name]
            if not sockets:
                _lobby_sockets.pop(lobby_id, None)
            _, lobby = _find_lobby(lobby_id)
            if lobby is not None:
                if left or not lobby['started']:
                    snapshot = _remove_player(lobby_id, user_name)
                else:
                    grace = True
        if grace:
            # Players change pages when the game starts, so give them time to reconnect.
            task = asyncio.create_task(_drop_after_grace(lobby_id, user_name))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
        elif snapshot is not None:
            await _broadcast(lobby_id, {'type': 'lobby_update', 'event': 'left', 'user_name': user_name, **snapshot})
        if left:
            try:
                await websocket.close()
            except Exception:
                pass  # already closed

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
