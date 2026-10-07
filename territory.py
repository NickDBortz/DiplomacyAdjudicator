class Territory:
    def __init__(self, name, abbr, is_supply_center, owner):
        self.name = name
        self.abbr = abbr
        self.is_supply_center = is_supply_center
        self.unit = None
        self.owner = owner
        self.home_owner = owner

        self.unit_coast = None
        self.north_coast = []
        self.south_coast = []

        self.temp_coast = None
        self.temp_unit = None

        self.adjacents = []
        self.contesting = []

    def set_unit(self, unit, coast=None):
        self.unit_coast = coast
        self.unit = unit
        self.temp_coast = coast
        self.temp_unit = unit

    def set_temp_unit(self, unit, coast=None):
        self.temp_coast = coast
        self.temp_unit = unit

    def set_adjacent(self, territory):
        if territory in self.adjacents:
            return
        self.adjacents.append(territory)
        territory.set_adjacent(self)

    def add_contestant(self, order):
        self.contesting.append(order)

    def clear_contesting(self):
        self.contesting.clear()

    def has_contesting(self, friendly_country, dest_territory):
        # Loop over all contestants of this territory
        for contestant in self.contesting:
            # Friendly units cannot cut support
            # Skip over convoy contestants, as they need to be resolved separately
            if contestant.unit.owner != friendly_country and not contestant.unit.order.is_utilizing_convoy:
                # Nullify any power from friendly supports on unfriendly advance
                for supporter in contestant.unit.order.supporters:
                    if supporter.unit.owner == friendly_country:
                        contestant.unit.order.cut_support(supporter)
                # If that contestant still beats the holding unit's hold, territory is successfully contested
                if contestant.unit.order.power > self.unit.order.power:
                    return True
                # Ignore contestant if part of a head-to-head
                return contestant.unit.territory != dest_territory
        # Otherwise, no valid contestants found
        return False

    def needs_resolved(self):
        if len(self.contesting) > 0 or self.unit is not None:
            return True
        return False

    def resolve(self):
        # Winner is the contestant that has the most power
        winner = self.winner()
        if winner is not None and winner.unit != self.unit:
            if self.unit is not None: self.unit.dislodge()
            winner.unit.collapse(self)
            self.owner = winner.unit.owner

    def winner(self):
        current_unit_advancing = self.unit is not None and self.unit.order.name == 'Advance'
        current_unit_leaves = not self.is_blocked(self.unit.order, []) if current_unit_advancing else False

        # Disallow the advance if head-to-head with another advancing order and neither is a convoy
        if current_unit_leaves and current_unit_advancing and self.unit.order.dest_territory.unit is not None and not self.unit.order.is_utilizing_convoy:
            competing_unit = self.unit.order.dest_territory.unit
            if competing_unit.order is not None and competing_unit.order.name == 'Advance' and competing_unit.order.dest_territory == self and not competing_unit.order.is_utilizing_convoy:
                self.fix_order_power(self.unit.order, competing_unit.owner)
                self.fix_order_power(competing_unit.order, self.unit.owner)
                current_unit_leaves = self.unit.order.passive_power > competing_unit.order.passive_power

        if len(self.contesting) == 0:
            if current_unit_leaves: return None
            else: return None if self.unit is None else self.unit.order

        if current_unit_advancing:
            if current_unit_leaves:
                max_score = -1
                winner = None
            else:
                # Current unit fails to advance and reverts to a hold
                max_score = 0
                winner = self.unit.order
        else:
            max_score = -1 if self.unit is None else self.unit.order.power
            winner = None if self.unit is None else self.unit.order

        head_to_head = None
        for contestant in self.contesting:
            pandins_paradox = False
            if contestant.name == 'Advance':
                # If the contestant is an advance order and the territory it is advancing on has a support order supporting an advance onto the advancing contestant, nullify that contestant
                if contestant.power == 0:
                    if contestant.dest_territory.unit is not None and contestant.dest_territory.unit.order is not None and contestant.dest_territory.unit.order.name == 'Support':
                        if contestant.dest_territory.unit.order.supported_order is not None and contestant.dest_territory.unit.order.supported_order.name == 'Advance' and contestant.dest_territory.unit.order.supported_order.dest_territory == contestant.unit.territory:
                            continue

                # If the contestant is an advance order and convoying
                if contestant.is_utilizing_convoy:
                    # If the convoy does not succeed, ignore it
                    if not self.check_convoy_from(contestant.unit, contestant.unit.territory, self):
                        continue
                    # If the convoy does succeed and the current territory's unit is a support, cut that support
                    elif self.unit is not None and self.unit.order.name == 'Support':
                        # If the supported order is advancing on a part of said convoy, don't cut support
                        supported_order = self.unit.order.supported_order
                        dest = supported_order.dest_territory if supported_order.name == 'Advance' or supported_order.name == 'Convoy' else None
                        # Pandin's Paradox
                        if supported_order.name == 'Advance' and dest.unit is not None and dest.unit.order.name == 'Convoy' and dest.unit.order.convoying_unit.order == contestant:
                            # The paradox condition has been met. If the convoyed unit would normally cut this support, it fails to.
                            # I prefer the official rulebook for this one, so it stays the same for now
                            # The Simon Szykman rules are that the convoy would fail, not dislodging or cutting this support. This is subject to change

                            # If we cut this support and the convoy still succeeds, this support remains cut
                            supported_order.cut_support(self.unit.order)
                            if not self.check_convoy_from(contestant.unit, contestant.unit.territory, self):
                                # Otherwise, the convoy failed without this support, so the support remains
                                supported_order.support(self.unit.order)

                            pandins_paradox = True
                        elif supported_order.name == 'Advance' and dest.unit is not None and dest.unit.order.name == 'Convoy' and dest.unit.order.dest_territory.unit is not None and dest.unit.order.dest_territory.unit.order.name == 'Support' and dest.unit.order.dest_territory.unit.order.supported_order.name == 'Convoy' and dest.unit.order.dest_territory.unit.order.supported_order.dest_territory == self:
                            # This is a case of a second-order paradox with no resolution. Convoy fails and support stays
                            continue
                        elif supported_order.name == 'Convoy' and dest == self:
                            # The paradox condition has been met. If the convoyed unit would normally cut this support, it fails to.
                            # The convoy also fails

                            # If we cut this support and the convoy still succeeds, this support remains cut
                            supported_order.cut_support(self.unit.order)
                            if not self.check_convoy_from(contestant.unit, contestant.unit.territory, self):
                                # Otherwise, the convoy failed without this support, so the support remains
                                supported_order.support(self.unit.order)

                            continue
                        elif supported_order.name == 'Convoy' and dest.unit is not None and dest.unit.order.name == 'Support' and dest.unit.order.supported_order.name == 'Convoy' and dest.unit.order.supported_order.dest_territory == self:
                            # This is a case of a second-order paradox with exclusive convoys. Convoy fails and support stays
                            continue
                        else:
                            supported_order.cut_support(self.unit.order)

                # Check for head-to-head direct advance
                if self.unit is not None and self.unit.order.name == 'Advance' and not self.unit.order.is_utilizing_convoy and not contestant.is_utilizing_convoy and self.unit.order.dest_territory == contestant.unit.territory:
                    # Dislodged unit has no effect on the area from which the attacker came
                    # So, if the contestant is dislodged, and the dislodger is this advance, it no longer succeeds
                    # Check for head-to-head
                    self.fix_order_power(contestant, self.unit.owner)
                    self.fix_order_power(self.unit.order, contestant.unit.owner)
                    if contestant.passive_power < self.unit.order.passive_power:
                        # Check if the contestant gets dislodged
                        # If it is dislodged and the dislodger is the current unit, it loses it's affect. Otherwise, it affects but cannot win
                        dislodger = None
                        max_power = 0
                        for contestant2 in contestant.unit.territory.contesting:
                            self.fix_order_power(contestant2, contestant.unit.owner)
                            if contestant2.power > max_power:
                                if contestant2.passive_power > max_power:
                                    dislodger = contestant2
                                max_power = contestant2.power
                            elif contestant2.power == max_power:
                                dislodger = None
                        if dislodger is not None and dislodger == self.unit.order:
                            continue
                        head_to_head = contestant
                    elif contestant.passive_power == self.unit.order.passive_power:
                        head_to_head = contestant

            # Remove friendly supports from advance, assuming this unit holds
            if current_unit_advancing and not current_unit_leaves or not current_unit_advancing and self.unit is not None:
                friendly_country = self.unit.owner
                self.fix_order_power(contestant, friendly_country)

            power = contestant.power

            if power > max_score:
                if contestant.passive_power > max_score:
                    winner = contestant
                else:
                    winner = None if self.unit is None else self.unit.order
                max_score = power
            elif power == max_score:
                winner = None if self.unit is None else self.unit.order
        # If the winner is a friendly unit and the current unit is not moving, current unit wins, as self-dislodgement is prohibited
        winner_owner = winner.unit.owner if winner is not None else None
        current_owner = self.unit.owner if self.unit is not None else None
        if self.unit is not None and not current_unit_leaves and winner_owner == current_owner:
            winner = self.unit.order
        elif winner == head_to_head:
            winner = self.unit.order if self.unit is not None and not current_unit_leaves else None
        elif self.unit is not None and winner == self.unit.order and current_unit_leaves:
            winner = None
        return winner

    def check_convoy_from(self, unit, start_territory, dest_territory, exclude=[], force_owner=None):
        # Starting at start territory
        # Check all possible convoy routes of non-dislodged fleets convoying target unit to the destination
        # If all routes are blocked, return False
        visited = []
        to_check = [adj for adj in start_territory.adjacents if isinstance(adj, WaterTerritory) and adj not in exclude]
        while len(to_check) > 0:
            current_territory = to_check.pop()
            visited.append(current_territory)

            # Valid convoy territory must be a water territory with a fleet on it
            if current_territory.unit is not None and current_territory.unit.type == 'Fleet':
                # Valid convoy unit must be convoying the unit to the destination
                order = current_territory.unit.order
                if order.name == 'Convoy' and order.convoying_unit == unit and order.dest_territory == dest_territory:
                    if force_owner is not None and order.unit.owner != force_owner:
                        continue
                    # Valid convoy unit must not be dislodged
                    hold_power = order.power
                    victor = self.get_victor(order.unit.territory)
                    if victor is not None and victor.power > hold_power:
                        continue # This doesn't automatically disrupt the convoy. Continue checking for alternate routes
                    # This territory succeeds, so add it's adjacents to be checked
                    for adj in current_territory.adjacents:
                        if adj == dest_territory:
                            return True
                        if adj not in visited and adj not in exclude and isinstance(adj, WaterTerritory):
                            to_check.append(adj)
        # Failed to find a valid convoy route
        return False

    def is_blocked(self, current_order, visited=[]):
        # Start with a given advance order
        start_territory = current_order.unit.territory
        # If start territory in visited, we've looped and not been blocked
        if start_territory in visited:
            return False # Unblocked, made a full loop
        visited.append(start_territory)

        dest_territory = current_order.dest_territory
        dest_unit = dest_territory.unit
        dest_unit_order = dest_unit.order if dest_unit is not None else None

        # If advancing with a convoy and the convoy is broken, blocked
        if current_order.is_utilizing_convoy:
            if not self.check_convoy_from(current_order.unit, start_territory, dest_territory):
                return True # Blocked: Convoy broken

        # If territory has a unit and unit is not advancing, fix current advance support and if it loses, return true
        if dest_unit is not None and dest_unit_order.name != 'Advance':
            # Fix current order support
            self.fix_order_power(current_order, dest_unit.owner)
            if current_order.passive_power <= dest_unit_order.power:
                return True # Blocked: Failed to dislodge a hold
            # If dislodged opponent, unblock
            dislodger = self.get_victor(dest_territory)
            if dislodger == current_order:
                return False # Unblocked: Dislodged opponent
            else:
                return True # Blocked: Someone else dislodged opponent

        # If territory has a unit and unit is advancing on current unit
        if dest_unit is not None and dest_unit_order.name == 'Advance' and dest_unit_order.dest_territory == start_territory:
            # Fix order supports if neither is a convoy
            # If either is a convoy, they go around and it's not an issue
            if not current_order.is_utilizing_convoy and not dest_unit_order.is_utilizing_convoy:
                self.fix_order_power(current_order, dest_unit.owner)
                self.fix_order_power(dest_unit_order, current_order.unit.owner)
                # If lost head-to-head, blocked
                if current_order.passive_power <= dest_unit_order.passive_power:
                    return True # Blocked: Head-to-Head lost

            # If dislodged opponent or swapped places, unblocked
            dislodger = self.get_victor(dest_territory)
            if dislodger == current_order:
                return False # Unblocked: Head-to-Head won
            else:
                return True # Blocked: Head-to-Head won, but someone else got the dislodge

        # If territory has no unit and the only contestant is the current order, unblocked
        if dest_unit is None and len(dest_territory.contesting) == 1 and dest_territory.contesting[0] == current_order:
            return False # Unblocked: No competition

        # If territory has a unit and unit is advancing, check if that unit is blocked
        if dest_unit is not None and dest_unit_order.name == 'Advance':
            # Check if there is a head-to-head
            if dest_unit_order.dest_territory.unit is not None and dest_unit_order.dest_territory.unit.order.name == 'Advance' and dest_unit_order.dest_territory.unit.order.dest_territory == dest_territory and not dest_unit_order.is_utilizing_convoy and not dest_unit_order.dest_territory.unit.order.is_utilizing_convoy:
                # Fix the powers
                self.fix_order_power(dest_unit_order, dest_unit_order.dest_territory.unit.owner)
                self.fix_order_power(dest_unit_order.dest_territory.unit.order, dest_unit.owner)
                # If second unit is not dislodged or the second unit is dislodged by another unit besides the first unit, blocked
                dislodger = self.get_victor(dest_unit_order.dest_territory)
                if dislodger is None or dislodger != dest_unit_order:
                    return True # Blocked: Did not move into head-to-head spot
            elif self.is_blocked(dest_unit_order, visited):
                return True # Blocked: Next unit in chain blocked

        # Check if this order beats all contestants
        victor = self.get_victor(dest_territory)
        if victor != current_order:
            return True # Blocked: Lost contest
        return False # Unblocked

    def get_victor(self, territory):
        max_power = -1
        dislodger = None
        for contestant in territory.contesting:
            # # Fix contestant power if the territory has a unit and that unit is not in a non-convoy head-to-head with the contestant
            # if territory.unit is not None:
            #     # If this is a head-to-head
            #     if territory.unit.order.name == 'Advance' and territory.unit.order.dest_territory == contestant.unit.territory:
            #         # If this is without convoys
            #         if not territory.unit.order.is_utilizing_convoy and not contestant.is_utilizing_convoy:
            #             self.fix_order_power(contestant, territory.unit.owner)
            #     else:
            #         self.fix_order_power(contestant, territory.unit.owner)
            # If contestant has greater power than current best power, it is the new winner
            # Still use primary power before fix to affect the position, but that power is not used to win
            if contestant.power > max_power:
                if contestant.passive_power > max_power:
                    dislodger = contestant
                else:
                    dislodger = None
                max_power = contestant.power
            elif contestant.power == max_power:
                dislodger = None
                max_power = contestant.power
        return dislodger

    def fix_order_power(self, order, friendly_country):
        for support in order.supporters:
            if support.unit.owner == friendly_country:
                order.nullify_support(support)

    def __str__(self):
        return f'{self.name}{f'*' if self.is_supply_center else ''}'

class LandTerritory(Territory):
    def __init__(self, name, abbr, is_supply_center, owner):
        super().__init__(name, abbr, is_supply_center, owner)
        self.is_coast = False

    def set_adjacent(self, territory, coast=-1):
        if isinstance(territory, WaterTerritory):
            self.is_coast = True

        if coast > -1:
            if coast == 0:
                self.north_coast.append(territory)
            elif coast == 1:
                self.south_coast.append(territory)

        if territory in self.adjacents:
            return

        self.adjacents.append(territory)
        territory.set_adjacent(self)

class WaterTerritory(Territory):
    def __init__(self, name, abbr, owner):
        super().__init__(name, abbr, False, owner)