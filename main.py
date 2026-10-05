from player import Player
from map import Map
from orders import HoldOrder

if __name__ == "__main__":
    player1 = Player('Player 1')
    map = Map(player1)
    map.init_player_units(player1)

    # Generate single hold order
    for x in range(5):
        for i in range(5):
            hold_order = HoldOrder(player1.units[0])
            map.queue_order(hold_order)

        map.resolve_orders()