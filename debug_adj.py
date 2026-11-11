import sys
sys.path.insert(0, 'server')

from game.map_loader import MapLoader

# Load the map
loader = MapLoader('server/data/maps/classic_map.json')
result = loader.load_map_json()
territories = result[1]

# Find territories
lon = next(t for t in territories if t.abbr == 'LON')
bel = next(t for t in territories if t.abbr == 'BEL')

print(f"London ({lon.abbr}) adjacents: {[t.abbr for t in lon.adjacents]}")
print(f"BEL in LON adjacents? {bel in lon.adjacents}")
