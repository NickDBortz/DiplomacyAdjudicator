const SVG_NS = 'http://www.w3.org/2000/svg';

// Backend base URL; override with ?api=<url> or localStorage 'diplomacyApi'.
const API_BASE = (new URLSearchParams(location.search).get('api')
  || localStorage.getItem('diplomacyApi')
  || (['localhost', '127.0.0.1'].includes(location.hostname) ? 'http://localhost:8001' : 'https://YOUR-SERVICE.onrender.com')
).replace(/\/$/, '');

let mapData, svg;
window.diplomacy = window.diplomacy || { state: null };

function setStatus(text) {
  document.getElementById('status').textContent = text;
}

async function request(method, path, body) {
  const res = await fetch(API_BASE + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${method} ${path} failed: ${res.status} ${await res.text()}`);
  return res.json();
}

function goTo(page) {
  location.href = page;
}

function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('main');
  document.getElementById('toggleBtn').addEventListener('click', () => {
    const collapsed = sidebar.classList.toggle('collapsed');
    mainContent.classList.toggle('shifted', collapsed);
  });
}

function confirmAction(title, message, callback) {
  const modal = document.getElementById('confirm-modal');

  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-message').textContent = message;

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
    close();
    callback();
  };
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
    for (let x = 0; x < 2; x++) {
      const next = [];
      for (let i = 0; i < poly.length; i++) {
        const p0 = poly[i];
        const p1 = poly[(i + 1) % poly.length];
        if (isEdgePoint(p0, mapData.width, mapData.height) || isEdgePoint(p1, mapData.width, mapData.height)) {
          next.push(p0);
          continue;
        }
        const q = [0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1]];
        const r = [0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1]];
        next.push(q, r);
      }
      poly.splice(0, poly.length, ...next);
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

async function loadMap() {
  mapData = await (await fetch('data/classic_map.json')).json();
  buildMap();
}

function unitPosition(t, unit) {
  if (!t.land) return t.fleet_pos;
  if (unit.type === 'A') return t.army_pos;
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
          const adv_from = byAbbr[supported.territory];
          const adv_to = byAbbr[supported.dest_territory];

          const unit = state.units.find(u => u.territory === supported.territory && !u.dislodged);
          if (unit) {
            const [adv_fromX, adv_fromY] = unitPosition(adv_from, unit);
            const [adv_toX, adv_toY] = unitPosition(adv_to, {'type': unit.type, 'coast': supported.dest_coast});
            // to points to halfway between from and to for visual clarity
            toX = (adv_fromX + adv_toX) / 2;
            toY = (adv_fromY + adv_toY) / 2;
          }
        } else if (supported) {
          const loc = byAbbr[supported.territory];
          const unit = state.units.find(u => u.territory === supported.territory && !u.dislodged);
          if (unit) {
            [toX, toY] = unitPosition(loc, unit);
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

  setStatus(`${state.phase} phase, ${state.year}`);
  const popup = document.getElementById('outcome-popup');
  if (popup && (state.winner || state.draw)) {
    popup.classList.remove('hidden');
    document.getElementById('outcome-title').textContent = state.winner ? 'Victory!' : 'Draw!';
    document.getElementById('outcome-message').textContent = state.winner
      ? `${state.winner} controls 18 supply centers and wins the game!`
      : 'All players chose to draw. The game ends in a draw.';
  }
  window.diplomacy.state = state;
}

function drawArrow(fromX, fromY, toX, toY, color) {
  const line = document.createElementNS(SVG_NS, 'line');
  line.setAttribute('x1', fromX);
  line.setAttribute('y1', fromY);
  line.setAttribute('x2', toX);
  line.setAttribute('y2', toY);
  line.setAttribute('stroke', color);
  line.setAttribute('stroke-width', '2');
  svg.appendChild(line);
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
