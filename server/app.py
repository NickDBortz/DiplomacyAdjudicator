"""FastAPI backend exposing the Diplomacy adjudicator to the GitHub Pages frontend."""
import asyncio
import json
import os
import threading
import uuid
import secrets
import hashlib
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from game import web_api

MAX_SAVE_BYTES = 2_000_000
MAX_LOBBIES = 200
MAX_GAMES = 200
MAX_ORDER_LENGTH = 200
REJOIN_GRACE_SECONDS = 10  # players moving from the lobby page to the game page reconnect within this
MAPS_DIR = Path(__file__).resolve().parent / 'data' / 'maps'
DEFAULT_MAP = 'classic_map'
SPECTATOR_POWER = 'Spectator'
KICKED_CLOSE_CODE = 4410
AUTH_FAILED_CLOSE_CODE = 4401
AUTH_TIMEOUT_SECONDS = 10  # how long a new socket has to send its secret token

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
_lobby_pending_games = {}  # restored Game objects waiting for the host to start the lobby
_background_tasks = set()
_lock = threading.Lock()
_games = {}  # single-player games; independent of lobbies

class OrderRequest(BaseModel):
    order: str
    power: str

class DrawRequest(BaseModel):
    power: str

class LobbyRequest(BaseModel):
    user_name: str
    lobby_name: str
    lobby_password: str

class JoinRequest(BaseModel):
    user_name: str
    lobby_password: str

def _get_player_token():
    return secrets.token_urlsafe(32)

def _get_salt_hash(password, salt=None):
    if salt is None:
        salt = secrets.token_bytes(16)
    hash = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt, hash

def _get_client_safe_lobby(lobby):
    return {
        'id': lobby['id'],
        'name': lobby['name'],
        'needs_password': lobby['needs_password'],
        'host': lobby['host'],
        'started': lobby['started'],
        'settings': lobby['settings'],
        'players': [{'user_name': player['user_name'], 'selected_power': player['selected_power']} for player in lobby['players']]
    }

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
        'prepared_save': lobby.get('prepared_save'),
    }

@app.get('/health')
def health():
    return {'ok': True}

@app.post('/open_lobby')
def open_lobby(lobby_request: LobbyRequest):
    with _lock:
        lobby_name = lobby_request.lobby_name
        user_name = lobby_request.user_name
        password = lobby_request.lobby_password
        if len(_lobbies) >= MAX_LOBBIES:
            evicted = _lobbies.pop(next(iter(_lobbies)))
            _lobby_games.pop(evicted['id'], None)
            _lobby_pending_games.pop(evicted['id'], None)
        if lobby_name in _lobbies:
            return {'ok': False, 'message': 'Lobby name already in use.'}
        lobby_id = uuid.uuid4().hex
        secret_token = _get_player_token()
        needs_password = password != ''
        salt, hash = '', ''
        if needs_password:
            salt, hash = _get_salt_hash(password)
        _lobbies[lobby_name] = {
            'id': lobby_id,
            'name': lobby_name,
            'needs_password': password != '',
            'salt': salt,
            'hash': hash,
            'host': user_name,
            'started': False,
            'settings': {'map': DEFAULT_MAP},
            'players': [{'user_name': user_name, 'selected_power': None, 'secret_token': secret_token}],
        }
    return {'ok': True, 'lobby': _get_client_safe_lobby(_lobbies[lobby_name]), 'secret_token': secret_token}

@app.get('/maps')
def get_maps():
    return [{'id': m, 'name': m.removesuffix('_map').replace('_', ' ').title()} for m in _available_maps()]

@app.get('/lobbies')
def get_lobbies():
    lobbies = {}
    for key, value in _lobbies.items():
        if not value['started']:
            lobbies[key] = {'id': value['id'], 'needs_password': value['needs_password'], 'Players': len(value['players'])}
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
                if value['id'] in _lobby_pending_games:
                    return {'ok': False, 'message': 'A save is prepared; the host must start or cancel it first.'}
                if any(p['user_name'] == req.user_name for p in value['players']):
                    return {'ok': False, 'message': 'Name already taken in this lobby.'}
                if value['needs_password']:
                    _, hash = _get_salt_hash(req.lobby_password, _lobbies[key]['salt'])
                    if not secrets.compare_digest(hash, _lobbies[key]['hash']):
                        return {'ok': False, 'message': 'Incorrect password.'}
                secret_token = _get_player_token()
                _lobbies[key]['players'].append({'user_name': req.user_name, 'selected_power': None, 'secret_token': secret_token})
                return {'ok': True, 'lobby': _get_client_safe_lobby(_lobbies[key]), 'secret_token': secret_token}
    return {'ok': False, 'message': 'Lobby does not exist.'}

def _game_save_data(lobby):
    return {
        'format': 'diplomacy-game-save',
        'version': 1,
        'name': lobby.get('name', 'Diplomacy game'),
        'map': lobby['settings']['map'],
        'players': [
            {
                'user_name': player['user_name'],
                'selected_power': player['selected_power'],
                'eliminated': player['user_name'] in lobby.get('eliminated', []),
            }
            for player in lobby['players']
        ],
        'eliminated_players': list(lobby.get('eliminated', [])),
        'game': web_api.serialize_game(_lobby_games[lobby['id']], lobby['settings']['map']),
    }


def _restore_lobby_game(lobby, save_data):
    if not isinstance(save_data, dict) or save_data.get('format') != 'diplomacy-game-save' or save_data.get('version') != 1:
        raise ValueError('This is not a supported Diplomacy save file.')
    if len(json.dumps(save_data, separators=(',', ':')).encode('utf-8')) > MAX_SAVE_BYTES:
        raise ValueError('Save file is too large.')

    map_id = save_data.get('map')
    saved_players = save_data.get('players')
    game_data = save_data.get('game')
    if map_id not in _available_maps() or not isinstance(saved_players, list) or not isinstance(game_data, dict):
        raise ValueError('Save file has invalid game data or an unavailable map.')
    if game_data.get('map') != map_id:
        raise ValueError('Save file map does not match its game state.')

    game = web_api.restore_game(game_data, str(MAPS_DIR / f'{map_id}.json'))
    available_powers = {player.name for player in game.game_state.player_list}
    saved_by_name = {
        player['user_name']: player for player in saved_players
        if isinstance(player, dict) and isinstance(player.get('user_name'), str)
    }
    saved_power_list = [player.get('selected_power') for player in saved_players if isinstance(player, dict)]
    if any(power not in available_powers and power != SPECTATOR_POWER for power in saved_power_list if power is not None):
        raise ValueError('Save file assigns an unknown Great Power.')
    active_powers = [power for power in saved_power_list if power in available_powers]
    if len(active_powers) != len(set(active_powers)):
        raise ValueError('Save file assigns a Great Power to more than one player.')
    if len(lobby['players']) < len(active_powers):
        raise ValueError(f'This save needs {len(active_powers)} players. Invite them before loading it.')

    assigned = set()
    for player in lobby['players']:
        saved_player = saved_by_name.get(player['user_name'])
        power = saved_player.get('selected_power') if saved_player else None
        if power == SPECTATOR_POWER:
            player['selected_power'] = SPECTATOR_POWER
        elif power in available_powers and power not in assigned:
            player['selected_power'] = power
            assigned.add(power)
        else:
            player['selected_power'] = None

    remaining_powers = [power for power in active_powers if power not in assigned]
    for player in lobby['players']:
        if player['selected_power'] is None:
            if remaining_powers:
                player['selected_power'] = remaining_powers.pop(0)
                assigned.add(player['selected_power'])
            else:
                player['selected_power'] = SPECTATOR_POWER

    lobby['settings']['map'] = map_id
    lobby['orders_revealed'] = False
    lobby['eliminated'] = [
        player['user_name'] for player in lobby['players']
        if saved_by_name.get(player['user_name'], {}).get('eliminated', False)
    ]
    if _power_of(lobby, lobby['host']) is None:
        successor = next((p['user_name'] for p in lobby['players'] if _power_of(lobby, p['user_name']) is not None), None)
        if successor:
            lobby['host'] = successor
    _lobby_pending_games[lobby['id']] = game
    lobby['prepared_save'] = {
        'name': save_data.get('name') or 'Loaded game',
        'year': game.game_state.year,
        'phase': game.game_state.get_phase(),
        'map': map_id,
    }
    return lobby['prepared_save']

def _remove_player(lobby_id, user_name):
    """Drops a player, hands the host role to the next in line, and closes the lobby when empty.

    Returns the new snapshot, or None if nothing changed or the lobby closed. Call with _lock held.
    """
    name, lobby = _find_lobby(lobby_id)
    if lobby is None or not any(p['user_name'] == user_name for p in lobby['players']):
        return None
    lobby['players'] = [p for p in lobby['players'] if p['user_name'] != user_name]
    if lobby_id in _lobby_pending_games:
        _lobby_pending_games.pop(lobby_id, None)
        lobby.pop('prepared_save', None)
        lobby['eliminated'] = []
        for player in lobby['players']:
            player['selected_power'] = None
    if not lobby['players']:
        del _lobbies[name]
        _lobby_games.pop(lobby_id, None)
        _lobby_pending_games.pop(lobby_id, None)
        return None
    if lobby['host'] == user_name:
        lobby['host'] = next(
            (p['user_name'] for p in lobby['players'] if _power_of(lobby, p['user_name']) is not None),
            lobby['players'][0]['user_name'],
        )
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
    power = next((p['selected_power'] for p in lobby['players'] if p['user_name'] == user_name), None)
    return None if power == SPECTATOR_POWER else power

def _update_eliminations(lobby):
    game = _lobby_games[lobby['id']]
    state = game.game_state
    eliminated = lobby.setdefault('eliminated', [])

    for member in lobby['players']:
        power_name = member['selected_power']
        if not power_name or power_name == SPECTATOR_POWER:
            continue
        power = state.get_player(power_name)
        has_centers = bool(power.get_supply_centers(state.territory_list))
        has_units = any(not unit.disbanded for unit in power.units)
        lost = (not has_centers and not has_units) or (
            state.winner is not None and power.name != state.winner.name)
        if lost:
            member['selected_power'] = SPECTATOR_POWER
            eliminated.append(member['user_name'])

    if _power_of(lobby, lobby['host']) is None:
        successor = next((p['user_name'] for p in lobby['players'] if _power_of(lobby, p['user_name']) is not None), None)
        if successor is not None:
            lobby['host'] = successor

def _view(lobby, power, user_name):
    """Own orders only, or everyone's once the host has revealed them."""
    revealed = lobby.get('orders_revealed', False)
    state = web_api.get_state(_lobby_games[lobby['id']], power=web_api.ALL_ORDERS if revealed else power)
    state['orders_revealed'] = revealed
    state['player_power'] = next((p['selected_power'] for p in lobby['players'] if p['user_name'] == user_name), None)
    state['player_eliminated'] = user_name in lobby.get('eliminated', [])
    state['host'] = lobby['host']
    state['lobby_players'] = [p['user_name'] for p in lobby['players']]
    state['selected_powers'] = {p['user_name']: p['selected_power'] for p in lobby['players']}
    state['eliminated_players'] = list(lobby.get('eliminated', []))
    return state

def _game_views(lobby):
    """Each player sees every unit and territory, plus their own orders until the host reveals all."""
    return {p['user_name']: _view(lobby, _power_of(lobby, p['user_name']), p['user_name']) for p in lobby['players']}

GAME_REPLY_TYPES = {
    'submit_order': 'order_result',
    'delete_order': 'order_delete_result',
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
            _update_eliminations(lobby)
            return {
                'type': reply_type,
                'ok': True,
                'error': None,
                'save_data': _game_save_data(lobby),
            }, _game_views(lobby)
        return {'type': reply_type, 'ok': True, 'error': None}, _game_views(lobby)

    if power is None:
        return fail('You have not been assigned a power.')
    if msg.get('power') != power:
        return fail(f'You cannot act for {msg.get("power")}.')

    player = game.game_state.get_player(power)
    if kind == 'delete_order':
        if lobby.get('orders_revealed'):
            return fail('Orders are revealed; waiting for the host to resolve.')
        queue_id = msg.get('queue_id')
        orders = game.game_state.queued_orders
        if isinstance(queue_id, bool) or not isinstance(queue_id, int) or queue_id < 0 or queue_id >= len(orders):
            return fail('That order no longer exists.')
        order = orders[queue_id]
        if order.unit.owner != player:
            return fail('You can only delete your own orders.')
        game.game_state.remove_queued_order(order)
        if order.unit.order is order:
            order.unit.reset_order()
        view = _view(lobby, power, user_name)
        return {'type': 'order_delete_result', 'ok': True, 'error': None, 'state': view}, _game_views(lobby)

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
        view = _view(lobby, power, user_name)
        return {'type': 'order_result', 'ok': True, 'error': None, 'orders': view['orders'], 'state': view}, _game_views(lobby)

    game.game_state.vote_draw(player)
    reply = {'type': 'draw_result', 'ok': True, 'error': None, 'draw_votes': [p.name for p in game.game_state.draw_votes]}
    return reply, _game_views(lobby)

def _kick_player(lobby, user_name, target):
    """Host only: removes another player. Returns (reply, broadcast payload, socket to close). Call with _lock held."""
    def fail(error):
        return {'type': 'kick_result', 'ok': False, 'error': error}, None, None

    if lobby['host'] != user_name:
        return fail('Only the host can kick players.')
    if not isinstance(target, str) or not any(p['user_name'] == target for p in lobby['players']):
        return fail('That player is not in the lobby.')
    if target == user_name:
        return fail('You cannot kick yourself.')
    # Unregister the socket first so its disconnect handler does not treat the kick as a normal leave.
    kicked_socket = _lobby_sockets.get(lobby['id'], {}).pop(target, None)
    snapshot = _remove_player(lobby['id'], target)
    payload = None
    if snapshot is not None:
        payload = {'type': 'lobby_update', 'event': 'kicked', 'user_name': target, **snapshot}
    return {'type': 'kick_result', 'ok': True, 'error': None}, payload, kicked_socket

async def _handle_message(lobby_id, user_name, raw):
    try:
        msg = json.loads(raw)
    except ValueError:
        return
    kind = msg.get('type') if isinstance(msg, dict) else None
    if kind not in ('set_map', 'set_power', 'start_game', 'load_saved_game', 'submit_order', 'delete_order', 'draw', 'reveal_orders', 'resolve', 'kick_player'):
        return

    reply = None
    payload = None
    views = None
    kicked_socket = None
    with _lock:
        _, lobby = _find_lobby(lobby_id)
        if lobby is None:
            return
        if kind == 'kick_player':
            reply, payload, kicked_socket = _kick_player(lobby, user_name, msg.get('user_name'))
        elif kind in GAME_REPLY_TYPES:
            reply, views = _handle_game_message(lobby, user_name, kind, msg)
        elif lobby['started']:
            return
        elif kind == 'set_power':  # any player may pick their own power
            if lobby['id'] in _lobby_pending_games:
                reply = {'type': 'error', 'message': 'A save is prepared; the host must start it or change the map first.'}
            else:
                settings = msg.get('settings')
                power = (settings.get('power') or None) if isinstance(settings, dict) else None
                taken = power not in (None, SPECTATOR_POWER) and any(
                    p['selected_power'] == power and p['user_name'] != user_name for p in lobby['players'])
                if power is not None and power != SPECTATOR_POWER and power not in _available_powers(lobby['settings']['map']):
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
            _lobby_pending_games.pop(lobby['id'], None)
            lobby.pop('prepared_save', None)
            lobby['eliminated'] = []
            lobby['settings']['map'] = map_id
            # Powers differ per map, so picks are cleared.
            for player in lobby['players']:
                player['selected_power'] = None
            payload = {'type': 'lobby_update', 'event': 'map_change', 'user_name': user_name, **_snapshot(lobby)}
        elif kind == 'load_saved_game':
            try:
                prepared = _restore_lobby_game(lobby, msg.get('save_data'))
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
                reply = {'type': 'error', 'message': str(e) or 'Could not load that saved game.'}
            else:
                payload = {
                    'type': 'lobby_update',
                    'event': 'save_loaded',
                    'user_name': user_name,
                    'prepared_save': prepared,
                    **_snapshot(lobby),
                }
        else:
            if any(p['selected_power'] is None for p in lobby['players']):
                reply = {'type': 'error', 'message': 'Every player must select a Great Power before starting.'}
            elif not any(p['selected_power'] != SPECTATOR_POWER for p in lobby['players']):
                reply = {'type': 'error', 'message': 'At least one player must select a Great Power.'}
            else:
                if _power_of(lobby, lobby['host']) is None:
                    lobby['host'] = next(p['user_name'] for p in lobby['players'] if p['selected_power'] != SPECTATOR_POWER)
                game = _lobby_pending_games.pop(lobby['id'], None)
                _lobby_games[lobby['id']] = game or web_api.new_game(str(MAPS_DIR / f"{lobby['settings']['map']}.json"))
                lobby['started'] = True
                lobby.pop('prepared_save', None)
                payload = {'type': 'game_started', **_snapshot(lobby)}

    if kicked_socket is not None:
        try:
            await kicked_socket.close(code=KICKED_CLOSE_CODE)
        except Exception:
            pass
    if reply is not None:
        ws = _lobby_sockets.get(lobby_id, {}).get(user_name)
        if ws is not None:
            await ws.send_json(reply)
    if views is not None:
        await _send_game_views(lobby_id, views)
    elif payload is not None:
        await _broadcast(lobby_id, payload)

def _token_matches(player, token):
    expected = player.get('secret_token')
    if not isinstance(expected, str) or not isinstance(token, str):
        return False
    return secrets.compare_digest(expected.encode(), token.encode())

async def _receive_token(websocket):
    """The client's first message must be its secret token; returns None if it is missing or late."""
    try:
        token = await asyncio.wait_for(websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS)
    except (asyncio.TimeoutError, WebSocketDisconnect, RuntimeError):
        return None
    return token.strip() or None

@app.websocket('/ws/lobbies/{lobby_id}')
async def lobby_socket(websocket: WebSocket, lobby_id: str, user_name: str):
    await websocket.accept()

    token = await _receive_token(websocket)
    if token is None:
        try:
            await websocket.close(code=AUTH_FAILED_CLOSE_CODE)
        except Exception:
            pass
        return

    # No awaits between these checks and registering the socket, so they are atomic on the event loop.
    replaced = None
    game_view = None
    with _lock:
        _, lobby = _find_lobby(lobby_id)
        is_member = lobby is not None and any(
            p['user_name'] == user_name and _token_matches(p, token) for p in lobby['players'])
        sockets = _lobby_sockets.get(lobby_id, {})
        already_connected = user_name in sockets
        # After the start, players reconnect from the game page and supersede their lobby-page socket.
        can_register = is_member and (not already_connected or lobby['started'])
        if can_register:
            replaced = sockets.get(user_name)
            _lobby_sockets.setdefault(lobby_id, {})[user_name] = websocket
            snapshot = _snapshot(lobby)
            if lobby['id'] in _lobby_games:
                game_view = _view(lobby, _power_of(lobby, user_name), user_name)
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

# Single-player games: one browser plays every power, so there is no per-player identity to check.
def _get(game_id):
    game = _games.get(game_id)
    if game is None:
        raise HTTPException(404, 'Unknown game id')
    return game

def _check_power(game, power):
    if game.game_state.get_player(power) is None:
        raise HTTPException(400, f'Unknown power: {power}')

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