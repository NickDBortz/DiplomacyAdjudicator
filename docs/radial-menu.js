/**
 * Radial Menu System for Diplomacy Map-based Order Selection
 * 
 * Provides visual radial menus for selecting order types (Hold, Advance, Support, Transform, Convoy)
 * with phase-aware highlighting and interactive selection flows.
 */

const RADIAL_MENU_CONFIG = {
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

/**
 * Parse order details from order text (reuses shared.js logic)
 */
function parseOrderDetails(text) {
  const parts = text.split(' ');
  const adjustment = parts[0] === 'Build' || parts[0] === 'Remove';
  const unit = adjustment ? parts[2].replace(/\([^)]*\)$/, '')
    : `${parts[0]} ${parts[1]}`;
  const action = adjustment ? parts[0] : parts[2].split('(')[0];
  const types = { H: 'Hold', '-': 'Move', S: 'Support', C: 'Convoy', T: 'Transform',
    Build: 'Build', Remove: 'Remove' };
  return { text, unit, type: types[action] || action };
}

class RadialMenu {
  constructor(options = {}) {
    this.svg = null;
    this.state = null;
    this.selectedPower = null;
    this.currentUnit = null;
    this.menuGroup = null;
    this.isVisible = false;
    this.position = { x: 0, y: 0 };
    this.config = { ...RADIAL_MENU_CONFIG, ...options };
    this.selectionMode = null; // 'hold', 'advance', 'support-hold', 'support-advance', 'convoy'
    this.selectionState = {}; // Track multi-step selections
    this.onOrderSelected = null;
    this.highlightedTerritories = new Set();
    this.highlightClasses = new Map(); // territory -> class name
  }

  initialize(svgElement) {
    console.log('[RadialMenu] Initializing with SVG element:', !!svgElement);
    this.svg = svgElement;
    this.menuGroup = document.createElementNS(SVG_NS, 'g');
    this.menuGroup.setAttribute('id', 'radial-menu');
    this.menuGroup.setAttribute('class', 'radial-menu-group');
    this.svg.appendChild(this.menuGroup);
    console.log('[RadialMenu] Initialization complete, menuGroup appended to SVG');
  }

  /**
   * Show radial menu for a unit click
   */
  showForUnit(unit, territory, position, availableOrders, state, power) {
    console.log('[RadialMenu] showForUnit called', { unit, territory, position });
    
    this.state = state;
    this.selectedPower = power;
    this.currentUnit = unit;
    this.position = position;
    this.isVisible = true;
    this.availableOrders = availableOrders;

    // Determine which order types are available for this unit
    const unitStr = `${unit.type} ${territory}`;
    console.log('[RadialMenu] Looking for orders matching unitStr:', unitStr);
    
    const availableTypes = new Set();
    for (const order of availableOrders) {
      const orderDetails = parseOrderDetails(order.text || order);
      console.log('[RadialMenu] Checking order:', { order, orderDetails });
      if (orderDetails.unit === unitStr) {
        availableTypes.add(orderDetails.type === 'Move' ? 'Advance' : orderDetails.type);
      }
    }

    console.log('[RadialMenu] Available types found:', Array.from(availableTypes));
    this.renderMenu(availableTypes);
  }

  /**
   * Submit order through the game system
   */
  async submitOrder(order) {
    const powerSelect = document.getElementById('greatpower');
    const power = powerSelect ? powerSelect.value : this.selectedPower;
    
    if (!power || !order) {
      setPickerStatus('Error: No power selected or order invalid.');
      return false;
    }

    try {
      const result = typeof window.diplomacy.order === 'function'
        ? await window.diplomacy.order(order, power)
        : await submitMultiplayerOrder(order);
      if (result.ok) {
        setPickerStatus(`Order submitted: ${order}`);
        return true;
      } else {
        setPickerStatus(`Order rejected: ${result.error}`);
        return false;
      }
    } catch (e) {
      setPickerStatus(`Error submitting order: ${e.message}`);
      return false;
    }
  }

  /**
   * Render the radial menu with available options
   */
  renderMenu(availableTypes) {
    console.log('[RadialMenu] Rendering menu with available types:', Array.from(availableTypes));
    
    this.menuGroup.innerHTML = '';

    const items = [
      { type: 'Hold', icon: '◆', color: this.config.colors.Hold },
      { type: 'Advance', icon: '→', color: this.config.colors.Advance },
      { type: 'Support', icon: '†', color: this.config.colors.Support },
      { type: 'Transform', icon: '✦', color: this.config.colors.Transform },
      { type: 'Convoy', icon: 'C', color: this.config.colors.Convoy },
    ];

    const angleStep = (Math.PI * 2) / items.length;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      const angle = (i * angleStep) - (Math.PI / 2); // Start from top
      const x = this.position.x + Math.cos(angle) * this.config.radius;
      const y = this.position.y + Math.sin(angle) * this.config.radius;

      const isAvailable = availableTypes.has(item.type);
      console.log(`[RadialMenu] Creating item ${item.type} at (${x}, ${y}), available=${isAvailable}`);
      this.createMenuItem(item, x, y, isAvailable, angle);
    }

    // Center circle
    const center = document.createElementNS(SVG_NS, 'circle');
    center.setAttribute('cx', this.position.x);
    center.setAttribute('cy', this.position.y);
    center.setAttribute('r', this.config.innerRadius);
    center.setAttribute('fill', '#555');
    center.setAttribute('stroke', '#fff');
    center.setAttribute('stroke-width', 2);
    center.setAttribute('class', 'radial-menu-center');
    this.menuGroup.appendChild(center);
    
    console.log('[RadialMenu] Menu rendered, group children count:', this.menuGroup.children.length);
  }

  /**
   * Create individual menu item
   */
  createMenuItem(item, x, y, isAvailable, angle) {
    const group = document.createElementNS(SVG_NS, 'g');
    group.setAttribute('class', `radial-menu-item ${isAvailable ? 'available' : 'disabled'}`);
    group.setAttribute('data-type', item.type);
    group.style.setProperty('--hover-x', `${Math.cos(angle) * 8}px`);
    group.style.setProperty('--hover-y', `${Math.sin(angle) * 8}px`);

    if (!isAvailable) {
      group.style.opacity = 0.5;
      group.style.pointerEvents = 'none';
    }

    const hitArea = document.createElementNS(SVG_NS, 'circle');
    hitArea.setAttribute('cx', x);
    hitArea.setAttribute('cy', y);
    hitArea.setAttribute('r', 34);
    hitArea.setAttribute('fill', 'transparent');
    group.appendChild(hitArea);

    const visual = document.createElementNS(SVG_NS, 'g');
    visual.setAttribute('class', 'radial-menu-visual');
    visual.setAttribute('pointer-events', 'none');

    const circle = document.createElementNS(SVG_NS, 'circle');
    circle.setAttribute('cx', x);
    circle.setAttribute('cy', y);
    circle.setAttribute('r', 25);
    circle.setAttribute('fill', item.color);
    circle.setAttribute('stroke', '#fff');
    circle.setAttribute('stroke-width', 2);
    circle.setAttribute('class', 'radial-menu-bg');
    visual.appendChild(circle);

    // Icon/Label
    const text = document.createElementNS(SVG_NS, 'text');
    text.setAttribute('x', x);
    text.setAttribute('y', y);
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('dominant-baseline', 'middle');
    text.setAttribute('fill', '#fff');
    text.setAttribute('font-weight', 'bold');
    text.setAttribute('font-size', '11');
    if (item.type.length > 6) {
      text.setAttribute('textLength', 42);
      text.setAttribute('lengthAdjust', 'spacingAndGlyphs');
    }
    text.setAttribute('pointer-events', 'none');
    text.textContent = item.type;
    visual.appendChild(text);
    group.appendChild(visual);

    // Click handler
    if (isAvailable) {
      group.addEventListener('click', (e) => {
        e.stopPropagation();
        this.handleMenuItemClick(item.type);
      });

    }

    this.menuGroup.appendChild(group);
  }

  /**
   * Handle menu item selection
   */
  handleMenuItemClick(orderType) {
    this.selectionMode = orderType.toLowerCase();
    this.selectionState = { mode: null };

    switch (orderType) {
      case 'Hold':
        this.executeHoldOrder();
        break;
      case 'Advance':
        this.startAdvanceSelection();
        break;
      case 'Support':
        this.startSupportSelection();
        break;
      case 'Transform':
        this.executeTransformOrder();
        break;
      case 'Convoy':
        this.startConvoySelection();
        break;
    }

    if (orderType === 'Hold' || orderType === 'Transform') {
      this.hide();
    }
    // For other modes, menu stays visible for multi-step selection
  }

  /**
   * Execute Hold order immediately
   */
  executeHoldOrder() {
    const unitStr = `${this.currentUnit.type} ${this.currentUnit.territory}`;
    const order = `${unitStr} H`;
    this.submitOrder(order);
    this.clearHighlights();
  }

  /**
   * Execute Transform order immediately
   */
  executeTransformOrder() {
    const unitStr = `${this.currentUnit.type} ${this.currentUnit.territory}`;
    const order = `${unitStr} T`;
    this.submitOrder(order);
    this.clearHighlights();
  }

  /**
   * Start advance selection: highlight available territories
   */
  startAdvanceSelection() {
    this.clearHighlights();
    const territory = this.currentUnit.territory;
    const byAbbr = Object.fromEntries(mapData.territories.map(t => [t.abbr, t]));
    const currentTerritory = byAbbr[territory];

    if (!currentTerritory) return;

    // Get adjacent territory abbreviations from adjacents list (which contains names)
    const adjacentNames = currentTerritory.adjacents || [];
    const adjacentAbbrs = [];
    
    for (const adjName of adjacentNames) {
      const adjTerr = mapData.territories.find(t => t.name === adjName);
      if (adjTerr) {
        adjacentAbbrs.push(adjTerr.abbr);
      }
    }

    for (const adjAbbr of adjacentAbbrs) {
      this.highlightTerritory(adjAbbr, 'advance-target');
    }

    this.showMessage(`Click on a destination territory to advance to.`);
  }

  /**
   * Start support selection: show available units for hold support
   */
  startSupportSelection() {
    this.clearHighlights();
    this.selectionState.mode = 'hold-support';
    
    // Show adjacent units that can be hold-supported
    this.highlightAdjacentUnits();
    
    this.showMessage(`Click on a unit to support it (hold or advance). Currently in hold-support mode.`);
  }

  /**
   * Start convoy selection: unit then destination
   */
  startConvoySelection() {
    this.clearHighlights();
    this.selectionState.mode = 'convoy-source';
    
    const territory = this.currentUnit.territory;
    const byAbbr = Object.fromEntries(mapData.territories.map(t => [t.abbr, t]));
    const currentTerritory = byAbbr[territory];

    if (!currentTerritory) return;

    // Only fleets can convoy, only armies can be convoyed
    // Get adjacent territory abbreviations
    const adjacentNames = currentTerritory.adjacents || [];
    const adjacentAbbrs = [];
    
    for (const adjName of adjacentNames) {
      const adjTerr = mapData.territories.find(t => t.name === adjName);
      if (adjTerr) {
        adjacentAbbrs.push(adjTerr.abbr);
      }
    }

    // Highlight adjacent territories where convoiable units are
    for (const unit of this.state.units) {
      if (unit.owner !== this.selectedPower || unit.dislodged) continue;
      if (unit.type !== 'A') continue; // Only armies can be convoyed

      if (adjacentAbbrs.includes(unit.territory)) {
        this.highlightUnit(unit, 'convoy-target');
      }
    }

    this.showMessage(`Click on an army to convoy.`);
  }

  /**
   * Highlight adjacent units for support
   */
  highlightAdjacentUnits() {
    const territory = this.currentUnit.territory;
    const byAbbr = Object.fromEntries(mapData.territories.map(t => [t.abbr, t]));
    const currentTerritory = byAbbr[territory];

    if (!currentTerritory) return;

    const adjacentNames = currentTerritory.adjacents || [];
    const adjacentAbbrs = [];
    
    for (const adjName of adjacentNames) {
      const adjTerr = mapData.territories.find(t => t.name === adjName);
      if (adjTerr) {
        adjacentAbbrs.push(adjTerr.abbr);
      }
    }

    for (const unit of this.state.units) {
      if (unit.owner !== this.selectedPower || unit.dislodged) continue;
      if (!adjacentAbbrs.includes(unit.territory)) continue;

      this.highlightUnit(unit, 'support-target');
    }
  }

  /**
   * Highlight a territory
   */
  highlightTerritory(abbr, className) {
    const element = document.getElementById(`terr-${abbr}`);
    if (element) {
      element.classList.add(className);
      this.highlightedTerritories.add(abbr);
      this.highlightClasses.set(abbr, className);
    }
  }

  /**
   * Highlight a unit
   */
  highlightUnit(unit, className) {
    // Find unit marker in SVG
    const unitMarkers = this.svg.querySelectorAll('.unit');
    for (const marker of unitMarkers) {
      if (marker.dataset.territory === unit.territory &&
          marker.dataset.owner === unit.owner &&
          marker.dataset.type === unit.type &&
          !marker.classList.contains('order-highlight-source')) {
        marker.classList.add(className);
        this.highlightedTerritories.add(`unit-${unit.territory}-${unit.owner}`);
        this.highlightClasses.set(`unit-${unit.territory}-${unit.owner}`, className);
      }
    }
  }

  /**
   * Clear all highlights
   */
  clearHighlights() {
    for (const [target, className] of this.highlightClasses) {
      if (target.startsWith('unit-')) {
        const unitMarkers = this.svg.querySelectorAll('.unit');
        for (const marker of unitMarkers) {
          marker.classList.remove(className);
        }
      } else {
        const element = document.getElementById(`terr-${target}`);
        if (element) {
          element.classList.remove(className);
        }
      }
    }
    this.highlightedTerritories.clear();
    this.highlightClasses.clear();
  }

  /**
   * Show temporary message to user
   */
  showMessage(text) {
    const mapStatus = document.getElementById('map-order-status');
    if (mapStatus) {
      mapStatus.textContent = text;
    }
  }

  /**
   * Handle territory selection during multi-step order (advance, support, etc)
   */
  handleTerritorySelection(abbr) {
    if (!this.selectionMode) return;

    const byAbbr = Object.fromEntries(mapData.territories.map(t => [t.abbr, t]));
    const territory = byAbbr[abbr];
    
    if (!territory) {
      this.showMessage('Invalid territory selected.');
      return;
    }

    const unitStr = `${this.currentUnit.type} ${this.currentUnit.territory}`;

    switch (this.selectionMode) {
      case 'advance':
        this.completeAdvanceOrder(abbr);
        break;
      case 'support':
        if (this.selectionState.mode === 'advance-support') {
          this.completeSupportAdvanceOrder(abbr);
        } else {
          this.showMessage('Please click on a unit to support.');
        }
        break;
      case 'convoy':
        if (this.selectionState.mode === 'convoy-destination') {
          this.completeConvoyOrder(abbr);
        } else {
          this.showMessage('Please select an army to convoy.');
        }
        break;
    }
  }

  /**
   * Handle unit selection during multi-step order
   */
  handleUnitSelection(unitDataset) {
    if (!this.selectionMode) return;

    if (this.selectionMode === 'support') {
      if (this.selectionState.mode === 'hold-support') {
        this.completeSupportHoldOrder(unitDataset.territory);
      } else {
        // Switch to advance support mode - show adjacent territories for advance
        this.startAdvanceSupportSelection(unitDataset.territory);
      }
    } else if (this.selectionMode === 'convoy') {
      this.startConvoyDestinationSelection(unitDataset.territory);
    }
  }

  /**
   * Switch from hold-support to advance-support mode
   */
  startAdvanceSupportSelection(sourceTerritory) {
    this.selectionState.mode = 'advance-support';
    this.selectionState.supportSource = sourceTerritory;
    this.clearHighlights();
    
    // Show adjacent territories to source for potential advance
    const byAbbr = Object.fromEntries(mapData.territories.map(t => [t.abbr, t]));
    const sourceTerr = byAbbr[sourceTerritory];
    
    if (!sourceTerr) return;

    const adjacentNames = sourceTerr.adjacents || [];
    for (const adjName of adjacentNames) {
      const adjTerr = mapData.territories.find(t => t.name === adjName);
      if (adjTerr) {
        this.highlightTerritory(adjTerr.abbr, 'support-target');
      }
    }

    this.showMessage(`Click on a territory for advance support.`);
  }

  /**
   * Complete advance order with selected destination
   */
  completeAdvanceOrder(destAbbr) {
    const unitStr = `${this.currentUnit.type} ${this.currentUnit.territory}`;
    const order = `${unitStr} - ${destAbbr}`;
    this.submitOrder(order);
    this.clearHighlights();
    this.hide();
  }

  /**
   * Complete support hold order
   */
  completeSupportHoldOrder(targetTerritory) {
    const unitStr = `${this.currentUnit.type} ${this.currentUnit.territory}`;
    // Find unit to support
    const supportedUnit = this.state.units.find(u => u.territory === targetTerritory && 
                                                      u.owner === this.selectedPower &&
                                                      !u.dislodged);
    if (supportedUnit) {
      const supportedStr = `${supportedUnit.type} ${targetTerritory}`;
      const order = `${unitStr} S ${supportedStr} H`;
      this.submitOrder(order);
    }
    this.clearHighlights();
    this.hide();
  }

  /**
   * Start second phase of support: select advance destination
   */
  startAdvanceSupportDestinationSelection(sourceTerritory) {
    this.selectionState.advanceSupportSource = sourceTerritory;
    this.clearHighlights();
    
    // Show adjacent territories to source for advance
    const byAbbr = Object.fromEntries(mapData.territories.map(t => [t.abbr, t]));
    const sourceTerr = byAbbr[sourceTerritory];
    
    if (!sourceTerr) return;

    const adjacentNames = sourceTerr.adjacents || [];
    for (const adjName of adjacentNames) {
      const adjTerr = mapData.territories.find(t => t.name === adjName);
      if (adjTerr) {
        this.highlightTerritory(adjTerr.abbr, 'support-target');
      }
    }

    this.showMessage(`Click on a territory for the unit to advance to.`);
  }

  /**
   * Start second phase of convoy: select destination
   */
  startConvoyDestinationSelection(sourceTerritory) {
    this.selectionState.mode = 'convoy-destination';
    this.selectionState.convoySource = sourceTerritory;
    this.clearHighlights();
    
    // Show adjacent territories to source for advance
    const byAbbr = Object.fromEntries(mapData.territories.map(t => [t.abbr, t]));
    const sourceTerr = byAbbr[sourceTerritory];
    
    if (!sourceTerr) return;

    const adjacentNames = sourceTerr.adjacents || [];
    for (const adjName of adjacentNames) {
      const adjTerr = mapData.territories.find(t => t.name === adjName);
      if (adjTerr) {
        this.highlightTerritory(adjTerr.abbr, 'convoy-target');
      }
    }

    this.showMessage(`Click on a territory for the army to advance to.`);
  }

  /**
   * Complete support advance order
   */
  completeSupportAdvanceOrder(destAbbr) {
    const supportSource = this.selectionState.advanceSupportSource || this.selectionState.supportSource;
    if (!supportSource) {
      this.showMessage('Error: No source unit selected.');
      return;
    }

    const unitStr = `${this.currentUnit.type} ${this.currentUnit.territory}`;
    const supportedUnit = this.state.units.find(u => u.territory === supportSource && 
                                                     u.owner === this.selectedPower &&
                                                     !u.dislodged);
    if (supportedUnit) {
      const supportedStr = `${supportedUnit.type} ${supportSource}`;
      const order = `${unitStr} S ${supportedStr} - ${destAbbr}`;
      this.submitOrder(order);
    }
    this.clearHighlights();
    this.hide();
  }

  /**
   * Complete convoy order after destination selection
   */
  completeConvoyOrder(destAbbr) {
    const convoyed = this.selectionState.convoySource;
    if (!convoyed) {
      this.showMessage('Error: No army selected for convoy.');
      return;
    }

    const unitStr = `${this.currentUnit.type} ${this.currentUnit.territory}`;
    const army = this.state.units.find(u => u.territory === convoyed && 
                                            u.owner === this.selectedPower &&
                                            !u.dislodged);
    if (army) {
      const armyStr = `${army.type} ${convoyed}`;
      const order = `${unitStr} C ${armyStr} - ${destAbbr}`;
      this.submitOrder(order);
    }
    this.clearHighlights();
    this.hide();
  }

  /**
   * Hide the radial menu
   */
  hide() {
    if (this.menuGroup) {
      this.menuGroup.innerHTML = '';
    }
    this.isVisible = false;
    this.currentUnit = null;
    this.selectionMode = null;
  }

  /**
   * Destroy the menu
   */
  destroy() {
    this.clearHighlights();
    this.hide();
    if (this.menuGroup && this.menuGroup.parentNode) {
      this.menuGroup.parentNode.removeChild(this.menuGroup);
    }
  }
}

// Global radial menu instance
let radialMenu = null;

/**
 * Initialize the radial menu system
 */
function initRadialMenu(svgElement) {
  if (!radialMenu || radialMenu.svg !== svgElement) {
    radialMenu = new RadialMenu();
    radialMenu.initialize(svgElement);
  }
  return radialMenu;
}

/**
 * Handle map click for order selection with radial menu
 */
function handleMapClickWithRadialMenu(event, availableOrders, state, power, phase) {
  const unit = event.target.closest('.unit');
  const territory = event.target.closest('.territory');

  // Debug logging
  console.log('[RadialMenu] Click detected', {
    phase,
    hasUnit: !!unit,
    hasTerritory: !!territory,
    unitTerritory: unit?.dataset.territory,
    power,
    availableOrdersCount: availableOrders.length
  });

  // For adjustment phase, use original logic
  if (phase.includes('Adjustment')) {
    selectMapTerritory(territory ? territory.id.slice(5) : unit.dataset.territory);
    return;
  }

  // For retreat phase, handle advance-only highlighting
  if (phase.includes('Retreat')) {
    handleRetreatSelection(event, availableOrders, state, power);
    return;
  }

  // If radial menu is active and processing a multi-step selection
  if (radialMenu && radialMenu.isVisible && radialMenu.selectionMode) {
    if (territory) {
      radialMenu.handleTerritorySelection(territory.id.slice(5));
    } else if (unit) {
      radialMenu.handleUnitSelection(unit.dataset);
    }
    return;
  }

  // For Spring/Fall, show radial menu
  if (unit && unit.dataset.territory) {
    console.log('[RadialMenu] Showing menu for unit', unit.dataset.territory);
    
    const unitData = state.units.find(u => u.territory === unit.dataset.territory &&
                                             u.owner === unit.dataset.owner &&
                                             u.type === unit.dataset.type);

    console.log('[RadialMenu] Unit data found:', unitData);

    if (unitData && unitData.owner === power) {
      const rect = unit.getBoundingClientRect();
      const point = svg.createSVGPoint();
      point.x = rect.left + rect.width / 2;
      point.y = rect.top + rect.height / 2;
      const position = point.matrixTransform(svg.getScreenCTM().inverse());

      console.log('[RadialMenu] Position calculated:', position);

      if (!radialMenu) {
        console.log('[RadialMenu] Initializing menu');
        initRadialMenu(svg);
      }

      console.log('[RadialMenu] Showing menu for unit');
      radialMenu.showForUnit(unitData, unit.dataset.territory, position, availableOrders, state, power);
    } else {
      console.log('[RadialMenu] Unit not owned by player or unit data not found');
    }
  } else {
    console.log('[RadialMenu] Click was not on a unit');
  }
}

/**
 * Handle retreat phase selection (advance-only, no convoy)
 */
function handleRetreatSelection(event, availableOrders, state, power) {
  const unit = event.target.closest('.unit');
  const territory = event.target.closest('.territory');

  if (unit && unit.dataset.territory) {
    const unitTerritory = unit.dataset.territory;
    const byAbbr = Object.fromEntries(mapData.territories.map(t => [t.abbr, t]));
    const currentTerritory = byAbbr[unitTerritory];

    if (!currentTerritory) return;

    // Clear previous highlights
    document.querySelectorAll('.retreat-target').forEach(el => {
      el.classList.remove('retreat-target');
    });

    // Highlight adjacent territories
    const adjacentNames = currentTerritory.adjacents || [];
    const adjacentAbbrs = [];
    for (const adjName of adjacentNames) {
      const adjTerr = mapData.territories.find(t => t.name === adjName);
      if (adjTerr) {
        adjacentAbbrs.push(adjTerr.abbr);
      }
    }

    for (const adjAbbr of adjacentAbbrs) {
      const element = document.getElementById(`terr-${adjAbbr}`);
      if (element) {
        element.classList.add('retreat-target');
      }
    }

    document.getElementById('map-order-status').textContent =
      `Select a territory to retreat ${unit.dataset.type === 'A' ? 'army' : 'fleet'} from ${currentTerritory.name}.`;
  }

  if (territory) {
    const abbr = territory.id.slice(5);
    const dislodgedUnit = state.units.find(u => u.dislodged_from === abbr && u.owner === power);

    if (dislodgedUnit) {
      selectMapTerritory(abbr);
    }
  }
}
