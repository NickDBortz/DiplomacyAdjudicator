from game.enums import ADJUSTMENT_PHASE, SPRING_PHASE, SPRING_RETREAT_PHASE, FALL_PHASE, FALL_RETREAT_PHASE

class GameState:
    def __init__(self, players, territories):
        self.players = {}
        for player in players:
            self.players[player.name] = player 
        self.player_list = players
        self.territories = {}
        for territory in territories:
            self.territories[territory.name] = territory
            self.territories[territory.abbr] = territory
        self.territory_list = territories

        self.resolution_phases = [ADJUSTMENT_PHASE, SPRING_PHASE, SPRING_RETREAT_PHASE, FALL_PHASE, FALL_RETREAT_PHASE]
        self.resolution_phase = 0
        
        self.year = 1800 # Set to what it should be
        self.winner = None
        self.draw = False

        self.queued_orders = []

    def get_player(self, name):
        if name in self.players:
            return self.players[name]
        return None

    def get_territory(self, name):
        if name in self.territories:
            return self.territories[name]
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

    def build_unit(self, unit, territory, coast):
        territory.set_unit(unit, coast)
        territory.owner.add_unit(unit)

    def disband_unit(self, unit):
        if unit.territory is not None:
            unit.territory.set_unit(None)
            unit.territory = None
        unit.owner.remove_unit(unit)
        unit.disbanded = True

    def retreat_unit(self, unit):
        unit.dislodged = False
        unit.dislodge_from = None
        destination = unit.order.dest_territory
        destination_owner = destination.owner
        unit.set_territory(destination)
        destination.set_unit(unit, coast=unit.order.coast)
        destination.owner = destination_owner
        unit.reset_order()