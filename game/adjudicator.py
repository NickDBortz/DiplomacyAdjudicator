from game.orders import HoldOrder, BuildOrder
from game.enums import HOLD, ADVANCE, SUPPORT, TRANSFORM, CONVOY, BUILD, DISBAND, ADJUSTMENT_PHASE, SPRING_PHASE, SPRING_RETREAT_PHASE, FALL_PHASE, FALL_RETREAT_PHASE

class Adjudicator:
    def __init__(self, game_state, supply_centers_to_win):
        self.game_state = game_state
        self.supply_centers_to_win = supply_centers_to_win

    def queue_order(self, order, owner=None):
        # Cannot queue an order from the wrong owner or that is blank
        if order is None:
            return False
        if owner is not None and order.unit.owner != owner:
            return False

        # If the order is not valid, reset it
        if not order.is_valid:
            return False

        # If the phase is a retreat phase, only allow advance orders acting on dislodged units
        phase = self.game_state.get_phase()
        if phase == SPRING_RETREAT_PHASE or phase == FALL_RETREAT_PHASE:
            dislodged = self.gather_dislodged()
            if order.type != ADVANCE or order.is_utilizing_convoy or order.unit not in dislodged:
                return False

        # If the phase is not a build phase, disallow build and disband orders
        if phase != ADJUSTMENT_PHASE and (order.type == BUILD or order.type == DISBAND):
            return False
        
        # If the phase is a build phase, disallow non-build and non-disband orders
        if phase == ADJUSTMENT_PHASE and order.type != BUILD and order.type != DISBAND:
            return False

        # If the order is a build order on a territory that is not initially owned by the owner, fail
        if phase == ADJUSTMENT_PHASE and order.type == BUILD and order.dest_territory.home_owner != owner:
            return False 
        
        self.game_state.queue_order(order)
        return True

    def resolve_orders(self):
        skip_retreat = False
        skip_adjustment = False
        # If this is the retreat phase, resolve retreat orders
        phase = self.game_state.get_phase()
        if phase == SPRING_PHASE or phase == FALL_PHASE:
            self._resolve_general_orders()

            dislodged = self.gather_dislodged()
            if len(dislodged) == 0:
                # Need to remove contesting, as they're only used for retreat phases
                for territory in self.game_state.territory_list:
                    territory.clear_contesting()
                skip_retreat = True

            if phase == FALL_PHASE:
                self._check_for_winner()
        elif phase == SPRING_RETREAT_PHASE or phase == FALL_RETREAT_PHASE:
            self._resolve_retreat_orders()
            if phase == FALL_RETREAT_PHASE:
                needs_adjustment = False
                for player in self.game_state.player_list:
                    units_to_build = player.units_to_build(self.game_state.territory_list)
                    if units_to_build != 0:
                        needs_adjustment = True
                skip_adjustment = not needs_adjustment
        elif phase == ADJUSTMENT_PHASE:
            self._resolve_adjustment_orders()

        # Clear orders
        self.game_state.clear_queued_orders()

        self.game_state.advance_phase(skip_retreat, skip_adjustment)

    def gather_dislodged(self):
        dislodged = []
        for player in self.game_state.player_list:
            for unit in player.units:
                if unit.dislodged:
                    dislodged.append(unit)
        return dislodged

    def _resolve_general_orders(self):
        # Build the order graph, so each territory knows who occupies and who contests it
        # Each unit knows who supports it
        self._build_order_graph()

        # Go through and cut supports as necessary
        self._cut_supports()

        # Filter to only the territories that need to be resolved
        # These either have a unit or have contestants
        # All other territories don't need to be touched
        territories_to_resolve = [territory for territory in self.game_state.territory_list if territory.needs_resolved()]

        # Order so we handle territories that have unmoving units first
        order_mapping = {
            SUPPORT: 1,
            HOLD: 1,
            TRANSFORM: 1,
            ADVANCE: 2,
            CONVOY: 1,
        }
        territories_to_resolve.sort(key=lambda territory: order_mapping[territory.unit.order.type] if territory.unit is not None else 0)

        # Resolve all remaining territories
        for territory in territories_to_resolve:
            territory.resolve()

        # Collapse units
        for player in self.game_state.player_list:
            for unit in player.units:
                unit.handle_collapse()
                unit.reset_order()

    def _resolve_retreat_orders(self):
        # Loop over all dislodged units
        all_dislodged = self.gather_dislodged()
        for dislodged in all_dislodged:
            dislodged.set_territory(None)

            # If the order is none, disband
            if dislodged.order is None:
                self.game_state.disband_unit(dislodged)
                continue

            # If the order is retreating to an occupied territory, disband
            if dislodged.order.dest_territory.unit is not None:
                self.game_state.disband_unit(dislodged)
                continue

            # If the order is retreating to a territory that was contested during the order phase, disband
            if len(dislodged.order.dest_territory.contesting) > 0:
                if len(dislodged.order.dest_territory.contesting) == 1 and dislodged.order.dest_territory.contesting[0].unit == dislodged:
                    pass
                else:
                    self.game_state.disband_unit(dislodged)
                    continue

            # If the order is retreating to the territory it was attacked from and said order was not a convoy, disband
            found_attacker = False
            for contesting_order in dislodged.dislodged_from.contesting:
                if not contesting_order.is_utilizing_convoy and contesting_order.unit_territory == dislodged.order.dest_territory:
                    found_attacker = True
                    break
            if found_attacker:
                self.game_state.disband_unit(dislodged)
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
                self.game_state.disband_unit(dislodged)
                continue

            # Otherwise, retreat succeeds
            self.game_state.retreat_unit(dislodged)

        # Clear the contesting of each territory
        for territory in self.game_state.territory_list:
            territory.clear_contesting()

    def _resolve_adjustment_orders(self):
        # Loop through build orders
        for order in self.game_state.get_orders():
            if isinstance(order, BuildOrder):
                build_order = order
                territory = build_order.dest_territory
                player = territory.owner
                units_to_build = player.units_to_build(self.game_state.territory_list)
                # Only build the unit if the player has enough supply centers, the territory is a supply center
                if units_to_build > 0 and territory.is_supply_center and territory.unit is None:
                    self.game_state.build_unit(build_order.unit, territory, build_order.coast)
            else:
                disband_order = order
                player = disband_order.unit.owner
                units_to_build = player.units_to_build(self.game_state.territory_list)
                # Only disband the unit if the player has not enough supply centers
                if units_to_build < 0:
                    self.game_state.disband_unit(disband_order.unit)

        # After we're done, check and see if any players have too many troops
        for player in self.game_state.player_list:
            units_to_build = player.units_to_build(self.game_state.territory_list)
            while units_to_build < 0:
                # Find the furthest unit from a home supply center and disband it
                furthest_unit = player.get_furthest_unit(self.game_state.territory_list)
                self.game_state.disband_unit(furthest_unit)
                units_to_build = player.units_to_build(self.game_state.territory_list)

            # Reset orders
            for unit in player.units:
                unit.reset_order()

    def _build_order_graph(self):
        # Ensure all units with no order are ordered to hold
        empty_territories = [territory for territory in self.game_state.territory_list if territory.unit is not None and territory.unit.order is None]
        for territory in empty_territories:
            order = HoldOrder(territory.unit)
            territory.unit.set_order(order)
            self.game_state.queue_order(order)

        # Match supports to the valid orders. For supports that don't match, remove and set to hold, as they are invalid
        support_orders = [order for order in self.game_state.get_orders() if order.type == SUPPORT]
        for order in support_orders:
            # Match supporting order
            supported_order = order.supported_order
            matching_orders = [o for o in self.game_state.get_orders() if o.match(supported_order)]
            matching_order = matching_orders[0] if len(matching_orders) > 0 else None
            if matching_order is not None:
                order.supported_order = matching_order
            else:
                # If there is an order with a matching unit that is not an advance and the supported order expects a hold, support it
                matching_orders = [o for o in self.game_state.get_orders() if o.unit == supported_order.unit and o.type != ADVANCE]
                matching_order = matching_orders[0] if len(matching_orders) > 0 else None
                if matching_order is not None and supported_order.type == HOLD:
                    order.supported_order = matching_order

            if order.supported_order == supported_order:
                self.game_state.remove_queued_order(order)
                o = HoldOrder(order.unit)
                for supporter in order.supporters:
                    o.support(supporter)
                    supporter.supported_order = o
                order.unit.set_order(o)
                self.game_state.queue_order(o)

        # Loop over all orders and activate them
        for order in self.game_state.get_orders():
            order.activate()

    def _cut_supports(self):
        # For each support, check if it's territory is contested
        # If attacked
        # and attack is from a territory other than the target territory
        # and attacker is not from same country as supporter
        # and supporting unit is not immune due to a special convoy/head-to-head exception
        support_orders = [order for order in self.game_state.get_orders() if order.type == SUPPORT]
        for order in support_orders:
            territory = order.unit.territory
            friendly_country = territory.unit.owner
            dest_territory = order.supported_order.dest_territory if order.supported_order.type == ADVANCE else None 
            if territory.has_contesting(friendly_country, dest_territory):
                # Support is cut
                order.supported_order.cut_support(order)

            # If the supported order is advancing on a friendly, cut support, assuming friendly stays put
            if dest_territory is not None and dest_territory.unit is not None and dest_territory.unit.owner == friendly_country and dest_territory.unit.order.type != ADVANCE:
                order.supported_order.cut_support(order)

    def _check_for_winner(self):
        for player in self.game_state.player_list:
            if player.get_supply_centers(self.game_state.territory_list) >= self.supply_centers_to_win:
                # This player wins
                self.game_state.set_winner(player)