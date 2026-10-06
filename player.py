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