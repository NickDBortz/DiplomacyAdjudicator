from game.territory import LandTerritory, WaterTerritory

class Unit:
    def __init__(self, owner, type, territory=None):
        self.owner = owner
        self.type = type
        self.territory = territory
        self.order = None

        self.collapse_to = None
        self.is_collapsed = False

        self.dislodged = False
        self.dislodged_from = None
        self.disbanded = False

    def set_territory(self, territory):
        self.territory = territory

    def set_order(self, order):
        self.order = order

    def reset_order(self):
        self.order = None

    def dislodge(self):
        self.is_collapsed = True
        self.dislodged = True
        self.dislodged_from = self.territory

    def collapse(self, territory):
        self.collapse_to = territory
        self.is_collapsed = True

    def handle_collapse(self):
        if self.is_collapsed:
            if self.territory.unit == self:
                self.territory.set_unit(None)

            self.territory = self.collapse_to
            if self.territory is not None:
                self.territory.set_unit(self)

            self.collapse_to = None
            self.is_collapsed = False

    def disband(self):
        self.owner.remove_unit(self)
        self.disbanded = True
        self.territory = None

    def transform(self):
        transformation_map = {
            'Army': 'Fleet',
            'Fleet': 'Army'
        }
        self.type = transformation_map[self.type]

    def can_traverse(self, territory, coast=None, for_support=False):
        if self.type == 'Army':
            return isinstance(territory, LandTerritory)
        if (for_support or isinstance(self.territory, WaterTerritory)) and isinstance(territory, LandTerritory) and territory.is_coast:
            return True

        occupied_coast = self.territory.unit_coast
        if occupied_coast is not None:
            if occupied_coast == 0 and territory not in self.territory.north_coast or occupied_coast == 1 and territory not in self.territory.south_coast:
                return False
        
        if isinstance(territory, WaterTerritory):
            return True
        if isinstance(territory, LandTerritory) and territory.is_coast:
            # Must ensure that destination territory connects to current coastal regions
            if len(territory.north_coast) > 0:
                # The destination territory has north/south coasts, so we need additional logic
                can_north_coast = self.territory in territory.north_coast
                can_south_coast = self.territory in territory.south_coast
                if can_north_coast and can_south_coast:
                    if coast is not None:
                        if coast == 'nc' or coast == 'sc':
                            return True
                    return False
                elif can_north_coast or can_south_coast:
                    if coast is not None:
                        if can_north_coast and coast == 'nc' or can_south_coast and coast == 'sc':
                            return True
                        return False
                    return True
                return False
            else:
                for t in self.territory.adjacents:
                    if isinstance(t, WaterTerritory) and territory in t.adjacents:
                        return True
        return False

    def __str__(self):
        return f"{self.owner.name}'s {self.type} at {self.territory if self.territory else '???'}"