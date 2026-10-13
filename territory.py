class Territory:
    def __init__(self, name, abbr, is_supply_center, owner, polygons, vertices, width, height, label_pos, np, cv2):
        self.name = name
        self.abbr = abbr
        self.is_supply_center = is_supply_center
        self.unit = None
        self.owner = owner
        self.home_owner = owner

        self.polygons = polygons
        self.label_pos = label_pos

        self.np = np
        self.cv2 = cv2

        self.unit_coast = None
        self.north_coast = []
        self.south_coast = []

        self.temp_coast = None
        self.temp_unit = None

        self.adjacents = []
        self.contesting = []

        if len(vertices) > 0:
            self.smooth_polygons(vertices, width, height)

    def smooth_polygons(self, vertices, width, height):
        EDGE_EPSILON = 10
        def is_edge_point(p):
            x, y = p

            return (
                x <= EDGE_EPSILON or
                y <= EDGE_EPSILON or
                x >= width - EDGE_EPSILON or
                y >= height - EDGE_EPSILON
            )

        for i in range(len(self.polygons)):
            pts = self.np.asarray([vertices[vertex_index] for vertex_index in self.polygons[i]], dtype=float)

            for _ in range(2):
                new_pts = []
                n = len(pts)
                for j in range(n):
                    p0 = pts[j]
                    p1 = pts[(j+1) % n]

                    if is_edge_point(p0) or is_edge_point(p1):
                        new_pts.append(p0)
                        continue

                    q = 0.75 * p0 + 0.25 * p1
                    r = 0.25 * p0 + 0.75 * p1

                    new_pts.extend(([q, r]))

                pts = self.np.array(new_pts)

            pts = pts.astype(self.np.int32)

            self.polygons[i] = pts

    def render(self, canvas):
        for polygon in self.polygons:
            self.cv2.fillPoly(
                canvas,
                [polygon],
                self.get_color()
            )

    def render_borders(self, canvas):
        for polygon in self.polygons:
            self.cv2.polylines(
                canvas,
                [polygon],
                isClosed=True,
                color=(0, 0, 0),
                thickness=1
            )

    def render_text(self, canvas):
        # Render Abbreviation
        font = self.cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 2
        color = (255, 255, 255)

        outline_color = (0, 0, 0)

        line_type = self.cv2.LINE_AA

        text_size, _ = self.cv2.getTextSize(self.abbr, font, font_scale, thickness)
        text_w, text_h = text_size[0], text_size[1]

        text_x = self.label_pos[0] - (text_w // 2)
        text_y = self.label_pos[1] + (text_h // 2)

        for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
            self.cv2.putText(
                canvas, 
                self.abbr, 
                (text_x+dx, text_y+dy), 
                font, 
                font_scale, 
                outline_color, 
                thickness,
                line_type
            )

        self.cv2.putText(
            canvas, 
            self.abbr, 
            (text_x, text_y), 
            font, 
            font_scale, 
            color, 
            thickness,
            line_type
        )

    def render_unit(self, canvas):
        pass

    def render_army(self, canvas, pos):
        sq_size = 15
        pt1 = (pos[0] - (sq_size//2), pos[1] - (sq_size//2))
        pt2 = (pos[0] + (sq_size//2), pos[1] + (sq_size//2))

        b,r,g = self.get_color()
        b -= 30
        r -= 30
        g -= 30

        border_thickness = 2
        self.cv2.rectangle(
            canvas,
            (pt1[0]-border_thickness, pt1[1]-border_thickness),
            (pt2[0]+border_thickness, pt2[1]+border_thickness),
            (0,0,0),
            -1
        )

        self.cv2.rectangle(
            canvas,
            pt1,
            pt2,
            (b,r,g),
            -1
        )

    def render_fleet(self, canvas, pos):
        sq_size = 15
        pt1 = (pos[0] - (sq_size), pos[1] - (sq_size//2))
        pt2 = (pos[0] + (sq_size), pos[1] + (sq_size//2))

        b,r,g = self.get_color()
        b -= 30
        r -= 30
        g -= 30

        border_thickness = 2
        self.cv2.rectangle(
            canvas,
            (pt1[0]-border_thickness, pt1[1]-border_thickness),
            (pt2[0]+border_thickness, pt2[1]+border_thickness),
            (0,0,0),
            -1
        )

        self.cv2.rectangle(
            canvas,
            pt1,
            pt2,
            (b,r,g),
            -1
        )

    def get_color(self):
        color = self.owner.color if self.owner is not None else '#E2C69E'
        h = color.lstrip("#")
        
        # Parse R, G, B integers
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        
        # Return BGR scalar tuple (OpenCV format)
        return (b, g, r)

    def set_unit(self, unit, coast=None):
        self.unit_coast = coast
        self.unit = unit
        self.temp_coast = coast
        self.temp_unit = unit
        if unit is not None:
            self.owner = unit.owner

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
        elif winner is not None and winner.unit == self.unit:
            if winner.name == 'Transform':
                current_type = winner.unit.type
                if current_type == 'Fleet':
                    winner.unit.type = 'Army'
                    self.unit_coast = None
                else:
                    winner.unit.type = 'Fleet'
                    if len(self.north_coast) > 0:
                        self.unit_coast = winner.coast

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

    def get_distance_from(self, territory):
        if self == territory:
            return 0
        depth = 1
        visited = [self]
        check_this_depth = [t for t in self.adjacents]
        check_next_depth = []
        while True:
            while len(check_this_depth) > 0:
                t = check_this_depth.pop()
                visited.append(t)
                if t == territory:
                    return depth
                for adj in t.adjacents:
                    if adj not in visited:
                        check_next_depth.append(adj)
            depth += 1
            check_this_depth = check_next_depth
            check_next_depth = []

    def __str__(self):
        return f'{self.name}{f'*' if self.is_supply_center else ''}'

class LandTerritory(Territory):
    def __init__(self, name, abbr, is_supply_center, owner, polygons, vertices, width, height, label_pos, supply_center_pos, army_pos, coast_pos, south_coast_pos, np, cv2):
        super().__init__(name, abbr, is_supply_center, owner, polygons, vertices, width, height, label_pos, np, cv2)
        self.is_coast = False

        self.supply_center_pos = supply_center_pos
        self.army_pos = army_pos
        self.coast_pos = coast_pos
        self.south_coast_pos = south_coast_pos

    def render_supply_center(self, canvas):
        if self.is_supply_center:
            self.cv2.circle(
                canvas,
                (self.supply_center_pos[0], self.supply_center_pos[1]),
                5,
                (0, 173, 218),
                -1
            )
            self.cv2.circle(
                canvas,
                (self.supply_center_pos[0], self.supply_center_pos[1]),
                5,
                (0,0,0), # (0, 173, 218),
                3
            )

    def render_unit(self, canvas):
        if self.unit is not None:
            if self.unit.type == 'Army':
                self.render_army(canvas, self.army_pos)
            else:
                pos_x = self.coast_pos[0]
                pos_y = self.coast_pos[1]
                if self.unit_coast in ('sc', 1):
                    pos_x = self.south_coast_pos[0]
                    pos_y = self.south_coast_pos[1]
                self.render_fleet(canvas, (pos_x, pos_y))

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
    def __init__(self, name, abbr, owner, color, polygons, vertices, width, height, label_pos, fleet_pos, np, cv2):
        super().__init__(name, abbr, False, owner, polygons, vertices, width, height, label_pos, np, cv2)

        self.color = color

        self.fleet_pos = fleet_pos

    def render_unit(self, canvas):
        if self.unit is not None:
            self.render_fleet(canvas, self.fleet_pos)

    def get_color(self):
        color = self.color
        h = color.lstrip("#")
        
        # Parse R, G, B integers
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        
        # Return BGR scalar tuple (OpenCV format)
        return (b, g, r)