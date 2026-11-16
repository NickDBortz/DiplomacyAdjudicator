import asyncio
import json
from pathlib import Path

import app as server
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
