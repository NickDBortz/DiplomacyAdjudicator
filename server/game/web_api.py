"""JSON-friendly helpers around Game for the HTTP API. Each takes an explicit Game."""
from game.game import Game
from game.unit import Unit
from game.enums import ARMY, FLEET, HOLD, ADVANCE, SUPPORT, CONVOY, TRANSFORM, BUILD, DISBAND, ADJUSTMENT_PHASE, SPRING_RETREAT_PHASE, FALL_RETREAT_PHASE


ALL_ORDERS = object()  # pass as get_state(power=...) to include every power's orders


def get_valid_orders(game, player):
    """Return generated orders that can currently be submitted for this player."""
    state = game.game_state
    if player is None or state.winner is not None or state.draw:
        return []

    phase = state.get_phase()
    queued = [order for order in state.queued_orders if order.unit.owner == player]
    adjustment_count = player.units_to_build(state.territory_list) if phase == ADJUSTMENT_PHASE else 0
    queued_builds = [order for order in queued if order.type == BUILD]
    queued_removals = [order for order in queued if order.type == DISBAND]
    dislodged = game.adjudicator.gather_dislodged()
    positions = [(unit, unit.territory) for unit in dislodged]
    result = []
    seen = set()
    try:
        for text in game.order_generator.generate_valid_orders(player):
            if text in seen:
                continue
            order = game.order_parser._parse_order_string(text.lower())
            if order is None or not order.is_valid or order.unit.owner != player:
                continue
            if order.type == BUILD:
                if len(queued_builds) >= adjustment_count or any(
                    existing.dest_territory == order.dest_territory for existing in queued_builds
                ):
                    continue
            elif order.type == DISBAND and len(queued_removals) >= -adjustment_count:
                continue
            if phase in (SPRING_RETREAT_PHASE, FALL_RETREAT_PHASE):
                if order.type != ADVANCE or order.is_utilizing_convoy or order.unit not in dislodged:
                    continue
                if any(not attack.is_utilizing_convoy and attack.unit_territory == order.dest_territory
                       for attack in order.unit.dislodged_from.contesting):
                    continue
            seen.add(text)
            result.append((text, order))
    finally:
        for unit, territory in positions:
            unit.territory = territory
    # Keep parser-accepted shorthand out of the picker when explicit choices exist.
    specified_coasts = {
        (order.unit, order.dest_territory) for _, order in result
        if order.type == ADVANCE and order.unit.type == FLEET and order.coast is not None
    }
    return [
        text for text, order in result
        if not (order.type == ADVANCE and order.unit.type == FLEET and order.coast is None
                and (order.unit, order.dest_territory) in specified_coasts)
    ]


def new_game(map_path='data/maps/classic_map.json', start_phase=None, neutral_powers=None):
    kwargs = {'json_file': map_path, 'render': False}
    if start_phase is not None:
        kwargs['start_phase'] = start_phase
    if neutral_powers is not None:
        kwargs['neutral_powers'] = neutral_powers
    return Game(**kwargs)


def serialize_game(game, map_id):
    state = game.game_state
    return {
        'map': map_id,
        'phase': state.get_phase(),
        'year': state.year,
        'winner': state.winner.name if state.winner else None,
        'draw': state.draw,
        'draw_votes': [player.name for player in state.draw_votes],
        'territory_owners': {territory.abbr: territory.owner.name if territory.owner else None
                             for territory in state.territory_list},
        'units': [
            {
                'owner': player.name,
                'type': 'A' if unit.type == ARMY else 'F',
                'territory': unit.territory.abbr if unit.territory and not unit.dislodged else None,
                'coast': unit.territory.unit_coast if unit.territory and not unit.dislodged else None,
                'dislodged': bool(unit.dislodged),
                'dislodged_from': unit.dislodged_from.abbr if unit.dislodged_from else None,
            }
            for player in state.player_list
            for unit in player.units
            if not unit.disbanded
        ],
    }


def restore_game(data, map_path):
    game = new_game(map_path, start_phase=data['phase'])
    state = game.game_state
    territories = {territory.abbr: territory for territory in state.territory_list}

    for territory in state.territory_list:
        territory.unit = None
        territory.unit_coast = None
        territory.temp_unit = None
        territory.temp_coast = None
        owner_name = data['territory_owners'].get(territory.abbr)
        territory.owner = state.get_player(owner_name) if owner_name else None

    for player in state.player_list:
        player.units.clear()

    for saved_unit in data['units']:
        owner = state.get_player(saved_unit['owner'])
        unit_type = ARMY if saved_unit['type'] == 'A' else FLEET
        position = territories.get(saved_unit['territory']) if saved_unit['territory'] else None
        unit = Unit(owner, unit_type, position)
        unit.dislodged = bool(saved_unit['dislodged'])
        unit.dislodged_from = territories.get(saved_unit['dislodged_from']) if saved_unit['dislodged_from'] else None
        owner.add_unit(unit)
        if position is not None:
            position.set_unit(unit, saved_unit['coast'])

    for abbr, territory in territories.items():
        owner_name = data['territory_owners'].get(abbr)
        territory.owner = state.get_player(owner_name) if owner_name else None

    state.year = int(data['year'])
    state.winner = state.get_player(data['winner']) if data.get('winner') else None
    state.draw = bool(data.get('draw', False))
    state.draw_votes = [state.get_player(name) for name in data.get('draw_votes', [])]
    state.queued_orders.clear()
    return game


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

    if isinstance(power, str):
        queued = _visible_orders(state, power)
    else:
        queued = []
        for p in power:
            queued.extend(_visible_orders(state, p))
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
        entry['queue_id'] = next(i for i, queued_order in enumerate(state.queued_orders) if queued_order is order)
        entry['owner'] = order.unit.owner.name
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