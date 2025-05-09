// Global variables
let aiModel;
let profitChart;
const marketData = new Map();
let lastExec = 0;

// Initialize the application
function init() {
  setupEventListeners();
  loadModel();
  connectWebSocket();
}

// Set up event listeners
function setupEventListeners() {
  // Sortable columns
  document.querySelectorAll('th[data-col]').forEach(th => {
    th.addEventListener('click', () => sortTable(parseInt(th.dataset.col)));
  });

  // Filter rows
  document.getElementById('filterInput').addEventListener('input', debounce(e => {
    const term = e.target.value.trim().toUpperCase();
    document.querySelectorAll('#results tr').forEach(r => {
      const txt = r.cells[0]?.innerText.toUpperCase() || '';
      r.style.display = txt.includes(term) ? '' : 'none';
    });
  }, 300));
}

// Debounce helper
function debounce(fn, delay) { 
  let timer; 
  return (...args) => { 
    clearTimeout(timer); 
    timer = setTimeout(() => fn(...args), delay); 
  }; 
}

// Sortable columns
function sortTable(col) {
  const table = document.getElementById('arbitrageTable');
  const rows = Array.from(table.tBodies[0].rows);
  const dir = table.getAttribute('data-sort-dir') === 'asc' ? 'desc' : 'asc';
  rows.sort((a, b) => {
    const x = a.cells[col].innerText.trim();
    const y = b.cells[col].innerText.trim();
    const nx = parseFloat(x), ny = parseFloat(y);
    const cmp = !isNaN(nx) && !isNaN(ny) ? nx - ny : x.localeCompare(y);
    return dir === 'asc' ? cmp : -cmp;
  });
  const tbody = table.tBodies[0]; 
  tbody.innerHTML = ''; 
  rows.forEach(r => tbody.appendChild(r));
  table.setAttribute('data-sort-dir', dir);
}

// AI Model
async function loadModel() {
  try { 
    aiModel = await tf.loadLayersModel('https://example.com/model.json'); 
  }
  catch (err) { 
    console.warn('AI model load failed', err); 
  }
}

async function predictScore(features) {
  if (!aiModel) return 0;
  const input = tf.tensor2d([features]);
  const out = aiModel.predict(input);
  const score = (await out.data())[0];
  return Math.round(score * 100);
}

// Profit chart
function updateProfitChart(profits) {
  const ctx = document.getElementById('profitChart').getContext('2d');
  if (!profitChart) {
    profitChart = new Chart(ctx, { 
      type: 'line', 
      data: { 
        labels: [], 
        datasets: [{ 
          label: 'Max Profit (%)', 
          data: [] 
        }] 
      }, 
      options: { 
        responsive: true, 
        scales: { 
          y: { 
            beginAtZero: true 
          } 
        } 
      } 
    });
  }
  profitChart.data.labels.push(new Date().toLocaleTimeString());
  profitChart.data.datasets[0].data.push(Math.max(...profits, 0));
  profitChart.update();
}

// Validate top-of-book price only
async function validateOpportunityWithDepth(op) {
  try {
    const [u, s, t] = await Promise.all([
      fetch(`https://api.binance.com/api/v3/depth?symbol=${op.usdtPair}&limit=5`).then(r => r.json()),
      fetch(`https://api.binance.com/api/v3/depth?symbol=${op.secondPair}&limit=5`).then(r => r.json()),
      fetch(`https://api.binance.com/api/v3/depth?symbol=${op.thirdPair}&limit=5`).then(r => r.json())
    ]);
    const ask1 = +u.asks[0][0], ask2 = +s.asks[0][0], bid3 = +t.bids[0][0];
    const vol1 = +u.asks[0][1], vol2 = +s.asks[0][1], vol3 = +t.bids[0][1];
    const d1 = marketData.get(op.usdtPair).ask;
    const d2 = marketData.get(op.secondPair).ask;
    const d3 = marketData.get(op.thirdPair).bid;
    return { 
      isValid: ask1 === d1 && ask2 === d2 && bid3 === d3, 
      usdtLiquidity: vol1, 
      secondLiquidity: vol2, 
      thirdLiquidity: vol3, 
      desiredPrices: [d1, d2, d3] 
    };
  } catch (err) { 
    console.error('Depth validation error:', err); 
    return { 
      isValid: false, 
      usdtLiquidity: 0, 
      secondLiquidity: 0, 
      thirdLiquidity: 0, 
      desiredPrices: [0,0,0] 
    }; 
  }
}

// Show errors
function displayError(msg) { 
  document.getElementById('errorMessage').innerText = msg; 
}

// WebSocket + worker setup
function connectWebSocket() {
  const ws = new WebSocket('wss://stream.binance.com:9443/ws/!ticker@arr');
  
  ws.onmessage = e => {
    try {
      const ticks = JSON.parse(e.data);
      ticks.forEach(t => marketData.set(t.s, { ask:+t.a, bid:+t.b }));
      if (Date.now() - lastExec > 300) {
        lastExec = Date.now();
        arbitrageWorker.postMessage({ 
          marketData: Array.from(marketData, ([sym, v]) => ({ 
            symbol: sym, 
            ask: v.ask, 
            bid: v.bid 
          })) 
        });
      }
    } catch (err) { 
      displayError('Data error: '+err.message); 
    }
  };
  
  ws.onerror = () => { 
    displayError('WebSocket error. Reconnecting...'); 
    setTimeout(connectWebSocket, 5000); 
  };
}

// Create Web Worker
const arbitrageWorker = new Worker(URL.createObjectURL(new Blob([`
  self.onmessage = e => {
    const d = e.data.marketData;
    const opps = [];
    
    for (const t of d) {
      if (!t.symbol.endsWith('USDT')) continue;
      const c = t.symbol.replace('USDT','');
      
      for (const s of d) {
        if (!s.symbol.startsWith(c) || s.symbol.endsWith('USDT')) continue;
        const n = d.find(x => x.symbol === s.symbol.replace(c,'')+'USDT');
        if (!n) continue;
        
        const tot = (1/t.ask) * s.ask * n.bid;
        const p = (tot-1)*100 - 0.3;
        
        if (p > 0) {
          opps.push({
            usdtPair: t.symbol,
            secondPair: s.symbol,
            thirdPair: n.symbol,
            profitPercent: p
          });
        }
      }
    }
    
    postMessage({ opportunities: opps });
  };
`], { type: 'application/javascript' })));

// Handle opportunities without removal
arbitrageWorker.onmessage = async e => {
  const ops = e.data.opportunities;
  const profits = [];
  
  for (const op of ops) {
    await displayRow(op);
    profits.push(op.profitPercent);
  }
  
  if (profits.length) updateProfitChart(profits);
  document.getElementById('loadingSpinner').style.display = 'none';
};

// Create or update a row, but never remove
async function displayRow(op) {
  const tbody = document.getElementById('results');
  const id = `opportunity-${op.usdtPair}-${op.secondPair}-${op.thirdPair}`;
  let row = document.getElementById(id);
  const det = await validateOpportunityWithDepth(op);
  const aiScore = await predictScore([op.profitPercent, det.usdtLiquidity, det.secondLiquidity, det.thirdLiquidity]);
  const status = det.isValid ? '<span class="badge-high">Valid</span>' : '<span class="badge-low">Mismatch</span>';
  const prices = det.desiredPrices.join(' / ');
  const advice = det.isValid ? 'Exec at top prices' : '';
  const liq = `${det.usdtLiquidity}/${det.secondLiquidity}/${det.thirdLiquidity}`;
  const linkTemplate = symbol => {
    const pair = symbol.replace(/USDT$/,'_USDT');
    return `https://www.binance.com/en/trade/${pair}?type=spot`;
  };

  if (!row) {
    row = document.createElement('tr');
    row.id = id;
    tbody.appendChild(row);
  }
  
  row.className = det.isValid ? 'profitable' : '';
  row.innerHTML = `
    <td>
      <a class="pair-link" href="${linkTemplate(op.usdtPair)}" target="_blank">${op.usdtPair}</a> →
      <a class="pair-link" href="${linkTemplate(op.secondPair)}" target="_blank">${op.secondPair}</a> →
      <a class="pair-link" href="${linkTemplate(op.thirdPair)}" target="_blank">${op.thirdPair}</a>
    </td>
    <td>${op.profitPercent.toFixed(2)}</td>
    <td>${status}</td>
    <td>${liq}</td>
    <td>${prices}</td>
    <td>${aiScore}</td>
    <td>${advice}</td>
  `;
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', init);