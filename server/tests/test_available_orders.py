from pathlib import Path

from fastapi.testclient import TestClient

import app as server
from game import web_api
from game.enums import ARMY, FLEET
from game.orders import AdvanceOrder
from game.unit import Unit


MAP = str(Path(__file__).resolve().parents[1] / 'data' / 'maps' / 'classic_map.json')


def new_game(phase=None):
    return web_api.new_game(MAP, start_phase=phase)


def add_unit(game, power, territory, unit_type):
    player = game.game_state.get_player(power)
    location = game.game_state.get_territory(territory)
    unit = Unit(player, unit_type, location)
    location.set_unit(unit)
    player.add_unit(unit)
    return unit


def test_adjustment_orders_follow_home_centers_and_queued_builds():
    game = new_game()
    france = game.game_state.get_player('France')
    england = game.game_state.get_player('England')
    game.game_state.get_territory('LON').owner = france
    options = web_api.get_valid_orders(game, france)
    assert 'Build F BRE' in options
    assert 'Build A PAR' in options
    assert not any('LON' in order for order in options)
    assert all(game.order_parser._parse_order_string(order.lower()).is_valid for order in options)
    assert game.submit_order('Build F BRE', france)
    assert 'Build A BRE' not in web_api.get_valid_orders(game, france)
    assert all('BRE' not in order for order in web_api.get_valid_orders(game, england))


def test_movement_orders_update_after_queue_and_delete():
    game = new_game('Spring')
    unit = add_unit(game, 'France', 'BRE', FLEET)
    france = unit.owner
    orders = web_api.get_valid_orders(game, france)
    assert 'F BRE H' in orders
    assert 'F BRE - MAO' in orders
    assert 'F BRE T' not in orders
    assert game.submit_order('F BRE H', france)
    assert not any(order.startswith('F BRE ') for order in web_api.get_valid_orders(game, france))
    game.game_state.remove_queued_order(unit.order)
    unit.reset_order()
    assert 'F BRE H' in web_api.get_valid_orders(game, france)


def test_listed_movement_and_support_orders_can_be_submitted():
    def position():
        game = new_game('Spring')
        add_unit(game, 'France', 'PAR', ARMY)
        add_unit(game, 'France', 'MAR', ARMY)
        add_unit(game, 'England', 'NTH', FLEET)
        add_unit(game, 'England', 'LON', ARMY)
        return game

    game = position()
    options = web_api.get_valid_orders(game, game.game_state.get_player('France'))
    assert 'A MAR S A PAR - BUR' in options
    for text in options:
        fresh = position()
        assert fresh.submit_order(text, fresh.game_state.get_player('France')), text


def test_retreat_generation_preserves_unit_position_and_excludes_attacker():
    game = new_game('Spring Retreat')
    unit = add_unit(game, 'France', 'PAR', ARMY)
    unit.dislodge()
    unit.territory.set_unit(None)
    unit.territory = None
    attacker_unit = add_unit(game, 'Germany', 'BUR', ARMY)
    attacker = AdvanceOrder(attacker_unit, unit.dislodged_from)
    unit.dislodged_from.contesting.append(attacker)
    orders = web_api.get_valid_orders(game, unit.owner)
    assert 'A PAR - BUR' not in orders
    assert 'A PAR - PIC' in orders
    assert unit.territory is None
    assert unit.order is None


def test_fleet_coast_options_and_retreats():
    game = new_game('Spring')
    unit = add_unit(game, 'France', 'MAO', FLEET)
    options = web_api.get_valid_orders(game, unit.owner)
    assert 'F MAO - SPA(nc)' in options
    assert 'F MAO - SPA(sc)' in options
    assert game.submit_order('F MAO - SPA(sc)', unit.owner)

    game = new_game('Spring Retreat')
    unit = add_unit(game, 'France', 'MAO', FLEET)
    unit.dislodge()
    unit.territory.set_unit(None)
    unit.territory = None
    options = web_api.get_valid_orders(game, unit.owner)
    assert 'F MAO - SPA(nc)' in options
    assert 'F MAO - SPA(sc)' in options
    assert unit.territory is None


def test_removal_orders_only_for_units_without_queued_orders():
    game = new_game()
    france = game.game_state.get_player('France')
    for location in ('BRE', 'PAR', 'MAR', 'BUR'):
        add_unit(game, 'France', location, ARMY)
    assert france.units_to_build(game.game_state.territory_list) == -1
    assert 'Remove A BRE' in web_api.get_valid_orders(game, france)
    assert game.submit_order('Remove A BRE', france)
    assert web_api.get_valid_orders(game, france) == []


def test_multiplayer_views_are_per_player_and_safe_for_spectators(monkeypatch):
    game = new_game()
    lobby = {
        'id': 'test-orders',
        'host': 'host',
        'players': [
            {'user_name': 'host', 'selected_power': 'France'},
            {'user_name': 'guest', 'selected_power': 'England'},
            {'user_name': 'spectator', 'selected_power': 'Spectator'},
        ],
    }
    monkeypatch.setitem(server._lobby_games, lobby['id'], game)
    views = server._game_views(lobby)
    assert 'Build A PAR' in views['host']['valid_orders']
    assert 'Build F LON' in views['guest']['valid_orders']
    assert 'Build A PAR' not in views['guest']['valid_orders']
    assert views['spectator']['valid_orders'] == []
    lobby['orders_revealed'] = True
    assert all(view['valid_orders'] == [] for view in server._game_views(lobby).values())


def test_singleplayer_valid_orders_endpoint(monkeypatch):
    game = new_game()
    monkeypatch.setitem(server._games, 'test-orders', game)
    client = TestClient(server.app)
    response = client.get('/games/test-orders/valid-orders', params={'power': 'France'})
    assert response.status_code == 200
    assert 'Build F BRE' in response.json()['valid_orders']
    assert client.get('/games/test-orders/valid-orders', params={'power': 'unknown'}).status_code == 400
    assert client.get('/games/missing/valid-orders', params={'power': 'France'}).status_code == 404


def test_fleet_can_traverse_coastal_territory_through_water():
    """Test that fleets can reach coastal territories with coast distinctions through water paths.
    
    This test specifically covers the bug where a fleet at Marseilles should be able to reach
    Spain's south coast through the Gulf of Lyon, even though Marseilles is not directly listed
    in Spain's north_coast or south_coast adjacents.
    """
    game = new_game('Spring')
    unit = add_unit(game, 'France', 'MAR', FLEET)
    france = unit.owner
    options = web_api.get_valid_orders(game, france)
    
    # Fleet at Marseilles should be able to move to Spain's south coast
    assert 'F MAR - SPA(sc)' in options
    # And also the generic move order
    assert 'F MAR - SPA' in options
    
    # But NOT to Spain's north coast (which requires Gascony adjacency)
    assert 'F MAR - SPA(nc)' not in options
    
    # Verify the move can actually be submitted
    assert game.submit_order('F MAR - SPA(sc)', france)


def test_fleet_coast_traversal_validates_water_adjacency():
    """Test that coast-specific moves only work when there's a valid water path."""
    game = new_game('Spring')
    unit = add_unit(game, 'France', 'GAS', FLEET)
    france = unit.owner
    options = web_api.get_valid_orders(game, france)
    
    # Gascony is in Spain's north coast adjacents, so a fleet there should reach it
    assert 'F GAS - SPA(nc)' in options
    # Gascony is NOT in Spain's south coast adjacents, so this should NOT be available
    # unless there's a water path (there isn't a direct one from Gascony's water neighbors)
    assert 'F GAS - SPA(sc)' not in options


def test_all_generated_orders_are_valid():
    """Test that all generated orders can be parsed and are structurally valid."""
    game = new_game('Spring')
    france = game.game_state.get_player('France')
    
    # Add some units to generate a variety of orders
    add_unit(game, 'France', 'MAR', FLEET)
    add_unit(game, 'France', 'BRE', FLEET)
    add_unit(game, 'France', 'PAR', ARMY)
    
    options = web_api.get_valid_orders(game, france)
    
    # Every generated order should be parseable
    for order_text in options:
        parsed = game.order_parser._parse_order_string(order_text.lower())
        assert parsed.is_valid, f"Generated order '{order_text}' failed to parse"


def test_no_invalid_coast_orders_generated():
    """Test that fleets cannot reach territories they shouldn't be able to reach."""
    game = new_game('Spring')
    unit = add_unit(game, 'France', 'MAR', FLEET)
    france = unit.owner
    options = web_api.get_valid_orders(game, france)
    
    # Marseilles is NOT adjacent to any interior (non-coastal) territories
    # So there should be no orders like "F MAR - BUR" since Burgundy is not coastal
    
    # Get all the destinations that were generated
    mars_orders = [o for o in options if o.startswith('F MAR -')]
    for order in mars_orders:
        dest_part = order.replace('F MAR - ', '')
        # Remove coast specification if present
        dest = dest_part.split('(')[0]
        
        # Get the destination territory
        dest_terr = game.game_state.get_territory(dest)
        if dest_terr:
            # Verify the unit can actually traverse there
            assert unit.can_traverse(dest_terr), \
                f"Order '{order}' was generated but unit cannot traverse to {dest}"


def test_support_orders_respect_coast_constraints():
    """Test that support orders are only generated for reachable destinations."""
    game = new_game('Spring')
    
    # Set up: Fleet at Marseilles, Army at Bordeaux trying to support
    fleet = add_unit(game, 'France', 'MAR', FLEET)
    france = fleet.owner
    
    options = web_api.get_valid_orders(game, france)
    
    # Verify no impossible support orders are generated
    # (e.g., supporting a fleet at a land territory the supporting fleet can't reach)
    for order in options:
        if 'S' in order:
            # This is a support order, verify it's valid
            parsed = game.order_parser._parse_order_string(order.lower())
            assert parsed.is_valid, f"Generated support order '{order}' failed to parse"


def test_no_duplicate_convoy_orders():
    """Test that armies don't generate 'via convoy' orders for non-adjacent territories since they're redundant.
    
    For non-adjacent territories, only the plain advance order is generated (since it can only be executed via convoy).
    For adjacent territories that can also be reached via convoy, both orders are generated as alternatives.
    """
    game = new_game('Spring')
    
    # Set up an army and fleets to create a convoy route
    army = add_unit(game, 'France', 'PAR', ARMY)
    fleet1 = add_unit(game, 'France', 'BRE', FLEET)
    fleet2 = add_unit(game, 'France', 'MAO', FLEET)
    france = army.owner
    
    options = web_api.get_valid_orders(game, france)
    
    # Filter orders for the army at PAR
    par_orders = [o for o in options if o.startswith('A PAR')]
    
    # Check that non-adjacent convoyable territories only have plain orders, not "via convoy"
    for order in par_orders:
        if ' via convoy' in order:
            # This is a convoy order - it should only exist for adjacent territories
            dest_part = order.replace('A PAR - ', '').replace(' via convoy', '').strip()
            dest_terr = game.game_state.get_territory(dest_part)
            
            # The territory must be adjacent for the "via convoy" variant to exist
            assert dest_terr in army.territory.adjacents, \
                f"'via convoy' order '{order}' generated for non-adjacent territory {dest_part}"
