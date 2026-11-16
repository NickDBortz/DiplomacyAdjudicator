import app as server
from game import web_api

from test_multi_power import GROUP_A, GROUP_A_NAME, GROUP_B, GROUP_B_NAME, MAP, add_unit, make_lobby


def create_lobby(monkeypatch, phase='Fall'):
    game = web_api.new_game(MAP, start_phase=phase, power_groups=[GROUP_A[:], GROUP_B[:]])
    lobby = make_lobby('coin-flip', [
        {'user_name': 'Alice', 'selected_power': GROUP_A_NAME},
        {'user_name': 'Bob', 'selected_power': GROUP_B_NAME},
        {'user_name': 'Sam', 'selected_power': 'Spectator'},
    ])
    lobby['name'] = 'Game'
    lobby['orders_revealed'] = True
    monkeypatch.setitem(server._lobby_games, lobby['id'], game)
    return lobby, game


def resolve(lobby):
    return server._handle_game_message(lobby, 'Alice', 'resolve', {})


def test_coin_flip_after_fall_allows_build_and_survives_leave_and_restore(monkeypatch):
    lobby, game = create_lobby(monkeypatch)
    monkeypatch.setattr(server.secrets, 'choice', lambda members: members[1])
    assert not game.game_state.get_player('Italy').units

    reply, views = resolve(lobby)

    group = GROUP_B_NAME + ' / Italy'
    assert reply['ok']
    assert lobby['players'][1]['selected_power'] == group
    assert game.game_state.power_groups == [GROUP_A, GROUP_B + ['Italy']]
    assert game.game_state.get_phase() == 'Adjustment'
    assert 'Build A ROM' in views['Bob']['valid_orders']
    assert 'Build A ROM' not in views['Alice']['valid_orders']
    assert 'Build A ROM' not in views['Sam']['valid_orders']
    order_reply, order_views = server._handle_game_message(
        lobby, 'Bob', 'submit_order', {'power': group, 'order': 'Build A ROM'},
    )
    assert order_reply['ok']
    assert order_views['Bob']['orders'][0]['owner'] == 'Italy'
    assert not order_views['Alice']['orders']

    monkeypatch.setattr(server, '_lobbies', {'Game': lobby})
    assert group in server.get_lobby_powers(lobby['id'])
    saved_assigned = reply['save_data']
    restored_players = make_lobby('restore-assigned', [
        {'user_name': 'Alice', 'selected_power': None},
        {'user_name': 'Bob', 'selected_power': None},
    ])
    server._restore_lobby_game(restored_players, saved_assigned)
    restored_game = server._lobby_pending_games[restored_players['id']]
    assert restored_players['players'][1]['selected_power'] == group
    assert restored_game.game_state.power_groups == [GROUP_A, GROUP_B + ['Italy']]

    server._remove_player(lobby['id'], 'Bob')
    assert group in server._vacant_powers(lobby)
    saved = server._game_save_data(lobby)
    restored_lobby = make_lobby('restore-coin', [
        {'user_name': 'Alice', 'selected_power': None},
    ])
    server._restore_lobby_game(restored_lobby, saved)
    restored = server._lobby_pending_games[restored_lobby['id']]
    assert restored.game_state.power_groups == [GROUP_A, GROUP_B + ['Italy']]
    assert restored_lobby['players'][0]['selected_power'] == GROUP_A_NAME


def test_save_before_flip_preserves_pending_assignment(monkeypatch):
    lobby, game = create_lobby(monkeypatch, 'Spring')
    saved = server._game_save_data(lobby)
    restored_lobby = make_lobby('restore-pending', [
        {'user_name': 'Alice', 'selected_power': None},
        {'user_name': 'Bob', 'selected_power': None},
    ])
    server._restore_lobby_game(restored_lobby, saved)
    restored = server._lobby_pending_games[restored_lobby['id']]
    restored.game_state.set_phase('Fall')
    restored_lobby['orders_revealed'] = True
    monkeypatch.setitem(server._lobby_games, restored_lobby['id'], restored)
    monkeypatch.setattr(server.secrets, 'choice', lambda members: members[0])

    reply, _ = resolve(restored_lobby)
    assert reply['ok']
    assert restored_lobby['players'][0]['selected_power'] == GROUP_A_NAME + ' / Italy'


def test_flip_waits_for_retreat_and_is_not_repeated(monkeypatch):
    lobby, game = create_lobby(monkeypatch)
    monkeypatch.setattr(server.secrets, 'choice', lambda members: members[0])
    add_unit(game, 'France', 'PAR')
    germany = game.game_state.get_player('Germany')
    add_unit(game, 'Germany', 'BUR')
    add_unit(game, 'Germany', 'PIC')
    assert game.submit_order('A BUR - PAR', germany)
    assert game.submit_order('A PIC S A BUR - PAR', germany)

    reply, _ = resolve(lobby)
    assert reply['ok']
    assert game.game_state.get_phase() == 'Fall Retreat'
    assert lobby['players'][0]['selected_power'] == GROUP_A_NAME

    lobby['orders_revealed'] = True
    reply, _ = resolve(lobby)
    assert reply['ok']
    assert lobby['players'][0]['selected_power'] == GROUP_A_NAME + ' / Italy'

    lobby['orders_revealed'] = True
    resolve(lobby)
    assert lobby['players'][0]['selected_power'] == GROUP_A_NAME + ' / Italy'


def test_each_power_is_assigned_independently_to_an_active_player(monkeypatch):
    lobby, game = create_lobby(monkeypatch)
    game.game_state.power_groups = [['England'], ['France']]
    lobby['players'][0]['selected_power'] = 'England'
    lobby['players'][1]['selected_power'] = 'France'
    monkeypatch.setattr(server, '_get_coin_flip_powers', lambda map_id, variant_id: ['Italy', 'Germany'])
    choices = iter([0, 1])

    def choose(members):
        assert [member['user_name'] for member in members] == ['Alice', 'Bob']
        return members[next(choices)]

    monkeypatch.setattr(server.secrets, 'choice', choose)
    reply, _ = resolve(lobby)
    assert reply['ok']
    assert lobby['players'][0]['selected_power'] == 'England / Italy'
    assert lobby['players'][1]['selected_power'] == 'France / Germany'


def test_missing_active_player_does_not_resolve_orders(monkeypatch):
    lobby, game = create_lobby(monkeypatch)
    for member in lobby['players']:
        member['selected_power'] = 'Spectator'

    reply, _ = resolve(lobby)
    assert not reply['ok']
    assert 'active player' in reply['error']
    assert game.game_state.get_phase() == 'Fall'


def test_flip_occurs_even_when_adjustment_is_skipped(monkeypatch):
    lobby, game = create_lobby(monkeypatch, 'Fall Retreat')
    for territory in game.game_state.territory_list:
        if territory.is_supply_center:
            territory.owner = None
    for power, location in [('England', 'LON'), ('Germany', 'BER')]:
        territory = game.game_state.get_territory(location)
        territory.owner = game.game_state.get_player(power)
        add_unit(game, power, location)
    monkeypatch.setattr(server.secrets, 'choice', lambda members: members[0])

    reply, _ = resolve(lobby)
    assert reply['ok']
    assert game.game_state.get_phase() == 'Spring'
    assert game.game_state.year == 1902
    assert lobby['players'][0]['selected_power'] == GROUP_A_NAME + ' / Italy'


def test_coin_flip_contributes_to_combined_victory(monkeypatch):
    lobby, game = create_lobby(monkeypatch)
    england = game.game_state.get_player('England')
    italy = game.game_state.get_player('Italy')
    centers = [territory for territory in game.game_state.territory_list if territory.is_supply_center]
    for center in centers:
        center.owner = None
    for center in centers[:17]:
        center.owner = england
    centers[17].owner = italy
    monkeypatch.setattr(server.secrets, 'choice', lambda members: members[0])

    reply, views = resolve(lobby)
    assert reply['ok']
    assert game.game_state.get_winner_name() == GROUP_A_NAME + ' / Italy'
    assert views['Alice']['winner'] == GROUP_A_NAME + ' / Italy'


def test_coin_flip_does_not_run_on_spring_or_initial_adjustment(monkeypatch):
    lobby, game = create_lobby(monkeypatch, 'Spring')
    monkeypatch.setattr(server.secrets, 'choice', lambda members: members[0])
    reply, _ = resolve(lobby)
    assert reply['ok']
    assert lobby['players'][0]['selected_power'] == GROUP_A_NAME
    assert game.game_state.power_groups == [GROUP_A, GROUP_B]
