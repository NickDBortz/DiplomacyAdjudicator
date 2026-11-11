# 🧪 Quick Radial Menu Test Checklist

## Before Testing

- [ ] Backend server running: `python server.py`
- [ ] Game loaded in browser at `http://localhost:8001/docs/singleplayer.html`
- [ ] Game is in **Spring** or **Fall** phase (NOT Adjustment)
- [ ] Browser console open (F12 → Console tab)
- [ ] Clear console before test: `console.clear()`

## Step 1: Verify Scripts Are Loaded

In browser console, run:
```javascript
console.log('Scripts check:');
console.log('radialMenu:', typeof radialMenu, radialMenu);
console.log('initRadialMenu:', typeof initRadialMenu);
console.log('handleMapClickWithRadialMenu:', typeof handleMapClickWithRadialMenu);
console.log('SVG element:', document.querySelector('svg') ? '✓' : '✗');
```

**Expected output:**
- `radialMenu: object` or `radialMenu: null` ✓
- `initRadialMenu: function` ✓
- `handleMapClickWithRadialMenu: function` ✓
- `SVG element: ✓` ✓

## Step 2: Check Game State

```javascript
const state = window.diplomacy.state;
console.log('Phase:', state.phase);
console.log('Player power:', state.player_power);
console.log('Units count:', state.units.length);
console.log('Player units:', state.units.filter(u => u.owner === state.player_power).length);
```

**Expected:**
- Phase: `Spring` or `Fall` (not Adjustment)
- Player power: Should be a country name (England, France, etc.)
- Units count: Should be > 0
- Player units: Should be > 0

## Step 3: Click on Your Unit

1. On the map, **click on one of your units** (should be your color)
2. **Watch browser console** for `[RadialMenu]` messages

**What should happen:**
- Console shows: `[RadialMenu] Click detected`
- Console shows: `[RadialMenu] Unit data found: ...`
- Console shows: `[RadialMenu] Showing menu for unit`
- **Radial menu appears on the map near the clicked unit**

## Step 4: If Menu Doesn't Appear

### Check 1: Did console show `[RadialMenu] Click detected`?

**If NO:**
- Click handler not firing
- Try: Click directly on the unit symbol, not the territory
- Try: Make sure you're in Spring/Fall phase
- Check: `event.target` in click handler

**If YES:** → Go to Check 2

### Check 2: Did console show available orders?

Run in console:
```javascript
console.log('Available orders:');
console.log(availableOrders);
```

**If empty array:**
- No orders available for your units
- Try: Wait for game to fully load orders
- Try: Refresh page and try again

**If has orders:** → Go to Check 3

### Check 3: Is the menu group in SVG?

Run in console:
```javascript
const menu = document.getElementById('radial-menu');
console.log('Menu group exists:', !!menu);
if (menu) {
    console.log('Menu children:', menu.children.length);
    console.log('Menu HTML:', menu.outerHTML.substring(0, 200));
}
```

**If menu group doesn't exist:**
- Menu wasn't created
- Check: Did `initRadialMenu()` run?
- Try: Manually initialize: `initRadialMenu(document.querySelector('svg'))`

**If menu group exists but is hidden:**
- Check visibility: `menu.style.display`, `menu.style.visibility`, `menu.style.opacity`
- Check position: `menu.getAttribute('transform')`
- Try: Make visible: `menu.style.display = 'block'; menu.style.opacity = '1';`

### Check 4: Is the menu clickable?

```javascript
const menuItems = document.querySelectorAll('.radial-menu-item');
console.log('Menu items:', menuItems.length);
menuItems.forEach((item, i) => {
    const type = item.getAttribute('data-type');
    const available = !item.classList.contains('disabled');
    console.log(`  ${i}: ${type} - ${available ? '✓ available' : '✗ disabled'}`);
});
```

**Expected:** Should show 5 items (Hold, Advance, Support, Transform, Convoy) with at least some available

**If all disabled:**
- No available orders for this unit
- Try: Click a different unit
- Try: Check `availableOrders` list

## Step 5: Test Menu Click

If menu is visible:
1. Hover over a menu option (should highlight)
2. Click on "Hold" option
3. Unit should be selected and menu should close

**In console**, you should see:
```
[RadialMenu] Menu item clicked: Hold
```

---

## Troubleshooting Quick Fixes

| Symptom | Fix |
|---------|-----|
| Menu not appearing | Click on a different unit, or refresh and try again |
| "radialMenu is not defined" | Reload page - script may not have loaded |
| Menu appears but is grayed out | No valid orders; check available orders |
| Menu appears far from unit | Check SVG zoom/transform settings |
| Menu stuck on screen | Click elsewhere to close, or refresh |

## Getting Help

If none of this works:
1. Copy the **full browser console output** (including all `[RadialMenu]` messages)
2. Share screenshot of map with click location
3. Run this diagnostic in console:
   ```javascript
   console.log('=== DIAGNOSTIC ===');
   console.log('Phase:', window.diplomacy.state.phase);
   console.log('Unit clicked:', event?.target?.closest('.unit')?.dataset);
   console.log('Available orders:', availableOrders.length);
   console.log('RadialMenu initialized:', !!radialMenu && !!radialMenu.menuGroup);
   ```

---

**Last Updated:** After CSS fixes for radial menu visibility
**Status:** Ready to test ✓
