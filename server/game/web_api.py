"""JSON-friendly helpers around Game for the HTTP API. Each takes an explicit Game."""
from game.game import Game
from game.enums import ARMY, FLEET, HOLD, ADVANCE, SUPPORT, CONVOY, TRANSFORM, BUILD, DISBAND


ALL_ORDERS = object()  # pass as get_state(power=...) to include every power's orders


def new_game(map_path='data/maps/classic_map.json', start_phase=None):
    kwargs = {'json_file': map_path, 'render': False}
    if start_phase is not None:
        kwargs['start_phase'] = start_phase
    return Game(**kwargs)


def _visible_orders(state, power):
    if power is ALL_ORDERS:
        return list(state.queued_orders)
    if power is None:
        return []
    return [o for o in state.queued_orders if o.unit.owner.name == power]


def _unit_json(unit):
    return {
        'type': 'A' if unit.type == ARMY else 'F',
        'owner': unit.owner.name,
        'territory': unit.territory.abbr if unit.territory else None,
        'coast': unit.territory.unit_coast if unit.territory else None,
        'dislodged': bool(unit.dislodged),
        'dislodged_from': unit.dislodged_from.abbr if unit.dislodged_from else None,
        'order': str(unit.order) if unit.order is not None else None,
    }


def get_state(game, power=ALL_ORDERS):
    """Game state as JSON-friendly dict; orders are limited to `power` (None means no orders)."""
    state = game.game_state
    units = []
    for player in state.player_list:
        for unit in player.units:
            if not unit.disbanded:
                units.append(_unit_json(unit))

    queued = _visible_orders(state, power)
    orders = []
    for order in queued:
        if order.type == HOLD:
            orders.append({'id': len(orders), 'type': HOLD, 'territory': order.unit_territory.abbr})
        elif order.type == ADVANCE:
            orders.append({'id': len(orders), 'type': ADVANCE, 'territory': (order.unit_territory or order.unit.dislodged_from).abbr, 'dest_territory': order.dest_territory.abbr, 'dest_coast': order.coast})
        elif order.type == CONVOY:
            orders.append({'id': len(orders), 'type': CONVOY, 'territory': order.unit_territory.abbr, 'start_territory': order.convoying_unit.territory.abbr, 'dest_territory': order.dest_territory.abbr})
        if order.type == TRANSFORM:
            orders.append({'id': len(orders), 'type': TRANSFORM, 'territory': order.unit_territory.abbr})
        if order.type == BUILD:
            orders.append({'id': len(orders), 'type': BUILD, 'territory': order.dest_territory.abbr})
        if order.type == DISBAND:
            orders.append({'id': len(orders), 'type': DISBAND, 'territory': order.unit_territory.abbr})

    for order in queued:
        if order.type == SUPPORT:
            found = False
            for i in range(len(orders)):
                o = orders[i]
                if order.supported_order.type == ADVANCE and o['type'] == ADVANCE and o['territory'] == order.supported_order.unit_territory.abbr and o['dest_territory'] == order.supported_order.dest_territory.abbr:
                    orders.append({'id': len(orders), 'type': SUPPORT, 'territory': order.unit_territory.abbr, 'supported_order_id': i})
                    found = True
                    break
                elif order.supported_order.type == HOLD and o['type'] != ADVANCE and o['territory'] == order.supported_order.unit_territory.abbr:
                    orders.append({'id': len(orders), 'type': SUPPORT, 'territory': order.unit_territory.abbr, 'supported_order_id': i})
                    found = True
                    break
            if not found:
                orders.append({'id': len(orders), 'type': SUPPORT, 'territory': order.unit_territory.abbr, 'supported_order_id': None})

    # Entries were appended non-support first, then supports, each in queue order.
    ordered = [o for o in queued if o.type != SUPPORT] + [o for o in queued if o.type == SUPPORT]
    for entry, order in zip(orders, ordered):
        entry['text'] = str(order)
        if order.type == SUPPORT:
            # Inlined so a support of another power's order can still be drawn without exposing that order.
            supported = order.supported_order
            supported_territory = supported.unit_territory or supported.unit.dislodged_from
            is_advance = supported.type == ADVANCE
            entry.update({
                'supported_type': supported.type,
                'supported_territory': supported_territory.abbr if supported_territory else None,
                'supported_dest': supported.dest_territory.abbr if is_advance else None,
                'supported_coast': supported.coast if is_advance else None,
            })
    
    return {
        'phase': state.get_phase(),
        'year': state.year,
        'winner': state.winner.name if state.winner else None,
        'draw': state.draw,
        'draw_votes': [p.name for p in state.draw_votes],
        'players': [
            {
                'name': p.name,
                'color': p.color,
                'supply_centers': p.get_supply_centers(state.territory_list),
                'units_to_build': p.units_to_build(state.territory_list),
            }
            for p in state.player_list
        ],
        'territories': [
            {
                'abbr': t.abbr,
                'name': t.name,
                'owner': t.owner.name if t.owner else None,
                'supply_center': t.is_supply_center
            }
            for t in state.territory_list
        ],
        'units': units,
        'orders': orders
    }

def submit_order(game, order, power):
    """Submit one order string for a power. Returns {ok, error}."""
    player = game.game_state.get_player(power)
    if player is None:
        return {'ok': False, 'error': f'Unknown power: {power}'}
    ok = game.submit_order(order, player)
    return {'ok': bool(ok), 'error': None if ok else 'Invalid order'}

def resolve(game):
    game.adjudicator.resolve_orders()
    return get_state(game)

def draw(game, power):
    player = game.game_state.get_player(power)
    game.game_state.vote_draw(player)
    return get_state(game)