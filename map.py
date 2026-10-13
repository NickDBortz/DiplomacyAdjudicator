from player import Player
from territory import LandTerritory, WaterTerritory
from unit import Unit
from orders import Order, HoldOrder, AdvanceOrder, SupportOrder, TransformOrder, ConvoyOrder, BuildOrder, DisbandOrder
from pathlib import Path
import json

class Map:
    def __init__(self, silent_mode=False, begin_empty=False, json_file='', load_rendering_data=True, allow_transformations=True):
        if load_rendering_data:
            import cv2
            import numpy as np
            self.cv2 = cv2
            self.np = np
        else:
            self.cv2 = None
            self.np = None

        self.silent_mode = silent_mode
        self.allow_transformations = allow_transformations

        self.players = []
        self.territories = []

        self.width = 0
        self.height = 0
        self.vertices = []

        self.load_map_json(json_file, load_rendering_data)

        if not begin_empty:
            for player in self.players:
                self.init_player_units(player)

        self.queued_orders = []

        self.resolution_phases = ['Spring', 'Spring Retreat', 'Fall', 'Fall Retreat', 'Adjustment']
        self.resolution_phase = 0
        self.year = 1800 # Set to what it should be

    def load_map_json(self, json_file, load_rendering_data):
        json_file_path = Path(json_file)
        if not json_file_path.is_file():
            json_file = 'classic_map.json'

        with open(json_file, 'r') as file:
            map_obj = json.load(file)

            # Load Players
            players = map_obj['players']
            for player_obj in players:
                player = Player(player_obj['name'], player_obj['color'])
                setattr(self, player_obj['var_name'], player)
                self.players.append(player)

            if load_rendering_data:
                self.vertices = map_obj['vertices']

                water_color = map_obj['water_color']
                self.width = map_obj['width']
                self.height = map_obj['height']
            else:
                water_color = []

            # Load Territories
            territories = map_obj['territories']
            for territory_obj in territories:
                name = territory_obj['name']
                abbr = territory_obj['abbr']
                is_supply_center = territory_obj['supply_center']
                owner_name = territory_obj['owner']
                owner = next((player for player in self.players if player.name == owner_name), None)

                if load_rendering_data:
                    polygons = territory_obj['polygons']
                    label_pos = territory_obj['label_pos']
                else:
                    polygons = []
                    label_pos = []

                if territory_obj['land']:
                    if load_rendering_data:
                        supply_center_pos = territory_obj['supply_center_pos']
                        army_pos = territory_obj['army_pos']
                        coast_pos = territory_obj['coast_pos']
                        south_coast_pos = territory_obj['south_coast_pos']
                    else:
                        supply_center_pos = []
                        army_pos = []
                        coast_pos = []
                        south_coast_pos = []
                    territory = LandTerritory(name, abbr, is_supply_center, owner, polygons, self.vertices, self.width, self.height, label_pos, supply_center_pos, army_pos, coast_pos, south_coast_pos, self.np, self.cv2)
                else:
                    if load_rendering_data:
                        fleet_pos = territory_obj['fleet_pos']
                    else:
                        fleet_pos = []
                    territory = WaterTerritory(name, abbr, owner, water_color, polygons, self.vertices, self.width, self.height, label_pos, fleet_pos, self.np, self.cv2)

                setattr(self, territory_obj['var_name'], territory)
                self.territories.append(territory)

            # Set Adjacents
            for territory_obj in territories:
                territory = next((t for t in self.territories if t.name == territory_obj['name']), None)

                for nth_adj_name in territory_obj['north_coast']:
                    nth_adj = next((t for t in self.territories if t.name == nth_adj_name), None)
                    territory.set_adjacent(nth_adj, 0)

                for sth_adj_name in territory_obj['south_coast']:
                    sth_adj = next((t for t in self.territories if t.name == sth_adj_name), None)
                    territory.set_adjacent(sth_adj, 1)

                for adj_name in territory_obj['adjacents']:
                    adj = next((t for t in self.territories if t.name == adj_name), None)
                    territory.set_adjacent(adj)

    def render(self):
        # Create canvas
        canvas = self.np.zeros((self.height, self.width, 3), dtype=self.np.uint8)

        # Render the territories and their borders and decorations
        for territory in self.territories:
            territory.render(canvas)
        for territory in self.territories:
            territory.render_borders(canvas)

        # Render the units on the territories
        for territory in self.territories:
            if isinstance(territory, LandTerritory):
                territory.render_supply_center(canvas)
            territory.render_unit(canvas)

        # Render the orders
        self.render_orders(canvas)

        # Render the text on the territories
        for territory in self.territories:
            territory.render_text(canvas)

        # Display the canvas
        self.cv2.imshow("Diplomacy", canvas)
        self.cv2.waitKey(0)
        self.cv2.destroyAllWindows()

    def render_orders(self, canvas):
        # Render advances first
        for order in self.queued_orders:
            if order.name == 'Advance':
                # Render a red arrow in the direction of the advance
                self.cv2.arrowedLine(
                    canvas,
                    order.get_start_pos(),
                    order.get_dest_pos(),
                    (0, 0, 255),
                    3,
                    self.cv2.LINE_AA
                )

        # Then render all other orders
        for order in self.queued_orders:
            if order.name == 'Support':
                # If we find a match, continue
                found_match = False
                for other in self.queued_orders:
                    if other.match(order.supported_order):
                        found_match = True
                        break
                if not found_match:
                    continue

                if order.supported_order.name == 'Advance':
                    adv_start = order.supported_order.get_start_pos()
                    adv_dest = order.supported_order.get_dest_pos()

                    dest_pos = [(adv_start[0] - adv_dest[0]) // 2 + adv_dest[0], (adv_start[1] - adv_dest[1]) // 2 + adv_dest[1]]
                else:
                    dest_pos = order.supported_order.get_start_pos()
                # Render a red arrow in the direction of the advance
                self.cv2.arrowedLine(
                    canvas,
                    order.get_start_pos(),
                    dest_pos,
                    (0, 255, 0),
                    3,
                    self.cv2.LINE_AA
                )

    def advance_phase(self):
        self.resolution_phase += 1
        if self.resolution_phase >= len(self.resolution_phases):
            self.resolution_phase = 0
            self.year += 1

        # Skip retreat phases if there are no dislodged units that need to retreat
        dislodged = self.gather_dislodged()
        if (self.get_phase() == 'Spring Retreat' or self.get_phase() == 'Fall Retreat') and len(dislodged) == 0:
            self.advance_phase()

    def get_phase(self):
        return self.resolution_phases[self.resolution_phase]

    def set_phase(self, phase):
        if phase not in self.resolution_phases:
            return
        self.resolution_phase = self.resolution_phases.index(phase)

    def init_player_units(self, player):
        for i in range(len(self.territories)):
            territory = self.territories[i]
            if territory.is_supply_center and territory.owner == player:
                unit_type = 'Army' if isinstance(territory, LandTerritory) else 'Fleet'
                unit = Unit(player, unit_type, territory)
                territory.set_unit(unit)
                player.add_unit(unit)

    def queue_order(self, order, owner=None):
        # Cannot queue an order from the wrong owner or that is blank
        if owner is not None and order.unit.owner != owner:
            if not self.silent_mode: print(f'{order.pretty_print()}: Cannot order a unit that is not your own!')
            return False
        if order is None:
            return False

        # If the order is not valid, reset it
        if not order.is_valid:
            order.unit.reset_order()
            if not self.silent_mode: print(f'{order.unit.pretty_print()} already has orders. Skipped {order.pretty_print()}')
            return False

        # If the phase is a retreat phase, only allow advance orders acting on dislodged units
        if self.get_phase() == 'Spring Retreat' or self.get_phase() == 'Fall Retreat':
            dislodged = self.gather_dislodged()
            if order.name != 'Advance' or order.is_utilizing_convoy or order.unit not in dislodged:
                return False

        # If the phase is not a build phase, disallow build and disband orders
        if self.get_phase() != 'Adjustment' and (order.name == 'Build' or order.name == 'Disband'):
            return False
        
        # If the phase is a build phase, disallow non-build and non-disband orders
        if self.get_phase() == 'Adjustment' and order.name != 'Build' and order.name != 'Disband':
            return False

        # If the order is a build order on a territory that is not initially owned by the owner, fail
        if self.get_phase() == 'Adjustment' and order.name == 'Build' and order.dest_territory.home_owner != owner:
            return False 
        
        self.queued_orders.append(order)
        # if not self.silent_mode: print(f'Orders set! {order.pretty_print()}')
        return True

    def resolve_retreat_orders(self):
        # Loop over all dislodged units
        all_dislodged = self.gather_dislodged()
        for dislodged in all_dislodged:
            dislodged.set_territory(None)

            # If the order is none, disband
            if dislodged.order is None:
                dislodged.disband()
                continue

            # If the order is retreating to an occupied territory, disband
            if dislodged.order.dest_territory.unit is not None:
                dislodged.disband()
                continue

            # If the order is retreating to a territory that was contested during the order phase, disband
            if len(dislodged.order.dest_territory.contesting) > 0:
                if len(dislodged.order.dest_territory.contesting) == 1 and dislodged.order.dest_territory.contesting[0].unit == dislodged:
                    pass
                else:
                    dislodged.disband()
                    continue

            # If the order is retreating to the territory it was attacked from and said order was not a convoy, disband
            found_attacker = False
            for contesting_order in dislodged.dislodged_from.contesting:
                if not contesting_order.is_utilizing_convoy and contesting_order.unit_territory == dislodged.order.dest_territory:
                    found_attacker = True
                    break
            if found_attacker:
                dislodged.disband()
                continue

            # If the order is retreating to a territory and is contested by another retreat, disband
            contested = False
            for other_dislodged in all_dislodged:
                if other_dislodged == dislodged:
                    continue

                # If other is advancing on a territory it was attacked from and contesting order was not a convoy, it doesn't actually contest
                found_attacker = False
                for contesting_order in other_dislodged.dislodged_from.contesting:
                    if other_dislodged.order is not None and not contesting_order.is_utilizing_convoy and contesting_order.unit_territory == other_dislodged.order.dest_territory:
                        found_attacker = True
                        break
                if found_attacker:
                    continue

                if other_dislodged.order is not None and other_dislodged.order.dest_territory == dislodged.order.dest_territory:
                    contested = True
                    break
            if contested:
                dislodged.disband()
                continue

            # Otherwise, retreat succeeds
            dislodged.dislodged = False
            dislodged.dislodge_to = None
            dislodged.set_territory(dislodged.order.dest_territory)
            dislodged.reset_order()

        # Clear the contesting of each territory
        for territory in self.territories:
            territory.clear_contesting()

    def resolve_adjustment_orders(self):
        # Loop through build orders
        for order in self.queued_orders:
            if isinstance(order, BuildOrder):
                build_order = order
                territory = build_order.dest_territory
                player = territory.owner
                units_to_build = player.units_to_build(self.territories)
                # Only build the unit if the player has enough supply centers, the territory is a supply center
                if units_to_build > 0 and territory.is_supply_center and territory.unit is None:
                    build_order.resolve()
            else:
                disband_order = order
                player = disband_order.unit.owner
                units_to_build = player.units_to_build(self.territories)
                # Only disband the unit if the player has not enough supply centers
                if units_to_build < 0:
                    disband_order.resolve()

        # After we're done, check and see if any players have too many troops
        for player in self.players:
            units_to_build = player.units_to_build(self.territories)
            if units_to_build < 0:
                # Find the furthest unit from a home supply center and disband it
                furthest_unit = player.get_furthest_unit(self.territories)
                furthest_unit.territory.set_unit(None)
                furthest_unit.territory = None
                furthest_unit.owner.remove_unit(furthest_unit)

    def resolve_orders(self):
        # If this is the retreat phase, resolve retreat orders
        phase = self.get_phase()
        if phase == 'Spring Retreat' or phase == 'Fall Retreat':
            self.resolve_retreat_orders()
        elif phase == 'Spring' or phase == 'Fall':
            self.resolve_general_orders()
        elif phase == 'Adjustment':
            self.resolve_adjustment_orders()

        # Clear orders
        self.queued_orders.clear()

        self.advance_phase()

    def resolve_general_orders(self):
        # Build the order graph, so each territory knows who occupies and who contests it
        # Each unit knows who supports it
        self.build_order_graph()

        # Go through and cut supports as necessary
        self.cut_supports()

        # Filter to only the territories that need to be resolved
        # These either have a unit or have contestants
        # All other territories don't need to be touched
        territories_to_resolve = [territory for territory in self.territories if territory.needs_resolved()]

        # Order so we handle territories that have unmoving units first
        order_mapping = {
            'Support': 1,
            'Hold': 1,
            'Transform': 1,
            'Advance': 2,
            'Convoy': 1,
        }
        territories_to_resolve.sort(key=lambda territory: order_mapping[territory.unit.order.name] if territory.unit is not None else 0)

        # Resolve all remaining territories
        for territory in territories_to_resolve:
            territory.resolve()

        # Collapse units
        for player in self.players:
            for unit in player.units:
                unit.handle_collapse()
                unit.reset_order()

    def gather_dislodged(self):
        dislodged = []
        for player in self.players:
            for unit in player.units:
                if unit.dislodged:
                    dislodged.append(unit)
        return dislodged

    def build_order_graph(self):
        # Ensure all units with no order are ordered to hold
        empty_territories = [territory for territory in self.territories if territory.unit is not None and territory.unit.order is None]
        for territory in empty_territories:
            order = HoldOrder(territory.unit)
            territory.unit.set_order(order)
            self.queued_orders.append(order)

        # Match supports to the valid orders. For supports that don't match, remove and set to hold, as they are invalid
        support_orders = [order for order in self.queued_orders if order.name == 'Support']
        for order in support_orders:
            # Match supporting order
            supported_order = order.supported_order
            matching_orders = [o for o in self.queued_orders if o.match(supported_order)]
            matching_order = matching_orders[0] if len(matching_orders) > 0 else None
            if matching_order is not None:
                order.supported_order = matching_order
            else:
                # If there is an order with a matching unit that is not an advance and the supported order expects a hold, support it
                matching_orders = [o for o in self.queued_orders if o.unit == supported_order.unit and o.name != 'Advance']
                matching_order = matching_orders[0] if len(matching_orders) > 0 else None
                if matching_order is not None and supported_order.name == 'Hold':
                    order.supported_order = matching_order

            if order.supported_order == supported_order:
                self.queued_orders.remove(order)
                o = HoldOrder(order.unit)
                for supporter in order.supporters:
                    o.support(supporter)
                    supporter.supported_order = o
                order.unit.set_order(o)
                self.queued_orders.append(o)

        # Loop over all orders and activate them
        for order in self.queued_orders:
            order.activate()

    def cut_supports(self):
        # For each support, check if it's territory is contested
        # If attacked
        # and attack is from a territory other than the target territory
        # and attacker is not from same country as supporter
        # and supporting unit is not immune due to a special convoy/head-to-head exception
        support_orders = [order for order in self.queued_orders if order.name == 'Support']
        for order in support_orders:
            territory = order.unit.territory
            friendly_country = territory.unit.owner
            dest_territory = order.supported_order.dest_territory if order.supported_order.name == 'Advance' else None 
            if territory.has_contesting(friendly_country, dest_territory):
                # Support is cut
                order.supported_order.cut_support(order)

            # If the supported order is advancing on a friendly, cut support, assuming friendly stays put
            if dest_territory is not None and dest_territory.unit is not None and dest_territory.unit.owner == friendly_country and dest_territory.unit.order.name != 'Advance':
                order.supported_order.cut_support(order)

    def parse_order_string(self, order_string, owner=None):
        order = self._parse_order_string(order_string)
        if order is not None:
            if self.queue_order(order, owner):
                order.unit.set_order(order)

    def _parse_order_string(self, order_string):
        # Helper functions
        def expect_unit_type(split_order_string, idx):
            if idx < 0 or idx >= len(split_order_string):
                raise Exception()
            unit_type = split_order_string[idx]
            if unit_type not in ['A', 'F', 'Build', 'Remove']:
                raise Exception()
            return 'Army' if unit_type == 'A' else 'Fleet' if unit_type == 'F' else unit_type

        def expect_territory_abbr(split_order_string, idx, allow_coast=False):
            if idx < 0 or idx >= len(split_order_string):
                raise Exception()
            territory_abbr = split_order_string[idx]
            coast = None
            if allow_coast:
                split_terr_coast = territory_abbr.split('(')
                if len(split_terr_coast) > 1:
                    territory_abbr = split_terr_coast[0]
                    coast = split_terr_coast[1].split(')')[0]
                    if coast not in ('nc', 'sc'):
                        raise Exception()
            for terr in self.territories:
                if terr.abbr == territory_abbr:
                    return terr, coast
            raise Exception()

        def expect_order_type(split_order_string, idx):
            if idx < 0 or idx >= len(split_order_string):
                raise Exception()
            order_type = split_order_string[idx]
            if order_type not in ['H', '-', 'S', 'T', 'T(nc)', 'T(sc)', 'C', 'B']:
                raise Exception()
            return order_type

        try:
            # Split the string into parts
            split_order_string = order_string.strip().split(' ')
            idx = 0
            # Expect Unit type
            unit_type = expect_unit_type(split_order_string, idx)
            idx += 1

            if unit_type == 'Build':
                unit_type = expect_unit_type(split_order_string, idx)
                idx += 1
                territory, coast = expect_territory_abbr(split_order_string, idx, allow_coast=True)
                idx += 1
                unit = Unit(territory.owner, unit_type, territory)
                return BuildOrder(unit, territory, coast)

            if unit_type == 'Remove':
                unit_type = expect_unit_type(split_order_string, idx)
                idx += 1
                territory, _ = expect_territory_abbr(split_order_string, idx)
                idx += 1
                unit = territory.unit
                if unit is None or (unit.type != unit_type and not territory.is_coast):
                    raise Exception()
                return DisbandOrder(unit)

            # Expect Territory abbreviation
            territory, _ = expect_territory_abbr(split_order_string, idx)
            idx += 1
            # Expect Order type
            order_type = expect_order_type(split_order_string, idx)
            idx += 1

            # Get troop from territory
            if self.get_phase() == 'Spring Retreat' or self.get_phase() == 'Fall Retreat':
                unit = None
                for dislodged in self.gather_dislodged():
                    if dislodged.dislodged_from == territory:
                        unit = dislodged
                        break
            else:
                unit = territory.unit
            if unit is None or (unit.type != unit_type and not territory.is_coast):
                raise Exception()

            if order_type == 'H':
                return HoldOrder(unit)
            elif order_type == '-':
                dest_territory, coast = expect_territory_abbr(split_order_string, idx, allow_coast=True)
                idx += 1
                is_via_convoy = False
                if len(split_order_string) > idx+1:
                    is_via_convoy = split_order_string[idx].strip().lower() == 'via' and split_order_string[idx+1].strip().lower() == 'convoy'
                return AdvanceOrder(unit, dest_territory, coast, is_via_convoy)
            elif order_type == 'S':
                supported_order_string = ' '.join(split_order_string[idx:])
                supported_order = self._parse_order_string(supported_order_string)
                if not isinstance(supported_order, Order):
                    raise Exception()
                return SupportOrder(unit, supported_order)
            elif order_type.startswith('T') and self.allow_transformations: # This is a house rule and isn't always allowed
                split_terr_coast = order_type.split('(')
                coast = None
                if len(split_terr_coast) > 1:
                    coast = split_terr_coast[1].split(')')[0]
                    if coast not in ('nc', 'sc'):
                        raise Exception()
                return TransformOrder(unit, coast)
            elif order_type == 'C':
                if unit_type != 'Fleet':
                    raise Exception()
                advance_order_string = ' '.join(split_order_string[idx:])
                advance_order = self._parse_order_string(advance_order_string)
                if not isinstance(advance_order, AdvanceOrder):
                    raise Exception()
                return ConvoyOrder(unit, advance_order.unit, advance_order.dest_territory)
            else:
                raise Exception()
        except Exception:
            return None