# Radial Menu Troubleshooting Checklist

## Pre-Testing Checklist

Before testing, make sure:

- [ ] Backend server running: `python server.py` (should show "Running on http://127.0.0.1:8001")
- [ ] Browser opened to: `http://localhost:8001/docs/singleplayer.html`
- [ ] DevTools open: Press `F12`
- [ ] On Console tab
- [ ] **No red error messages** in console (look at top)

## Testing the Radial Menu

### Test 1: Correct Game Phase

**Requirement:** Radial menu only appears in Spring or Fall phases
- [ ] Game is in **Spring** or **Fall** phase (check status at top of screen)
- [ ] NOT in Adjustment phase
- [ ] NOT in Retreat phase

**If wrong phase:**
- Load a different game or wait for the correct phase
- Menu won't appear in Adjustment or Retreat phases (by design)

### Test 2: Click on YOUR Unit

**Requirement:** Must click on a unit you own
- [ ] Click on a **small unit icon** (not the territory background)
- [ ] Make sure the unit is **your color** (same as your power)
- [ ] The unit should have a **clear marker** (F or A)

**If clicking on wrong element:**
- Territory: Won't show menu (need to click unit)
- Opponent's unit: Won't show menu (ownership check fails)

### Test 3: Run Diagnostic

In browser console, paste and run `DIAGNOSTIC.js`:

```javascript
// Copy DIAGNOSTIC.js contents and paste in console
```

**Look for issues marked with ✗**

### Test 4: Check Console Output

With DevTools open, click on one of your units:

**You should see messages like:**
```
[RadialMenu] Click detected {
  phase: "Spring",
  hasUnit: true,
  ...
}
[RadialMenu] Showing menu for unit LON
[RadialMenu] Unit data found: {...}
[RadialMenu] Menu rendered, group children count: 6
```

**If you DON'T see these messages:**
- Click handler not firing
- Check that click target is the unit element
- Verify phase is Spring or Fall

### Test 5: Verify Menu Visibility

If console shows menu rendered but nothing visible:

**Run in console:**
```javascript
// Check if menu group exists
const menuGroup = document.getElementById('radial-menu');
console.log('Menu exists:', !!menuGroup);

// Check if it has children
if (menuGroup) {
  console.log('Menu items:', menuGroup.children.length);
  // Should be 6 (5 options + 1 center)
}
```

### Test 6: Test SVG Rendering

**Run in console:**
```javascript
// Try adding a test element
const test = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
test.setAttribute('cx', 200);
test.setAttribute('cy', 200);
test.setAttribute('r', 20);
test.setAttribute('fill', 'yellow');
test.setAttribute('id', 'test-circle');
svg.appendChild(test);
```

**Expected:** A yellow circle appears on the map
- **If yes:** SVG rendering works
- **If no:** SVG not loading or `svg` variable not set

## Common Issues and Fixes

### Issue: "No console messages at all"

**Problem:** Click handler not running
**Possible Causes:**
1. Clicking on wrong element (territory instead of unit)
2. Wrong phase (need Spring or Fall)
3. Script not loaded

**Fix:**
```javascript
// In console, check:
console.log('Handler function exists:', typeof handleMapClickWithRadialMenu);
console.log('SVG click listener attached:', !!svg);
```

---

### Issue: "Click detected, but 'Unit data found' doesn't appear"

**Problem:** Unit matching failed
**Possible Causes:**
1. Unit dataset missing or incorrect
2. State units not populated
3. Unit ownership mismatch

**Fix:**
```javascript
// In console:
const clickedUnit = document.querySelector('.unit'); // First unit on map
console.log('Unit dataset:', clickedUnit?.dataset);
console.log('State units:', window.diplomacy.state.units);
// Compare to see if unit exists in state
```

---

### Issue: "Menu rendered, but nothing visible on map"

**Problem:** Menu elements created but not showing
**Possible Causes:**
1. Menu positioned off-screen
2. SVG transform issue
3. CSS hiding menu

**Fix:**
```javascript
// In console:
const menuGroup = document.getElementById('radial-menu');
if (menuGroup) {
  // Check position
  console.log('Menu transform:', menuGroup.getAttribute('transform'));
  console.log('Menu children:', menuGroup.children.length);
  
  // Force visibility
  menuGroup.style.display = 'block';
  menuGroup.style.visibility = 'visible';
  
  // Check first child (menu item)
  if (menuGroup.children[0]) {
    console.log('First item:', menuGroup.children[0].getAttribute('data-type'));
  }
}
```

---

### Issue: "TypeError: Cannot read property 'appendChild' of null"

**Problem:** `menuGroup` is null
**Fix:**
1. Check that `radialMenu.initialize()` was called
2. Verify SVG element exists
3. Reload page

```javascript
// In console:
console.log('radialMenu:', radialMenu);
console.log('radialMenu.menuGroup:', radialMenu?.menuGroup);
console.log('svg:', svg);
```

---

### Issue: "Script errors in console"

**Example errors:**
- "SVG_NS is not defined" → Script loading order wrong
- "RadialMenu is not defined" → radial-menu.js didn't load
- "Cannot find element" → SVG not created yet

**Fix:**
1. Reload page (Ctrl+R or Cmd+R)
2. Check Network tab → all scripts should load with 200 status
3. Check script loading order in singleplayer.html

---

## Script Loading Order Check

**In browser console:**
```javascript
// These should all be true
console.log('shared.js loaded:', typeof SVG_NS !== 'undefined');
console.log('radial-menu.js loaded:', typeof RadialMenu !== 'undefined');
console.log('singleplayer.js loaded:', typeof buildMap === 'function');
```

**Expected output:**
```
shared.js loaded: true
radial-menu.js loaded: true
singleplayer.js loaded: true
```

---

## Testing Checklist

After making changes or before testing:

- [ ] Backend running (python server.py)
- [ ] No JavaScript errors in console
- [ ] All scripts loaded (SVG_NS, RadialMenu, etc.)
- [ ] Game loaded (state shows units)
- [ ] In Spring or Fall phase
- [ ] Diagnostic runs without ✗ errors
- [ ] Can click on unit and see [RadialMenu] messages
- [ ] Menu renders (console shows "group children count: 6")

---

## Debug Commands Reference

**Copy and paste any of these into console:**

```javascript
// Check all prerequisites
console.clear();
console.log('SVG_NS:', SVG_NS);
console.log('RadialMenu:', RadialMenu);
console.log('radialMenu:', radialMenu);
console.log('svg:', svg);
console.log('mapData:', mapData.territories.length + ' territories');
console.log('Game phase:', window.diplomacy.state.phase);
console.log('Player units:', window.diplomacy.state.units.filter(u => u.owner === window.diplomacy.state.player_power));

// Check if menu exists
const menu = document.getElementById('radial-menu');
console.log('Menu group:', menu);
if (menu) console.log('Menu children:', menu.children.length);

// Test manual menu creation
radialMenu.showForUnit(
  {type: 'F', territory: 'LON'},
  'LON',
  {x: 500, y: 400},
  window.availableOrders,
  window.diplomacy.state,
  'England'
);
```

---

## Still Not Working?

If you've gone through all these steps and the menu still doesn't appear:

1. **Take a screenshot** of:
   - The game screen
   - The console output (full page scroll)

2. **Copy the diagnostic output:**
   ```javascript
   // Run this in console and screenshot
   // [Run contents of DIAGNOSTIC.js]
   ```

3. **Save the browser console to file:**
   - Right-click console → Save as... → console-output.txt

4. **Check file permissions:**
   - Make sure `docs/radial-menu.js` exists and has read permission

5. **Try clearing cache:**
   - Ctrl+Shift+Delete (or Cmd+Shift+Delete on Mac)
   - Clear all browser data
   - Reload page

---

## Expected Behavior

When everything works:

1. **Phase:** Spring or Fall
2. **Action:** Click on YOUR unit
3. **Result:** Circular menu appears at unit location with 5 options
4. **Options:** Hold (green), Advance (blue), Support (orange), Transform (purple), Convoy (red)
5. **Next:** Click one of the colored options to select order

---

## Questions to Ask Yourself

- [ ] Did I actually click on a **unit** and not empty space?
- [ ] Is my unit the same **color/ownership** as my power?
- [ ] Am I in **Spring** or **Fall** phase?
- [ ] Does the console show **[RadialMenu] Click detected**?
- [ ] Are there any **red error messages** in console?
- [ ] Did I reload the page after making changes?
- [ ] Is the backend **actually running** (python server.py)?

If you can answer YES to all these, the menu should appear!
