# Interactive Map-Based Order Picker

This document describes the new interactive map-based order picking feature for the Diplomacy game interface.

## Overview

The map order picker allows players to select orders by clicking territories on the game map, in addition to using the traditional dropdown selectors. This feature improves usability on both desktop and mobile devices.

## How It Works

### Basic Workflow

1. **Select a Power**: First, select a Great Power from the dropdown in the sidebar
2. **Click a Unit Territory**: Click on the map to select a territory with one of your units
   - The territory will be highlighted in gold
   - The unit/location will automatically be selected in the "Unit or build location" dropdown
3. **Click a Destination/Action Territory**: Click another territory for the order action
   - The second territory will be highlighted in red
   - The system will suggest valid orders automatically
4. **Confirm and Submit**: Click the "Submit Order" button to confirm the order

### Game Phases

The map picker works differently depending on the current game phase:

#### Spring/Fall (Movement Phases)
- Click on your territories that contain units
- Click on destination territories for movement, support, or convoy actions
- The system automatically suggests valid orders based on the territories selected

#### Spring Retreat / Fall Retreat
- Click on territories containing your dislodged units
- Click on valid retreat destinations
- The order will be automatically selected

#### Adjustment (Build/Remove Phase)
- For **Building**: Click on your supply centers
- For **Removing**: Click on your units
- The appropriate build or remove order will be suggested

## Features

### Intelligent Order Suggestion
- When you click two territories, the system analyzes the game state and suggests valid orders
- If only one valid order exists, it's automatically selected
- If multiple valid orders exist, a dialog appears allowing you to choose

### Visual Feedback
- **Gold highlighting**: Currently selected unit/location (source)
- **Red highlighting**: Selected destination/action territory (target)
- **Status message**: Shows what phase you're in and what to click next
- **Territory hover**: Territories show a lighter stroke on hover

### Mobile Friendly
- Larger touch targets on mobile devices
- Full-screen sidebar on small screens
- Same functionality on touchscreen as desktop
- Responsive message sizes and text

### Synchronization with Dropdowns
- When you click territories on the map, the dropdowns automatically update
- When you manually select options in the dropdowns, the map highlighting updates
- Clear separation and sync between both input methods

### Order Types Supported
- **Move**: `A PAR - BUR` (movement to an adjacent territory)
- **Hold**: Holding in the current territory
- **Support**: `A PAR S A BUR - GAS` (supporting another unit's action)
- **Convoy**: `F ENG C A EDI - NWY` (transporting an army by sea)
- **Build**: `Build A PAR` (during adjustment phase)
- **Remove**: `Remove A PAR` (during adjustment phase)

## Clear Selection

Click the "Clear selection" button to:
- Reset all map highlighting
- Clear the unit and target selections
- Start over with a new order

## Accessibility Features

- Color-coded highlighting works for colorblind players
- All territories have tooltips showing the territory name and abbreviation
- Status messages provide clear feedback on what to do next
- Works on keyboard, mouse, and touchscreen input

## Technical Implementation

### Files Modified
- `singleplayer.html` - Added map-order-picker.js script
- `style.css` - Added styling for map highlighting and mobile responsiveness
- `docs/map-order-picker.js` - Main interactive order picker logic (new file)

### Browser Compatibility
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Tested on desktop and mobile devices
- SVG-based interactions work on all platforms

## Usage Tips

1. **For Beginners**: Use the traditional dropdowns if the map clicking feels confusing
2. **For Experienced Players**: Use map clicking for faster order entry
3. **On Mobile**: Tap the territories carefully; they have a larger hit area than they appear
4. **For Complex Orders**: If the system suggests multiple orders, you can either:
   - Click the suggested order in the dialog
   - Use the dropdowns to select a different order manually

## Troubleshooting

### My clicks on the map aren't working
- Make sure you've selected a power from the dropdown first
- Ensure the territory has a unit (for movement phases) or is a valid location
- Try refreshing the page if issues persist

### The territory highlighting doesn't show
- Check your browser's developer console for errors
- The highlight appears as a gold glow around the selected territory
- On some browsers, the effect may be subtle

### Orders aren't being suggested
- Ensure the destination territory is adjacent and valid for the unit type
- Check that the order hasn't already been submitted for this unit
- The destination must be available in the current game state

## Future Enhancements

Potential improvements for future versions:
- Show available destinations on hover
- Visual arrows showing possible moves before clicking
- Convoy route visualization
- Keyboard shortcuts for faster order entry
- Undo/redo functionality for orders
