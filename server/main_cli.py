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
    french_army = add_army(map.game_state.get_territory('STP'), map.game_state.get_player('France'))

    print(map.order_generator.generate_valid_orders())

    map.submit_order('A STP T(sc)')