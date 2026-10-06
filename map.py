from player import Player
from territory import LandTerritory, WaterTerritory
from unit import Unit
from orders import Order, HoldOrder, AdvanceOrder, SupportOrder, TransformOrder, ConvoyOrder, BuildOrder
from classic_map_setup import init_classic_map

class Map:
    def __init__(self, silent_mode=False, use_test_map=True, begin_empty=False):
        self.silent_mode = silent_mode
        if use_test_map:
            player1 = Player('Player 1')
            player2 = Player('Player 2')
            player3 = Player('Player 3')
            player4 = Player('Player 4')

            self.player1 = player1
            self.player2 = player2
            self.player3 = player3
            self.player4 = player4

            self.territories = []
            t1 = LandTerritory('Territory 1', 'T1', True, player1)
            t2 = LandTerritory('Territory 2', 'T2', False, player1)
            t3 = LandTerritory('Territory 3', 'T3', True, player2)
            t4 = LandTerritory('Territory 4', 'T4', False, player2)
            t5 = LandTerritory('Territory 5', 'T5', True, player3)
            t6 = LandTerritory('Territory 6', 'T6', True, player4)

            t7 = LandTerritory('Territory 7', 'T7', False, player4)
            t8 = WaterTerritory('Territory 8', 'T8', player4)
            t9 = WaterTerritory('Territory 9', 'T9', player1)
            t10 = LandTerritory('Territory 10', 'T10', False, player1)
            t11 = WaterTerritory('Territory 11', 'T11', player1)
            t12 = WaterTerritory('Territory 12', 'T12', player1)
            t13 = LandTerritory('Territory 13', 'T13', False, player1)

            t14 = WaterTerritory('Territory 14', 'T14', player2)
            t15 = LandTerritory('Territory 15', 'T15', True, player2)

            t16 = LandTerritory('Territory 16', 'T16', True, player3)
            t1.set_adjacent(t2)
            t1.set_adjacent(t3)
            t1.set_adjacent(t4)
            t2.set_adjacent(t3)
            t2.set_adjacent(t4)
            t3.set_adjacent(t4)

            t5.set_adjacent(t1)
            t5.set_adjacent(t3)
            t6.set_adjacent(t5)

            t7.set_adjacent(t6)
            t8.set_adjacent(t7)

            t9.set_adjacent(t1)
            t10.set_adjacent(t9)

            t11.set_adjacent(t9)
            t12.set_adjacent(t11)
            t13.set_adjacent(t12)

            t14.set_adjacent(t11)

            t15.set_adjacent(t12)
            t15.set_adjacent(t1)
            t15.set_adjacent(t5)

            t16.set_adjacent(t5)

            self.territories.append(t1)
            self.territories.append(t2)
            self.territories.append(t3)
            self.territories.append(t4)
            self.territories.append(t5)
            self.territories.append(t6)
            self.territories.append(t7)
            self.territories.append(t8)
            self.territories.append(t9)
            self.territories.append(t10)
            self.territories.append(t11)
            self.territories.append(t12)
            self.territories.append(t13)
            self.territories.append(t14)
            self.territories.append(t15)
            self.territories.append(t16)

            if not begin_empty:
                self.init_player_units(self.player1)
                self.init_player_units(self.player2)
                self.init_player_units(self.player3)
                self.init_player_units(self.player4)
        else:
            init_classic_map(self)

            if not begin_empty:
                for player in self.players:
                    self.init_player_units(player)

        self.queued_orders = []

        self.cycle = []
        self.guess_based = False
        self.recursion_hits = 0

        self.resolution_phases = ['Spring', 'Spring Retreat', 'Fall', 'Fall Retreat', 'Build']
        self.resolution_phase = 0
        self.year = 1800 # Set to what it should be

    def advance_phase(self):
        self.resolution_phase += 1
        if self.resolution_phase >= len(self.resolution_phases):
            self.resolution_phase = 0
            self.year += 1

    def get_phase(self):
        return self.resolution_phases[self.resolution_phase]

    def get_primary_territories(self, player):
        count = 0
        for i in range(len(self.territories)):
            territory = self.territories[i]
            if territory.is_supply_center and territory.owner == player:
                count += 1
        return count

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
        
        self.queued_orders.append(order)
        if not self.silent_mode: print(f'Orders set! {order.pretty_print()}')
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

            # If the order is retreating to a territory and is contested by another retreat, disband
            contested = False
            for other_dislodged in all_dislodged:
                if other_dislodged == dislodged:
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

    def resolve_orders(self):
        # If this is the retreat phase, resolve retreat orders
        phase = self.get_phase()
        if phase == 'Spring Retreat' or phase == 'Fall Retreat':
            self.resolve_retreat_orders()
        elif phase == 'Spring' or phase == 'Fall':
            self.resolve_general_orders()

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
            if unit_type not in ['A', 'F', 'Build']:
                raise Exception()
            return 'Army' if unit_type == 'A' else 'Fleet' if unit_type == 'F' else 'Build'

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
            if order_type not in ['H', '-', 'S', 'T', 'C', 'B']:
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
            elif order_type == 'T':
                return TransformOrder(unit)
            elif order_type == 'C':
                if unit_type != 'Fleet':
                    raise Exception()
                advance_order_string = ' '.join(split_order_string[idx:])
                advance_order = self._parse_order_string(advance_order_string)
                if not isinstance(advance_order, AdvanceOrder):
                    raise Exception()
                return ConvoyOrder(unit, advance_order.unit, advance_order.dest_territory)
        except Exception:
            return None