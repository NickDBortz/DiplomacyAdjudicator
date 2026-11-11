/**
 * Radial Menu Diagnostic Script
 * Paste this into the browser console to diagnose issues
 */

console.log('%c=== RADIAL MENU DIAGNOSTIC ===', 'color: blue; font-size: 16px; font-weight: bold');

// 1. Check if scripts loaded
console.log('\n%c1. SCRIPT STATUS', 'color: green; font-weight: bold');
console.log('✓ SVG_NS defined:', typeof SVG_NS !== 'undefined' ? '✓ YES' : '✗ NO');
console.log('✓ RadialMenu class defined:', typeof RadialMenu !== 'undefined' ? '✓ YES' : '✗ NO');
console.log('✓ radialMenu instance:', typeof radialMenu !== 'undefined' ? '✓ YES (' + (radialMenu ? 'initialized' : 'null') + ')' : '✗ NO');
console.log('✓ mapData available:', typeof mapData !== 'undefined' ? '✓ YES (' + mapData.territories.length + ' territories)' : '✗ NO');
console.log('✓ svg element:', typeof svg !== 'undefined' ? '✓ YES' : '✗ NO');

// 2. Check game state
console.log('\n%c2. GAME STATE', 'color: green; font-weight: bold');
console.log('Phase:', window.diplomacy.state?.phase || 'NOT LOADED');
console.log('Year:', window.diplomacy.state?.year || 'NOT LOADED');
console.log('Player Power:', window.diplomacy.state?.player_power || 'NOT LOADED');
console.log('Units Count:', window.diplomacy.state?.units?.length || 0);
console.log('Dislodged Units:', window.diplomacy.state?.dislodged_units?.length || 0);

// 3. Check available orders
console.log('\n%c3. AVAILABLE ORDERS', 'color: green; font-weight: bold');
console.log('Total orders available:', window.availableOrders?.length || 0);
if (window.availableOrders) {
  const ordersByType = {};
  window.availableOrders.forEach(order => {
    const type = order.type || 'Unknown';
    ordersByType[type] = (ordersByType[type] || 0) + 1;
  });
  console.log('Orders by type:', ordersByType);
}

// 4. Check player units
console.log('\n%c4. YOUR UNITS', 'color: green; font-weight: bold');
const playerPower = window.diplomacy.state?.player_power;
const playerUnits = window.diplomacy.state?.units?.filter(u => u.owner === playerPower);
console.log('Units owned by', playerPower + ':', playerUnits?.length || 0);
playerUnits?.forEach(u => {
  console.log(`  - ${u.type} at ${u.territory} (coast: ${u.coast || 'none'})`);
});

// 5. Check SVG elements
console.log('\n%c5. SVG STRUCTURE', 'color: green; font-weight: bold');
console.log('SVG element exists:', !!svg ? '✓ YES' : '✗ NO');
console.log('SVG viewBox:', svg?.getAttribute('viewBox') || 'NOT SET');
console.log('SVG children count:', svg?.children?.length || 0);
console.log('Radial menu group exists:', !!document.getElementById('radial-menu') ? '✓ YES' : '✗ NO');

// 6. Check unit elements
console.log('\n%c6. UNIT ELEMENTS ON MAP', 'color: green; font-weight: bold');
const unitElements = document.querySelectorAll('.unit');
console.log('Unit elements found:', unitElements.length);
unitElements.forEach((el, i) => {
  if (i < 5) { // Show first 5
    console.log(`  - ${el.dataset.type} at ${el.dataset.territory} (owner: ${el.dataset.owner})`);
  }
});
if (unitElements.length > 5) {
  console.log(`  ... and ${unitElements.length - 5} more`);
}

// 7. Check phase
console.log('\n%c7. PHASE CHECK', 'color: green; font-weight: bold');
const phase = window.diplomacy.state?.phase;
console.log('Current phase:', phase);
console.log('Is Spring/Fall:', (phase === 'Spring' || phase === 'Fall') ? '✓ YES' : '✗ NO');
console.log('Is Adjustment:', phase?.includes('Adjustment') ? '✓ YES' : '✗ NO');
console.log('Is Retreat:', phase?.includes('Retreat') ? '✓ YES' : '✗ NO');

// 8. Test menu creation
console.log('\n%c8. MENU CREATION TEST', 'color: green; font-weight: bold');
if (typeof radialMenu !== 'undefined' && radialMenu && svg) {
  console.log('✓ Can create menu');
  console.log('Menu config:', {
    radius: radialMenu.config.radius,
    itemCount: radialMenu.config.itemCount,
    hasColors: Object.keys(radialMenu.config.colors).length
  });
} else {
  console.log('✗ Cannot create menu - missing dependencies');
}

// 9. Test SVG rendering
console.log('\n%c9. SVG RENDERING TEST', 'color: green; font-weight: bold');
try {
  const testCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  testCircle.setAttribute('cx', 100);
  testCircle.setAttribute('cy', 100);
  testCircle.setAttribute('r', 10);
  testCircle.setAttribute('fill', 'red');
  testCircle.setAttribute('id', 'test-diagnostic-circle');
  testCircle.setAttribute('opacity', '0.5');
  svg.appendChild(testCircle);
  console.log('✓ Test circle added (red circle at top-left of map)');
  console.log('  If you can see a red semi-transparent circle, SVG rendering works');
  console.log('  Run: document.getElementById("test-diagnostic-circle").remove() to remove it');
} catch (e) {
  console.log('✗ Cannot add test circle:', e.message);
}

// 10. Function availability check
console.log('\n%c10. FUNCTION CHECK', 'color: green; font-weight: bold');
console.log('initRadialMenu:', typeof initRadialMenu !== 'undefined' ? '✓ YES' : '✗ NO');
console.log('handleMapClickWithRadialMenu:', typeof handleMapClickWithRadialMenu !== 'undefined' ? '✓ YES' : '✗ NO');
console.log('handleRetreatSelection:', typeof handleRetreatSelection !== 'undefined' ? '✓ YES' : '✗ NO');
console.log('selectMapTerritory:', typeof selectMapTerritory !== 'undefined' ? '✓ YES' : '✗ NO');

// 11. Recommendations
console.log('\n%c11. RECOMMENDATIONS', 'color: orange; font-weight: bold');
const issues = [];

if (typeof SVG_NS === 'undefined') issues.push('SVG_NS not defined - check script load order');
if (typeof RadialMenu === 'undefined') issues.push('RadialMenu class not defined - radial-menu.js may not have loaded');
if (!svg) issues.push('SVG element not found - buildMap() may not have been called');
if (!window.diplomacy.state) issues.push('Game state not loaded - load a game first');
if (!playerUnits || playerUnits.length === 0) issues.push('No player units found - wait for game to initialize');
if (phase !== 'Spring' && phase !== 'Fall') issues.push('Not in Spring/Fall phase - menu only appears in these phases');

if (issues.length === 0) {
  console.log('%c✓ All checks passed! If menu not appearing:', 'color: green');
  console.log('  1. Make sure you\'re clicking on a UNIT (small icon), not a territory');
  console.log('  2. Make sure it\'s YOUR unit (same color as your power)');
  console.log('  3. Check that you\'re in Spring or Fall phase');
  console.log('  4. Open the console and click on a unit to see debug messages');
} else {
  console.log('%c⚠ Issues found:', 'color: red; font-weight: bold');
  issues.forEach(issue => console.log('  ✗ ' + issue));
}

// 12. Manual test
console.log('\n%c12. MANUAL MENU TEST', 'color: green; font-weight: bold');
console.log('To manually test the menu, run in console:');
console.log(`
const testUnit = {type: 'F', territory: 'LON', owner: 'England', coast: 'sc'};
const testPosition = {x: 500, y: 400};
radialMenu.showForUnit(testUnit, 'LON', testPosition, window.availableOrders, window.diplomacy.state, 'England');
`);

console.log('\n%c=== END DIAGNOSTIC ===', 'color: blue; font-size: 16px; font-weight: bold');
console.log('Copy the above output if reporting issues');
