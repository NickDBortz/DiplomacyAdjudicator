/**
 * Interactive Map-based Order Picker
 * Allows players to click territories on the map to select orders
 */

let mapOrderPickerState = {
  selectedUnit: null,
  selectedTarget: null,
  isSelecting: false,
  availableTargets: new Set(),
};

const TERRITORY_SELECTION_COLORS = {
  SOURCE: '#FFD700',      // Gold for source/unit selection
  TARGET: '#FF6347',      // Red for target selection
  AVAILABLE: '#00FF00',   // Green for available targets
};

/**
 * Initialize the interactive map order picker
 * Should be called after the map is loaded
 */
function initMapOrderPicker() {
  const svg = document.querySelector('svg');
  if (!svg) return;

  // Add click event listeners to all territory paths
  svg.querySelectorAll('.territory').forEach(path => {
    path.addEventListener('click', (e) => handleTerritoryClick(e));
    path.style.cursor = 'pointer';
  });
}

/**
 * Handle territory click on the map
 */
function handleTerritoryClick(event) {
  if (!window.diplomacy.state) return;

  const path = event.target;
  const terrId = path.id;
  if (!terrId.startsWith('terr-')) return;

  const abbr = terrId.substring(5); // Remove 'terr-' prefix
  const state = window.diplomacy.state;
  const territory = mapData.territories.find(t => t.abbr === abbr);
  if (!territory) return;

  const power = document.getElementById('greatpower').value;
  if (!power) {
    showMapPickerMessage('Select a power first', 'error');
    return;
  }

  // If user clicks the same territory twice, treat as cancel/reset
  if (mapOrderPickerState.selectedUnit === abbr && !mapOrderPickerState.selectedTarget) {
    resetMapOrderPicker();
    showMapPickerMessage('Selection cleared. Click a territory to select a unit.', 'info');
    return;
  }

  // If user clicks selected target again, treat as deselect target
  if (mapOrderPickerState.selectedTarget === abbr) {
    mapOrderPickerState.selectedTarget = null;
    clearMapSelection();
    highlightTerritory(mapOrderPickerState.selectedUnit, TERRITORY_SELECTION_COLORS.SOURCE);
    showMapPickerMessage('Target cleared. Click a new destination.', 'info');
    return;
  }

  // Step 1: User hasn't selected a unit yet
  if (!mapOrderPickerState.selectedUnit) {
    selectUnitFromMap(abbr, territory, power, state);
  } 
  // Step 2: User has selected a unit, now selecting target/action
  else {
    selectTargetFromMap(abbr, territory, power, state);
  }
}

/**
 * Select a unit/source territory from the map
 */
function selectUnitFromMap(abbr, territory, power, state) {
  const phase = state.phase;
  
  // Handle movement phases
  if (phase === 'Spring' || phase === 'Fall') {
    const unit = state.units.find(u => u.territory === abbr && u.owner === power && !u.dislodged);
    if (!unit) {
      showMapPickerMessage(`${territory.name} has no units for ${power}`, 'error');
      return;
    }
    selectUnit(abbr, unit, power, state, territory);
  }
  // Handle retreat phases
  else if (phase === 'Spring Retreat' || phase === 'Fall Retreat') {
    const unit = state.units.find(u => u.dislodged_from === abbr && u.owner === power && u.dislodged);
    if (!unit) {
      showMapPickerMessage(`${territory.name} has no dislodged units for ${power}`, 'error');
      return;
    }
    selectUnit(abbr, unit, power, state, territory);
  }
  // Handle adjustment phase
  else if (phase === 'Adjustment') {
    // For building - check if it's a valid supply center
    if (territory.supply_center && territory.owner === power) {
      selectUnit(abbr, { type: 'BUILD', territory: abbr }, power, state, territory);
    } else {
      // For removing - check if there's a unit to remove
      const unit = state.units.find(u => u.territory === abbr && u.owner === power);
      if (!unit) {
        showMapPickerMessage(`${territory.name} is not a valid build/remove location`, 'error');
        return;
      }
      selectUnit(abbr, unit, power, state, territory);
    }
  }
}

/**
 * Helper to select a unit and update UI
 */
function selectUnit(abbr, unit, power, state, territory) {
  mapOrderPickerState.selectedUnit = abbr;
  const unitDisplay = unit.type === 'BUILD' ? `BUILD ${abbr}` : `${unit.type} ${abbr}`;
  
  // Update the UI
  clearMapSelection();
  highlightTerritory(abbr, TERRITORY_SELECTION_COLORS.SOURCE);
  
  // Update the dropdown
  const unitSelect = document.getElementById('order-unit');
  unitSelect.value = unitDisplay;
  unitSelect.dispatchEvent(new Event('change'));

  showMapPickerMessage(`Selected ${territory.name}. Click a destination or action territory.`, 'info');

  // Calculate and show available targets
  updateAvailableTargetsForUnit(state, power, unit);
}

/**
 * Select a target territory for the order
 */
function selectTargetFromMap(targetAbbr, targetTerritory, power, state) {
  const sourceAbbr = mapOrderPickerState.selectedUnit;
  if (!sourceAbbr) return;

  // Check for same territory - user might want to set hold
  if (sourceAbbr === targetAbbr) {
    const holdOrders = availableOrders.filter(o => {
      const sourceUnit = state.units.find(u => u.territory === sourceAbbr && u.owner === power);
      if (!sourceUnit) return false;
      const unitStr = `${sourceUnit.type} ${sourceAbbr}`;
      return o.unit === unitStr && o.type === 'Hold';
    });

    if (holdOrders.length > 0) {
      mapOrderPickerState.selectedTarget = targetAbbr;
      clearMapSelection();
      highlightTerritory(sourceAbbr, TERRITORY_SELECTION_COLORS.SOURCE);
      
      const choiceSelect = document.getElementById('order-choice');
      choiceSelect.value = holdOrders[0].text;
      choiceSelect.dispatchEvent(new Event('change'));
      
      showMapPickerMessage(`Order ready: Hold. Click Submit to confirm.`, 'success');
      return;
    }
  }

  const source = mapData.territories.find(t => t.abbr === sourceAbbr);
  const sourceUnit = state.units.find(u => u.territory === sourceAbbr && u.owner === power && !u.dislodged);
  
  // For retreat phase, dislodged units are the source
  let unitToMove = sourceUnit;
  if (!unitToMove && (state.phase === 'Spring Retreat' || state.phase === 'Fall Retreat')) {
    unitToMove = state.units.find(u => u.dislodged_from === sourceAbbr && u.owner === power && u.dislodged);
  }

  // Handle adjustment phase build
  if (!unitToMove && state.phase === 'Adjustment') {
    unitToMove = { type: 'BUILD', territory: sourceAbbr };
  }

  if (!unitToMove) {
    showMapPickerMessage(`No unit selected at ${source.name}`, 'error');
    return;
  }

  // Auto-detect order type based on source and target
  const suggestedOrders = suggestOrdersForMovement(state, power, unitToMove, sourceAbbr, targetAbbr, availableOrders);
  
  if (suggestedOrders.length === 0) {
    showMapPickerMessage(`No valid orders from ${source.name} to ${targetTerritory.name}`, 'error');
    return;
  }

  if (suggestedOrders.length === 1) {
    // Auto-select if only one option
    mapOrderPickerState.selectedTarget = targetAbbr;
    clearMapSelection();
    highlightTerritory(sourceAbbr, TERRITORY_SELECTION_COLORS.SOURCE);
    highlightTerritory(targetAbbr, TERRITORY_SELECTION_COLORS.TARGET);
    
    const choiceSelect = document.getElementById('order-choice');
    choiceSelect.value = suggestedOrders[0].text;
    choiceSelect.dispatchEvent(new Event('change'));
    
    showMapPickerMessage(`Order ready: ${suggestedOrders[0].text}. Click Submit to confirm.`, 'success');
  } else {
    // Show choice dialog if multiple options
    showOrderChoiceDialog(suggestedOrders, sourceAbbr, targetAbbr, targetTerritory);
  }
}

/**
 * Suggest valid orders for a movement from source to target
 */
function suggestOrdersForMovement(state, power, sourceUnit, sourceAbbr, targetAbbr, availableOrders) {
  if (!sourceUnit || !sourceAbbr) return [];

  const source = mapData.territories.find(t => t.abbr === sourceAbbr);
  const target = mapData.territories.find(t => t.abbr === targetAbbr);
  
  if (!source || !target) return [];

  // Handle special case for BUILD orders
  if (sourceUnit.type === 'BUILD') {
    const unitStr = `BUILD ${sourceAbbr}`;
    return availableOrders.filter(o => o.unit === unitStr);
  }

  const unitStr = `${sourceUnit.type} ${sourceAbbr}`;
  const matching = availableOrders.filter(o => {
    if (o.unit !== unitStr) return false;
    
    // Check if target is in the order text
    const text = o.text;
    const parts = text.split(' ');
    
    // For move orders: "A PAR - BUR" or "A PAR - BUR(nc)"
    if (parts.length >= 4 && parts[2] === '-') {
      const destTerritory = parts[3].replace(/\([^)]*\)/, '');
      if (destTerritory === targetAbbr) return true;
    }
    
    // For support: "A PAR S A BUR - GAS" or "A PAR S A BUR H"
    // Supporting unit move: source -> territory where supported unit is moving to
    if (parts.length >= 5 && parts[2] === 'S') {
      // Check if this is supporting a move
      if (parts.length >= 6 && parts[4] === '-') {
        const supportedDest = parts[5].replace(/\([^)]*\)/, '');
        if (supportedDest === targetAbbr) return true;
      }
      // Supporting a hold in target territory
      if (parts.length >= 4) {
        const supportedTerritory = parts[4].replace(/\([^)]*\)/, '');
        if (supportedTerritory === targetAbbr) return true;
      }
    }
    
    // For convoy: "A PAR C F ENG - BEL" - moving army from source via convoy
    if (parts[2] === 'C') {
      // Find the destination in the convoy order
      for (let i = 3; i < parts.length - 1; i++) {
        if (parts[i] === '-') {
          const convoyDest = parts[i + 1].replace(/\([^)]*\)/, '');
          if (convoyDest === targetAbbr) return true;
        }
      }
    }
    
    return false;
  });

  return matching;
}

/**
 * Show a dialog to choose between multiple orders
 */
function showOrderChoiceDialog(orders, sourceAbbr, targetAbbr, targetTerritory) {
  const sourceTerritory = mapData.territories.find(t => t.abbr === sourceAbbr);

  const modal = document.getElementById('confirm-modal');
  document.getElementById('modal-title').textContent = 'Choose Order Type';
  
  // Create list of order options
  const orderList = orders.map((o, i) => `${i + 1}. ${o.text}`).join('\n');
  document.getElementById('modal-message').textContent = 
    `Multiple orders possible from ${sourceTerritory.name} to ${targetTerritory.name}:\n\n${orderList}\n\nThe first option (move) will be selected by default.`;
  
  modal.classList.remove('hidden');
  
  const confirmBtn = document.getElementById('modal-confirm');
  const cancelBtn = document.getElementById('modal-cancel');
  
  const close = () => {
    modal.classList.add('hidden');
    confirmBtn.onclick = null;
    cancelBtn.onclick = null;
  };
  
  cancelBtn.onclick = close;
  confirmBtn.onclick = () => {
    // Select the first (move) order by default
    clearMapSelection();
    highlightTerritory(sourceAbbr, TERRITORY_SELECTION_COLORS.SOURCE);
    highlightTerritory(targetAbbr, TERRITORY_SELECTION_COLORS.TARGET);
    
    const choiceSelect = document.getElementById('order-choice');
    choiceSelect.value = orders[0].text;
    choiceSelect.dispatchEvent(new Event('change'));
    mapOrderPickerState.selectedTarget = targetAbbr;
    showMapPickerMessage(`Order selected: ${orders[0].text}. Click Submit to confirm.`, 'success');
    close();
  };
}

/**
 * Highlight a territory on the map
 */
function highlightTerritory(abbr, color) {
  const element = document.getElementById(`terr-${abbr}`);
  if (element) {
    element.classList.add('map-picker-highlight');
    element.style.filter = `drop-shadow(0 0 8px ${color})`;
  }
}

/**
 * Clear all map-based highlighting
 */
function clearMapSelection() {
  document.querySelectorAll('.map-picker-highlight').forEach(el => {
    el.classList.remove('map-picker-highlight');
    el.style.filter = '';
  });
}

/**
 * Reset the map order picker state
 */
function resetMapOrderPicker() {
  mapOrderPickerState.selectedUnit = null;
  mapOrderPickerState.selectedTarget = null;
  mapOrderPickerState.availableTargets.clear();
  clearMapSelection();
}

/**
 * Update available targets for the selected unit
 */
function updateAvailableTargetsForUnit(state, power, unit) {
  mapOrderPickerState.availableTargets.clear();
  
  if (!unit || !unit.territory) return;
  
  // Build unit string - handle different unit formats
  let unitStr;
  if (unit.type === 'BUILD') {
    unitStr = `BUILD ${unit.territory}`;
  } else if (unit.type === 'Remove' || unit.type === 'REMOVE') {
    unitStr = `Remove ${unit.territory}`;
  } else {
    unitStr = `${unit.type} ${unit.territory}`;
  }
  
  // Find all orders for this unit
  const unitOrders = availableOrders.filter(o => {
    if (o.unit === unitStr) return true;
    // Handle case variations
    if (o.text && o.text.toLowerCase().includes(unit.territory.toLowerCase())) {
      const parts = o.text.split(' ');
      const orderUnitStr = `${parts[0]} ${parts[1]}`;
      return orderUnitStr === unitStr || orderUnitStr.includes(unit.territory);
    }
    return false;
  });
  
  // Extract all target territories from these orders
  unitOrders.forEach(o => {
    const parts = o.text.split(' ');
    
    // Handle different order types
    if (parts[2] === '-' && parts[3]) {
      // Move/Advance order
      const target = parts[3].replace(/\([^)]*\)/, '');
      if (target) mapOrderPickerState.availableTargets.add(target);
    } else if (parts[2] === 'S' && parts[4]) {
      // Support order
      const target = parts[4].replace(/\([^)]*\)/, '');
      if (target) mapOrderPickerState.availableTargets.add(target);
    } else if (parts[2] === 'C') {
      // Convoy order - multiple possible destinations
      for (let i = 3; i < parts.length - 1; i++) {
        if (parts[i] === '-' && parts[i + 1]) {
          const convoyDest = parts[i + 1].replace(/\([^)]*\)/, '');
          if (convoyDest) mapOrderPickerState.availableTargets.add(convoyDest);
        }
      }
    } else if (parts[0] === 'Build' || parts[0] === 'Remove') {
      // Build/Remove orders don't have targets
      return;
    } else if (parts[2] === 'H') {
      // Hold order - add current territory
      mapOrderPickerState.availableTargets.add(unit.territory);
    }
  });
}

/**
 * Show message to user about map picker status
 */
function showMapPickerMessage(message, type = 'default') {
  const statusEl = document.getElementById('order-picker-status');
  if (statusEl) {
    statusEl.textContent = message;
    statusEl.style.color = type === 'error' ? '#ff6b6b' : type === 'success' ? '#51cf66' : type === 'info' ? '#4a90e2' : '#999';
  }
}

/**
 * Monitor dropdown changes and sync with map state
 */
function syncMapPickerWithDropdowns() {
  const unitSelect = document.getElementById('order-unit');
  const choiceSelect = document.getElementById('order-choice');
  
  if (unitSelect) {
    unitSelect.addEventListener('change', () => {
      // If user manually selects a unit, update map picker state
      if (unitSelect.value) {
        const abbr = unitSelect.value.split(' ').pop();
        mapOrderPickerState.selectedUnit = abbr;
        clearMapSelection();
        highlightTerritory(abbr, TERRITORY_SELECTION_COLORS.SOURCE);
      }
    });
  }

  if (choiceSelect) {
    choiceSelect.addEventListener('change', () => {
      // If user manually selects an order, extract target and highlight
      if (choiceSelect.value) {
        const parts = choiceSelect.value.split(' ');
        
        // Find target in the order text
        for (let i = 2; i < parts.length; i++) {
          if ((i === 3 && parts[i - 1] === '-') || (i === 4 && parts[i - 1] === 'S')) {
            const target = parts[i].replace(/\([^)]*\)/, '');
            if (target && mapData.territories.find(t => t.abbr === target)) {
              mapOrderPickerState.selectedTarget = target;
              highlightTerritory(target, TERRITORY_SELECTION_COLORS.TARGET);
              break;
            }
          }
        }
      }
    });
  }
}

/**
 * Add UI hint to order picker about map interaction
 */
function addMapPickerHint() {
  const orderPicker = document.querySelector('.order-picker');
  if (!orderPicker) return;

  const hint = document.createElement('div');
  hint.className = 'map-picker-hint';
  hint.innerHTML = `
    <p style="font-size: 12px; color: #888; margin: 8px 0 0 0;">
      💡 Tip: Click territories on the map to select units and targets, then submit the order.
    </p>
  `;
  orderPicker.insertBefore(hint, orderPicker.firstChild);
}

/**
 * Handle clear selection button - reset map picker
 */
function setupClearSelectionWithMapReset() {
  const clearBtn = document.getElementById('clear-order-selection');
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      resetMapOrderPicker();
    });
  }
}

/**
 * Initialize everything when the document is ready
 */
function initMapOrderPickerSystem() {
  // Wait for map to be loaded
  const checkMapLoaded = setInterval(() => {
    if (document.querySelector('svg') && mapData) {
      clearInterval(checkMapLoaded);
      initMapOrderPicker();
      syncMapPickerWithDropdowns();
      addMapPickerHint();
      setupClearSelectionWithMapReset();
    }
  }, 100);
}

// Start initialization when this script loads
document.addEventListener('DOMContentLoaded', () => {
  initMapOrderPickerSystem();
});
