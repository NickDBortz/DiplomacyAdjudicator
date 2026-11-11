# Radial Menu System - Testing Guide

## Quick Start

### Automated Tests (Recommended)
```bash
node tests/run-tests.js
```
Expected output: **21 passed, 0 failed**

---

## Manual Browser Testing

### Prerequisites
1. Backend server running: `python server.py` (should be on localhost:8001)
2. Open browser to: `http://localhost:8001/docs/singleplayer.html`
3. Open browser DevTools (F12) to watch for errors

### Test Cases

#### **Adjustment Phase Tests** (Spring Adjustment or Fall Adjustment)

##### Test 1: Auto-submit Build Order
1. Create a new game or load one in Adjustment phase
2. Click on an unoccupied supply center
3. **Expected:** Order automatically submits without requiring button click
4. **Verify:** Status shows order was submitted

##### Test 2: Auto-submit Disband Order
1. In Adjustment phase with excess units
2. Click on one of your own units
3. **Expected:** Unit automatically disbands without requiring button click
4. **Verify:** Status shows unit was removed

---

#### **Spring/Fall Phase Tests**

##### Test 3: Radial Menu Appears
1. Load a Spring or Fall phase game
2. Click on one of your units
3. **Expected:** Circular radial menu appears with 5 options:
   - Hold (Green)
   - Advance (Blue)
   - Support (Orange)
   - Transform (Purple)
   - Convoy (Red)
4. **Verify:** Menu is positioned at unit location

##### Test 4: Hold Order
1. Radial menu open (from Test 3)
2. Click "Hold" option
3. **Expected:** Order submits immediately, unit highlighted with blue circle
4. **Verify:** Status shows "Order selected: [Unit] H"

##### Test 5: Advance Order with Territory Highlighting
1. Radial menu open
2. Click "Advance" option
3. **Expected:** Adjacent territories light up with green highlight
4. **Verify:** Only adjacent territories are highlighted
5. Click a highlighted territory
6. **Expected:** Order submits, unit and destination shown with arrow

##### Test 6: Support Hold Order
1. Radial menu open
2. Click "Support" option
3. **Expected:** Adjacent units light up for hold support selection
4. Click an adjacent unit to support
5. **Expected:** Order submits, support shown with line connection

##### Test 7: Support Advance Order (Multi-step)
1. Radial menu open
2. Click "Support" option
3. Click on an adjacent unit that can advance
4. **Expected:** Menu switches to show advance destination territories
5. Click a destination territory
6. **Expected:** Order submits (Support Advance)

##### Test 8: Transform Order
1. Radial menu open
2. Click "Transform" option
3. **Expected:** Order submits immediately (same as Hold)
4. **Verify:** Status shows transform order

##### Test 9: Convoy Order (Multi-step)
1. Radial menu open on a fleet
2. Click "Convoy" option
3. **Expected:** Adjacent armies highlight
4. Click an army to convoy
5. **Expected:** Army's adjacent territories highlight
6. Click a destination territory
7. **Expected:** Order submits with convoy notation

##### Test 10: Grayed Out Options
1. Open radial menu on a Fleet unit
2. **Expected:** Some options may be unavailable (e.g., Convoy may not apply)
3. Unavailable options should appear grayed out or disabled
4. **Verify:** Cannot click invalid options

---

#### **Retreat Phase Tests**

##### Test 11: Retreat Highlighting
1. Load a game with dislodged units (Retreat phase)
2. Click on a dislodged unit
3. **Expected:** Adjacent territories highlight (gold color)
4. Only non-convoy advance destinations show
5. **Verify:** No radial menu appears (simpler interface)

##### Test 12: Retreat Selection
1. Retreat highlighting active (from Test 11)
2. Click a highlighted territory
3. **Expected:** Unit retreats to selected territory
4. **Verify:** Dislodged unit is no longer shown

---

## Error Scenarios

### Test 13: No Menu Variable Defined
1. Artificially break `radial-menu.js` loading
2. Try to click a unit in Spring phase
3. **Expected:** Falls back to dropdown interface (no crash)
4. **Verify:** No JavaScript errors in console

### Test 14: Invalid Territory Click
1. In Spring phase, click on a territory with no valid destination
2. **Expected:** Status message "No matching order for that territory"
3. **Verify:** Order not submitted

### Test 15: Multiple Matching Orders
1. In Spring phase, select unit with multiple move options
2. Click on a territory that matches multiple orders
3. **Expected:** Status shows "X matching orders. Select an order or tap the next territory."
4. **Verify:** Must use dropdown to disambiguate

---

## Console Verification

### Expected Console Behavior
- No JavaScript errors when loading
- No ReferenceError for `radialMenu`
- No error when clicking territories in any phase

### Check Console
1. Open DevTools (F12)
2. Go to Console tab
3. Perform all test cases above
4. **Expected:** No red error messages

### Debugging
If errors appear:
```javascript
// Check if radial menu is loaded
console.log(typeof radialMenu); // Should be 'object', not 'undefined'

// Check if SVG created
console.log(document.querySelector('svg')); // Should return SVG element

// Check game state
console.log(window.diplomacy.state); // Should show game state
```

---

## Performance Tests

### Test 16: Menu Responsiveness
1. Open radial menu
2. **Expected:** Menu appears within 100ms
3. **Verify:** No lag or jank

### Test 17: Multiple Selections
1. Click multiple units and territories rapidly
2. **Expected:** System handles input without errors
3. **Verify:** Selections correctly tracked

### Test 18: Large Map
1. Load classic map with many territories
2. **Expected:** All highlighting works smoothly
3. **Verify:** No performance degradation

---

## Browser Compatibility

Test with:
- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)

### Expected Support
- All modern browsers supporting ES6 and SVG
- Touch support for mobile/tablet

---

## Known Limitations

1. **Adjustment Phase Auto-submit:**
   - Only submits if exactly one order matches
   - Multiple matching orders still require dropdown selection

2. **Radial Menu:**
   - Requires JavaScript enabled
   - SVG must load properly
   - Menu position calculated from viewport (may need adjustment for unusual layouts)

3. **Retreat Phase:**
   - No radial menu (simplified UI)
   - Only retreat (non-convoy) moves allowed

---

## Checklist for Production

- [ ] All 21 automated tests passing
- [ ] Manual browser testing completed
- [ ] Console clean (no errors)
- [ ] Adjustment phase auto-submit working
- [ ] All order types tested (Hold, Advance, Support, Transform, Convoy)
- [ ] Retreat highlighting working
- [ ] Menu positioning correct on different map sizes
- [ ] Performance acceptable
- [ ] Cross-browser compatibility verified
- [ ] Touch input tested (if applicable)

---

## Support

If tests fail:
1. Check that all files are present:
   - `docs/radial-menu.js`
   - `docs/shared.js` (modified)
   - `tests/run-tests.js`
   - `tests/radial-menu.test.js`

2. Verify script loading order in `singleplayer.html`:
   - shared.js
   - radial-menu.js
   - singleplayer.js

3. Run automated tests first: `node tests/run-tests.js`

4. Check browser console for errors (F12)

5. Verify backend server is running on localhost:8001
