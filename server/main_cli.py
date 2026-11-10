from game.game import Game
from game.unit import Unit
from game.enums import ARMY, FLEET

def add_army(territory, owner):
    unit = Unit(owner, ARMY, territory)
    territory.set_unit(unit)
    owner.add_unit(unit)
    return unit

def add_fleet(territory, owner, coast=None):
    unit = Unit(owner, FLEET, territory)
    territory.set_unit(unit, coast=coast)
    owner.add_unit(unit)
    return unit

if __name__ == "__main__":
    map = Game(start_phase='Spring', render=False, allow_transformations=True)

    # game.do_gameplay_loop()
    english_army = add_army(map.game_state.get_territory('PIC'), map.game_state.get_player('England'))
    english_fleet = add_fleet(map.game_state.get_territory('ENG'), map.game_state.get_player('England'))
    french_army1 = add_army(map.game_state.get_territory('PAR'), map.game_state.get_player('France'))
    french_army2 = add_army(map.game_state.get_territory('BRE'), map.game_state.get_player('France'))

    print(map.order_generator.generate_valid_orders())

    map.submit_order('A PIC H')
    map.submit_order('F ENG C A PIC - LON')
    map.submit_order('A PAR - PIC')
    map.submit_order('A BRE S A PAR - PIC')