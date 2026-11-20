from game.player import Player
from game.territory import LandTerritory, WaterTerritory
from game.enums import NORTH_COAST, SOUTH_COAST
from pathlib import Path
import json

class MapLoader:
    def __init__(self, json_file='/data/maps/classic_map/classic_map.json', variant=None):
        self.json_file = json_file
        self.variant = variant if variant is not None else {}

    def load_map_json(self):
        json_file_path = Path(self.json_file)
        if not json_file_path.is_file():
            self.json_file = str(Path(__file__).resolve().parent.parent / 'data' / 'maps' / 'classic_map' / 'classic_map.json')

        with open(self.json_file, 'r') as file:
            map_obj = json.load(file)

            # ------ Create Game State ------

            # Load Players
            players_obj = map_obj['players'] + self.variant.get('add_power', [])
            players = []
            for player_obj in players_obj:
                if any(player.name.lower() == player_obj['name'].lower() for player in players):
                    raise ValueError(f"Duplicate power: {player_obj['name']}")
                player = Player(player_obj['name'], player_obj['color'])
                players.append(player)

            # Load Territories
            territories_obj = map_obj['territories']
            territories_by_name = {territory['name']: territory for territory in territories_obj}
            player_names = {player.name for player in players}
            for change in self.variant.get('modify_ownership', []):
                name = change['territory_name']
                owner = change['new_owner']
                if name not in territories_by_name:
                    raise ValueError(f'Unknown territory in variant: {name}')
                if owner not in player_names and owner not in ('', None):
                    raise ValueError(f'Unknown power in variant: {owner}')
                territories_by_name[name]['owner'] = owner
            territories = []
            for territory_obj in territories_obj:
                name = territory_obj['name']
                abbr = territory_obj['abbr']
                is_supply_center = territory_obj['supply_center']
                owner_name = territory_obj['owner']
                owner = next((player for player in players if player.name == owner_name), None)

                if territory_obj['land']:
                    territory = LandTerritory(name, abbr, is_supply_center, owner)
                else:
                    territory = WaterTerritory(name, abbr, owner)

                territories.append(territory)

            # Set Adjacents
            for territory_obj in territories_obj:
                territory = next((t for t in territories if t.name == territory_obj['name']), None)

                for nth_adj_name in territory_obj['north_coast']:
                    nth_adj = next((t for t in territories if t.name == nth_adj_name), None)
                    territory.set_adjacent(nth_adj, NORTH_COAST)

                for sth_adj_name in territory_obj['south_coast']:
                    sth_adj = next((t for t in territories if t.name == sth_adj_name), None)
                    territory.set_adjacent(sth_adj, SOUTH_COAST)

                for adj_name in territory_obj['adjacents']:
                    adj = next((t for t in territories if t.name == adj_name), None)
                    territory.set_adjacent(adj)

            # ------ Create Adjudicator ------

            supply_centers_to_win = self.variant.get('win_count', map_obj['win_count'])

            # ------ Create Renderer ------

            width = map_obj['width']
            height = map_obj['height']
            vertices = map_obj['vertices']
            water_color = map_obj['water_color']
            start_date = self.variant.get('start_date', 1901)

            return players, territories, supply_centers_to_win, width, height, vertices, water_color, territories_obj, start_date