from game.territory import LandTerritory, WaterTerritory
from game.enums import NORTH_COAST, SOUTH_COAST, ARMY, FLEET, ADVANCE

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
            coast = None
            # Get the coast if this is an advance order with a coast
            if self.order is not None and self.order.type == ADVANCE:
                coast = self.order.coast

            if self.territory.unit == self:
                self.territory.set_unit(None, coast)

            self.territory = self.collapse_to
            if self.territory is not None:
                self.territory.set_unit(self, coast)

            self.collapse_to = None
            self.is_collapsed = False

    def transform(self):
        transformation_map = {
            ARMY: FLEET,
            FLEET: ARMY
        }
        self.type = transformation_map[self.type]

    def can_traverse(self, territory, coast=None, for_support=False):
        if self.type == ARMY:
            return isinstance(territory, LandTerritory)
        if (for_support or isinstance(self.territory, WaterTerritory)) and isinstance(territory, LandTerritory) and territory.is_coast:
            return True

        occupied_coast = self.territory.unit_coast
        if occupied_coast is not None:
            if occupied_coast == NORTH_COAST and territory not in self.territory.north_coast or occupied_coast == SOUTH_COAST and territory not in self.territory.south_coast:
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
                        if coast == NORTH_COAST or coast == SOUTH_COAST:
                            return True
                    return False
                elif can_north_coast or can_south_coast:
                    if coast is not None:
                        if can_north_coast and coast == NORTH_COAST or can_south_coast and coast == SOUTH_COAST:
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