from game.player import Player
from game.territory import LandTerritory, WaterTerritory
from game.state import GameState
from game.adjudicator import Adjudicator
from game.order_parser import OrderParser
from game.renderer import BlankRenderer, CV2Renderer
from pathlib import Path
import json

class MapLoader:
    def __init__(self, json_file='data/maps/classic_map.json'):
        self.json_file = json_file

    def load_map_json(self, load_rendering_data):
        json_file_path = Path(self.json_file)
        if not json_file_path.is_file():
            self.json_file = 'data/maps/classic_map.json'

        with open(self.json_file, 'r') as file:
            map_obj = json.load(file)

            # ------ Create Game State ------

            # Load Players
            players_obj = map_obj['players']
            players = []
            for player_obj in players_obj:
                player = Player(player_obj['name'], player_obj['color'])
                players.append(player)
                # setattr(self, player_obj['var_name'], player)
                # self.players.append(player)

            water_color = map_obj['water_color']

            # Load Territories
            territories_obj = map_obj['territories']
            territories = []
            for territory_obj in territories_obj:
                name = territory_obj['name']
                abbr = territory_obj['abbr']
                is_supply_center = territory_obj['supply_center']
                owner_name = territory_obj['owner']
                owner = next((player for player in players if player.name == owner_name), None)

                label_pos = territory_obj['label_pos']
                polygons = []
                if load_rendering_data:
                    polygons = territory_obj['polygons']

                if territory_obj['land']:
                    supply_center_pos = territory_obj['supply_center_pos']
                    army_pos = territory_obj['army_pos']
                    coast_pos = territory_obj['coast_pos']
                    south_coast_pos = territory_obj['south_coast_pos']
                    territory = LandTerritory(name, abbr, is_supply_center, owner, polygons, label_pos, supply_center_pos, army_pos, coast_pos, south_coast_pos)
                else:
                    fleet_pos = territory_obj['fleet_pos']
                    territory = WaterTerritory(name, abbr, owner, water_color, polygons, label_pos, fleet_pos)

                # setattr(self, territory_obj['var_name'], territory)
                # self.territories.append(territory)
                territories.append(territory)

            # Set Adjacents
            for territory_obj in territories_obj:
                territory = next((t for t in territories if t.name == territory_obj['name']), None)

                for nth_adj_name in territory_obj['north_coast']:
                    nth_adj = next((t for t in territories if t.name == nth_adj_name), None)
                    territory.set_adjacent(nth_adj, 'nc')

                for sth_adj_name in territory_obj['south_coast']:
                    sth_adj = next((t for t in territories if t.name == sth_adj_name), None)
                    territory.set_adjacent(sth_adj, 'sc')

                for adj_name in territory_obj['adjacents']:
                    adj = next((t for t in territories if t.name == adj_name), None)
                    territory.set_adjacent(adj)

            game_state = GameState(players, territories)

            # ------ Create Adjudicator ------

            supply_centers_to_win = map_obj['win_count']

            adjudicator = Adjudicator(game_state, supply_centers_to_win)

            # ------ Create Order Parser ------

            order_parser = OrderParser(adjudicator, game_state)

            # ------ Create Renderer ------

            width = map_obj['width']
            height = map_obj['height']
            vertices = []
            if load_rendering_data:
                vertices = map_obj['vertices']

            renderer = None
            if load_rendering_data:
                renderer = CV2Renderer(width, height, vertices, game_state)
                for territory in territories:
                    renderer.smooth_polygons(territory)
            else:
                renderer = BlankRenderer()

            return game_state, adjudicator, order_parser, renderer