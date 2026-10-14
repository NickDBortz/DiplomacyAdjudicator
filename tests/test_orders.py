from game.player import Player
from game.territory import Territory
from game.unit import Unit
from game.game import Game
import subprocess

passed = 0
count = 0
prefix = ''
test_num = 0

def assert_equal(text, actual, expected):
    assert actual == expected, text

def assert_not_equal(text, actual, not_expected):
    assert actual != not_expected, text

def run_test(test):
    global passed, count, prefix, test_num
    try:
        test()
        print(f'{prefix}{test_num}. {test.__name__} Passed!')
        passed += 1
    except Exception as e:
        print(f'{prefix}{test_num}. {test.__name__} Failed. {e}')
    count += 1
    test_num += 1

def get_empty_player(name):
    player = Player(name)
    assert_equal('Player Name', player.name, name)
    assert_equal('Player unit Count', len(player.units), 0)
    return player

def get_empty_territory(player_name, territory_name, territory_abbreviation, is_primary):
    player = get_empty_player(player_name)
    territory = Territory(territory_name, territory_abbreviation, is_primary, player)
    assert_equal('Territory Name', territory.name, territory_name)
    assert_equal('Territory Abbreviation', territory.abbr, territory_abbreviation)
    assert_equal('Territory Primary Flag', territory.is_supply_center, is_primary)
    assert_equal('Territory Owner', territory.owner, player)
    assert_equal('Territory unit', territory.unit, None)  
    assert_equal('Territory Adjacent Count', len(territory.adjacents), 0)  
    return player, territory

def get_army(player_name, territory_name, territory_abbreviation, is_primary):
    player, territory = get_empty_territory(player_name, territory_name, territory_abbreviation, is_primary)
    army = Unit(player, 'Army', territory)
    assert_equal('Army Owner', army.owner, player)
    assert_equal('Army Type', army.type, 'Army')
    assert_equal('Army Territory', army.territory, territory)
    assert_equal('Army order', army.order, None)
    return player, territory, army

def get_classic_map():
    return Game(start_phase='Spring', render=False, allow_transformations=True)

def add_army(territory, owner):
    assert territory is not None
    assert owner is not None

    unit = Unit(owner, 'Army', territory)
    territory.set_unit(unit)
    owner.add_unit(unit)
    return unit

def add_fleet(territory, owner, coast=None):
    assert territory is not None
    assert owner is not None

    unit = Unit(owner, 'Fleet', territory)
    territory.set_unit(unit, coast=coast)
    owner.add_unit(unit)
    return unit

# 6.A Basic Checks
# 6.A.1
def test_advance_not_neighbor():
    map = get_classic_map()
    unit = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    map.submit_order('F NTH - PIC')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

# 6.A.2
def test_move_army_to_sea():
    map = get_classic_map()
    unit = add_army(map.game_state.get_territory('LPL'), map.game_state.get_player('England'))
    map.submit_order('A LPL - IRI')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

# 6.A.3
def test_move_fleet_to_land():
    map = get_classic_map()
    unit = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    map.submit_order('F KIE - MUC')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

# 6.A.4
def test_move_to_own_territory():
    map = get_classic_map()
    unit = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    map.submit_order('F KIE - KIE')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

# 6.A.5
def test_move_to_own_territory_with_convoy():
    map = get_classic_map()
    english_unit1 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_unit2 = add_army(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    english_unit3 = add_army(map.game_state.get_territory('LPL'), map.game_state.get_player('England'))
    german_unit1 = add_fleet(map.game_state.get_territory('LON'), map.game_state.get_player('Germany'))
    german_unit2 = add_army(map.game_state.get_territory('WAL'), map.game_state.get_player('Germany'))

    map.submit_order('F NTH C A YOR - YOR')
    map.submit_order('A YOR - YOR')
    map.submit_order('A LPL S A YOR - YOR')
    map.submit_order('F LON - YOR')
    map.submit_order('A WAL S F LON - YOR')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    # English army's move is illegal. This makes Liverpool's support illegal
    # This allows the Germans to have the stronger force and dislodge the army in Yorkshire
    assert_equal('English Fleet Territory', english_unit1.territory, map.game_state.get_territory('NTH'))
    assert_not_equal('English Army 1 Territory', english_unit2.territory, map.game_state.get_territory('YOR'))
    assert_equal('English Army 2 Territory', english_unit3.territory, map.game_state.get_territory('LPL'))
    assert_equal('German Fleet Territory', german_unit1.territory, map.game_state.get_territory('YOR'))
    assert_equal('German Army Territory', german_unit2.territory, map.game_state.get_territory('WAL'))

# 6.A.6
def test_ordering_other_countrys_unit():
    map = get_classic_map()
    unit = add_fleet(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    map.submit_order('F LON - NTH', owner=map.game_state.get_player('Germany'))
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

# 6.A.7
def test_only_convoy_armies():
    map = get_classic_map()
    unit1 = add_fleet(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    unit2 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))

    map.submit_order('F LON - BEL')
    map.submit_order('F NTH C A LON - BEL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Fleet 1 Territory', unit1.territory, map.game_state.get_territory('LON'))
    assert_equal('Fleet 2 Territory', unit2.territory, map.game_state.get_territory('NTH'))

# 6.A.8
def test_support_hold_yourself_fails():
    map = get_classic_map()
    italian_army1 = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Italy'))
    italian_army2 = add_army(map.game_state.get_territory('TYR'), map.game_state.get_player('Italy'))
    austrian_fleet = add_fleet(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))

    map.submit_order('A VEN - TRI')
    map.submit_order('A TYR S A VEN - TRI')
    map.submit_order('F TRI S F TRI')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 2)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.game_state.get_territory('TRI'))
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.game_state.get_territory('TYR'))
    assert_not_equal('Austrian Fleet Territory', austrian_fleet.territory, map.game_state.get_territory('TRI'))

# 6.A.9
def test_fleets_must_follow_coast_if_not_sea():
    map = get_classic_map()
    italian_fleet = add_fleet(map.game_state.get_territory('ROM'), map.game_state.get_player('Italy'))
    map.submit_order('F ROM - VEN')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

# 6.A.10
def test_support_unreachable_territory_impossible():
    map = get_classic_map()
    austrian_army = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Austria-Hungary'))
    italian_fleet = add_fleet(map.game_state.get_territory('ROM'), map.game_state.get_player('Italy'))
    italian_army = add_army(map.game_state.get_territory('APU'), map.game_state.get_player('Italy'))

    map.submit_order('A VEN H')
    map.submit_order('F ROM S A APU - VEN')
    map.submit_order('A APU - VEN')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 2)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('VEN'))
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.game_state.get_territory('ROM'))
    assert_equal('Italian Army Territory', italian_army.territory, map.game_state.get_territory('APU'))

# 6.A.11
def test_simple_bounce():
    map = get_classic_map()
    austrian_army = add_army(map.game_state.get_territory('VIE'), map.game_state.get_player('Austria-Hungary'))
    italian_army = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Italy'))

    map.submit_order('A VIE - TYR')
    map.submit_order('A VEN - TYR')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 2)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('VIE'))
    assert_equal('Italian Army Territory', italian_army.territory, map.game_state.get_territory('VEN'))

# 6.A.12
def test_triple_bounce():
    map = get_classic_map()
    austrian_army = add_army(map.game_state.get_territory('VIE'), map.game_state.get_player('Austria-Hungary'))
    german_army = add_army(map.game_state.get_territory('MUC'), map.game_state.get_player('Germany'))
    italian_army = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Italy'))

    map.submit_order('A VIE - TYR')
    map.submit_order('A MUC - TYR')
    map.submit_order('A VEN - TYR')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('VIE'))
    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('MUC'))
    assert_equal('Italian Army Territory', italian_army.territory, map.game_state.get_territory('VEN'))

# 6.B Coastal Issues
# 6.B.1
def test_move_unspecified_coast_when_necessary():
    map = get_classic_map()
    french_fleet = add_fleet(map.game_state.get_territory('POR'), map.game_state.get_player('France'))

    map.submit_order('F POR - SPA')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

# 6.B.2
def test_move_unspecified_coast_when_not_necessary():
    map = get_classic_map()
    french_fleet = add_fleet(map.game_state.get_territory('GAS'), map.game_state.get_player('France'))

    map.submit_order('F GAS - SPA')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('SPA'))

# 6.B.3
def test_move_wrong_coast_when_not_necessary():
    map = get_classic_map()
    french_fleet = add_fleet(map.game_state.get_territory('GAS'), map.game_state.get_player('France'))

    map.submit_order('F GAS - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

# 6.B.4
def test_support_to_unreachable_coast_allowed():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.game_state.get_territory('GAS'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('MAR'), map.game_state.get_player('France'))
    italian_fleet = add_fleet(map.game_state.get_territory('WES'), map.game_state.get_player('Italy'))

    map.submit_order('F GAS - SPA(nc)')
    map.submit_order('F MAR S F GAS - SPA(nc)')
    map.submit_order('F WES - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('SPA'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('MAR'))
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.game_state.get_territory('WES'))

# 6.B.5
def test_support_from_unreachable_coast_not_allowed():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.game_state.get_territory('MAR'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('SPA'), map.game_state.get_player('France'), coast='nc')
    italian_fleet = add_fleet(map.game_state.get_territory('LYO'), map.game_state.get_player('Italy'))

    map.submit_order('F MAR - LYO')
    map.submit_order('F SPA S F MAR - LYO')
    map.submit_order('F LYO H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 2)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('MAR'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('SPA'))
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.game_state.get_territory('LYO'))

# 6.B.6
def test_support_cut_from_other_coast():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('IRI'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('NAO'), map.game_state.get_player('England'))
    french_fleet1 = add_fleet(map.game_state.get_territory('SPA'), map.game_state.get_player('France'), coast='nc')
    french_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))
    italian_fleet = add_fleet(map.game_state.get_territory('LYO'), map.game_state.get_player('Italy'))

    map.submit_order('F IRI S F NAO - MAO')
    map.submit_order('F NAO - MAO')
    map.submit_order('F SPA S F MAO H')
    map.submit_order('F MAO H')
    map.submit_order('F LYO - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('IRI'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('MAO'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('SPA'))
    assert_not_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('MAO'))
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.game_state.get_territory('LYO'))

# 6.B.7
def test_support_own_unit_with_unspecified_coast():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.game_state.get_territory('POR'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))
    italian_fleet1 = add_fleet(map.game_state.get_territory('LYO'), map.game_state.get_player('Italy'))
    italian_fleet2 = add_fleet(map.game_state.get_territory('WES'), map.game_state.get_player('Italy'))

    map.submit_order('F POR S F MAO - SPA')
    map.submit_order('F MAO - SPA(nc)')
    map.submit_order('F LYO S F WES - SPA(sc)')
    map.submit_order('F WES - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('POR'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('MAO'))
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.game_state.get_territory('LYO'))
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.game_state.get_territory('WES'))

# 6.B.8
def test_support_with_unspecified_coast_when_only_one_coast_possible():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.game_state.get_territory('POR'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('GAS'), map.game_state.get_player('France'))
    italian_fleet1 = add_fleet(map.game_state.get_territory('LYO'), map.game_state.get_player('Italy'))
    italian_fleet2 = add_fleet(map.game_state.get_territory('WES'), map.game_state.get_player('Italy'))

    map.submit_order('F POR S F GAS - SPA')
    map.submit_order('F GAS - SPA(nc)')
    map.submit_order('F LYO S F WES - SPA(sc)')
    map.submit_order('F WES - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('POR'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('GAS'))
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.game_state.get_territory('LYO'))
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.game_state.get_territory('WES'))

# 6.B.9
def test_support_with_wrong_coast():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.game_state.get_territory('POR'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))
    italian_fleet1 = add_fleet(map.game_state.get_territory('LYO'), map.game_state.get_player('Italy'))
    italian_fleet2 = add_fleet(map.game_state.get_territory('WES'), map.game_state.get_player('Italy'))

    map.submit_order('F POR S F MAO - SPA(nc)')
    map.submit_order('F MAO - SPA(sc)')
    map.submit_order('F LYO S F WES - SPA(sc)')
    map.submit_order('F WES - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('POR'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('MAO'))
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.game_state.get_territory('LYO'))
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.game_state.get_territory('SPA'))

# 6.B.10
# This assumes we allow specifying moves like F SPA(nc) - LYO. We don't allow coast specifications on start territory

# 6.B.11
def test_coast_cannot_be_ordered_to_change():
    map = get_classic_map()
    french_fleet = add_fleet(map.game_state.get_territory('SPA'), map.game_state.get_player('France'), coast='nc')

    map.submit_order('F SPA - LYO')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

# 6.B.12
def test_army_movement_with_coastal_specifications():
    map = get_classic_map()
    french_army = add_army(map.game_state.get_territory('GAS'), map.game_state.get_player('France'))

    map.submit_order('A GAS - SPA(nc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('SPA'))

# 6.B.13
def test_coastal_crawl_not_allowed():
    map = get_classic_map()
    turkish_fleet1 = add_fleet(map.game_state.get_territory('BUL'), map.game_state.get_player('Turkey'), coast='sc')
    turkish_fleet2 = add_fleet(map.game_state.get_territory('CON'), map.game_state.get_player('Turkey'))

    map.submit_order('F BUL - CON')
    map.submit_order('F CON - BUL(nc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 2)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Turkish Fleet 1 Territory', turkish_fleet1.territory, map.game_state.get_territory('BUL'))
    assert_equal('Turkish Fleet 2 Territory', turkish_fleet2.territory, map.game_state.get_territory('CON'))

# 6.B.14
def test_building_unspecified_coast():
    map = get_classic_map()
    map.submit_order('Build F STP')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

# 6.B.15
def test_support_foreign_unit_unspecified_coast():
    map = get_classic_map()
    french_fleet = add_fleet(map.game_state.get_territory('POR'), map.game_state.get_player('France'))
    english_fleet = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('England'))
    italian_fleet1 = add_fleet(map.game_state.get_territory('LYO'), map.game_state.get_player('Italy'))
    italian_fleet2 = add_fleet(map.game_state.get_territory('WES'), map.game_state.get_player('Italy'))

    map.submit_order('F POR S F MAO - SPA')
    map.submit_order('F MAO - SPA(nc)')
    map.submit_order('F LYO S F WES - SPA(sc)')
    map.submit_order('F WES - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('POR'))
    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('MAO'))
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.game_state.get_territory('LYO'))
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.game_state.get_territory('WES'))

# 6.C Circular Movement
# 6.C.1
def test_three_army_circular_movement():
    map = get_classic_map()
    turkish_fleet = add_fleet(map.game_state.get_territory('ANK'), map.game_state.get_player('Turkey'))
    turkish_army1 = add_army(map.game_state.get_territory('CON'), map.game_state.get_player('Turkey'))
    turkish_army2 = add_army(map.game_state.get_territory('SMY'), map.game_state.get_player('Turkey'))

    map.submit_order('F ANK - CON')
    map.submit_order('A CON - SMY')
    map.submit_order('A SMY - ANK')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('CON'))
    assert_equal('Turkish Army 1 Territory', turkish_army1.territory, map.game_state.get_territory('SMY'))
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.game_state.get_territory('ANK'))

# 6.C.2
def test_three_army_circular_movement_with_support():
    map = get_classic_map()
    turkish_fleet = add_fleet(map.game_state.get_territory('ANK'), map.game_state.get_player('Turkey'))
    turkish_army1 = add_army(map.game_state.get_territory('CON'), map.game_state.get_player('Turkey'))
    turkish_army2 = add_army(map.game_state.get_territory('SMY'), map.game_state.get_player('Turkey'))
    turkish_army3 = add_army(map.game_state.get_territory('BUL'), map.game_state.get_player('Turkey'))

    map.submit_order('F ANK - CON')
    map.submit_order('A CON - SMY')
    map.submit_order('A SMY - ANK')
    map.submit_order('A BUL S F ANK - CON') 
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('CON'))
    assert_equal('Turkish Army 1 Territory', turkish_army1.territory, map.game_state.get_territory('SMY'))
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.game_state.get_territory('ANK'))
    assert_equal('Turkish Army 3 Territory', turkish_army3.territory, map.game_state.get_territory('BUL'))

# 6.C.3
def test_disrupted_three_army_circular_movement():
    map = get_classic_map()
    turkish_fleet = add_fleet(map.game_state.get_territory('ANK'), map.game_state.get_player('Turkey'))
    turkish_army1 = add_army(map.game_state.get_territory('CON'), map.game_state.get_player('Turkey'))
    turkish_army2 = add_army(map.game_state.get_territory('SMY'), map.game_state.get_player('Turkey'))
    turkish_army3 = add_army(map.game_state.get_territory('BUL'), map.game_state.get_player('Turkey'))

    map.submit_order('F ANK - CON')
    map.submit_order('A CON - SMY')
    map.submit_order('A SMY - ANK')
    map.submit_order('A BUL - CON')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('ANK'))
    assert_equal('Turkish Army 1 Territory', turkish_army1.territory, map.game_state.get_territory('CON'))
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.game_state.get_territory('SMY'))
    assert_equal('Turkish Army 3 Territory', turkish_army3.territory, map.game_state.get_territory('BUL'))

# 6.C.4
def test_circular_movement_with_attacked_convoy():
    map = get_classic_map()
    austrian_army1 = add_army(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))
    austrian_army2 = add_army(map.game_state.get_territory('SER'), map.game_state.get_player('Austria-Hungary'))
    turkish_army = add_army(map.game_state.get_territory('BUL'), map.game_state.get_player('Turkey'))
    turkish_fleet1 = add_fleet(map.game_state.get_territory('AEG'), map.game_state.get_player('Turkey'))
    turkish_fleet2 = add_fleet(map.game_state.get_territory('ION'), map.game_state.get_player('Turkey'))
    turkish_fleet3 = add_fleet(map.game_state.get_territory('ADR'), map.game_state.get_player('Turkey'))
    italian_fleet = add_fleet(map.game_state.get_territory('NAP'), map.game_state.get_player('Italy'))

    map.submit_order('A TRI - SER')
    map.submit_order('A SER - BUL')
    map.submit_order('A BUL - TRI')
    map.submit_order('F AEG C A BUL - TRI')
    map.submit_order('F ION C A BUL - TRI')
    map.submit_order('F ADR C A BUL - TRI')
    map.submit_order('F NAP - ION')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 7)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.game_state.get_territory('SER'))
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.game_state.get_territory('BUL'))
    assert_equal('Turkish Army Territory', turkish_army.territory, map.game_state.get_territory('TRI'))
    assert_equal('Turkish Fleet 1 Territory', turkish_fleet1.territory, map.game_state.get_territory('AEG'))
    assert_equal('Turkish Fleet 2 Territory', turkish_fleet2.territory, map.game_state.get_territory('ION'))
    assert_equal('Turkish Fleet 3 Territory', turkish_fleet3.territory, map.game_state.get_territory('ADR'))
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.game_state.get_territory('NAP'))

# 6.C.5
def test_disrupted_circular_movement_dislodged_convoy():
    map = get_classic_map()
    austrian_army1 = add_army(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))
    austrian_army2 = add_army(map.game_state.get_territory('SER'), map.game_state.get_player('Austria-Hungary'))
    turkish_army = add_army(map.game_state.get_territory('BUL'), map.game_state.get_player('Turkey'))
    turkish_fleet1 = add_fleet(map.game_state.get_territory('AEG'), map.game_state.get_player('Turkey'))
    turkish_fleet2 = add_fleet(map.game_state.get_territory('ION'), map.game_state.get_player('Turkey'))
    turkish_fleet3 = add_fleet(map.game_state.get_territory('ADR'), map.game_state.get_player('Turkey'))
    italian_fleet1 = add_fleet(map.game_state.get_territory('NAP'), map.game_state.get_player('Italy'))
    italian_fleet2 = add_fleet(map.game_state.get_territory('TUN'), map.game_state.get_player('Italy'))

    map.submit_order('A TRI - SER')
    map.submit_order('A SER - BUL')
    map.submit_order('A BUL - TRI')
    map.submit_order('F AEG C A BUL - TRI')
    map.submit_order('F ION C A BUL - TRI')
    map.submit_order('F ADR C A BUL - TRI')
    map.submit_order('F NAP - ION')
    map.submit_order('F TUN S F NAP - ION')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 8)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.game_state.get_territory('TRI'))
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.game_state.get_territory('SER'))
    assert_equal('Turkish Army Territory', turkish_army.territory, map.game_state.get_territory('BUL'))
    assert_equal('Turkish Fleet 1 Territory', turkish_fleet1.territory, map.game_state.get_territory('AEG'))
    assert_not_equal('Turkish Fleet 2 Territory', turkish_fleet2.territory, map.game_state.get_territory('ION'))
    assert_equal('Turkish Fleet 3 Territory', turkish_fleet3.territory, map.game_state.get_territory('ADR'))
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.game_state.get_territory('ION'))
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.game_state.get_territory('TUN'))

# 6.C.6
def test_two_armies_two_convoys():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    french_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    french_army = add_army(map.game_state.get_territory('BEL'), map.game_state.get_player('France'))

    map.submit_order('F NTH C A LON - BEL')
    map.submit_order('A LON - BEL')
    map.submit_order('F ENG C A BEL - LON')
    map.submit_order('A BEL - LON')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('BEL'))
    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('LON'))

# 6.C.7
def test_disrupted_unit_swap():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    french_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    french_army1 = add_army(map.game_state.get_territory('BEL'), map.game_state.get_player('France'))
    french_army2 = add_army(map.game_state.get_territory('BUR'), map.game_state.get_player('France'))

    map.submit_order('F NTH C A LON - BEL')
    map.submit_order('A LON - BEL')
    map.submit_order('F ENG C A BEL - LON')
    map.submit_order('A BEL - LON')
    map.submit_order('A BUR - BEL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('LON'))
    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Army 1 Territory', french_army1.territory, map.game_state.get_territory('BEL'))
    assert_equal('French Army 2 Territory', french_army2.territory, map.game_state.get_territory('BUR'))

# 6.C.8
def test_no_self_dislodgement_in_disrupted_circular_movement():
    map = get_classic_map()
    turkish_fleet = add_fleet(map.game_state.get_territory('CON'), map.game_state.get_player('Turkey'))
    turkish_army1 = add_army(map.game_state.get_territory('BUL'), map.game_state.get_player('Turkey'))
    turkish_army2 = add_army(map.game_state.get_territory('SMY'), map.game_state.get_player('Turkey'))
    russian_fleet = add_fleet(map.game_state.get_territory('BLA'), map.game_state.get_player('Russia'))
    austrian_army = add_army(map.game_state.get_territory('SER'), map.game_state.get_player('Austria-Hungary'))

    map.submit_order('F CON - BLA')
    map.submit_order('A BUL - CON')
    map.submit_order('A SMY S A BUL - CON')
    map.submit_order('F BLA - BUL(nc)')
    map.submit_order('A SER - BUL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('CON'))
    assert_equal('Turkish Army 1 Territory', turkish_army1.territory, map.game_state.get_territory('BUL'))
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.game_state.get_territory('SMY'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('BLA'))
    assert_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('SER'))
    
# 6.C.9
def test_no_help_in_dislodgement_of_own_unit_in_disrupted_circular_movement():
    map = get_classic_map()
    turkish_fleet = add_fleet(map.game_state.get_territory('CON'), map.game_state.get_player('Turkey'))
    turkish_army = add_army(map.game_state.get_territory('SMY'), map.game_state.get_player('Turkey'))
    russian_fleet = add_fleet(map.game_state.get_territory('BLA'), map.game_state.get_player('Russia'))
    austrian_army1 = add_army(map.game_state.get_territory('SER'), map.game_state.get_player('Austria-Hungary'))
    austrian_army2 = add_army(map.game_state.get_territory('BUL'), map.game_state.get_player('Austria-Hungary'))

    map.submit_order('F CON - BLA')
    map.submit_order('A SMY S A BUL - CON')
    map.submit_order('F BLA - BUL(nc)')
    map.submit_order('A SER - BUL')
    map.submit_order('A BUL - CON')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('CON'))
    assert_equal('Turkish Army Territory', turkish_army.territory, map.game_state.get_territory('SMY'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('BLA'))
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.game_state.get_territory('SER'))
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.game_state.get_territory('BUL'))

# 6.D Supports and Dislodges
# 6.D.1
def test_supported_hold_can_prevent_dislodgement():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.game_state.get_territory('ADR'), map.game_state.get_player('Austria-Hungary'))
    austrian_army = add_army(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))
    italian_army1 = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Italy'))
    italian_army2 = add_army(map.game_state.get_territory('TYR'), map.game_state.get_player('Italy'))

    map.submit_order('F ADR S A TRI - VEN')
    map.submit_order('A TRI - VEN')
    map.submit_order('A VEN H')
    map.submit_order('A TYR S A VEN H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.game_state.get_territory('ADR'))
    assert_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('TRI'))
    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.game_state.get_territory('VEN'))
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.game_state.get_territory('TYR'))

# 6.D.2
def test_move_cuts_support_on_hold():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.game_state.get_territory('ADR'), map.game_state.get_player('Austria-Hungary'))
    austrian_army1 = add_army(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))
    austrian_army2 = add_army(map.game_state.get_territory('VIE'), map.game_state.get_player('Austria-Hungary'))
    italian_army1 = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Italy'))
    italian_army2 = add_army(map.game_state.get_territory('TYR'), map.game_state.get_player('Italy'))

    map.submit_order('F ADR S A TRI - VEN')
    map.submit_order('A TRI - VEN')
    map.submit_order('A VIE - TYR')
    map.submit_order('A VEN H')
    map.submit_order('A TYR S A VEN H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.game_state.get_territory('ADR'))
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.game_state.get_territory('VEN'))
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.game_state.get_territory('VIE'))
    assert_not_equal('Italian Army 1 Territory', italian_army1.territory, map.game_state.get_territory('VEN'))
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.game_state.get_territory('TYR'))

# 6.D.3
def test_move_cuts_support_on_move():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.game_state.get_territory('ADR'), map.game_state.get_player('Austria-Hungary'))
    austrian_army = add_army(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))
    italian_army = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Italy'))
    italian_fleet = add_fleet(map.game_state.get_territory('ION'), map.game_state.get_player('Italy'))

    map.submit_order('F ADR S A TRI - VEN')
    map.submit_order('A TRI - VEN')
    map.submit_order('A VEN H')
    map.submit_order('F ION - ADR')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.game_state.get_territory('ADR'))
    assert_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('TRI'))
    assert_equal('Italian Army Territory', italian_army.territory, map.game_state.get_territory('VEN'))
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.game_state.get_territory('ION'))

# 6.D.4
def test_support_to_hold_on_unit_supporting_hold_allowed():
    map = get_classic_map()
    german_army = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_fleet = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    russian_fleet = add_fleet(map.game_state.get_territory('BAL'), map.game_state.get_player('Russia'))
    russian_army = add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Russia'))

    map.submit_order('A BER S F KIE H')
    map.submit_order('F KIE S A BER H')
    map.submit_order('F BAL S A PRU - BER')
    map.submit_order('A PRU - BER')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('BER'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('KIE'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('BAL'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('PRU'))

# 6.D.5
def test_support_to_hold_on_unit_supporting_move_allowed():
    map = get_classic_map()
    german_army1 = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_fleet = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('MUC'), map.game_state.get_player('Germany'))
    russian_fleet = add_fleet(map.game_state.get_territory('BAL'), map.game_state.get_player('Russia'))
    russian_army = add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Russia'))

    map.submit_order('A BER S A MUC - SIL')
    map.submit_order('F KIE S A BER H')
    map.submit_order('A MUC - SIL')
    map.submit_order('F BAL S A PRU - BER')
    map.submit_order('A PRU - BER')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('BER'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('KIE'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('SIL'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('BAL'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('PRU'))

# 6.D.6
def test_support_to_hold_on_convoying_unit_allowed():
    map = get_classic_map()
    german_army = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_fleet1 = add_fleet(map.game_state.get_territory('BAL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('PRU'), map.game_state.get_player('Germany'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('LIV'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('BOT'), map.game_state.get_player('Russia'))

    map.submit_order('A BER - SWE')
    map.submit_order('F BAL C A BER - SWE')
    map.submit_order('F PRU S F BAL H')
    map.submit_order('F LIV - BAL')
    map.submit_order('F BOT S F LIV - BAL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('SWE'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('BAL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('PRU'))
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('LIV'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('BOT'))

# 6.D.7
def test_support_to_hold_on_moving_unit_not_allowed():
    map = get_classic_map()
    german_fleet1 = add_fleet(map.game_state.get_territory('BAL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('PRU'), map.game_state.get_player('Germany'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('LIV'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('BOT'), map.game_state.get_player('Russia'))
    russian_army = add_army(map.game_state.get_territory('FIN'), map.game_state.get_player('Russia'))

    map.submit_order('F BAL - SWE')
    map.submit_order('F PRU S F BAL H')
    map.submit_order('F LIV - BAL')
    map.submit_order('F BOT S F LIV - BAL')
    map.submit_order('A FIN - SWE')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_not_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('BAL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('PRU'))
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('BAL'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('BOT'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('FIN'))

# 6.D.8
def test_failed_convoy_cannot_receive_hold_support():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.game_state.get_territory('ION'), map.game_state.get_player('Austria-Hungary'))
    austrian_army1 = add_army(map.game_state.get_territory('SER'), map.game_state.get_player('Austria-Hungary'))
    austrian_army2 = add_army(map.game_state.get_territory('ALB'), map.game_state.get_player('Austria-Hungary'))
    turkish_army1 = add_army(map.game_state.get_territory('GRE'), map.game_state.get_player('Turkey'))
    turkish_army2 = add_army(map.game_state.get_territory('BUL'), map.game_state.get_player('Turkey'))

    map.submit_order('F ION H')
    map.submit_order('A SER S A ALB - GRE')
    map.submit_order('A ALB - GRE')
    map.submit_order('A GRE - NAP')
    map.submit_order('A BUL S A GRE H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.game_state.get_territory('ION'))
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.game_state.get_territory('SER'))
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.game_state.get_territory('GRE'))
    assert_not_equal('Turkish Army 1 Territory', turkish_army1.territory, map.game_state.get_territory('GRE'))
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.game_state.get_territory('BUL'))

# 6.D.9
def test_support_to_move_on_holding_unit_not_allowed():
    map = get_classic_map()
    italian_army1 = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Italy'))
    italian_army2 = add_army(map.game_state.get_territory('TYR'), map.game_state.get_player('Italy'))
    austrian_army1 = add_army(map.game_state.get_territory('ALB'), map.game_state.get_player('Austria-Hungary'))
    austrian_army2 = add_army(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))

    map.submit_order('A VEN - TRI')
    map.submit_order('A TYR S A VEN - TRI')
    map.submit_order('A ALB S A TRI - SER')
    map.submit_order('A TRI H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.game_state.get_territory('TRI'))
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.game_state.get_territory('TYR'))
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.game_state.get_territory('ALB'))
    assert_not_equal('Austrian Army 2 Territory', austrian_army2.territory, map.game_state.get_territory('TRI'))

# 6.D.10
def test_self_dislodgement_prohibited():
    map = get_classic_map()
    german_army1 = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_fleet = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('MUC'), map.game_state.get_player('Germany'))

    map.submit_order('A BER H')
    map.submit_order('F KIE - BER')
    map.submit_order('A MUC S F KIE - BER')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('BER'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('KIE'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('MUC'))

# 6.D.11
def test_no_self_dislodgement_of_returning_unit():
    map = get_classic_map()
    german_army1 = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_fleet = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('MUC'), map.game_state.get_player('Germany'))
    russian_army = add_army(map.game_state.get_territory('WAR'), map.game_state.get_player('Russia'))

    map.submit_order('A BER - PRU')
    map.submit_order('F KIE - BER')
    map.submit_order('A MUC S F KIE - BER')
    map.submit_order('A WAR - PRU')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('BER'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('KIE'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('MUC'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('WAR'))

# 6.D.12
def test_supporting_foreign_unit_to_dislodge_own_unit_prohibited():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))
    austrian_army = add_army(map.game_state.get_territory('VIE'), map.game_state.get_player('Austria-Hungary'))
    italian_army = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Italy'))

    map.submit_order('F TRI H')
    map.submit_order('A VIE S A VEN - TRI')
    map.submit_order('A VEN - TRI')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.game_state.get_territory('TRI'))
    assert_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('VIE'))
    assert_equal('Italian Army Territory', italian_army.territory, map.game_state.get_territory('VEN'))

# 6.D.13
def test_supporting_foreign_unit_to_dislodge_returning_own_unit_prohibited():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))
    austrian_army = add_army(map.game_state.get_territory('VIE'), map.game_state.get_player('Austria-Hungary'))
    italian_army = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Italy'))
    italian_fleet = add_fleet(map.game_state.get_territory('APU'), map.game_state.get_player('Italy'))

    map.submit_order('F TRI - ADR')
    map.submit_order('A VIE S A VEN - TRI')
    map.submit_order('A VEN - TRI')
    map.submit_order('F APU - ADR')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.game_state.get_territory('TRI'))
    assert_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('VIE'))
    assert_equal('Italian Army Territory', italian_army.territory, map.game_state.get_territory('VEN'))
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.game_state.get_territory('APU'))

# 6.D.14
def test_supporting_foreign_unit_not_enough_to_prevent_dislodgement():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))
    austrian_army = add_army(map.game_state.get_territory('VIE'), map.game_state.get_player('Austria-Hungary'))
    italian_army1 = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Italy'))
    italian_army2 = add_army(map.game_state.get_territory('TYR'), map.game_state.get_player('Italy'))
    italian_fleet = add_fleet(map.game_state.get_territory('ADR'), map.game_state.get_player('Italy'))

    map.submit_order('F TRI - ADR')
    map.submit_order('A VIE S A VEN - TRI')
    map.submit_order('A VEN - TRI')
    map.submit_order('A TYR S A VEN - TRI')
    map.submit_order('F ADR S A VEN - TRI')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('Austrian Fleet Territory', austrian_fleet.territory, map.game_state.get_territory('TRI'))
    assert_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('VIE'))
    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.game_state.get_territory('TRI'))
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.game_state.get_territory('TYR'))
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.game_state.get_territory('ADR'))

# 6.D.15
def test_defender_cannot_cut_support_for_attack_on_itself():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.game_state.get_territory('CON'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('BLA'), map.game_state.get_player('Russia'))
    turkish_fleet = add_fleet(map.game_state.get_territory('ANK'), map.game_state.get_player('Turkey'))

    map.submit_order('F CON S F BLA - ANK')
    map.submit_order('F BLA - ANK')
    map.submit_order('F ANK - CON')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('CON'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('ANK'))
    assert_not_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('ANK'))

# 6.D.16
def test_convoying_unit_dislodging_unit_of_same_power_allowed():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    french_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    french_army = add_army(map.game_state.get_territory('BEL'), map.game_state.get_player('France'))

    map.submit_order('A LON H')
    map.submit_order('F NTH C A BEL - LON')
    map.submit_order('F ENG S A BEL - LON')
    map.submit_order('A BEL - LON')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('English Army Territory', english_army.territory, map.game_state.get_territory('LON'))
    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('LON'))

# 6.D.17
def test_dislodgement_cuts_support():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.game_state.get_territory('CON'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('BLA'), map.game_state.get_player('Russia'))
    turkish_fleet = add_fleet(map.game_state.get_territory('ANK'), map.game_state.get_player('Turkey'))
    turkish_army1 = add_army(map.game_state.get_territory('SMY'), map.game_state.get_player('Turkey'))
    turkish_army2 = add_army(map.game_state.get_territory('ARM'), map.game_state.get_player('Turkey'))

    map.submit_order('F CON S F BLA - ANK')
    map.submit_order('F BLA - ANK')
    map.submit_order('F ANK - CON')
    map.submit_order('A SMY S F ANK - CON')
    map.submit_order('A ARM - ANK')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('CON'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('BLA'))
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('CON'))
    assert_equal('Turkish Army 1 Territory', turkish_army1.territory, map.game_state.get_territory('SMY'))
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.game_state.get_territory('ARM'))

# 6.D.18
def test_surviving_unit_will_sustain_support():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.game_state.get_territory('CON'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('BLA'), map.game_state.get_player('Russia'))
    russian_army = add_army(map.game_state.get_territory('BUL'), map.game_state.get_player('Russia'))
    turkish_fleet = add_fleet(map.game_state.get_territory('ANK'), map.game_state.get_player('Turkey'))
    turkish_army1 = add_army(map.game_state.get_territory('SMY'), map.game_state.get_player('Turkey'))
    turkish_army2 = add_army(map.game_state.get_territory('ARM'), map.game_state.get_player('Turkey'))

    map.submit_order('F CON S F BLA - ANK')
    map.submit_order('F BLA - ANK')
    map.submit_order('A BUL S F CON H')
    map.submit_order('F ANK - CON')
    map.submit_order('A SMY S F ANK - CON')
    map.submit_order('A ARM - ANK')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('CON'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('ANK'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('BUL'))
    assert_not_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('ANK'))
    assert_equal('Turkish Army 1 Territory', turkish_army1.territory, map.game_state.get_territory('SMY'))
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.game_state.get_territory('ARM'))

# 6.D.19
def test_even_when_surviving_is_in_alternative_way():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.game_state.get_territory('CON'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('BLA'), map.game_state.get_player('Russia'))
    russian_army = add_army(map.game_state.get_territory('SMY'), map.game_state.get_player('Russia'))
    turkish_fleet = add_fleet(map.game_state.get_territory('ANK'), map.game_state.get_player('Turkey'))

    map.submit_order('F CON S F BLA - ANK')
    map.submit_order('F BLA - ANK')
    map.submit_order('A SMY S F ANK - CON')
    map.submit_order('F ANK - CON')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('CON'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('ANK'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('SMY'))
    assert_not_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('ANK'))

# 6.D.20
def test_unit_cannot_cut_support_of_its_own_country():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    french_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))

    map.submit_order('F LON S F NTH - ENG')
    map.submit_order('F NTH - ENG')
    map.submit_order('A YOR - LON')
    map.submit_order('F ENG H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('LON'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('ENG'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('YOR'))
    assert_not_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('ENG'))

# 6.D.21
def test_dislodging_dows_not_cancel_a_support_cut():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))
    italian_army1 = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Italy'))
    italian_army2 = add_army(map.game_state.get_territory('TYR'), map.game_state.get_player('Italy'))
    german_army = add_army(map.game_state.get_territory('MUC'), map.game_state.get_player('Germany'))
    russian_army1 = add_army(map.game_state.get_territory('SIL'), map.game_state.get_player('Russia'))
    russian_army2 = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Russia'))

    map.submit_order('F TRI H')
    map.submit_order('A VEN - TRI')
    map.submit_order('A TYR S A VEN - TRI')
    map.submit_order('A MUC - TYR')
    map.submit_order('A SIL - MUC')
    map.submit_order('A BER S A SIL - MUC')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.game_state.get_territory('TRI'))
    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.game_state.get_territory('VEN'))
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.game_state.get_territory('TYR'))
    assert_not_equal('German Army Territory', german_army.territory, map.game_state.get_territory('MUC'))
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.game_state.get_territory('MUC'))
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.game_state.get_territory('BER'))

# 6.D.22
def test_impossible_fleet_move_cannot_be_supported():
    map = get_classic_map()
    german_fleet = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    german_army = add_army(map.game_state.get_territory('BUR'), map.game_state.get_player('Germany'))
    russian_army1 = add_army(map.game_state.get_territory('MUC'), map.game_state.get_player('Russia'))
    russian_army2 = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Russia'))

    map.submit_order('F KIE - MUC')
    map.submit_order('A BUR S F KIE - MUC')
    map.submit_order('A MUC - KIE')
    map.submit_order('A BER S A MUC - KIE')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('KIE'))
    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('BUR'))
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.game_state.get_territory('KIE'))
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.game_state.get_territory('BER'))

# 6.D.23
def test_impossible_coast_move_cannot_be_supported():
    map = get_classic_map()
    italian_fleet1 = add_fleet(map.game_state.get_territory('LYO'), map.game_state.get_player('Italy'))
    italian_fleet2 = add_fleet(map.game_state.get_territory('WES'), map.game_state.get_player('Italy'))
    french_fleet1 = add_fleet(map.game_state.get_territory('SPA'), map.game_state.get_player('France'), coast='nc')
    french_fleet2 = add_fleet(map.game_state.get_territory('MAR'), map.game_state.get_player('France'))

    map.submit_order('F LYO - SPA(sc)')
    map.submit_order('F WES S F LYO - SPA(sc)')
    map.submit_order('F SPA - LYO')
    map.submit_order('F MAR S F SPA - LYO')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.game_state.get_territory('SPA'))
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.game_state.get_territory('WES'))
    assert_not_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('SPA'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('MAR'))

# 6.D.24
def test_impossible_army_move_cannot_be_supported():
    map = get_classic_map()
    french_army = add_army(map.game_state.get_territory('MAR'), map.game_state.get_player('France'))
    french_fleet = add_fleet(map.game_state.get_territory('SPA'), map.game_state.get_player('France'), coast='sc')
    italian_fleet = add_fleet(map.game_state.get_territory('LYO'), map.game_state.get_player('Italy'))
    turkish_fleet1 = add_fleet(map.game_state.get_territory('TYS'), map.game_state.get_player('Turkey'))
    turkish_fleet2 = add_fleet(map.game_state.get_territory('WES'), map.game_state.get_player('Turkey'))

    map.submit_order('A MAR - LYO')
    map.submit_order('F SPA S A MAR - LYO')
    map.submit_order('F LYO H')
    map.submit_order('F TYS S F WES - LYO')
    map.submit_order('F WES - LYO')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Italian Fleet 1 Territory', french_army.territory, map.game_state.get_territory('MAR'))
    assert_equal('Italian Fleet 2 Territory', french_fleet.territory, map.game_state.get_territory('SPA'))
    assert_not_equal('French Fleet 1 Territory', italian_fleet.territory, map.game_state.get_territory('LYO'))
    assert_equal('French Fleet 2 Territory', turkish_fleet1.territory, map.game_state.get_territory('TYS'))
    assert_equal('French Fleet 2 Territory', turkish_fleet2.territory, map.game_state.get_territory('LYO'))

# 6.D.25
def test_failing_hold_support_can_be_supported():
    map = get_classic_map()
    german_army = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_fleet = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    russian_fleet = add_fleet(map.game_state.get_territory('BAL'), map.game_state.get_player('Russia'))
    russian_army = add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Russia'))

    map.submit_order('A BER S A PRU H')
    map.submit_order('F KIE S A BER H')
    map.submit_order('F BAL S A PRU - BER')
    map.submit_order('A PRU - BER')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('BER'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('KIE'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('BAL'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('PRU'))

# 6.D.26
def test_failing_move_support_can_be_supported():
    map = get_classic_map()
    german_army = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_fleet = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    russian_fleet = add_fleet(map.game_state.get_territory('BAL'), map.game_state.get_player('Russia'))
    russian_army = add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Russia'))

    map.submit_order('A BER S A PRU - SIL')
    map.submit_order('F KIE S A BER H')
    map.submit_order('F BAL S A PRU - BER')
    map.submit_order('A PRU - BER')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('BER'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('KIE'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('BAL'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('PRU'))

# 6.D.27
def test_failing_convoy_can_be_supported():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('SWE'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('DEN'), map.game_state.get_player('England'))
    german_army = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('BAL'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('PRU'), map.game_state.get_player('Russia'))

    map.submit_order('F SWE - BAL')
    map.submit_order('F DEN S F SWE - BAL')
    map.submit_order('A BER H')
    map.submit_order('F BAL C A BER - LIV')
    map.submit_order('F PRU S F BAL H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('SWE'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('DEN'))
    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('BER'))
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('BAL'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('PRU'))

# 6.D.28
def test_impossible_move_and_support():
    map = get_classic_map()
    austrian_army = add_army(map.game_state.get_territory('BUD'), map.game_state.get_player('Austria-Hungary'))
    russian_fleet = add_fleet(map.game_state.get_territory('RUM'), map.game_state.get_player('Russia'))
    turkish_fleet = add_fleet(map.game_state.get_territory('BLA'), map.game_state.get_player('Turkey'))
    turkish_army = add_army(map.game_state.get_territory('BUL'), map.game_state.get_player('Turkey'))

    map.submit_order('A BUD S F RUM H')
    map.submit_order('F RUM - HOL')
    map.submit_order('F BLA - RUM')
    map.submit_order('A BUL S F BLA - RUM')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('BUD'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('RUM'))
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('BLA'))
    assert_equal('Turkish Army Territory', turkish_army.territory, map.game_state.get_territory('BUL'))

# 6.D.29
def test_move_to_impossible_coast_and_support():
    map = get_classic_map()
    austrian_army = add_army(map.game_state.get_territory('BUD'), map.game_state.get_player('Austria-Hungary'))
    russian_fleet = add_fleet(map.game_state.get_territory('RUM'), map.game_state.get_player('Russia'))
    turkish_fleet = add_fleet(map.game_state.get_territory('BLA'), map.game_state.get_player('Turkey'))
    turkish_army = add_army(map.game_state.get_territory('BUL'), map.game_state.get_player('Turkey'))

    map.submit_order('A BUD S F RUM H')
    map.submit_order('F RUM - BUL(sc)')
    map.submit_order('F BLA - RUM')
    map.submit_order('A BUL S F BLA - RUM')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('BUD'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('RUM'))
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('BLA'))
    assert_equal('Turkish Army Territory', turkish_army.territory, map.game_state.get_territory('BUL'))

# 6.D.30
def test_move_without_coast_and_support():
    map = get_classic_map()
    italian_fleet = add_fleet(map.game_state.get_territory('AEG'), map.game_state.get_player('Italy'))
    russian_fleet = add_fleet(map.game_state.get_territory('CON'), map.game_state.get_player('Russia'))
    turkish_fleet = add_fleet(map.game_state.get_territory('BLA'), map.game_state.get_player('Turkey'))
    turkish_army = add_army(map.game_state.get_territory('BUL'), map.game_state.get_player('Turkey'))

    map.submit_order('F AEG S F CON H')
    map.submit_order('F CON - BUL')
    map.submit_order('F BLA - CON')
    map.submit_order('A BUL S F BLA - CON')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.game_state.get_territory('AEG'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('CON'))
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('BLA'))
    assert_equal('Turkish Army Territory', turkish_army.territory, map.game_state.get_territory('BUL'))

# 6.D.31
def test_tricky_impossible_support():
    map = get_classic_map()
    austrian_army = add_army(map.game_state.get_territory('RUM'), map.game_state.get_player('Austria-Hungary'))
    turkish_fleet = add_fleet(map.game_state.get_territory('BLA'), map.game_state.get_player('Turkey'))

    map.submit_order('A RUM - ARM')
    map.submit_order('F BLA S A RUM - ARM')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('RUM'))
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('BLA'))

# 6.D.32
def test_missing_fleet():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('EDI'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LPL'), map.game_state.get_player('England'))
    french_fleet = add_fleet(map.game_state.get_territory('LON'), map.game_state.get_player('France'))
    german_army = add_army(map.game_state.get_territory('YOR'), map.game_state.get_player('Germany'))

    map.submit_order('F EDI S A LPL - YOR')
    map.submit_order('A LPL - YOR')
    map.submit_order('F LON S A YOR H')
    map.submit_order('A YOR - HOL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('EDI'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('LPL'))
    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('LON'))
    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('YOR'))

# 6.D.33
def test_unwanted_support_allowed():
    map = get_classic_map()
    austrian_army1 = add_army(map.game_state.get_territory('SER'), map.game_state.get_player('Austria-Hungary'))
    austrian_army2 = add_army(map.game_state.get_territory('VIE'), map.game_state.get_player('Austria-Hungary'))
    russian_army = add_army(map.game_state.get_territory('GAL'), map.game_state.get_player('Russia'))
    turkish_army = add_army(map.game_state.get_territory('BUL'), map.game_state.get_player('Turkey'))

    map.submit_order('A SER - BUD')
    map.submit_order('A VIE - BUD')
    map.submit_order('A GAL S A SER - BUD')
    map.submit_order('A BUL - SER')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.game_state.get_territory('BUD'))
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.game_state.get_territory('VIE'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('GAL'))
    assert_equal('Turkish Army Territory', turkish_army.territory, map.game_state.get_territory('SER'))

# 6.D.34
def test_support_targeting_own_area_not_allowed():
    map = get_classic_map()
    german_army1 = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('SIL'), map.game_state.get_player('Germany'))
    german_fleet = add_fleet(map.game_state.get_territory('BAL'), map.game_state.get_player('Germany'))
    italian_army = add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Italy'))
    russian_army1 = add_army(map.game_state.get_territory('WAR'), map.game_state.get_player('Russia'))
    russian_army2 = add_army(map.game_state.get_territory('LIV'), map.game_state.get_player('Russia'))

    map.submit_order('A BER - PRU')
    map.submit_order('A SIL S A BER - PRU')
    map.submit_order('F BAL S A BER - PRU')
    map.submit_order('A PRU S A LIV - PRU')
    map.submit_order('A WAR S A LIV - PRU')
    map.submit_order('A LIV - PRU')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Army 1 Territory', german_army1.territory, map.game_state.get_territory('PRU'))
    assert_equal('Austrian Army 2 Territory', german_army2.territory, map.game_state.get_territory('SIL'))
    assert_equal('Russian Army Territory', german_fleet.territory, map.game_state.get_territory('BAL'))
    assert_not_equal('Turkish Army Territory', italian_army.territory, map.game_state.get_territory('PRU'))
    assert_equal('Turkish Army Territory', russian_army1.territory, map.game_state.get_territory('WAR'))
    assert_equal('Turkish Army Territory', russian_army2.territory, map.game_state.get_territory('LIV'))

# 6.E Head-to-Head Battles and Beleaguered Garrison
# 6.E.1
def test_dislodged_unit_has_no_effect_on_attackers_area():
    map = get_classic_map()
    german_army1 = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_fleet = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('SIL'), map.game_state.get_player('Germany'))
    russian_army = add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Russia'))

    map.submit_order('A BER - PRU')
    map.submit_order('F KIE - BER')
    map.submit_order('A SIL S A BER - PRU')
    map.submit_order('A PRU - BER')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('PRU'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('BER'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('SIL'))
    assert_not_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('PRU'))

# 6.E.2
def test_no_self_dislodgement_in_head_to_head_battle():
    map = get_classic_map()
    german_army1 = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_fleet = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('MUC'), map.game_state.get_player('Germany'))

    map.submit_order('A BER - KIE')
    map.submit_order('F KIE - BER')
    map.submit_order('A MUC S A BER - KIE')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('BER'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('KIE'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('MUC'))

# 6.E.3
def test_no_help_in_dislodging_own_unit():
    map = get_classic_map()
    german_army1 = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('MUC'), map.game_state.get_player('Germany'))
    english_fleet = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('England'))

    map.submit_order('A BER - KIE')
    map.submit_order('A MUC S F KIE - BER')
    map.submit_order('F KIE - BER')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('BER'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('MUC'))
    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('KIE'))

# 6.E.4
def test_non_dislodged_loser_still_has_effect():
    map = get_classic_map()
    german_fleet1 = add_fleet(map.game_state.get_territory('HOL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('Germany'))
    german_fleet3 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Germany'))
    french_fleet1 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('BEL'), map.game_state.get_player('France'))
    english_fleet1 = add_fleet(map.game_state.get_territory('EDI'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    english_fleet3 = add_fleet(map.game_state.get_territory('NWG'), map.game_state.get_player('England'))
    austrian_army1 = add_army(map.game_state.get_territory('KIE'), map.game_state.get_player('Austria-Hungary'))
    austrian_army2 = add_army(map.game_state.get_territory('RUH'), map.game_state.get_player('Austria-Hungary'))

    map.submit_order('F HOL - NTH')
    map.submit_order('F HEL S F HOL - NTH')
    map.submit_order('F SKA S F HOL - NTH')
    map.submit_order('F NTH - HOL')
    map.submit_order('F BEL S F NTH - HOL')
    map.submit_order('F EDI S F NWG - NTH')
    map.submit_order('F YOR S F NWG - NTH')
    map.submit_order('F NWG - NTH')
    map.submit_order('A KIE S A RUH - HOL')
    map.submit_order('A RUH - HOL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 10)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('HOL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('HEL'))
    assert_equal('German Fleet 3 Territory', german_fleet3.territory, map.game_state.get_territory('SKA'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('NTH'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('BEL'))
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('EDI'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('YOR'))
    assert_equal('English Fleet 3 Territory', english_fleet3.territory, map.game_state.get_territory('NWG'))
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.game_state.get_territory('KIE'))
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.game_state.get_territory('RUH'))

# 6.E.5
def test_loser_dislodged_by_another_army_still_has_effect():
    map = get_classic_map()
    german_fleet1 = add_fleet(map.game_state.get_territory('HOL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('Germany'))
    german_fleet3 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Germany'))
    french_fleet1 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('BEL'), map.game_state.get_player('France'))
    english_fleet1 = add_fleet(map.game_state.get_territory('EDI'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    english_fleet3 = add_fleet(map.game_state.get_territory('NWG'), map.game_state.get_player('England'))
    english_fleet4 = add_fleet(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    austrian_army1 = add_army(map.game_state.get_territory('KIE'), map.game_state.get_player('Austria-Hungary'))
    austrian_army2 = add_army(map.game_state.get_territory('RUH'), map.game_state.get_player('Austria-Hungary'))

    map.submit_order('F HOL - NTH')
    map.submit_order('F HEL S F HOL - NTH')
    map.submit_order('F SKA S F HOL - NTH')
    map.submit_order('F NTH - HOL')
    map.submit_order('F BEL S F NTH - HOL')
    map.submit_order('F EDI S F NWG - NTH')
    map.submit_order('F YOR S F NWG - NTH')
    map.submit_order('F NWG - NTH')
    map.submit_order('F LON S F NWG - NTH')
    map.submit_order('A KIE S A RUH - HOL')
    map.submit_order('A RUH - HOL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 11)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('HOL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('HEL'))
    assert_equal('German Fleet 3 Territory', german_fleet3.territory, map.game_state.get_territory('SKA'))
    assert_not_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('NTH'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('BEL'))
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('EDI'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('YOR'))
    assert_equal('English Fleet 3 Territory', english_fleet3.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Fleet 4 Territory', english_fleet4.territory, map.game_state.get_territory('LON'))
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.game_state.get_territory('KIE'))
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.game_state.get_territory('RUH'))

# 6.E.6
def test_not_dislodge_because_of_own_support_still_in_effect():
    map = get_classic_map()
    german_fleet1 = add_fleet(map.game_state.get_territory('HOL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('Germany'))
    french_fleet1 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('BEL'), map.game_state.get_player('France'))
    french_fleet3 = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    austrian_army1 = add_army(map.game_state.get_territory('KIE'), map.game_state.get_player('Austria-Hungary'))
    austrian_army2 = add_army(map.game_state.get_territory('RUH'), map.game_state.get_player('Austria-Hungary'))

    map.submit_order('F HOL - NTH')
    map.submit_order('F HEL S F HOL - NTH')
    map.submit_order('F NTH - HOL')
    map.submit_order('F BEL S F NTH - HOL')
    map.submit_order('F ENG S F HOL - NTH')
    map.submit_order('A KIE S A RUH - HOL')
    map.submit_order('A RUH - HOL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 7)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('HOL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('HEL'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('NTH'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('BEL'))
    assert_equal('French Fleet 3 Territory', french_fleet3.territory, map.game_state.get_territory('ENG'))
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.game_state.get_territory('KIE'))
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.game_state.get_territory('RUH'))

# 6.E.7
def test_no_self_dislodgement_with_beleaguered_garrison():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    german_fleet1 = add_fleet(map.game_state.get_territory('HOL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('Germany'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('NWY'), map.game_state.get_player('Russia'))

    map.submit_order('F NTH H')
    map.submit_order('F YOR S F NWY - NTH')
    map.submit_order('F HOL S F HEL - NTH')
    map.submit_order('F HEL - NTH')
    map.submit_order('F SKA S F NWY - NTH')
    map.submit_order('F NWY - NTH')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('YOR'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('HOL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('HEL'))
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('SKA'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('NWY'))

# 6.E.8
def test_no_self_dislodgement_with_beleaguered_garrison_and_head_to_head_battle():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    german_fleet1 = add_fleet(map.game_state.get_territory('HOL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('Germany'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('NWY'), map.game_state.get_player('Russia'))

    map.submit_order('F NTH - NWY')
    map.submit_order('F YOR S F NWY - NTH')
    map.submit_order('F HOL S F HEL - NTH')
    map.submit_order('F HEL - NTH')
    map.submit_order('F SKA S F NWY - NTH')
    map.submit_order('F NWY - NTH')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('YOR'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('HOL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('HEL'))
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('SKA'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('NWY'))

# 6.E.9
def test_almost_self_dislodgement_with_beleaguered_garrison():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    german_fleet1 = add_fleet(map.game_state.get_territory('HOL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('Germany'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('NWY'), map.game_state.get_player('Russia'))

    map.submit_order('F NTH - NWG')
    map.submit_order('F YOR S F NWY - NTH')
    map.submit_order('F HOL S F HEL - NTH')
    map.submit_order('F HEL - NTH')
    map.submit_order('F SKA S F NWY - NTH')
    map.submit_order('F NWY - NTH')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('NWG'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('YOR'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('HOL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('HEL'))
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('SKA'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('NTH'))

# 6.E.10
def test_almost_circular_movement_with_no_self_dislodgement_with_beleaguered_garrison():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    german_fleet1 = add_fleet(map.game_state.get_territory('HOL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('Germany'))
    german_fleet3 = add_fleet(map.game_state.get_territory('DEN'), map.game_state.get_player('Germany'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('NWY'), map.game_state.get_player('Russia'))

    map.submit_order('F NTH - DEN')
    map.submit_order('F YOR S F NWY - NTH')
    map.submit_order('F HOL S F HEL - NTH')
    map.submit_order('F HEL - NTH')
    map.submit_order('F DEN - HEL')
    map.submit_order('F SKA S F NWY - NTH')
    map.submit_order('F NWY - NTH')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 7)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('YOR'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('HOL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('HEL'))
    assert_equal('German Fleet 3 Territory', german_fleet3.territory, map.game_state.get_territory('DEN'))
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('SKA'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('NWY'))

# 6.E.11
def test_no_self_dislodgement_with_beleaguered_garrison_unit_swap_with_adjacent_convoying_and_two_coasts():
    map = get_classic_map()
    french_army = add_army(map.game_state.get_territory('SPA'), map.game_state.get_player('France'))
    french_fleet1 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('LYO'), map.game_state.get_player('France'))
    german_army1 = add_army(map.game_state.get_territory('MAR'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('GAS'), map.game_state.get_player('Germany'))
    italian_fleet1 = add_fleet(map.game_state.get_territory('POR'), map.game_state.get_player('Italy'))
    italian_fleet2 = add_fleet(map.game_state.get_territory('WES'), map.game_state.get_player('Italy'))

    map.submit_order('A SPA - POR via convoy')
    map.submit_order('F MAO C A SPA - POR')
    map.submit_order('F LYO S F POR - SPA(nc)')
    map.submit_order('A MAR S A GAS - SPA')
    map.submit_order('A GAS - SPA')
    map.submit_order('F POR - SPA(nc)')
    map.submit_order('F WES S F POR - SPA(nc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 7)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('POR'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('MAO'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('LYO'))
    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('MAR'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('GAS'))
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.game_state.get_territory('SPA'))
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.game_state.get_territory('WES'))

# 6.E.12
def test_support_on_attack_on_own_unit_can_be_used_for_other_means():
    map = get_classic_map()
    austrian_army1 = add_army(map.game_state.get_territory('BUD'), map.game_state.get_player('Austria-Hungary'))
    austrian_army2 = add_army(map.game_state.get_territory('SER'), map.game_state.get_player('Austria-Hungary'))
    italian_army = add_army(map.game_state.get_territory('VIE'), map.game_state.get_player('Italy'))
    russian_army1 = add_army(map.game_state.get_territory('GAL'), map.game_state.get_player('Russia'))
    russian_army2 = add_army(map.game_state.get_territory('RUM'), map.game_state.get_player('Russia'))

    map.submit_order('A BUD - RUM')
    map.submit_order('A SER S A VIE - BUD')
    map.submit_order('A VIE - BUD')
    map.submit_order('A GAL - BUD')
    map.submit_order('A RUM S A GAL - BUD')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.game_state.get_territory('BUD'))
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.game_state.get_territory('SER'))
    assert_equal('Italian Army Territory', italian_army.territory, map.game_state.get_territory('VIE'))
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.game_state.get_territory('GAL'))
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.game_state.get_territory('RUM'))

# 6.E.13
def test_three_way_beleaguered_garrison():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('EDI'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    french_fleet1 = add_fleet(map.game_state.get_territory('BEL'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    german_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('Germany'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('NWG'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('NWY'), map.game_state.get_player('Russia'))

    map.submit_order('F EDI S F YOR - NTH')
    map.submit_order('F YOR - NTH')
    map.submit_order('F BEL - NTH')
    map.submit_order('F ENG S F BEL - NTH')
    map.submit_order('F NTH H')
    map.submit_order('F NWG - NTH')
    map.submit_order('F NWY S F NWG - NTH')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 7)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('EDI'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('YOR'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('BEL'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('ENG'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('NWG'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('NWY'))

# 6.E.14
def test_illegal_head_to_head_battle_can_still_defend():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('LPL'), map.game_state.get_player('England'))
    russian_fleet = add_fleet(map.game_state.get_territory('EDI'), map.game_state.get_player('Russia'))

    map.submit_order('A LPL - EDI')
    map.submit_order('F EDI - LPL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('LPL'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('EDI'))

# 6.E.15
def test_the_friendly_head_to_head_battle():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('HOL'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('RUH'), map.game_state.get_player('England'))
    french_army1 = add_army(map.game_state.get_territory('KIE'), map.game_state.get_player('France'))
    french_army2 = add_army(map.game_state.get_territory('MUC'), map.game_state.get_player('France'))
    french_army3 = add_army(map.game_state.get_territory('SIL'), map.game_state.get_player('France'))
    german_army = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_fleet1 = add_fleet(map.game_state.get_territory('DEN'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('Germany'))
    russian_fleet = add_fleet(map.game_state.get_territory('BAL'), map.game_state.get_player('Russia'))
    russian_army = add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Russia'))

    map.submit_order('F HOL S A RUH - KIE')
    map.submit_order('A RUH - KIE')
    map.submit_order('A KIE - BER')
    map.submit_order('A MUC S A KIE - BER')
    map.submit_order('A SIL S A KIE - BER')
    map.submit_order('A BER - KIE')
    map.submit_order('F DEN S A BER - KIE')
    map.submit_order('F HEL S A BER - KIE')
    map.submit_order('F BAL S A PRU - BER')
    map.submit_order('F PRU - BER')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 10)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('HOL'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('RUH'))
    assert_equal('French Army 1 Territory', french_army1.territory, map.game_state.get_territory('KIE'))
    assert_equal('French Army 2 Territory', french_army2.territory, map.game_state.get_territory('MUC'))
    assert_equal('French Army 3 Territory', french_army3.territory, map.game_state.get_territory('SIL'))
    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('BER'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('DEN'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('HEL'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('BAL'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('PRU'))

# 6.F Convoys
# 6.F.1
def test_no_convoy_in_coastal_areas():
    map = get_classic_map()
    turkish_army = add_army(map.game_state.get_territory('GRE'), map.game_state.get_player('Turkey'))
    turkish_fleet1 = add_fleet(map.game_state.get_territory('AEG'), map.game_state.get_player('Turkey'))
    turkish_fleet2 = add_fleet(map.game_state.get_territory('CON'), map.game_state.get_player('Turkey'))
    turkish_fleet3 = add_fleet(map.game_state.get_territory('BLA'), map.game_state.get_player('Turkey'))

    map.submit_order('A GRE - SEV')
    map.submit_order('F AEG C A GRE - SEV')
    map.submit_order('F CON C A GRE - SEV')
    map.submit_order('F BLA C A GRE - SEV')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Turkish Army Territory', turkish_army.territory, map.game_state.get_territory('GRE'))
    assert_equal('Turkish Fleet 1 Territory', turkish_fleet1.territory, map.game_state.get_territory('AEG'))
    assert_equal('Turkish Fleet 2 Territory', turkish_fleet2.territory, map.game_state.get_territory('CON'))
    assert_equal('Turkish Fleet 3 Territory', turkish_fleet3.territory, map.game_state.get_territory('BLA'))

# 6.F.2
def test_an_army_being_convoyed_can_bounce_as_normal():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    french_army = add_army(map.game_state.get_territory('PAR'), map.game_state.get_player('France'))

    map.submit_order('F ENG C A LON - BRE')
    map.submit_order('A LON - BRE')
    map.submit_order('A PAR - BRE')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('LON'))
    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('PAR'))

# 6.F.3
def test_an_army_being_convoyed_can_receive_support():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('England'))
    french_army = add_army(map.game_state.get_territory('PAR'), map.game_state.get_player('France'))

    map.submit_order('F ENG C A LON - BRE')
    map.submit_order('A LON - BRE')
    map.submit_order('F MAO S A LON - BRE')
    map.submit_order('A PAR - BRE')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('ENG'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('BRE'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('MAO'))
    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('PAR'))

# 6.F.4
def test_an_attacked_convoy_is_not_disrupted():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    german_fleet = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Germany'))

    map.submit_order('F NTH C A LON - HOL')
    map.submit_order('A LON - HOL')
    map.submit_order('F SKA - NTH')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('HOL'))
    assert_equal('French Army Territory', german_fleet.territory, map.game_state.get_territory('SKA'))

# 6.F.5
def test_beleaguered_convoy_is_not_disrupted():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    french_fleet1 = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('BEL'), map.game_state.get_player('France'))
    german_fleet1 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('DEN'), map.game_state.get_player('Germany'))

    map.submit_order('F NTH C A LON - HOL')
    map.submit_order('A LON - HOL')
    map.submit_order('F ENG - NTH')
    map.submit_order('F BEL S F ENG - NTH')
    map.submit_order('F SKA - NTH')
    map.submit_order('F DEN S F SKA - NTH')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('HOL'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('BEL'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('SKA'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('DEN'))

# 6.F.6
def test_dislodged_convoy_does_not_cut_support():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    german_army1 = add_army(map.game_state.get_territory('HOL'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('BEL'), map.game_state.get_player('Germany'))
    german_fleet1 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Germany'))
    french_army1 = add_army(map.game_state.get_territory('PIC'), map.game_state.get_player('France'))
    french_army2 = add_army(map.game_state.get_territory('BUR'), map.game_state.get_player('France'))

    map.submit_order('F NTH C A LON - HOL')
    map.submit_order('A LON - HOL')
    map.submit_order('A HOL S A BEL H')
    map.submit_order('A BEL S A HOL H')
    map.submit_order('F HEL S F SKA - NTH')
    map.submit_order('F SKA - NTH')
    map.submit_order('A PIC - BEL')
    map.submit_order('A BUR S A PIC - BEL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 8)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('LON'))
    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('HOL'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('BEL'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('HEL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('NTH'))
    assert_equal('French Fleet 1 Territory', french_army1.territory, map.game_state.get_territory('PIC'))
    assert_equal('French Fleet 2 Territory', french_army2.territory, map.game_state.get_territory('BUR'))

# 6.F.7
def test_dislodged_convoy_does_not_cause_contested_area():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    german_fleet1 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Germany'))

    map.submit_order('F NTH C A LON - HOL')
    map.submit_order('A LON - HOL')
    map.submit_order('F HEL S F SKA - NTH')
    map.submit_order('F SKA - NTH')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('LON'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('HEL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('NTH'))

# 6.F.8
def test_dislodged_convoy_does_not_cause_a_bounce():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    german_fleet1 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Germany'))
    german_army = add_army(map.game_state.get_territory('BEL'), map.game_state.get_player('Germany'))

    map.submit_order('F NTH C A LON - HOL')
    map.submit_order('A LON - HOL')
    map.submit_order('F HEL S F SKA - NTH')
    map.submit_order('F SKA - NTH')
    map.submit_order('F BEL - HOL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('LON'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('HEL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('NTH'))
    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('HOL'))

# 6.F.9
def test_dislodge_of_multi_route_convoy():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    french_fleet1 = add_fleet(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))

    map.submit_order('F ENG C A LON - BEL')
    map.submit_order('F NTH C A LON - BEL')
    map.submit_order('A LON - BEL')
    map.submit_order('F BRE S F MAO - ENG')
    map.submit_order('F MAO - ENG')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('ENG'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('BEL'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('BRE'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('ENG'))

# 6.F.10
def test_dislodge_of_multi_route_convoy_with_foreign_fleet():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    german_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('Germany'))
    french_fleet1 = add_fleet(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))

    map.submit_order('F NTH C A LON - BEL')
    map.submit_order('A LON - BEL')
    map.submit_order('F ENG C A LON - BEL')
    map.submit_order('F BRE S F MAO - ENG')
    map.submit_order('F MAO - ENG')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('BEL'))
    assert_not_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('BRE'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('ENG'))

# 6.F.11
def test_dislodge_of_multi_route_convoy_with_only_foreign_fleets():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    german_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('Germany'))
    russian_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('Russia'))
    french_fleet1 = add_fleet(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))

    map.submit_order('A LON - BEL')
    map.submit_order('F ENG C A LON - BEL')
    map.submit_order('F NTH C A LON - BEL')
    map.submit_order('F BRE S F MAO - ENG')
    map.submit_order('F MAO - ENG')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('BEL'))
    assert_not_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('BRE'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('ENG'))

# 6.F.12
def test_dislodged_convoying_fleet_not_on_route():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('IRI'), map.game_state.get_player('England'))
    french_fleet1 = add_fleet(map.game_state.get_territory('NAO'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))

    map.submit_order('F ENG C A LON - BEL')
    map.submit_order('A LON - BEL')
    map.submit_order('F IRI C A LON - BEL')
    map.submit_order('F NAO S F MAO - IRI')
    map.submit_order('F MAO - IRI')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('ENG'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('BEL'))
    assert_not_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('IRI'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('NAO'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('IRI'))

# 6.F.13
def test_the_unwanted_alternative():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    french_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    german_fleet1 = add_fleet(map.game_state.get_territory('HOL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('DEN'), map.game_state.get_player('Germany'))

    map.submit_order('A LON - BEL')
    map.submit_order('F NTH C A LON - BEL')
    map.submit_order('F ENG C A LON - BEL')
    map.submit_order('F HOL S F DEN - NTH')
    map.submit_order('F DEN - NTH')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('BEL'))
    assert_not_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('HOL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('NTH'))

# 6.F.14
def test_simple_convoy_paradox():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('WAL'), map.game_state.get_player('England'))
    french_army = add_army(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))

    map.submit_order('F LON S F WAL - ENG')
    map.submit_order('F WAL - ENG')
    map.submit_order('A BRE - LON')
    map.submit_order('F ENG C A BRE - LON')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('LON'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('BRE'))
    assert_not_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('ENG'))

# 6.F.15
def test_simple_convoy_paradox_with_additional_convoy():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('WAL'), map.game_state.get_player('England'))
    french_army = add_army(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    italian_fleet1 = add_fleet(map.game_state.get_territory('IRI'), map.game_state.get_player('Italy'))
    italian_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('Italy'))
    italian_army = add_army(map.game_state.get_territory('NAF'), map.game_state.get_player('Italy'))

    map.submit_order('F LON S F WAL - ENG')
    map.submit_order('F WAL - ENG')
    map.submit_order('A BRE - LON')
    map.submit_order('F ENG C A BRE - LON')
    map.submit_order('F IRI C A NAF - WAL')
    map.submit_order('F MAO C A NAF - WAL')
    map.submit_order('A NAF - WAL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 7)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('LON'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('BRE'))
    assert_not_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.game_state.get_territory('IRI'))
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.game_state.get_territory('MAO'))
    assert_equal('Italian Army Territory', italian_army.territory, map.game_state.get_territory('WAL'))

# 6.F.16
def test_pandins_paradox():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('WAL'), map.game_state.get_player('England'))
    french_army = add_army(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    german_fleet1 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('BEL'), map.game_state.get_player('Germany'))

    map.submit_order('F LON S F WAL - ENG')
    map.submit_order('F WAL - ENG')
    map.submit_order('A BRE - LON')
    map.submit_order('F ENG C A BRE - LON')
    map.submit_order('F NTH S F BEL - ENG')
    map.submit_order('F BEL - ENG')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('LON'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('WAL'))
    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('BRE'))
    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('NTH'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('BEL'))

# 6.F.17
def test_pandins_extended_paradox():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('WAL'), map.game_state.get_player('England'))
    french_army = add_army(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_fleet1 = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('YOR'), map.game_state.get_player('France'))
    german_fleet1 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('BEL'), map.game_state.get_player('Germany'))

    map.submit_order('F LON S F WAL - ENG')
    map.submit_order('F WAL - ENG')
    map.submit_order('A BRE - LON')
    map.submit_order('F ENG C A BRE - LON')
    map.submit_order('F YOR S A BRE - LON')
    map.submit_order('F NTH S F BEL - ENG')
    map.submit_order('F BEL - ENG')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 7)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('LON'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('WAL'))
    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('LON'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('YOR'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('NTH'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('BEL'))

# 6.F.18
def test_betrayal_paradox():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('England'))
    french_fleet = add_fleet(map.game_state.get_territory('BEL'), map.game_state.get_player('France'))
    german_fleet1 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Germany'))

    map.submit_order('F NTH C A LON - BEL')
    map.submit_order('A LON - BEL')
    map.submit_order('F ENG S A LON - BEL')
    map.submit_order('F BEL S F NTH H')
    map.submit_order('F HEL S F SKA - NTH')
    map.submit_order('F SKA - NTH')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('LON'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('BEL'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('HEL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('SKA'))

# 6.F.19
def test_multi_route_convoy_disruption_paradox():
    map = get_classic_map()
    french_army = add_army(map.game_state.get_territory('TUN'), map.game_state.get_player('France'))
    french_fleet1 = add_fleet(map.game_state.get_territory('TYS'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('ION'), map.game_state.get_player('France'))
    italian_fleet1 = add_fleet(map.game_state.get_territory('NAP'), map.game_state.get_player('Italy'))
    italian_fleet2 = add_fleet(map.game_state.get_territory('ROM'), map.game_state.get_player('Italy'))

    map.submit_order('A TUN - NAP')
    map.submit_order('F TYS C A TUN - NAP')
    map.submit_order('F ION C A TUN - NAP')
    map.submit_order('F NAP S F ROM - TYS')
    map.submit_order('F ROM - TYS')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('TUN'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('TYS'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('ION'))
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.game_state.get_territory('NAP'))
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.game_state.get_territory('ROM'))

# 6.F.20
def test_unwanted_multi_route_convoy_paradox():
    map = get_classic_map()
    french_army = add_army(map.game_state.get_territory('TUN'), map.game_state.get_player('France'))
    french_fleet = add_fleet(map.game_state.get_territory('TYS'), map.game_state.get_player('France'))
    italian_fleet1 = add_fleet(map.game_state.get_territory('NAP'), map.game_state.get_player('Italy'))
    italian_fleet2 = add_fleet(map.game_state.get_territory('ION'), map.game_state.get_player('Italy'))
    turkish_fleet1 = add_fleet(map.game_state.get_territory('AEG'), map.game_state.get_player('Turkey'))
    turkish_fleet2 = add_fleet(map.game_state.get_territory('EAS'), map.game_state.get_player('Turkey'))

    map.submit_order('A TUN - NAP')
    map.submit_order('F TYS C A TUN - NAP')
    map.submit_order('F NAP S F ION H')
    map.submit_order('F ION C A TUN - NAP')
    map.submit_order('F AEG S F EAS - ION')
    map.submit_order('F EAS - ION')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('TUN'))
    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('TYS'))
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.game_state.get_territory('NAP'))
    assert_not_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.game_state.get_territory('ION'))
    assert_equal('Turkish Fleet 1 Territory', turkish_fleet1.territory, map.game_state.get_territory('AEG'))
    assert_equal('Turkish Fleet 2 Territory', turkish_fleet2.territory, map.game_state.get_territory('ION'))

# 6.F.21
def test_dads_army_convoy():
    map = get_classic_map()
    russian_army1 = add_army(map.game_state.get_territory('EDI'), map.game_state.get_player('Russia'))
    russian_fleet = add_fleet(map.game_state.get_territory('NWG'), map.game_state.get_player('Russia'))
    russian_army2 = add_army(map.game_state.get_territory('NWY'), map.game_state.get_player('Russia'))
    french_fleet1 = add_fleet(map.game_state.get_territory('IRI'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))
    english_army = add_army(map.game_state.get_territory('LPL'), map.game_state.get_player('England'))
    english_fleet1 = add_fleet(map.game_state.get_territory('NAO'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('CLY'), map.game_state.get_player('England'))

    map.submit_order('A EDI S A NWY - CLY')
    map.submit_order('F NWG C A NWY - CLY')
    map.submit_order('A NWY - CLY')
    map.submit_order('F IRI S F MAO - NAO')
    map.submit_order('F MAO - NAO')
    map.submit_order('A LPL - CLY via convoy')
    map.submit_order('F NAO C A LPL - CLY')
    map.submit_order('F CLY S F NAO H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 8)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.game_state.get_territory('EDI'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('NWG'))
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.game_state.get_territory('NWY'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('IRI'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('NAO'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('LPL'))
    assert_not_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('NAO'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('CLY'))

# 6.F.22
def test_second_order_paradox_with_two_resolutions():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('EDI'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    french_army = add_army(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    german_fleet1 = add_fleet(map.game_state.get_territory('BEL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('PIC'), map.game_state.get_player('Germany'))
    russian_army = add_army(map.game_state.get_territory('NWY'), map.game_state.get_player('Russia'))
    russian_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('Russia'))

    map.submit_order('F EDI - NTH')
    map.submit_order('F LON S F EDI - NTH')
    map.submit_order('A BRE - LON')
    map.submit_order('F ENG C A BRE - LON')
    map.submit_order('F BEL S F PIC - ENG')
    map.submit_order('F PIC - ENG')
    map.submit_order('A NWY - BEL')
    map.submit_order('F NTH C A NWY - BEL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 8)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('LON'))
    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('BRE'))
    assert_not_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('BEL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('ENG'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('NWY'))
    assert_not_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('NTH'))

# 6.F.23
def test_second_order_paradox_with_two_exclusive_convoys():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('EDI'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    french_army = add_army(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    german_fleet1 = add_fleet(map.game_state.get_territory('BEL'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('LON'), map.game_state.get_player('Germany'))
    italian_fleet1 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('Italy'))
    italian_fleet2 = add_fleet(map.game_state.get_territory('IRI'), map.game_state.get_player('Italy'))
    russian_army = add_army(map.game_state.get_territory('NWY'), map.game_state.get_player('Russia'))
    russian_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('Russia'))

    map.submit_order('F EDI - NTH')
    map.submit_order('F YOR S F EDI - NTH')
    map.submit_order('A BRE - LON')
    map.submit_order('F ENG C A BRE - LON')
    map.submit_order('F BEL S F ENG H')
    map.submit_order('F LON S F NTH H')
    map.submit_order('F MAO - ENG')
    map.submit_order('F IRI S F MAO - ENG')
    map.submit_order('A NWY - BEL')
    map.submit_order('F NTH C A NWY - BEL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 10)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('EDI'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('YOR'))
    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('BRE'))
    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('BEL'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('LON'))
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.game_state.get_territory('MAO'))
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.game_state.get_territory('IRI'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('NWY'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('NTH'))

# 6.F.24
def test_second_order_paradox_with_no_resolution():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('EDI'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    english_fleet3 = add_fleet(map.game_state.get_territory('IRI'), map.game_state.get_player('England'))
    english_fleet4 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('England'))
    french_army = add_army(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_fleet1 = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('BEL'), map.game_state.get_player('France'))
    russian_army = add_army(map.game_state.get_territory('NWY'), map.game_state.get_player('Russia'))
    russian_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('Russia'))

    map.submit_order('F EDI - NTH')
    map.submit_order('F LON S F EDI - NTH')
    map.submit_order('F IRI - ENG')
    map.submit_order('F MAO S F IRI - ENG')
    map.submit_order('A BRE - LON')
    map.submit_order('F ENG C A BRE - LON')
    map.submit_order('F BEL S F ENG H')
    map.submit_order('A NWY - BEL')
    map.submit_order('F NTH C A NWY - BEL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 9)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('LON'))
    assert_equal('English Fleet 3 Territory', english_fleet3.territory, map.game_state.get_territory('IRI'))
    assert_equal('English Fleet 4 Territory', english_fleet4.territory, map.game_state.get_territory('MAO'))
    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('BRE'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('BEL'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('NWY'))
    assert_not_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('NTH'))

# 6.F.25
def test_cut_support_last():
    map = get_classic_map()
    german_army1 = add_army(map.game_state.get_territory('RUH'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('HOL'), map.game_state.get_player('Germany'))
    german_army3 = add_army(map.game_state.get_territory('DEN'), map.game_state.get_player('Germany'))
    german_fleet = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Germany'))
    german_army4 = add_army(map.game_state.get_territory('FIN'), map.game_state.get_player('Germany'))
    english_army1 = add_army(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    english_fleet1 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('England'))
    english_army2 = add_army(map.game_state.get_territory('BEL'), map.game_state.get_player('England'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('NWG'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('NWY'), map.game_state.get_player('Russia'))
    russian_fleet3 = add_fleet(map.game_state.get_territory('SWE'), map.game_state.get_player('Russia'))

    map.submit_order('A RUH - BEL')
    map.submit_order('A HOL S A RUH - BEL')
    map.submit_order('A DEN - NWY')
    map.submit_order('F SKA C A DEN - NWY')
    map.submit_order('A FIN S A DEN - NWY')
    map.submit_order('A YOR - HOL')
    map.submit_order('F NTH C A YOR - HOL')
    map.submit_order('F HEL S A YOR - HOL')
    map.submit_order('A BEL H')
    map.submit_order('F NWG - NTH')
    map.submit_order('F NWY S F NWG - NTH')
    map.submit_order('F SWE - SKA')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 12)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('RUH'))
    assert_not_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('HOL'))
    assert_equal('German Army 3 Territory', german_army3.territory, map.game_state.get_territory('NWY'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('SKA'))
    assert_equal('German Army 4 Territory', german_army4.territory, map.game_state.get_territory('FIN'))
    assert_equal('English Army 1 Territory', english_army1.territory, map.game_state.get_territory('HOL'))
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('HEL'))
    assert_equal('English Army 2 Territory', english_army2.territory, map.game_state.get_territory('BEL'))
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('NWG'))
    assert_not_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('NWY'))
    assert_equal('Russian Fleet 3 Territory', russian_fleet3.territory, map.game_state.get_territory('SWE'))

# 6.G Convoying to Adjacent Provinces
# 6.G.1
def test_two_units_can_swap_provinces_by_convoy():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('NWY'), map.game_state.get_player('England'))
    english_fleet = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('England'))
    russian_army = add_army(map.game_state.get_territory('SWE'), map.game_state.get_player('Russia'))

    map.submit_order('A NWY - SWE')
    map.submit_order('F SKA C A NWY - SWE')
    map.submit_order('A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('SWE'))
    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('SKA'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('NWY'))

# 6.G.2
def test_kidnapping_an_army():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('NWY'), map.game_state.get_player('England'))
    russian_fleet = add_fleet(map.game_state.get_territory('SWE'), map.game_state.get_player('Russia'))
    german_fleet = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Germany'))

    map.submit_order('A NWY - SWE')
    map.submit_order('F SWE - NWY')
    map.submit_order('F SKA C A NWY - SWE')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('NWY'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('SWE'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('SKA'))

# 6.G.3
def test_unwanted_disrupted_convoy_to_adjacent_province():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_army1 = add_army(map.game_state.get_territory('PIC'), map.game_state.get_player('France'))
    french_army2 = add_army(map.game_state.get_territory('BUR'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))
    english_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('England'))

    map.submit_order('F BRE - ENG')
    map.submit_order('A PIC - BEL')
    map.submit_order('A BUR S A PIC - BEL')
    map.submit_order('F MAO S F BRE - ENG')
    map.submit_order('F ENG C A PIC - BEL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Army 1 Territory', french_army1.territory, map.game_state.get_territory('BEL'))
    assert_equal('French Army 2 Territory', french_army2.territory, map.game_state.get_territory('BUR'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('MAO'))
    assert_not_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('ENG'))

# 6.G.4
def test_unwanted_disrupted_convoy_to_adjacent_province_and_opposite_move():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_army1 = add_army(map.game_state.get_territory('PIC'), map.game_state.get_player('France'))
    french_army2 = add_army(map.game_state.get_territory('BUR'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))
    english_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('BEL'), map.game_state.get_player('England'))

    map.submit_order('F BRE - ENG')
    map.submit_order('A PIC - BEL')
    map.submit_order('A BUR S A PIC - BEL')
    map.submit_order('F MAO S F BRE - ENG')
    map.submit_order('F ENG C A PIC - BEL')
    map.submit_order('A BEL - PIC')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Army 1 Territory', french_army1.territory, map.game_state.get_territory('BEL'))
    assert_equal('French Army 2 Territory', french_army2.territory, map.game_state.get_territory('BUR'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('MAO'))
    assert_not_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('ENG'))
    assert_not_equal('English Army Territory', english_army.territory, map.game_state.get_territory('BEL'))

# 6.G.5
def test_swapping_with_multiple_fleets_with_one_own_fleet():
    map = get_classic_map()
    italian_army = add_army(map.game_state.get_territory('ROM'), map.game_state.get_player('Italy'))
    italian_fleet = add_fleet(map.game_state.get_territory('TYS'), map.game_state.get_player('Italy'))
    turkish_army = add_army(map.game_state.get_territory('APU'), map.game_state.get_player('Turkey'))
    turkish_fleet = add_fleet(map.game_state.get_territory('ION'), map.game_state.get_player('Turkey'))

    map.submit_order('A ROM - APU')
    map.submit_order('F TYS C A APU - ROM')
    map.submit_order('A APU - ROM')
    map.submit_order('F ION C A APU - ROM')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', italian_army.territory, map.game_state.get_territory('APU'))
    assert_equal('English Fleet Territory', italian_fleet.territory, map.game_state.get_territory('TYS'))
    assert_equal('Russian Army Territory', turkish_army.territory, map.game_state.get_territory('ROM'))
    assert_equal('Russian Army Territory', turkish_fleet.territory, map.game_state.get_territory('ION'))

# 6.G.6
def test_swapping_with_unintended_intent():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('LPL'), map.game_state.get_player('England'))
    english_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('England'))
    german_army = add_army(map.game_state.get_territory('EDI'), map.game_state.get_player('Germany'))
    french_fleet1 = add_fleet(map.game_state.get_territory('IRI'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('France'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('NWG'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('NAO'), map.game_state.get_player('Russia'))

    map.submit_order('A LPL - EDI')
    map.submit_order('F ENG C A LPL - EDI')
    map.submit_order('A EDI - LPL')
    map.submit_order('F IRI H')
    map.submit_order('F NTH H')
    map.submit_order('F NWG C A LPL - EDI')
    map.submit_order('F NAO C A LPL - EDI')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 7)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('EDI'))
    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('LPL'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('IRI'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('NTH'))
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('NWG'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('NAO'))

# 6.G.7
def test_swapping_with_illegal_intent():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('NWY'), map.game_state.get_player('England'))
    russian_army = add_army(map.game_state.get_territory('SWE'), map.game_state.get_player('Russia'))
    russian_fleet = add_fleet(map.game_state.get_territory('BOT'), map.game_state.get_player('Russia'))

    map.submit_order('F SKA C A SWE - NWY')
    map.submit_order('F NWY - SWE')
    map.submit_order('A SWE - NWY')
    map.submit_order('F BOT C A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('SKA'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('NWY'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('SWE'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('BOT'))

# 6.G.8
def test_explicit_convoy_that_isnt_there():
    map = get_classic_map()
    french_army = add_army(map.game_state.get_territory('BEL'), map.game_state.get_player('France'))
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('HOL'), map.game_state.get_player('England'))

    map.submit_order('A BEL - HOL via convoy')
    map.submit_order('F NTH - HEL')
    map.submit_order('A HOL - KIE')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('BEL'))
    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('HEL'))
    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('KIE'))

# 6.G.9
def test_swapped_or_dislodged():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('NWY'), map.game_state.get_player('England'))
    english_fleet1 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('FIN'), map.game_state.get_player('England'))
    russian_army = add_army(map.game_state.get_territory('SWE'), map.game_state.get_player('Russia'))

    map.submit_order('A NWY - SWE')
    map.submit_order('F SKA C A NWY - SWE')
    map.submit_order('F FIN S A NWY - SWE')
    map.submit_order('A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('SWE'))
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('SKA'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('FIN'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('NWY'))

# 6.G.10
def test_swapped_or_a_head_to_head_battle():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('NWY'), map.game_state.get_player('England'))
    english_fleet1 = add_fleet(map.game_state.get_territory('DEN'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('FIN'), map.game_state.get_player('England'))
    german_fleet = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Germany'))
    russian_army = add_army(map.game_state.get_territory('SWE'), map.game_state.get_player('Russia'))
    russian_fleet = add_fleet(map.game_state.get_territory('BAR'), map.game_state.get_player('Russia'))
    french_fleet1 = add_fleet(map.game_state.get_territory('NWG'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('France'))

    map.submit_order('A NWY - SWE via convoy')
    map.submit_order('F DEN S A NWY - SWE')
    map.submit_order('F FIN S A NWY - SWE')
    map.submit_order('F SKA C A NWY - SWE')
    map.submit_order('A SWE - NWY')
    map.submit_order('F BAR S A SWE - NWY')
    map.submit_order('F NWG - NWY')
    map.submit_order('F NTH S F NWG - NWY')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 8)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('SWE'))
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('DEN'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('FIN'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('SKA'))
    assert_not_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('SWE'))
    assert_not_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('NWY'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('BAR'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('NWG'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('NTH'))

# 6.G.11
def test_convoy_to_an_adjacent_province_with_a_paradox():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('NWY'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    russian_army = add_army(map.game_state.get_territory('SWE'), map.game_state.get_player('Russia'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('BAR'), map.game_state.get_player('Russia'))

    map.submit_order('F NWY S F NTH - SKA')
    map.submit_order('F NTH - SKA')
    map.submit_order('A SWE - NWY')
    map.submit_order('F SKA C A SWE - NWY')
    map.submit_order('F BAR S A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('NWY'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('SKA'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('SWE'))
    assert_not_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('SKA'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('BAR'))

# 6.G.12
def test_swapping_two_units_with_two_convoys():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('LPL'), map.game_state.get_player('England'))
    english_fleet1 = add_fleet(map.game_state.get_territory('NAO'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('NWG'), map.game_state.get_player('England'))
    german_army = add_army(map.game_state.get_territory('EDI'), map.game_state.get_player('Germany'))
    german_fleet1 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('Germany'))
    german_fleet2 = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('Germany'))
    german_fleet3 = add_fleet(map.game_state.get_territory('IRI'), map.game_state.get_player('Germany'))

    map.submit_order('A LPL - EDI via convoy')
    map.submit_order('F NAO C A LPL - EDI')
    map.submit_order('F NWG C A LPL - EDI')
    map.submit_order('A EDI - LPL via convoy')
    map.submit_order('F NTH C A EDI - LPL')
    map.submit_order('F ENG C A EDI - LPL')
    map.submit_order('F IRI C A EDI - LPL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 7)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('EDI'))
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('NAO'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('NWG'))
    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('LPL'))
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.game_state.get_territory('NTH'))
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.game_state.get_territory('ENG'))
    assert_equal('German Fleet 3 Territory', german_fleet3.territory, map.game_state.get_territory('IRI'))

# 6.G.13
def test_support_cut_on_attack_on_itself_via_convoy():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.game_state.get_territory('ADR'), map.game_state.get_player('Austria-Hungary'))
    austrian_army = add_army(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))
    italian_army = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Italy'))
    italian_fleet = add_fleet(map.game_state.get_territory('ALB'), map.game_state.get_player('Italy'))

    map.submit_order('F ADR C A TRI - VEN')
    map.submit_order('A TRI - VEN via convoy')
    map.submit_order('A VEN S F ALB - TRI')
    map.submit_order('F ALB - TRI')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.game_state.get_territory('ADR'))
    assert_not_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('TRI'))
    assert_equal('Italian Army Territory', italian_army.territory, map.game_state.get_territory('VEN'))
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.game_state.get_territory('TRI'))

# 6.G.14
def test_bounce_by_convoy_to_adjacent_province():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('NWY'), map.game_state.get_player('England'))
    english_fleet1 = add_fleet(map.game_state.get_territory('DEN'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('FIN'), map.game_state.get_player('England'))
    french_fleet1 = add_fleet(map.game_state.get_territory('NWG'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('France'))
    german_fleet = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Germany'))
    russian_army = add_army(map.game_state.get_territory('SWE'), map.game_state.get_player('Russia'))
    russian_fleet = add_fleet(map.game_state.get_territory('BAR'), map.game_state.get_player('Russia'))

    map.submit_order('A NWY - SWE')
    map.submit_order('F DEN S A NWY - SWE')
    map.submit_order('F FIN S A NWY - SWE')
    map.submit_order('F NWG - NWY')
    map.submit_order('F NTH S F NWG - NWY')
    map.submit_order('F SKA C A SWE - NWY')
    map.submit_order('A SWE - NWY via convoy')
    map.submit_order('F BAR S A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 8)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('SWE'))
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('DEN'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('FIN'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('NWG'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('NTH'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('SKA'))
    assert_not_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('SWE'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('BAR'))

# 6.G.15
def test_bounce_and_dislodge_with_double_convoy():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army1 = add_army(map.game_state.get_territory('HOL'), map.game_state.get_player('England'))
    english_army2 = add_army(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    english_army3 = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    french_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    french_army = add_army(map.game_state.get_territory('BEL'), map.game_state.get_player('France'))

    map.submit_order('F NTH C A LON - BEL')
    map.submit_order('A HOL S A LON - BEL')
    map.submit_order('A YOR - LON')
    map.submit_order('A LON - BEL via convoy')
    map.submit_order('F ENG C A BEL - LON')
    map.submit_order('A BEL - LON via convoy')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Army 1 Territory', english_army1.territory, map.game_state.get_territory('HOL'))
    assert_equal('English Army 2 Territory', english_army2.territory, map.game_state.get_territory('YOR'))
    assert_equal('English Army 3 Territory', english_army3.territory, map.game_state.get_territory('BEL'))
    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('ENG'))
    assert_not_equal('French Army Territory', french_army.territory, map.game_state.get_territory('BEL'))

# 6.G.16
def test_the_two_unit_in_one_area_bug_moving_by_convoy():
    map = get_classic_map()
    english_army1 = add_army(map.game_state.get_territory('NWY'), map.game_state.get_player('England'))
    english_army2 = add_army(map.game_state.get_territory('DEN'), map.game_state.get_player('England'))
    english_fleet1 = add_fleet(map.game_state.get_territory('BAL'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    russian_army = add_army(map.game_state.get_territory('SWE'), map.game_state.get_player('Russia'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('NWG'), map.game_state.get_player('Russia'))

    map.submit_order('A NWY - SWE')
    map.submit_order('A DEN S A NWY - SWE')
    map.submit_order('F BAL S A NWY - SWE')
    map.submit_order('F NTH - NWY')
    map.submit_order('A SWE - NWY via convoy')
    map.submit_order('F SKA C A SWE - NWY')
    map.submit_order('F NWG S A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 7)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army 2 Territory', english_army1.territory, map.game_state.get_territory('SWE'))
    assert_equal('English Army 2 Territory', english_army2.territory, map.game_state.get_territory('DEN'))
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('BAL'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('NTH'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('NWY'))
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('SKA'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('NWG'))

# 6.G.17
def test_the_two_unit_in_one_area_bug_moving_over_land():
    map = get_classic_map()
    english_army1 = add_army(map.game_state.get_territory('NWY'), map.game_state.get_player('England'))
    english_army2 = add_army(map.game_state.get_territory('DEN'), map.game_state.get_player('England'))
    english_fleet1 = add_fleet(map.game_state.get_territory('BAL'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('England'))
    english_fleet3 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    russian_army = add_army(map.game_state.get_territory('SWE'), map.game_state.get_player('Russia'))
    russian_fleet = add_fleet(map.game_state.get_territory('NWG'), map.game_state.get_player('Russia'))

    map.submit_order('A NWY - SWE via convoy')
    map.submit_order('A DEN S A NWY - SWE')
    map.submit_order('F BAL S A NWY - SWE')
    map.submit_order('F SKA C A NWY - SWE')
    map.submit_order('F NTH - NWY')
    map.submit_order('A SWE - NWY')
    map.submit_order('F NWG S A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 7)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army 2 Territory', english_army1.territory, map.game_state.get_territory('SWE'))
    assert_equal('English Army 2 Territory', english_army2.territory, map.game_state.get_territory('DEN'))
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('BAL'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('SKA'))
    assert_equal('English Fleet 3 Territory', english_fleet3.territory, map.game_state.get_territory('NTH'))
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('NWY'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('NWG'))

# 6.G.18
def test_the_two_unit_in_one_area_bug_with_double_convoy():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army1 = add_army(map.game_state.get_territory('HOL'), map.game_state.get_player('England'))
    english_army2 = add_army(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    english_army3 = add_army(map.game_state.get_territory('LON'), map.game_state.get_player('England'))
    english_army4 = add_army(map.game_state.get_territory('RUH'), map.game_state.get_player('England'))
    french_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('France'))
    french_army1 = add_army(map.game_state.get_territory('BEL'), map.game_state.get_player('France'))
    french_army2 = add_army(map.game_state.get_territory('WAL'), map.game_state.get_player('France'))

    map.submit_order('F NTH C A LON - BEL')
    map.submit_order('A HOL S A LON - BEL')
    map.submit_order('A YOR - LON')
    map.submit_order('A LON - BEL')
    map.submit_order('A RUH S A LON - BEL')
    map.submit_order('F ENG C A BEL - LON')
    map.submit_order('A BEL - LON')
    map.submit_order('A WAL S A BEL - LON')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 8)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_equal('English Army 1 Territory', english_army1.territory, map.game_state.get_territory('HOL'))
    assert_equal('English Army 2 Territory', english_army2.territory, map.game_state.get_territory('YOR'))
    assert_equal('English Army 3 Territory', english_army3.territory, map.game_state.get_territory('BEL'))
    assert_equal('English Army 4 Territory', english_army4.territory, map.game_state.get_territory('RUH'))
    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Army 1 Territory', french_army1.territory, map.game_state.get_territory('LON'))
    assert_equal('French Army 2 Territory', french_army2.territory, map.game_state.get_territory('WAL'))

# 6.G.19
def test_swapping_with_intent_of_unnecessary_convoy():
    map = get_classic_map()
    french_army = add_army(map.game_state.get_territory('MAR'), map.game_state.get_player('France'))
    french_fleet = add_fleet(map.game_state.get_territory('WES'), map.game_state.get_player('France'))
    italian_fleet = add_fleet(map.game_state.get_territory('LYO'), map.game_state.get_player('Italy'))
    italian_army = add_army(map.game_state.get_territory('SPA'), map.game_state.get_player('Italy'))

    map.submit_order('A MAR - SPA')
    map.submit_order('F WES C A MAR - SPA')
    map.submit_order('F LYO C A MAR - SPA')
    map.submit_order('A SPA - MAR')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('MAR'))
    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('WES'))
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.game_state.get_territory('LYO'))
    assert_equal('Italian Army Territory', italian_army.territory, map.game_state.get_territory('SPA'))

# 6.G.20
def test_explicit_convoy_to_adjacent_province_disrupted():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_army1 = add_army(map.game_state.get_territory('PIC'), map.game_state.get_player('France'))
    french_army2 = add_army(map.game_state.get_territory('BUR'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))
    english_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('England'))

    map.submit_order('F BRE - ENG')
    map.submit_order('A PIC - BEL via convoy')
    map.submit_order('A BUR S A PIC - BEL')
    map.submit_order('F MAO S F BRE - ENG')
    map.submit_order('F ENG C A PIC - BEL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Army 1 Territory', french_army1.territory, map.game_state.get_territory('PIC'))
    assert_equal('French Army 2 Territory', french_army2.territory, map.game_state.get_territory('BUR'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('MAO'))
    assert_not_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('ENG'))

# 6.H Retreating
# 6.H.1
def test_no_supports_during_retreat():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))
    austrian_army = add_army(map.game_state.get_territory('SER'), map.game_state.get_player('Austria-Hungary'))
    turkish_fleet = add_fleet(map.game_state.get_territory('GRE'), map.game_state.get_player('Turkey'))
    italian_army1 = add_army(map.game_state.get_territory('VEN'), map.game_state.get_player('Italy'))
    italian_army2 = add_army(map.game_state.get_territory('TYR'), map.game_state.get_player('Italy'))
    italian_fleet1 = add_fleet(map.game_state.get_territory('ION'), map.game_state.get_player('Italy'))
    italian_fleet2 = add_fleet(map.game_state.get_territory('AEG'), map.game_state.get_player('Italy'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('F TRI H')
    map.submit_order('A SER H')
    map.submit_order('F GRE H')
    map.submit_order('A VEN S A TYR - TRI')
    map.submit_order('A TYR - TRI')
    map.submit_order('F ION - GRE')
    map.submit_order('F AEG S F ION - GRE')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 7)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('Austrian Fleet Territory', austrian_fleet.territory, map.game_state.get_territory('TRI'))
    assert_equal('Austrian Army Territory', austrian_army.territory, map.game_state.get_territory('SER'))
    assert_not_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('GRE'))
    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.game_state.get_territory('VEN'))
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.game_state.get_territory('TRI'))
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.game_state.get_territory('GRE'))
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.game_state.get_territory('AEG'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('F TRI - ALB')
    map.submit_order('A SER S F TRI - ALB')
    map.submit_order('F GRE - ALB')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 2)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, None)
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, None)
    assert_equal('Austrian Fleet Disbanded', austrian_fleet.disbanded, True)
    assert_equal('Turkish Fleet Disbanded', turkish_fleet.disbanded, True)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.2
def test_no_supports_from_retreating_unit():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('LPL'), map.game_state.get_player('England'))
    english_fleet1 = add_fleet(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('NWY'), map.game_state.get_player('England'))
    german_army1 = add_army(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('RUH'), map.game_state.get_player('Germany'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('EDI'), map.game_state.get_player('Russia'))
    russian_army1 = add_army(map.game_state.get_territory('SWE'), map.game_state.get_player('Russia'))
    russian_army2 = add_army(map.game_state.get_territory('FIN'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('HOL'), map.game_state.get_player('Russia'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('A LPL - EDI')
    map.submit_order('F YOR S A LPL - EDI')
    map.submit_order('F NWY H')
    map.submit_order('A KIE S A RUH - HOL')
    map.submit_order('A RUH - HOL')
    map.submit_order('F EDI H')
    map.submit_order('A SWE S A FIN - NWY')
    map.submit_order('A FIN - NWY')
    map.submit_order('F HOL H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 9)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('EDI'))
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('YOR'))
    assert_not_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('NWY'))
    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('KIE'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('HOL'))
    assert_not_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('EDI'))
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.game_state.get_territory('SWE'))
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.game_state.get_territory('NWY'))
    assert_not_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('HOL'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('F NWY - NTH')
    map.submit_order('F EDI - NTH')
    map.submit_order('F HOL S F EDI - NTH')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 2)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 2 Territory', english_fleet2.territory, None)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, None)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, None)
    assert_equal('English Fleet 2 Disbanded', english_fleet2.disbanded, True)
    assert_equal('Russian Fleet 1 Disbanded', russian_fleet1.disbanded, True)
    assert_equal('Russian Fleet 2 Disbanded', russian_fleet2.disbanded, True)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.3
def test_no_convoy_during_retreat():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('HOL'), map.game_state.get_player('England'))
    german_fleet = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    german_army = add_army(map.game_state.get_territory('RUH'), map.game_state.get_player('Germany'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('F NTH H')
    map.submit_order('A HOL H')
    map.submit_order('F KIE S A RUH - HOL')
    map.submit_order('A RUH - HOL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_not_equal('English Army Territory', english_army.territory, map.game_state.get_territory('HOL'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('KIE'))
    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('HOL'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('A HOL - YOR')
    map.submit_order('F NTH C A HOL - YOR')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, None)
    assert_equal('English Army Disbanded', english_army.disbanded, True)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.4
def test_no_other_moves_during_retreat():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    english_army = add_army(map.game_state.get_territory('HOL'), map.game_state.get_player('England'))
    german_fleet = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    german_army = add_army(map.game_state.get_territory('RUH'), map.game_state.get_player('Germany'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('F NTH H')
    map.submit_order('A HOL H')
    map.submit_order('F KIE S A RUH - HOL')
    map.submit_order('A RUH - HOL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('NTH'))
    assert_not_equal('English Army Territory', english_army.territory, map.game_state.get_territory('HOL'))
    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('KIE'))
    assert_equal('German Army Territory', german_army.territory, map.game_state.get_territory('HOL'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('A HOL - BEL')
    map.submit_order('F NTH - NWG')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('BEL'))
    assert_equal('English Army Disbanded', english_army.disbanded, False)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.5
def test_unit_may_not_retreat_to_area_from_which_it_is_attacked():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.game_state.get_territory('CON'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('BLA'), map.game_state.get_player('Russia'))
    turkish_fleet = add_fleet(map.game_state.get_territory('ANK'), map.game_state.get_player('Turkey'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('F CON S F BLA - ANK')
    map.submit_order('F BLA - ANK')
    map.submit_order('F ANK H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('CON'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('ANK'))
    assert_not_equal('Turkish Fleet Territory', turkish_fleet.territory, map.game_state.get_territory('ANK'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('F ANK - BLA')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, None)
    assert_equal('Turkish Fleet Disbanded', turkish_fleet.disbanded, True)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.6
def test_unit_may_not_retreat_to_a_contested_area():
    map = get_classic_map()
    austrian_army1 = add_army(map.game_state.get_territory('BUD'), map.game_state.get_player('Austria-Hungary'))
    austrian_army2 = add_army(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))
    german_army1 = add_army(map.game_state.get_territory('MUC'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('SIL'), map.game_state.get_player('Germany'))
    italian_army = add_army(map.game_state.get_territory('VIE'), map.game_state.get_player('Italy'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('A BUD S A TRI - VIE')
    map.submit_order('A TRI - VIE')
    map.submit_order('A MUC - BOH')
    map.submit_order('A SIL - BOH')
    map.submit_order('A VIE H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.game_state.get_territory('BUD'))
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.game_state.get_territory('VIE'))
    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('MUC'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('SIL'))
    assert_not_equal('Italian Army Territory', italian_army.territory, map.game_state.get_territory('VIE'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('A VIE - BOH')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Italian Army Territory', italian_army.territory, None)
    assert_equal('Italian Army Disbanded', italian_army.disbanded, True)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.7
def test_multiple_retreat_to_same_area_will_disband_units():
    map = get_classic_map()
    austrian_army1 = add_army(map.game_state.get_territory('BUD'), map.game_state.get_player('Austria-Hungary'))
    austrian_army2 = add_army(map.game_state.get_territory('TRI'), map.game_state.get_player('Austria-Hungary'))
    german_army1 = add_army(map.game_state.get_territory('MUC'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('SIL'), map.game_state.get_player('Germany'))
    italian_army1 = add_army(map.game_state.get_territory('VIE'), map.game_state.get_player('Italy'))
    italian_army2 = add_army(map.game_state.get_territory('BOH'), map.game_state.get_player('Italy'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('A BUD S A TRI - VIE')
    map.submit_order('A TRI - VIE')
    map.submit_order('A MUC S A SIL - BOH')
    map.submit_order('A SIL - BOH')
    map.submit_order('A VIE H')
    map.submit_order('A BOH H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.game_state.get_territory('BUD'))
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.game_state.get_territory('VIE'))
    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('MUC'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('BOH'))
    assert_not_equal('Italian Army 1 Territory', italian_army1.territory, map.game_state.get_territory('VIE'))
    assert_not_equal('Italian Army 2 Territory', italian_army2.territory, map.game_state.get_territory('BOH'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('A BOH - TYR')
    map.submit_order('A VIE - TYR')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 2)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Italian Army 1 Territory', italian_army1.territory, None)
    assert_equal('Italian Army 1 Disbanded', italian_army1.disbanded, True)
    assert_equal('Italian Army 2 Territory', italian_army2.territory, None)
    assert_equal('Italian Army 2 Disbanded', italian_army2.disbanded, True)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.8
def test_triple_retreat_to_same_area_will_disband_units():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('LPL'), map.game_state.get_player('England'))
    english_fleet1 = add_fleet(map.game_state.get_territory('YOR'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('NWY'), map.game_state.get_player('England'))
    german_army1 = add_army(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('RUH'), map.game_state.get_player('Germany'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('EDI'), map.game_state.get_player('Russia'))
    russian_army1 = add_army(map.game_state.get_territory('SWE'), map.game_state.get_player('Russia'))
    russian_army2 = add_army(map.game_state.get_territory('FIN'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('HOL'), map.game_state.get_player('Russia'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('A LPL - EDI')
    map.submit_order('F YOR S A LPL - EDI')
    map.submit_order('F NWY H')
    map.submit_order('A KIE S A RUH - HOL')
    map.submit_order('A RUH - HOL')
    map.submit_order('F EDI H')
    map.submit_order('A SWE S A FIN - NWY')
    map.submit_order('A FIN - NWY')
    map.submit_order('F HOL H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 9)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('EDI'))
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('YOR'))
    assert_not_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('NWY'))
    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('KIE'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('HOL'))
    assert_not_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('EDI'))
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.game_state.get_territory('SWE'))
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.game_state.get_territory('NWY'))
    assert_not_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('HOL'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('F NWY - NTH')
    map.submit_order('F EDI - NTH')
    map.submit_order('F HOL - NTH')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 2 Territory', english_fleet2.territory, None)
    assert_equal('English Fleet 2 Disbanded', english_fleet2.disbanded, True)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, None)
    assert_equal('Russian Fleet 1 Disbanded', russian_fleet1.disbanded, True)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, None)
    assert_equal('Russian Fleet 2 Disbanded', russian_fleet2.disbanded, True)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.9
def test_dislodged_unit_will_not_make_attackers_area_contested():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.game_state.get_territory('HEL'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('DEN'), map.game_state.get_player('England'))
    german_army1 = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_fleet = add_fleet(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('SIL'), map.game_state.get_player('Germany'))
    russian_army = add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Russia'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('F HEL - KIE')
    map.submit_order('F DEN S F HEL - KIE')
    map.submit_order('A BER - PRU')
    map.submit_order('F KIE H')
    map.submit_order('A SIL S A BER - PRU')
    map.submit_order('A PRU H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('KIE'))
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('DEN'))
    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('PRU'))
    assert_not_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('KIE'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('SIL'))
    assert_not_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('PRU'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('F KIE - BER')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Fleet Territory', german_fleet.territory, map.game_state.get_territory('BER'))
    assert_equal('German Fleet Disbanded', german_fleet.disbanded, False)
    assert_equal('Russian Army Territory', russian_army.territory, None)
    assert_equal('Russian Army Disbanded', russian_army.disbanded, True)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.10
def test_not_retreating_to_attackers_does_not_mean_contested():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('KIE'), map.game_state.get_player('England'))
    german_army1 = add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('MUC'), map.game_state.get_player('Germany'))
    german_army3 = add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Germany'))
    russian_army1 = add_army(map.game_state.get_territory('WAR'), map.game_state.get_player('Russia'))
    russian_army2 = add_army(map.game_state.get_territory('SIL'), map.game_state.get_player('Russia'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('A KIE H')
    map.submit_order('A BER - KIE')
    map.submit_order('A MUC S A BER - KIE')
    map.submit_order('A PRU H')
    map.submit_order('A WAR - PRU')
    map.submit_order('A SIL S A WAR - PRU')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('English Army Territory', english_army.territory, map.game_state.get_territory('KIE'))
    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('KIE'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('MUC'))
    assert_not_equal('German Army 3 Territory', german_army3.territory, map.game_state.get_territory('PRU'))
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.game_state.get_territory('PRU'))
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.game_state.get_territory('SIL'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('A KIE - BER')
    map.submit_order('A PRU - BER')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 2)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, None)
    assert_equal('English Army Disbanded', english_army.disbanded, True)
    assert_equal('German Army 3 Territory', german_army3.territory, map.game_state.get_territory('BER'))
    assert_equal('German Army 3 Disbanded', german_army3.disbanded, False)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.11
def test_retreat_when_dislodged_by_adjacent_convoy():
    map = get_classic_map()
    french_army1 = add_army(map.game_state.get_territory('GAS'), map.game_state.get_player('France'))
    french_army2 = add_army(map.game_state.get_territory('BUR'), map.game_state.get_player('France'))
    french_fleet1 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('WES'), map.game_state.get_player('France'))
    french_fleet3 = add_fleet(map.game_state.get_territory('LYO'), map.game_state.get_player('France'))
    italian_army = add_army(map.game_state.get_territory('MAR'), map.game_state.get_player('Italy'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('A GAS - MAR via convoy')
    map.submit_order('A BUR S A GAS - MAR')
    map.submit_order('F MAO C A GAS - MAR')
    map.submit_order('F WES C A GAS - MAR')
    map.submit_order('F LYO C A GAS - MAR')
    map.submit_order('A MAR H')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 6)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Army 1 Territory', french_army1.territory, map.game_state.get_territory('MAR'))
    assert_equal('French Army 2 Territory', french_army2.territory, map.game_state.get_territory('BUR'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('MAO'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('WES'))
    assert_equal('French Fleet 3 Territory', french_fleet3.territory, map.game_state.get_territory('LYO'))
    assert_not_equal('Italian Army Territory', italian_army.territory, map.game_state.get_territory('MAR'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('A MAR - GAS')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Italian Army Territory', italian_army.territory, map.game_state.get_territory('GAS'))
    assert_equal('Italian Army Disbanded', italian_army.disbanded, False)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.12
def test_retreat_when_dislodged_by_adjacent_convoy_while_trying_to_do_the_same():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('LPL'), map.game_state.get_player('England'))
    english_fleet1 = add_fleet(map.game_state.get_territory('IRI'), map.game_state.get_player('England'))
    english_fleet2 = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('England'))
    english_fleet3 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('England'))
    french_fleet1 = add_fleet(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))
    russian_army1 = add_army(map.game_state.get_territory('EDI'), map.game_state.get_player('Russia'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('NWG'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('NAO'), map.game_state.get_player('Russia'))
    russian_army2 = add_army(map.game_state.get_territory('CLY'), map.game_state.get_player('Russia'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('A LPL - EDI via convoy')
    map.submit_order('F IRI C A LPL - EDI')
    map.submit_order('F ENG C A LPL - EDI')
    map.submit_order('F NTH C A LPL - EDI')
    map.submit_order('F BRE - ENG')
    map.submit_order('F MAO S F BRE - ENG')
    map.submit_order('A EDI - LPL via convoy')
    map.submit_order('F NWG C A EDI - LPL')
    map.submit_order('F NAO C A EDI - LPL')
    map.submit_order('A CLY S A EDI - LPL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 10)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('English Army Territory', english_army.territory, map.game_state.get_territory('LPL'))
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.game_state.get_territory('IRI'))
    assert_not_equal('English Fleet 2 Territory', english_fleet2.territory, map.game_state.get_territory('ENG'))
    assert_equal('English Fleet 3 Territory', english_fleet3.territory, map.game_state.get_territory('NTH'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('MAO'))
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.game_state.get_territory('LPL'))
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('NWG'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('NAO'))
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.game_state.get_territory('CLY'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('A LPL - EDI')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.game_state.get_territory('EDI'))
    assert_equal('English Army Disbanded', english_army.disbanded, False)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.13
def test_no_retreat_with_convoy_in_movement_phase():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('PIC'), map.game_state.get_player('England'))
    english_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('England'))
    french_army1 = add_army(map.game_state.get_territory('PAR'), map.game_state.get_player('France'))
    french_army2 = add_army(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('A PIC H')
    map.submit_order('F ENG C A PIC - LON')
    map.submit_order('A PAR - PIC')
    map.submit_order('A BRE S A PAR - PIC')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 4)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('English Army Territory', english_army.territory, map.game_state.get_territory('PIC'))
    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Army 1 Territory', french_army1.territory, map.game_state.get_territory('PIC'))
    assert_equal('French Army 2 Territory', french_army2.territory, map.game_state.get_territory('BRE'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('A PIC - LON')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, None)
    assert_equal('English Army Disbanded', english_army.disbanded, True)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.14
def test_no_retreat_with_support_in_movement_phase():
    map = get_classic_map()
    english_army = add_army(map.game_state.get_territory('PIC'), map.game_state.get_player('England'))
    english_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('England'))
    french_army1 = add_army(map.game_state.get_territory('PAR'), map.game_state.get_player('France'))
    french_army2 = add_army(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))
    french_army3 = add_army(map.game_state.get_territory('BUR'), map.game_state.get_player('France'))
    german_army1 = add_army(map.game_state.get_territory('MUC'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('MAR'), map.game_state.get_player('Germany'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('A PIC H')
    map.submit_order('F ENG S A PIC - BEL')
    map.submit_order('A PAR - PIC')
    map.submit_order('A BRE S A PAR - PIC')
    map.submit_order('A BUR H')
    map.submit_order('A MUC S A MAR - BUR')
    map.submit_order('A MAR - BUR')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 7)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('English Army Territory', english_army.territory, map.game_state.get_territory('PIC'))
    assert_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('ENG'))
    assert_equal('French Army 1 Territory', french_army1.territory, map.game_state.get_territory('PIC'))
    assert_equal('French Army 2 Territory', french_army2.territory, map.game_state.get_territory('BRE'))
    assert_not_equal('French Army 3 Territory', french_army3.territory, map.game_state.get_territory('BUR'))
    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('MUC'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('BUR'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('A PIC - BEL')
    map.submit_order('A BUR - BEL')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 2)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, None)
    assert_equal('English Army Disbanded', english_army.disbanded, True)
    assert_equal('French Army 3 Territory', french_army3.territory, None)
    assert_equal('French Army 3 Disbanded', french_army3.disbanded, True)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.15
def test_no_coastal_crawl_in_retreat():
    map = get_classic_map()
    english_fleet = add_fleet(map.game_state.get_territory('POR'), map.game_state.get_player('England'))
    french_fleet1 = add_fleet(map.game_state.get_territory('SPA'), map.game_state.get_player('France'), 'sc')
    french_fleet2 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('F POR H')
    map.submit_order('F SPA - POR')
    map.submit_order('F MAO S F SPA - POR')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('English Fleet Territory', english_fleet.territory, map.game_state.get_territory('POR'))
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('POR'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('MAO'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('F POR - SPA(nc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, None)
    assert_equal('English Fleet Disbanded', english_fleet.disbanded, True)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.H.16
def test_contested_for_both_coasts():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.game_state.get_territory('MAO'), map.game_state.get_player('France'))
    french_fleet2 = add_fleet(map.game_state.get_territory('GAS'), map.game_state.get_player('France'))
    french_fleet3 = add_fleet(map.game_state.get_territory('WES'), map.game_state.get_player('France'))
    italian_fleet1 = add_fleet(map.game_state.get_territory('TUN'), map.game_state.get_player('Italy'))
    italian_fleet2 = add_fleet(map.game_state.get_territory('TYS'), map.game_state.get_player('Italy'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('F MAO - SPA(nc)')
    map.submit_order('F GAS - SPA(nc)')
    map.submit_order('F WES H')
    map.submit_order('F TUN S F TYS - WES')
    map.submit_order('F TYS - WES')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 5)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.game_state.get_territory('MAO'))
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.game_state.get_territory('GAS'))
    assert_not_equal('French Fleet 3 Territory', french_fleet3.territory, map.game_state.get_territory('WES'))
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.game_state.get_territory('TUN'))
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.game_state.get_territory('WES'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring Retreat')

    map.submit_order('F WES - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet 3 Territory', french_fleet3.territory, None)
    assert_equal('French Fleet 3 Disbanded', french_fleet3.disbanded, True)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

# 6.I Building
# 6.I.1
def test_too_many_build_orders():
    map = get_classic_map()
    # Leave only one build slot open for germany
    add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Germany'))
    
    assert_equal('German Units', len(map.game_state.get_player('Germany').units), 2)
    assert_equal('German Available Units', map.game_state.get_player('Germany').units_to_build(map.game_state.territories), 1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    map.submit_order('Build A WAR', owner=map.game_state.get_player('Germany'))
    map.submit_order('Build A KIE', owner=map.game_state.get_player('Germany'))
    map.submit_order('Build A MUC', owner=map.game_state.get_player('Germany'))
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 2)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Units', len(map.game_state.get_player('Germany').units), 3)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.I.2
def test_fleets_cannot_be_built_in_land_areas():
    map = get_classic_map()
    # Leave only one build slot open for russia
    add_army(map.game_state.get_territory('FIN'), map.game_state.get_player('Russia'))
    add_army(map.game_state.get_territory('STP'), map.game_state.get_player('Russia'))
    add_army(map.game_state.get_territory('LIV'), map.game_state.get_player('Russia'))
    
    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 3)
    assert_equal('Russian Available Units', map.game_state.get_player('Russia').units_to_build(map.game_state.territories), 1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    map.submit_order('Build F MOS', owner=map.game_state.get_player('Russia'))
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 3)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.I.3
def test_supply_center_must_be_empty_for_building():
    map = get_classic_map()
    # Leave only one build slot open for russia
    add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    add_army(map.game_state.get_territory('FIN'), map.game_state.get_player('Germany'))
    
    assert_equal('German Units', len(map.game_state.get_player('Germany').units), 2)
    assert_equal('German Available Units', map.game_state.get_player('Germany').units_to_build(map.game_state.territories), 1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    map.submit_order('Build A BER', owner=map.game_state.get_player('Germany'))
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Units', len(map.game_state.get_player('Germany').units), 2)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.I.4
def test_both_coasts_must_be_empty_for_building():
    map = get_classic_map()
    # Leave only one build slot open for russia
    add_army(map.game_state.get_territory('FIN'), map.game_state.get_player('Russia'))
    add_fleet(map.game_state.get_territory('STP'), map.game_state.get_player('Russia'), 'sc')
    add_army(map.game_state.get_territory('LIV'), map.game_state.get_player('Russia'))
    
    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 3)
    assert_equal('Russian Available Units', map.game_state.get_player('Russia').units_to_build(map.game_state.territories), 1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    map.submit_order('Build F STP(nc)', owner=map.game_state.get_player('Russia'))
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 3)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.I.5
def test_building_in_home_supply_center_that_is_not_owned():
    map = get_classic_map()
    # Leave only one build slot open for russia
    russian_army = add_army(map.game_state.get_territory('KIE'), map.game_state.get_player('Russia'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

    map.submit_order('A KIE - BER')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('BER'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Fall')

    map.submit_order('A BER - KIE')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)
    
    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('KIE'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')
    
    assert_equal('German Units', len(map.game_state.get_player('Germany').units), 0)
    assert_equal('German Available Units', map.game_state.get_player('Germany').units_to_build(map.game_state.territories), 1)

    map.submit_order('Build A BER', owner=map.game_state.get_player('Germany'))
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Units', len(map.game_state.get_player('Germany').units), 0)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.I.6
def test_building_in_owned_supply_center_that_is_not_a_home_supply_center():
    map = get_classic_map()
    # Leave only one build slot open for russia
    add_army(map.game_state.get_territory('BER'), map.game_state.get_player('Germany'))
    add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Germany'))
    add_army(map.game_state.get_territory('KIE'), map.game_state.get_player('Germany'))

    map.game_state.get_territory('WAR').owner = map.game_state.get_player('Germany')
    
    assert_equal('German Units', len(map.game_state.get_player('Germany').units), 3)
    assert_equal('German Available Units', map.game_state.get_player('Germany').units_to_build(map.game_state.territories), 1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    map.submit_order('Build A WAR', owner=map.game_state.get_player('Germany'))
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('German Units', len(map.game_state.get_player('Germany').units), 3)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.I.7
def test_only_one_build_in_a_home_supply_center():
    map = get_classic_map()
    # Leave only one build slot open for russia
    add_army(map.game_state.get_territory('UKR'), map.game_state.get_player('Russia'))
    add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Russia'))
    
    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 2)
    assert_equal('Russian Available Units', map.game_state.get_player('Russia').units_to_build(map.game_state.territories), 2)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    map.submit_order('Build A MOS', owner=map.game_state.get_player('Russia'))
    map.submit_order('Build A MOS', owner=map.game_state.get_player('Russia'))
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 2)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 3)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.J Civil Disorder and Disbands
# 6.J.1
def test_too_many_disband_orders():
    map = get_classic_map()
    french_army1 = add_army(map.game_state.get_territory('PAR'), map.game_state.get_player('France'))
    french_army2 = add_army(map.game_state.get_territory('PIC'), map.game_state.get_player('France'))

    map.game_state.get_territory('BRE').owner = map.game_state.get_player('Russia')
    map.game_state.get_territory('MAR').owner = map.game_state.get_player('Russia')
    
    assert_equal('French Units', len(map.game_state.get_player('France').units), 2)
    assert_equal('French Available Units', map.game_state.get_player('France').units_to_build(map.game_state.territories), -1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    map.submit_order('Remove F LYO', owner=map.game_state.get_player('France'))
    map.submit_order('Remove A PIC', owner=map.game_state.get_player('France'))
    map.submit_order('Remove A PAR', owner=map.game_state.get_player('France'))
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 2)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Units', len(map.game_state.get_player('France').units), 1)

    assert_equal('French Army 1 Territory', french_army1.territory, map.game_state.get_territory('PAR'))
    assert_equal('French Army 2 Territory', french_army2.territory, None)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.J.2
def test_removing_the_same_unit_twice():
    map = get_classic_map()
    french_army1 = add_army(map.game_state.get_territory('PAR'), map.game_state.get_player('France'))
    french_army2 = add_army(map.game_state.get_territory('PIC'), map.game_state.get_player('France'))

    map.game_state.get_territory('BRE').owner = map.game_state.get_player('Russia')
    map.game_state.get_territory('MAR').owner = map.game_state.get_player('Russia')
    
    assert_equal('French Units', len(map.game_state.get_player('France').units), 2)
    assert_equal('French Available Units', map.game_state.get_player('France').units_to_build(map.game_state.territories), -1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    map.submit_order('Remove A PAR', owner=map.game_state.get_player('France'))
    map.submit_order('Remove A PAR', owner=map.game_state.get_player('France'))
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Units', len(map.game_state.get_player('France').units), 1)

    assert_equal('French Army 1 Territory', french_army1.territory, None)
    assert_equal('French Army 2 Territory', french_army2.territory, map.game_state.get_territory('PIC'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.J.3
def test_civil_disorder_two_armies_with_different_distance():
    map = get_classic_map()
    russian_army1 = add_army(map.game_state.get_territory('LIV'), map.game_state.get_player('Russia'))
    russian_army2 = add_army(map.game_state.get_territory('SWE'), map.game_state.get_player('Russia'))
    russian_army3 = add_army(map.game_state.get_territory('FIN'), map.game_state.get_player('Russia'))

    map.game_state.get_territory('STP').owner = map.game_state.get_player('Russia')

    map.game_state.get_territory('MOS').owner = map.game_state.get_player('France')
    map.game_state.get_territory('WAR').owner = map.game_state.get_player('France')
    map.game_state.get_territory('SEV').owner = map.game_state.get_player('France')
    
    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 3)
    assert_equal('Russian Available Units', map.game_state.get_player('Russia').units_to_build(map.game_state.territories), -1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 2)

    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.game_state.get_territory('LIV'))
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.game_state.get_territory('SWE'))
    assert_equal('Russian Army 3 Territory', russian_army3.territory, None)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.J.4
def test_civil_disorder_two_armies_with_equal_distance():
    map = get_classic_map()
    russian_army1 = add_army(map.game_state.get_territory('LIV'), map.game_state.get_player('Russia'))
    russian_army2 = add_army(map.game_state.get_territory('UKR'), map.game_state.get_player('Russia'))
    add_army(map.game_state.get_territory('MOS'), map.game_state.get_player('Russia'))

    map.game_state.get_territory('MOS').owner = map.game_state.get_player('Russia')

    map.game_state.get_territory('WAR').owner = map.game_state.get_player('France')
    map.game_state.get_territory('SEV').owner = map.game_state.get_player('France')
    
    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 3)
    assert_equal('Russian Available Units', map.game_state.get_player('Russia').units_to_build(map.game_state.territories), -1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 2)

    assert_equal('Russian Army 1 Territory', russian_army1.territory, None)
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.game_state.get_territory('UKR'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.J.5
def test_civil_disorder_two_fleets_with_different_distance():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('BER'), map.game_state.get_player('Russia'))
    add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Russia'))

    map.game_state.get_territory('STP').owner = map.game_state.get_player('Russia')

    map.game_state.get_territory('MOS').owner = map.game_state.get_player('France')
    map.game_state.get_territory('WAR').owner = map.game_state.get_player('France')
    map.game_state.get_territory('SEV').owner = map.game_state.get_player('France')
    
    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 3)
    assert_equal('Russian Available Units', map.game_state.get_player('Russia').units_to_build(map.game_state.territories), -1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 2)

    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, None)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('BER'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.J.6
def test_civil_disorder_two_fleets_with_equal_distance():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.game_state.get_territory('BOT'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('Russia'))

    map.game_state.get_territory('MUC').owner = map.game_state.get_player('Russia')

    map.game_state.get_territory('STP').owner = map.game_state.get_player('France')
    map.game_state.get_territory('MOS').owner = map.game_state.get_player('France')
    map.game_state.get_territory('WAR').owner = map.game_state.get_player('France')
    map.game_state.get_territory('SEV').owner = map.game_state.get_player('France')
    
    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 2)
    assert_equal('Russian Available Units', map.game_state.get_player('Russia').units_to_build(map.game_state.territories), -1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 1)

    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, None)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.game_state.get_territory('NTH'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.J.7
def test_civil_disorder_two_fleets_and_army_with_equal_distance():
    map = get_classic_map()
    russian_army = add_army(map.game_state.get_territory('BOH'), map.game_state.get_player('Russia'))
    russian_fleet1 = add_fleet(map.game_state.get_territory('SKA'), map.game_state.get_player('Russia'))
    russian_fleet2 = add_fleet(map.game_state.get_territory('NTH'), map.game_state.get_player('Russia'))

    map.game_state.get_territory('STP').owner = map.game_state.get_player('Russia')
    map.game_state.get_territory('WAR').owner = map.game_state.get_player('Russia')

    map.game_state.get_territory('MOS').owner = map.game_state.get_player('France')
    map.game_state.get_territory('SEV').owner = map.game_state.get_player('France')
    
    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 3)
    assert_equal('Russian Available Units', map.game_state.get_player('Russia').units_to_build(map.game_state.territories), -1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 2)

    assert_equal('Russian Army Territory', russian_army.territory, map.game_state.get_territory('BOH'))
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.game_state.get_territory('SKA'))
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, None)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.J.8
def test_civil_disorder_a_fleet_with_shorter_distance_than_the_army():
    map = get_classic_map()
    russian_army = add_army(map.game_state.get_territory('TYR'), map.game_state.get_player('Russia'))
    russian_fleet = add_fleet(map.game_state.get_territory('BAL'), map.game_state.get_player('Russia'))

    map.game_state.get_territory('WAR').owner = map.game_state.get_player('Russia')

    map.game_state.get_territory('STP').owner = map.game_state.get_player('France')
    map.game_state.get_territory('MOS').owner = map.game_state.get_player('France')
    map.game_state.get_territory('SEV').owner = map.game_state.get_player('France')
    
    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 2)
    assert_equal('Russian Available Units', map.game_state.get_player('Russia').units_to_build(map.game_state.territories), -1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 1)

    assert_equal('Russian Army Territory', russian_army.territory, None)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.game_state.get_territory('BAL'))

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.J.9
def test_civil_disorder_must_be_counted_from_both_coasts():
    map = get_classic_map()
    russian_army1 = add_army(map.game_state.get_territory('GRE'), map.game_state.get_player('Russia'))
    russian_army2 = add_army(map.game_state.get_territory('SEV'), map.game_state.get_player('Russia'))
    russian_fleet = add_fleet(map.game_state.get_territory('BAL'), map.game_state.get_player('Russia'))
    add_army(map.game_state.get_territory('PRU'), map.game_state.get_player('Russia'))

    map.game_state.get_territory('STP').owner = map.game_state.get_player('Russia')
    map.game_state.get_territory('SEV').owner = map.game_state.get_player('Russia')

    map.game_state.get_territory('WAR').owner = map.game_state.get_player('France')
    map.game_state.get_territory('MOS').owner = map.game_state.get_player('France')
    
    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 4)
    assert_equal('Russian Available Units', map.game_state.get_player('Russia').units_to_build(map.game_state.territories), -1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Russian Units', len(map.game_state.get_player('Russia').units), 3)

    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.game_state.get_territory('GRE'))
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.game_state.get_territory('SEV'))
    assert_equal('Russian Fleet Territory', russian_fleet.territory, None)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.J.10
def test_civil_disorder_counting_convoying_distance():
    map = get_classic_map()
    italian_army1 = add_army(map.game_state.get_territory('GRE'), map.game_state.get_player('Italy'))
    italian_army2 = add_army(map.game_state.get_territory('PIE'), map.game_state.get_player('Italy'))
    add_army(map.game_state.get_territory('TUS'), map.game_state.get_player('Italy'))

    map.game_state.get_territory('NAP').owner = map.game_state.get_player('Italy')

    map.game_state.get_territory('VEN').owner = map.game_state.get_player('France')
    map.game_state.get_territory('ROM').owner = map.game_state.get_player('France')
    
    assert_equal('Italian Units', len(map.game_state.get_player('Italy').units), 3)
    assert_equal('Italian Available Units', map.game_state.get_player('Italy').units_to_build(map.game_state.territories), -1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Italian Units', len(map.game_state.get_player('Italy').units), 2)

    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.game_state.get_territory('GRE'))
    assert_equal('Italian Army 2 Territory', italian_army2.territory, None)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# 6.J.11
def test_distance_to_owned_supply_center():
    map = get_classic_map()
    italian_army1 = add_army(map.game_state.get_territory('WAR'), map.game_state.get_player('Italy'))
    italian_army2 = add_army(map.game_state.get_territory('TUS'), map.game_state.get_player('Italy'))

    map.game_state.get_territory('WAR').owner = map.game_state.get_player('Italy')

    map.game_state.get_territory('NAP').owner = map.game_state.get_player('France')
    map.game_state.get_territory('VEN').owner = map.game_state.get_player('France')
    map.game_state.get_territory('ROM').owner = map.game_state.get_player('France')
    
    assert_equal('Italian Units', len(map.game_state.get_player('Italy').units), 2)
    assert_equal('Italian Available Units', map.game_state.get_player('Italy').units_to_build(map.game_state.territories), -1)

    map.game_state.set_phase('Adjustment')
    assert_equal('Map Phase', map.game_state.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('Italian Units', len(map.game_state.get_player('Italy').units), 1)

    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.game_state.get_territory('WAR'))
    assert_equal('Italian Army 2 Territory', italian_army2.territory, None)

    assert_equal('Map Phase', map.game_state.get_phase(), 'Spring')

# Transform Orders
# T.1
def test_transform_coastal_army():
    map = get_classic_map()
    french_army = add_army(map.game_state.get_territory('NWY'), map.game_state.get_player('France'))

    map.submit_order('A NWY T')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet Territory', french_army.territory, map.game_state.get_territory('NWY'))
    assert_equal('French Fleet Type', french_army.type, 'Fleet')

# T.2
def test_transform_inland_army():
    map = get_classic_map()
    french_army = add_army(map.game_state.get_territory('MOS'), map.game_state.get_player('France'))

    map.submit_order('A MOS T')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('MOS'))
    assert_equal('French Army Type', french_army.type, 'Army')

# T.3
def test_transform_coastal_fleet():
    map = get_classic_map()
    french_fleet = add_fleet(map.game_state.get_territory('SWE'), map.game_state.get_player('France'))

    map.submit_order('F SWE T')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Army Territory', french_fleet.territory, map.game_state.get_territory('SWE'))
    assert_equal('French Army Type', french_fleet.type, 'Army')

# T.4
def test_transform_coastal_army_to_south_coast():
    map = get_classic_map()
    french_army = add_army(map.game_state.get_territory('STP'), map.game_state.get_player('France'))

    map.submit_order('A STP T(sc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 1)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet Territory', french_army.territory, map.game_state.get_territory('STP'))
    assert_equal('French Fleet Territory Coast', french_army.territory.unit_coast, 'sc')
    assert_equal('French Fleet Type', french_army.type, 'Fleet')

# T.5
def test_transform_coastal_army_to_invalid_south_coast():
    map = get_classic_map()
    french_army = add_army(map.game_state.get_territory('NWY'), map.game_state.get_player('France'))

    map.submit_order('A NWY T(sc)')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.game_state.get_territory('NWY'))
    assert_equal('French Army Territory Coast', french_army.territory.unit_coast, None)
    assert_equal('French Army Type', french_army.type, 'Army')

# T.6
def test_transform_fleet_in_water():
    map = get_classic_map()
    french_fleet = add_fleet(map.game_state.get_territory('NAO'), map.game_state.get_player('France'))

    map.submit_order('F NAO T')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_equal('French Fleet Territory', french_fleet.territory, map.game_state.get_territory('NAO'))
    assert_equal('French Fleet Type', french_fleet.type, 'Fleet')

# T.7
def test_dislodged_army_cannot_transform():
    map = get_classic_map()
    french_army = add_army(map.game_state.get_territory('GAS'), map.game_state.get_player('France'))
    german_army1 = add_army(map.game_state.get_territory('MAR'), map.game_state.get_player('Germany'))
    german_army2 = add_army(map.game_state.get_territory('SPA'), map.game_state.get_player('Germany'))

    map.submit_order('A GAS T')
    map.submit_order('A MAR - GAS')
    map.submit_order('A SPA S A MAR - GAS')
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 3)

    map.adjudicator.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.game_state.queued_orders), 0)

    assert_not_equal('French Army Territory', french_army.territory, map.game_state.get_territory('GAS'))
    assert_equal('German Army 1 Territory', german_army1.territory, map.game_state.get_territory('GAS'))
    assert_equal('German Army 2 Territory', german_army2.territory, map.game_state.get_territory('SPA'))
    assert_equal('French Army Type', french_army.type, 'Army')

def main():
    global prefix, test_num

    # Tests are taken from this site: https://webdiplomacy.net/doc/DATC_v3_0.html#5.A

    # 6.A Basic Checks
    print('Basic Checks:')
    prefix = '6.A.'
    test_num = 1
    run_test(test_advance_not_neighbor)
    run_test(test_move_army_to_sea)
    run_test(test_move_fleet_to_land)
    run_test(test_move_to_own_territory)
    run_test(test_move_to_own_territory_with_convoy)
    run_test(test_ordering_other_countrys_unit)
    run_test(test_only_convoy_armies)
    run_test(test_support_hold_yourself_fails)
    run_test(test_fleets_must_follow_coast_if_not_sea)
    run_test(test_support_unreachable_territory_impossible)
    run_test(test_simple_bounce)
    run_test(test_triple_bounce)
    print()

    # 6.B Coastal Issues
    print('Coastal Issues:')
    prefix = '6.B.'
    test_num = 1
    run_test(test_move_unspecified_coast_when_necessary)
    run_test(test_move_unspecified_coast_when_not_necessary)
    run_test(test_move_wrong_coast_when_not_necessary)
    run_test(test_support_to_unreachable_coast_allowed)
    run_test(test_support_from_unreachable_coast_not_allowed)
    run_test(test_support_cut_from_other_coast)
    run_test(test_support_own_unit_with_unspecified_coast)
    run_test(test_support_with_unspecified_coast_when_only_one_coast_possible)
    run_test(test_support_with_wrong_coast)
    test_num += 1 # Skip missing test
    run_test(test_coast_cannot_be_ordered_to_change)
    run_test(test_army_movement_with_coastal_specifications)
    run_test(test_coastal_crawl_not_allowed)
    run_test(test_building_unspecified_coast)
    run_test(test_support_foreign_unit_unspecified_coast)
    print()

    # 6.C Circular Movement
    print('Circular Movement:')
    prefix = '6.C.'
    test_num = 1
    run_test(test_three_army_circular_movement)
    run_test(test_three_army_circular_movement_with_support)
    run_test(test_disrupted_three_army_circular_movement)
    run_test(test_circular_movement_with_attacked_convoy)
    run_test(test_disrupted_circular_movement_dislodged_convoy)
    run_test(test_two_armies_two_convoys)
    run_test(test_disrupted_unit_swap)
    run_test(test_no_self_dislodgement_in_disrupted_circular_movement)
    run_test(test_no_help_in_dislodgement_of_own_unit_in_disrupted_circular_movement)
    print()

    # 6.D Supports and Dislodges
    print('Supports and Dislodges:')
    prefix = '6.D.'
    test_num = 1
    run_test(test_supported_hold_can_prevent_dislodgement)
    run_test(test_move_cuts_support_on_hold)
    run_test(test_move_cuts_support_on_move)
    run_test(test_support_to_hold_on_unit_supporting_hold_allowed)
    run_test(test_support_to_hold_on_unit_supporting_move_allowed)
    run_test(test_support_to_hold_on_convoying_unit_allowed)
    run_test(test_support_to_hold_on_moving_unit_not_allowed)
    run_test(test_failed_convoy_cannot_receive_hold_support)
    run_test(test_support_to_move_on_holding_unit_not_allowed)
    run_test(test_self_dislodgement_prohibited)
    run_test(test_no_self_dislodgement_of_returning_unit)
    run_test(test_supporting_foreign_unit_to_dislodge_own_unit_prohibited)
    run_test(test_supporting_foreign_unit_to_dislodge_returning_own_unit_prohibited)
    run_test(test_supporting_foreign_unit_not_enough_to_prevent_dislodgement)
    run_test(test_defender_cannot_cut_support_for_attack_on_itself)
    run_test(test_convoying_unit_dislodging_unit_of_same_power_allowed)
    run_test(test_dislodgement_cuts_support)
    run_test(test_surviving_unit_will_sustain_support)
    run_test(test_even_when_surviving_is_in_alternative_way)
    run_test(test_unit_cannot_cut_support_of_its_own_country)
    run_test(test_dislodging_dows_not_cancel_a_support_cut)
    run_test(test_impossible_fleet_move_cannot_be_supported)
    run_test(test_impossible_coast_move_cannot_be_supported)
    run_test(test_impossible_army_move_cannot_be_supported)
    run_test(test_failing_hold_support_can_be_supported)
    run_test(test_failing_move_support_can_be_supported)
    run_test(test_failing_convoy_can_be_supported)
    run_test(test_impossible_move_and_support)
    run_test(test_move_to_impossible_coast_and_support)
    run_test(test_move_without_coast_and_support)
    run_test(test_tricky_impossible_support)
    run_test(test_missing_fleet)
    run_test(test_unwanted_support_allowed)
    run_test(test_support_targeting_own_area_not_allowed)
    print()

    # 6.E Head-to-Head Battles and Beleaguered Garrison
    prefix = '6.E.'
    test_num = 1
    print('Head-to-Head Battles and Beleaguered Garrison:')
    run_test(test_dislodged_unit_has_no_effect_on_attackers_area)
    run_test(test_no_self_dislodgement_in_head_to_head_battle)
    run_test(test_no_help_in_dislodging_own_unit)
    run_test(test_non_dislodged_loser_still_has_effect)
    run_test(test_loser_dislodged_by_another_army_still_has_effect)
    run_test(test_not_dislodge_because_of_own_support_still_in_effect)
    run_test(test_no_self_dislodgement_with_beleaguered_garrison)
    run_test(test_no_self_dislodgement_with_beleaguered_garrison_and_head_to_head_battle)
    run_test(test_almost_self_dislodgement_with_beleaguered_garrison)
    run_test(test_almost_circular_movement_with_no_self_dislodgement_with_beleaguered_garrison)
    run_test(test_no_self_dislodgement_with_beleaguered_garrison_unit_swap_with_adjacent_convoying_and_two_coasts)
    run_test(test_support_on_attack_on_own_unit_can_be_used_for_other_means)
    run_test(test_three_way_beleaguered_garrison)
    run_test(test_illegal_head_to_head_battle_can_still_defend)
    run_test(test_the_friendly_head_to_head_battle)
    print()

    # 6.F Convoys
    prefix = '6.F.'
    test_num = 1
    print('Convoys:')
    run_test(test_no_convoy_in_coastal_areas)
    run_test(test_an_army_being_convoyed_can_bounce_as_normal)
    run_test(test_an_army_being_convoyed_can_receive_support)
    run_test(test_an_attacked_convoy_is_not_disrupted)
    run_test(test_beleaguered_convoy_is_not_disrupted)
    run_test(test_dislodged_convoy_does_not_cut_support)
    run_test(test_dislodged_convoy_does_not_cause_contested_area)
    run_test(test_dislodged_convoy_does_not_cause_a_bounce)
    run_test(test_dislodge_of_multi_route_convoy)
    run_test(test_dislodge_of_multi_route_convoy_with_foreign_fleet)
    run_test(test_dislodge_of_multi_route_convoy_with_only_foreign_fleets)
    run_test(test_dislodged_convoying_fleet_not_on_route)
    run_test(test_the_unwanted_alternative)
    run_test(test_simple_convoy_paradox)
    run_test(test_simple_convoy_paradox_with_additional_convoy)
    run_test(test_pandins_paradox)
    run_test(test_pandins_extended_paradox)
    run_test(test_betrayal_paradox)
    run_test(test_multi_route_convoy_disruption_paradox)
    run_test(test_unwanted_multi_route_convoy_paradox)
    run_test(test_dads_army_convoy)
    run_test(test_second_order_paradox_with_two_resolutions)
    run_test(test_second_order_paradox_with_two_exclusive_convoys)
    run_test(test_second_order_paradox_with_no_resolution)
    run_test(test_cut_support_last)
    print()

    # 6.G Convoying to Adjacent Provinces
    prefix = '6.G.'
    test_num = 1
    print('Convoying to Adjacent Provinces:')
    run_test(test_two_units_can_swap_provinces_by_convoy)
    run_test(test_kidnapping_an_army)
    run_test(test_unwanted_disrupted_convoy_to_adjacent_province)
    run_test(test_unwanted_disrupted_convoy_to_adjacent_province_and_opposite_move)
    run_test(test_swapping_with_multiple_fleets_with_one_own_fleet)
    run_test(test_swapping_with_unintended_intent)
    run_test(test_swapping_with_illegal_intent)
    run_test(test_explicit_convoy_that_isnt_there)
    run_test(test_swapped_or_dislodged)
    run_test(test_swapped_or_a_head_to_head_battle)
    run_test(test_convoy_to_an_adjacent_province_with_a_paradox)
    run_test(test_swapping_two_units_with_two_convoys)
    run_test(test_support_cut_on_attack_on_itself_via_convoy)
    run_test(test_bounce_by_convoy_to_adjacent_province)
    run_test(test_bounce_and_dislodge_with_double_convoy)
    run_test(test_the_two_unit_in_one_area_bug_moving_by_convoy)
    run_test(test_the_two_unit_in_one_area_bug_moving_over_land)
    run_test(test_the_two_unit_in_one_area_bug_with_double_convoy)
    run_test(test_swapping_with_intent_of_unnecessary_convoy)
    run_test(test_explicit_convoy_to_adjacent_province_disrupted)
    print()

    # 6.H Retreating
    prefix = '6.H.'
    test_num = 1
    print('Retreating:')
    run_test(test_no_supports_during_retreat)
    run_test(test_no_supports_from_retreating_unit)
    run_test(test_no_convoy_during_retreat)
    run_test(test_no_other_moves_during_retreat)
    run_test(test_unit_may_not_retreat_to_area_from_which_it_is_attacked)
    run_test(test_unit_may_not_retreat_to_a_contested_area)
    run_test(test_multiple_retreat_to_same_area_will_disband_units)
    run_test(test_triple_retreat_to_same_area_will_disband_units)
    run_test(test_dislodged_unit_will_not_make_attackers_area_contested)
    run_test(test_not_retreating_to_attackers_does_not_mean_contested)
    run_test(test_retreat_when_dislodged_by_adjacent_convoy)
    run_test(test_retreat_when_dislodged_by_adjacent_convoy_while_trying_to_do_the_same)
    run_test(test_no_retreat_with_convoy_in_movement_phase)
    run_test(test_no_retreat_with_support_in_movement_phase)
    run_test(test_no_coastal_crawl_in_retreat)
    run_test(test_contested_for_both_coasts)
    print()

    # 6.I Building
    prefix = '6.I.'
    test_num = 1
    print('Building:')
    run_test(test_too_many_build_orders)
    run_test(test_fleets_cannot_be_built_in_land_areas)
    run_test(test_supply_center_must_be_empty_for_building)
    run_test(test_both_coasts_must_be_empty_for_building)
    run_test(test_building_in_home_supply_center_that_is_not_owned)
    run_test(test_building_in_owned_supply_center_that_is_not_a_home_supply_center)
    run_test(test_only_one_build_in_a_home_supply_center)
    print()

    # 6.J Civil Disorder and Disbands
    prefix = '6.J.'
    test_num = 1
    print('Civil Disorder and Disbands:')
    run_test(test_too_many_disband_orders)
    run_test(test_removing_the_same_unit_twice)
    run_test(test_civil_disorder_two_armies_with_different_distance)
    run_test(test_civil_disorder_two_armies_with_equal_distance)
    run_test(test_civil_disorder_two_fleets_with_different_distance)
    run_test(test_civil_disorder_two_fleets_with_equal_distance)
    run_test(test_civil_disorder_two_fleets_and_army_with_equal_distance)
    run_test(test_civil_disorder_a_fleet_with_shorter_distance_than_the_army)
    run_test(test_civil_disorder_must_be_counted_from_both_coasts)
    run_test(test_civil_disorder_counting_convoying_distance)
    run_test(test_distance_to_owned_supply_center)
    print()

    # T Transform Orders
    prefix = 'T.'
    test_num = 1
    print('Transform Orders:')
    run_test(test_transform_coastal_army)
    run_test(test_transform_inland_army)
    run_test(test_transform_coastal_fleet)
    run_test(test_transform_coastal_army_to_south_coast)
    run_test(test_transform_coastal_army_to_invalid_south_coast)
    run_test(test_transform_fleet_in_water)
    run_test(test_dislodged_army_cannot_transform)
    print()

    print(f'{passed}/{count} Tests Passed')

if __name__ == '__main__':
    main()