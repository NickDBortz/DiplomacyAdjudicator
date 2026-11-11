const RADIAL_MENU_CONFIG = {
  radius: 80,
  innerRadius: 30,
  colors: {
    Hold: '#4CAF50',
    Advance: '#2196F3',
    Support: '#FF9800',
    Transform: '#9C27B0',
    Convoy: '#F44336',
  },
};

class RadialMenu {
  constructor() {
    this.svg = null;
    this.menuGroup = null;
    this.currentUnit = null;
    this.orders = [];
    this.selectionMode = null;
    this.selectionSource = null;
    this.highlights = new Map();
  }

  initialize(svgElement) {
    this.svg = svgElement;
    this.menuGroup = document.createElementNS(SVG_NS, 'g');
    this.menuGroup.setAttribute('id', 'radial-menu');
    this.menuGroup.setAttribute('class', 'radial-menu-group');
    this.svg.appendChild(this.menuGroup);
  }

  showForUnit(unit, position, availableOrders, state) {
    this.cancel();
    this.currentUnit = unit;
    this.state = state;
    this.orders = availableOrders.filter(order => order.unit === `${unit.type} ${unit.territory}`);
    if (!this.orders.length) {
      setPickerStatus('No available orders for this unit.');
      this.currentUnit = null;
      return;
    }

    setMapOrderSelection(`${unit.type} ${unit.territory}`, '', []);
    const availableTypes = new Set(this.orders.map(order => order.type === 'Move' ? 'Advance' : order.type));
    const types = ['Hold', 'Advance', 'Support', 'Transform', 'Convoy'];
    types.forEach((type, index) => {
      const angle = index * Math.PI * 2 / types.length - Math.PI / 2;
      const x = position.x + Math.cos(angle) * RADIAL_MENU_CONFIG.radius;
      const y = position.y + Math.sin(angle) * RADIAL_MENU_CONFIG.radius;
      this.createMenuItem(type, x, y, angle, availableTypes.has(type));
    });

    const center = document.createElementNS(SVG_NS, 'circle');
    center.setAttribute('cx', position.x);
    center.setAttribute('cy', position.y);
    center.setAttribute('r', RADIAL_MENU_CONFIG.innerRadius);
    center.setAttribute('fill', '#555');
    center.setAttribute('stroke', '#fff');
    center.setAttribute('stroke-width', 2);
    center.setAttribute('class', 'radial-menu-center');
    this.menuGroup.appendChild(center);
  }

  createMenuItem(type, x, y, angle, isAvailable) {
    const group = document.createElementNS(SVG_NS, 'g');
    group.setAttribute('class', `radial-menu-item ${isAvailable ? 'available' : 'disabled'}`);
    group.setAttribute('data-type', type);
    group.style.setProperty('--hover-x', `${Math.cos(angle) * 8}px`);
    group.style.setProperty('--hover-y', `${Math.sin(angle) * 8}px`);
    if (!isAvailable) group.style.pointerEvents = 'none';

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
    circle.setAttribute('fill', RADIAL_MENU_CONFIG.colors[type]);
    circle.setAttribute('stroke', '#fff');
    circle.setAttribute('stroke-width', 2);
    circle.setAttribute('class', 'radial-menu-bg');
    visual.appendChild(circle);
    const text = document.createElementNS(SVG_NS, 'text');
    text.setAttribute('x', x);
    text.setAttribute('y', y);
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('dominant-baseline', 'middle');
    text.setAttribute('fill', '#fff');
    text.setAttribute('font-weight', 'bold');
    text.setAttribute('font-size', '11');
    if (type.length > 6) {
      text.setAttribute('textLength', 42);
      text.setAttribute('lengthAdjust', 'spacingAndGlyphs');
    }
    text.textContent = type;
    visual.appendChild(text);
    group.appendChild(visual);
    if (isAvailable) {
      group.addEventListener('click', event => {
        event.stopPropagation();
        this.selectType(type);
      });
    }
    this.menuGroup.appendChild(group);
  }

  selectType(type) {
    const pickerType = type === 'Advance' ? 'Move' : type;
    const unit = `${this.currentUnit.type} ${this.currentUnit.territory}`;
    this.menuGroup.innerHTML = '';
    this.clearHighlights();
    setMapOrderSelection(unit, pickerType);

    if (type === 'Hold' || type === 'Transform') {
      if (!document.getElementById('order-choice').value) {
        setPickerStatus('Choose the desired order in the sidebar, then submit it.');
      }
      this.cancel();
      return;
    }

    this.selectionMode = pickerType;
    this.selectionSource = null;
    if (pickerType === 'Move') {
      this.highlightMoveTargets();
      setPickerStatus('Select a highlighted destination.');
    } else {
      this.highlightSourceUnits(pickerType);
      setPickerStatus(pickerType === 'Support'
        ? 'Select a highlighted unit or its territory to support.'
        : 'Select a highlighted army or its territory to convoy.');
    }
  }

  ordersForType() {
    const type = this.selectionMode === 'Retreat' ? 'Move' : this.selectionMode;
    return this.orders.filter(order => order.type === type);
  }

  highlight(element, className) {
    if (!element) return;
    element.classList.add(className);
    if (!this.highlights.has(element)) this.highlights.set(element, new Set());
    this.highlights.get(element).add(className);
  }

  clearHighlights() {
    for (const [element, classes] of this.highlights) {
      for (const className of classes) element.classList.remove(className);
    }
    this.highlights.clear();
  }

  highlightMoveTargets() {
    const origin = mapData.territories.find(territory => territory.abbr === this.currentUnit.territory);
    const destinations = new Map();
    for (const order of this.ordersForType()) {
      const target = orderMapTargets(order)[0];
      const territory = mapData.territories.find(item => item.abbr === target);
      const convoy = /\s+via convoy$/i.test(order.text) ||
        (this.currentUnit.type === 'A' && origin && territory && !(origin.adjacents || []).includes(territory.name));
      const modes = destinations.get(target) || new Set();
      modes.add(convoy ? 'convoy' : 'regular');
      destinations.set(target, modes);
    }
    for (const [target, modes] of destinations) {
      const className = modes.size > 1 ? 'checkerboard-convoy'
        : modes.has('convoy') ? 'convoy-target' : 'advance-target';
      if (className === 'checkerboard-convoy') this.ensureCheckerboard();
      this.highlight(document.getElementById(`terr-${target}`), className);
    }
  }

  ensureCheckerboard() {
    if (this.svg.querySelector('#radial-convoy-pattern')) return;
    const defs = document.createElementNS(SVG_NS, 'defs');
    const pattern = document.createElementNS(SVG_NS, 'pattern');
    pattern.setAttribute('id', 'radial-convoy-pattern');
    pattern.setAttribute('patternUnits', 'userSpaceOnUse');
    pattern.setAttribute('width', 20);
    pattern.setAttribute('height', 20);
    for (const [x, y, width, height, fill] of [
      [0, 0, 20, 20, '#90EE90'], [0, 0, 10, 10, '#87CEEB'], [10, 10, 10, 10, '#87CEEB'],
    ]) {
      const rect = document.createElementNS(SVG_NS, 'rect');
      for (const [key, value] of Object.entries({ x, y, width, height, fill })) rect.setAttribute(key, value);
      pattern.appendChild(rect);
    }
    defs.appendChild(pattern);
    this.svg.insertBefore(defs, this.svg.firstChild);
  }

  highlightSourceUnits(type) {
    const targets = new Set(this.ordersForType().map(order => orderMapTargets(order)[0]));
    for (const unit of this.state.units) {
      if (unit.dislodged || !targets.has(unit.territory)) continue;
      this.highlight(document.getElementById(`terr-${unit.territory}`),
        type === 'Support' ? 'support-target' : 'convoy-target');
      for (const marker of this.svg.querySelectorAll('#units .unit')) {
        if (marker.dataset.territory === unit.territory && marker.dataset.type === unit.type &&
            marker.dataset.owner === unit.owner) {
          this.highlight(marker, type === 'Support' ? 'support-target' : 'convoy-target');
        }
      }
    }
  }

  highlightDestinations(orders) {
    for (const order of orders) {
      const targets = orderMapTargets(order);
      if (targets.length > 1) {
        this.highlight(document.getElementById(`terr-${targets[1]}`),
          this.selectionMode === 'Support' ? 'support-target' : 'convoy-target');
      }
    }
  }

  selectTarget(abbr) {
    const unit = `${this.currentUnit.type} ${this.currentUnit.territory}`;
    const orders = this.ordersForType();
    if (this.selectionMode === 'Retreat') {
      if (!orders.some(order => orderMapTargets(order)[0] === abbr)) {
        setPickerStatus('Select a highlighted retreat destination.');
        return;
      }
      const matches = setMapOrderSelection(unit, 'Move', [abbr]);
      if (matches.length > 1) setPickerStatus('Choose the desired retreat in the sidebar, then submit it.');
      this.cancel();
      return;
    }
    if (this.selectionMode === 'Move') {
      if (!orders.some(order => orderMapTargets(order)[0] === abbr)) {
        setPickerStatus('Select a highlighted destination.');
        return;
      }
      const matches = setMapOrderSelection(unit, 'Move', [abbr]);
      if (matches.length > 1) setPickerStatus('Choose the desired move in the sidebar, then submit it.');
      this.cancel();
      return;
    }

    if (!this.selectionSource) {
      const matches = orders.filter(order => orderMapTargets(order)[0] === abbr);
      if (!matches.length) {
        setPickerStatus('Select a highlighted unit or its territory.');
        return;
      }
      this.selectionSource = abbr;
      const hold = matches.filter(order => orderMapTargets(order).length === 1);
      setMapOrderSelection(unit, this.selectionMode, [abbr], hold.length === 1 ? hold[0].text : '');
      this.clearHighlights();
      const moves = matches.filter(order => orderMapTargets(order).length > 1);
      if (moves.length) {
        this.highlightDestinations(moves);
        setPickerStatus(hold.length === 1
          ? 'Support hold selected. Submit it, or select a highlighted destination to support a move.'
          : 'Select a highlighted destination.');
      } else {
        if (hold.length !== 1) setPickerStatus('Choose the desired order in the sidebar, then submit it.');
        this.cancel();
      }
      return;
    }

    const matches = orders.filter(order => {
      const targets = orderMapTargets(order);
      return targets[0] === this.selectionSource && targets[1] === abbr;
    });
    if (!matches.length) {
      setPickerStatus('Select a highlighted destination.');
      return;
    }
    setMapOrderSelection(unit, this.selectionMode, [this.selectionSource, abbr]);
    if (matches.length > 1) setPickerStatus('Choose the desired order in the sidebar, then submit it.');
    this.cancel();
  }

  cancel() {
    this.clearHighlights();
    if (this.menuGroup) this.menuGroup.innerHTML = '';
    this.currentUnit = null;
    this.selectionMode = null;
    this.selectionSource = null;
  }
}

let radialMenu = null;

function initRadialMenu(svgElement) {
  if (!radialMenu || radialMenu.svg !== svgElement) {
    radialMenu = new RadialMenu();
    radialMenu.initialize(svgElement);
  }
  return radialMenu;
}

function handleMapClickWithRadialMenu(event, availableOrders, state, power, phase) {
  const marker = event.target.closest('.unit');
  const territory = event.target.closest('.territory');
  const abbr = marker ? marker.dataset.territory : territory ? territory.id.slice(5) : null;
  if (!abbr) return;

  if (phase.includes('Retreat')) {
    if (radialMenu.selectionMode === 'Retreat') {
      radialMenu.selectTarget(abbr);
      return;
    }
    const unit = state.units.find(item => item.dislodged && item.dislodged_from === abbr && item.owner === power);
    if (!unit) return;
    radialMenu.cancel();
    radialMenu.currentUnit = { ...unit, territory: abbr };
    radialMenu.orders = availableOrders.filter(order =>
      order.unit === `${unit.type} ${abbr}` && order.type === 'Move' && !/\s+via convoy$/i.test(order.text));
    if (!radialMenu.orders.length) {
      radialMenu.cancel();
      setPickerStatus('No available retreats for this unit.');
      return;
    }
    radialMenu.selectionMode = 'Retreat';
    setMapOrderSelection(`${unit.type} ${abbr}`, 'Move');
    for (const order of radialMenu.orders) {
      radialMenu.highlight(document.getElementById(`terr-${orderMapTargets(order)[0]}`), 'retreat-target');
    }
    setPickerStatus('Select a highlighted retreat destination.');
    return;
  }
  if (radialMenu.selectionMode) {
    radialMenu.selectTarget(abbr);
    return;
  }

  const unit = state.units.find(item => !item.dislodged && item.territory === abbr && item.owner === power);
  if (!unit) return;
  const unitMarker = marker || [...svg.querySelectorAll('#units .unit')].find(item =>
    item.dataset.territory === unit.territory && item.dataset.owner === unit.owner && item.dataset.type === unit.type);
  if (!unitMarker) {
    setPickerStatus('Could not locate the selected unit on the map.');
    return;
  }
  const rect = unitMarker.getBoundingClientRect();
  const point = svg.createSVGPoint();
  point.x = rect.left + rect.width / 2;
  point.y = rect.top + rect.height / 2;
  const position = point.matrixTransform(svg.getScreenCTM().inverse());
  radialMenu.showForUnit(unit, position, availableOrders, state);
}
