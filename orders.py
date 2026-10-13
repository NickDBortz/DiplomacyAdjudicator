from territory import LandTerritory, WaterTerritory

class Order:
    def __init__(self, name, unit):
        self.name = name
        self.unit = unit 
        self.unit_territory = unit.territory

        self.power = 0
        self.passive_power = 0
        self.supporters = []
        self.deactivated_supporters = []

        self.is_valid = self.validate()
        if self.unit.order is not None:
            self.is_valid = False

    def validate(self):
        # Default invalid
        return False

    def support(self, supporter):
        self.supporters.append(supporter)
        self.power += 1
        self.passive_power += 1

    def cut_support(self, supporter):
        if supporter in self.supporters:
            self.supporters.remove(supporter)
            self.power -= 1
            self.passive_power -= 1

    def nullify_support(self, supporter):
        if supporter not in self.deactivated_supporters:
            self.deactivated_supporters.append(supporter)
            self.passive_power -= 1

    def get_start_pos(self):
        t = self.unit.territory
        if isinstance(t, LandTerritory):
            if self.unit.type == 'Army':
                return t.army_pos
            else:
                if len(t.north_coast) > 0:
                    if t.unit_coast in ('nc', 0):
                        return t.coast_pos
                    else:
                        return t.south_coast_pos
                else:
                    return t.coast_pos
        else:
            return t.fleet_pos

    def __str__(self):
        return f'{self.name} {self.unit}'

class HoldOrder(Order):
    def __init__(self, unit):
        super().__init__('Hold', unit)

    def match(self, other):
        if not isinstance(other, HoldOrder):
            return False
        return other.unit == self.unit

    def validate(self):
        # Always valid
        return True

    def activate(self):
        # A hold order does nothing, just stays at current territory with the same power
        pass

    def __str__(self):
        return f'{self.unit} Hold'

class AdvanceOrder(Order):
    def __init__(self, unit, dest_territory, coast=None, force_via_convoy=False):
        self.dest_territory = dest_territory
        self.coast = coast
        self.is_utilizing_convoy = force_via_convoy
        super().__init__('Advance', unit)

    def match(self, other):
        if not isinstance(other, AdvanceOrder):
            return False
        return other.unit == self.unit and other.dest_territory == self.dest_territory and (other.coast == self.coast if other.coast is not None else True)

    def get_dest_pos(self):
        t = self.dest_territory
        if isinstance(t, LandTerritory):
            if self.unit.type == 'Army':
                return t.army_pos
            else:
                if len(t.north_coast) > 0:
                    if self.coast == 'nc':
                        return t.coast_pos
                    else:
                        return t.south_coast_pos
                else:
                    return t.coast_pos
        else:
            return t.fleet_pos

    def validate(self):
        if self.unit.territory is None:
            self.unit.territory = self.unit.dislodged_from

        if self.dest_territory == self.unit.territory or not self.unit.can_traverse(self.dest_territory, self.coast):
            return False
        
        # Valid if destination territory is adjacent to current unit's territory and traversable by unit type and not forcing a convoy
        if self.dest_territory in self.unit.territory.adjacents and not self.is_utilizing_convoy:
            return True

        self.is_utilizing_convoy = True
        if not self.unit.type == 'Army':
            return False

        # If the army unit, valid if there is a string of fleets in water territories between current territory and destination land territory
        # If fleet unit, valid if path from itself through fleets in water territories to convoying unit and the destination land territory
        traversed = []
        traverse_list = []
        for territory in self.unit.territory.adjacents:
            if isinstance(territory, WaterTerritory) and territory.unit is not None and territory.unit.type == 'Fleet':
                traverse_list.append(territory)

        while len(traverse_list) > 0:
            territory = traverse_list.pop()
            for adj in territory.adjacents:
                if adj == self.dest_territory: return True
                if isinstance(adj, WaterTerritory) and adj not in traversed and adj.unit is not None and adj.unit.type == 'Fleet':
                    traverse_list.append(adj)
            traversed.append(territory)

        return False

    def activate(self):
        # Contest the destination territory
        self.dest_territory.add_contestant(self)

    def __str__(self):
        return f'{self.unit} Advance to {self.dest_territory}'

class SupportOrder(Order):
    def __init__(self, unit, supported_order):
        self.supported_order = supported_order
        super().__init__('Support', unit)

    def match(self, other):
        if not isinstance(other, SupportOrder):
            return False
        return other.unit == self.unit and other.supported_order == self.supported_order

    def validate(self):
        # TODO: A support order of a convoy advance is invalid if the unit supporting is a necessary fleet in the convoy
        # Valid if supported order unit is in an adjacent territory to the current unit's territory and traversible by unit type
        unit_territory = self.unit.territory
        dest_territory = self.supported_order.dest_territory if self.supported_order.name == 'Advance' else self.supported_order.unit.territory
        valid_location = False
        if unit_territory.unit_coast is not None:
            coast = unit_territory.unit_coast 
            valid_location = coast == 0 and dest_territory in unit_territory.north_coast or coast == 1 and dest_territory in unit_territory.south_coast
        else:
            valid_location = dest_territory in unit_territory.adjacents

        # Check if the supported order is a convoy, and then check for valid routes, excluding the current unit's territory, as that unit must be supporting
        if self.supported_order.name == 'Advance' and self.supported_order.is_utilizing_convoy:
            visited = []
            to_visit = [t for t in self.supported_order.unit.territory.adjacents if isinstance(t, WaterTerritory) and t.unit is not None and t != unit_territory]
            found = False
            while len(to_visit) > 0:
                territory = to_visit.pop()
                visited.append(territory)
                # Check all neighboring territories
                for t in territory.adjacents:
                    if not t in visited:
                        if t == dest_territory:
                            to_visit.clear()
                            found = True
                            break
                        if isinstance(t, WaterTerritory) and t.unit is not None and t != unit_territory:
                            to_visit.append(t)
            valid_location = found and valid_location

        return valid_location and self.unit.can_traverse(dest_territory, for_support=self.supported_order.unit.type == 'Fleet')

    def activate(self):
        # Add support to supported order
        self.supported_order.support(self)

    def __str__(self):
        return f'{self.unit} Supports {self.supported_order}'

class TransformOrder(Order):
    def __init__(self, unit, coast=None):
        self.coast = coast
        super().__init__('Transform', unit)

    def match(self, other):
        if not isinstance(other, TransformOrder):
            return False
        return other.unit == self.unit

    def validate(self):
        if isinstance(self.unit.territory, WaterTerritory):
            return False

        if self.unit.territory.is_coast:
            if len(self.unit.territory.north_coast) > 0:
                if self.coast is None:
                    return False
                return True
            elif self.coast is not None:
                return False
            else:
                return True
        else:
            return False

    def activate(self):
        # Functions like a hold order, does not contest
        pass

    def __str__(self):
        return f'{self.unit} Transforms'

class ConvoyOrder(Order):
    def __init__(self, unit, convoying_unit, dest_territory):
        self.convoying_unit = convoying_unit
        self.dest_territory = dest_territory
        super().__init__('Convoy', unit)

    def match(self, other):
        if not isinstance(other, ConvoyOrder):
            return False
        return other.unit == self.unit and other.convoying_unit == self.convoying_unit and other.dest_territory == self.dest_territory

    def validate(self):
        # If the army unit, valid if there is a string of fleets in water territories between current territory and destination land territory
        # If fleet unit, valid if path from itself through fleets in water territories to convoying unit and the destination land territory
        if not self.unit.type == 'Fleet':
            return False

        # Cannot convoy a unit from it's territory to the same territory
        if self.dest_territory == self.convoying_unit.territory:
            return False 
        
        traversed = []
        traverse_list = []
        found_convoying_unit = False
        found_dest_territory = False
        for territory in self.unit.territory.adjacents:
            if territory.unit == self.convoying_unit:
                found_convoying_unit = True
            if territory == self.dest_territory:
                found_dest_territory = True
            if found_convoying_unit and found_dest_territory: return True
            if isinstance(territory, WaterTerritory) and territory.unit is not None and territory.unit.type == 'Fleet':
                traverse_list.append(territory)

        while len(traverse_list) > 0:
            territory = traverse_list.pop()
            if self.dest_territory in territory.adjacents:
                # Don't consider neighbors of this territory if found destination. They're illegal convoy locations
                found_dest_territory = True
                continue
            for adj in territory.adjacents:
                if adj.unit == self.convoying_unit:
                    found_convoying_unit = True
                if found_convoying_unit and found_dest_territory: return True
                if isinstance(adj, WaterTerritory) and adj not in traversed and adj.unit is not None and adj.unit.type == 'Fleet':
                    traverse_list.append(adj)
            traversed.append(territory)

        return found_convoying_unit and found_dest_territory

    def activate(self):
        # If the convoyed unit is a friendly unit, infer that the intent of the order is to convoy, if not specified by order
        # This is only possible if the entire convoy route is friendly fleets
        if self.convoying_unit.owner == self.unit.owner and self.convoying_unit.order.name == 'Advance' and self.convoying_unit.order.dest_territory == self.dest_territory:
            # Check convoy using only friendly fleets
            # if self.unit.territory.check_convoy_from(self.convoying_unit, self.convoying_unit.territory, self.dest_territory, force_owner=self.unit.owner):
            self.convoying_unit.order.is_utilizing_convoy = True

    def __str__(self):
        return f'{self.convoying_unit} Convoys to {self.dest_territory}'

class BuildOrder(Order):
    def __init__(self, unit, territory, coast=None):
        self.dest_territory = territory
        self.coast = coast
        super().__init__('Build', unit)

    def match(self, other):
        if not isinstance(other, BuildOrder):
            return False
        return other.unit == self.unit and other.dest_territory == self.dest_territory and other.coast == self.coast

    def validate(self):
        # If the destination has multiple coasts and we don't specify one and the unit is a fleet, fail
        if len(self.dest_territory.north_coast) > 0 and self.coast is None and self.unit.type == 'Fleet' or self.dest_territory.unit is not None:
            return False

        # If the destination is a water territory and the unit is an army, fail
        if isinstance(self.dest_territory, WaterTerritory) and self.unit.type == 'Army':
            return False

        # If the destination is an inland territory and the unit is a fleet, fail
        if isinstance(self.dest_territory, LandTerritory) and not self.dest_territory.is_coast and self.unit.type == 'Fleet':
            return False

        # If the destination is occupied, fail
        if self.dest_territory.unit is not None:
            return False
        
        return True

    def activate(self):
        pass

    def resolve(self):
        self.dest_territory.set_unit(self.unit, coast=self.coast)
        self.dest_territory.owner.add_unit(self.unit)

    def __str__(self):
        return f'{self.unit} Built at {self.dest_territory}'

class DisbandOrder(Order):
    def __init__(self, unit):
        super().__init__('Disband', unit)

    def match(self, other):
        if not isinstance(other, DisbandOrder):
            return False
        return other.unit == self.unit

    def validate(self):        
        return True

    def activate(self):
        pass

    def resolve(self):
        self.unit.territory.set_unit(None)
        self.unit.territory = None
        self.unit.owner.remove_unit(self.unit)

    def __str__(self):
        return f'{self.unit} Removed from {self.territory}'