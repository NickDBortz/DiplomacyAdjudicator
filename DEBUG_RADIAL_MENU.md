# Debugging Radial Menu - Not Appearing

If the radial menu doesn't pop up when clicking on a unit, follow these debugging steps:

## Quick Diagnostic (Start Here!)

1. Open the game page: `http://localhost:8001/docs/singleplayer.html`
2. Press `F12` to open DevTools
3. Go to **Console** tab
4. Copy the content from `DIAGNOSTIC.js` and paste it into the console
5. Press Enter

This will run a comprehensive check and tell you exactly what's wrong:

```javascript
// Or paste the diagnostic directly:
[Paste contents of DIAGNOSTIC.js file into console]
```

The diagnostic will check:
- ✓ All scripts loaded (SVG_NS, RadialMenu, etc.)
- ✓ Game state available
- ✓ Units on map
- ✓ Available orders
- ✓ SVG rendering
- ✓ Current phase
- And more...

---

## Manual Debugging Steps

If the diagnostic shows all green, but menu still doesn't appear:

### Step 1: Check Console Messages

With the console open, try clicking on one of your units in Spring/Fall phase:

Look for console output starting with `[RadialMenu]`. You should see something like:

```
[RadialMenu] Click detected {
  phase: "Spring",
  hasUnit: true,
  hasTerritory: false,
  unitTerritory: "LON",
  power: "England",
  availableOrdersCount: 6
}
[RadialMenu] Showing menu for unit LON
[RadialMenu] Unit data found: {territory: 'LON', owner: 'England', type: 'F', coast: 'sc'}
[RadialMenu] Position calculated: {x: 450, y: 320}
[RadialMenu] Initializing menu
[RadialMenu] Showing menu for unit
[RadialMenu] showForUnit called {unit: {...}, territory: 'LON', position: {...}}
[RadialMenu] Looking for orders matching unitStr: F LON
[RadialMenu] Checking order: {order: {...}, orderDetails: {...}}
[RadialMenu] Available types found: ['Hold', 'Advance', ...]
[RadialMenu] Rendering menu with available types: ['Hold', 'Advance', ...]
[RadialMenu] Creating item Hold at (450, 240), available=true
[RadialMenu] Creating item Advance at (520, 350), available=true
[RadialMenu] Creating item Support at (450, 460), available=true
[RadialMenu] Creating item Transform at (380, 350), available=false
[RadialMenu] Creating item Convoy at (450, 240), available=true
[RadialMenu] Menu rendered, group children count: 6
```

## Step 3: Troubleshooting Based on Output

### Case 1: No console output at all
- **Problem:** Click handler not firing
- **Solution:** 
  - Check that you're clicking on a UNIT (small icon), not a territory
  - Make sure you're in Spring or Fall phase (not Adjustment or Retreat)
  - Check that it's YOUR unit (same color as your power)

### Case 2: "Click detected" but "Showing menu for unit" doesn't appear
- **Problem:** Unit data not matching or not owned by player
- **Check:** 
  ```javascript
  // In console, run:
  console.log(window.diplomacy.state.units);
  // Look for your unit in the list
  ```

### Case 3: "Showing menu" but "Available types found" is empty
- **Problem:** No available orders matching the unit
- **Check:**
  ```javascript
  // In console, run:
  window.availableOrders.forEach(o => console.log(o));
  // Look for orders for your unit
  ```

### Case 4: "Menu rendered" but nothing visible
- **Problem:** Menu group might exist but is off-screen or invisible
- **Check:**
  ```javascript
  // In console, run:
  document.getElementById('radial-menu');
  // Should return the menu group element
  // If it exists, check its transform or position
  ```

## Step 4: Verify Key Variables

In the browser console, you can check:

```javascript
// Check if radial menu initialized
console.log('radialMenu:', radialMenu);

// Check if SVG exists
console.log('svg:', svg);

// Check if map data loaded
console.log('mapData:', mapData.territories.length);

// Check game state
console.log('Game state:', window.diplomacy.state);

// Check available orders
console.log('Available orders:', availableOrders);
```

## Step 5: Check Network Requests

1. Go to **Network** tab in DevTools
2. Look for any failed requests (red)
3. Specifically check:
   - `radial-menu.js` - Should load successfully
   - `shared.js` - Should load successfully
   - Game state API calls - Should return 200 OK

## Step 6: Check for JavaScript Errors

In the console, look for any error messages (shown in red):

### Common Errors:

**"SVG_NS is not defined"**
- `radial-menu.js` loaded before `shared.js`
- Check script loading order in HTML

**"Cannot read property 'appendChild' of null"**
- `menuGroup` is null
- Menu not initialized properly

**"radialMenu is not defined"**
- This shouldn't happen with the new fix
- Clear browser cache and reload

## Step 7: Manual Menu Creation Test

Try this in the console to manually test menu creation:

```javascript
// Make sure both are loaded
console.log('SVG_NS exists:', typeof SVG_NS);
console.log('RadialMenu class exists:', typeof RadialMenu);
console.log('radialMenu instance exists:', !!radialMenu);

// Test creating a menu item manually
if (svg && radialMenu) {
  const testMenu = document.createElementNS(SVG_NS, 'circle');
  testMenu.setAttribute('cx', 300);
  testMenu.setAttribute('cy', 300);
  testMenu.setAttribute('r', 30);
  testMenu.setAttribute('fill', 'red');
  svg.appendChild(testMenu);
  console.log('✓ Test circle added to SVG');
  // You should see a red circle appear on the map
  // If you see it, SVG rendering works
}
```

## Step 8: Check CSS

The menu might be rendered but hidden by CSS:

```javascript
// In console, check the menu group styling
const menuGroup = document.getElementById('radial-menu');
if (menuGroup) {
  console.log('Menu group computed style:', getComputedStyle(menuGroup));
  console.log('Menu group visibility:', menuGroup.style.display, menuGroup.style.visibility);
}
```

## Step 9: Force Menu to Appear

If debugging confirms the menu is rendering but not visible, try forcing it to show:

```javascript
// In console:
const menuGroup = document.getElementById('radial-menu');
if (menuGroup) {
  menuGroup.style.display = 'block';
  menuGroup.style.visibility = 'visible';
  menuGroup.style.pointerEvents = 'auto';
}
```

## Step 10: Check SVG Viewport

Make sure the SVG has proper viewBox:

```javascript
console.log('SVG viewBox:', svg.getAttribute('viewBox'));
console.log('SVG width:', svg.getAttribute('width'));
console.log('SVG height:', svg.getAttribute('height'));
```

## Reporting Issues

If you've followed all steps and still have issues, please provide:

1. **Browser console output** - Copy all `[RadialMenu]` messages
2. **Game state** - Output of `window.diplomacy.state`
3. **Available orders** - Output of `window.availableOrders`
4. **Phase** - What phase are you in?
5. **Unit** - Which unit did you click on?
6. **Browser** - Chrome/Firefox/Safari + version

---

## Quick Summary Checklist

- [ ] Opened DevTools (F12)
- [ ] See `[RadialMenu]` console messages
- [ ] Spring or Fall phase (not Adjustment/Retreat)
- [ ] Clicking on YOUR unit (check color/ownership)
- [ ] No JavaScript errors in console
- [ ] radialMenu, svg, mapData all defined
- [ ] SVG_NS defined (from shared.js)
- [ ] Script loading order: shared.js → radial-menu.js → singleplayer.js
