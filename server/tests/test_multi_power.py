import asyncio
import json
from pathlib import Path

import app as server
import pytest
from game import web_api
from game.enums import ARMY
from game.unit import Unit


MAP = str(
    Path(__file__).resolve().parents[1]
    / 'data'
    / 'maps'
    / 'classic_map'
    / 'classic_map.json'
)
VARIANT = '2_players_variant'
GROUP_A = ['England', 'France', 'Russia']
GROUP_B = ['Austria-Hungary', 'Germany', 'Turkey']
GROUP_A_NAME = ' / '.join(GROUP_A)
GROUP_B_NAME = ' / '.join(GROUP_B)


def new_game(phase='Spring'):
    return web_api.new_game(
        MAP,
        start_phase=phase,
        power_groups=[GROUP_A, GROUP_B],
    )


def make_lobby(game_id, players):
    return {
        'id': game_id,
        'host': players[0]['user_name'],
        'started': True,
        'players': players,
        'settings': {'map': 'classic_map'},
        'variant': VARIANT,
    }


def add_unit(game, power, territory):
    player = game.game_state.get_player(power)
    location = game.game_state.get_territory(territory)
    unit = Unit(player, ARMY, location)
    location.set_unit(unit)
    player.add_unit(unit)
    return unit


def clear_supply_centers_for(game, powers):
    powers = set(powers)
    for territory in game.game_state.territory_list:
        if territory.owner is not None and territory.owner.name in powers:
            territory.owner = None


def test_group_can_win_with_combined_supply_centers():
    game = new_game(phase='Fall')
    england = game.game_state.get_player('England')
    france = game.game_state.get_player('France')
    centers = [t for t in game.game_state.territory_list if t.is_supply_center][:18]

    for center in centers[:9]:
        center.owner = england
    for center in centers[9:]:
        center.owner = france

    assert len(england.get_supply_centers(game.game_state.territory_list)) < 18
    assert len(france.get_supply_centers(game.game_state.territory_list)) < 18

    game.adjudicator._check_for_winner()

    assert game.game_state.winner is england
    assert game.game_state.get_winner_name() == GROUP_A_NAME
    assert web_api.get_state(game)['winner'] == GROUP_A_NAME


def test_single_power_win_condition_is_unchanged():
    game = web_api.new_game(MAP, start_phase='Fall')
    england = game.game_state.get_player('England')
    centers = [t for t in game.game_state.territory_list if t.is_supply_center][:18]
    for center in centers:
        center.owner = england

    game.adjudicator._check_for_winner()

    assert game.game_state.winner is england
    assert game.game_state.get_winner_name() == 'England'


def test_group_order_submission_rejects_invalid_and_accepts_owned_order(monkeypatch):
    game = new_game()
    add_unit(game, 'France', 'PAR')
    add_unit(game, 'England', 'LON')
    lobby = make_lobby('multi-order', [
        {'user_name': 'Alice', 'selected_power': GROUP_A_NAME},
    ])
    monkeypatch.setitem(server._lobby_games, lobby['id'], game)

    view = server._view(lobby, GROUP_A_NAME, 'Alice')
    assert 'A PAR H' in view['valid_orders']
    assert 'A LON H' in view['valid_orders']

    rejected, _ = server._handle_game_message(
        lobby, 'Alice', 'submit_order',
        {'power': GROUP_A_NAME, 'order': 'A PAR - XXX'},
    )
    assert not rejected['ok']
    assert not game.game_state.queued_orders

    accepted, _ = server._handle_game_message(
        lobby, 'Alice', 'submit_order',
        {'power': GROUP_A_NAME, 'order': 'A PAR H'},
    )
    assert accepted['ok']
    assert len(game.game_state.queued_orders) == 1
    assert game.game_state.queued_orders[0].unit.owner.name == 'France'
    assert accepted['orders'][0]['territory'] == 'PAR'
    assert accepted['orders'][0]['owner'] == 'France'


def test_starting_group_variant_passes_groups_into_game(monkeypatch):
    class Socket:
        async def send_json(self, message):
            pass

    lobby = {
        'id': 'multi-start',
        'name': 'Grouped game',
        'host': 'Alice',
        'started': False,
        'ruleset': 'normal',
        'variant': VARIANT,
        'settings': {'map': 'classic_map'},
        'players': [
            {'user_name': 'Alice', 'selected_power': GROUP_A_NAME},
            {'user_name': 'Bob', 'selected_power': GROUP_B_NAME},
        ],
    }
    monkeypatch.setattr(server, '_lobbies', {'Grouped game': lobby})
    monkeypatch.setattr(server, '_lobby_games', {})
    monkeypatch.setitem(server._lobby_sockets, lobby['id'], {'Alice': Socket()})

    asyncio.run(server._handle_message(
        lobby['id'], 'Alice', json.dumps({'type': 'start_game', 'variant': VARIANT}),
    ))

    assert lobby['started']
    assert server._lobby_games[lobby['id']].game_state.power_groups == [GROUP_A, GROUP_B]


def test_group_draw_votes_use_power_objects_and_can_complete(monkeypatch):
    game = new_game()
    clear_supply_centers_for(game, GROUP_B)
    lobby = make_lobby('multi-draw', [
        {'user_name': 'Alice', 'selected_power': GROUP_A_NAME},
        {'user_name': 'Bob', 'selected_power': GROUP_B_NAME},
    ])
    monkeypatch.setitem(server._lobby_games, lobby['id'], game)

    voters = server._draw_voters(lobby, game)
    assert all(not isinstance(voter, str) for voter in voters)

    reply, _ = server._handle_game_message(
        lobby, 'Alice', 'draw', {'power': GROUP_A_NAME},
    )

    assert reply['ok']
    assert game.game_state.draw
    assert {player.name for player in game.game_state.draw_votes} == set(GROUP_A)


def test_leaving_group_removes_all_of_its_draw_votes(monkeypatch):
    game = new_game()
    lobby = make_lobby('multi-leave', [
        {'user_name': 'Alice', 'selected_power': GROUP_A_NAME},
        {'user_name': 'Bob', 'selected_power': 'Spectator'},
    ])
    game.game_state.draw_votes = [game.game_state.get_player(power) for power in GROUP_A]
    monkeypatch.setattr(server, '_lobbies', {'Game': lobby})
    monkeypatch.setitem(server._lobby_games, lobby['id'], game)

    server._remove_player(lobby['id'], 'Alice')

    assert not any(voter.name in GROUP_A for voter in game.game_state.draw_votes)


def test_group_is_vacant_while_any_power_in_it_remains_alive(monkeypatch):
    game = new_game()
    clear_supply_centers_for(game, ['England', 'Russia'])
    lobby = make_lobby('multi-vacant', [
        {'user_name': 'Alice', 'selected_power': GROUP_B_NAME},
        {'user_name': 'Sam', 'selected_power': 'Spectator'},
    ])
    monkeypatch.setitem(server._lobby_games, lobby['id'], game)

    assert GROUP_A_NAME in server._vacant_powers(lobby)
    reply, _, _, _ = server._assign_power(
        lobby, 'Alice', {'user_name': 'Sam', 'power': GROUP_A_NAME},
    )
    assert reply['ok']
    assert lobby['players'][1]['selected_power'] == GROUP_A_NAME


def test_group_save_restores_variant_powers_and_winner(monkeypatch):
    game = new_game()
    game.game_state.set_winner(game.game_state.get_player('England'), GROUP_A_NAME)
    save_data = {
        'format': 'diplomacy-game-save',
        'version': 1,
        'name': 'Grouped game',
        'map': 'classic_map',
        'variant': VARIANT,
        'players': [
            {'user_name': 'Alice', 'selected_power': GROUP_A_NAME},
            {'user_name': 'Bob', 'selected_power': GROUP_B_NAME},
        ],
        'game': web_api.serialize_game(game, 'classic_map'),
    }
    lobby = {
        'id': 'multi-save',
        'host': 'Alice',
        'players': [
            {'user_name': 'Alice', 'selected_power': None},
            {'user_name': 'Bob', 'selected_power': None},
        ],
        'settings': {'map': 'classic_map'},
        'variant': 'standard_variant',
    }
    monkeypatch.setitem(server._lobby_pending_games, lobby['id'], None)

    server._restore_lobby_game(lobby, save_data)

    restored = server._lobby_pending_games[lobby['id']]
    assert lobby['variant'] == VARIANT
    assert [player['selected_power'] for player in lobby['players']] == [
        GROUP_A_NAME, GROUP_B_NAME,
    ]
    assert restored.game_state.power_groups == [GROUP_A, GROUP_B]
    assert restored.game_state.get_winner_name() == GROUP_A_NAME


def test_added_power_ownership_builds_and_save_restore(monkeypatch):
    class Socket:
        async def send_json(self, message):
            pass

    variant = '8_players_variant'
    lobby = {
        'id': 'eight-player',
        'name': 'Eight player game',
        'host': 'Alice',
        'started': False,
        'variant': variant,
        'settings': {'map': 'classic_map'},
        'players': [{'user_name': 'Alice', 'selected_power': 'Ottoman Empire'}],
    }
    monkeypatch.setattr(server, '_lobbies', {'Eight player game': lobby})
    monkeypatch.setattr(server, '_lobby_games', {})
    monkeypatch.setattr(server, '_lobby_pending_games', {})
    monkeypatch.setitem(server._lobby_sockets, lobby['id'], {'Alice': Socket()})

    assert 'Ottoman Empire' in server._available_powers('classic_map', variant)
    assert server._snapshot(lobby)['power_colors']['Ottoman Empire'] == '#FFFFFF'
    asyncio.run(server._handle_message(lobby['id'], 'Alice', json.dumps({'type': 'start_game'})))

    assert lobby['started']
    game = server._lobby_games[lobby['id']]
    ottoman = game.game_state.get_player('Ottoman Empire')
    assert ottoman.color == '#FFFFFF'
    for abbr in ('RUM', 'BUL', 'SER', 'ALB', 'GRE'):
        territory = game.game_state.get_territory(abbr)
        assert territory.owner is ottoman
        assert territory.home_owner is ottoman
    view = server._view(lobby, 'Ottoman Empire', 'Alice')
    assert next(player for player in view['players'] if player['name'] == 'Ottoman Empire')['color'] == '#FFFFFF'
    assert {t['abbr'] for t in view['territories'] if t['owner'] == 'Ottoman Empire'} == {'RUM', 'BUL', 'SER', 'ALB', 'GRE'}
    assert 'Build A RUM' in view['valid_orders']
    assert server._handle_game_message(lobby, 'Alice', 'submit_order', {'power': 'Ottoman Empire', 'order': 'Build A RUM'})[0]['ok']
    game.adjudicator.resolve_orders()

    game.game_state.get_territory('BUL').owner = game.game_state.get_player('Turkey')
    saved = server._game_save_data(lobby)
    restored_lobby = make_lobby('eight-restored', [{'user_name': 'Alice', 'selected_power': None}])
    server._restore_lobby_game(restored_lobby, saved)
    restored = server._lobby_pending_games['eight-restored']
    ottoman = restored.game_state.get_player('Ottoman Empire')
    assert restored_lobby['players'][0]['selected_power'] == 'Ottoman Empire'
    assert restored.game_state.get_territory('BUL').owner.name == 'Turkey'
    assert restored.game_state.get_territory('BUL').home_owner is ottoman
    assert restored.game_state.get_territory('RUM').unit.owner is ottoman
    restored.game_state.get_territory('BUL').owner = ottoman
    restored.game_state.set_phase('Adjustment')
    assert 'Build A BUL' in web_api.get_valid_orders(restored, ottoman)


def test_variant_ownership_changes_and_invalid_references():
    variant = {
        'modify_ownership': [
            {'territory_name': 'Paris', 'new_owner': 'England'},
            {'territory_name': 'London', 'new_owner': ''},
        ],
    }
    game = web_api.new_game(MAP, variant=variant)
    assert game.game_state.get_territory('PAR').home_owner.name == 'England'
    assert game.game_state.get_territory('LON').home_owner is None
    assert web_api.new_game(MAP).game_state.get_territory('PAR').home_owner.name == 'France'
    for change in (
        {'territory_name': 'Unknown', 'new_owner': 'England'},
        {'territory_name': 'Paris', 'new_owner': 'Unknown'},
    ):
        with pytest.raises(ValueError, match='Unknown'):
            web_api.new_game(MAP, variant={'modify_ownership': [change]})
    with pytest.raises(ValueError, match='Duplicate power'):
        web_api.new_game(MAP, variant={'add_power': [{'name': 'FRANCE', 'color': '#000000'}]})


def test_added_power_color_in_running_groups():
    colors = server._power_colors('classic_map', '8_players_variant', [['Ottoman Empire', 'France']])
    assert colors['Ottoman Empire / France'] == '#bcd7e2'


def test_start_rejects_a_power_from_another_variant(monkeypatch):
    class Socket:
        def __init__(self):
            self.messages = []

        async def send_json(self, message):
            self.messages.append(message)

    lobby = {
        'id': 'wrong-variant', 'host': 'Alice', 'started': False,
        'variant': '8_players_variant', 'settings': {'map': 'classic_map'},
        'players': [{'user_name': 'Alice', 'selected_power': 'Ottoman Empire'}],
    }
    socket = Socket()
    monkeypatch.setattr(server, '_lobbies', {'Game': lobby})
    monkeypatch.setattr(server, '_lobby_games', {})
    monkeypatch.setattr(server, '_lobby_pending_games', {})
    monkeypatch.setitem(server._lobby_sockets, lobby['id'], {'Alice': socket})
    asyncio.run(server._handle_message(lobby['id'], 'Alice', json.dumps({
        'type': 'start_game', 'variant': 'standard_variant',
    })))
    assert not lobby['started']
    assert socket.messages[-1]['message'] == 'A selected Great Power is not available in this variant.'
