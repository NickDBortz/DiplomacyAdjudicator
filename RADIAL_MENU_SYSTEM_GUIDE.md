# 🚀 Radial Menu System - Complete Setup & Debugging Guide

## What Was Fixed

### 1. **CSS Styling** ✅
- Added complete CSS for radial menu elements in `docs/style.css`
- Menu group, items, and icons now properly styled
- Hover effects and pointer events configured
- All visual elements have proper transitions

### 2. **Click Handler Initialization** ✅
- Modified `handleMapClickWithRadialMenu()` to auto-initialize menu on first click
- Click handler now safely checks for and initializes radial menu if needed
- Works in Spring/Fall and Retreat phases

### 3. **Phase Detection** ✅
- Improved phase checking to handle both exact matches and partial matches
- `Spring`, `Fall`, `Spring Retreat`, `Fall Retreat` all detected correctly

### 4. **Console Logging** ✅
- Added comprehensive logging at every step
- All messages prefixed with `[RadialMenu]` for easy filtering
- Helps identify exactly where the flow stops

---

## Files Modified

| File | Changes |
|------|---------|
| `docs/shared.js` | Added auto-initialization in SVG click handler; improved phase detection |
| `docs/radial-menu.js` | Added logging to `initialize()` function |
| `docs/style.css` | Added complete CSS for radial menu styling |

---

## Files Created for Testing

| File | Purpose |
|------|---------|
| `QUICK_TEST_CHECKLIST.md` | Step-by-step checklist with console commands |
| `TEST_RADIAL_MENU_SIMPLE.html` | Standalone test (no backend needed) |
| `RADIAL_MENU_TEST.html` | Full game integration test |

---

## How to Test

### Option 1: Quick Visual Test (Recommended)

1. **Start backend**: `python server.py`
2. **Open game**: http://localhost:8001/docs/singleplayer.html
3. **Wait for game to load** in Spring or Fall phase
4. **Open browser console**: F12 → Console
5. **Click on your unit** (should be your color)
6. **Watch for:**
   - Console messages starting with `[RadialMenu]`
   - Radial menu appearing near clicked unit
   - Menu items highlighted on hover

### Option 2: Console Verification (if menu doesn't appear)

Run in console after clicking a unit:
```javascript
console.log('1. Menu group exists:', !!document.getElementById('radial-menu'));
console.log('2. Menu items:', document.querySelectorAll('.radial-menu-item').length);
console.log('3. Available orders:', availableOrders.length);
console.log('4. Current phase:', window.diplomacy.state.phase);
console.log('5. Player units:', window.diplomacy.state.units.filter(u => u.owner === window.diplomacy.state.player_power).length);
```

### Option 3: Standalone Component Test

Open `TEST_RADIAL_MENU_SIMPLE.html` in browser (no backend needed):
1. Click "Create Test SVG"
2. Click "Initialize Menu"
3. Click "Show Menu (Test)"
4. See working menu in isolation

---

## Expected Behavior by Phase

### Spring/Fall Phases
✅ Click on **your unit** → Radial menu appears
✅ Hover menu items → Items highlight
✅ Click menu item → Order selected

### Adjustment Phase
✅ Click on **supply center** → Order auto-submits (no menu)
✅ Click on **your unit** → Order auto-submits (disband or build)

### Retreat Phase
✅ Click on **adjacent territory** → Retreat order auto-submitted

---

## Console Output Examples

### Successful Flow
```
[RadialMenu] Click detected {phase: "Spring", hasUnit: true, ...}
[RadialMenu] Unit data found: {type: "Army", territory: "London", owner: "England"}
[RadialMenu] Showing menu for unit
[RadialMenu] showForUnit called {unit: {...}, territory: "London", position: {x: 250, y: 150}}
[RadialMenu] Available types found: Set(3) {'Hold', 'Advance', 'Support'}
[RadialMenu] Rendering menu with available types: ['Hold', 'Advance', 'Support']
[RadialMenu] Creating item Hold at (250, 80), available=true
[RadialMenu] Creating item Advance at (320, 120), available=true
[RadialMenu] Creating item Support at (180, 120), available=true
[RadialMenu] Creating item Transform at (250, 220), available=false
[RadialMenu] Creating item Convoy at (250, 220), available=false
[RadialMenu] Menu rendered, group children count: 8
```

### If Menu Doesn't Appear

Check these messages in order:

1. **No `[RadialMenu] Click detected`?**
   - Click handler isn't firing
   - Solution: Make sure you're clicking ON the unit, not next to it

2. **No `[RadialMenu] Unit data found`?**
   - Unit lookup failed
   - Solution: Verify you clicked on your own unit (correct color)

3. **No `[RadialMenu] Showing menu`?**
   - showForUnit() wasn't called
   - Solution: Check previous error messages

4. **`availableOrders` is empty?**
   - No valid orders for this unit
   - Solution: Try a different unit or phase

5. **Menu items show count 0?**
   - Menu group exists but no items rendered
   - Solution: Check if `menuGroup.innerHTML` was cleared properly

---

## Troubleshooting

### Menu appears but items are grayed out
- **Cause**: No available orders for this unit
- **Fix**: Try clicking on a different unit, or ensure it's Spring/Fall phase

### Menu appears far from clicked unit
- **Cause**: SVG coordinate transformation issue
- **Fix**: Check browser zoom level (should be 100%), or check SVG transform attribute
- **Debug**: Log position: `console.log('Position:', {x: 250, y: 150})`

### Menu doesn't close after clicking item
- **Cause**: Click handler didn't clear menu visibility
- **Fix**: Manually close: `document.getElementById('radial-menu').innerHTML = ''`

### "radialMenu is not defined" error
- **Cause**: radial-menu.js script didn't load
- **Fix**: 
  1. Refresh page
  2. Check Network tab (F12) to see if script loaded
  3. Check if script is included in HTML: `<script src="radial-menu.js"></script>`

### Menu appears but clicking does nothing
- **Cause**: Event handlers not attached to menu items
- **Fix**: Check CSS `pointer-events` settings
- **Debug**: Try clicking center circle, see if console logs

---

## Key Code Locations

### Click Handler Setup
📍 `docs/shared.js:1071-1098` - SVG addEventListener with auto-initialization

### Menu Initialization
📍 `docs/radial-menu.js:52-60` - RadialMenu.initialize()

### Menu Display
📍 `docs/radial-menu.js:118-158` - RadialMenu.renderMenu()

### Item Creation
📍 `docs/radial-menu.js:161-210` - RadialMenu.createMenuItem()

### CSS Styling
📍 `docs/style.css:1373-1397` - Radial menu CSS rules

---

## Next Steps if Menu Still Doesn't Appear

1. **Copy all `[RadialMenu]` console messages** from a click attempt
2. **Take screenshot** showing:
   - Which unit you clicked on
   - Expected menu location
   - Any error messages
3. **Run diagnostic** in console:
   ```javascript
   console.log('DIAGNOSTIC:');
   console.log('SVG exists:', !!document.querySelector('svg'));
   console.log('Menu group exists:', !!document.getElementById('radial-menu'));
   console.log('radialMenu object:', typeof radialMenu, radialMenu ? 'initialized' : 'null');
   console.log('initRadialMenu function:', typeof initRadialMenu);
   console.log('Game phase:', window.diplomacy.state?.phase);
   console.log('Player power:', window.diplomacy.state?.player_power);
   ```

---

**Status**: ✅ All fixes applied and documented  
**Last Updated**: After CSS and initialization fixes  
**Testing Tools**: 3 test files provided  
**Ready to Test**: YES ✓
