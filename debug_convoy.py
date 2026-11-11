import sys
sys.path.insert(0, 'server')

from game.map_loader import MapLoader
from game.state import GameState
from game.order_generator import OrderGenerator
from game.unit import Unit
from game.enums import ARMY

# Load the map
loader = MapLoader('server/data/maps/classic_map.json')
result = loader.load_map_json()
players, territories = result[0], result[1]

# Create game state
game_state = GameState(players, territories)

# Find London and Brest
lon = next(t for t in territories if t.name == 'London')
bre = next(t for t in territories if t.name == 'Brest')
eng = next(t for t in territories if t.name == 'English Channel')
wal = next(t for t in territories if t.name == 'Wales')

print(f"London ({lon.abbr}) adjacents: {[t.abbr for t in lon.adjacents]}")
print(f"Brest ({bre.abbr}) is adjacent to London? {bre in lon.adjacents}")
print(f"Wales ({wal.abbr}) is adjacent to London? {wal in lon.adjacents}")

# Create army at London
england = next(p for p in players if p.name == 'England')
army = Unit(england, ARMY, lon)
lon.set_unit(army)
england.add_unit(army)

# Create fleet at English Channel to enable convoy
fleet = Unit(england, 'Fleet', eng)
eng.set_unit(fleet)
england.add_unit(fleet)

# Generate valid orders
order_gen = OrderGenerator(game_state, None)
orders = order_gen._generate_valid_standard_orders(england)

print(f"\nArmy movement orders:")
lon_orders = [o for o in orders if o.startswith('A LON -')]
for order in sorted(lon_orders):
    print(f"  {order}")

# Check specific cases
bre_orders = [o for o in lon_orders if 'BRE' in o]
wal_orders = [o for o in lon_orders if 'WAL' in o]

print(f"\nAnalysis:")
print(f"  BRE (non-adjacent): {bre_orders}")
print(f"    Has plain order? {any(' via convoy' not in o for o in bre_orders)}")
print(f"    Has via convoy? {any(' via convoy' in o for o in bre_orders)}")

print(f"  WAL (adjacent): {wal_orders}")
print(f"    Has plain order? {any(' via convoy' not in o for o in wal_orders)}")
print(f"    Has via convoy? {any(' via convoy' in o for o in wal_orders)}")


