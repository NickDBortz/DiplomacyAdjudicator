from game.enums import ARMY, ADJUSTMENT_PHASE, SPRING_PHASE, SPRING_RETREAT_PHASE, FALL_PHASE, FALL_RETREAT_PHASE
from game.territory import LandTerritory

class OrderGenerator:
    def __init__(self, game_state, adjudicator):
        self.game_state = game_state
        self.adjudicator = adjudicator

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

        if power is not None:
            units_to_build = power.units_to_build(self.game_state.territory_list)
            if units_to_build > 0:
                for supply_center in power.get_supply_centers(self.game_state.territory_list):
                    territory = self.game_state.get_territory(supply_center)
                    if territory.unit is None:
                        if territory.is_coast:
                            if len(territory.north_coast) > 0:
                                valid_orders.append(f'Build F {territory.abbr}(nc)')
                                valid_orders.append(f'Build F {territory.abbr}(sc)')
                        valid_orders.append(f'Build A {territory.abbr}')
            elif units_to_build < 0:
                for unit in power.units:
                    unit_type_text = 'A' if unit.type == ARMY else 'F'
                    unit_territory_abbr = unit.territory.abbr
                    valid_orders.append(f'Remove {unit_type_text} {unit_territory_abbr}')

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
            # Get the player units
            units = power.units

        for unit in units:
            # Get unit type
            unit_type = unit.type
            type_text = 'A' if unit_type == ARMY else 'F'

            # Get the unit territory
            start_territory = unit.territory
            start_territory_abbr = start_territory.abbr

            # Add hold order
            valid_orders.append(f'{type_text} {start_territory_abbr} H')

            # Add transform order (requires coast territory)
            if isinstance(start_territory, LandTerritory) and start_territory.is_coast:
                if unit_type == ARMY and len(start_territory.north_coast) > 0:
                    valid_orders.append(f'{type_text} {start_territory_abbr} T(nc)')
                    valid_orders.append(f'{type_text} {start_territory_abbr} T(sc)')
                else:
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
                        # Skip support of self
                        if supported_unit == unit:
                            continue

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

        dislodged = self.adjudicator.gather_dislodged(power)

        for unit in dislodged:
            unit_type = unit.type
            unit_type_text = 'A' if unit_type == ARMY else 'F'

            start_territory = unit.dislodged_from
            start_territory_abbr = start_territory.abbr

            for dest_territory in start_territory.adjacents:
                # TODO: Handle multiple coasts
                if unit.can_traverse(dest_territory):
                    if dest_territory.unit is None:
                        if len(dest_territory.contesting) == 0 or len(dest_territory.contesting) == 1 and dest_territory.contesting[0].unit == unit:
                            dest_territory_abbr = dest_territory.abbr
                            valid_orders.append(f'{unit_type_text} {start_territory_abbr} - {dest_territory_abbr}')

        return valid_orders