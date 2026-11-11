# 🎯 MASTER RADIAL MENU CHECKLIST

## Pre-Testing Setup

- [ ] Backend running: `python server.py`
- [ ] No errors in backend startup
- [ ] Game opens without errors
- [ ] Browser console clear (F12)
- [ ] Game is in **Spring** or **Fall** phase (NOT Adjustment)

## Testing Steps

### Step 1: Verify System Is Ready
```javascript
// Run in console
console.log({
  'radialMenu': typeof radialMenu,
  'phase': window.diplomacy?.state?.phase,
  'svg': !!document.querySelector('svg'),
  'orders': availableOrders?.length || 0
});
```

**Expected**: 
- `radialMenu: "object"` or `"object"` (after first click)
- `phase: "Spring"` or `"Fall"`
- `svg: true`
- `orders: > 0`

### Step 2: Click on Your Unit
1. Identify a unit that's yours (correct color)
2. Click directly on the unit symbol
3. **Watch browser console** for `[RadialMenu]` messages
4. **Watch game map** for radial menu appearance

### Step 3: Verify Menu Behavior
- [ ] Menu appears near clicked unit
- [ ] Menu has 5 circular options (Hold, Advance, Support, Transform, Convoy)
- [ ] Some options are highlighted (available) 
- [ ] Some options are grayed out (unavailable)
- [ ] Hovering over options highlights them more
- [ ] Clicking an option selects that order

## Troubleshooting Decision Tree

### Q1: Does console show `[RadialMenu]` messages?

**NO** → Click handler not running
- [ ] Make sure you're in Spring/Fall phase
- [ ] Make sure you clicked ON the unit, not near it
- [ ] Try clicking a different unit
- [ ] Try refreshing page

**YES** → Go to Q2

### Q2: Does console show `[RadialMenu] Unit data found`?

**NO** → Unit lookup failed
- [ ] Make sure unit is yours (check unit color)
- [ ] Unit data: `console.log(state.units.find(u => u.territory === 'TERRITORY_NAME'))`
- [ ] Try a different unit

**YES** → Go to Q3

### Q3: Does console show `[RadialMenu] Showing menu for unit`?

**NO** → showForUnit() wasn't called
- [ ] Check previous console output for errors
- [ ] Try: `initRadialMenu(document.querySelector('svg'))`
- [ ] Refresh page

**YES** → Go to Q4

### Q4: Does menu appear on the map?

**NO** → Menu was created but not visible
- [ ] Check menu group exists: `document.getElementById('radial-menu')`
- [ ] Check CSS applied: 
  ```javascript
  const menu = document.getElementById('radial-menu');
  console.log({
    'exists': !!menu,
    'children': menu?.children.length,
    'display': menu?.style.display,
    'opacity': menu?.style.opacity
  });
  ```
- [ ] Make visible: `document.getElementById('radial-menu').style.display = 'block'`

**YES** → Go to Q5

### Q5: Are menu items clickable?

**NO** → Event handlers not working
- [ ] Check pointer-events CSS
- [ ] Try clicking center circle
- [ ] Check console for click errors

**YES** → Menu is working! ✅

## Common Issues & Solutions

| Symptom | Cause | Solution |
|---------|-------|----------|
| "No [RadialMenu] in console" | Phase wrong | Verify phase is Spring/Fall |
| "No [RadialMenu] in console" | Clicked terrain | Click unit symbol directly |
| "Menu group missing" | Init failed | Manual: `initRadialMenu(svg)` |
| "Menu appears off-screen" | SVG transform | Check zoom = 100% |
| "Menu items all gray" | No orders | Try different unit |
| "Can't click menu items" | CSS issue | Check `pointer-events: auto` |
| "Menu won't close" | Normal | Click elsewhere on map |
| "radialMenu undefined" | Script not loaded | Refresh page |

## Console Commands Reference

```javascript
// Check if everything is loaded
console.log('Loaded:', {
  radialMenu: typeof radialMenu,
  initRadialMenu: typeof initRadialMenu,
  svg: !!document.querySelector('svg')
});

// Check game state
const state = window.diplomacy.state;
console.log('State:', {
  phase: state.phase,
  player: state.player_power,
  units: state.units.length
});

// Check available orders
console.log('Orders:', availableOrders.length, availableOrders);

// Check menu group
const menu = document.getElementById('radial-menu');
console.log('Menu:', {
  exists: !!menu,
  children: menu?.children.length,
  visible: menu?.style.display !== 'none'
});

// Force menu visibility
const menu = document.getElementById('radial-menu');
if (menu) {
  menu.style.display = 'block';
  menu.style.opacity = '1';
  menu.style.pointerEvents = 'auto';
}

// Get all [RadialMenu] messages from console
// Filter: type [RadialMenu] in console filter box
```

## Testing Sequence

1. **Start Backend**
   ```bash
   python server.py
   ```
   Wait for "Server running on http://localhost:8001"

2. **Load Game**
   - Open http://localhost:8001/docs/singleplayer.html
   - Wait for map to load (3-5 seconds)

3. **Verify Phase**
   ```javascript
   window.diplomacy.state.phase  // Should be "Spring" or "Fall"
   ```

4. **Click Unit and Observe**
   - Click YOUR unit (your color)
   - Watch console for `[RadialMenu]` messages
   - Watch map for menu appearance

5. **Test Menu Interaction**
   - Hover over menu items
   - Click a menu item
   - Verify order is selected

## Success Criteria

✅ **All of these must be true:**
1. Console shows `[RadialMenu]` messages when clicking unit
2. Menu appears on map within 1 second of click
3. Menu has 5 circular options
4. Some options are highlighted (available)
5. Hover changes option appearance
6. Clicking option selects the order
7. Menu disappears after selection

## If Still Stuck

1. Copy **all console output** from a test click
2. Note **which unit you clicked**
3. Share **screenshot** of map with expected menu location
4. Run and share output of **diagnostic** (see above)
5. Check **QUICK_TEST_CHECKLIST.md** for more detailed steps
6. Review **RADIAL_MENU_SYSTEM_GUIDE.md** for technical details

## Files to Reference

- `QUICK_REFERENCE.md` - 1-minute overview
- `FIX_SUMMARY.md` - What was fixed
- `QUICK_TEST_CHECKLIST.md` - Detailed console steps
- `RADIAL_MENU_SYSTEM_GUIDE.md` - Complete technical guide

---

**Last Updated**: After all CSS and initialization fixes  
**Status**: ✅ READY FOR TESTING
