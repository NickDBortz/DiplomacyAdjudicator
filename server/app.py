"""FastAPI backend exposing the Diplomacy adjudicator to the GitHub Pages frontend."""
import asyncio
import json
import os
import threading
import uuid
import secrets
import hashlib
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from game import web_api

MAX_SAVE_BYTES = 2_000_000
MAX_LOBBIES = 200
MAX_GAMES = 200
MAX_ORDER_LENGTH = 200
REJOIN_GRACE_SECONDS = 10  # page changes and refreshes reconnect within this, so nobody is announced as gone
HOST_HANDOVER_SECONDS = 60  # a disconnected host keeps the role this long before it passes to a connected player
ABANDONED_LOBBY_SECONDS = 2 * 60 * 60  # a running game with nobody connected is deleted after this
JOIN_REQUEST_TIMEOUT_SECONDS = 180
MAX_JOIN_REQUESTS = 5  # pending requests per lobby
MAPS_DIR = Path(__file__).resolve().parent / 'data' / 'maps'
DEFAULT_MAP = 'classic_map'
SPECTATOR_POWER = 'Spectator'
KICKED_CLOSE_CODE = 4410
REPLACED_CLOSE_CODE = 4409  # the same seat connected from another tab or window
JOIN_EXPIRED_CLOSE_CODE = 4408
JOIN_REJECTED_CLOSE_CODE = 4412
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
_join_waiters = {}  # join request id -> WebSocket of the person waiting for the host's answer
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

def _connected_names(lobby):
    return set(_lobby_sockets.get(lobby['id'], {}))

def _power_is_alive(state, power):
    return bool(power.get_supply_centers(state.territory_list)) or any(not unit.disbanded for unit in power.units)

def _vacant_powers(lobby):
    """Powers still in a running game that no player controls; their units hold until someone takes over."""
    game = _lobby_games.get(lobby['id'])
    if game is None or game.game_state.winner is not None or game.game_state.draw:
        return []
    state = game.game_state
    assigned = {p['selected_power'] for p in lobby['players']}
    return sorted(p.name for p in state.player_list if p.name not in assigned and _power_is_alive(state, p))

def _open_join_requests(lobby):
    """Requests whose sender is connected and waiting; those are the ones the host can answer."""
    return [{'request_id': rid, 'user_name': r['user_name']}
            for rid, r in lobby.get('join_requests', {}).items() if rid in _join_waiters]

def _pick_successor(lobby, exclude=None, require_power=False, require_connected=False):
    """Next host: prefers connected players who control a power. Returns None if nobody qualifies."""
    connected = _connected_names(lobby)
    names = [p['user_name'] for p in lobby['players'] if p['user_name'] != exclude]
    for needs_power, needs_connection in ((True, True), (False, True), (True, False), (False, False)):
        if (require_power and not needs_power) or (require_connected and not needs_connection):
            continue
        match = next((n for n in names
                      if (not needs_power or _power_of(lobby, n) is not None)
                      and (not needs_connection or n in connected)), None)
        if match is not None:
            return match
    return None

def _snapshot(lobby):
    return {
        'players': [p['user_name'] for p in lobby['players']],
        'selected_powers': {p['user_name']: p['selected_power'] for p in lobby['players']},
        'connected_players': sorted(_connected_names(lobby)),
        'host': lobby['host'],
        'started': lobby['started'],
        'settings': lobby['settings'],
        'prepared_save': lobby.get('prepared_save'),
        'vacant_powers': _vacant_powers(lobby),
        'accepting_joins': lobby.get('accepting_joins', False),
        'join_requests': _open_join_requests(lobby),
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
            'accepting_joins': False,
            'join_requests': {},
        }
    return {'ok': True, 'lobby': _get_client_safe_lobby(_lobbies[lobby_name]), 'secret_token': secret_token}

@app.get('/maps')
def get_maps():
    return [{'id': m, 'name': m.removesuffix('_map').replace('_', ' ').title()} for m in _available_maps()]

@app.get('/lobbies')
def get_lobbies():
    """Open lobbies, plus running games whose host is accepting join requests."""
    lobbies = {}
    with _lock:
        for key, value in _lobbies.items():
            if value['started'] and not value.get('accepting_joins'):
                continue
            lobbies[key] = {
                'id': value['id'],
                'needs_password': value['needs_password'],
                'Players': len(value['players']),
                'in_progress': value['started'],
                'vacant_powers': _vacant_powers(value) if value['started'] else [],
            }
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

def _prune_join_requests(lobby):
    """Drops expired requests whose sender never connected to wait; connected waiters time out on their own."""
    now = time.monotonic()
    requests = lobby.setdefault('join_requests', {})
    for rid in [rid for rid, r in requests.items() if r['expires'] <= now and rid not in _join_waiters]:
        del requests[rid]

@app.post('/join_lobby/{lobby_id}')
def join_lobby(lobby_id: str, req: JoinRequest):
    with _lock:
        _, lobby = _find_lobby(lobby_id)
        if lobby is None:
            return {'ok': False, 'message': 'Lobby does not exist.'}
        if lobby['started'] and not lobby.get('accepting_joins'):
            return {'ok': False, 'message': 'Game already started.'}
        if lobby['id'] in _lobby_pending_games:
            return {'ok': False, 'message': 'A save is prepared; the host must start or cancel it first.'}
        _prune_join_requests(lobby)
        if any(p['user_name'] == req.user_name for p in lobby['players']) or any(
                r['user_name'] == req.user_name for r in lobby['join_requests'].values()):
            return {'ok': False, 'message': 'Name already taken in this lobby.'}
        if lobby['needs_password']:
            _, hash = _get_salt_hash(req.lobby_password, lobby['salt'])
            if not secrets.compare_digest(hash, lobby['hash']):
                return {'ok': False, 'message': 'Incorrect password.'}
        if lobby['started']:
            # Running games need the host's approval; the client waits on the request socket for the answer.
            if len(lobby['join_requests']) >= MAX_JOIN_REQUESTS:
                return {'ok': False, 'message': 'Too many people are waiting to join. Try again shortly.'}
            request_id = uuid.uuid4().hex
            request_token = _get_player_token()
            lobby['join_requests'][request_id] = {
                'user_name': req.user_name,
                'token': request_token,
                'expires': time.monotonic() + JOIN_REQUEST_TIMEOUT_SECONDS,
            }
            return {'ok': True, 'pending': True, 'request_id': request_id, 'request_token': request_token,
                    'lobby': _get_client_safe_lobby(lobby)}
        secret_token = _get_player_token()
        lobby['players'].append({'user_name': req.user_name, 'selected_power': None, 'secret_token': secret_token})
        return {'ok': True, 'lobby': _get_client_safe_lobby(lobby), 'secret_token': secret_token}

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
    removed = next(p for p in lobby['players'] if p['user_name'] == user_name)
    lobby['players'] = [p for p in lobby['players'] if p['user_name'] != user_name]
    game = _lobby_games.get(lobby_id)
    if game is not None and removed['selected_power'] not in (None, SPECTATOR_POWER):
        # The power is now vacant: its units hold, and a vote it can no longer withdraw should not count.
        power = game.game_state.get_player(removed['selected_power'])
        if power in game.game_state.draw_votes:
            game.game_state.draw_votes.remove(power)
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
        lobby['host'] = _pick_successor(lobby)
    return _snapshot(lobby)

def _spawn(coro):
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

async def _after_disconnect(lobby_id, user_name):
    """A socket closed without a deliberate leave. Running games keep the seat until the player leaves or the
    host kicks them; lobbies that have not started drop the player once the grace period passes."""
    await asyncio.sleep(REJOIN_GRACE_SECONDS)
    with _lock:
        _, lobby = _find_lobby(lobby_id)
        if lobby is None or user_name in _lobby_sockets.get(lobby_id, {}):
            return  # gone, or reconnected
        if not lobby['started']:
            snapshot, event = _remove_player(lobby_id, user_name), 'left'
        elif any(p['user_name'] == user_name for p in lobby['players']):
            snapshot, event = _snapshot(lobby), 'disconnected'
        else:
            return
        watch_host = lobby['started'] and lobby['host'] == user_name
        abandoned = lobby['started'] and not _lobby_sockets.get(lobby_id)
    if snapshot is not None:
        await _broadcast(lobby_id, {'type': 'lobby_update', 'event': event, 'user_name': user_name, **snapshot})
    if abandoned:
        _spawn(_close_if_abandoned(lobby_id))
    if not watch_host:
        return

    await asyncio.sleep(max(0, HOST_HANDOVER_SECONDS - REJOIN_GRACE_SECONDS))
    with _lock:
        _, lobby = _find_lobby(lobby_id)
        if lobby is None or lobby['host'] != user_name or user_name in _lobby_sockets.get(lobby_id, {}):
            return
        successor = _pick_successor(lobby, exclude=user_name, require_power=True, require_connected=True)
        if successor is None:
            return  # nobody connected can take over, so the role waits for the host to return
        lobby['host'] = successor
        snapshot = _snapshot(lobby)
    await _broadcast(lobby_id, {'type': 'lobby_update', 'event': 'host_changed', 'user_name': successor,
                                'previous_host': user_name, **snapshot})

async def _close_if_abandoned(lobby_id):
    await asyncio.sleep(ABANDONED_LOBBY_SECONDS)
    with _lock:
        name, lobby = _find_lobby(lobby_id)
        if lobby is None or _lobby_sockets.get(lobby_id):
            return
        del _lobbies[name]
        _lobby_games.pop(lobby_id, None)
        _lobby_pending_games.pop(lobby_id, None)

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
        successor = _pick_successor(lobby, require_power=True)
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
    state['connected_players'] = sorted(_connected_names(lobby))
    state['vacant_powers'] = _vacant_powers(lobby)
    state['accepting_joins'] = lobby.get('accepting_joins', False)
    state['join_requests'] = _open_join_requests(lobby)
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

def _host_action_fail(reply_type, error):
    return {'type': reply_type, 'ok': False, 'error': error}, None, None, []

def _host_action_ok(reply_type, payload, views=None, closes=()):
    return {'type': reply_type, 'ok': True, 'error': None}, payload, views, list(closes)

# Host-only actions. Each returns (reply, lobby_update payload, game views, [(socket, final message, close code)]).
# Call with _lock held; sockets are closed after the lock is released.

def _kick_player(lobby, user_name, msg):
    """Removes another player. In a running game their power becomes vacant; this is also how the host releases
    the seat of someone who disconnected and is not coming back."""
    reply_type = 'kick_result'
    target = msg.get('user_name')
    if lobby['host'] != user_name:
        return _host_action_fail(reply_type, 'Only the host can kick players.')
    if not isinstance(target, str) or not any(p['user_name'] == target for p in lobby['players']):
        return _host_action_fail(reply_type, 'That player is not in the lobby.')
    if target == user_name:
        return _host_action_fail(reply_type, 'You cannot kick yourself.')
    # Unregister the socket first so its disconnect handler does not treat the kick as a normal leave.
    kicked_socket = _lobby_sockets.get(lobby['id'], {}).pop(target, None)
    snapshot = _remove_player(lobby['id'], target)
    payload = None
    if snapshot is not None:
        payload = {'type': 'lobby_update', 'event': 'kicked', 'user_name': target, **snapshot}
    closes = [(kicked_socket, None, KICKED_CLOSE_CODE)] if kicked_socket is not None else []
    return _host_action_ok(reply_type, payload, closes=closes)

def _transfer_host(lobby, user_name, msg):
    reply_type = 'host_transfer_result'
    target = msg.get('user_name')
    if lobby['host'] != user_name:
        return _host_action_fail(reply_type, 'Only the host can hand over the host role.')
    if not isinstance(target, str) or not any(p['user_name'] == target for p in lobby['players']):
        return _host_action_fail(reply_type, 'That player is not in the lobby.')
    if target == user_name:
        return _host_action_fail(reply_type, 'You are already the host.')
    if target not in _connected_names(lobby):
        return _host_action_fail(reply_type, f'{target} is not connected.')
    if lobby['started'] and _power_of(lobby, target) is None:
        return _host_action_fail(reply_type, 'During a game the host must control a Great Power.')
    lobby['host'] = target
    payload = {'type': 'lobby_update', 'event': 'host_changed', 'user_name': target,
               'previous_host': user_name, **_snapshot(lobby)}
    return _host_action_ok(reply_type, payload)

def _assign_power(lobby, user_name, msg):
    """Gives a vacant power to a spectator in a running game."""
    reply_type = 'assign_power_result'
    target, power = msg.get('user_name'), msg.get('power')
    if lobby['host'] != user_name:
        return _host_action_fail(reply_type, 'Only the host can assign powers.')
    if lobby['id'] not in _lobby_games:
        return _host_action_fail(reply_type, 'The game has not started.')
    member = next((p for p in lobby['players'] if p['user_name'] == target), None)
    if member is None:
        return _host_action_fail(reply_type, 'That player is not in the lobby.')
    if member['selected_power'] != SPECTATOR_POWER:
        return _host_action_fail(reply_type, f'{target} already controls {member["selected_power"]}.')
    if power not in _vacant_powers(lobby):
        return _host_action_fail(reply_type, 'That power is not vacant.')
    member['selected_power'] = power
    if target in lobby.get('eliminated', []):
        lobby['eliminated'].remove(target)
    payload = {'type': 'lobby_update', 'event': 'power_assigned', 'user_name': target, 'power': power,
               **_snapshot(lobby)}
    return _host_action_ok(reply_type, payload, views=_game_views(lobby))

def _set_accepting_joins(lobby, user_name, msg):
    reply_type = 'accepting_joins_result'
    if lobby['host'] != user_name:
        return _host_action_fail(reply_type, 'Only the host can change that.')
    lobby['accepting_joins'] = bool(msg.get('value'))
    closes = []
    if not lobby['accepting_joins']:
        # Anyone still waiting is turned away rather than left hanging.
        rejection = {'type': 'join_rejected', 'message': 'The host stopped accepting new players.'}
        for rid in list(lobby.get('join_requests', {})):
            lobby['join_requests'].pop(rid)
            waiter = _join_waiters.pop(rid, None)
            if waiter is not None:
                closes.append((waiter, rejection, JOIN_REJECTED_CLOSE_CODE))
    payload = {'type': 'lobby_update', 'event': 'joins_toggled', 'user_name': user_name, **_snapshot(lobby)}
    return _host_action_ok(reply_type, payload, closes=closes)

def _answer_join(lobby, user_name, msg):
    """decision is 'reject', 'spectator', or 'power' (with a vacant `power`)."""
    reply_type = 'join_answer_result'
    request_id, decision = msg.get('request_id'), msg.get('decision')
    if lobby['host'] != user_name:
        return _host_action_fail(reply_type, 'Only the host can answer join requests.')
    request = lobby.get('join_requests', {}).get(request_id) if isinstance(request_id, str) else None
    waiter = _join_waiters.get(request_id) if request is not None else None
    if waiter is None:
        return _host_action_fail(reply_type, 'That request is no longer waiting.')
    if decision not in ('reject', 'spectator', 'power'):
        return _host_action_fail(reply_type, 'Unknown decision.')
    joiner = request['user_name']

    if decision == 'reject':
        del lobby['join_requests'][request_id]
        del _join_waiters[request_id]
        payload = {'type': 'lobby_update', 'event': 'join_rejected', 'user_name': joiner, **_snapshot(lobby)}
        rejection = {'type': 'join_rejected', 'message': 'The host declined your request.'}
        return _host_action_ok(reply_type, payload, closes=[(waiter, rejection, JOIN_REJECTED_CLOSE_CODE)])

    if lobby['id'] not in _lobby_games:
        return _host_action_fail(reply_type, 'The game has not started.')
    if any(p['user_name'] == joiner for p in lobby['players']):
        return _host_action_fail(reply_type, f'Someone named {joiner} is already playing. Reject this request.')
    power = SPECTATOR_POWER
    if decision == 'power':
        power = msg.get('power')
        if power not in _vacant_powers(lobby):
            return _host_action_fail(reply_type, 'That power is not vacant.')

    secret_token = _get_player_token()
    lobby['players'].append({'user_name': joiner, 'selected_power': power, 'secret_token': secret_token})
    del lobby['join_requests'][request_id]
    del _join_waiters[request_id]
    accepted = {
        'type': 'join_accepted',
        'lobby_id': lobby['id'],
        'lobby_name': lobby['name'],
        'user_name': joiner,
        'secret_token': secret_token,
        'power': power,
        'map': lobby['settings']['map'],
    }
    payload = {'type': 'lobby_update', 'event': 'admitted', 'user_name': joiner, 'power': power, **_snapshot(lobby)}
    return _host_action_ok(reply_type, payload, closes=[(waiter, accepted, 1000)])

HOST_ACTIONS = {
    'kick_player': _kick_player,
    'transfer_host': _transfer_host,
    'assign_power': _assign_power,
    'set_accepting_joins': _set_accepting_joins,
    'answer_join': _answer_join,
}

async def _close_sockets(closes):
    for ws, message, code in closes:
        try:
            if message is not None:
                await ws.send_json(message)
            await ws.close(code=code)
        except Exception:
            pass  # already closed

async def _handle_message(lobby_id, user_name, raw):
    try:
        msg = json.loads(raw)
    except ValueError:
        return
    kind = msg.get('type') if isinstance(msg, dict) else None
    if kind not in ('set_map', 'set_power', 'start_game', 'load_saved_game', *GAME_REPLY_TYPES, *HOST_ACTIONS):
        return

    reply = None
    payload = None
    views = None
    closes = []
    with _lock:
        _, lobby = _find_lobby(lobby_id)
        if lobby is None:
            return
        if kind in HOST_ACTIONS:
            reply, payload, views, closes = HOST_ACTIONS[kind](lobby, user_name, msg)
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

    if closes:
        await _close_sockets(closes)
    if reply is not None:
        ws = _lobby_sockets.get(lobby_id, {}).get(user_name)
        if ws is not None:
            await ws.send_json(reply)
    if payload is not None:
        await _broadcast(lobby_id, payload)
    if views is not None:
        await _send_game_views(lobby_id, views)

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
        # The token proves who this is, so a new connection (refresh, page change, reconnect, another tab)
        # always takes over the seat from an older one.
        if is_member:
            sockets = _lobby_sockets.setdefault(lobby_id, {})
            replaced = sockets.get(user_name)
            sockets[user_name] = websocket
            snapshot = _snapshot(lobby)
            if lobby['id'] in _lobby_games:
                game_view = _view(lobby, _power_of(lobby, user_name), user_name)
    if lobby is None:
        await websocket.close(code=4404)
        return
    if not is_member:
        await websocket.close(code=4403)
        return
    if replaced is not None:
        try:
            await replaced.close(code=REPLACED_CLOSE_CODE)
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
                left = True  # deliberate exit: give up the seat right away
                break
            await _handle_message(lobby_id, user_name, raw)
    except WebSocketDisconnect:
        pass
    finally:
        snapshot = None
        was_current = False
        with _lock:
            sockets = _lobby_sockets.get(lobby_id, {})
            # A socket that was replaced or kicked is no longer the seat's connection, so its close means nothing.
            was_current = sockets.get(user_name) is websocket
            if was_current:
                del sockets[user_name]
            if not sockets:
                _lobby_sockets.pop(lobby_id, None)
            if was_current and left:
                snapshot = _remove_player(lobby_id, user_name)
        if was_current and left:
            if snapshot is not None:
                await _broadcast(lobby_id, {'type': 'lobby_update', 'event': 'left', 'user_name': user_name, **snapshot})
        elif was_current:
            _spawn(_after_disconnect(lobby_id, user_name))
        if left:
            try:
                await websocket.close()
            except Exception:
                pass  # already closed

@app.websocket('/ws/lobbies/{lobby_id}/requests/{request_id}')
async def join_request_socket(websocket: WebSocket, lobby_id: str, request_id: str):
    """Someone asking to join a running game waits here. The host's answer arrives as join_accepted (with the
    new seat's token) or join_rejected; the request expires if the host does not answer in time."""
    await websocket.accept()
    token = await _receive_token(websocket)

    with _lock:
        _, lobby = _find_lobby(lobby_id)
        request = lobby.get('join_requests', {}).get(request_id) if lobby is not None else None
        valid = (request is not None and token is not None
                 and secrets.compare_digest(request['token'].encode(), token.encode())
                 and request['expires'] > time.monotonic()
                 and request_id not in _join_waiters)
        if valid:
            _join_waiters[request_id] = websocket
            deadline = request['expires']
            payload = {'type': 'lobby_update', 'event': 'join_request', 'user_name': request['user_name'],
                       **_snapshot(lobby)}
    if not valid:
        try:
            await websocket.close(code=AUTH_FAILED_CLOSE_CODE if token is None else 4403)
        except Exception:
            pass
        return

    await _broadcast(lobby_id, payload)
    try:
        await websocket.send_json({'type': 'join_pending'})
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            await asyncio.wait_for(websocket.receive_text(), timeout=remaining)  # pings only
    except (asyncio.TimeoutError, WebSocketDisconnect, RuntimeError):
        pass
    finally:
        # The host answering removes the waiter first, so reaching here still registered means expiry or exit.
        payload = None
        with _lock:
            still_waiting = _join_waiters.get(request_id) is websocket
            if still_waiting:
                del _join_waiters[request_id]
                _, lobby = _find_lobby(lobby_id)
                if lobby is not None:
                    request = lobby.get('join_requests', {}).pop(request_id, None)
                    payload = {'type': 'lobby_update', 'event': 'join_request_closed',
                               'user_name': request['user_name'] if request else None, **_snapshot(lobby)}
        if still_waiting:
            try:
                await websocket.send_json({'type': 'join_rejected', 'message': 'The host did not answer in time.'})
                await websocket.close(code=JOIN_EXPIRED_CLOSE_CODE)
            except Exception:
                pass
            if payload is not None:
                await _broadcast(lobby_id, payload)

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