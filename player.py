class Player:
    def __init__(self, name):
        self.name = name
        self.units = []

        self.queue_to_remove = []

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
