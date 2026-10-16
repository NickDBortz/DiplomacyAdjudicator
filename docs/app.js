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

function setStatus(text) {
  document.getElementById('status').textContent = text;
}

async function loadPython() {
  pyodide = await loadPyodide();
  const manifest = await (await fetch('py/manifest.json')).json();
  pyodide.FS.mkdirTree('game');
  pyodide.FS.mkdirTree('data/maps');
  for (const path of manifest) {
    pyodide.FS.writeFile(path, await (await fetch('py/' + path)).text());
  }
  pyodide.FS.writeFile('data/maps/classic_map.json', await (await fetch('data/classic_map.json')).text());
  pyodide.runPython('import game.web_api as web_api');
  api = pyodide.globals.get('web_api');
}

function call(fn, ...args) {
  return JSON.parse(api[fn](...args));
}

function buildMap() {
  const container = document.getElementById('map');
  container.innerHTML = '';
  svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${mapData.width} ${mapData.height}`);
  const bg = document.createElementNS(SVG_NS, 'rect');
  bg.setAttribute('width', mapData.width);
  bg.setAttribute('height', mapData.height);
  bg.setAttribute('fill', mapData.water_color);
  svg.appendChild(bg);

  for (const t of mapData.territories) {
    const d = t.polygons
      .map(poly => 'M' + poly.map(i => mapData.vertices[i].join(',')).join('L') + 'Z')
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
  setStatus(`${state.phase} phase, ${state.year}` + (state.winner ? ` — ${state.winner} wins!` : ''));
  window.diplomacy.state = state;
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
      console.log(r.ok ? `Accepted: ${order}` : `Rejected: ${order}`);
      render(call('get_state'));
      return r.ok;
    },
    orders(list, power) { return list.map(o => this.order(o, power)); },
    resolve() { render(call('resolve')); },
    help() { console.log(CONSOLE_HELP); },
  };
  window.diplomacy.newGame();
  console.log(CONSOLE_HELP);
}

init().catch(e => { setStatus('Error: ' + e); console.error(e); });
