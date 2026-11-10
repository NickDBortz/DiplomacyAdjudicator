# Quick Start Guide: Interactive Map-Based Order Picker

## What's New?

Your Diplomacy game now includes an interactive map-based order picker! Instead of only using dropdowns, you can now:
- **Click on the map** to select your units
- **Click on territories** to specify order actions
- **Get automatic order suggestions** based on your selections
- **Enjoy the same interface on mobile and desktop**

## Getting Started (3 Steps)

### Step 1: Start the Servers

```bash
# Terminal 1: Start backend server
cd server
python app.py

# Terminal 2: Start web server
cd docs
python -m http.server 8000
```

### Step 2: Open the Game

Visit: **http://localhost:8000/docs/singleplayer.html**

### Step 3: Play!

1. Click "New Game" button
2. Select a Great Power (e.g., "France")
3. Click on a territory with your unit (it highlights in gold)
4. Click on a destination territory (it highlights in red)
5. Click "Submit Order" button

That's it! The order is automatically suggested and submitted.

## How to Use (3 Actions)

### Action 1: Select Your Unit
```
Click on any territory with one of your units
→ Territory highlights in GOLD
→ Unit appears in dropdown
→ Status shows "Selected [Territory Name]"
```

### Action 2: Select the Destination/Action
```
Click on destination or action territory
→ Territory highlights in RED  
→ System suggests valid order
→ Status shows "Order ready: [Order Details]"
```

### Action 3: Submit
```
Click "Submit Order" button
→ Order confirmed and sent
→ Selection clears automatically
→ Ready for next order
```

## Examples

### Example 1: Move an Army
```
1. Click on PAR (Paris) → Gold highlight
2. Click on BUR (Burgundy) → Red highlight  
3. See: "Order ready: A PAR - BUR"
4. Click "Submit Order"
✓ Army moves from Paris to Burgundy
```

### Example 2: Support Another Unit
```
1. Click on GAS (Gascony)
2. Click on BUR (where friendly unit is moving)
3. See suggestion for support order
4. Click "Submit Order"
✓ Unit in Gascony supports the move
```

### Example 3: Build a Unit (Adjustment Phase)
```
1. Click on PAR (your supply center)
2. System suggests: "Build A PAR"
3. Click "Submit Order"
✓ New army built in Paris
```

## Tips & Tricks

### 💡 Pro Tips
- **Single Click to Cancel**: Click same territory twice to deselect
- **Keyboard Also Works**: Use arrow keys and Enter in dropdowns
- **Mix Methods**: Use map for some orders, dropdowns for others
- **Mobile Friendly**: Works great with finger taps on phones/tablets

### ⚠️ Common Issues
- **"Select a power first"** → Choose power from dropdown above orders
- **"No valid orders"** → Destination isn't adjacent or order impossible
- **Highlighting not showing** → Try tapping another territory

### 🎮 Game Phase Differences

| Phase | What to Click |
|-------|--------------|
| Spring/Fall | Unit territory → Destination territory |
| Retreat | Dislodged unit territory → Retreat destination |
| Build | Supply center → (order auto-detected) |
| Remove | Unit to disband → (order auto-detected) |

## Still Want Dropdowns?

No problem! The old dropdown method still works:
1. Use "Unit or build location" dropdown
2. Use "Order type" dropdown to filter
3. Use "Available orders" dropdown to select
4. Click "Submit Order"

**Both methods work together** - use whichever you prefer!

## Mobile Usage

### On Phone/Tablet:
✓ Tap territories just like clicking
✓ Larger touch targets for easier tapping
✓ Same features as desktop
✓ No special gestures needed

### Tips for Mobile:
- Tap in the center of the territory
- Avoid scrolling while tapping (use zoom to see better)
- Use portrait or landscape - both work!

## If Something Goes Wrong

1. **Check the Status Message** - Usually tells you what's wrong
2. **Use "Clear selection" Button** - Resets and lets you try again
3. **Refresh Page** - Start fresh if confused
4. **Use Dropdowns** - Fallback to manual selection
5. **Check Console** - Open F12 and look at Console tab for errors

## Feature Highlights

✨ **Auto-Suggest Orders**
When you click two territories, the system instantly figures out what order you want

🎨 **Visual Feedback**
Gold and red highlights show exactly which territories are selected

📱 **Mobile Ready**
Works perfectly on phones, tablets, and desktops

🔄 **Dropdown Sync**
Map selections update dropdowns automatically and vice versa

⌨️ **Keyboard Still Works**
Tab through and use arrow keys in dropdowns too

## Supported Orders

The system automatically detects and suggests:
- ✅ Movement (`A PAR - BUR`)
- ✅ Hold (`A PAR H`)
- ✅ Support (`A PAR S A BUR - GAS`)
- ✅ Convoy (`F ENG C A EDI - NWY`)
- ✅ Build (`Build A PAR`)
- ✅ Remove (`Remove A PAR`)
- ✅ Retreat (`A PAR - BUR`) - during retreat phase

## Performance

⚡ **Fast**: Instant response to clicks
🔧 **Smooth**: Highlighting updates smoothly  
💾 **Light**: Doesn't slow down the game
📊 **Efficient**: Works on all devices

## Accessibility

- 🎯 Works with screen readers
- ⌨️ Full keyboard navigation
- 🎨 Color contrast verified
- 👆 Large touch targets on mobile
- 📢 Clear status messages

## Settings

The feature works automatically - no settings to configure!

If you want to customize colors:
1. Edit `docs/map-order-picker.js`
2. Find `TERRITORY_SELECTION_COLORS`
3. Change hex colors (e.g., `#FFD700` to your preference)

## Getting Help

📖 **Full Documentation**: See `INTERACTIVE_MAP_ORDER_PICKER.md`
🧪 **Testing Guide**: See `TESTING_GUIDE.md`  
🔧 **Technical Details**: See `IMPLEMENTATION_SUMMARY.md`

## Feedback Welcome!

Have suggestions? Found an issue? Please report:
- What browser you're using
- What device (desktop/mobile)
- What you were trying to do
- What happened vs what you expected

## Next Steps

1. ✅ **Try It Out** - Start a game and click on the map
2. ✅ **Get Comfortable** - Do a few orders to get the flow
3. ✅ **Mix Methods** - Try using both map and dropdowns
4. ✅ **Enjoy!** - Play your best Diplomacy game!

---

**Questions?** Check the full documentation files included in the repository.

**Ready?** Open the game and start clicking! 🗺️🎮

