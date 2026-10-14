class GameState:
    def __init__(self, players, territories):
        self.players = players
        self.territories = territories

        self.resolution_phases = ['Adjustment', 'Spring', 'Spring Retreat', 'Fall', 'Fall Retreat']
        self.resolution_phase = 0
        
        self.year = 1800 # Set to what it should be
        self.winner = None
        self.draw = False

        self.queued_orders = []

    def get_player(self, name):
        for player in self.players:
            if player.name.lower() == name.lower():
                return player
        return None

    def get_territory(self, name):
        for territory in self.territories:
            if territory.name.lower() == name.lower() or territory.abbr.lower() == name.lower():
                return territory
        return None

    def queue_order(self, order):
        self.queued_orders.append(order)

    def get_orders(self):
        return self.queued_orders

    def remove_queued_order(self, order):
        if order in self.queued_orders:
            self.queued_orders.remove(order)

    def clear_queued_orders(self):
        self.queued_orders.clear()

    def get_phase(self):
        return self.resolution_phases[self.resolution_phase]

    def set_phase(self, phase):
        if phase not in self.resolution_phases:
            return
        self.resolution_phase = self.resolution_phases.index(phase)

    def get_winner(self):
        return self.winner

    def set_winner(self, winner):
        self.winner = winner

    def advance_phase(self, skip_retreat=False, skip_adjustment=False):
        self.resolution_phase += 1
        if self.resolution_phase >= len(self.resolution_phases):
            self.resolution_phase = 0
            self.year += 1

        if skip_retreat or skip_adjustment:
            self.advance_phase()