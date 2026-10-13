from map import Map
from unit import Unit

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

if __name__ == "__main__":
    map = Map()

    map.do_gameplay_loop()