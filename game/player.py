from game.enums import FLEET

class Player:
    def __init__(self, name, color):
        self.name = name
        self.units = []

        self.color = color

    def add_unit(self, unit):
        self.units.append(unit)

    def remove_unit(self, unit):
        if unit in self.units:
            self.units.remove(unit)

    def get_supply_centers(self, territories):
        supply_centers = 0
        for territory in territories:
            if territory.is_supply_center and territory.owner == self:
                supply_centers += 1
        return supply_centers

    def units_to_build(self, territories):
        supply_centers = self.get_supply_centers(territories)
        current_units = len(self.units)
        return supply_centers - current_units

    def get_furthest_unit(self, territories):
        owned_supply_centers = [territory for territory in territories if territory.owner == self and territory.is_supply_center]
        furthest_distance = 0
        furthest_units = []
        for unit in self.units:
            dist = 100
            for sc in owned_supply_centers:
                _dist = sc.get_distance_from(unit.territory)
                if _dist < dist:
                    dist = _dist
            if dist > furthest_distance:
                furthest_distance = dist
                furthest_units.clear()
                furthest_units.append(unit)
            elif dist == furthest_distance:
                furthest_units.append(unit)

        if len(furthest_units) == 1:
            return furthest_units[0]

        # Fleets take precedence in civil disobedience
        furthest_fleets = [unit for unit in furthest_units if unit.type == FLEET]
        if len(furthest_fleets) > 0:
            furthest_units = furthest_fleets

        first_alphabetized = furthest_units[0].territory.name
        first_unit = furthest_units[0]
        for unit in furthest_units:
            if unit.territory.name < first_alphabetized:
                first_alphabetized = unit.territory.name
                first_unit = unit

        return first_unit

    def __str__(self):
        return f'Player {self.name}'
