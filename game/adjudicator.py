from game.orders import HoldOrder, BuildOrder

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
        if phase == 'Spring Retreat' or phase == 'Fall Retreat':
            dislodged = self.gather_dislodged()
            if order.name != 'Advance' or order.is_utilizing_convoy or order.unit not in dislodged:
                return False

        # If the phase is not a build phase, disallow build and disband orders
        if phase != 'Adjustment' and (order.name == 'Build' or order.name == 'Disband'):
            return False
        
        # If the phase is a build phase, disallow non-build and non-disband orders
        if phase == 'Adjustment' and order.name != 'Build' and order.name != 'Disband':
            return False

        # If the order is a build order on a territory that is not initially owned by the owner, fail
        if phase == 'Adjustment' and order.name == 'Build' and order.dest_territory.home_owner != owner:
            return False 
        
        self.game_state.queue_order(order)
        return True

    def resolve_orders(self):
        skip_retreat = False
        skip_adjustment = False
        # If this is the retreat phase, resolve retreat orders
        phase = self.game_state.get_phase()
        if phase == 'Spring' or phase == 'Fall':
            self._resolve_general_orders()

            dislodged = self.gather_dislodged()
            if len(dislodged) == 0:
                # Need to remove contesting, as they're only used for retreat phases
                for territory in self.game_state.territories:
                    territory.clear_contesting()
                skip_retreat = True
        elif phase == 'Spring Retreat' or phase == 'Fall Retreat':
            self._resolve_retreat_orders()
            if phase == 'Fall Retreat':
                self._check_for_winner()

                needs_adjustment = False
                for player in self.game_state.players:
                    units_to_build = player.units_to_build(self.game_state.territories)
                    if units_to_build != 0:
                        needs_adjustment = True
                skip_adjustment = not needs_adjustment
        elif phase == 'Adjustment':
            self._resolve_adjustment_orders()

        # Clear orders
        self.game_state.clear_queued_orders()

        self.game_state.advance_phase(skip_retreat, skip_adjustment)

    def gather_dislodged(self):
        dislodged = []
        for player in self.game_state.players:
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
        territories_to_resolve = [territory for territory in self.game_state.territories if territory.needs_resolved()]

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
        for player in self.game_state.players:
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
            destination = dislodged.order.dest_territory
            destination_owner = destination.owner
            dislodged.set_territory(destination)
            destination.set_unit(dislodged, coast=dislodged.order.coast)
            destination.owner = destination_owner
            dislodged.reset_order()

        # Clear the contesting of each territory
        for territory in self.game_state.territories:
            territory.clear_contesting()

    def _resolve_adjustment_orders(self):
        # Loop through build orders
        for order in self.game_state.get_orders():
            if isinstance(order, BuildOrder):
                build_order = order
                territory = build_order.dest_territory
                player = territory.owner
                units_to_build = player.units_to_build(self.game_state.territories)
                # Only build the unit if the player has enough supply centers, the territory is a supply center
                if units_to_build > 0 and territory.is_supply_center and territory.unit is None:
                    build_order.resolve()
            else:
                disband_order = order
                player = disband_order.unit.owner
                units_to_build = player.units_to_build(self.game_state.territories)
                # Only disband the unit if the player has not enough supply centers
                if units_to_build < 0:
                    disband_order.resolve()

        # After we're done, check and see if any players have too many troops
        for player in self.game_state.players:
            units_to_build = player.units_to_build(self.game_state.territories)
            while units_to_build < 0:
                # Find the furthest unit from a home supply center and disband it
                furthest_unit = player.get_furthest_unit(self.game_state.territories)
                furthest_unit.territory.set_unit(None)
                furthest_unit.territory = None
                furthest_unit.owner.remove_unit(furthest_unit)
                units_to_build = player.units_to_build(self.game_state.territories)

            # Reset orders
            for unit in player.units:
                unit.reset_order()

    def _build_order_graph(self):
        # Ensure all units with no order are ordered to hold
        empty_territories = [territory for territory in self.game_state.territories if territory.unit is not None and territory.unit.order is None]
        for territory in empty_territories:
            order = HoldOrder(territory.unit)
            territory.unit.set_order(order)
            self.game_state.queue_order(order)

        # Match supports to the valid orders. For supports that don't match, remove and set to hold, as they are invalid
        support_orders = [order for order in self.game_state.get_orders() if order.name == 'Support']
        for order in support_orders:
            # Match supporting order
            supported_order = order.supported_order
            matching_orders = [o for o in self.game_state.get_orders() if o.match(supported_order)]
            matching_order = matching_orders[0] if len(matching_orders) > 0 else None
            if matching_order is not None:
                order.supported_order = matching_order
            else:
                # If there is an order with a matching unit that is not an advance and the supported order expects a hold, support it
                matching_orders = [o for o in self.game_state.get_orders() if o.unit == supported_order.unit and o.name != 'Advance']
                matching_order = matching_orders[0] if len(matching_orders) > 0 else None
                if matching_order is not None and supported_order.name == 'Hold':
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
        support_orders = [order for order in self.game_state.get_orders() if order.name == 'Support']
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

    def _check_for_winner(self):
        for player in self.game_state.players:
            if player.get_supply_centers(self.game_state.territories) >= self.supply_centers_to_win:
                # This player wins
                self.game_state.set_winner(player)