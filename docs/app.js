const SVG_NS = 'http://www.w3.org/2000/svg';
const CONSOLE_HELP = `
Diplomacy console API (window.diplomacy):
  diplomacy.order("A PAR - BUR", "France")  submit one order
  diplomacy.orders(["A PAR H", ...], "France")  submit several
  diplomacy.resolve()                       adjudicate and redraw
  diplomacy.state                           latest game state
  diplomacy.newGame()                       restart
Order syntax is case-sensitive: "A PAR - BUR", "F NTH C A LON - BEL",
"Build A PAR", "Remove A PAR", "F STP(nc) - BAR".`;

let pyodide, api, mapData, svg;

let greatPower;
let queuedOrders = {};

function setStatus(text) {
  document.getElementById('status').textContent = text;
}

async function loadPython() {
  pyodide = await loadPyodide();
  const manifest = await (await fetch('py/manifest.json')).json();
  pyodide.FS.mkdirTree('game');
  pyodide.FS.mkdirTree('data/maps');

  for (const path of manifest) {
    try {
      let text = await (await fetch('py/' + path)).text();
      pyodide.FS.writeFile("/" + path, text);
    } catch (e) {
      console.error(`Failed to load ${path}:`, e);
    }
  }
  try {
    pyodide.FS.writeFile('/data/maps/classic_map.json', await (await fetch('data/classic_map.json')).text());
  } catch (e) {
    console.error(`Failed to load classic_map.json:`, e);
  }
  pyodide.runPython(`
    import sys
    sys.path.insert(0, '/')
    import game.web_api as web_api
  `);
  api = pyodide.globals.get('web_api');
}

function call(fn, ...args) {
  return JSON.parse(api[fn](...args));
}

function smoothPolygons(polygons) {
  const edgeEpsilon = 10;
  function isEdgePoint(p, width, height) {
    const [x, y] = p;
    return (
      x <= edgeEpsilon ||
      y <= edgeEpsilon ||
      x >= width - edgeEpsilon ||
      y >= height - edgeEpsilon
    );
  }

  for (const poly of polygons) {
    for (let i = 0; i < poly.length; i++) {
      const p0 = poly[i];
      const p1 = poly[(i + 1) % poly.length];
      if (isEdgePoint(p0, mapData.width, mapData.height) || isEdgePoint(p1, mapData.width, mapData.height)) {
        continue;
      }
      const q = [0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1]];
      const r = [0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1]];
      poly.splice(i + 1, 0, q, r);
      i += 2;
    }
  }
  return polygons;
}

function buildMap() {
  const container = document.getElementById('map');
  container.innerHTML = '';
  svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${mapData.width} ${mapData.height}`);
  const bg = document.createElementNS(SVG_NS, 'rect');
  bg.setAttribute('width', mapData.width);
  bg.setAttribute('height', mapData.height);
  bg.setAttribute('fill', 'black');
  svg.appendChild(bg);

  for (const t of mapData.territories) {
    const polygons = smoothPolygons(t.polygons.map(poly => poly.map(i => mapData.vertices[i])));
    const d = polygons
      .map(poly => 'M' + poly.map(v => v.join(',')).join('L') + 'Z')
      .join(' ');
    const path = document.createElementNS(SVG_NS, 'path');
    path.setAttribute('d', d);
    path.setAttribute('class', 'territory');
    path.setAttribute('id', 'terr-' + t.abbr);
    path.setAttribute('fill-rule', 'evenodd');
    path.addEventListener('click', () => console.log(`${t.name} (${t.abbr})`));
    const title = document.createElementNS(SVG_NS, 'title');
    title.textContent = `${t.name} (${t.abbr})`;
    path.appendChild(title);
    svg.appendChild(path);
  }
  for (const t of mapData.territories) {
    const [x, y] = t.label_pos;
    const label = document.createElementNS(SVG_NS, 'text');
    label.setAttribute('class', 'label');
    label.setAttribute('x', x);
    label.setAttribute('y', y);
    label.textContent = t.abbr;
    svg.appendChild(label);
    if (t.land && t.supply_center) {
      const [sx, sy] = t.supply_center_pos;
      const c = document.createElementNS(SVG_NS, 'circle');
      c.setAttribute('cx', sx);
      c.setAttribute('cy', sy);
      c.setAttribute('r', 4);
      c.setAttribute('fill', '#000');
      svg.appendChild(c);
    }
  }
  const unitLayer = document.createElementNS(SVG_NS, 'g');
  unitLayer.setAttribute('id', 'units');
  svg.appendChild(unitLayer);
  container.appendChild(svg);
}

function unitPosition(t, unit) {
  if (!t.land) return t.fleet_pos;
  const coast = unit.coast;
  if (coast == 'nc')
    return t.coast_pos;
  else if (coast == 'sc')
    return t.south_coast_pos;
  return unit.type === 'A' ? t.army_pos : t.coast_pos;
}

function render(state) {
  const colors = Object.fromEntries(state.players.map(p => [p.name, p.color]));
  const byAbbr = Object.fromEntries(mapData.territories.map(t => [t.abbr, t]));
  for (const t of state.territories) {
    const el = document.getElementById('terr-' + t.abbr);
    const def = byAbbr[t.abbr];
    el.setAttribute('fill', t.owner ? colors[t.owner] : (def.land ? '#DDD' : mapData.water_color));
  }
  const layer = document.getElementById('units');
  layer.innerHTML = '';
  for (const u of state.units) {
    if (!u.territory || u.dislodged) continue;
    const [x, y] = unitPosition(byAbbr[u.territory], u);
    const g = document.createElementNS(SVG_NS, 'g');
    g.setAttribute('class', 'unit');
    const c = document.createElementNS(SVG_NS, 'circle');
    c.setAttribute('cx', x);
    c.setAttribute('cy', y);
    c.setAttribute('r', 10);
    c.setAttribute('fill', colors[u.owner]);
    const txt = document.createElementNS(SVG_NS, 'text');
    txt.setAttribute('x', x);
    txt.setAttribute('y', y);
    txt.textContent = u.type;
    g.append(c, txt);
    layer.appendChild(g);
  }

  // Remove old orders
  const oldOrders = document.querySelectorAll('line, polygon');
  oldOrders.forEach(el => el.remove());

  for (const o of state.orders) {
    // Render each order here
    if (o.type == 'Advance') {
      const from = byAbbr[o.territory];
      const to = byAbbr[o.dest_territory];
      const unit = state.units.find(u => u.territory === o.territory && !u.dislodged);
      if (unit) {
        const [fromX, fromY] = unitPosition(from, unit);
        const [toX, toY] = unitPosition(to, {'type': unit.type, 'coast': o.dest_coast});
        drawArrow(fromX, fromY, toX, toY, '#F00');
      }
    } else if (o.type == 'Support') {
      const from = byAbbr[o.territory];
      let [toX, toY] = [0, 0];
      if (o.supported_order_id != null) {
        let supported = state.orders[o.supported_order_id];
        if (supported && supported.type == 'Advance') {
          adv_from = byAbbr[supported.territory];
          adv_to = byAbbr[supported.dest_territory];

          const unit = state.units.find(u => u.territory === supported.territory && !u.dislodged);
          if (unit) {
            const [adv_fromX, adv_fromY] = unitPosition(adv_from, unit);
            const [adv_toX, adv_toY] = unitPosition(adv_to, {'type': unit.type, 'coast': supported.dest_coast});
            // to points to halfway between from and to for visual clarity
            toX = (adv_fromX + adv_toX) / 2;
            toY = (adv_fromY + adv_toY) / 2;
          }
        } else if (supported && supported.type == 'Hold') {
          loc = byAbbr[supported.territory];
          const unit = state.units.find(u => u.territory === supported.territory && !u.dislodged);
          if (unit) {
            [toX, toY] = unitPosition(loc, supported.unit);
          }
        }

        if (supported) {
          const unit = state.units.find(u => u.territory === o.territory && !u.dislodged);
          if (unit) {
            const [fromX, fromY] = unitPosition(from, unit);
            drawArrow(fromX, fromY, toX, toY, '#0F0');
          }
        }
      }
    }
  }

  setStatus(`${state.phase} phase, ${state.year}` + (state.winner ? ` — ${state.winner} wins!` : ''));
  window.diplomacy.state = state;
}

function drawArrow(fromX, fromY, toX, toY, color) {
  // Draw line
  const line = document.createElementNS(SVG_NS, 'line');
  line.setAttribute('x1', fromX);
  line.setAttribute('y1', fromY);
  line.setAttribute('x2', toX);
  line.setAttribute('y2', toY);
  line.setAttribute('stroke', color);
  line.setAttribute('stroke-width', '2');
  svg.appendChild(line);
  // Draw arrow point
  const arrow = document.createElementNS(SVG_NS, 'polygon');
  const arrowSize = 10;
  const angle = Math.atan2(toY - fromY, toX - fromX);
  const arrowPoints = [
    [toX, toY],
    [toX - arrowSize * Math.cos(angle - Math.PI / 6), toY - arrowSize * Math.sin(angle - Math.PI / 6)],
    [toX - arrowSize * Math.cos(angle + Math.PI / 6), toY - arrowSize * Math.sin(angle + Math.PI / 6)]
  ].map(p => p.join(',')).join(' ');
  arrow.setAttribute('points', arrowPoints);
  arrow.setAttribute('fill', color);
  svg.appendChild(arrow);
}

function populateGreatPowerSelect() {
  const select = document.getElementById('greatpower');
  select.innerHTML = '';
  const option = document.createElement('option');
  option.value = '';
  option.textContent = '-- Select a Great Power --';
  select.appendChild(option);
  select.addEventListener('change', () => {
    greatPower = select.value;
    setGreatPowerInfo();
  });
  for (const p of window.diplomacy.state.players) {
    const option = document.createElement('option');
    option.value = p.name;
    option.textContent = p.name;
    select.appendChild(option);
  }
}

async function init() {
  await loadPython();
  mapData = await (await fetch('data/classic_map.json')).json();
  buildMap();
  window.diplomacy = {
    state: null,
    newGame() { render(call('new_game')); },
    order(order, power) {
      const r = call('submit_order', order, power);
      render(call('get_state'));
      return r;
    },
    orders(list, power) { return list.map(o => this.order(o, power)); },
    resolve() { render(call('resolve')); },
    help() { console.log(CONSOLE_HELP); },
  };
  window.diplomacy.newGame();
  populateGreatPowerSelect();
  console.log(CONSOLE_HELP);
}

init().catch(e => { setStatus('Error: ' + e); console.error(e); });

const sidebar = document.getElementById('sidebar');
const mainContent = document.getElementById('main');
const toggleBtn = document.getElementById('toggleBtn');

function toggleSidebar() {
  if (sidebar.classList.contains('collapsed'))
    expandSidebar();
  else
    collapseSidebar();
}

function collapseSidebar() {
  sidebar.classList.add('collapsed');
  mainContent.classList.add('shifted');
}

function expandSidebar() {
  sidebar.classList.remove('collapsed');
  mainContent.classList.remove('shifted');
}

toggleBtn.addEventListener('click', toggleSidebar);

const infoElement = document.getElementById('info');
const orderErrorElement = document.getElementById("order-error");

function setGreatPowerInfo() {
  orderErrorElement.textContent = '';
  if (greatPower) {
    // If the current state is Spring or Fall, display the current units and their territories for the selected great power
    // Also list out the current orders for the selected great power
    const state = window.diplomacy.state;
    const player = state.players.find(p => p.name === greatPower);
    if (player) {
      if (state && (state.phase === 'Spring' || state.phase === 'Fall')) {
        infoElement.textContent = `Units for ${greatPower}:\n`;
        units = state.units;
        for (const unit of units) {
          if (unit.owner !== greatPower) continue;
          infoElement.textContent += `- ${unit.type} in ${unit.territory}\n`;
        }
      }

      // If the current state is Spring Retreat or Fall Retreat, display the dislodged units for the selected great power
      if (state && (state.phase === 'Spring Retreat' || state.phase === 'Fall Retreat')) {
        infoElement.textContent = `Dislodged units for ${greatPower}:\n`;
        units = state.units;
        for (const unit of units) {
          if (unit.owner !== greatPower) continue;
          if (!unit.dislodged) continue;
          infoElement.textContent += `- ${unit.type} in ${unit.dislodged_from}\n`;
        }
      }

      // If the current state is Adjustment, display how many units the selected great power can build or must disband
      // Also list out the supply centers that are available for the selected great power
      if (state && state.phase === 'Adjustment') {
        infoElement.textContent = `Adjustment for ${greatPower}:\n`;
        const unitsToBuild = player.units_to_build;
        if (unitsToBuild > 0) {
          infoElement.textContent += `- Units to build: ${unitsToBuild}\n`;

          // List out the supply centers if units need to be built
          const availableSupplyCenters = player.supply_centers;
          if (availableSupplyCenters && availableSupplyCenters.length > 0) {
            infoElement.textContent += `\nAvailable supply centers for ${greatPower}:\n`;
            for (const center of availableSupplyCenters) {
              infoElement.textContent += `- ${center}\n`;
            }
          }
        } else if (unitsToBuild < 0) {
          infoElement.textContent += `- Units to disband: ${unitsToBuild}\n`;
          
          // List out the current units for the selected great power that can be disbanded
          const currentUnits = state.units.filter(unit => unit.owner === greatPower);
          if (currentUnits && currentUnits.length > 0) {
            infoElement.textContent += `\nCurrent units for ${greatPower} that can be disbanded:\n`;
            for (const unit of currentUnits) {
              infoElement.textContent += `- ${unit.type} in ${unit.territory}\n`;
            }
          }
        }
      }

      // list out the current orders for the selected great power from queuedOrders
      if (queuedOrders[greatPower] && queuedOrders[greatPower].length > 0) {
        infoElement.textContent += `\nCurrent orders for ${greatPower}:\n`;
        for (const order of queuedOrders[greatPower]) {
          infoElement.textContent += `- ${order}\n`;
        }
      }
    }
  } else {
    infoElement.textContent = '';
  }
}

function clearGreatPowerInfo() {
  if (infoElement) {
    infoElement.textContent = '';
  }
}

document.getElementById("submit-order").addEventListener("click", () => {
  const order = document.getElementById("order").value;
  const power = document.getElementById("greatpower").value;

  const ok = window.diplomacy.order(order, power);
  if (ok.ok) {
    if (!queuedOrders[power]) {
      queuedOrders[power] = [];
    }
    queuedOrders[power].push(order);
    orderErrorElement.textContent = 'Order submitted successfully!';
    setGreatPowerInfo();
  } else {
    orderErrorElement.textContent = `Error submitting order for ${power}: ${ok['error']}`;
  }
});

document.getElementById("resolve").addEventListener("click", () => {
  window.diplomacy.resolve();
  // After resolving, clear the queued orders
  queuedOrders = {};
  // Reset great power
  document.getElementById("greatpower").value = '';
  clearGreatPowerInfo();

  // Clear the order input field
  document.getElementById("order").value = '';
});