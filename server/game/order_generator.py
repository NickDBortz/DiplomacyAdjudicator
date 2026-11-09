from game.enums import ARMY, ADJUSTMENT_PHASE, SPRING_PHASE, SPRING_RETREAT_PHASE, FALL_PHASE, FALL_RETREAT_PHASE
from game.territory import LandTerritory

class OrderGenerator:
    def __init__(self, game_state):
        self.game_state = game_state

    def generate_valid_orders(self, power=None):
        phase = self.game_state.get_phase()
        if phase == ADJUSTMENT_PHASE:
            return self._generate_valid_adjustment_orders(power)
        elif phase == SPRING_PHASE or phase == FALL_PHASE:
            return self._generate_valid_standard_orders(power)
        elif phase == SPRING_RETREAT_PHASE or phase == FALL_RETREAT_PHASE:
            return self._generate_valid_retreat_orders(power)
    
    def _generate_valid_adjustment_orders(self, power=None):
        valid_orders = []

        return valid_orders

    def _generate_valid_standard_orders(self, power=None):
        valid_orders = []

        # Calculate all advances keyed by target territory
        advances_to = {}
        advances_of_unit = {}
        hold_in = {}
        units = []
        for player in self.game_state.player_list:
            for unit in player.units:
                units.append(unit)
                start_territory = unit.territory

                # Fill out the dict for which territories have a holding unit
                hold_in[start_territory] = unit

                for dest_territory in start_territory.adjacents:
                    # Fill out the dict for which territories have advancing units
                    if dest_territory in advances_to:
                        advances_to[dest_territory].append(unit)
                    else:
                        advances_to[dest_territory] = [unit]

                    # Fill out the dict for which units are advancing
                    if unit in advances_of_unit:
                        advances_of_unit[unit].append(dest_territory)
                    else:
                        advances_of_unit[unit] = [dest_territory]

        if power is not None:
            # Get the player
            player = self.game_state.get_player(power)
            if player is None:
                return None
            
            # Get the player units
            units = player.units

        for unit in units:
            # Get unit type
            type_text = 'A' if unit.type == ARMY else 'F'

            # Get the unit territory
            start_territory = unit.territory
            start_territory_abbr = start_territory.abbr

            # Add hold order
            valid_orders.append(f'{type_text} {start_territory_abbr} H')

            # Add transform order (requires coast territory)
            if isinstance(start_territory, LandTerritory) and start_territory.is_coast:
                # TODO: If Army, handle multiple coasts to transform to
                valid_orders.append(f'{type_text} {start_territory_abbr} T')

            # Add advance order
            for dest_territory in advances_of_unit[unit]:
                # Skip advances to this territory
                if dest_territory == start_territory:
                    continue

                dest_territory_abbr = dest_territory.abbr
                # TODO: If Fleet, handle multiple coasts
                # TODO: If Army and valid convoy, handle via convoy variant
                valid_orders.append(f'{type_text} {start_territory_abbr} - {dest_territory_abbr}')

            # Add support order
            for dest_territory in advances_of_unit[unit]:
                # For holds
                if dest_territory in hold_in:
                    supported_unit = hold_in[dest_territory]
                    supported_unit_type_text = 'A' if supported_unit.type == ARMY else 'F'
                    dest_territory_abbr = dest_territory.abbr
                    valid_orders.append(f'{type_text} {start_territory_abbr} S {supported_unit_type_text} {dest_territory_abbr} H')

                # For advances
                if dest_territory in advances_to:
                    for supported_unit in advances_to[dest_territory]:
                        supported_unit_type_text = 'A' if supported_unit.type == ARMY else 'F'
                        supported_unit_start_territory = supported_unit.territory
                        supported_unit_start_territory_abbr = supported_unit_start_territory.abbr
                        dest_territory_abbr = dest_territory.abbr
                        # TODO: If supporting fleet, handle multiple coasts
                        valid_orders.append(f'{type_text} {start_territory_abbr} S {supported_unit_type_text} {supported_unit_start_territory_abbr} - {dest_territory_abbr}')

            # Add convoy order
        return valid_orders
    
    def _generate_valid_retreat_orders(self, power=None):
        valid_orders = []

        return valid_orders