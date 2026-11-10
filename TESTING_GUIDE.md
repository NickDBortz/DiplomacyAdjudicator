# Interactive Map Order Picker - Testing Guide

## Quick Start Testing

### Prerequisites
- Python 3.x (for the backend server)
- Modern web browser
- Both desktop and mobile device (for testing responsiveness)

### Starting the Application

1. **Start Backend Server**:
   ```bash
   cd server
   python app.py
   ```
   The server will start on http://localhost:8001

2. **Start Local Web Server** (in another terminal):
   ```bash
   cd docs
   python -m http.server 8000
   ```
   The interface will be at http://localhost:8000

3. **Open in Browser**:
   - Desktop: http://localhost:8000/singleplayer.html
   - Mobile: Navigate to your machine's IP address on mobile device

## Test Scenarios

### Test 1: Basic Unit Selection and Movement

**Objective**: Test clicking on units and selecting move orders

**Steps**:
1. Click "New Game" to start a game
2. Select a power (e.g., "France")
3. On the map, click on territory "PAR" (Paris) - should highlight in gold
4. Click on an adjacent territory like "BUR" (Burgundy) - should highlight in red
5. Check that order is auto-selected in dropdown
6. Click "Submit Order"
7. Verify order submitted successfully

**Expected Results**:
- Territories highlight in correct colors
- Dropdowns update automatically
- Order appears in queued orders list
- Map selection resets for next order

---

### Test 2: Hold Order Selection

**Objective**: Test selecting hold orders

**Steps**:
1. Select a power
2. Click on a unit territory
3. Click the SAME territory again (to deselect target)
4. Should see message about clearing selection
5. Click the territory again
6. Only "Hold" order should be available
7. Submit

**Expected Results**:
- Same-territory click toggles selection
- Hold order auto-selected
- Works correctly

---

### Test 3: Support Order Selection

**Objective**: Test selecting support orders with multiple units

**Steps**:
1. Select a power with multiple units
2. Click on a unit (e.g., army)
3. Click on another allied unit's location
4. System should detect this as potential support order
5. If multiple options, dialog should appear
6. Select appropriate order and submit

**Expected Results**:
- Support orders are properly detected
- Appropriate order is suggested
- Works with dialog if multiple options

---

### Test 4: Multiple Order Suggestions

**Objective**: Test the dialog when multiple valid orders exist

**Steps**:
1. Select power with fleets
2. Click on fleet location
3. Click on destination where both move and convoy could work
4. Dialog should appear with order options
5. Verify list shows all valid orders
6. Click to select option

**Expected Results**:
- Dialog shows multiple valid orders
- Dialog properly formatted and readable
- Selection works correctly

---

### Test 5: Dropdown to Map Synchronization

**Objective**: Test that changing dropdowns updates map highlighting

**Steps**:
1. Select power
2. Use dropdown to select a unit
3. Check that map highlights that unit's territory in gold
4. Use dropdown to select order type
5. Change to different unit
6. Verify highlighting updates

**Expected Results**:
- Map highlighting updates when dropdowns change
- Synchronization is bidirectional
- No conflicts between map and dropdown selections

---

### Test 6: Mobile Touch Interaction

**Objective**: Test touch interaction on mobile/tablet

**Steps**:
1. Open on mobile/tablet device
2. Tap on unit territory
3. Tap on destination territory
4. Verify highlighting and selection works
5. Try multiple orders
6. Test "Clear selection" button

**Expected Results**:
- Touch events properly detected
- No need for precise clicking
- Touch targets are adequate
- Scrolling doesn't interfere

---

### Test 7: Retreat Phase

**Objective**: Test order selection during retreat phase

**Steps**:
1. Play until units get dislodged
2. Game enters retreat phase
3. Click dislodged unit's territory
4. Click valid retreat destination
5. Submit retreat order
6. Verify it works correctly

**Expected Results**:
- Dislodged units properly detected
- Retreat destinations are valid
- Retreat orders submitted successfully

---

### Test 8: Build/Remove Phase

**Objective**: Test order selection during adjustment phase

**Steps**:
1. Play until adjustment phase
2. If units need building:
   - Click supply center
   - Build order should appear
   - Submit build order
3. If units need removing:
   - Click unit location
   - Remove order should appear
   - Submit remove order

**Expected Results**:
- Build options appear only for supply centers you own
- Remove options appear for your units
- Appropriate orders auto-detected
- Orders submit successfully

---

### Test 9: Error Cases

**Objective**: Test error handling for invalid selections

**Steps**:
1. Try to click territory before selecting power
   - Should see error: "Select a power first"
2. Select enemy territory as unit
   - Should see error: "has no units for [power]"
3. Try invalid move (to non-adjacent territory)
   - Should see error: "No valid orders from X to Y"

**Expected Results**:
- All error messages clear and helpful
- System handles all edge cases gracefully
- No crashes or console errors

---

### Test 10: Multiple Orders in Sequence

**Objective**: Test submitting multiple orders for different units

**Steps**:
1. Select power
2. Submit first order using map picker
3. Submit second order using map picker
4. Submit third order using dropdown only
5. Check all appear in queued orders

**Expected Results**:
- Multiple orders all queue correctly
- Mix of map and dropdown input works
- Clear selection resets properly after each submission

---

## Responsive Design Testing

### Desktop (1920x1080)
- Sidebar on right
- Full map visible
- Large territory click areas
- All text readable

### Tablet (768px)
- Sidebar takes full width when open
- Map visible when sidebar closed
- Touch-friendly territory sizes
- Text remains readable

### Mobile (375px)
- Sidebar takes full screen
- Toggle button visible
- Touch targets appropriately sized
- No horizontal scrolling
- Status message clear

## Browser Testing Checklist

- [ ] Chrome/Edge (Windows)
- [ ] Firefox (Windows)
- [ ] Safari (macOS if available)
- [ ] Chrome Mobile (Android)
- [ ] Safari Mobile (iOS)
- [ ] Firefox Mobile (Android)

## Console Checking

While testing, open Developer Console (F12) and check:
1. No JavaScript errors in Console tab
2. No warnings about missing resources
3. Network tab shows all files loaded successfully
4. SVG click events firing (can add debug logs)

## Performance Testing

1. **Map Load Time**: Should be < 2 seconds
2. **Click Response**: Should be instantaneous (< 100ms)
3. **Highlighting**: Should update smoothly
4. **Dialog Render**: Should appear < 500ms

## Accessibility Testing

1. **Keyboard Navigation**:
   - Tab through all controls
   - Dropdowns should work with keyboard
   - Space/Enter should activate buttons

2. **Screen Reader**:
   - Territory names should be readable
   - Order selections should be announced
   - Status messages should be heard

3. **Color Contrast**:
   - Gold and red highlighting should be distinct
   - Can work without color (patterns or different hues)

## Known Limitations to Test

1. Dislodged unit selection only works after retreat phase starts
2. Multiple unit types in same territory may be visually overlapping
3. Very small territories on map may be hard to click on mobile
4. Convoy route visualization shows end points only

## Reporting Issues

When reporting a bug, include:
- Browser and version
- Device type (desktop/mobile)
- Steps to reproduce
- Expected vs actual behavior
- Console error messages
- Screenshot or screen recording

## Success Criteria

The interactive map order picker is working correctly when:
- ✅ All click interactions work as expected
- ✅ Territories highlight in correct colors
- ✅ Orders auto-suggest intelligently
- ✅ Dropdowns sync with map selection
- ✅ Mobile interaction is smooth and responsive
- ✅ All error cases handled gracefully
- ✅ No console errors
- ✅ Responsive design works on all screen sizes

