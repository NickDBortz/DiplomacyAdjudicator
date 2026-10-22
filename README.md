# Diplomacy Adjudicator

A Python implementation of Diplomacy's map, orders, and turn adjudication, with a browser front end for singleplayer and online multiplayer games. The included map is the classic Europe map.

> **Disclaimer:** *Diplomacy* is a registered trademark of its rights holder (currently Hasbro, Inc., through its Avalon Hill brand). This project is not affiliated with, endorsed by, or sponsored by the trademark holder. The included classic map and the rules implemented here are based on the original board game and are provided **for personal, non-commercial development and testing purposes only**. If you want to play Diplomacy, please support the official game.

## Project layout

| Path | Contents |
| --- | --- |
| `server/game/` | The rules engine: map loading, order parsing, adjudication, and game state. |
| `server/app.py` | FastAPI backend that runs singleplayer games, multiplayer lobbies, and live games over WebSockets. |
| `server/main_cli.py` | Command-line version of the game with an OpenCV map window. |
| `server/data/maps/` | Map JSON files used by the server. |
| `server/tests/` | Pytest suite for orders and adjudication. |
| `docs/` | Static web front end (published to GitHub Pages). |
| `docs/data/` | Map JSON files the browser uses to draw the map. |
| `tools/` | Scripts used to build the map JSON from reference images. |

## Playing in the browser

The front end in `docs/` is published to GitHub Pages and talks to the backend hosted on Render. The main menu offers:

- **Singleplayer**: one browser plays every power. Choose a power, enter its orders, switch to the next power, and resolve when all orders are in.
- **Multiplayer**: host or join a game where each player controls one power.

The free Render instance sleeps when idle, so the first request after a break can take around 30 seconds.

### Multiplayer

1. **Host a game.** Pick a player name, a lobby name, and an optional password. The password is hashed with a salt on the server; the connection itself is protected by HTTPS/WSS.
2. **Join a game.** Other players choose the lobby from the list (a lock icon marks password-protected lobbies) and enter a name.
3. **Lobby.** Each player picks a Great Power or chooses to spectate. The host picks the map and can load a save file from an earlier game. The host starts the game once everyone has chosen; powers nobody picked start vacant.
4. **Playing.** Players submit orders for their own power; other players' orders stay hidden. The host clicks **Render Orders** to show everyone's orders, then **Resolve Orders** to adjudicate. After each resolution the host's browser downloads a save file. Games live only in the server's memory, so keep the latest save to restart a game if the server restarts.

Every player gets a secret token when they join. The server checks it on every connection, so players can act only for themselves and only the host can use host controls.

### Chat

The **Chat** button at the bottom-left of the lobby and game pages opens a chat panel that can be collapsed again.

- **Lobby / Everyone** is visible to everyone in the lobby, and it carries over into the game.
- **Private messages** are available during a game between two players who control powers. Pick a player from **Private message…** to start one; only the two of you can see it. Spectators can't send or receive private messages.
- While the panel is collapsed or showing another conversation, new messages show a short pop-up, an unread count on the Chat button and tabs, and a count in the page title.
- Messages are limited to 500 characters, with at most 5 every 5 seconds per player. The server keeps the last 200 messages of each conversation in memory; history is not part of save files. A player's private conversations are deleted when they leave or are kicked.

### Host controls

- **Kick** removes a player. During a game their power becomes vacant.
- **Make host** hands the host role to another connected player. During a game the new host must control a power.
- **Open Game to New Players** lists a running game on the join page. Anyone who asks to join waits until the host admits them as a spectator, gives them a vacant power, or rejects them. A request expires if it isn't answered within 3 minutes.
- **Fill a Vacant Power** gives a vacant power to a spectator.

### Disconnects and leaving

- If a player's connection drops, the page reconnects automatically and the player keeps their seat. Other players see them marked as disconnected.
- A player who closes the tab can return with **Rejoin** on the main menu. The seat is kept until the player leaves or the host kicks them.
- If the host is disconnected for 60 seconds, the host role passes to a connected player who controls a power. The new host can hand it back with **Make host**.
- Opening the same seat in another tab moves the connection to the new tab.
- A game nobody is connected to is closed after 2 hours.

A power with no player is **vacant**. Its units hold, a dislodged unit is disbanded, and if it must remove units, the ones furthest from home are removed. Vacant powers do not vote on draws.

## How the game works

Diplomacy is a strategy game in which powers compete to control supply centers. Armies move over land, fleets move over water and coastal territories, and fleets can convoy armies across connected seas. A unit can hold, move, support another unit, or take part in a convoy. A successful move into a supply center changes its owner. The first power to control the map's `win_count` supply centers wins.

The game cycles through Spring and Fall movement, retreat, and adjustment phases; phases with nothing to resolve are skipped. Orders are entered separately but resolve simultaneously.

- In retreat phases, order a move for each dislodged unit that should retreat. A unit without a valid retreat order is disbanded.
- In Adjustment, build or remove units to match the number of supply centers you own. New units can only be built in an empty home supply center that you still control.

Maps define players and territory ownership but not starting units. The classic map begins in Adjustment, so players build their starting units at their home supply centers before the first movement phase.

**Draws:** any power can vote to draw. The game ends in a draw once every power that still has supply centers and is controlled by a player has voted. In singleplayer that means every power with supply centers. A player who leaves takes their vote with them.

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

For a fleet in a territory with multiple coasts, specify the coast with `(nc)` or `(sc)`; these suffixes are lowercase. Order and unit tokens use the capitalization shown above. During a retreat, use the normal move form, such as `A PAR - BUR`.

## Running locally

Use Python 3. All commands below start from the repository root.

### Backend

```bash
cd server
python -m pip install -r requirements.txt
python -m uvicorn app:app --port 8001
```

The `ALLOWED_ORIGINS` environment variable sets the allowed CORS origins (comma-separated); it defaults to `*`.

### Front end

In a second terminal:

```bash
python -m http.server 8000 --directory docs
```

Open http://localhost:8000. When the page is served from `localhost`, it uses the backend at `http://localhost:8001`. To use a different backend, add `?api=<url>` to the page URL or set `localStorage.diplomacyApi`.

On the singleplayer page, the browser console also exposes `diplomacy.order("Build A PAR", "France")`, `diplomacy.resolve()`, `diplomacy.state`, and `diplomacy.help()`.

### Command-line version

The original command-line game draws the map in an OpenCV window, so it needs a desktop session:

```bash
cd server
python -m pip install -r requirements-cli.txt
python main_cli.py
```

1. At the `Name of Great Power` prompt, enter a power name.
2. Enter that power's orders one at a time. Invalid orders are reported.
3. Enter `q` to finish that power's orders. Enter `q` at the power prompt when every power is done, then press Enter to resolve.
4. Enter `draw` instead of an order to vote for a draw for that power.

## Tests

```bash
cd server
python -m pytest
```

The `Run Tests` workflow runs the suite on every push.

## Deployment

- **Front end:** the `Deploy Pages` workflow publishes `docs/` to GitHub Pages on every push to `main`. Set the Pages source to "GitHub Actions".
- **Backend:** `render.yaml` deploys `server/` to Render with `uvicorn app:app`. Set `ALLOWED_ORIGINS` to the Pages origin.

## Custom maps

Maps are JSON files. To use a map in the web game, put the same file in both `server/data/maps/` (rules) and `docs/data/` (drawing). The host can then pick it in the lobby. The default is `classic_map.json`. A map has these top-level fields:

| Field | Meaning |
| --- | --- |
| `players` | Array of powers. Each item requires a `name` and a six-digit hex `color` such as `#A87E9F`. |
| `win_count` | Number of supply centers needed to win. |
| `water_color` | Hex color used for water. |
| `width`, `height` | Map image dimensions in pixels. |
| `vertices` | Array of `[x, y]` coordinate pairs. |
| `territories` | Array of territory definitions described below. |

Each territory requires `name`, `abbr`, `owner`, `land`, `supply_center`, `adjacents`, `north_coast`, and `south_coast`.

- `owner` is a player name from `players`, or `""` if unowned.
- `land` and `supply_center` are booleans.
- `adjacents` lists neighboring territory names. Adjacency is made reciprocal when the map loads.
- For a land territory with two coasts, `north_coast` and `south_coast` list the neighbors reachable from each coast. Use empty lists when a territory has no coast-specific neighbors.

Drawing the map also needs layout data on each territory:

- `polygons`: arrays of polygons, each a list of indices into the top-level `vertices` array.
- `label_pos`: `[x, y]` position for the territory abbreviation.
- `fleet_pos` for water territories.
- `army_pos` and `coast_pos` for land territories; `south_coast_pos` is also used for fleets on a south coast.
- `supply_center_pos` for land supply centers.

All positions are pixel coordinates within `width` by `height`. `var_name` appears in the included JSON but is not used. See `server/data/maps/classic_map.json` for a full example.

To run the command-line game with a custom map, from `server/`:

```bash
python -c "from game.game import Game; Game(json_file='data/maps/my_map.json').do_gameplay_loop()"
```
