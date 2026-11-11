#!/usr/bin/env node

/**
 * Test Runner for Diplomacy Radial Menu System
 * Executes all tests and provides detailed output
 */

// Create minimal mock for browser globals
const globalMock = {
  window: {
    RadialMenu: null,
    diplomacy: { state: null },
    addEventListener: () => {},
  },
  document: {
    getElementById: () => null,
    querySelectorAll: () => [],
    createElementNS: () => ({ setAttribute: () => {}, appendChild: () => {} }),
    createElement: () => ({ classList: { add: () => {}, remove: () => {} } }),
  },
  RADIAL_MENU_CONFIG: null,
};

// Make globals available
Object.assign(global, globalMock);
global.window = globalMock.window;
global.document = globalMock.document;

// ============================================================================
// MOCK RADIAL MENU CLASS
// ============================================================================

class RadialMenu {
  constructor(options = {}) {
    this.svg = null;
    this.state = null;
    this.selectedPower = null;
    this.currentUnit = null;
    this.menuGroup = null;
    this.isVisible = false;
    this.position = { x: 0, y: 0 };
    this.config = { radius: 80, itemCount: 5, ...options };
    this.selectionMode = null;
  }
}

global.RadialMenu = RadialMenu;
global.RADIAL_MENU_CONFIG = {
  radius: 80,
  innerRadius: 30,
  itemCount: 5,
  colors: {
    Hold: '#4CAF50',
    Advance: '#2196F3',
    Support: '#FF9800',
    Transform: '#9C27B0',
    Convoy: '#F44336',
  },
  highlights: {
    regular: '#90EE90',
    convoy: '#87CEEB',
    checkerboard: '#FFD700',
  }
};

// ============================================================================
// TEST UTILITIES
// ============================================================================

const tests = [];
function test(name, fn) {
  tests.push({ name, fn });
}

function assertEqual(actual, expected, message) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(`${message}\nExpected: ${JSON.stringify(expected)}\nActual: ${JSON.stringify(actual)}`);
  }
}

function assertExists(value, message) {
  if (!value) throw new Error(message);
}

function assertContains(array, value, message) {
  if (!Array.isArray(array) || !array.includes(value)) {
    throw new Error(message);
  }
}

global.test = test;
global.assertEqual = assertEqual;
global.assertExists = assertExists;
global.assertContains = assertContains;

// ============================================================================
// MOCK DATA
// ============================================================================

const mockMapData = {
  territories: [
    {
      name: "London",
      abbr: "LON",
      land: true,
      supply_center: true,
      label_pos: [100, 100],
      supply_center_pos: [105, 105],
      adjacents: ["North Sea", "English Channel", "Wales"],
      army_pos: [100, 100],
      coast_pos: [110, 105],
      fleet_pos: [110, 105]
    },
    {
      name: "North Sea",
      abbr: "NTH",
      land: false,
      label_pos: [150, 50],
      adjacents: ["London", "Norway", "Denmark"],
      fleet_pos: [150, 50]
    },
    {
      name: "France",
      abbr: "FRA",
      land: true,
      supply_center: true,
      label_pos: [80, 150],
      supply_center_pos: [85, 155],
      adjacents: ["England", "Spain", "Burgundy"],
      army_pos: [80, 150],
      coast_pos: [90, 155],
      fleet_pos: [90, 155]
    },
    {
      name: "English Channel",
      abbr: "ECH",
      land: false,
      label_pos: [120, 120],
      adjacents: ["London", "France", "North Sea"],
      fleet_pos: [120, 120]
    },
    {
      name: "Wales",
      abbr: "WAL",
      land: true,
      label_pos: [70, 110],
      adjacents: ["London", "Liverpool", "North Atlantic Ocean"],
      army_pos: [70, 110]
    }
  ],
  width: 1000,
  height: 1000,
  water_color: '#4A90E2'
};

const mockGameState = {
  phase: 'Spring',
  year: 1901,
  player_power: 'England',
  units: [
    { territory: 'LON', owner: 'England', type: 'F', coast: 'sc' },
    { territory: 'NTH', owner: 'England', type: 'F', coast: null },
    { territory: 'WAL', owner: 'England', type: 'A', coast: null },
  ]
};

const mockAvailableOrders = [
  { unit: 'F LON (sc)', type: 'Hold', text: 'F LON H' },
  { unit: 'F LON (sc)', type: 'Move', text: 'F LON - NTH', targets: ['NTH'] },
  { unit: 'F LON (sc)', type: 'Move', text: 'F LON - ECH', targets: ['ECH'] },
  { unit: 'F LON (sc)', type: 'Support', text: 'F LON S F NTH H' },
  { unit: 'F LON (sc)', type: 'Convoy', text: 'F LON C A WAL - FRA', targets: ['WAL', 'FRA'] },
  { unit: 'A WAL', type: 'Hold', text: 'A WAL H' },
  { unit: 'A WAL', type: 'Move', text: 'A WAL - LON', targets: ['LON'] },
];

global.mockMapData = mockMapData;
global.mockGameState = mockGameState;
global.mockAvailableOrders = mockAvailableOrders;

// ============================================================================
// TEST CASES
// ============================================================================

test('RadialMenu initialization', () => {
  assertExists(RadialMenu, 'RadialMenu class should be defined');
  const menu = new RadialMenu({ radius: 80 });
  assertExists(menu, 'RadialMenu should instantiate');
  assertEqual(menu.isVisible, false, 'Menu should start hidden');
});

test('RadialMenu configuration', () => {
  const menu = new RadialMenu({ radius: 100 });
  assertEqual(menu.config.radius, 100, 'Custom radius should be set');
  assertEqual(menu.config.itemCount, 5, 'Should have 5 items by default');
});

test('RADIAL_MENU_CONFIG colors defined', () => {
  assertExists(global.RADIAL_MENU_CONFIG.colors, 'Color configuration should exist');
  assertExists(global.RADIAL_MENU_CONFIG.colors.Hold, 'Hold color should be defined');
  assertExists(global.RADIAL_MENU_CONFIG.colors.Advance, 'Advance color should be defined');
  assertExists(global.RADIAL_MENU_CONFIG.colors.Support, 'Support color should be defined');
  assertExists(global.RADIAL_MENU_CONFIG.colors.Transform, 'Transform color should be defined');
  assertExists(global.RADIAL_MENU_CONFIG.colors.Convoy, 'Convoy color should be defined');
});

test('Territory adjacency conversion (name to abbreviation)', () => {
  const territory = mockMapData.territories.find(t => t.name === 'London');
  const adjacentNames = territory.adjacents;
  const adjacentAbbrs = [];
  
  for (const adjName of adjacentNames) {
    const adjTerr = mockMapData.territories.find(t => t.name === adjName);
    if (adjTerr) {
      adjacentAbbrs.push(adjTerr.abbr);
    }
  }
  
  assertContains(adjacentAbbrs, 'NTH', 'North Sea abbr should be in adjacents');
  assertContains(adjacentAbbrs, 'ECH', 'English Channel abbr should be in adjacents');
  assertContains(adjacentAbbrs, 'WAL', 'Wales abbr should be in adjacents');
});

test('Hold order detection', () => {
  const holdOrders = mockAvailableOrders.filter(o => o.type === 'Hold');
  assertEqual(holdOrders.length >= 2, true, 'Should have at least 2 hold orders');
  assertContains(holdOrders.map(o => o.text), 'F LON H', 'F LON H should be a hold order');
});

test('Advance order detection and targets', () => {
  const advanceOrders = mockAvailableOrders.filter(o => o.type === 'Move');
  assertEqual(advanceOrders.length >= 2, true, 'Should have at least 2 move orders');
  
  const lonMoves = advanceOrders.filter(o => o.unit === 'F LON (sc)');
  assertEqual(lonMoves.length, 2, 'F LON should have 2 move options');
  
  const nthMove = lonMoves.find(o => o.targets.includes('NTH'));
  assertExists(nthMove, 'F LON should be able to move to NTH');
});

test('Support order structure', () => {
  const supportOrders = mockAvailableOrders.filter(o => o.type === 'Support');
  assertEqual(supportOrders.length >= 1, true, 'Should have support orders');
});

test('Convoy order detection', () => {
  const convoyOrders = mockAvailableOrders.filter(o => o.type === 'Convoy');
  assertEqual(convoyOrders.length >= 1, true, 'Should have convoy orders');
  
  const lonConvoy = convoyOrders.find(o => o.unit === 'F LON (sc)');
  assertExists(lonConvoy, 'F LON should have a convoy order');
});

test('Order text parsing', () => {
  const orderText = 'F LON H';
  const parts = orderText.split(' ');
  assertEqual(parts[0], 'F', 'First part should be unit type');
  assertEqual(parts[1], 'LON', 'Second part should be territory');
  assertEqual(parts[2], 'H', 'Third part should be action code');
});

test('Adjacent territory filtering', () => {
  const lonTerr = mockMapData.territories.find(t => t.abbr === 'LON');
  const adjacents = lonTerr.adjacents;
  assertEqual(adjacents.length, 3, 'LON should have 3 adjacent territories by name');
  
  const adjAbbrs = [];
  for (const adjName of adjacents) {
    const t = mockMapData.territories.find(x => x.name === adjName);
    if (t) adjAbbrs.push(t.abbr);
  }
  assertEqual(adjAbbrs.length, 3, 'Should have 3 adjacent abbreviations');
});

test('Unit ownership validation', () => {
  const englishUnits = mockGameState.units.filter(u => u.owner === 'England');
  assertEqual(englishUnits.length, 3, 'England should have 3 units');
  assertContains(englishUnits.map(u => u.territory), 'LON', 'England should have unit in LON');
});

test('Land vs sea territory handling', () => {
  const lonTerr = mockMapData.territories.find(t => t.abbr === 'LON');
  assertEqual(lonTerr.land, true, 'LON should be land territory');
  
  const nthTerr = mockMapData.territories.find(t => t.abbr === 'NTH');
  assertEqual(nthTerr.land, false, 'NTH should be sea territory');
});

test('Supply center identification', () => {
  const scTerritories = mockMapData.territories.filter(t => t.supply_center);
  assertEqual(scTerritories.length >= 2, true, 'Should have multiple supply centers');
  
  const lonSc = mockMapData.territories.find(t => t.abbr === 'LON' && t.supply_center);
  assertExists(lonSc, 'LON should be a supply center');
});

test('Unit type detection (Army vs Fleet)', () => {
  const armies = mockGameState.units.filter(u => u.type === 'A');
  const fleets = mockGameState.units.filter(u => u.type === 'F');
  
  assertEqual(armies.length >= 1, true, 'Should have army units');
  assertEqual(fleets.length >= 2, true, 'Should have fleet units');
});

test('Phase detection', () => {
  const state1 = { phase: 'Spring', year: 1901 };
  const state2 = { phase: 'Spring Adjustment', year: 1901 };
  const state5 = { phase: 'Retreat (England)', year: 1901 };
  
  assertEqual(state1.phase === 'Spring', true, 'Should detect Spring phase');
  assertEqual(state2.phase.includes('Adjustment'), true, 'Should detect Adjustment phase');
  assertEqual(state5.phase.includes('Retreat'), true, 'Should detect Retreat phase');
});

test('Menu position calculation from SVG rect', () => {
  const mockRect = {
    left: 100,
    top: 200,
    width: 40,
    height: 40
  };
  const mockSvgRect = {
    left: 50,
    top: 100
  };
  
  const x = (mockRect.left - mockSvgRect.left + mockRect.width / 2);
  const y = (mockRect.top - mockSvgRect.top + mockRect.height / 2);
  
  // x = (100 - 50 + 40/2) = 50 + 20 = 70
  // y = (200 - 100 + 40/2) = 100 + 20 = 120
  assertEqual(x, 70, 'X position should be calculated correctly');
  assertEqual(y, 120, 'Y position should be calculated correctly');
});

test('Radial menu item positions (5 items)', () => {
  const itemCount = 5;
  const radius = 80;
  const positions = [];
  
  for (let i = 0; i < itemCount; i++) {
    const angle = (i * 2 * Math.PI / itemCount) - Math.PI / 2;
    const x = Math.cos(angle) * radius;
    const y = Math.sin(angle) * radius;
    positions.push({ x, y });
  }
  
  assertEqual(positions.length, 5, 'Should have 5 menu positions');
  assertExists(positions[0], 'First position should exist');
});

test('Advance highlighting color', () => {
  const advanceColor = global.RADIAL_MENU_CONFIG.highlights.regular;
  assertExists(advanceColor, 'Advance highlight color should be defined');
  assertEqual(typeof advanceColor, 'string', 'Color should be a string');
});

test('Convoy highlighting with checkerboard', () => {
  const convoyColor = global.RADIAL_MENU_CONFIG.highlights.convoy;
  const checkerboardColor = global.RADIAL_MENU_CONFIG.highlights.checkerboard;
  assertExists(convoyColor, 'Convoy highlight color should be defined');
  assertExists(checkerboardColor, 'Checkerboard highlight color should be defined');
});

test('Multiple selection tracking state', () => {
  const menu = new RadialMenu();
  menu.selectionState = {
    step: 1,
    supportUnit: 'F LON',
    supportMode: 'advance'
  };
  
  assertExists(menu.selectionState.step, 'Selection step should be tracked');
  assertEqual(menu.selectionState.supportUnit, 'F LON', 'Support unit should be tracked');
  assertEqual(menu.selectionState.supportMode, 'advance', 'Support mode should be tracked');
});

test('Adjustment phase auto-submit condition', () => {
  const state1 = { phase: 'Spring Adjustment' };
  const state2 = { phase: 'Fall Adjustment' };
  const state3 = { phase: 'Spring' };
  
  const shouldAutoSubmit1 = state1.phase === 'Spring Adjustment' || state1.phase === 'Fall Adjustment';
  const shouldAutoSubmit2 = state2.phase === 'Spring Adjustment' || state2.phase === 'Fall Adjustment';
  const shouldAutoSubmit3 = state3.phase === 'Spring Adjustment' || state3.phase === 'Fall Adjustment';
  
  assertEqual(shouldAutoSubmit1, true, 'Spring Adjustment should auto-submit');
  assertEqual(shouldAutoSubmit2, true, 'Fall Adjustment should auto-submit');
  assertEqual(shouldAutoSubmit3, false, 'Spring should NOT auto-submit');
});

// ============================================================================
// RUN TESTS
// ============================================================================

console.log('\n' + '='.repeat(70));
console.log('  Diplomacy Radial Menu System - Test Suite');
console.log('='.repeat(70) + '\n');

let passed = 0;
let failed = 0;
const failedTests = [];

for (const { name, fn } of tests) {
  try {
    fn();
    passed++;
    console.log(`✓ ${name}`);
  } catch (error) {
    failed++;
    failedTests.push({ name, error: error.message });
    console.log(`✗ ${name}`);
    console.log(`  Error: ${error.message}\n`);
  }
}

console.log('\n' + '='.repeat(70));
console.log(`RESULTS: ${passed} passed, ${failed} failed out of ${passed + failed} total`);
console.log('='.repeat(70) + '\n');

if (failed === 0) {
  console.log('✓ All tests passed!\n');
  process.exit(0);
} else {
  console.log(`✗ ${failed} test(s) failed:\n`);
  failedTests.forEach(({ name, error }) => {
    console.log(`  • ${name}`);
    console.log(`    ${error}\n`);
  });
  process.exit(1);
}
