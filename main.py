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

    add_army(map.st_petersburg, map.russia)
    add_army(map.moscow, map.russia)
    add_army(map.warsaw, map.russia)
    add_army(map.sevastopol, map.russia)
    add_army(map.constantinople, map.russia)
    add_army(map.ankara, map.russia)
    add_army(map.smyrna, map.russia)
    add_army(map.vienna, map.russia)
    add_army(map.budapest, map.russia)
    add_army(map.trieste, map.russia)
    add_army(map.berlin, map.russia)
    add_army(map.kiel, map.russia)
    add_army(map.munich, map.russia)
    add_army(map.sweden, map.russia)
    add_army(map.norway, map.russia)
    add_army(map.rumania, map.russia)
    add_army(map.bulgaria, map.russia)
    add_army(map.serbia, map.russia)

    map.do_gameplay_loop()