from game.map_loader import MapLoader
from game.state import GameState
from game.adjudicator import Adjudicator
from game.order_parser import OrderParser
from game.renderer import BlankRenderer, CV2Renderer
from game.enums import ADJUSTMENT_PHASE, SPRING_RETREAT_PHASE, FALL_RETREAT_PHASE

class Game:
    def __init__(self, json_file='data/maps/classic_map.json', start_phase=ADJUSTMENT_PHASE, render=True, allow_transformations=False):
        # Create a map loader to load the json file and populate the rest of the objects
        loader = MapLoader(json_file)

        players, territories, supply_centers_to_win, width, height, vertices, water_color, territories_obj = loader.load_map_json()

        self.game_state = GameState(players, territories)
        self.adjudicator = Adjudicator(self.game_state, supply_centers_to_win)
        self.order_parser = OrderParser(self.adjudicator, self.game_state)
        if render:
            self.renderer = CV2Renderer(width, height, vertices, water_color, territories_obj, self.game_state)
        else:
            self.renderer = BlankRenderer()

        self.game_state.set_phase(start_phase)
        if allow_transformations:
            self.order_parser.activate_transformations()

    def submit_order(self, order, owner=None):
        self.order_parser.parse_order_string(order, owner)

    def do_gameplay_loop(self):
        while True:
            self.renderer.render()

            phase = self.game_state.get_phase()
            print(f'{phase} Phase, {self.game_state.year}')

            # Request any number of orders until told to stop
            self._get_user_orders()

            # If a draw proposal has succeeded, render the final frame and break
            if self.game_state.draw:
                print('All remaining players have chosen to draw.')
                self.renderer.render(wait=True)
                break

            # Render the orders
            self.renderer.render()

            # Wait for Enter before resolving the orders
            input('Press Enter to resolve...')

            # Resolve the orders
            self.adjudicator.resolve_orders()

            # If there is a winner, render the final frame and break
            if self.game_state.winner is not None:
                print(f'{self.game_state.winner.name} wins!')
                self.renderer.render(wait=True)
                break

    def _get_user_orders(self):
        phase = self.game_state.get_phase()

        # If the phase is a retreat phase, list the players that need to retreat troops
        if phase in [SPRING_RETREAT_PHASE, FALL_RETREAT_PHASE]:
            players = []
            dislodged = self.adjudicator.gather_dislodged()
            for d in dislodged:
                if d.owner not in players:
                    players.append(d.owner)
            for player in players:
                print(f'{player.name} has dislodged units that need to retreat.')

        # If the phase is an adjustment phase, list the players that need to build/disband troops
        if phase == ADJUSTMENT_PHASE:
            for player in self.game_state.players:
                units_to_build = player.units_to_build(self.game_state.territories)
                if units_to_build > 0:
                    print(f'{player.name} has {units_to_build} units to build.')
                elif units_to_build < 0:
                    print(f'{player.name} has {-units_to_build} units to disband.')

        # List of players who can choose to draw (must be an active player)
        no_draw_list = [player.name for player in self.game_state.players if player.get_supply_centers(self.game_state.territories) > 0]
        draw_proposed = False

        # Until told to stop, ask for orders
        while True:
            if draw_proposed:
                print('A draw has been proposed. Order "draw" to vote to draw.')
            user_name = input('Name of Great Power (e.g. Russia; q to stop): ').lower().strip()

            # If q, stop
            if user_name == 'q':
                break

            # Match user name to power
            player = self.game_state.get_player(user_name)
            if player is None:
                print('Invalid Great Power; please try again')
                continue

            while True:
                # If the phase is a retreat phase, list the units this player has that still need to retreat
                if phase in [SPRING_RETREAT_PHASE, FALL_RETREAT_PHASE]:
                    dislodged = self.adjudicator.gather_dislodged()
                    for d in dislodged:
                        if d.owner == player and d.order is None:
                            unit_type = d.type
                            territory = d.dislodged_from
                            print(f'{unit_type} in {territory} has been dislodged and needs to retreat.')

                # If the phase is an adjustment phase, list the units this player still needs to build/disband
                if phase == ADJUSTMENT_PHASE:
                    units_to_build = player.units_to_build(self.game_state.territories)
                    if units_to_build > 0:
                        print(f'{player.name} has {units_to_build} units to build.')
                    elif units_to_build < 0:
                        print(f'{player.name} has {-units_to_build} units to disband.')
                    else:
                        print(f'{player.name} has no units to build/disband.')

                # Get the order
                order = input('Enter your order (q to stop, draw to propose a draw): ').strip()
                if order.lower() == 'q':
                    break

                # If the order is to propose a draw, add to draw list
                if order.lower() == 'draw':
                    if player.name in no_draw_list:
                        no_draw_list.remove(player.name)
                        draw_proposed = True
                        if not no_draw_list:
                            self.game_state.draw = True
                            return
                        break

                valid = self.order_parser.parse_order_string(order, player)
                if not valid:
                    print('Invalid Order; please try again')

        if len(no_draw_list) == 0 and draw_proposed:
            self.game_state.draw = True