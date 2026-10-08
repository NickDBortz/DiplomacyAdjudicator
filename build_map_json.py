from map import Map
from territory import LandTerritory
import json
import re

def to_snake_case(text):
    s1 = re.sub('([a-z])([A-Z][a-z]+)', r'\1_\2', text)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    s3 = re.sub('[\s\-]+', '_', s2)
    return s3.lower()

if __name__ == '__main__':
    map = Map()

    obj = {
        'players': [],
        'vertices': [],
        'edges': [],
        'territories': []
    }

    for player in map.players:
        player_obj = {
            'name': player.name,
            'var_name': to_snake_case(player.name),
            'hex': '#000000'
        }
        obj['players'].append(player_obj)

    for territory in map.territories:
        territory_obj = {
            'name': territory.name,
            'abbr': territory.abbr,
            'var_name': to_snake_case(territory.name),
            'owner': territory.owner.name if territory.owner is not None else '',
            'land': isinstance(territory, LandTerritory),
            'supply_center': territory.is_supply_center,
            'adjacents': [],
            'north_coast': [],
            'south_coast': [],
            'edges': []
        }

        for adj in territory.adjacents:
            territory_obj['adjacents'].append(adj.name)
            if adj in territory.north_coast:
                territory_obj['north_coast'].append(adj.name)
            if adj in territory.south_coast:
                territory_obj['south_coast'].append(adj.name)

        obj['territories'].append(territory_obj)

    json_string = json.dumps(obj, indent=4)
    with open('classic_map.json', 'w', encoding='utf-8') as file:
        file.write(json_string)