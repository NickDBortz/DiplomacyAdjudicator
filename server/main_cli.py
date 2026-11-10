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
    french_army = add_army(map.game_state.get_territory('MAR'), map.game_state.get_player('France'))
    french_fleet = add_fleet(map.game_state.get_territory('SPA'), map.game_state.get_player('France'), coast='sc')
    italian_fleet = add_fleet(map.game_state.get_territory('LYO'), map.game_state.get_player('Italy'))
    turkish_fleet1 = add_fleet(map.game_state.get_territory('TYS'), map.game_state.get_player('Turkey'))
    turkish_fleet2 = add_fleet(map.game_state.get_territory('WES'), map.game_state.get_player('Turkey'))

    orders = map.order_generator.generate_valid_orders()
    split_order = orders[0].split(' ')
    prefix1 = split_order[0]
    prefix2 = split_order[1]
    print(f'{prefix1} {prefix2}: ')
    for order in orders:
        split_order = order.split(' ')
        if split_order[0] == prefix1 and split_order[1] == prefix2:
            print(order)
        else:
            prefix1 = split_order[0]
            prefix2 = split_order[1]
            print()
            print(f'{prefix1} {prefix2}: ')
            print(order)

    map.submit_order('A MAR - LYO')
    map.submit_order('F SPA S A MAR - LYO')
    map.submit_order('F LYO H')
    map.submit_order('F TYS S F WES - LYO')
    map.submit_order('F WES - LYO')