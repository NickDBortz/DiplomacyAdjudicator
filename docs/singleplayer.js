const CONSOLE_HELP = `
Diplomacy console API (window.diplomacy):
  diplomacy.order("A PAR - BUR", "France")  submit one order
  diplomacy.orders(["A PAR H", ...], "France")  submit several
  diplomacy.resolve()                       adjudicate and redraw
  diplomacy.state                           latest game state
  diplomacy.newGame()                       restart
Order syntax is case-insensitive: "A PAR - BUR", "F NTH C A LON - BEL",
"Build A PAR", "Remove A PAR", "F STP(nc) - BAR".`;

let gameId;
let greatPower;
let drawVotes = [];
let queuedOrders = {};
let orderRequestId = 0;

const infoElement = document.getElementById('info');
const orderErrorElement = document.getElementById('order-error');

Object.assign(window.diplomacy, {
  async newGame() {
    const r = await request('POST', '/games');
    gameId = r.game_id;
    render(r.state);
    await refreshAvailableOrders();
  },
  async order(order, power) {
    const r = await request('POST', `/games/${gameId}/orders`, { order, power });
    render(r.state);
    if (r.ok) {
      resetOrderFilters();
      await refreshAvailableOrders();
    }
    return { ok: r.ok, error: r.error };
  },
  async orders(list, power) {
    const results = [];
    for (const o of list) results.push(await this.order(o, power));
    return results;
  },
  async resolve() {
    render(await request('POST', `/games/${gameId}/resolve`));
    await refreshAvailableOrders();
  },
  help() { console.log(CONSOLE_HELP); },
  async draw(power) {
    render(await request('POST', `/games/${gameId}/draw`, { power }));
    await refreshAvailableOrders();
  }
});

async function refreshAvailableOrders() {
  const requestId = ++orderRequestId;
  const power = greatPower;
  const currentGameId = gameId;
  if (!power || !currentGameId) {
    setOrderPicker([], 'Select a power to see available orders.');
    return;
  }
  setOrderPicker([], 'Loading available orders...');
  try {
    const result = await request('GET', `/games/${currentGameId}/valid-orders?power=${encodeURIComponent(power)}`);
    if (requestId !== orderRequestId || power !== greatPower || currentGameId !== gameId) return;
    if (!Array.isArray(result.valid_orders)) throw new Error('Invalid available orders response.');
    setOrderPicker(result.valid_orders);
  } catch (e) {
    if (requestId === orderRequestId) setOrderPicker([], `Could not load available orders: ${e.message}`);
  }
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
    refreshAvailableOrders();
  });
  for (const p of window.diplomacy.state.players) {
    const option = document.createElement('option');
    option.value = p.name;
    option.textContent = p.name;
    select.appendChild(option);
  }
}

function setGreatPowerInfo() {
  orderErrorElement.textContent = '';
  infoElement.textContent = '';
  if (greatPower) {
    const state = window.diplomacy.state;
    const player = state.players.find(p => p.name === greatPower);
    if (player) {
      if (drawVotes.length > 0) {
        infoElement.textContent += `A draw vote has been started.\n`;
        infoElement.textContent += `Players who have voted to draw:\n`;
        for (const voter of drawVotes) {
          infoElement.textContent += `- ${voter}\n`;
        }
        infoElement.textContent += `\n`;
      }

      if (state.phase === 'Spring' || state.phase === 'Fall') {
        infoElement.textContent += `Units for ${greatPower}:\n`;
        for (const unit of state.units) {
          if (unit.owner !== greatPower) continue;
          infoElement.textContent += `- ${unit.type} in ${unit.territory}\n`;
        }
      }

      if (state.phase === 'Spring Retreat' || state.phase === 'Fall Retreat') {
        infoElement.textContent += `Dislodged units for ${greatPower}:\n`;
        for (const unit of state.units) {
          if (unit.owner !== greatPower) continue;
          if (!unit.dislodged) continue;
          infoElement.textContent += `- ${unit.type} in ${unit.dislodged_from}\n`;
        }
      }

      if (state.phase === 'Adjustment') {
        infoElement.textContent += `Adjustment for ${greatPower}:\n`;
        const unitsToBuild = player.units_to_build;
        if (unitsToBuild > 0) {
          infoElement.textContent += `- Units to build: ${unitsToBuild}\n`;

          const availableSupplyCenters = player.supply_centers;
          if (availableSupplyCenters && availableSupplyCenters.length > 0) {
            infoElement.textContent += `\nAvailable supply centers for ${greatPower}:\n`;
            for (const center of availableSupplyCenters) {
              infoElement.textContent += `- ${center}\n`;
            }
          }
        } else if (unitsToBuild < 0) {
          infoElement.textContent += `- Units to disband: ${unitsToBuild}\n`;

          const currentUnits = state.units.filter(unit => unit.owner === greatPower);
          if (currentUnits.length > 0) {
            infoElement.textContent += `\nCurrent units for ${greatPower} that can be disbanded:\n`;
            for (const unit of currentUnits) {
              infoElement.textContent += `- ${unit.type} in ${unit.territory}\n`;
            }
          }
        }
      }

      if (queuedOrders[greatPower] && queuedOrders[greatPower].length > 0) {
        infoElement.textContent += `\nCurrent orders for ${greatPower}:\n`;
        for (const order of queuedOrders[greatPower]) {
          infoElement.textContent += `- ${order}\n`;
        }
      }
    }
  }
}

function resetLocalUi() {
  orderRequestId++;
  queuedOrders = {};
  drawVotes = [];
  document.getElementById('greatpower').value = '';
  greatPower = '';
  infoElement.textContent = '';
  setOrderPicker([], 'Select a power to see available orders.');
}

document.getElementById('submit-order').addEventListener('click', async () => {
  const order = document.getElementById('order-choice').value;
  const power = document.getElementById('greatpower').value;

  if (!power || !order) {
    orderErrorElement.textContent = 'Select a power and an order.';
    return;
  }
  try {
    const ok = await window.diplomacy.order(order, power);
    if (ok.ok) {
      if (!queuedOrders[power]) queuedOrders[power] = [];
      queuedOrders[power].push(order);
      setGreatPowerInfo();
      orderErrorElement.textContent = 'Order submitted successfully!';
    } else {
      orderErrorElement.textContent = `Error submitting order for ${power}: ${ok['error']}`;
    }
  } catch (e) {
    orderErrorElement.textContent = `Error submitting order for ${power}: ${e.message}`;
  }
});

document.getElementById('resolve').addEventListener('click', () => {
  confirmAction('Resolve Orders', 'Are you sure you want to resolve all orders?', async () => {
    await window.diplomacy.resolve();
    resetLocalUi();
  });
});

document.getElementById('new-game').addEventListener('click', () => {
  confirmAction('Start New Game', 'This will reset the current game. Continue?', async () => {
    await window.diplomacy.newGame();
    resetLocalUi();
  });
});

document.getElementById('outome-new-game').addEventListener('click', async () => {
  document.getElementById('outcome-popup').classList.add('hidden');
  await window.diplomacy.newGame();
  resetLocalUi();
});

document.getElementById('draw').addEventListener('click', () => {
  const power = document.getElementById('greatpower').value;
  if (power) {
    confirmAction('Draw Game', 'Are you sure you want to vote to draw?', async () => {
      await window.diplomacy.draw(power);
      drawVotes.push(power);
      setGreatPowerInfo();
    });
  }
});

document.getElementById('back-to-menu').addEventListener('click', () => goTo('index.html'));

async function init() {
  initSidebar();
  setStatus('Connecting to server (may take ~30s if it was asleep)...');
  await loadMap();
  await window.diplomacy.newGame();
  populateGreatPowerSelect();
  console.log(CONSOLE_HELP);
}

init().catch(e => { setStatus('Error: ' + e); console.error(e); });
