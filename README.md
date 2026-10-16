# Diplomacy Adjudicator

A Python implementation of Diplomacy's map, orders, and turn adjudication. The included map is the classic Europe map. Players enter orders one power at a time; the orders are resolved together after everyone is finished.

## Setup and start

Use Python 3 and install the dependencies from the repository root:

```bash
python -m pip install -r requirements.txt
python main.py
```

The game opens a map window and starts in the Adjustment phase. A desktop session that supports OpenCV windows is required for the default renderer.

## Playing

Diplomacy is a strategy game in which powers compete to control supply centers. Armies move over land, fleets move over water and coastal territories, and fleets can convoy armies across connected seas. A unit can hold, move, support another unit, or take part in a convoy. A successful move into a supply center changes its owner. The first power to control the map's `win_count` supply centers wins.

The game cycles through Spring and Fall movement, retreat, and adjustment phases (phases with nothing to resolve may be skipped). Each power enters its orders separately, but orders resolve simultaneously:

1. At the `Name of Great Power` prompt, enter a power name.
2. Enter that power's orders, one at a time. The game reports invalid orders.
3. Enter `q` to finish that power's orders and return to the power prompt. Enter `q` there when all powers have entered orders; press Enter to resolve.
4. In retreat phases, submit a move for each dislodged unit that should retreat. A unit without a valid retreat order is disbanded.
5. In Adjustment, build or remove units to match the number of supply centers you own. New units can only be built in a territory initially owned by that power.

Maps define players and territory ownership but do not define starting units. The included classic map begins in Adjustment, so players build units at their owned home supply centers before regular movement phases.

### Order format

Enter one order per unit. Unit tokens are `A` (army) and `F` (fleet); territory abbreviations are shown on the map.

| Order | Example |
| --- | --- |
| Hold | `A PAR H` |
| Move | `A PAR - BUR` |
| Support a move or hold | `A MAR S A PAR - BUR` or `A MAR S A PAR H` |
| Convoy an army | `F NTH C A LON - BEL` |
| Build an army or fleet | `Build A PAR` or `Build F STP(nc)` |
| Remove a unit | `Remove A PAR` |

For a fleet in a territory with multiple coasts, specify the coast where needed with `(nc)` or `(sc)`; these suffixes are lowercase. Order tokens and unit tokens use the capitalization shown above. During a retreat, use the normal move form, such as `A PAR - BUR`. Enter `draw` for a power to vote for a draw; the game ends in a draw when every remaining active power has voted for it.

## Custom maps

The default map is `data/maps/classic_map.json`. A custom map must be valid JSON and contain these top-level fields:

| Field | Meaning |
| --- | --- |
| `players` | Array of powers. Each item requires a `name` and a six-digit hex `color` such as `#A87E9F`. |
| `win_count` | Number of supply centers needed to win. |
| `water_color` | Hex color used for water. |
| `width`, `height` | Map image dimensions in pixels. |
| `vertices` | Array of `[x, y]` coordinate pairs. |
| `territories` | Array of territory definitions described below. |

Each territory requires `name`, `abbr`, `owner`, `land`, `supply_center`, `adjacents`, `north_coast`, and `south_coast`. `owner` must be a player name from `players`, or `""` for unowned. `land` and `supply_center` are booleans. `adjacents` is a list of neighboring territory names; adjacency is made reciprocal when the map is loaded. For a multi-coast land territory, `north_coast` and `south_coast` list the neighboring territories accessible from each coast. Use empty lists when a territory has no coast-specific neighbors.

The default renderer also needs layout data on each territory:

- `polygons`: arrays of polygons, each polygon being a list of indices into the top-level `vertices` array.
- `label_pos`: `[x, y]` position for the territory abbreviation.
- `fleet_pos` for water territories.
- `army_pos` and `coast_pos` for land territories; `south_coast_pos` is also used for fleets on a south coast.
- `supply_center_pos` for land supply centers.

All positions are pixel coordinates within `width` by `height`. `var_name` is present in the included JSON but is not used by the game. See `data/maps/classic_map.json` for the full-size example.

To launch with a custom map, construct the game with its JSON path from the repository root:

```bash
python -c 'from game.game import Game; Game(json_file="data/maps/my_map.json").do_gameplay_loop()'
```

## Tests

Run the test suite from the repository root:

```bash
python -m pytest
```

## Web frontend (GitHub Pages)

`docs/` holds a static site that runs the Python game in the browser via Pyodide and draws the map as SVG. Build the generated files and serve locally:

```bash
python tools/build_web.py
python -m http.server --directory docs
```

Open http://localhost:8000 and use the developer console: `diplomacy.order("Build A PAR", "France")`, `diplomacy.resolve()`, `diplomacy.state`, `diplomacy.help()`. The `Deploy Pages` workflow builds and publishes it (set Pages source to "GitHub Actions").
