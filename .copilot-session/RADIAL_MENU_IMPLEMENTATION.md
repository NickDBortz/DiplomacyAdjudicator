# Radial Menu System Implementation for Diplomacy

## Overview
This document describes the comprehensive click-based order selection system using radial menus that replaces the need for dropdown-based order selection in the Diplomacy game UI.

## Implementation Summary

### Files Modified

#### 1. **docs/radial-menu.js** (NEW)
A complete radial menu system module featuring:
- **RadialMenu class**: Core component managing all radial menu operations
- **Configuration**: 5-option menu (Hold, Advance, Support, Transform, Convoy) with color coding
- **Multi-step selection flows** for complex orders
- **Territory highlighting** for advance, support, and convoy destinations
- **Unit highlighting** for support and convoy operations

### Key Features

#### Adjustment Phase
- Automatic building on supply center click
- Automatic disbanding on unit click
- (Already working before this implementation)

#### Spring/Fall Phases
**Radial Menu appears on unit click with 5 options:**

1. **Hold**: Immediately creates "Unit H" order
   - Simple single-step operation
   - No highlighting needed

2. **Advance**: Multi-step destination selection
   - Shows all adjacent territories highlighted in light green
   - Player clicks destination to create "Unit - Territory" order

3. **Support**: Two-mode system
   - **Mode 1 (Hold Support)**: Click adjacent unit → "Unit S TargetUnit H"
   - **Mode 2 (Advance Support)**: 
     - Click adjacent unit
     - System shows its adjacent territories
     - Click destination → "Unit S TargetUnit - Territory"

4. **Transform**: Immediately creates "Unit T" order
   - Simple single-step operation (like Hold)
   - No highlighting needed

5. **Convoy**: Multi-step army and destination selection
   - Shows adjacent armies highlighted in blue
   - Click army to convoy
   - System shows army's adjacent territories
   - Click destination → "Unit C Army - Territory"

#### Retreat Phase
- No radial menu (retreat is simpler)
- Click on dislodged unit to see highlighted adjacent territories
- Click territory to retreat there
- Only advance orders allowed (no convoy)

### Technical Implementation

#### Radial Menu Rendering
- Circular menu positioned at unit click location
- 5 items evenly spaced around center circle
- Each menu item is a clickable SVG circle with label
- Color-coded by order type:
  - Hold: Green (#4CAF50)
  - Advance: Blue (#2196F3)
  - Support: Orange (#FF9800)
  - Transform: Purple (#9C27B0)
  - Convoy: Red (#F44336)

#### Highlighting System
Territory highlights use CSS classes:
- `advance-target`: Light green (#90EE90) with green border
- `support-target`: Light pink (#FFB6C1) with hot pink border
- `convoy-target`: Light blue (#87CEEB) with blue border
- `retreat-target`: Gold (#FFD700) with orange border
- `checkerboard-convoy`: Checkerboard pattern for dual-purpose spaces (future enhancement)

Unit highlights use SVG filters:
- Brightness increase + drop shadow effect
- Color-coded to match order type

#### State Management
The RadialMenu class tracks:
- `selectionMode`: Current order type being created
- `selectionState`: Multi-step selection state (source unit, destination)
- `highlightClasses`: Map of highlighted territories and their CSS classes
- `availableOrders`: List of valid orders for current power

#### Integration with Existing System
- Integrates with existing `window.diplomacy.order()` function
- Uses existing `mapData` and territory structure
- Respects existing phase-based order validation
- Maintains existing order highlighting (blue/gold for manual selection)

### Data Structures

#### Territory Adjacency
Uses JSON structure with:
- `adjacents`: Array of adjacent territory *names* (not abbreviations)
- Example: `"adjacents": ["St Petersburg", "Norway", "Sweden", "Gulf of Bothnia"]`

Adjacency is converted to abbreviations at runtime for display.

### CSS Styling

#### New Classes (style.css)
```css
.radial-menu-group
.radial-menu-item / .radial-menu-item.available / .radial-menu-item.disabled
.radial-menu-bg
.radial-menu-center

.territory.advance-target / .territory.convoy-target / .territory.retreat-target / .territory.support-target
.territory.checkerboard-convoy

.unit.advance-target / .unit.support-target / .unit.convoy-target

#map-order-status.active
```

### Adjacency Data Conversion
The system handles territory adjacency properly:
1. Map JSON stores `adjacents` as territory *names*
2. At runtime, names are converted to abbreviations:
   ```javascript
   const adjacentNames = currentTerritory.adjacents || [];
   const adjacentAbbrs = adjacentNames.map(name => {
     return mapData.territories.find(t => t.name === name)?.abbr;
   });
   ```

### Error Handling
- Validates unit ownership and dislodged status
- Checks territory existence before highlighting
- Shows user-friendly messages on selection or validation failures
- Gracefully degrades if menu not initialized

### Performance Considerations
- Menu SVG elements cached and reused
- Efficient territory lookup using mapData object
- Minimal DOM manipulations (CSS class toggling)
- Event delegation for click handling

## User Experience Flow

### Example: Support Order (Hold)
1. User clicks unit → Radial menu appears
2. User clicks "Support" option
3. Adjacent units highlight in pink
4. User clicks target unit
5. Order "Unit S TargetUnit H" immediately submits
6. Menu closes, highlights clear

### Example: Support Order (Advance)
1. User clicks unit → Radial menu appears
2. User clicks "Support" option
3. Adjacent units highlight in pink
4. User clicks target unit
5. Target unit's adjacent territories highlight
6. User clicks destination territory
7. Order "Unit S TargetUnit - Territory" submits
8. Menu closes, highlights clear

### Example: Convoy Order
1. User clicks unit (must be fleet) → Radial menu appears
2. User clicks "Convoy" option
3. Adjacent armies highlight in blue
4. User clicks army to convoy
5. That army's adjacent territories highlight
6. User clicks destination
7. Order "Fleet C Army - Territory" submits
8. Menu closes, highlights clear

## Files Changed

### docs/radial-menu.js (NEW FILE)
- 760+ lines of JavaScript
- Complete RadialMenu class implementation
- Handler functions for map clicks
- Integration with order submission system

### docs/singleplayer.html
- Added `<script src="radial-menu.js"></script>` before main script

### docs/style.css
- Added ~80 lines of CSS for radial menu and highlighting

### docs/shared.js
- Modified `buildMap()` to initialize radial menu
- Modified SVG click handler to use `handleMapClickWithRadialMenu()`

## Backward Compatibility
- All existing dropdown-based order selection still works
- Adjustment phase unchanged
- Original order highlighting (blue/gold for manual selection) still appears
- Sidebar order picker still functional for detailed order review

## Future Enhancements
1. **Convoy Highlighting**: Checkerboard pattern for spaces that can both accept convoys and be advanced to
2. **Advanced UI**: Show order preview before confirmation
3. **Animation**: Smooth transitions for menu open/close
4. **Touch Support**: Optimize for touch devices with larger menu items
5. **Keyboard Support**: Arrow keys to navigate menu, Enter to select

## Testing Checklist
- [ ] Adjustment phase: Build order works
- [ ] Adjustment phase: Disband order works
- [ ] Spring/Fall: Hold order submits immediately
- [ ] Spring/Fall: Advance order highlights adjacent territories
- [ ] Spring/Fall: Support Hold order works correctly
- [ ] Spring/Fall: Support Advance requires two steps
- [ ] Spring/Fall: Transform order submits immediately
- [ ] Spring/Fall: Convoy order requires unit and destination
- [ ] Retreat phase: Only adjacent territories highlight
- [ ] Retreat phase: Advance-only orders available
- [ ] All orders respect ownership and dislodged status

## Code Quality
- No syntax errors (validated with Node.js)
- Follows existing code style and conventions
- Well-documented with JSDoc-style comments
- Handles edge cases gracefully
