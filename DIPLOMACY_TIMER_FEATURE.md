# Diplomacy Phase Timer Feature

## Overview
This feature adds a real-time timer system for the Diplomacy negotiation phase. The host can start a customizable timer (5 minutes to 24 hours), and players can mark themselves as "done" when they've completed their negotiations. The host receives live feedback on who is ready and can end the phase early once all players are done.

## Features Implemented

### 1. Timer Management (Backend - Python/FastAPI)
- **Start Timer**: Host initiates a Diplomacy phase timer with a duration (300-86400 seconds)
- The duration selector defaults to 15 minutes. Adjust the hour, minute, and second dials by dragging, using the arrows, or typing.
- **Extend Timer**: Host can add time to an active timer
- **End Timer**: Host can terminate the timer early
- **Timer State**: Synced server time ensures all clients see the same countdown

**Backend Changes (server/app.py)**:
- Added `_start_diplomacy_timer()` function for initiating timers
- Added `_extend_diplomacy_timer()` function for extending active timers
- Added `_end_diplomacy_timer()` function for ending timers
- Added `_mark_player_done()` function for players to mark themselves as ready
- Updated `_can_private_chat()` to restrict private messages to only during active Diplomacy timer
- Updated order submission/deletion to reset player "done" status when orders change
- Updated resolve logic to warn if not all players are done, with override option
- Timer state included in game views sent to all clients

### 2. Player Ready Tracking
- Players controlling powers can mark themselves as "done"
- Status automatically resets when a player submits or deletes an order
- Host sees live indicator of who is ready (✓) and who is not ready (○)

### 3. Private Chat Restriction
- Private messages are only available during an active Diplomacy timer
- All other times, only public chat is available
- Prevents meta-gaming and communication outside designated negotiation phases

### 4. Override Warning Modal
- When host tries to resolve orders before all players are done:
  - Modal displays which players are not ready
  - Host can choose to override and proceed anyway
  - Or cancel to wait for remaining players

### 5. Client-Side Timer Display

#### For All Players:
- Real-time countdown display (MM:SS format)
- Live update every 100ms based on server time
- Automatically hides when timer is inactive

#### For Host:
- See which players are done (marker next to their name)
- Control buttons: Extend Timer, End Timer
- Duration input with time conversion helper (5 min → 24 hours)

#### For Regular Players:
- "Mark as Done" button in sidebar
- Button toggles between done/not done state
- Marked as not done automatically when submitting/deleting orders

## Technical Implementation

### Backend Architecture
1. **Timer Storage**: Stored in lobby object as `diplomacy_timer` dict:
   ```python
   {
       'active': bool,
       'start_time': float,  # Unix timestamp
       'duration': float,    # seconds
       'player_ready': {user_name: bool}
   }
   ```

2. **New Host Actions**:
   - `start_diplomacy_timer` - initiates timer
   - `extend_diplomacy_timer` - adds time
   - `end_diplomacy_timer` - stops timer
   - `mark_player_done` - player marks ready status

3. **Game State Updates**:
   - Timer state included in all game views
   - Players and spectators get full timer info
   - Updates broadcast to all connected players

### Frontend Architecture
1. **Timer Display Component** (`shared.js`):
   - `updateTimerDisplay()` - updates countdown and player status
   - `startTimerUpdate()` - starts 100ms interval updates
   - `stopTimerUpdate()` - stops timer updates
   - `formatSeconds()` - converts seconds to MM:SS
   - `initTimerDial()` - configures duration dial controls

2. **UI Elements**:
   - Dedicated `#diplomacy-timer-section` in sidebar
   - Host controls: start, extend, end buttons
   - Player status list with ready markers
   - Player done button for regular players

3. **HTML Changes**:
   - Added timer section to both `multiplayer-host.html` and `multiplayer-client.html`
   - Hour, minute, and second dials with total-duration validation (300-86400 seconds)
   - Modal reuses existing confirm-modal for override warning

4. **CSS Styling** (`style.css`):
   - `.timer-display` - container styling
   - `.timer-countdown` - large monospace countdown (32px, cyan color)
   - `.player-ready-item` - status indicators (green for ready, red for not ready)
   - `.timer-controls` - button layout
   - Input and form styling for duration selection

## Data Flow

### Starting Timer
1. Host sets duration and clicks "Start Timer"
2. Frontend sends `start_diplomacy_timer` message with duration
3. Backend creates timer state with current server time
4. Backend includes timer in next game state update
5. All clients receive timer state and start countdown display

### Player Marking Done
1. Player clicks "Mark as Done" button
2. Frontend sends `mark_player_done` with ready status
3. Backend updates player's ready status in timer
4. Backend broadcasts updated timer to all clients
5. All clients update player status indicators

### Submitting/Deleting Order
1. Player submits or deletes an order (existing flow)
2. Backend resets player's ready status (if timer active)
3. Backend includes updated timer in game view response
4. Frontend updates player status to "not ready"

### Resolving Orders Before All Done
1. Host clicks "Render Orders" (reveal_orders)
2. Host clicks "Resolve Orders" (resolve action)
3. Backend checks if all players are ready
4. If not ready and not overridden: returns error with not-ready list
5. Frontend shows modal with override option
6. Host can override or cancel
7. If override: Backend proceeds with resolve
8. Timer automatically deactivated on successful resolve

## Configuration

### Duration Limits
- Minimum: 300 seconds (5 minutes)
- Maximum: 86400 seconds (24 hours)
- Default UI value: 1800 seconds (30 minutes)

### Timer Updates
- Client-side update interval: 100ms
- Server time used for all calculations (prevents client clock manipulation)

## File Changes Summary

### Backend Files Modified:
- `server/app.py`
  - Added 4 new host action functions
  - Modified `_can_private_chat()` logic
  - Updated order handling to reset ready status
  - Enhanced resolve logic with override warning
  - Added timer state to `_view()` function

### Frontend Files Modified:
- `docs/multiplayer-host.html` - Added timer controls section
- `docs/multiplayer-client.html` - Added timer display section
- `docs/shared.js` - Added all timer functions and display logic
- `docs/style.css` - Added timer styling

## Testing Recommendations

### Backend Tests
- [ ] Timer creation with valid duration (300-86400)
- [ ] Timer creation with invalid duration (rejects <300 or >86400)
- [ ] Timer extend with valid/invalid additional time
- [ ] Timer end functionality
- [ ] Player ready status updates
- [ ] Ready status reset on order submission
- [ ] Ready status reset on order deletion
- [ ] Private chat blocked outside timer
- [ ] Resolve warning when not all ready
- [ ] Resolve override succeeds

### Frontend Tests
- [ ] Timer display shows correct countdown
- [ ] Timer updates every 100ms
- [ ] Player status indicators update in real-time
- [ ] Duration helper shows correct time format
- [ ] Start button disabled with invalid duration
- [ ] Extend/End buttons disabled when no timer
- [ ] Done button toggles correctly
- [ ] Modal appears when resolving with non-ready players
- [ ] Override modal option sends override flag
- [ ] Timer hides when inactive

### Integration Tests
- [ ] Multi-client timer synchronization
- [ ] Timer survives page refresh (server state maintained)
- [ ] Host timeout/reconnect preserves timer
- [ ] Multiple timer cycles in one game
- [ ] Chat restriction works correctly during/outside timer

## Known Limitations
- Timer continues to count even if all players disconnect (design intent)
- No audio/push notification alerts (could be added in future)
- Duration input doesn't persist across sessions (design intent)
- No timer presets (could be added for common durations)

## Future Enhancements
- Preset timer durations (5 min, 10 min, 15 min, 30 min, 1 hour, etc.)
- Audio/push notifications when timer ending (last minute warning, time's up)
- Timer pause/resume functionality
- Player-initiated "extend by 5 minutes" requests that host can approve
- Per-power ready tracking (not just per-player)
- Statistics on average time players take in Diplomacy phase
- Automatic resolution when all players mark done (if host enables)

## Debugging
- Check `window.diplomacy.timerInterval` to see if timer updates are running
- Check `window.diplomacy.state.diplomacy_timer` for server timer state
- Server logs will show timer actions: start, extend, end, ready changes
- Browser console will show timer callback errors if they occur
