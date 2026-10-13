from player import Player
from territory import Territory
from unit import Unit
from map import Map
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
    return Map(silent_mode=True, start_phase='Spring', load_rendering_data=False)

def add_army(territory, owner):
    unit = Unit(owner, 'Army', territory)
    territory.set_unit(unit)
    owner.add_unit(unit)
    return unit

def add_fleet(territory, owner, coast=None):
    unit = Unit(owner, 'Fleet', territory)
    territory.set_unit(unit, coast=coast)
    owner.add_unit(unit)
    return unit

# 6.A Basic Checks
# 6.A.1
def test_advance_not_neighbor():
    map = get_classic_map()
    unit = add_fleet(map.north_sea, map.england)
    map.parse_order_string('F NTH - PIC')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

# 6.A.2
def test_move_army_to_sea():
    map = get_classic_map()
    unit = add_army(map.liverpool, map.england)
    map.parse_order_string('A LPL - IRI')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

# 6.A.3
def test_move_fleet_to_land():
    map = get_classic_map()
    unit = add_fleet(map.kiel, map.germany)
    map.parse_order_string('F KIE - MUC')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

# 6.A.4
def test_move_to_own_territory():
    map = get_classic_map()
    unit = add_fleet(map.kiel, map.germany)
    map.parse_order_string('F KIE - KIE')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

# 6.A.5
def test_move_to_own_territory_with_convoy():
    map = get_classic_map()
    english_unit1 = add_fleet(map.north_sea, map.england)
    english_unit2 = add_army(map.yorkshire, map.england)
    english_unit3 = add_army(map.liverpool, map.england)
    german_unit1 = add_fleet(map.london, map.germany)
    german_unit2 = add_army(map.wales, map.germany)

    map.parse_order_string('F NTH C A YOR - YOR')
    map.parse_order_string('A YOR - YOR')
    map.parse_order_string('A LPL S A YOR - YOR')
    map.parse_order_string('F LON - YOR')
    map.parse_order_string('A WAL S F LON - YOR')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    # English army's move is illegal. This makes Liverpool's support illegal
    # This allows the Germans to have the stronger force and dislodge the army in Yorkshire
    assert_equal('English Fleet Territory', english_unit1.territory, map.north_sea)
    assert_not_equal('English Army 1 Territory', english_unit2.territory, map.yorkshire)
    assert_equal('English Army 2 Territory', english_unit3.territory, map.liverpool)
    assert_equal('German Fleet Territory', german_unit1.territory, map.yorkshire)
    assert_equal('German Army Territory', german_unit2.territory, map.wales)

# 6.A.6
def test_ordering_other_countrys_unit():
    map = get_classic_map()
    unit = add_fleet(map.london, map.england)
    map.parse_order_string('F LON - NTH', owner=map.germany)
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

# 6.A.7
def test_only_convoy_armies():
    map = get_classic_map()
    unit1 = add_fleet(map.london, map.england)
    unit2 = add_fleet(map.north_sea, map.england)

    map.parse_order_string('F LON - BEL')
    map.parse_order_string('F NTH C A LON - BEL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Fleet 1 Territory', unit1.territory, map.london)
    assert_equal('Fleet 2 Territory', unit2.territory, map.north_sea)

# 6.A.8
def test_support_hold_yourself_fails():
    map = get_classic_map()
    italian_army1 = add_army(map.venice, map.italy)
    italian_army2 = add_army(map.tyrolia, map.italy)
    austrian_fleet = add_fleet(map.trieste, map.austria_hungary)

    map.parse_order_string('A VEN - TRI')
    map.parse_order_string('A TYR S A VEN - TRI')
    map.parse_order_string('F TRI S F TRI')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 2)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.trieste)
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.tyrolia)
    assert_not_equal('Austrian Fleet Territory', austrian_fleet.territory, map.trieste)

# 6.A.9
def test_fleets_must_follow_coast_if_not_sea():
    map = get_classic_map()
    italian_fleet = add_fleet(map.rome, map.italy)
    map.parse_order_string('F ROM - VEN')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

# 6.A.10
def test_support_unreachable_territory_impossible():
    map = get_classic_map()
    austrian_army = add_army(map.venice, map.austria_hungary)
    italian_fleet = add_fleet(map.rome, map.italy)
    italian_army = add_army(map.apulia, map.italy)

    map.parse_order_string('A VEN H')
    map.parse_order_string('F ROM S A APU - VEN')
    map.parse_order_string('A APU - VEN')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 2)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Army Territory', austrian_army.territory, map.venice)
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.rome)
    assert_equal('Italian Army Territory', italian_army.territory, map.apulia)

# 6.A.11
def test_simple_bounce():
    map = get_classic_map()
    austrian_army = add_army(map.vienna, map.austria_hungary)
    italian_army = add_army(map.venice, map.italy)

    map.parse_order_string('A VIE - TYR')
    map.parse_order_string('A VEN - TYR')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 2)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Army Territory', austrian_army.territory, map.vienna)
    assert_equal('Italian Army Territory', italian_army.territory, map.venice)

# 6.A.12
def test_triple_bounce():
    map = get_classic_map()
    austrian_army = add_army(map.vienna, map.austria_hungary)
    german_army = add_army(map.munich, map.germany)
    italian_army = add_army(map.venice, map.italy)

    map.parse_order_string('A VIE - TYR')
    map.parse_order_string('A MUC - TYR')
    map.parse_order_string('A VEN - TYR')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Army Territory', austrian_army.territory, map.vienna)
    assert_equal('German Army Territory', german_army.territory, map.munich)
    assert_equal('Italian Army Territory', italian_army.territory, map.venice)

# 6.B Coastal Issues
# 6.B.1
def test_move_unspecified_coast_when_necessary():
    map = get_classic_map()
    french_fleet = add_fleet(map.portugal, map.france)

    map.parse_order_string('F POR - SPA')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

# 6.B.2
def test_move_unspecified_coast_when_not_necessary():
    map = get_classic_map()
    french_fleet = add_fleet(map.gascony, map.france)

    map.parse_order_string('F GAS - SPA')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet Territory', french_fleet.territory, map.spain)

# 6.B.3
def test_move_wrong_coast_when_not_necessary():
    map = get_classic_map()
    french_fleet = add_fleet(map.gascony, map.france)

    map.parse_order_string('F GAS - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

# 6.B.4
def test_support_to_unreachable_coast_allowed():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.gascony, map.france)
    french_fleet2 = add_fleet(map.marseilles, map.france)
    italian_fleet = add_fleet(map.western_mediterranean, map.italy)

    map.parse_order_string('F GAS - SPA(nc)')
    map.parse_order_string('F MAR S F GAS - SPA(nc)')
    map.parse_order_string('F WES - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.spain)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.marseilles)
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.western_mediterranean)

# 6.B.5
def test_support_from_unreachable_coast_not_allowed():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.marseilles, map.france)
    french_fleet2 = add_fleet(map.spain, map.france, coast=0)
    italian_fleet = add_fleet(map.gulf_of_lyon, map.italy)

    map.parse_order_string('F MAR - LYO')
    map.parse_order_string('F SPA S F MAR - LYO')
    map.parse_order_string('F LYO H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 2)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.marseilles)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.spain)
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.gulf_of_lyon)

# 6.B.6
def test_support_cut_from_other_coast():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.irish_sea, map.england)
    english_fleet2 = add_fleet(map.north_atlantic_ocean, map.england)
    french_fleet1 = add_fleet(map.spain, map.france, coast=0)
    french_fleet2 = add_fleet(map.mid_atlantic_ocean, map.france)
    italian_fleet = add_fleet(map.gulf_of_lyon, map.italy)

    map.parse_order_string('F IRI S F NAO - MAO')
    map.parse_order_string('F NAO - MAO')
    map.parse_order_string('F SPA S F MAO H')
    map.parse_order_string('F MAO H')
    map.parse_order_string('F LYO - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.irish_sea)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.mid_atlantic_ocean)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.spain)
    assert_not_equal('French Fleet 2 Territory', french_fleet2.territory, map.mid_atlantic_ocean)
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.gulf_of_lyon)

# 6.B.7
def test_support_own_unit_with_unspecified_coast():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.portugal, map.france)
    french_fleet2 = add_fleet(map.mid_atlantic_ocean, map.france)
    italian_fleet1 = add_fleet(map.gulf_of_lyon, map.italy)
    italian_fleet2 = add_fleet(map.western_mediterranean, map.italy)

    map.parse_order_string('F POR S F MAO - SPA')
    map.parse_order_string('F MAO - SPA(nc)')
    map.parse_order_string('F LYO S F WES - SPA(sc)')
    map.parse_order_string('F WES - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.portugal)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.mid_atlantic_ocean)
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.gulf_of_lyon)
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.western_mediterranean)

# 6.B.8
def test_support_with_unspecified_coast_when_only_one_coast_possible():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.portugal, map.france)
    french_fleet2 = add_fleet(map.gascony, map.france)
    italian_fleet1 = add_fleet(map.gulf_of_lyon, map.italy)
    italian_fleet2 = add_fleet(map.western_mediterranean, map.italy)

    map.parse_order_string('F POR S F GAS - SPA')
    map.parse_order_string('F GAS - SPA(nc)')
    map.parse_order_string('F LYO S F WES - SPA(sc)')
    map.parse_order_string('F WES - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.portugal)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.gascony)
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.gulf_of_lyon)
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.western_mediterranean)

# 6.B.9
def test_support_with_wrong_coast():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.portugal, map.france)
    french_fleet2 = add_fleet(map.mid_atlantic_ocean, map.france)
    italian_fleet1 = add_fleet(map.gulf_of_lyon, map.italy)
    italian_fleet2 = add_fleet(map.western_mediterranean, map.italy)

    map.parse_order_string('F POR S F MAO - SPA(nc)')
    map.parse_order_string('F MAO - SPA(sc)')
    map.parse_order_string('F LYO S F WES - SPA(sc)')
    map.parse_order_string('F WES - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.portugal)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.mid_atlantic_ocean)
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.gulf_of_lyon)
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.spain)

# 6.B.10
# This assumes we allow specifying moves like F SPA(nc) - LYO. We don't allow coast specifications on start territory

# 6.B.11
def test_coast_cannot_be_ordered_to_change():
    map = get_classic_map()
    french_fleet = add_fleet(map.spain, map.france, coast=0)

    map.parse_order_string('F SPA - LYO')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

# 6.B.12
def test_army_movement_with_coastal_specifications():
    map = get_classic_map()
    french_army = add_army(map.gascony, map.france)

    map.parse_order_string('A GAS - SPA(nc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.spain)

# 6.B.13
def test_coastal_crawl_not_allowed():
    map = get_classic_map()
    turkish_fleet1 = add_fleet(map.bulgaria, map.turkey, coast=1)
    turkish_fleet2 = add_fleet(map.constantinople, map.turkey)

    map.parse_order_string('F BUL - CON')
    map.parse_order_string('F CON - BUL(nc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 2)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Turkish Fleet 1 Territory', turkish_fleet1.territory, map.bulgaria)
    assert_equal('Turkish Fleet 2 Territory', turkish_fleet2.territory, map.constantinople)

# 6.B.14
def test_building_unspecified_coast():
    map = get_classic_map()
    map.parse_order_string('Build F STP')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

# 6.B.15
def test_support_foreign_unit_unspecified_coast():
    map = get_classic_map()
    french_fleet = add_fleet(map.portugal, map.france)
    english_fleet = add_fleet(map.mid_atlantic_ocean, map.england)
    italian_fleet1 = add_fleet(map.gulf_of_lyon, map.italy)
    italian_fleet2 = add_fleet(map.western_mediterranean, map.italy)

    map.parse_order_string('F POR S F MAO - SPA')
    map.parse_order_string('F MAO - SPA(nc)')
    map.parse_order_string('F LYO S F WES - SPA(sc)')
    map.parse_order_string('F WES - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet Territory', french_fleet.territory, map.portugal)
    assert_equal('English Fleet Territory', english_fleet.territory, map.mid_atlantic_ocean)
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.gulf_of_lyon)
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.western_mediterranean)

# 6.C Circular Movement
# 6.C.1
def test_three_army_circular_movement():
    map = get_classic_map()
    turkish_fleet = add_fleet(map.ankara, map.turkey)
    turkish_army1 = add_army(map.constantinople, map.turkey)
    turkish_army2 = add_army(map.smyrna, map.turkey)

    map.parse_order_string('F ANK - CON')
    map.parse_order_string('A CON - SMY')
    map.parse_order_string('A SMY - ANK')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.constantinople)
    assert_equal('Turkish Army 1 Territory', turkish_army1.territory, map.smyrna)
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.ankara)

# 6.C.2
def test_three_army_circular_movement_with_support():
    map = get_classic_map()
    turkish_fleet = add_fleet(map.ankara, map.turkey)
    turkish_army1 = add_army(map.constantinople, map.turkey)
    turkish_army2 = add_army(map.smyrna, map.turkey)
    turkish_army3 = add_army(map.bulgaria, map.turkey)

    map.parse_order_string('F ANK - CON')
    map.parse_order_string('A CON - SMY')
    map.parse_order_string('A SMY - ANK')
    map.parse_order_string('A BUL S F ANK - CON') 
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.constantinople)
    assert_equal('Turkish Army 1 Territory', turkish_army1.territory, map.smyrna)
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.ankara)
    assert_equal('Turkish Army 3 Territory', turkish_army3.territory, map.bulgaria)

# 6.C.3
def test_disrupted_three_army_circular_movement():
    map = get_classic_map()
    turkish_fleet = add_fleet(map.ankara, map.turkey)
    turkish_army1 = add_army(map.constantinople, map.turkey)
    turkish_army2 = add_army(map.smyrna, map.turkey)
    turkish_army3 = add_army(map.bulgaria, map.turkey)

    map.parse_order_string('F ANK - CON')
    map.parse_order_string('A CON - SMY')
    map.parse_order_string('A SMY - ANK')
    map.parse_order_string('A BUL - CON')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.ankara)
    assert_equal('Turkish Army 1 Territory', turkish_army1.territory, map.constantinople)
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.smyrna)
    assert_equal('Turkish Army 3 Territory', turkish_army3.territory, map.bulgaria)

# 6.C.4
def test_circular_movement_with_attacked_convoy():
    map = get_classic_map()
    austrian_army1 = add_army(map.trieste, map.austria_hungary)
    austrian_army2 = add_army(map.serbia, map.austria_hungary)
    turkish_army = add_army(map.bulgaria, map.turkey)
    turkish_fleet1 = add_fleet(map.aegean_sea, map.turkey)
    turkish_fleet2 = add_fleet(map.ionian_sea, map.turkey)
    turkish_fleet3 = add_fleet(map.adriatic_sea, map.turkey)
    italian_fleet = add_fleet(map.naples, map.italy)

    map.parse_order_string('A TRI - SER')
    map.parse_order_string('A SER - BUL')
    map.parse_order_string('A BUL - TRI')
    map.parse_order_string('F AEG C A BUL - TRI')
    map.parse_order_string('F ION C A BUL - TRI')
    map.parse_order_string('F ADR C A BUL - TRI')
    map.parse_order_string('F NAP - ION')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 7)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.serbia)
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.bulgaria)
    assert_equal('Turkish Army Territory', turkish_army.territory, map.trieste)
    assert_equal('Turkish Fleet 1 Territory', turkish_fleet1.territory, map.aegean_sea)
    assert_equal('Turkish Fleet 2 Territory', turkish_fleet2.territory, map.ionian_sea)
    assert_equal('Turkish Fleet 3 Territory', turkish_fleet3.territory, map.adriatic_sea)
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.naples)

# 6.C.5
def test_disrupted_circular_movement_dislodged_convoy():
    map = get_classic_map()
    austrian_army1 = add_army(map.trieste, map.austria_hungary)
    austrian_army2 = add_army(map.serbia, map.austria_hungary)
    turkish_army = add_army(map.bulgaria, map.turkey)
    turkish_fleet1 = add_fleet(map.aegean_sea, map.turkey)
    turkish_fleet2 = add_fleet(map.ionian_sea, map.turkey)
    turkish_fleet3 = add_fleet(map.adriatic_sea, map.turkey)
    italian_fleet1 = add_fleet(map.naples, map.italy)
    italian_fleet2 = add_fleet(map.tunis, map.italy)

    map.parse_order_string('A TRI - SER')
    map.parse_order_string('A SER - BUL')
    map.parse_order_string('A BUL - TRI')
    map.parse_order_string('F AEG C A BUL - TRI')
    map.parse_order_string('F ION C A BUL - TRI')
    map.parse_order_string('F ADR C A BUL - TRI')
    map.parse_order_string('F NAP - ION')
    map.parse_order_string('F TUN S F NAP - ION')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 8)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.trieste)
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.serbia)
    assert_equal('Turkish Army Territory', turkish_army.territory, map.bulgaria)
    assert_equal('Turkish Fleet 1 Territory', turkish_fleet1.territory, map.aegean_sea)
    assert_not_equal('Turkish Fleet 2 Territory', turkish_fleet2.territory, map.ionian_sea)
    assert_equal('Turkish Fleet 3 Territory', turkish_fleet3.territory, map.adriatic_sea)
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.ionian_sea)
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.tunis)

# 6.C.6
def test_two_armies_two_convoys():
    map = get_classic_map()
    english_fleet = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.london, map.england)
    french_fleet = add_fleet(map.english_channel, map.france)
    french_army = add_army(map.belgium, map.france)

    map.parse_order_string('F NTH C A LON - BEL')
    map.parse_order_string('A LON - BEL')
    map.parse_order_string('F ENG C A BEL - LON')
    map.parse_order_string('A BEL - LON')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_equal('English Army Territory', english_army.territory, map.belgium)
    assert_equal('French Fleet Territory', french_fleet.territory, map.english_channel)
    assert_equal('French Army Territory', french_army.territory, map.london)

# 6.C.7
def test_disrupted_unit_swap():
    map = get_classic_map()
    english_fleet = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.london, map.england)
    french_fleet = add_fleet(map.english_channel, map.france)
    french_army1 = add_army(map.belgium, map.france)
    french_army2 = add_army(map.burgundy, map.france)

    map.parse_order_string('F NTH C A LON - BEL')
    map.parse_order_string('A LON - BEL')
    map.parse_order_string('F ENG C A BEL - LON')
    map.parse_order_string('A BEL - LON')
    map.parse_order_string('A BUR - BEL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_equal('English Army Territory', english_army.territory, map.london)
    assert_equal('French Fleet Territory', french_fleet.territory, map.english_channel)
    assert_equal('French Army 1 Territory', french_army1.territory, map.belgium)
    assert_equal('French Army 2 Territory', french_army2.territory, map.burgundy)

# 6.C.8
def test_no_self_dislodgement_in_disrupted_circular_movement():
    map = get_classic_map()
    turkish_fleet = add_fleet(map.constantinople, map.turkey)
    turkish_army1 = add_army(map.bulgaria, map.turkey)
    turkish_army2 = add_army(map.smyrna, map.turkey)
    russian_fleet = add_fleet(map.black_sea, map.russia)
    austrian_army = add_army(map.serbia, map.austria_hungary)

    map.parse_order_string('F CON - BLA')
    map.parse_order_string('A BUL - CON')
    map.parse_order_string('A SMY S A BUL - CON')
    map.parse_order_string('F BLA - BUL(nc)')
    map.parse_order_string('A SER - BUL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.constantinople)
    assert_equal('Turkish Army 1 Territory', turkish_army1.territory, map.bulgaria)
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.smyrna)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.black_sea)
    assert_equal('Austrian Army Territory', austrian_army.territory, map.serbia)
    
# 6.C.9
def test_no_help_in_dislodgement_of_own_unit_in_disrupted_circular_movement():
    map = get_classic_map()
    turkish_fleet = add_fleet(map.constantinople, map.turkey)
    turkish_army = add_army(map.smyrna, map.turkey)
    russian_fleet = add_fleet(map.black_sea, map.russia)
    austrian_army1 = add_army(map.serbia, map.austria_hungary)
    austrian_army2 = add_army(map.bulgaria, map.austria_hungary)

    map.parse_order_string('F CON - BLA')
    map.parse_order_string('A SMY S A BUL - CON')
    map.parse_order_string('F BLA - BUL(nc)')
    map.parse_order_string('A SER - BUL')
    map.parse_order_string('A BUL - CON')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.constantinople)
    assert_equal('Turkish Army Territory', turkish_army.territory, map.smyrna)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.black_sea)
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.serbia)
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.bulgaria)

# 6.D Supports and Dislodges
# 6.D.1
def test_supported_hold_can_prevent_dislodgement():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.adriatic_sea, map.austria_hungary)
    austrian_army = add_army(map.trieste, map.austria_hungary)
    italian_army1 = add_army(map.venice, map.italy)
    italian_army2 = add_army(map.tyrolia, map.italy)

    map.parse_order_string('F ADR S A TRI - VEN')
    map.parse_order_string('A TRI - VEN')
    map.parse_order_string('A VEN H')
    map.parse_order_string('A TYR S A VEN H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.adriatic_sea)
    assert_equal('Austrian Army Territory', austrian_army.territory, map.trieste)
    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.venice)
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.tyrolia)

# 6.D.2
def test_move_cuts_support_on_hold():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.adriatic_sea, map.austria_hungary)
    austrian_army1 = add_army(map.trieste, map.austria_hungary)
    austrian_army2 = add_army(map.vienna, map.austria_hungary)
    italian_army1 = add_army(map.venice, map.italy)
    italian_army2 = add_army(map.tyrolia, map.italy)

    map.parse_order_string('F ADR S A TRI - VEN')
    map.parse_order_string('A TRI - VEN')
    map.parse_order_string('A VIE - TYR')
    map.parse_order_string('A VEN H')
    map.parse_order_string('A TYR S A VEN H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.adriatic_sea)
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.venice)
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.vienna)
    assert_not_equal('Italian Army 1 Territory', italian_army1.territory, map.venice)
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.tyrolia)

# 6.D.3
def test_move_cuts_support_on_move():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.adriatic_sea, map.austria_hungary)
    austrian_army = add_army(map.trieste, map.austria_hungary)
    italian_army = add_army(map.venice, map.italy)
    italian_fleet = add_fleet(map.ionian_sea, map.italy)

    map.parse_order_string('F ADR S A TRI - VEN')
    map.parse_order_string('A TRI - VEN')
    map.parse_order_string('A VEN H')
    map.parse_order_string('F ION - ADR')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.adriatic_sea)
    assert_equal('Austrian Army Territory', austrian_army.territory, map.trieste)
    assert_equal('Italian Army Territory', italian_army.territory, map.venice)
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.ionian_sea)

# 6.D.4
def test_support_to_hold_on_unit_supporting_hold_allowed():
    map = get_classic_map()
    german_army = add_army(map.berlin, map.germany)
    german_fleet = add_fleet(map.kiel, map.germany)
    russian_fleet = add_fleet(map.baltic_sea, map.russia)
    russian_army = add_army(map.prussia, map.russia)

    map.parse_order_string('A BER S F KIE H')
    map.parse_order_string('F KIE S A BER H')
    map.parse_order_string('F BAL S A PRU - BER')
    map.parse_order_string('A PRU - BER')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('German Army Territory', german_army.territory, map.berlin)
    assert_equal('German Fleet Territory', german_fleet.territory, map.kiel)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.baltic_sea)
    assert_equal('Russian Army Territory', russian_army.territory, map.prussia)

# 6.D.5
def test_support_to_hold_on_unit_supporting_move_allowed():
    map = get_classic_map()
    german_army1 = add_army(map.berlin, map.germany)
    german_fleet = add_fleet(map.kiel, map.germany)
    german_army2 = add_army(map.munich, map.germany)
    russian_fleet = add_fleet(map.baltic_sea, map.russia)
    russian_army = add_army(map.prussia, map.russia)

    map.parse_order_string('A BER S A MUC - SIL')
    map.parse_order_string('F KIE S A BER H')
    map.parse_order_string('A MUC - SIL')
    map.parse_order_string('F BAL S A PRU - BER')
    map.parse_order_string('A PRU - BER')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('German Army 1 Territory', german_army1.territory, map.berlin)
    assert_equal('German Fleet Territory', german_fleet.territory, map.kiel)
    assert_equal('German Army 2 Territory', german_army2.territory, map.silesia)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.baltic_sea)
    assert_equal('Russian Army Territory', russian_army.territory, map.prussia)

# 6.D.6
def test_support_to_hold_on_convoying_unit_allowed():
    map = get_classic_map()
    german_army = add_army(map.berlin, map.germany)
    german_fleet1 = add_fleet(map.baltic_sea, map.germany)
    german_fleet2 = add_fleet(map.prussia, map.germany)
    russian_fleet1 = add_fleet(map.livonia, map.russia)
    russian_fleet2 = add_fleet(map.gulf_of_bothnia, map.russia)

    map.parse_order_string('A BER - SWE')
    map.parse_order_string('F BAL C A BER - SWE')
    map.parse_order_string('F PRU S F BAL H')
    map.parse_order_string('F LIV - BAL')
    map.parse_order_string('F BOT S F LIV - BAL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('German Army Territory', german_army.territory, map.sweden)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.baltic_sea)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.prussia)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.livonia)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.gulf_of_bothnia)

# 6.D.7
def test_support_to_hold_on_moving_unit_not_allowed():
    map = get_classic_map()
    german_fleet1 = add_fleet(map.baltic_sea, map.germany)
    german_fleet2 = add_fleet(map.prussia, map.germany)
    russian_fleet1 = add_fleet(map.livonia, map.russia)
    russian_fleet2 = add_fleet(map.gulf_of_bothnia, map.russia)
    russian_army = add_army(map.finland, map.russia)

    map.parse_order_string('F BAL - SWE')
    map.parse_order_string('F PRU S F BAL H')
    map.parse_order_string('F LIV - BAL')
    map.parse_order_string('F BOT S F LIV - BAL')
    map.parse_order_string('A FIN - SWE')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_not_equal('German Fleet 1 Territory', german_fleet1.territory, map.baltic_sea)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.prussia)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.baltic_sea)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.gulf_of_bothnia)
    assert_equal('Russian Army Territory', russian_army.territory, map.finland)

# 6.D.8
def test_failed_convoy_cannot_receive_hold_support():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.ionian_sea, map.austria_hungary)
    austrian_army1 = add_army(map.serbia, map.austria_hungary)
    austrian_army2 = add_army(map.albania, map.austria_hungary)
    turkish_army1 = add_army(map.greece, map.turkey)
    turkish_army2 = add_army(map.bulgaria, map.turkey)

    map.parse_order_string('F ION H')
    map.parse_order_string('A SER S A ALB - GRE')
    map.parse_order_string('A ALB - GRE')
    map.parse_order_string('A GRE - NAP')
    map.parse_order_string('A BUL S A GRE H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.ionian_sea)
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.serbia)
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.greece)
    assert_not_equal('Turkish Army 1 Territory', turkish_army1.territory, map.greece)
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.bulgaria)

# 6.D.9
def test_support_to_move_on_holding_unit_not_allowed():
    map = get_classic_map()
    italian_army1 = add_army(map.venice, map.italy)
    italian_army2 = add_army(map.tyrolia, map.italy)
    austrian_army1 = add_army(map.albania, map.austria_hungary)
    austrian_army2 = add_army(map.trieste, map.austria_hungary)

    map.parse_order_string('A VEN - TRI')
    map.parse_order_string('A TYR S A VEN - TRI')
    map.parse_order_string('A ALB S A TRI - SER')
    map.parse_order_string('A TRI H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.trieste)
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.tyrolia)
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.albania)
    assert_not_equal('Austrian Army 2 Territory', austrian_army2.territory, map.trieste)

# 6.D.10
def test_self_dislodgement_prohibited():
    map = get_classic_map()
    german_army1 = add_army(map.berlin, map.germany)
    german_fleet = add_fleet(map.kiel, map.germany)
    german_army2 = add_army(map.munich, map.germany)

    map.parse_order_string('A BER H')
    map.parse_order_string('F KIE - BER')
    map.parse_order_string('A MUC S F KIE - BER')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Army 1 Territory', german_army1.territory, map.berlin)
    assert_equal('German Fleet Territory', german_fleet.territory, map.kiel)
    assert_equal('German Army 2 Territory', german_army2.territory, map.munich)

# 6.D.11
def test_no_self_dislodgement_of_returning_unit():
    map = get_classic_map()
    german_army1 = add_army(map.berlin, map.germany)
    german_fleet = add_fleet(map.kiel, map.germany)
    german_army2 = add_army(map.munich, map.germany)
    russian_army = add_army(map.warsaw, map.russia)

    map.parse_order_string('A BER - PRU')
    map.parse_order_string('F KIE - BER')
    map.parse_order_string('A MUC S F KIE - BER')
    map.parse_order_string('A WAR - PRU')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Army 1 Territory', german_army1.territory, map.berlin)
    assert_equal('German Fleet Territory', german_fleet.territory, map.kiel)
    assert_equal('German Army 2 Territory', german_army2.territory, map.munich)
    assert_equal('Russian Army Territory', russian_army.territory, map.warsaw)

# 6.D.12
def test_supporting_foreign_unit_to_dislodge_own_unit_prohibited():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.trieste, map.austria_hungary)
    austrian_army = add_army(map.vienna, map.austria_hungary)
    italian_army = add_army(map.venice, map.italy)

    map.parse_order_string('F TRI H')
    map.parse_order_string('A VIE S A VEN - TRI')
    map.parse_order_string('A VEN - TRI')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.trieste)
    assert_equal('Austrian Army Territory', austrian_army.territory, map.vienna)
    assert_equal('Italian Army Territory', italian_army.territory, map.venice)

# 6.D.13
def test_supporting_foreign_unit_to_dislodge_returning_own_unit_prohibited():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.trieste, map.austria_hungary)
    austrian_army = add_army(map.vienna, map.austria_hungary)
    italian_army = add_army(map.venice, map.italy)
    italian_fleet = add_fleet(map.apulia, map.italy)

    map.parse_order_string('F TRI - ADR')
    map.parse_order_string('A VIE S A VEN - TRI')
    map.parse_order_string('A VEN - TRI')
    map.parse_order_string('F APU - ADR')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.trieste)
    assert_equal('Austrian Army Territory', austrian_army.territory, map.vienna)
    assert_equal('Italian Army Territory', italian_army.territory, map.venice)
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.apulia)

# 6.D.14
def test_supporting_foreign_unit_not_enough_to_prevent_dislodgement():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.trieste, map.austria_hungary)
    austrian_army = add_army(map.vienna, map.austria_hungary)
    italian_army1 = add_army(map.venice, map.italy)
    italian_army2 = add_army(map.tyrolia, map.italy)
    italian_fleet = add_fleet(map.adriatic_sea, map.italy)

    map.parse_order_string('F TRI - ADR')
    map.parse_order_string('A VIE S A VEN - TRI')
    map.parse_order_string('A VEN - TRI')
    map.parse_order_string('A TYR S A VEN - TRI')
    map.parse_order_string('F ADR S A VEN - TRI')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('Austrian Fleet Territory', austrian_fleet.territory, map.trieste)
    assert_equal('Austrian Army Territory', austrian_army.territory, map.vienna)
    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.trieste)
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.tyrolia)
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.adriatic_sea)

# 6.D.15
def test_defender_cannot_cut_support_for_attack_on_itself():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.constantinople, map.russia)
    russian_fleet2 = add_fleet(map.black_sea, map.russia)
    turkish_fleet = add_fleet(map.ankara, map.turkey)

    map.parse_order_string('F CON S F BLA - ANK')
    map.parse_order_string('F BLA - ANK')
    map.parse_order_string('F ANK - CON')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.constantinople)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.ankara)
    assert_not_equal('Turkish Fleet Territory', turkish_fleet.territory, map.ankara)

# 6.D.16
def test_convoying_unit_dislodging_unit_of_same_power_allowed():
    map = get_classic_map()
    english_army = add_army(map.london, map.england)
    english_fleet = add_fleet(map.north_sea, map.england)
    french_fleet = add_fleet(map.english_channel, map.france)
    french_army = add_army(map.belgium, map.france)

    map.parse_order_string('A LON H')
    map.parse_order_string('F NTH C A BEL - LON')
    map.parse_order_string('F ENG S A BEL - LON')
    map.parse_order_string('A BEL - LON')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('English Army Territory', english_army.territory, map.london)
    assert_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_equal('French Fleet Territory', french_fleet.territory, map.english_channel)
    assert_equal('French Army Territory', french_army.territory, map.london)

# 6.D.17
def test_dislodgement_cuts_support():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.constantinople, map.russia)
    russian_fleet2 = add_fleet(map.black_sea, map.russia)
    turkish_fleet = add_fleet(map.ankara, map.turkey)
    turkish_army1 = add_army(map.smyrna, map.turkey)
    turkish_army2 = add_army(map.armenia, map.turkey)

    map.parse_order_string('F CON S F BLA - ANK')
    map.parse_order_string('F BLA - ANK')
    map.parse_order_string('F ANK - CON')
    map.parse_order_string('A SMY S F ANK - CON')
    map.parse_order_string('A ARM - ANK')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.constantinople)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.black_sea)
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.constantinople)
    assert_equal('Turkish Army 1 Territory', turkish_army1.territory, map.smyrna)
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.armenia)

# 6.D.18
def test_surviving_unit_will_sustain_support():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.constantinople, map.russia)
    russian_fleet2 = add_fleet(map.black_sea, map.russia)
    russian_army = add_army(map.bulgaria, map.russia)
    turkish_fleet = add_fleet(map.ankara, map.turkey)
    turkish_army1 = add_army(map.smyrna, map.turkey)
    turkish_army2 = add_army(map.armenia, map.turkey)

    map.parse_order_string('F CON S F BLA - ANK')
    map.parse_order_string('F BLA - ANK')
    map.parse_order_string('A BUL S F CON H')
    map.parse_order_string('F ANK - CON')
    map.parse_order_string('A SMY S F ANK - CON')
    map.parse_order_string('A ARM - ANK')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.constantinople)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.ankara)
    assert_equal('Russian Army Territory', russian_army.territory, map.bulgaria)
    assert_not_equal('Turkish Fleet Territory', turkish_fleet.territory, map.ankara)
    assert_equal('Turkish Army 1 Territory', turkish_army1.territory, map.smyrna)
    assert_equal('Turkish Army 2 Territory', turkish_army2.territory, map.armenia)

# 6.D.19
def test_even_when_surviving_is_in_alternative_way():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.constantinople, map.russia)
    russian_fleet2 = add_fleet(map.black_sea, map.russia)
    russian_army = add_army(map.smyrna, map.russia)
    turkish_fleet = add_fleet(map.ankara, map.turkey)

    map.parse_order_string('F CON S F BLA - ANK')
    map.parse_order_string('F BLA - ANK')
    map.parse_order_string('A SMY S F ANK - CON')
    map.parse_order_string('F ANK - CON')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.constantinople)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.ankara)
    assert_equal('Russian Army Territory', russian_army.territory, map.smyrna)
    assert_not_equal('Turkish Fleet Territory', turkish_fleet.territory, map.ankara)

# 6.D.20
def test_unit_cannot_cut_support_of_its_own_country():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.london, map.england)
    english_fleet2 = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.yorkshire, map.england)
    french_fleet = add_fleet(map.english_channel, map.france)

    map.parse_order_string('F LON S F NTH - ENG')
    map.parse_order_string('F NTH - ENG')
    map.parse_order_string('A YOR - LON')
    map.parse_order_string('F ENG H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.london)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.english_channel)
    assert_equal('English Army Territory', english_army.territory, map.yorkshire)
    assert_not_equal('French Fleet Territory', french_fleet.territory, map.english_channel)

# 6.D.21
def test_dislodging_dows_not_cancel_a_support_cut():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.trieste, map.austria_hungary)
    italian_army1 = add_army(map.venice, map.italy)
    italian_army2 = add_army(map.tyrolia, map.italy)
    german_army = add_army(map.munich, map.germany)
    russian_army1 = add_army(map.silesia, map.russia)
    russian_army2 = add_army(map.berlin, map.russia)

    map.parse_order_string('F TRI H')
    map.parse_order_string('A VEN - TRI')
    map.parse_order_string('A TYR S A VEN - TRI')
    map.parse_order_string('A MUC - TYR')
    map.parse_order_string('A SIL - MUC')
    map.parse_order_string('A BER S A SIL - MUC')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.trieste)
    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.venice)
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.tyrolia)
    assert_not_equal('German Army Territory', german_army.territory, map.munich)
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.munich)
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.berlin)

# 6.D.22
def test_impossible_fleet_move_cannot_be_supported():
    map = get_classic_map()
    german_fleet = add_fleet(map.kiel, map.germany)
    german_army = add_army(map.burgundy, map.germany)
    russian_army1 = add_army(map.munich, map.russia)
    russian_army2 = add_army(map.berlin, map.russia)

    map.parse_order_string('F KIE - MUC')
    map.parse_order_string('A BUR S F KIE - MUC')
    map.parse_order_string('A MUC - KIE')
    map.parse_order_string('A BER S A MUC - KIE')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('German Fleet Territory', german_fleet.territory, map.kiel)
    assert_equal('German Army Territory', german_army.territory, map.burgundy)
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.kiel)
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.berlin)

# 6.D.23
def test_impossible_coast_move_cannot_be_supported():
    map = get_classic_map()
    italian_fleet1 = add_fleet(map.gulf_of_lyon, map.italy)
    italian_fleet2 = add_fleet(map.western_mediterranean, map.italy)
    french_fleet1 = add_fleet(map.spain, map.france, coast=0)
    french_fleet2 = add_fleet(map.marseilles, map.france)

    map.parse_order_string('F LYO - SPA(sc)')
    map.parse_order_string('F WES S F LYO - SPA(sc)')
    map.parse_order_string('F SPA - LYO')
    map.parse_order_string('F MAR S F SPA - LYO')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.spain)
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.western_mediterranean)
    assert_not_equal('French Fleet 1 Territory', french_fleet1.territory, map.spain)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.marseilles)

# 6.D.24
def test_impossible_army_move_cannot_be_supported():
    map = get_classic_map()
    french_army = add_army(map.marseilles, map.france)
    french_fleet = add_fleet(map.spain, map.france, coast=1)
    italian_fleet = add_fleet(map.gulf_of_lyon, map.italy)
    turkish_fleet1 = add_fleet(map.tyrrhenian_sea, map.turkey)
    turkish_fleet2 = add_fleet(map.western_mediterranean, map.turkey)

    map.parse_order_string('A MAR - LYO')
    map.parse_order_string('F SPA S A MAR - LYO')
    map.parse_order_string('F LYO H')
    map.parse_order_string('F TYS S F WES - LYO')
    map.parse_order_string('F WES - LYO')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Italian Fleet 1 Territory', french_army.territory, map.marseilles)
    assert_equal('Italian Fleet 2 Territory', french_fleet.territory, map.spain)
    assert_not_equal('French Fleet 1 Territory', italian_fleet.territory, map.gulf_of_lyon)
    assert_equal('French Fleet 2 Territory', turkish_fleet1.territory, map.tyrrhenian_sea)
    assert_equal('French Fleet 2 Territory', turkish_fleet2.territory, map.gulf_of_lyon)

# 6.D.25
def test_failing_hold_support_can_be_supported():
    map = get_classic_map()
    german_army = add_army(map.berlin, map.germany)
    german_fleet = add_fleet(map.kiel, map.germany)
    russian_fleet = add_fleet(map.baltic_sea, map.russia)
    russian_army = add_army(map.prussia, map.russia)

    map.parse_order_string('A BER S A PRU H')
    map.parse_order_string('F KIE S A BER H')
    map.parse_order_string('F BAL S A PRU - BER')
    map.parse_order_string('A PRU - BER')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Army Territory', german_army.territory, map.berlin)
    assert_equal('German Fleet Territory', german_fleet.territory, map.kiel)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.baltic_sea)
    assert_equal('Russian Army Territory', russian_army.territory, map.prussia)

# 6.D.26
def test_failing_move_support_can_be_supported():
    map = get_classic_map()
    german_army = add_army(map.berlin, map.germany)
    german_fleet = add_fleet(map.kiel, map.germany)
    russian_fleet = add_fleet(map.baltic_sea, map.russia)
    russian_army = add_army(map.prussia, map.russia)

    map.parse_order_string('A BER S A PRU - SIL')
    map.parse_order_string('F KIE S A BER H')
    map.parse_order_string('F BAL S A PRU - BER')
    map.parse_order_string('A PRU - BER')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Army Territory', german_army.territory, map.berlin)
    assert_equal('German Fleet Territory', german_fleet.territory, map.kiel)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.baltic_sea)
    assert_equal('Russian Army Territory', russian_army.territory, map.prussia)

# 6.D.27
def test_failing_convoy_can_be_supported():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.sweden, map.england)
    english_fleet2 = add_fleet(map.denmark, map.england)
    german_army = add_army(map.berlin, map.germany)
    russian_fleet1 = add_fleet(map.baltic_sea, map.russia)
    russian_fleet2 = add_fleet(map.prussia, map.russia)

    map.parse_order_string('F SWE - BAL')
    map.parse_order_string('F DEN S F SWE - BAL')
    map.parse_order_string('A BER H')
    map.parse_order_string('F BAL C A BER - LIV')
    map.parse_order_string('F PRU S F BAL H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.sweden)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.denmark)
    assert_equal('German Army Territory', german_army.territory, map.berlin)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.baltic_sea)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.prussia)

# 6.D.28
def test_impossible_move_and_support():
    map = get_classic_map()
    austrian_army = add_army(map.budapest, map.austria_hungary)
    russian_fleet = add_fleet(map.rumania, map.russia)
    turkish_fleet = add_fleet(map.black_sea, map.turkey)
    turkish_army = add_army(map.bulgaria, map.turkey)

    map.parse_order_string('A BUD S F RUM H')
    map.parse_order_string('F RUM - HOL')
    map.parse_order_string('F BLA - RUM')
    map.parse_order_string('A BUL S F BLA - RUM')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Army Territory', austrian_army.territory, map.budapest)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.rumania)
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.black_sea)
    assert_equal('Turkish Army Territory', turkish_army.territory, map.bulgaria)

# 6.D.29
def test_move_to_impossible_coast_and_support():
    map = get_classic_map()
    austrian_army = add_army(map.budapest, map.austria_hungary)
    russian_fleet = add_fleet(map.rumania, map.russia)
    turkish_fleet = add_fleet(map.black_sea, map.turkey)
    turkish_army = add_army(map.bulgaria, map.turkey)

    map.parse_order_string('A BUD S F RUM H')
    map.parse_order_string('F RUM - BUL(sc)')
    map.parse_order_string('F BLA - RUM')
    map.parse_order_string('A BUL S F BLA - RUM')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Army Territory', austrian_army.territory, map.budapest)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.rumania)
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.black_sea)
    assert_equal('Turkish Army Territory', turkish_army.territory, map.bulgaria)

# 6.D.30
def test_move_without_coast_and_support():
    map = get_classic_map()
    italian_fleet = add_fleet(map.aegean_sea, map.italy)
    russian_fleet = add_fleet(map.constantinople, map.russia)
    turkish_fleet = add_fleet(map.black_sea, map.turkey)
    turkish_army = add_army(map.bulgaria, map.turkey)

    map.parse_order_string('F AEG S F CON H')
    map.parse_order_string('F CON - BUL')
    map.parse_order_string('F BLA - CON')
    map.parse_order_string('A BUL S F BLA - CON')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.aegean_sea)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.constantinople)
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.black_sea)
    assert_equal('Turkish Army Territory', turkish_army.territory, map.bulgaria)

# 6.D.31
def test_tricky_impossible_support():
    map = get_classic_map()
    austrian_army = add_army(map.rumania, map.austria_hungary)
    turkish_fleet = add_fleet(map.black_sea, map.turkey)

    map.parse_order_string('A RUM - ARM')
    map.parse_order_string('F BLA S A RUM - ARM')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Army Territory', austrian_army.territory, map.rumania)
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, map.black_sea)

# 6.D.32
def test_missing_fleet():
    map = get_classic_map()
    english_fleet = add_fleet(map.edinburgh, map.england)
    english_army = add_army(map.liverpool, map.england)
    french_fleet = add_fleet(map.london, map.france)
    german_army = add_army(map.yorkshire, map.germany)

    map.parse_order_string('F EDI S A LPL - YOR')
    map.parse_order_string('A LPL - YOR')
    map.parse_order_string('F LON S A YOR H')
    map.parse_order_string('A YOR - HOL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.edinburgh)
    assert_equal('English Army Territory', english_army.territory, map.liverpool)
    assert_equal('French Fleet Territory', french_fleet.territory, map.london)
    assert_equal('German Army Territory', german_army.territory, map.yorkshire)

# 6.D.33
def test_unwanted_support_allowed():
    map = get_classic_map()
    austrian_army1 = add_army(map.serbia, map.austria_hungary)
    austrian_army2 = add_army(map.vienna, map.austria_hungary)
    russian_army = add_army(map.galicia, map.russia)
    turkish_army = add_army(map.bulgaria, map.turkey)

    map.parse_order_string('A SER - BUD')
    map.parse_order_string('A VIE - BUD')
    map.parse_order_string('A GAL S A SER - BUD')
    map.parse_order_string('A BUL - SER')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.budapest)
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.vienna)
    assert_equal('Russian Army Territory', russian_army.territory, map.galicia)
    assert_equal('Turkish Army Territory', turkish_army.territory, map.serbia)

# 6.D.34
def test_support_targeting_own_area_not_allowed():
    map = get_classic_map()
    german_army1 = add_army(map.berlin, map.germany)
    german_army2 = add_army(map.silesia, map.germany)
    german_fleet = add_fleet(map.baltic_sea, map.germany)
    italian_army = add_army(map.prussia, map.italy)
    russian_army1 = add_army(map.warsaw, map.russia)
    russian_army2 = add_army(map.livonia, map.russia)

    map.parse_order_string('A BER - PRU')
    map.parse_order_string('A SIL S A BER - PRU')
    map.parse_order_string('F BAL S A BER - PRU')
    map.parse_order_string('A PRU S A LIV - PRU')
    map.parse_order_string('A WAR S A LIV - PRU')
    map.parse_order_string('A LIV - PRU')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Army 1 Territory', german_army1.territory, map.prussia)
    assert_equal('Austrian Army 2 Territory', german_army2.territory, map.silesia)
    assert_equal('Russian Army Territory', german_fleet.territory, map.baltic_sea)
    assert_not_equal('Turkish Army Territory', italian_army.territory, map.prussia)
    assert_equal('Turkish Army Territory', russian_army1.territory, map.warsaw)
    assert_equal('Turkish Army Territory', russian_army2.territory, map.livonia)

# 6.E Head-to-Head Battles and Beleaguered Garrison
# 6.E.1
def test_dislodged_unit_has_no_effect_on_attackers_area():
    map = get_classic_map()
    german_army1 = add_army(map.berlin, map.germany)
    german_fleet = add_fleet(map.kiel, map.germany)
    german_army2 = add_army(map.silesia, map.germany)
    russian_army = add_army(map.prussia, map.russia)

    map.parse_order_string('A BER - PRU')
    map.parse_order_string('F KIE - BER')
    map.parse_order_string('A SIL S A BER - PRU')
    map.parse_order_string('A PRU - BER')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Army 1 Territory', german_army1.territory, map.prussia)
    assert_equal('German Fleet Territory', german_fleet.territory, map.berlin)
    assert_equal('German Army 2 Territory', german_army2.territory, map.silesia)
    assert_not_equal('Russian Army Territory', russian_army.territory, map.prussia)

# 6.E.2
def test_no_self_dislodgement_in_head_to_head_battle():
    map = get_classic_map()
    german_army1 = add_army(map.berlin, map.germany)
    german_fleet = add_fleet(map.kiel, map.germany)
    german_army2 = add_army(map.munich, map.germany)

    map.parse_order_string('A BER - KIE')
    map.parse_order_string('F KIE - BER')
    map.parse_order_string('A MUC S A BER - KIE')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Army 1 Territory', german_army1.territory, map.berlin)
    assert_equal('German Fleet Territory', german_fleet.territory, map.kiel)
    assert_equal('German Army 2 Territory', german_army2.territory, map.munich)

# 6.E.3
def test_no_help_in_dislodging_own_unit():
    map = get_classic_map()
    german_army1 = add_army(map.berlin, map.germany)
    german_army2 = add_army(map.munich, map.germany)
    english_fleet = add_fleet(map.kiel, map.england)

    map.parse_order_string('A BER - KIE')
    map.parse_order_string('A MUC S F KIE - BER')
    map.parse_order_string('F KIE - BER')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Army 1 Territory', german_army1.territory, map.berlin)
    assert_equal('German Army 2 Territory', german_army2.territory, map.munich)
    assert_equal('English Fleet Territory', english_fleet.territory, map.kiel)

# 6.E.4
def test_non_dislodged_loser_still_has_effect():
    map = get_classic_map()
    german_fleet1 = add_fleet(map.holland, map.germany)
    german_fleet2 = add_fleet(map.helgoland_bight, map.germany)
    german_fleet3 = add_fleet(map.skagerrak, map.germany)
    french_fleet1 = add_fleet(map.north_sea, map.france)
    french_fleet2 = add_fleet(map.belgium, map.france)
    english_fleet1 = add_fleet(map.edinburgh, map.england)
    english_fleet2 = add_fleet(map.yorkshire, map.england)
    english_fleet3 = add_fleet(map.norwegian_sea, map.england)
    austrian_army1 = add_army(map.kiel, map.austria_hungary)
    austrian_army2 = add_army(map.ruhr, map.austria_hungary)

    map.parse_order_string('F HOL - NTH')
    map.parse_order_string('F HEL S F HOL - NTH')
    map.parse_order_string('F SKA S F HOL - NTH')
    map.parse_order_string('F NTH - HOL')
    map.parse_order_string('F BEL S F NTH - HOL')
    map.parse_order_string('F EDI S F NWG - NTH')
    map.parse_order_string('F YOR S F NWG - NTH')
    map.parse_order_string('F NWG - NTH')
    map.parse_order_string('A KIE S A RUH - HOL')
    map.parse_order_string('A RUH - HOL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 10)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.holland)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.helgoland_bight)
    assert_equal('German Fleet 3 Territory', german_fleet3.territory, map.skagerrak)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.north_sea)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.belgium)
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.edinburgh)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.yorkshire)
    assert_equal('English Fleet 3 Territory', english_fleet3.territory, map.norwegian_sea)
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.kiel)
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.ruhr)

# 6.E.5
def test_loser_dislodged_by_another_army_still_has_effect():
    map = get_classic_map()
    german_fleet1 = add_fleet(map.holland, map.germany)
    german_fleet2 = add_fleet(map.helgoland_bight, map.germany)
    german_fleet3 = add_fleet(map.skagerrak, map.germany)
    french_fleet1 = add_fleet(map.north_sea, map.france)
    french_fleet2 = add_fleet(map.belgium, map.france)
    english_fleet1 = add_fleet(map.edinburgh, map.england)
    english_fleet2 = add_fleet(map.yorkshire, map.england)
    english_fleet3 = add_fleet(map.norwegian_sea, map.england)
    english_fleet4 = add_fleet(map.london, map.england)
    austrian_army1 = add_army(map.kiel, map.austria_hungary)
    austrian_army2 = add_army(map.ruhr, map.austria_hungary)

    map.parse_order_string('F HOL - NTH')
    map.parse_order_string('F HEL S F HOL - NTH')
    map.parse_order_string('F SKA S F HOL - NTH')
    map.parse_order_string('F NTH - HOL')
    map.parse_order_string('F BEL S F NTH - HOL')
    map.parse_order_string('F EDI S F NWG - NTH')
    map.parse_order_string('F YOR S F NWG - NTH')
    map.parse_order_string('F NWG - NTH')
    map.parse_order_string('F LON S F NWG - NTH')
    map.parse_order_string('A KIE S A RUH - HOL')
    map.parse_order_string('A RUH - HOL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 11)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.holland)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.helgoland_bight)
    assert_equal('German Fleet 3 Territory', german_fleet3.territory, map.skagerrak)
    assert_not_equal('French Fleet 1 Territory', french_fleet1.territory, map.north_sea)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.belgium)
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.edinburgh)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.yorkshire)
    assert_equal('English Fleet 3 Territory', english_fleet3.territory, map.north_sea)
    assert_equal('English Fleet 4 Territory', english_fleet4.territory, map.london)
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.kiel)
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.ruhr)

# 6.E.6
def test_not_dislodge_because_of_own_support_still_in_effect():
    map = get_classic_map()
    german_fleet1 = add_fleet(map.holland, map.germany)
    german_fleet2 = add_fleet(map.helgoland_bight, map.germany)
    french_fleet1 = add_fleet(map.north_sea, map.france)
    french_fleet2 = add_fleet(map.belgium, map.france)
    french_fleet3 = add_fleet(map.english_channel, map.france)
    austrian_army1 = add_army(map.kiel, map.austria_hungary)
    austrian_army2 = add_army(map.ruhr, map.austria_hungary)

    map.parse_order_string('F HOL - NTH')
    map.parse_order_string('F HEL S F HOL - NTH')
    map.parse_order_string('F NTH - HOL')
    map.parse_order_string('F BEL S F NTH - HOL')
    map.parse_order_string('F ENG S F HOL - NTH')
    map.parse_order_string('A KIE S A RUH - HOL')
    map.parse_order_string('A RUH - HOL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 7)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.holland)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.helgoland_bight)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.north_sea)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.belgium)
    assert_equal('French Fleet 3 Territory', french_fleet3.territory, map.english_channel)
    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.kiel)
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.ruhr)

# 6.E.7
def test_no_self_dislodgement_with_beleaguered_garrison():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.north_sea, map.england)
    english_fleet2 = add_fleet(map.yorkshire, map.england)
    german_fleet1 = add_fleet(map.holland, map.germany)
    german_fleet2 = add_fleet(map.helgoland_bight, map.germany)
    russian_fleet1 = add_fleet(map.skagerrak, map.russia)
    russian_fleet2 = add_fleet(map.norway, map.russia)

    map.parse_order_string('F NTH H')
    map.parse_order_string('F YOR S F NWY - NTH')
    map.parse_order_string('F HOL S F HEL - NTH')
    map.parse_order_string('F HEL - NTH')
    map.parse_order_string('F SKA S F NWY - NTH')
    map.parse_order_string('F NWY - NTH')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.north_sea)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.yorkshire)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.holland)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.helgoland_bight)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.skagerrak)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.norway)

# 6.E.8
def test_no_self_dislodgement_with_beleaguered_garrison_and_head_to_head_battle():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.north_sea, map.england)
    english_fleet2 = add_fleet(map.yorkshire, map.england)
    german_fleet1 = add_fleet(map.holland, map.germany)
    german_fleet2 = add_fleet(map.helgoland_bight, map.germany)
    russian_fleet1 = add_fleet(map.skagerrak, map.russia)
    russian_fleet2 = add_fleet(map.norway, map.russia)

    map.parse_order_string('F NTH - NWY')
    map.parse_order_string('F YOR S F NWY - NTH')
    map.parse_order_string('F HOL S F HEL - NTH')
    map.parse_order_string('F HEL - NTH')
    map.parse_order_string('F SKA S F NWY - NTH')
    map.parse_order_string('F NWY - NTH')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.north_sea)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.yorkshire)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.holland)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.helgoland_bight)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.skagerrak)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.norway)

# 6.E.9
def test_almost_self_dislodgement_with_beleaguered_garrison():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.north_sea, map.england)
    english_fleet2 = add_fleet(map.yorkshire, map.england)
    german_fleet1 = add_fleet(map.holland, map.germany)
    german_fleet2 = add_fleet(map.helgoland_bight, map.germany)
    russian_fleet1 = add_fleet(map.skagerrak, map.russia)
    russian_fleet2 = add_fleet(map.norway, map.russia)

    map.parse_order_string('F NTH - NWG')
    map.parse_order_string('F YOR S F NWY - NTH')
    map.parse_order_string('F HOL S F HEL - NTH')
    map.parse_order_string('F HEL - NTH')
    map.parse_order_string('F SKA S F NWY - NTH')
    map.parse_order_string('F NWY - NTH')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.norwegian_sea)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.yorkshire)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.holland)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.helgoland_bight)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.skagerrak)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.north_sea)

# 6.E.10
def test_almost_circular_movement_with_no_self_dislodgement_with_beleaguered_garrison():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.north_sea, map.england)
    english_fleet2 = add_fleet(map.yorkshire, map.england)
    german_fleet1 = add_fleet(map.holland, map.germany)
    german_fleet2 = add_fleet(map.helgoland_bight, map.germany)
    german_fleet3 = add_fleet(map.denmark, map.germany)
    russian_fleet1 = add_fleet(map.skagerrak, map.russia)
    russian_fleet2 = add_fleet(map.norway, map.russia)

    map.parse_order_string('F NTH - DEN')
    map.parse_order_string('F YOR S F NWY - NTH')
    map.parse_order_string('F HOL S F HEL - NTH')
    map.parse_order_string('F HEL - NTH')
    map.parse_order_string('F DEN - HEL')
    map.parse_order_string('F SKA S F NWY - NTH')
    map.parse_order_string('F NWY - NTH')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 7)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.north_sea)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.yorkshire)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.holland)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.helgoland_bight)
    assert_equal('German Fleet 3 Territory', german_fleet3.territory, map.denmark)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.skagerrak)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.norway)

# 6.E.11
def test_no_self_dislodgement_with_beleaguered_garrison_unit_swap_with_adjacent_convoying_and_two_coasts():
    map = get_classic_map()
    french_army = add_army(map.spain, map.france)
    french_fleet1 = add_fleet(map.mid_atlantic_ocean, map.france)
    french_fleet2 = add_fleet(map.gulf_of_lyon, map.france)
    german_army1 = add_army(map.marseilles, map.germany)
    german_army2 = add_army(map.gascony, map.germany)
    italian_fleet1 = add_fleet(map.portugal, map.italy)
    italian_fleet2 = add_fleet(map.western_mediterranean, map.italy)

    map.parse_order_string('A SPA - POR via convoy')
    map.parse_order_string('F MAO C A SPA - POR')
    map.parse_order_string('F LYO S F POR - SPA(nc)')
    map.parse_order_string('A MAR S A GAS - SPA')
    map.parse_order_string('A GAS - SPA')
    map.parse_order_string('F POR - SPA(nc)')
    map.parse_order_string('F WES S F POR - SPA(nc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 7)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.portugal)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.mid_atlantic_ocean)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.gulf_of_lyon)
    assert_equal('German Army 1 Territory', german_army1.territory, map.marseilles)
    assert_equal('German Army 2 Territory', german_army2.territory, map.gascony)
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.spain)
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.western_mediterranean)

# 6.E.12
def test_support_on_attack_on_own_unit_can_be_used_for_other_means():
    map = get_classic_map()
    austrian_army1 = add_army(map.budapest, map.austria_hungary)
    austrian_army2 = add_army(map.serbia, map.austria_hungary)
    italian_army = add_army(map.vienna, map.italy)
    russian_army1 = add_army(map.galicia, map.russia)
    russian_army2 = add_army(map.rumania, map.russia)

    map.parse_order_string('A BUD - RUM')
    map.parse_order_string('A SER S A VIE - BUD')
    map.parse_order_string('A VIE - BUD')
    map.parse_order_string('A GAL - BUD')
    map.parse_order_string('A RUM S A GAL - BUD')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.budapest)
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.serbia)
    assert_equal('Italian Army Territory', italian_army.territory, map.vienna)
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.galicia)
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.rumania)

# 6.E.13
def test_three_way_beleaguered_garrison():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.edinburgh, map.england)
    english_fleet2 = add_fleet(map.yorkshire, map.england)
    french_fleet1 = add_fleet(map.belgium, map.france)
    french_fleet2 = add_fleet(map.english_channel, map.france)
    german_fleet = add_fleet(map.north_sea, map.germany)
    russian_fleet1 = add_fleet(map.norwegian_sea, map.russia)
    russian_fleet2 = add_fleet(map.norway, map.russia)

    map.parse_order_string('F EDI S F YOR - NTH')
    map.parse_order_string('F YOR - NTH')
    map.parse_order_string('F BEL - NTH')
    map.parse_order_string('F ENG S F BEL - NTH')
    map.parse_order_string('F NTH H')
    map.parse_order_string('F NWG - NTH')
    map.parse_order_string('F NWY S F NWG - NTH')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 7)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.edinburgh)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.yorkshire)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.belgium)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.english_channel)
    assert_equal('German Fleet Territory', german_fleet.territory, map.north_sea)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.norwegian_sea)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.norway)

# 6.E.14
def test_illegal_head_to_head_battle_can_still_defend():
    map = get_classic_map()
    english_army = add_army(map.liverpool, map.england)
    russian_fleet = add_fleet(map.edinburgh, map.russia)

    map.parse_order_string('A LPL - EDI')
    map.parse_order_string('F EDI - LPL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.liverpool)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.edinburgh)

# 6.E.15
def test_the_friendly_head_to_head_battle():
    map = get_classic_map()
    english_fleet = add_fleet(map.holland, map.england)
    english_army = add_army(map.ruhr, map.england)
    french_army1 = add_army(map.kiel, map.france)
    french_army2 = add_army(map.munich, map.france)
    french_army3 = add_army(map.silesia, map.france)
    german_army = add_army(map.berlin, map.germany)
    german_fleet1 = add_fleet(map.denmark, map.germany)
    german_fleet2 = add_fleet(map.helgoland_bight, map.germany)
    russian_fleet = add_fleet(map.baltic_sea, map.russia)
    russian_army = add_army(map.prussia, map.russia)

    map.parse_order_string('F HOL S A RUH - KIE')
    map.parse_order_string('A RUH - KIE')
    map.parse_order_string('A KIE - BER')
    map.parse_order_string('A MUC S A KIE - BER')
    map.parse_order_string('A SIL S A KIE - BER')
    map.parse_order_string('A BER - KIE')
    map.parse_order_string('F DEN S A BER - KIE')
    map.parse_order_string('F HEL S A BER - KIE')
    map.parse_order_string('F BAL S A PRU - BER')
    map.parse_order_string('F PRU - BER')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 10)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.holland)
    assert_equal('English Army Territory', english_army.territory, map.ruhr)
    assert_equal('French Army 1 Territory', french_army1.territory, map.kiel)
    assert_equal('French Army 2 Territory', french_army2.territory, map.munich)
    assert_equal('French Army 3 Territory', french_army3.territory, map.silesia)
    assert_equal('German Army Territory', german_army.territory, map.berlin)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.denmark)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.helgoland_bight)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.baltic_sea)
    assert_equal('Russian Army Territory', russian_army.territory, map.prussia)

# 6.F Convoys
# 6.F.1
def test_no_convoy_in_coastal_areas():
    map = get_classic_map()
    turkish_army = add_army(map.greece, map.turkey)
    turkish_fleet1 = add_fleet(map.aegean_sea, map.turkey)
    turkish_fleet2 = add_fleet(map.constantinople, map.turkey)
    turkish_fleet3 = add_fleet(map.black_sea, map.turkey)

    map.parse_order_string('A GRE - SEV')
    map.parse_order_string('F AEG C A GRE - SEV')
    map.parse_order_string('F CON C A GRE - SEV')
    map.parse_order_string('F BLA C A GRE - SEV')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Turkish Army Territory', turkish_army.territory, map.greece)
    assert_equal('Turkish Fleet 1 Territory', turkish_fleet1.territory, map.aegean_sea)
    assert_equal('Turkish Fleet 2 Territory', turkish_fleet2.territory, map.constantinople)
    assert_equal('Turkish Fleet 3 Territory', turkish_fleet3.territory, map.black_sea)

# 6.F.2
def test_an_army_being_convoyed_can_bounce_as_normal():
    map = get_classic_map()
    english_fleet = add_fleet(map.english_channel, map.england)
    english_army = add_army(map.london, map.england)
    french_army = add_army(map.paris, map.france)

    map.parse_order_string('F ENG C A LON - BRE')
    map.parse_order_string('A LON - BRE')
    map.parse_order_string('A PAR - BRE')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.english_channel)
    assert_equal('English Army Territory', english_army.territory, map.london)
    assert_equal('French Army Territory', french_army.territory, map.paris)

# 6.F.3
def test_an_army_being_convoyed_can_receive_support():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.english_channel, map.england)
    english_army = add_army(map.london, map.england)
    english_fleet2 = add_fleet(map.mid_atlantic_ocean, map.england)
    french_army = add_army(map.paris, map.france)

    map.parse_order_string('F ENG C A LON - BRE')
    map.parse_order_string('A LON - BRE')
    map.parse_order_string('F MAO S A LON - BRE')
    map.parse_order_string('A PAR - BRE')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.english_channel)
    assert_equal('English Army Territory', english_army.territory, map.brest)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.mid_atlantic_ocean)
    assert_equal('French Army Territory', french_army.territory, map.paris)

# 6.F.4
def test_an_attacked_convoy_is_not_disrupted():
    map = get_classic_map()
    english_fleet = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.london, map.england)
    german_fleet = add_fleet(map.skagerrak, map.germany)

    map.parse_order_string('F NTH C A LON - HOL')
    map.parse_order_string('A LON - HOL')
    map.parse_order_string('F SKA - NTH')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_equal('English Army Territory', english_army.territory, map.holland)
    assert_equal('French Army Territory', german_fleet.territory, map.skagerrak)

# 6.F.5
def test_beleaguered_convoy_is_not_disrupted():
    map = get_classic_map()
    english_fleet = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.london, map.england)
    french_fleet1 = add_fleet(map.english_channel, map.france)
    french_fleet2 = add_fleet(map.belgium, map.france)
    german_fleet1 = add_fleet(map.skagerrak, map.germany)
    german_fleet2 = add_fleet(map.denmark, map.germany)

    map.parse_order_string('F NTH C A LON - HOL')
    map.parse_order_string('A LON - HOL')
    map.parse_order_string('F ENG - NTH')
    map.parse_order_string('F BEL S F ENG - NTH')
    map.parse_order_string('F SKA - NTH')
    map.parse_order_string('F DEN S F SKA - NTH')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_equal('English Army Territory', english_army.territory, map.holland)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.english_channel)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.belgium)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.skagerrak)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.denmark)

# 6.F.6
def test_dislodged_convoy_does_not_cut_support():
    map = get_classic_map()
    english_fleet = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.london, map.england)
    german_army1 = add_army(map.holland, map.germany)
    german_army2 = add_army(map.belgium, map.germany)
    german_fleet1 = add_fleet(map.helgoland_bight, map.germany)
    german_fleet2 = add_fleet(map.skagerrak, map.germany)
    french_army1 = add_army(map.picardy, map.france)
    french_army2 = add_army(map.burgundy, map.france)

    map.parse_order_string('F NTH C A LON - HOL')
    map.parse_order_string('A LON - HOL')
    map.parse_order_string('A HOL S A BEL H')
    map.parse_order_string('A BEL S A HOL H')
    map.parse_order_string('F HEL S F SKA - NTH')
    map.parse_order_string('F SKA - NTH')
    map.parse_order_string('A PIC - BEL')
    map.parse_order_string('A BUR S A PIC - BEL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 8)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_equal('English Army Territory', english_army.territory, map.london)
    assert_equal('German Army 1 Territory', german_army1.territory, map.holland)
    assert_equal('German Army 2 Territory', german_army2.territory, map.belgium)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.helgoland_bight)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.north_sea)
    assert_equal('French Fleet 1 Territory', french_army1.territory, map.picardy)
    assert_equal('French Fleet 2 Territory', french_army2.territory, map.burgundy)

# 6.F.7
def test_dislodged_convoy_does_not_cause_contested_area():
    map = get_classic_map()
    english_fleet = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.london, map.england)
    german_fleet1 = add_fleet(map.helgoland_bight, map.germany)
    german_fleet2 = add_fleet(map.skagerrak, map.germany)

    map.parse_order_string('F NTH C A LON - HOL')
    map.parse_order_string('A LON - HOL')
    map.parse_order_string('F HEL S F SKA - NTH')
    map.parse_order_string('F SKA - NTH')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_equal('English Army Territory', english_army.territory, map.london)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.helgoland_bight)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.north_sea)

# 6.F.8
def test_dislodged_convoy_does_not_cause_a_bounce():
    map = get_classic_map()
    english_fleet = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.london, map.england)
    german_fleet1 = add_fleet(map.helgoland_bight, map.germany)
    german_fleet2 = add_fleet(map.skagerrak, map.germany)
    german_army = add_army(map.belgium, map.germany)

    map.parse_order_string('F NTH C A LON - HOL')
    map.parse_order_string('A LON - HOL')
    map.parse_order_string('F HEL S F SKA - NTH')
    map.parse_order_string('F SKA - NTH')
    map.parse_order_string('F BEL - HOL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_equal('English Army Territory', english_army.territory, map.london)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.helgoland_bight)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.north_sea)
    assert_equal('German Army Territory', german_army.territory, map.holland)

# 6.F.9
def test_dislodge_of_multi_route_convoy():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.english_channel, map.england)
    english_fleet2 = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.london, map.england)
    french_fleet1 = add_fleet(map.brest, map.france)
    french_fleet2 = add_fleet(map.mid_atlantic_ocean, map.france)

    map.parse_order_string('F ENG C A LON - BEL')
    map.parse_order_string('F NTH C A LON - BEL')
    map.parse_order_string('A LON - BEL')
    map.parse_order_string('F BRE S F MAO - ENG')
    map.parse_order_string('F MAO - ENG')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('English Fleet 1 Territory', english_fleet1.territory, map.english_channel)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.north_sea)
    assert_equal('English Army Territory', english_army.territory, map.belgium)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.brest)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.english_channel)

# 6.F.10
def test_dislodge_of_multi_route_convoy_with_foreign_fleet():
    map = get_classic_map()
    english_fleet = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.london, map.england)
    german_fleet = add_fleet(map.english_channel, map.germany)
    french_fleet1 = add_fleet(map.brest, map.france)
    french_fleet2 = add_fleet(map.mid_atlantic_ocean, map.france)

    map.parse_order_string('F NTH C A LON - BEL')
    map.parse_order_string('A LON - BEL')
    map.parse_order_string('F ENG C A LON - BEL')
    map.parse_order_string('F BRE S F MAO - ENG')
    map.parse_order_string('F MAO - ENG')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_equal('English Army Territory', english_army.territory, map.belgium)
    assert_not_equal('German Fleet Territory', german_fleet.territory, map.english_channel)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.brest)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.english_channel)

# 6.F.11
def test_dislodge_of_multi_route_convoy_with_only_foreign_fleets():
    map = get_classic_map()
    english_army = add_army(map.london, map.england)
    german_fleet = add_fleet(map.english_channel, map.germany)
    russian_fleet = add_fleet(map.north_sea, map.russia)
    french_fleet1 = add_fleet(map.brest, map.france)
    french_fleet2 = add_fleet(map.mid_atlantic_ocean, map.france)

    map.parse_order_string('A LON - BEL')
    map.parse_order_string('F ENG C A LON - BEL')
    map.parse_order_string('F NTH C A LON - BEL')
    map.parse_order_string('F BRE S F MAO - ENG')
    map.parse_order_string('F MAO - ENG')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.belgium)
    assert_not_equal('German Fleet Territory', german_fleet.territory, map.english_channel)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.north_sea)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.brest)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.english_channel)

# 6.F.12
def test_dislodged_convoying_fleet_not_on_route():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.english_channel, map.england)
    english_army = add_army(map.london, map.england)
    english_fleet2 = add_fleet(map.irish_sea, map.england)
    french_fleet1 = add_fleet(map.north_atlantic_ocean, map.france)
    french_fleet2 = add_fleet(map.mid_atlantic_ocean, map.france)

    map.parse_order_string('F ENG C A LON - BEL')
    map.parse_order_string('A LON - BEL')
    map.parse_order_string('F IRI C A LON - BEL')
    map.parse_order_string('F NAO S F MAO - IRI')
    map.parse_order_string('F MAO - IRI')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.english_channel)
    assert_equal('English Army Territory', english_army.territory, map.belgium)
    assert_not_equal('English Fleet 2 Territory', english_fleet2.territory, map.irish_sea)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.north_atlantic_ocean)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.irish_sea)

# 6.F.13
def test_the_unwanted_alternative():
    map = get_classic_map()
    english_army = add_army(map.london, map.england)
    english_fleet = add_fleet(map.north_sea, map.england)
    french_fleet = add_fleet(map.english_channel, map.france)
    german_fleet1 = add_fleet(map.holland, map.germany)
    german_fleet2 = add_fleet(map.denmark, map.germany)

    map.parse_order_string('A LON - BEL')
    map.parse_order_string('F NTH C A LON - BEL')
    map.parse_order_string('F ENG C A LON - BEL')
    map.parse_order_string('F HOL S F DEN - NTH')
    map.parse_order_string('F DEN - NTH')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.belgium)
    assert_not_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_equal('French Fleet Territory', french_fleet.territory, map.english_channel)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.holland)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.north_sea)

# 6.F.14
def test_simple_convoy_paradox():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.london, map.england)
    english_fleet2 = add_fleet(map.wales, map.england)
    french_army = add_army(map.brest, map.france)
    french_fleet = add_fleet(map.english_channel, map.france)

    map.parse_order_string('F LON S F WAL - ENG')
    map.parse_order_string('F WAL - ENG')
    map.parse_order_string('A BRE - LON')
    map.parse_order_string('F ENG C A BRE - LON')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.london)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.english_channel)
    assert_equal('French Army Territory', french_army.territory, map.brest)
    assert_not_equal('French Fleet Territory', french_fleet.territory, map.english_channel)

# 6.F.15
def test_simple_convoy_paradox_with_additional_convoy():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.london, map.england)
    english_fleet2 = add_fleet(map.wales, map.england)
    french_army = add_army(map.brest, map.france)
    french_fleet = add_fleet(map.english_channel, map.france)
    italian_fleet1 = add_fleet(map.irish_sea, map.italy)
    italian_fleet2 = add_fleet(map.mid_atlantic_ocean, map.italy)
    italian_army = add_army(map.north_africa, map.italy)

    map.parse_order_string('F LON S F WAL - ENG')
    map.parse_order_string('F WAL - ENG')
    map.parse_order_string('A BRE - LON')
    map.parse_order_string('F ENG C A BRE - LON')
    map.parse_order_string('F IRI C A NAF - WAL')
    map.parse_order_string('F MAO C A NAF - WAL')
    map.parse_order_string('A NAF - WAL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 7)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.london)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.english_channel)
    assert_equal('French Army Territory', french_army.territory, map.brest)
    assert_not_equal('French Fleet Territory', french_fleet.territory, map.english_channel)
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.irish_sea)
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.mid_atlantic_ocean)
    assert_equal('Italian Army Territory', italian_army.territory, map.wales)

# 6.F.16
def test_pandins_paradox():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.london, map.england)
    english_fleet2 = add_fleet(map.wales, map.england)
    french_army = add_army(map.brest, map.france)
    french_fleet = add_fleet(map.english_channel, map.france)
    german_fleet1 = add_fleet(map.north_sea, map.germany)
    german_fleet2 = add_fleet(map.belgium, map.germany)

    map.parse_order_string('F LON S F WAL - ENG')
    map.parse_order_string('F WAL - ENG')
    map.parse_order_string('A BRE - LON')
    map.parse_order_string('F ENG C A BRE - LON')
    map.parse_order_string('F NTH S F BEL - ENG')
    map.parse_order_string('F BEL - ENG')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.london)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.wales)
    assert_equal('French Army Territory', french_army.territory, map.brest)
    assert_equal('French Fleet Territory', french_fleet.territory, map.english_channel)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.north_sea)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.belgium)

# 6.F.17
def test_pandins_extended_paradox():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.london, map.england)
    english_fleet2 = add_fleet(map.wales, map.england)
    french_army = add_army(map.brest, map.france)
    french_fleet1 = add_fleet(map.english_channel, map.france)
    french_fleet2 = add_fleet(map.yorkshire, map.france)
    german_fleet1 = add_fleet(map.north_sea, map.germany)
    german_fleet2 = add_fleet(map.belgium, map.germany)

    map.parse_order_string('F LON S F WAL - ENG')
    map.parse_order_string('F WAL - ENG')
    map.parse_order_string('A BRE - LON')
    map.parse_order_string('F ENG C A BRE - LON')
    map.parse_order_string('F YOR S A BRE - LON')
    map.parse_order_string('F NTH S F BEL - ENG')
    map.parse_order_string('F BEL - ENG')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 7)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('English Fleet 1 Territory', english_fleet1.territory, map.london)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.wales)
    assert_equal('French Army Territory', french_army.territory, map.london)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.english_channel)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.yorkshire)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.north_sea)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.belgium)

# 6.F.18
def test_betrayal_paradox():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.london, map.england)
    english_fleet2 = add_fleet(map.english_channel, map.england)
    french_fleet = add_fleet(map.belgium, map.france)
    german_fleet1 = add_fleet(map.helgoland_bight, map.germany)
    german_fleet2 = add_fleet(map.skagerrak, map.germany)

    map.parse_order_string('F NTH C A LON - BEL')
    map.parse_order_string('A LON - BEL')
    map.parse_order_string('F ENG S A LON - BEL')
    map.parse_order_string('F BEL S F NTH H')
    map.parse_order_string('F HEL S F SKA - NTH')
    map.parse_order_string('F SKA - NTH')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.north_sea)
    assert_equal('English Army Territory', english_army.territory, map.london)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.english_channel)
    assert_equal('French Fleet Territory', french_fleet.territory, map.belgium)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.helgoland_bight)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.skagerrak)

# 6.F.19
def test_multi_route_convoy_disruption_paradox():
    map = get_classic_map()
    french_army = add_army(map.tunis, map.france)
    french_fleet1 = add_fleet(map.tyrrhenian_sea, map.france)
    french_fleet2 = add_fleet(map.ionian_sea, map.france)
    italian_fleet1 = add_fleet(map.naples, map.italy)
    italian_fleet2 = add_fleet(map.rome, map.italy)

    map.parse_order_string('A TUN - NAP')
    map.parse_order_string('F TYS C A TUN - NAP')
    map.parse_order_string('F ION C A TUN - NAP')
    map.parse_order_string('F NAP S F ROM - TYS')
    map.parse_order_string('F ROM - TYS')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.tunis)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.tyrrhenian_sea)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.ionian_sea)
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.naples)
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.rome)

# 6.F.20
def test_unwanted_multi_route_convoy_paradox():
    map = get_classic_map()
    french_army = add_army(map.tunis, map.france)
    french_fleet = add_fleet(map.tyrrhenian_sea, map.france)
    italian_fleet1 = add_fleet(map.naples, map.italy)
    italian_fleet2 = add_fleet(map.ionian_sea, map.italy)
    turkish_fleet1 = add_fleet(map.aegean_sea, map.turkey)
    turkish_fleet2 = add_fleet(map.eastern_mediterranean, map.turkey)

    map.parse_order_string('A TUN - NAP')
    map.parse_order_string('F TYS C A TUN - NAP')
    map.parse_order_string('F NAP S F ION H')
    map.parse_order_string('F ION C A TUN - NAP')
    map.parse_order_string('F AEG S F EAS - ION')
    map.parse_order_string('F EAS - ION')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.tunis)
    assert_equal('French Fleet Territory', french_fleet.territory, map.tyrrhenian_sea)
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.naples)
    assert_not_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.ionian_sea)
    assert_equal('Turkish Fleet 1 Territory', turkish_fleet1.territory, map.aegean_sea)
    assert_equal('Turkish Fleet 2 Territory', turkish_fleet2.territory, map.ionian_sea)

# 6.F.21
def test_dads_army_convoy():
    map = get_classic_map()
    russian_army1 = add_army(map.edinburgh, map.russia)
    russian_fleet = add_fleet(map.norwegian_sea, map.russia)
    russian_army2 = add_army(map.norway, map.russia)
    french_fleet1 = add_fleet(map.irish_sea, map.france)
    french_fleet2 = add_fleet(map.mid_atlantic_ocean, map.france)
    english_army = add_army(map.liverpool, map.england)
    english_fleet1 = add_fleet(map.north_atlantic_ocean, map.england)
    english_fleet2 = add_fleet(map.clyde, map.england)

    map.parse_order_string('A EDI S A NWY - CLY')
    map.parse_order_string('F NWG C A NWY - CLY')
    map.parse_order_string('A NWY - CLY')
    map.parse_order_string('F IRI S F MAO - NAO')
    map.parse_order_string('F MAO - NAO')
    map.parse_order_string('A LPL - CLY via convoy')
    map.parse_order_string('F NAO C A LPL - CLY')
    map.parse_order_string('F CLY S F NAO H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 8)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.edinburgh)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.norwegian_sea)
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.norway)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.irish_sea)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.north_atlantic_ocean)
    assert_equal('English Army Territory', english_army.territory, map.liverpool)
    assert_not_equal('English Fleet 1 Territory', english_fleet1.territory, map.north_atlantic_ocean)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.clyde)

# 6.F.22
def test_second_order_paradox_with_two_resolutions():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.edinburgh, map.england)
    english_fleet2 = add_fleet(map.london, map.england)
    french_army = add_army(map.brest, map.france)
    french_fleet = add_fleet(map.english_channel, map.france)
    german_fleet1 = add_fleet(map.belgium, map.germany)
    german_fleet2 = add_fleet(map.picardy, map.germany)
    russian_army = add_army(map.norway, map.russia)
    russian_fleet = add_fleet(map.north_sea, map.russia)

    map.parse_order_string('F EDI - NTH')
    map.parse_order_string('F LON S F EDI - NTH')
    map.parse_order_string('A BRE - LON')
    map.parse_order_string('F ENG C A BRE - LON')
    map.parse_order_string('F BEL S F PIC - ENG')
    map.parse_order_string('F PIC - ENG')
    map.parse_order_string('A NWY - BEL')
    map.parse_order_string('F NTH C A NWY - BEL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 8)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.north_sea)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.london)
    assert_equal('French Army Territory', french_army.territory, map.brest)
    assert_not_equal('French Fleet Territory', french_fleet.territory, map.english_channel)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.belgium)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.english_channel)
    assert_equal('Russian Army Territory', russian_army.territory, map.norway)
    assert_not_equal('Russian Fleet Territory', russian_fleet.territory, map.north_sea)

# 6.F.23
def test_second_order_paradox_with_two_exclusive_convoys():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.edinburgh, map.england)
    english_fleet2 = add_fleet(map.yorkshire, map.england)
    french_army = add_army(map.brest, map.france)
    french_fleet = add_fleet(map.english_channel, map.france)
    german_fleet1 = add_fleet(map.belgium, map.germany)
    german_fleet2 = add_fleet(map.london, map.germany)
    italian_fleet1 = add_fleet(map.mid_atlantic_ocean, map.italy)
    italian_fleet2 = add_fleet(map.irish_sea, map.italy)
    russian_army = add_army(map.norway, map.russia)
    russian_fleet = add_fleet(map.north_sea, map.russia)

    map.parse_order_string('F EDI - NTH')
    map.parse_order_string('F YOR S F EDI - NTH')
    map.parse_order_string('A BRE - LON')
    map.parse_order_string('F ENG C A BRE - LON')
    map.parse_order_string('F BEL S F ENG H')
    map.parse_order_string('F LON S F NTH H')
    map.parse_order_string('F MAO - ENG')
    map.parse_order_string('F IRI S F MAO - ENG')
    map.parse_order_string('A NWY - BEL')
    map.parse_order_string('F NTH C A NWY - BEL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 10)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.edinburgh)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.yorkshire)
    assert_equal('French Army Territory', french_army.territory, map.brest)
    assert_equal('French Fleet Territory', french_fleet.territory, map.english_channel)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.belgium)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.london)
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.mid_atlantic_ocean)
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.irish_sea)
    assert_equal('Russian Army Territory', russian_army.territory, map.norway)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.north_sea)

# 6.F.24
def test_second_order_paradox_with_no_resolution():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.edinburgh, map.england)
    english_fleet2 = add_fleet(map.london, map.england)
    english_fleet3 = add_fleet(map.irish_sea, map.england)
    english_fleet4 = add_fleet(map.mid_atlantic_ocean, map.england)
    french_army = add_army(map.brest, map.france)
    french_fleet1 = add_fleet(map.english_channel, map.france)
    french_fleet2 = add_fleet(map.belgium, map.france)
    russian_army = add_army(map.norway, map.russia)
    russian_fleet = add_fleet(map.north_sea, map.russia)

    map.parse_order_string('F EDI - NTH')
    map.parse_order_string('F LON S F EDI - NTH')
    map.parse_order_string('F IRI - ENG')
    map.parse_order_string('F MAO S F IRI - ENG')
    map.parse_order_string('A BRE - LON')
    map.parse_order_string('F ENG C A BRE - LON')
    map.parse_order_string('F BEL S F ENG H')
    map.parse_order_string('A NWY - BEL')
    map.parse_order_string('F NTH C A NWY - BEL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 9)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.north_sea)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.london)
    assert_equal('English Fleet 3 Territory', english_fleet3.territory, map.irish_sea)
    assert_equal('English Fleet 4 Territory', english_fleet4.territory, map.mid_atlantic_ocean)
    assert_equal('French Army Territory', french_army.territory, map.brest)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.english_channel)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.belgium)
    assert_equal('Russian Army Territory', russian_army.territory, map.norway)
    assert_not_equal('Russian Fleet Territory', russian_fleet.territory, map.north_sea)

# 6.F.25
def test_cut_support_last():
    map = get_classic_map()
    german_army1 = add_army(map.ruhr, map.germany)
    german_army2 = add_army(map.holland, map.germany)
    german_army3 = add_army(map.denmark, map.germany)
    german_fleet = add_fleet(map.skagerrak, map.germany)
    german_army4 = add_army(map.finland, map.germany)
    english_army1 = add_army(map.yorkshire, map.england)
    english_fleet1 = add_fleet(map.north_sea, map.england)
    english_fleet2 = add_fleet(map.helgoland_bight, map.england)
    english_army2 = add_army(map.belgium, map.england)
    russian_fleet1 = add_fleet(map.norwegian_sea, map.russia)
    russian_fleet2 = add_fleet(map.norway, map.russia)
    russian_fleet3 = add_fleet(map.sweden, map.russia)

    map.parse_order_string('A RUH - BEL')
    map.parse_order_string('A HOL S A RUH - BEL')
    map.parse_order_string('A DEN - NWY')
    map.parse_order_string('F SKA C A DEN - NWY')
    map.parse_order_string('A FIN S A DEN - NWY')
    map.parse_order_string('A YOR - HOL')
    map.parse_order_string('F NTH C A YOR - HOL')
    map.parse_order_string('F HEL S A YOR - HOL')
    map.parse_order_string('A BEL H')
    map.parse_order_string('F NWG - NTH')
    map.parse_order_string('F NWY S F NWG - NTH')
    map.parse_order_string('F SWE - SKA')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 12)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Army 1 Territory', german_army1.territory, map.ruhr)
    assert_not_equal('German Army 2 Territory', german_army2.territory, map.holland)
    assert_equal('German Army 3 Territory', german_army3.territory, map.norway)
    assert_equal('German Fleet Territory', german_fleet.territory, map.skagerrak)
    assert_equal('German Army 4 Territory', german_army4.territory, map.finland)
    assert_equal('English Army 1 Territory', english_army1.territory, map.holland)
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.north_sea)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.helgoland_bight)
    assert_equal('English Army 2 Territory', english_army2.territory, map.belgium)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.norwegian_sea)
    assert_not_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.norway)
    assert_equal('Russian Fleet 3 Territory', russian_fleet3.territory, map.sweden)

# 6.G Convoying to Adjacent Provinces
# 6.G.1
def test_two_units_can_swap_provinces_by_convoy():
    map = get_classic_map()
    english_army = add_army(map.norway, map.england)
    english_fleet = add_fleet(map.skagerrak, map.england)
    russian_army = add_army(map.sweden, map.russia)

    map.parse_order_string('A NWY - SWE')
    map.parse_order_string('F SKA C A NWY - SWE')
    map.parse_order_string('A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.sweden)
    assert_equal('English Fleet Territory', english_fleet.territory, map.skagerrak)
    assert_equal('Russian Army Territory', russian_army.territory, map.norway)

# 6.G.2
def test_kidnapping_an_army():
    map = get_classic_map()
    english_army = add_army(map.norway, map.england)
    russian_fleet = add_fleet(map.sweden, map.russia)
    german_fleet = add_fleet(map.skagerrak, map.germany)

    map.parse_order_string('A NWY - SWE')
    map.parse_order_string('F SWE - NWY')
    map.parse_order_string('F SKA C A NWY - SWE')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.norway)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.sweden)
    assert_equal('German Fleet Territory', german_fleet.territory, map.skagerrak)

# 6.G.3
def test_unwanted_disrupted_convoy_to_adjacent_province():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.brest, map.france)
    french_army1 = add_army(map.picardy, map.france)
    french_army2 = add_army(map.burgundy, map.france)
    french_fleet2 = add_fleet(map.mid_atlantic_ocean, map.france)
    english_fleet = add_fleet(map.english_channel, map.england)

    map.parse_order_string('F BRE - ENG')
    map.parse_order_string('A PIC - BEL')
    map.parse_order_string('A BUR S A PIC - BEL')
    map.parse_order_string('F MAO S F BRE - ENG')
    map.parse_order_string('F ENG C A PIC - BEL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.english_channel)
    assert_equal('French Army 1 Territory', french_army1.territory, map.belgium)
    assert_equal('French Army 2 Territory', french_army2.territory, map.burgundy)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.mid_atlantic_ocean)
    assert_not_equal('English Fleet Territory', english_fleet.territory, map.english_channel)

# 6.G.4
def test_unwanted_disrupted_convoy_to_adjacent_province_and_opposite_move():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.brest, map.france)
    french_army1 = add_army(map.picardy, map.france)
    french_army2 = add_army(map.burgundy, map.france)
    french_fleet2 = add_fleet(map.mid_atlantic_ocean, map.france)
    english_fleet = add_fleet(map.english_channel, map.england)
    english_army = add_army(map.belgium, map.england)

    map.parse_order_string('F BRE - ENG')
    map.parse_order_string('A PIC - BEL')
    map.parse_order_string('A BUR S A PIC - BEL')
    map.parse_order_string('F MAO S F BRE - ENG')
    map.parse_order_string('F ENG C A PIC - BEL')
    map.parse_order_string('A BEL - PIC')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.english_channel)
    assert_equal('French Army 1 Territory', french_army1.territory, map.belgium)
    assert_equal('French Army 2 Territory', french_army2.territory, map.burgundy)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.mid_atlantic_ocean)
    assert_not_equal('English Fleet Territory', english_fleet.territory, map.english_channel)
    assert_not_equal('English Army Territory', english_army.territory, map.belgium)

# 6.G.5
def test_swapping_with_multiple_fleets_with_one_own_fleet():
    map = get_classic_map()
    italian_army = add_army(map.rome, map.italy)
    italian_fleet = add_fleet(map.tyrrhenian_sea, map.italy)
    turkish_army = add_army(map.apulia, map.turkey)
    turkish_fleet = add_fleet(map.ionian_sea, map.turkey)

    map.parse_order_string('A ROM - APU')
    map.parse_order_string('F TYS C A APU - ROM')
    map.parse_order_string('A APU - ROM')
    map.parse_order_string('F ION C A APU - ROM')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', italian_army.territory, map.apulia)
    assert_equal('English Fleet Territory', italian_fleet.territory, map.tyrrhenian_sea)
    assert_equal('Russian Army Territory', turkish_army.territory, map.rome)
    assert_equal('Russian Army Territory', turkish_fleet.territory, map.ionian_sea)

# 6.G.6
def test_swapping_with_unintended_intent():
    map = get_classic_map()
    english_army = add_army(map.liverpool, map.england)
    english_fleet = add_fleet(map.english_channel, map.england)
    german_army = add_army(map.edinburgh, map.germany)
    french_fleet1 = add_fleet(map.irish_sea, map.france)
    french_fleet2 = add_fleet(map.north_sea, map.france)
    russian_fleet1 = add_fleet(map.norwegian_sea, map.russia)
    russian_fleet2 = add_fleet(map.north_atlantic_ocean, map.russia)

    map.parse_order_string('A LPL - EDI')
    map.parse_order_string('F ENG C A LPL - EDI')
    map.parse_order_string('A EDI - LPL')
    map.parse_order_string('F IRI H')
    map.parse_order_string('F NTH H')
    map.parse_order_string('F NWG C A LPL - EDI')
    map.parse_order_string('F NAO C A LPL - EDI')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 7)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.edinburgh)
    assert_equal('English Fleet Territory', english_fleet.territory, map.english_channel)
    assert_equal('German Army Territory', german_army.territory, map.liverpool)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.irish_sea)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.north_sea)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.norwegian_sea)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.north_atlantic_ocean)

# 6.G.7
def test_swapping_with_illegal_intent():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.skagerrak, map.england)
    english_fleet2 = add_fleet(map.norway, map.england)
    russian_army = add_army(map.sweden, map.russia)
    russian_fleet = add_fleet(map.gulf_of_bothnia, map.russia)

    map.parse_order_string('F SKA C A SWE - NWY')
    map.parse_order_string('F NWY - SWE')
    map.parse_order_string('A SWE - NWY')
    map.parse_order_string('F BOT C A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.skagerrak)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.norway)
    assert_equal('Russian Army Territory', russian_army.territory, map.sweden)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.gulf_of_bothnia)

# 6.G.8
def test_explicit_convoy_that_isnt_there():
    map = get_classic_map()
    french_army = add_army(map.belgium, map.france)
    english_fleet = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.holland, map.england)

    map.parse_order_string('A BEL - HOL via convoy')
    map.parse_order_string('F NTH - HEL')
    map.parse_order_string('A HOL - KIE')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.belgium)
    assert_equal('English Fleet Territory', english_fleet.territory, map.helgoland_bight)
    assert_equal('English Army Territory', english_army.territory, map.kiel)

# 6.G.9
def test_swapped_or_dislodged():
    map = get_classic_map()
    english_army = add_army(map.norway, map.england)
    english_fleet1 = add_fleet(map.skagerrak, map.england)
    english_fleet2 = add_fleet(map.finland, map.england)
    russian_army = add_army(map.sweden, map.russia)

    map.parse_order_string('A NWY - SWE')
    map.parse_order_string('F SKA C A NWY - SWE')
    map.parse_order_string('F FIN S A NWY - SWE')
    map.parse_order_string('A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.sweden)
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.skagerrak)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.finland)
    assert_equal('Russian Army Territory', russian_army.territory, map.norway)

# 6.G.10
def test_swapped_or_a_head_to_head_battle():
    map = get_classic_map()
    english_army = add_army(map.norway, map.england)
    english_fleet1 = add_fleet(map.denmark, map.england)
    english_fleet2 = add_fleet(map.finland, map.england)
    german_fleet = add_fleet(map.skagerrak, map.germany)
    russian_army = add_army(map.sweden, map.russia)
    russian_fleet = add_fleet(map.barents_sea, map.russia)
    french_fleet1 = add_fleet(map.norwegian_sea, map.france)
    french_fleet2 = add_fleet(map.north_sea, map.france)

    map.parse_order_string('A NWY - SWE via convoy')
    map.parse_order_string('F DEN S A NWY - SWE')
    map.parse_order_string('F FIN S A NWY - SWE')
    map.parse_order_string('F SKA C A NWY - SWE')
    map.parse_order_string('A SWE - NWY')
    map.parse_order_string('F BAR S A SWE - NWY')
    map.parse_order_string('F NWG - NWY')
    map.parse_order_string('F NTH S F NWG - NWY')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 8)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.sweden)
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.denmark)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.finland)
    assert_equal('German Fleet Territory', german_fleet.territory, map.skagerrak)
    assert_not_equal('Russian Army Territory', russian_army.territory, map.sweden)
    assert_not_equal('Russian Army Territory', russian_army.territory, map.norway)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.barents_sea)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.norwegian_sea)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.north_sea)

# 6.G.11
def test_convoy_to_an_adjacent_province_with_a_paradox():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.norway, map.england)
    english_fleet2 = add_fleet(map.north_sea, map.england)
    russian_army = add_army(map.sweden, map.russia)
    russian_fleet1 = add_fleet(map.skagerrak, map.russia)
    russian_fleet2 = add_fleet(map.barents_sea, map.russia)

    map.parse_order_string('F NWY S F NTH - SKA')
    map.parse_order_string('F NTH - SKA')
    map.parse_order_string('A SWE - NWY')
    map.parse_order_string('F SKA C A SWE - NWY')
    map.parse_order_string('F BAR S A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.norway)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.skagerrak)
    assert_equal('Russian Army Territory', russian_army.territory, map.sweden)
    assert_not_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.skagerrak)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.barents_sea)

# 6.G.12
def test_swapping_two_units_with_two_convoys():
    map = get_classic_map()
    english_army = add_army(map.liverpool, map.england)
    english_fleet1 = add_fleet(map.north_atlantic_ocean, map.england)
    english_fleet2 = add_fleet(map.norwegian_sea, map.england)
    german_army = add_army(map.edinburgh, map.germany)
    german_fleet1 = add_fleet(map.north_sea, map.germany)
    german_fleet2 = add_fleet(map.english_channel, map.germany)
    german_fleet3 = add_fleet(map.irish_sea, map.germany)

    map.parse_order_string('A LPL - EDI via convoy')
    map.parse_order_string('F NAO C A LPL - EDI')
    map.parse_order_string('F NWG C A LPL - EDI')
    map.parse_order_string('A EDI - LPL via convoy')
    map.parse_order_string('F NTH C A EDI - LPL')
    map.parse_order_string('F ENG C A EDI - LPL')
    map.parse_order_string('F IRI C A EDI - LPL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 7)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.edinburgh)
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.north_atlantic_ocean)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.norwegian_sea)
    assert_equal('German Army Territory', german_army.territory, map.liverpool)
    assert_equal('German Fleet 1 Territory', german_fleet1.territory, map.north_sea)
    assert_equal('German Fleet 2 Territory', german_fleet2.territory, map.english_channel)
    assert_equal('German Fleet 3 Territory', german_fleet3.territory, map.irish_sea)

# 6.G.13
def test_support_cut_on_attack_on_itself_via_convoy():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.adriatic_sea, map.austria_hungary)
    austrian_army = add_army(map.trieste, map.austria_hungary)
    italian_army = add_army(map.venice, map.italy)
    italian_fleet = add_fleet(map.albania, map.italy)

    map.parse_order_string('F ADR C A TRI - VEN')
    map.parse_order_string('A TRI - VEN via convoy')
    map.parse_order_string('A VEN S F ALB - TRI')
    map.parse_order_string('F ALB - TRI')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, map.adriatic_sea)
    assert_not_equal('Austrian Army Territory', austrian_army.territory, map.trieste)
    assert_equal('Italian Army Territory', italian_army.territory, map.venice)
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.trieste)

# 6.G.14
def test_bounce_by_convoy_to_adjacent_province():
    map = get_classic_map()
    english_army = add_army(map.norway, map.england)
    english_fleet1 = add_fleet(map.denmark, map.england)
    english_fleet2 = add_fleet(map.finland, map.england)
    french_fleet1 = add_fleet(map.norwegian_sea, map.france)
    french_fleet2 = add_fleet(map.north_sea, map.france)
    german_fleet = add_fleet(map.skagerrak, map.germany)
    russian_army = add_army(map.sweden, map.russia)
    russian_fleet = add_fleet(map.barents_sea, map.russia)

    map.parse_order_string('A NWY - SWE')
    map.parse_order_string('F DEN S A NWY - SWE')
    map.parse_order_string('F FIN S A NWY - SWE')
    map.parse_order_string('F NWG - NWY')
    map.parse_order_string('F NTH S F NWG - NWY')
    map.parse_order_string('F SKA C A SWE - NWY')
    map.parse_order_string('A SWE - NWY via convoy')
    map.parse_order_string('F BAR S A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 8)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.sweden)
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.denmark)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.finland)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.norwegian_sea)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.north_sea)
    assert_equal('German Fleet Territory', german_fleet.territory, map.skagerrak)
    assert_not_equal('Russian Army Territory', russian_army.territory, map.sweden)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.barents_sea)

# 6.G.15
def test_bounce_and_dislodge_with_double_convoy():
    map = get_classic_map()
    english_fleet = add_fleet(map.north_sea, map.england)
    english_army1 = add_army(map.holland, map.england)
    english_army2 = add_army(map.yorkshire, map.england)
    english_army3 = add_army(map.london, map.england)
    french_fleet = add_fleet(map.english_channel, map.france)
    french_army = add_army(map.belgium, map.france)

    map.parse_order_string('F NTH C A LON - BEL')
    map.parse_order_string('A HOL S A LON - BEL')
    map.parse_order_string('A YOR - LON')
    map.parse_order_string('A LON - BEL via convoy')
    map.parse_order_string('F ENG C A BEL - LON')
    map.parse_order_string('A BEL - LON via convoy')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_equal('English Army 1 Territory', english_army1.territory, map.holland)
    assert_equal('English Army 2 Territory', english_army2.territory, map.yorkshire)
    assert_equal('English Army 3 Territory', english_army3.territory, map.belgium)
    assert_equal('French Fleet Territory', french_fleet.territory, map.english_channel)
    assert_not_equal('French Army Territory', french_army.territory, map.belgium)

# 6.G.16
def test_the_two_unit_in_one_area_bug_moving_by_convoy():
    map = get_classic_map()
    english_army1 = add_army(map.norway, map.england)
    english_army2 = add_army(map.denmark, map.england)
    english_fleet1 = add_fleet(map.baltic_sea, map.england)
    english_fleet2 = add_fleet(map.north_sea, map.england)
    russian_army = add_army(map.sweden, map.russia)
    russian_fleet1 = add_fleet(map.skagerrak, map.russia)
    russian_fleet2 = add_fleet(map.norwegian_sea, map.russia)

    map.parse_order_string('A NWY - SWE')
    map.parse_order_string('A DEN S A NWY - SWE')
    map.parse_order_string('F BAL S A NWY - SWE')
    map.parse_order_string('F NTH - NWY')
    map.parse_order_string('A SWE - NWY via convoy')
    map.parse_order_string('F SKA C A SWE - NWY')
    map.parse_order_string('F NWG S A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 7)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army 2 Territory', english_army1.territory, map.sweden)
    assert_equal('English Army 2 Territory', english_army2.territory, map.denmark)
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.baltic_sea)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.north_sea)
    assert_equal('Russian Army Territory', russian_army.territory, map.norway)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.skagerrak)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.norwegian_sea)

# 6.G.17
def test_the_two_unit_in_one_area_bug_moving_over_land():
    map = get_classic_map()
    english_army1 = add_army(map.norway, map.england)
    english_army2 = add_army(map.denmark, map.england)
    english_fleet1 = add_fleet(map.baltic_sea, map.england)
    english_fleet2 = add_fleet(map.skagerrak, map.england)
    english_fleet3 = add_fleet(map.north_sea, map.england)
    russian_army = add_army(map.sweden, map.russia)
    russian_fleet = add_fleet(map.norwegian_sea, map.russia)

    map.parse_order_string('A NWY - SWE via convoy')
    map.parse_order_string('A DEN S A NWY - SWE')
    map.parse_order_string('F BAL S A NWY - SWE')
    map.parse_order_string('F SKA C A NWY - SWE')
    map.parse_order_string('F NTH - NWY')
    map.parse_order_string('A SWE - NWY')
    map.parse_order_string('F NWG S A SWE - NWY')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 7)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army 2 Territory', english_army1.territory, map.sweden)
    assert_equal('English Army 2 Territory', english_army2.territory, map.denmark)
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.baltic_sea)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.skagerrak)
    assert_equal('English Fleet 3 Territory', english_fleet3.territory, map.north_sea)
    assert_equal('Russian Army Territory', russian_army.territory, map.norway)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.norwegian_sea)

# 6.G.18
def test_the_two_unit_in_one_area_bug_with_double_convoy():
    map = get_classic_map()
    english_fleet = add_fleet(map.north_sea, map.england)
    english_army1 = add_army(map.holland, map.england)
    english_army2 = add_army(map.yorkshire, map.england)
    english_army3 = add_army(map.london, map.england)
    english_army4 = add_army(map.ruhr, map.england)
    french_fleet = add_fleet(map.english_channel, map.france)
    french_army1 = add_army(map.belgium, map.france)
    french_army2 = add_army(map.wales, map.france)

    map.parse_order_string('F NTH C A LON - BEL')
    map.parse_order_string('A HOL S A LON - BEL')
    map.parse_order_string('A YOR - LON')
    map.parse_order_string('A LON - BEL')
    map.parse_order_string('A RUH S A LON - BEL')
    map.parse_order_string('F ENG C A BEL - LON')
    map.parse_order_string('A BEL - LON')
    map.parse_order_string('A WAL S A BEL - LON')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 8)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_equal('English Army 1 Territory', english_army1.territory, map.holland)
    assert_equal('English Army 2 Territory', english_army2.territory, map.yorkshire)
    assert_equal('English Army 3 Territory', english_army3.territory, map.belgium)
    assert_equal('English Army 4 Territory', english_army4.territory, map.ruhr)
    assert_equal('French Fleet Territory', french_fleet.territory, map.english_channel)
    assert_equal('French Army 1 Territory', french_army1.territory, map.london)
    assert_equal('French Army 2 Territory', french_army2.territory, map.wales)

# 6.G.19
def test_swapping_with_intent_of_unnecessary_convoy():
    map = get_classic_map()
    french_army = add_army(map.marseilles, map.france)
    french_fleet = add_fleet(map.western_mediterranean, map.france)
    italian_fleet = add_fleet(map.gulf_of_lyon, map.italy)
    italian_army = add_army(map.spain, map.italy)

    map.parse_order_string('A MAR - SPA')
    map.parse_order_string('F WES C A MAR - SPA')
    map.parse_order_string('F LYO C A MAR - SPA')
    map.parse_order_string('A SPA - MAR')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.marseilles)
    assert_equal('French Fleet Territory', french_fleet.territory, map.western_mediterranean)
    assert_equal('Italian Fleet Territory', italian_fleet.territory, map.gulf_of_lyon)
    assert_equal('Italian Army Territory', italian_army.territory, map.spain)

# 6.G.20
def test_explicit_convoy_to_adjacent_province_disrupted():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.brest, map.france)
    french_army1 = add_army(map.picardy, map.france)
    french_army2 = add_army(map.burgundy, map.france)
    french_fleet2 = add_fleet(map.mid_atlantic_ocean, map.france)
    english_fleet = add_fleet(map.english_channel, map.england)

    map.parse_order_string('F BRE - ENG')
    map.parse_order_string('A PIC - BEL via convoy')
    map.parse_order_string('A BUR S A PIC - BEL')
    map.parse_order_string('F MAO S F BRE - ENG')
    map.parse_order_string('F ENG C A PIC - BEL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.english_channel)
    assert_equal('French Army 1 Territory', french_army1.territory, map.picardy)
    assert_equal('French Army 2 Territory', french_army2.territory, map.burgundy)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.mid_atlantic_ocean)
    assert_not_equal('English Fleet Territory', english_fleet.territory, map.english_channel)

# 6.H Retreating
# 6.H.1
def test_no_supports_during_retreat():
    map = get_classic_map()
    austrian_fleet = add_fleet(map.trieste, map.austria_hungary)
    austrian_army = add_army(map.serbia, map.austria_hungary)
    turkish_fleet = add_fleet(map.greece, map.turkey)
    italian_army1 = add_army(map.venice, map.italy)
    italian_army2 = add_army(map.tyrolia, map.italy)
    italian_fleet1 = add_fleet(map.ionian_sea, map.italy)
    italian_fleet2 = add_fleet(map.aegean_sea, map.italy)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('F TRI H')
    map.parse_order_string('A SER H')
    map.parse_order_string('F GRE H')
    map.parse_order_string('A VEN S A TYR - TRI')
    map.parse_order_string('A TYR - TRI')
    map.parse_order_string('F ION - GRE')
    map.parse_order_string('F AEG S F ION - GRE')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 7)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('Austrian Fleet Territory', austrian_fleet.territory, map.trieste)
    assert_equal('Austrian Army Territory', austrian_army.territory, map.serbia)
    assert_not_equal('Turkish Fleet Territory', turkish_fleet.territory, map.greece)
    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.venice)
    assert_equal('Italian Army 2 Territory', italian_army2.territory, map.trieste)
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.greece)
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.aegean_sea)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('F TRI - ALB')
    map.parse_order_string('A SER S F TRI - ALB')
    map.parse_order_string('F GRE - ALB')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 2)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Fleet Territory', austrian_fleet.territory, None)
    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, None)
    assert_equal('Austrian Fleet Disbanded', austrian_fleet.disbanded, True)
    assert_equal('Turkish Fleet Disbanded', turkish_fleet.disbanded, True)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.2
def test_no_supports_from_retreating_unit():
    map = get_classic_map()
    english_army = add_army(map.liverpool, map.england)
    english_fleet1 = add_fleet(map.yorkshire, map.england)
    english_fleet2 = add_fleet(map.norway, map.england)
    german_army1 = add_army(map.kiel, map.germany)
    german_army2 = add_army(map.ruhr, map.germany)
    russian_fleet1 = add_fleet(map.edinburgh, map.russia)
    russian_army1 = add_army(map.sweden, map.russia)
    russian_army2 = add_army(map.finland, map.russia)
    russian_fleet2 = add_fleet(map.holland, map.russia)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('A LPL - EDI')
    map.parse_order_string('F YOR S A LPL - EDI')
    map.parse_order_string('F NWY H')
    map.parse_order_string('A KIE S A RUH - HOL')
    map.parse_order_string('A RUH - HOL')
    map.parse_order_string('F EDI H')
    map.parse_order_string('A SWE S A FIN - NWY')
    map.parse_order_string('A FIN - NWY')
    map.parse_order_string('F HOL H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 9)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.edinburgh)
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.yorkshire)
    assert_not_equal('English Fleet 2 Territory', english_fleet2.territory, map.norway)
    assert_equal('German Army 1 Territory', german_army1.territory, map.kiel)
    assert_equal('German Army 2 Territory', german_army2.territory, map.holland)
    assert_not_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.edinburgh)
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.sweden)
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.norway)
    assert_not_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.holland)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('F NWY - NTH')
    map.parse_order_string('F EDI - NTH')
    map.parse_order_string('F HOL S F EDI - NTH')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 2)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 2 Territory', english_fleet2.territory, None)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, None)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, None)
    assert_equal('English Fleet 2 Disbanded', english_fleet2.disbanded, True)
    assert_equal('Russian Fleet 1 Disbanded', russian_fleet1.disbanded, True)
    assert_equal('Russian Fleet 2 Disbanded', russian_fleet2.disbanded, True)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.3
def test_no_convoy_during_retreat():
    map = get_classic_map()
    english_fleet = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.holland, map.england)
    german_fleet = add_fleet(map.kiel, map.germany)
    german_army = add_army(map.ruhr, map.germany)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('F NTH H')
    map.parse_order_string('A HOL H')
    map.parse_order_string('F KIE S A RUH - HOL')
    map.parse_order_string('A RUH - HOL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_not_equal('English Army Territory', english_army.territory, map.holland)
    assert_equal('German Fleet Territory', german_fleet.territory, map.kiel)
    assert_equal('German Army Territory', german_army.territory, map.holland)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('A HOL - YOR')
    map.parse_order_string('F NTH C A HOL - YOR')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, None)
    assert_equal('English Army Disbanded', english_army.disbanded, True)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.4
def test_no_other_moves_during_retreat():
    map = get_classic_map()
    english_fleet = add_fleet(map.north_sea, map.england)
    english_army = add_army(map.holland, map.england)
    german_fleet = add_fleet(map.kiel, map.germany)
    german_army = add_army(map.ruhr, map.germany)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('F NTH H')
    map.parse_order_string('A HOL H')
    map.parse_order_string('F KIE S A RUH - HOL')
    map.parse_order_string('A RUH - HOL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, map.north_sea)
    assert_not_equal('English Army Territory', english_army.territory, map.holland)
    assert_equal('German Fleet Territory', german_fleet.territory, map.kiel)
    assert_equal('German Army Territory', german_army.territory, map.holland)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('A HOL - BEL')
    map.parse_order_string('F NTH - NWG')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.belgium)
    assert_equal('English Army Disbanded', english_army.disbanded, False)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.5
def test_unit_may_not_retreat_to_area_from_which_it_is_attacked():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.constantinople, map.russia)
    russian_fleet2 = add_fleet(map.black_sea, map.russia)
    turkish_fleet = add_fleet(map.ankara, map.turkey)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('F CON S F BLA - ANK')
    map.parse_order_string('F BLA - ANK')
    map.parse_order_string('F ANK H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.constantinople)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.ankara)
    assert_not_equal('Turkish Fleet Territory', turkish_fleet.territory, map.ankara)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('F ANK - BLA')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Turkish Fleet Territory', turkish_fleet.territory, None)
    assert_equal('Turkish Fleet Disbanded', turkish_fleet.disbanded, True)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.6
def test_unit_may_not_retreat_to_a_contested_area():
    map = get_classic_map()
    austrian_army1 = add_army(map.budapest, map.austria_hungary)
    austrian_army2 = add_army(map.trieste, map.austria_hungary)
    german_army1 = add_army(map.munich, map.germany)
    german_army2 = add_army(map.silesia, map.germany)
    italian_army = add_army(map.vienna, map.italy)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('A BUD S A TRI - VIE')
    map.parse_order_string('A TRI - VIE')
    map.parse_order_string('A MUC - BOH')
    map.parse_order_string('A SIL - BOH')
    map.parse_order_string('A VIE H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.budapest)
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.vienna)
    assert_equal('German Army 1 Territory', german_army1.territory, map.munich)
    assert_equal('German Army 2 Territory', german_army2.territory, map.silesia)
    assert_not_equal('Italian Army Territory', italian_army.territory, map.vienna)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('A VIE - BOH')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Italian Army Territory', italian_army.territory, None)
    assert_equal('Italian Army Disbanded', italian_army.disbanded, True)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.7
def test_multiple_retreat_to_same_area_will_disband_units():
    map = get_classic_map()
    austrian_army1 = add_army(map.budapest, map.austria_hungary)
    austrian_army2 = add_army(map.trieste, map.austria_hungary)
    german_army1 = add_army(map.munich, map.germany)
    german_army2 = add_army(map.silesia, map.germany)
    italian_army1 = add_army(map.vienna, map.italy)
    italian_army2 = add_army(map.bohemia, map.italy)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('A BUD S A TRI - VIE')
    map.parse_order_string('A TRI - VIE')
    map.parse_order_string('A MUC S A SIL - BOH')
    map.parse_order_string('A SIL - BOH')
    map.parse_order_string('A VIE H')
    map.parse_order_string('A BOH H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Austrian Army 1 Territory', austrian_army1.territory, map.budapest)
    assert_equal('Austrian Army 2 Territory', austrian_army2.territory, map.vienna)
    assert_equal('German Army 1 Territory', german_army1.territory, map.munich)
    assert_equal('German Army 2 Territory', german_army2.territory, map.bohemia)
    assert_not_equal('Italian Army 1 Territory', italian_army1.territory, map.vienna)
    assert_not_equal('Italian Army 2 Territory', italian_army2.territory, map.bohemia)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('A BOH - TYR')
    map.parse_order_string('A VIE - TYR')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 2)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Italian Army 1 Territory', italian_army1.territory, None)
    assert_equal('Italian Army 1 Disbanded', italian_army1.disbanded, True)
    assert_equal('Italian Army 2 Territory', italian_army2.territory, None)
    assert_equal('Italian Army 2 Disbanded', italian_army2.disbanded, True)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.8
def test_triple_retreat_to_same_area_will_disband_units():
    map = get_classic_map()
    english_army = add_army(map.liverpool, map.england)
    english_fleet1 = add_fleet(map.yorkshire, map.england)
    english_fleet2 = add_fleet(map.norway, map.england)
    german_army1 = add_army(map.kiel, map.germany)
    german_army2 = add_army(map.ruhr, map.germany)
    russian_fleet1 = add_fleet(map.edinburgh, map.russia)
    russian_army1 = add_army(map.sweden, map.russia)
    russian_army2 = add_army(map.finland, map.russia)
    russian_fleet2 = add_fleet(map.holland, map.russia)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('A LPL - EDI')
    map.parse_order_string('F YOR S A LPL - EDI')
    map.parse_order_string('F NWY H')
    map.parse_order_string('A KIE S A RUH - HOL')
    map.parse_order_string('A RUH - HOL')
    map.parse_order_string('F EDI H')
    map.parse_order_string('A SWE S A FIN - NWY')
    map.parse_order_string('A FIN - NWY')
    map.parse_order_string('F HOL H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 9)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.edinburgh)
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.yorkshire)
    assert_not_equal('English Fleet 2 Territory', english_fleet2.territory, map.norway)
    assert_equal('German Army 1 Territory', german_army1.territory, map.kiel)
    assert_equal('German Army 2 Territory', german_army2.territory, map.holland)
    assert_not_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.edinburgh)
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.sweden)
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.norway)
    assert_not_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.holland)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('F NWY - NTH')
    map.parse_order_string('F EDI - NTH')
    map.parse_order_string('F HOL - NTH')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 2 Territory', english_fleet2.territory, None)
    assert_equal('English Fleet 2 Disbanded', english_fleet2.disbanded, True)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, None)
    assert_equal('Russian Fleet 1 Disbanded', russian_fleet1.disbanded, True)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, None)
    assert_equal('Russian Fleet 2 Disbanded', russian_fleet2.disbanded, True)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.9
def test_dislodged_unit_will_not_make_attackers_area_contested():
    map = get_classic_map()
    english_fleet1 = add_fleet(map.helgoland_bight, map.england)
    english_fleet2 = add_fleet(map.denmark, map.england)
    german_army1 = add_army(map.berlin, map.germany)
    german_fleet = add_fleet(map.kiel, map.germany)
    german_army2 = add_army(map.silesia, map.germany)
    russian_army = add_army(map.prussia, map.russia)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('F HEL - KIE')
    map.parse_order_string('F DEN S F HEL - KIE')
    map.parse_order_string('A BER - PRU')
    map.parse_order_string('F KIE H')
    map.parse_order_string('A SIL S A BER - PRU')
    map.parse_order_string('A PRU H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.kiel)
    assert_equal('English Fleet 2 Territory', english_fleet2.territory, map.denmark)
    assert_equal('German Army 1 Territory', german_army1.territory, map.prussia)
    assert_not_equal('German Fleet Territory', german_fleet.territory, map.kiel)
    assert_equal('German Army 2 Territory', german_army2.territory, map.silesia)
    assert_not_equal('Russian Army Territory', russian_army.territory, map.prussia)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('F KIE - BER')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Fleet Territory', german_fleet.territory, map.berlin)
    assert_equal('German Fleet Disbanded', german_fleet.disbanded, False)
    assert_equal('Russian Army Territory', russian_army.territory, None)
    assert_equal('Russian Army Disbanded', russian_army.disbanded, True)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.10
def test_not_retreating_to_attackers_does_not_mean_contested():
    map = get_classic_map()
    english_army = add_army(map.kiel, map.england)
    german_army1 = add_army(map.berlin, map.germany)
    german_army2 = add_army(map.munich, map.germany)
    german_army3 = add_army(map.prussia, map.germany)
    russian_army1 = add_army(map.warsaw, map.russia)
    russian_army2 = add_army(map.silesia, map.russia)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('A KIE H')
    map.parse_order_string('A BER - KIE')
    map.parse_order_string('A MUC S A BER - KIE')
    map.parse_order_string('A PRU H')
    map.parse_order_string('A WAR - PRU')
    map.parse_order_string('A SIL S A WAR - PRU')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('English Army Territory', english_army.territory, map.kiel)
    assert_equal('German Army 1 Territory', german_army1.territory, map.kiel)
    assert_equal('German Army 2 Territory', german_army2.territory, map.munich)
    assert_not_equal('German Army 3 Territory', german_army3.territory, map.prussia)
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.prussia)
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.silesia)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('A KIE - BER')
    map.parse_order_string('A PRU - BER')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 2)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, None)
    assert_equal('English Army Disbanded', english_army.disbanded, True)
    assert_equal('German Army 3 Territory', german_army3.territory, map.berlin)
    assert_equal('German Army 3 Disbanded', german_army3.disbanded, False)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.11
def test_retreat_when_dislodged_by_adjacent_convoy():
    map = get_classic_map()
    french_army1 = add_army(map.gascony, map.france)
    french_army2 = add_army(map.burgundy, map.france)
    french_fleet1 = add_fleet(map.mid_atlantic_ocean, map.france)
    french_fleet2 = add_fleet(map.western_mediterranean, map.france)
    french_fleet3 = add_fleet(map.gulf_of_lyon, map.france)
    italian_army = add_army(map.marseilles, map.italy)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('A GAS - MAR via convoy')
    map.parse_order_string('A BUR S A GAS - MAR')
    map.parse_order_string('F MAO C A GAS - MAR')
    map.parse_order_string('F WES C A GAS - MAR')
    map.parse_order_string('F LYO C A GAS - MAR')
    map.parse_order_string('A MAR H')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 6)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Army 1 Territory', french_army1.territory, map.marseilles)
    assert_equal('French Army 2 Territory', french_army2.territory, map.burgundy)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.mid_atlantic_ocean)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.western_mediterranean)
    assert_equal('French Fleet 3 Territory', french_fleet3.territory, map.gulf_of_lyon)
    assert_not_equal('Italian Army Territory', italian_army.territory, map.marseilles)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('A MAR - GAS')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Italian Army Territory', italian_army.territory, map.gascony)
    assert_equal('Italian Army Disbanded', italian_army.disbanded, False)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.12
def test_retreat_when_dislodged_by_adjacent_convoy_while_trying_to_do_the_same():
    map = get_classic_map()
    english_army = add_army(map.liverpool, map.england)
    english_fleet1 = add_fleet(map.irish_sea, map.england)
    english_fleet2 = add_fleet(map.english_channel, map.england)
    english_fleet3 = add_fleet(map.north_sea, map.england)
    french_fleet1 = add_fleet(map.brest, map.france)
    french_fleet2 = add_fleet(map.mid_atlantic_ocean, map.france)
    russian_army1 = add_army(map.edinburgh, map.russia)
    russian_fleet1 = add_fleet(map.norwegian_sea, map.russia)
    russian_fleet2 = add_fleet(map.north_atlantic_ocean, map.russia)
    russian_army2 = add_army(map.clyde, map.russia)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('A LPL - EDI via convoy')
    map.parse_order_string('F IRI C A LPL - EDI')
    map.parse_order_string('F ENG C A LPL - EDI')
    map.parse_order_string('F NTH C A LPL - EDI')
    map.parse_order_string('F BRE - ENG')
    map.parse_order_string('F MAO S F BRE - ENG')
    map.parse_order_string('A EDI - LPL via convoy')
    map.parse_order_string('F NWG C A EDI - LPL')
    map.parse_order_string('F NAO C A EDI - LPL')
    map.parse_order_string('A CLY S A EDI - LPL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 10)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('English Army Territory', english_army.territory, map.liverpool)
    assert_equal('English Fleet 1 Territory', english_fleet1.territory, map.irish_sea)
    assert_not_equal('English Fleet 2 Territory', english_fleet2.territory, map.english_channel)
    assert_equal('English Fleet 3 Territory', english_fleet3.territory, map.north_sea)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.english_channel)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.mid_atlantic_ocean)
    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.liverpool)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.norwegian_sea)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.north_atlantic_ocean)
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.clyde)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('A LPL - EDI')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, map.edinburgh)
    assert_equal('English Army Disbanded', english_army.disbanded, False)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.13
def test_no_retreat_with_convoy_in_movement_phase():
    map = get_classic_map()
    english_army = add_army(map.picardy, map.england)
    english_fleet = add_fleet(map.english_channel, map.england)
    french_army1 = add_army(map.paris, map.france)
    french_army2 = add_army(map.brest, map.france)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('A PIC H')
    map.parse_order_string('F ENG C A PIC - LON')
    map.parse_order_string('A PAR - PIC')
    map.parse_order_string('A BRE S A PAR - PIC')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 4)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('English Army Territory', english_army.territory, map.picardy)
    assert_equal('English Fleet Territory', english_fleet.territory, map.english_channel)
    assert_equal('French Army 1 Territory', french_army1.territory, map.picardy)
    assert_equal('French Army 2 Territory', french_army2.territory, map.brest)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('A PIC - LON')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, None)
    assert_equal('English Army Disbanded', english_army.disbanded, True)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.14
def test_no_retreat_with_support_in_movement_phase():
    map = get_classic_map()
    english_army = add_army(map.picardy, map.england)
    english_fleet = add_fleet(map.english_channel, map.england)
    french_army1 = add_army(map.paris, map.france)
    french_army2 = add_army(map.brest, map.france)
    french_army3 = add_army(map.burgundy, map.france)
    german_army1 = add_army(map.munich, map.germany)
    german_army2 = add_army(map.marseilles, map.germany)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('A PIC H')
    map.parse_order_string('F ENG S A PIC - BEL')
    map.parse_order_string('A PAR - PIC')
    map.parse_order_string('A BRE S A PAR - PIC')
    map.parse_order_string('A BUR H')
    map.parse_order_string('A MUC S A MAR - BUR')
    map.parse_order_string('A MAR - BUR')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 7)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('English Army Territory', english_army.territory, map.picardy)
    assert_equal('English Fleet Territory', english_fleet.territory, map.english_channel)
    assert_equal('French Army 1 Territory', french_army1.territory, map.picardy)
    assert_equal('French Army 2 Territory', french_army2.territory, map.brest)
    assert_not_equal('French Army 3 Territory', french_army3.territory, map.burgundy)
    assert_equal('German Army 1 Territory', german_army1.territory, map.munich)
    assert_equal('German Army 2 Territory', german_army2.territory, map.burgundy)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('A PIC - BEL')
    map.parse_order_string('A BUR - BEL')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 2)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Army Territory', english_army.territory, None)
    assert_equal('English Army Disbanded', english_army.disbanded, True)
    assert_equal('French Army 3 Territory', french_army3.territory, None)
    assert_equal('French Army 3 Disbanded', french_army3.disbanded, True)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.15
def test_no_coastal_crawl_in_retreat():
    map = get_classic_map()
    english_fleet = add_fleet(map.portugal, map.england)
    french_fleet1 = add_fleet(map.spain, map.france, 'sc')
    french_fleet2 = add_fleet(map.mid_atlantic_ocean, map.france)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('F POR H')
    map.parse_order_string('F SPA - POR')
    map.parse_order_string('F MAO S F SPA - POR')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('English Fleet Territory', english_fleet.territory, map.portugal)
    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.portugal)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.mid_atlantic_ocean)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('F POR - SPA(nc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('English Fleet Territory', english_fleet.territory, None)
    assert_equal('English Fleet Disbanded', english_fleet.disbanded, True)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.H.16
def test_contested_for_both_coasts():
    map = get_classic_map()
    french_fleet1 = add_fleet(map.mid_atlantic_ocean, map.france)
    french_fleet2 = add_fleet(map.gascony, map.france)
    french_fleet3 = add_fleet(map.western_mediterranean, map.france)
    italian_fleet1 = add_fleet(map.tunis, map.italy)
    italian_fleet2 = add_fleet(map.tyrrhenian_sea, map.italy)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('F MAO - SPA(nc)')
    map.parse_order_string('F GAS - SPA(nc)')
    map.parse_order_string('F WES H')
    map.parse_order_string('F TUN S F TYS - WES')
    map.parse_order_string('F TYS - WES')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 5)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet 1 Territory', french_fleet1.territory, map.mid_atlantic_ocean)
    assert_equal('French Fleet 2 Territory', french_fleet2.territory, map.gascony)
    assert_not_equal('French Fleet 3 Territory', french_fleet3.territory, map.western_mediterranean)
    assert_equal('Italian Fleet 1 Territory', italian_fleet1.territory, map.tunis)
    assert_equal('Italian Fleet 2 Territory', italian_fleet2.territory, map.western_mediterranean)

    assert_equal('Map Phase', map.get_phase(), 'Spring Retreat')

    map.parse_order_string('F WES - SPA(sc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet 3 Territory', french_fleet3.territory, None)
    assert_equal('French Fleet 3 Disbanded', french_fleet3.disbanded, True)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

# 6.I Building
# 6.I.1
def test_too_many_build_orders():
    map = get_classic_map()
    # Leave only one build slot open for germany
    add_army(map.berlin, map.germany)
    add_army(map.prussia, map.germany)
    
    assert_equal('German Units', len(map.germany.units), 2)
    assert_equal('German Available Units', map.germany.units_to_build(map.territories), 1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    map.parse_order_string('Build A WAR', owner=map.germany)
    map.parse_order_string('Build A KIE', owner=map.germany)
    map.parse_order_string('Build A MUC', owner=map.germany)
    assert_equal('Map Queued orders Count', len(map.queued_orders), 2)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Units', len(map.germany.units), 3)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.I.2
def test_fleets_cannot_be_built_in_land_areas():
    map = get_classic_map()
    # Leave only one build slot open for russia
    add_army(map.finland, map.russia)
    add_army(map.st_petersburg, map.russia)
    add_army(map.livonia, map.russia)
    
    assert_equal('Russian Units', len(map.russia.units), 3)
    assert_equal('Russian Available Units', map.russia.units_to_build(map.territories), 1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    map.parse_order_string('Build F MOS', owner=map.russia)
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Units', len(map.russia.units), 3)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.I.3
def test_supply_center_must_be_empty_for_building():
    map = get_classic_map()
    # Leave only one build slot open for russia
    add_army(map.berlin, map.germany)
    add_army(map.finland, map.germany)
    
    assert_equal('German Units', len(map.germany.units), 2)
    assert_equal('German Available Units', map.germany.units_to_build(map.territories), 1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    map.parse_order_string('Build A BER', owner=map.germany)
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Units', len(map.germany.units), 2)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.I.4
def test_both_coasts_must_be_empty_for_building():
    map = get_classic_map()
    # Leave only one build slot open for russia
    add_army(map.finland, map.russia)
    add_fleet(map.st_petersburg, map.russia, 'sc')
    add_army(map.livonia, map.russia)
    
    assert_equal('Russian Units', len(map.russia.units), 3)
    assert_equal('Russian Available Units', map.russia.units_to_build(map.territories), 1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    map.parse_order_string('Build F STP(nc)', owner=map.russia)
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Units', len(map.russia.units), 3)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.I.5
def test_building_in_home_supply_center_that_is_not_owned():
    map = get_classic_map()
    # Leave only one build slot open for russia
    russian_army = add_army(map.kiel, map.russia)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

    map.parse_order_string('A KIE - BER')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('Russian Army Territory', russian_army.territory, map.berlin)

    assert_equal('Map Phase', map.get_phase(), 'Fall')

    map.parse_order_string('A BER - KIE')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)
    
    assert_equal('Russian Army Territory', russian_army.territory, map.kiel)

    assert_equal('Map Phase', map.get_phase(), 'Adjustment')
    
    assert_equal('German Units', len(map.germany.units), 0)
    assert_equal('German Available Units', map.germany.units_to_build(map.territories), 1)

    map.parse_order_string('Build A BER', owner=map.germany)
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Units', len(map.germany.units), 0)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.I.6
def test_building_in_owned_supply_center_that_is_not_a_home_supply_center():
    map = get_classic_map()
    # Leave only one build slot open for russia
    add_army(map.berlin, map.germany)
    add_army(map.prussia, map.germany)
    add_army(map.kiel, map.germany)

    map.warsaw.owner = map.germany
    
    assert_equal('German Units', len(map.germany.units), 3)
    assert_equal('German Available Units', map.germany.units_to_build(map.territories), 1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    map.parse_order_string('Build A WAR', owner=map.germany)
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('German Units', len(map.germany.units), 3)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.I.7
def test_only_one_build_in_a_home_supply_center():
    map = get_classic_map()
    # Leave only one build slot open for russia
    add_army(map.ukraine, map.russia)
    add_army(map.prussia, map.russia)
    
    assert_equal('Russian Units', len(map.russia.units), 2)
    assert_equal('Russian Available Units', map.russia.units_to_build(map.territories), 2)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    map.parse_order_string('Build A MOS', owner=map.russia)
    map.parse_order_string('Build A MOS', owner=map.russia)
    assert_equal('Map Queued orders Count', len(map.queued_orders), 2)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Units', len(map.russia.units), 3)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.J Civil Disorder and Disbands
# 6.J.1
def test_too_many_disband_orders():
    map = get_classic_map()
    french_army1 = add_army(map.paris, map.france)
    french_army2 = add_army(map.picardy, map.france)

    map.brest.owner = map.russia
    map.marseilles.owner = map.russia
    
    assert_equal('French Units', len(map.france.units), 2)
    assert_equal('French Available Units', map.france.units_to_build(map.territories), -1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    map.parse_order_string('Remove F LYO', owner=map.france)
    map.parse_order_string('Remove A PIC', owner=map.france)
    map.parse_order_string('Remove A PAR', owner=map.france)
    assert_equal('Map Queued orders Count', len(map.queued_orders), 2)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Units', len(map.france.units), 1)

    assert_equal('French Army 1 Territory', french_army1.territory, map.paris)
    assert_equal('French Army 2 Territory', french_army2.territory, None)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.J.2
def test_removing_the_same_unit_twice():
    map = get_classic_map()
    french_army1 = add_army(map.paris, map.france)
    french_army2 = add_army(map.picardy, map.france)

    map.brest.owner = map.russia
    map.marseilles.owner = map.russia
    
    assert_equal('French Units', len(map.france.units), 2)
    assert_equal('French Available Units', map.france.units_to_build(map.territories), -1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    map.parse_order_string('Remove A PAR', owner=map.france)
    map.parse_order_string('Remove A PAR', owner=map.france)
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Units', len(map.france.units), 1)

    assert_equal('French Army 1 Territory', french_army1.territory, None)
    assert_equal('French Army 2 Territory', french_army2.territory, map.picardy)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.J.3
def test_civil_disorder_two_armies_with_different_distance():
    map = get_classic_map()
    russian_army1 = add_army(map.livonia, map.russia)
    russian_army2 = add_army(map.sweden, map.russia)
    russian_army3 = add_army(map.finland, map.russia)

    map.st_petersburg.owner = map.russia

    map.moscow.owner = map.france
    map.warsaw.owner = map.france
    map.sevastopol.owner = map.france
    
    assert_equal('Russian Units', len(map.russia.units), 3)
    assert_equal('Russian Available Units', map.russia.units_to_build(map.territories), -1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Units', len(map.russia.units), 2)

    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.livonia)
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.sweden)
    assert_equal('Russian Army 3 Territory', russian_army3.territory, None)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.J.4
def test_civil_disorder_two_armies_with_equal_distance():
    map = get_classic_map()
    russian_army1 = add_army(map.livonia, map.russia)
    russian_army2 = add_army(map.ukraine, map.russia)
    add_army(map.moscow, map.russia)

    map.moscow.owner = map.russia

    map.warsaw.owner = map.france
    map.sevastopol.owner = map.france
    
    assert_equal('Russian Units', len(map.russia.units), 3)
    assert_equal('Russian Available Units', map.russia.units_to_build(map.territories), -1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Units', len(map.russia.units), 2)

    assert_equal('Russian Army 1 Territory', russian_army1.territory, None)
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.ukraine)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.J.5
def test_civil_disorder_two_fleets_with_different_distance():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.skagerrak, map.russia)
    russian_fleet2 = add_fleet(map.berlin, map.russia)
    add_army(map.prussia, map.russia)

    map.st_petersburg.owner = map.russia

    map.moscow.owner = map.france
    map.warsaw.owner = map.france
    map.sevastopol.owner = map.france
    
    assert_equal('Russian Units', len(map.russia.units), 3)
    assert_equal('Russian Available Units', map.russia.units_to_build(map.territories), -1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Units', len(map.russia.units), 2)

    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, None)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.berlin)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.J.6
def test_civil_disorder_two_fleets_with_equal_distance():
    map = get_classic_map()
    russian_fleet1 = add_fleet(map.gulf_of_bothnia, map.russia)
    russian_fleet2 = add_fleet(map.north_sea, map.russia)

    map.munich.owner = map.russia

    map.st_petersburg.owner = map.france
    map.moscow.owner = map.france
    map.warsaw.owner = map.france
    map.sevastopol.owner = map.france
    
    assert_equal('Russian Units', len(map.russia.units), 2)
    assert_equal('Russian Available Units', map.russia.units_to_build(map.territories), -1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Units', len(map.russia.units), 1)

    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, None)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, map.north_sea)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.J.7
def test_civil_disorder_two_fleets_and_army_with_equal_distance():
    map = get_classic_map()
    russian_army = add_army(map.bohemia, map.russia)
    russian_fleet1 = add_fleet(map.skagerrak, map.russia)
    russian_fleet2 = add_fleet(map.north_sea, map.russia)

    map.st_petersburg.owner = map.russia
    map.warsaw.owner = map.russia

    map.moscow.owner = map.france
    map.sevastopol.owner = map.france
    
    assert_equal('Russian Units', len(map.russia.units), 3)
    assert_equal('Russian Available Units', map.russia.units_to_build(map.territories), -1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Units', len(map.russia.units), 2)

    assert_equal('Russian Army Territory', russian_army.territory, map.bohemia)
    assert_equal('Russian Fleet 1 Territory', russian_fleet1.territory, map.skagerrak)
    assert_equal('Russian Fleet 2 Territory', russian_fleet2.territory, None)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.J.8
def test_civil_disorder_a_fleet_with_shorter_distance_than_the_army():
    map = get_classic_map()
    russian_army = add_army(map.tyrolia, map.russia)
    russian_fleet = add_fleet(map.baltic_sea, map.russia)

    map.warsaw.owner = map.russia

    map.st_petersburg.owner = map.france
    map.moscow.owner = map.france
    map.sevastopol.owner = map.france
    
    assert_equal('Russian Units', len(map.russia.units), 2)
    assert_equal('Russian Available Units', map.russia.units_to_build(map.territories), -1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Units', len(map.russia.units), 1)

    assert_equal('Russian Army Territory', russian_army.territory, None)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, map.baltic_sea)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.J.9
def test_civil_disorder_must_be_counted_from_both_coasts():
    map = get_classic_map()
    russian_army1 = add_army(map.greece, map.russia)
    russian_army2 = add_army(map.sevastopol, map.russia)
    russian_fleet = add_fleet(map.baltic_sea, map.russia)
    add_army(map.prussia, map.russia)

    map.st_petersburg.owner = map.russia
    map.sevastopol.owner = map.russia

    map.warsaw.owner = map.france
    map.moscow.owner = map.france
    
    assert_equal('Russian Units', len(map.russia.units), 4)
    assert_equal('Russian Available Units', map.russia.units_to_build(map.territories), -1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Russian Units', len(map.russia.units), 3)

    assert_equal('Russian Army 1 Territory', russian_army1.territory, map.greece)
    assert_equal('Russian Army 2 Territory', russian_army2.territory, map.sevastopol)
    assert_equal('Russian Fleet Territory', russian_fleet.territory, None)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.J.10
def test_civil_disorder_counting_convoying_distance():
    map = get_classic_map()
    italian_army1 = add_army(map.greece, map.italy)
    italian_army2 = add_army(map.piedmont, map.italy)
    add_army(map.tuscany, map.italy)

    map.naples.owner = map.italy

    map.venice.owner = map.france
    map.rome.owner = map.france
    
    assert_equal('Italian Units', len(map.italy.units), 3)
    assert_equal('Italian Available Units', map.italy.units_to_build(map.territories), -1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Italian Units', len(map.italy.units), 2)

    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.greece)
    assert_equal('Italian Army 2 Territory', italian_army2.territory, None)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# 6.J.11
def test_distance_to_owned_supply_center():
    map = get_classic_map()
    italian_army1 = add_army(map.warsaw, map.italy)
    italian_army2 = add_army(map.tuscany, map.italy)

    map.warsaw.owner = map.italy

    map.naples.owner = map.france
    map.venice.owner = map.france
    map.rome.owner = map.france
    
    assert_equal('Italian Units', len(map.italy.units), 2)
    assert_equal('Italian Available Units', map.italy.units_to_build(map.territories), -1)

    map.set_phase('Adjustment')
    assert_equal('Map Phase', map.get_phase(), 'Adjustment')

    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('Italian Units', len(map.italy.units), 1)

    assert_equal('Italian Army 1 Territory', italian_army1.territory, map.warsaw)
    assert_equal('Italian Army 2 Territory', italian_army2.territory, None)

    assert_equal('Map Phase', map.get_phase(), 'Spring')

# Transform Orders
# T.1
def test_transform_coastal_army():
    map = get_classic_map()
    french_army = add_army(map.norway, map.france)

    map.parse_order_string('A NWY T')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet Territory', french_army.territory, map.norway)
    assert_equal('French Fleet Type', french_army.type, 'Fleet')

# T.2
def test_transform_inland_army():
    map = get_classic_map()
    french_army = add_army(map.moscow, map.france)

    map.parse_order_string('A MOS T')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.moscow)
    assert_equal('French Army Type', french_army.type, 'Army')

# T.3
def test_transform_coastal_fleet():
    map = get_classic_map()
    french_fleet = add_fleet(map.sweden, map.france)

    map.parse_order_string('F SWE T')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Army Territory', french_fleet.territory, map.sweden)
    assert_equal('French Army Type', french_fleet.type, 'Army')

# T.4
def test_transform_coastal_army_to_south_coast():
    map = get_classic_map()
    french_army = add_army(map.st_petersburg, map.france)

    map.parse_order_string('A STP T(sc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 1)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet Territory', french_army.territory, map.st_petersburg)
    assert_equal('French Fleet Territory Coast', french_army.territory.unit_coast, 'sc')
    assert_equal('French Fleet Type', french_army.type, 'Fleet')

# T.5
def test_transform_coastal_army_to_invalid_south_coast():
    map = get_classic_map()
    french_army = add_army(map.norway, map.france)

    map.parse_order_string('A NWY T(sc)')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Army Territory', french_army.territory, map.norway)
    assert_equal('French Army Territory Coast', french_army.territory.unit_coast, None)
    assert_equal('French Army Type', french_army.type, 'Army')

# T.6
def test_transform_fleet_in_water():
    map = get_classic_map()
    french_fleet = add_fleet(map.north_atlantic_ocean, map.france)

    map.parse_order_string('F NAO T')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_equal('French Fleet Territory', french_fleet.territory, map.north_atlantic_ocean)
    assert_equal('French Fleet Type', french_fleet.type, 'Fleet')

# T.7
def test_dislodged_army_cannot_transform():
    map = get_classic_map()
    french_army = add_army(map.gascony, map.france)
    german_army1 = add_army(map.marseilles, map.germany)
    german_army2 = add_army(map.spain, map.germany)

    map.parse_order_string('A GAS T')
    map.parse_order_string('A MAR - GAS')
    map.parse_order_string('A SPA S A MAR - GAS')
    assert_equal('Map Queued orders Count', len(map.queued_orders), 3)

    map.resolve_orders()
    assert_equal('Map Queued orders Count', len(map.queued_orders), 0)

    assert_not_equal('French Army Territory', french_army.territory, map.gascony)
    assert_equal('German Army 1 Territory', german_army1.territory, map.gascony)
    assert_equal('German Army 2 Territory', german_army2.territory, map.spain)
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