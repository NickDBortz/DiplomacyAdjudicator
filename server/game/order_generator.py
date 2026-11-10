from game.enums import ARMY, FLEET, ADJUSTMENT_PHASE, SPRING_PHASE, SPRING_RETREAT_PHASE, FALL_PHASE, FALL_RETREAT_PHASE, NORTH_COAST, SOUTH_COAST
from game.territory import LandTerritory, WaterTerritory

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
                    if territory.unit is None and territory.home_owner == power:
                        if territory.is_coast:
                            if len(territory.north_coast) > 0:
                                valid_orders.append(f'Build F {territory.abbr}({NORTH_COAST})')
                                valid_orders.append(f'Build F {territory.abbr}({SOUTH_COAST})')
                            else:
                                valid_orders.append(f'Build F {territory.abbr}')
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
        supports_of_unit = {}
        hold_in = {}
        units = []
        for player in self.game_state.player_list:
            for unit in player.units:
                units.append(unit)
                start_territory = unit.territory

                # Fill out the dict for which territories have a holding unit
                hold_in[start_territory] = unit

                for dest_territory in start_territory.adjacents:
                    if not unit.can_traverse(dest_territory) and not unit.can_traverse(dest_territory, coast=NORTH_COAST) and not unit.can_traverse(dest_territory, coast=SOUTH_COAST):
                        if unit.can_traverse(dest_territory, for_support=True):
                            if unit in supports_of_unit:
                                supports_of_unit[unit].append(dest_territory)
                            else:
                                supports_of_unit[unit] = [dest_territory]
                        continue

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

                    if unit in supports_of_unit:
                        supports_of_unit[unit].append(dest_territory)
                    else:
                        supports_of_unit[unit] = [dest_territory]

                if unit.type == ARMY:
                    convoyable_territories = self._get_valid_convoy_territories_from(unit)
                    for dest_territory in convoyable_territories:
                        if dest_territory in advances_to:
                            if unit not in advances_to[dest_territory]:
                                advances_to[dest_territory].append(unit)
                        else:
                            advances_to[dest_territory] = [unit]

                        if unit in advances_of_unit:
                            if dest_territory not in advances_of_unit[unit]:
                                advances_of_unit[unit].append(dest_territory)
                        else:
                            advances_of_unit[unit] = [dest_territory]

                        if unit in supports_of_unit:
                            if dest_territory not in supports_of_unit[unit]:
                                supports_of_unit[unit].append(dest_territory)
                        else:
                            supports_of_unit[unit] = [dest_territory]

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
                if len(start_territory.north_coast) > 0:
                    valid_orders.append(f'{type_text} {start_territory_abbr} T({NORTH_COAST})')
                    valid_orders.append(f'{type_text} {start_territory_abbr} T({SOUTH_COAST})')
                else:
                    valid_orders.append(f'{type_text} {start_territory_abbr} T')

            # Add advance order
            for dest_territory in advances_of_unit.get(unit, []):
                # Skip advances to this territory
                if dest_territory == start_territory:
                    continue

                dest_territory_abbr = dest_territory.abbr
                if unit_type == FLEET:
                    if isinstance(dest_territory, LandTerritory) and len(dest_territory.north_coast) > 0:
                        if unit.can_traverse(dest_territory, coast=NORTH_COAST):
                            valid_orders.append(f'{type_text} {start_territory_abbr} - {dest_territory_abbr}({NORTH_COAST})')
                        if unit.can_traverse(dest_territory, coast=SOUTH_COAST):
                            valid_orders.append(f'{type_text} {start_territory_abbr} - {dest_territory_abbr}({SOUTH_COAST})')
                valid_orders.append(f'{type_text} {start_territory_abbr} - {dest_territory_abbr}')

            # Add convoy advance order
            if unit_type == ARMY:
                convoyable_territories = self._get_valid_convoy_territories_from(unit)
                for dest_territory in convoyable_territories:
                    dest_territory_abbr = dest_territory.abbr
                    if dest_territory in advances_of_unit.get(unit, []):
                        valid_orders.append(f'{type_text} {start_territory_abbr} - {dest_territory_abbr} via convoy')

            # Add support order
            for dest_territory in supports_of_unit.get(unit, []):
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

                        supported_unit_type = supported_unit.type
                        supported_unit_type_text = 'A' if supported_unit_type == ARMY else 'F'
                        supported_unit_start_territory = supported_unit.territory
                        supported_unit_start_territory_abbr = supported_unit_start_territory.abbr
                        dest_territory_abbr = dest_territory.abbr
                        if supported_unit_type == FLEET:
                            if isinstance(dest_territory, LandTerritory) and len(dest_territory.north_coast) > 0:
                                if unit.can_traverse(dest_territory, coast=NORTH_COAST, for_support=True):
                                    valid_orders.append(f'{type_text} {start_territory_abbr} S {supported_unit_type_text} {supported_unit_start_territory_abbr} - {dest_territory_abbr}({NORTH_COAST})')
                                if unit.can_traverse(dest_territory, coast=SOUTH_COAST, for_support=True):
                                    valid_orders.append(f'{type_text} {start_territory_abbr} S {supported_unit_type_text} {supported_unit_start_territory_abbr} - {dest_territory_abbr}({SOUTH_COAST})')
                        if unit.can_traverse(dest_territory, for_support=True):
                            valid_orders.append(f'{type_text} {start_territory_abbr} S {supported_unit_type_text} {supported_unit_start_territory_abbr} - {dest_territory_abbr}')

            # Add convoy order
            if unit_type == FLEET:
                convoy_pairs = self._get_valid_convoy_pairs(unit)
                for pair in convoy_pairs:
                    start_t, end_t = pair
                    convoying_unit = start_t.unit
                    convoying_unit_type_text = 'A' if convoying_unit.type == ARMY else 'F'
                    valid_orders.append(f'{type_text} {start_territory_abbr} C {convoying_unit_type_text} {start_t.abbr} - {end_t.abbr}')

        return valid_orders
    
    def _generate_valid_retreat_orders(self, power=None):
        valid_orders = []

        dislodged = self.adjudicator.gather_dislodged(power)

        for unit in dislodged:
            unit_type = unit.type
            unit_type_text = 'A' if unit_type == ARMY else 'F'

            start_territory = unit.dislodged_from
            start_territory_abbr = start_territory.abbr

            previous_territory = unit.territory
            try:
                unit.territory = start_territory
                for dest_territory in start_territory.adjacents:
                    if not (unit.can_traverse(dest_territory) or
                            unit.can_traverse(dest_territory, coast=NORTH_COAST) or
                            unit.can_traverse(dest_territory, coast=SOUTH_COAST)):
                        continue
                    if dest_territory.unit is not None:
                        continue
                    if dest_territory.contesting and not (
                        len(dest_territory.contesting) == 1 and dest_territory.contesting[0].unit == unit
                    ):
                        continue
                    dest_territory_abbr = dest_territory.abbr
                    if unit_type == FLEET and isinstance(dest_territory, LandTerritory) and dest_territory.north_coast:
                        if unit.can_traverse(dest_territory, coast=NORTH_COAST):
                            valid_orders.append(f'{unit_type_text} {start_territory_abbr} - {dest_territory_abbr}({NORTH_COAST})')
                        if unit.can_traverse(dest_territory, coast=SOUTH_COAST):
                            valid_orders.append(f'{unit_type_text} {start_territory_abbr} - {dest_territory_abbr}({SOUTH_COAST})')
                    if unit.can_traverse(dest_territory):
                        valid_orders.append(f'{unit_type_text} {start_territory_abbr} - {dest_territory_abbr}')
            finally:
                unit.territory = previous_territory

        return valid_orders

    def _get_valid_convoy_territories_from(self, unit):
        start_territory = unit.territory
        convoyable_territories = []
        fleet_territories = [adj for adj in start_territory.adjacents if isinstance(adj, WaterTerritory) and adj.unit is not None]
        visited = []

        while len(fleet_territories) > 0:
            t = fleet_territories.pop()
            visited.append(t)
            for adj in t.adjacents:
                if isinstance(adj, LandTerritory):
                    if adj not in convoyable_territories and adj != start_territory:
                        convoyable_territories.append(adj)
                else:
                    if adj not in visited:
                        if adj.unit is not None:
                            fleet_territories.append(adj)

        return convoyable_territories

    def _get_valid_convoy_pairs(self, unit):
        convoyable_territories = []
        fleet_territories = [unit.territory]
        visited = []

        while len(fleet_territories) > 0:
            t = fleet_territories.pop()
            visited.append(t)
            for adj in t.adjacents:
                if isinstance(adj, LandTerritory):
                    if adj not in convoyable_territories:
                        convoyable_territories.append(adj)
                else:
                    if adj not in visited:
                        if adj.unit is not None:
                            fleet_territories.append(adj)
        convoy_pairs = []
        for i in range(len(convoyable_territories)):
            start_t = convoyable_territories[i]
            if start_t.unit is not None and start_t.unit.type == ARMY:
                for j in range(len(convoyable_territories)):
                    if i == j:
                        continue

                    end_t = convoyable_territories[j]
                    convoy_pairs.append((start_t, end_t))
        return convoy_pairs