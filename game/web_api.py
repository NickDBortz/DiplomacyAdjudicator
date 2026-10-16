"""JSON-friendly wrapper around Game for the browser (Pyodide) frontend.

All functions return JSON strings so they are easy to consume from JavaScript.
"""
import json

from game.game import Game
from game.enums import ARMY, FLEET

_game = None


def new_game(map_path='data/maps/classic_map.json', start_phase=None):
    global _game
    kwargs = {'json_file': map_path, 'render': False}
    if start_phase is not None:
        kwargs['start_phase'] = start_phase
    _game = Game(**kwargs)
    return get_state()


def _require_game():
    if _game is None:
        raise RuntimeError('No game in progress; call new_game() first')
    return _game


def _unit_json(unit):
    return {
        'type': 'A' if unit.type == ARMY else 'F',
        'owner': unit.owner.name,
        'territory': unit.territory.abbr if unit.territory else None,
        'dislodged': bool(unit.dislodged),
        'dislodged_from': unit.dislodged_from.abbr if unit.dislodged_from else None,
        'order': str(unit.order) if unit.order is not None else None,
    }


def get_state():
    game = _require_game()
    state = game.game_state
    units = []
    for player in state.player_list:
        for unit in player.units:
            if not unit.disbanded:
                units.append(_unit_json(unit))
    return json.dumps({
        'phase': state.get_phase(),
        'year': state.year,
        'winner': state.winner.name if state.winner else None,
        'draw': state.draw,
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
            }
            for t in state.territory_list
        ],
        'units': units,
    })


def submit_order(order, power):
    """Submit one order string for a power. Returns a JSON object {ok: bool}."""
    game = _require_game()
    player = game.game_state.get_player(power)
    if player is None:
        return json.dumps({'ok': False, 'error': f'Unknown power: {power}'})
    ok = game.submit_order(order, player)
    return json.dumps({'ok': bool(ok), 'error': None if ok else 'Invalid order'})


def resolve():
    game = _require_game()
    game.adjudicator.resolve_orders()
    return get_state()
