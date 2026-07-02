const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const statusEl = document.getElementById('status');
const heatmapBtn = document.getElementById('heatmap-btn');

const TOTAL_CELLS = 200 * 200;
const TILE_SIZE = 16;

const WS_URL = window.location.protocol === 'https:'
  ? `wss://${window.location.hostname}/ws`
  : `ws://${window.location.hostname}:8765`;

let width = 200;
let height = 200;
let colorMap = {};
let biomeFrame = null;
let renderMode = 'live';

const BIOME_BG = {
  60: [80,  160, 100],
  61: [60,  80,  180],
  62: [180, 130, 40 ],
  63: [30,  180, 80 ],
};
const DEFAULT_BG = [20, 20, 20];

const SPRITE_IDS = {
  1:  'herb_a',
  2:  'predator',
  3:  'herb_b',
  4:  'omnivore',
  5:  'herb_a_infected',
  6:  'herb_b_infected',
  7:  'omnivore_infected',
  10: 'grass',
  30: 'water',
  31: 'rock',
  32: 'swamp',
  40: 'fire',
  41: 'flood',
};

const sprites = {};
let bgCanvas = null;
let currentBytes = null;
let rafId = null;

// ---- Fondo estático ----

function buildBackground() {
  if (!biomeFrame) return;
  bgCanvas = new OffscreenCanvas(width, height);
  const bgCtx = bgCanvas.getContext('2d');
  const img = bgCtx.createImageData(width, height);
  const px = img.data;
  for (let i = 0; i < width * height; i++) {
    const bv = biomeFrame[i];
    const c = (bv >= 30 && bv <= 32) ? colorMap[bv] : BIOME_BG[bv] || DEFAULT_BG;
    px[i * 4]     = c[0];
    px[i * 4 + 1] = c[1];
    px[i * 4 + 2] = c[2];
    px[i * 4 + 3] = 255;
  }
  bgCtx.putImageData(img, 0, 0);
}

// ---- Sprites ----

async function loadSprites() {
  await Promise.all(Object.entries(SPRITE_IDS).map(([val, name]) =>
    new Promise(resolve => {
      const img = new Image();
      img.src = `sprites/${name}.svg`;
      img.onload = () =>
        createImageBitmap(img, { resizeWidth: TILE_SIZE, resizeHeight: TILE_SIZE })
          .then(bm => { sprites[parseInt(val)] = bm; resolve(); })
          .catch(resolve);
      img.onerror = resolve;
    })
  ));
  scheduleRedraw();
}

// ---- Viewport / Zoom / Pan ----

let zoom = 1;
let panX = 0;
let panY = 0;
const MIN_ZOOM = 1;
const MAX_ZOOM = 10;

function ts() { return (canvas.width / width) * zoom; }

function clampPan() {
  const t = ts();
  const worldW = width  * t;
  const worldH = height * t;
  panX = worldW <= canvas.width
    ? (canvas.width  - worldW) / 2
    : Math.min(0, Math.max(canvas.width  - worldW, panX));
  panY = worldH <= canvas.height
    ? (canvas.height - worldH) / 2
    : Math.min(0, Math.max(canvas.height - worldH, panY));
}

function scheduleRedraw() {
  if (rafId) return;
  rafId = requestAnimationFrame(() => { rafId = null; redraw(); });
}

// ---- Render ----

function drawCellAt(val, px, py, tileW) {
  if (val === 40 || val === 41) {
    const c = colorMap[val] || DEFAULT_BG;
    ctx.fillStyle = `rgb(${c[0]},${c[1]},${c[2]})`;
    ctx.fillRect(px, py, tileW, tileW);
  }
  const spr = sprites[val];
  if (spr) {
    ctx.drawImage(spr, px, py, tileW, tileW);
  } else if (val >= 11 && val <= 13) {
    const c = colorMap[val] || [100, 100, 100];
    ctx.fillStyle = `rgba(${c[0]},${c[1]},${c[2]},0.45)`;
    ctx.fillRect(px, py, tileW, tileW);
  } else if (val >= 20 && val <= 22) {
    const c = colorMap[val] || [60, 60, 60];
    ctx.fillStyle = `rgba(${c[0]},${c[1]},${c[2]},0.30)`;
    ctx.fillRect(px, py, tileW, tileW);
  } else if (val === 50) {
    ctx.fillStyle = 'rgba(100,90,85,0.55)';
    ctx.fillRect(px, py, tileW, tileW);
  }
}

function redraw() {
  const t = ts();
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const c0 = Math.max(0, Math.floor(-panX / t));
  const r0 = Math.max(0, Math.floor(-panY / t));
  const c1 = Math.min(width,  Math.ceil((canvas.width  - panX) / t));
  const r1 = Math.min(height, Math.ceil((canvas.height - panY) / t));

  if (bgCanvas) {
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(bgCanvas,
      c0, r0, c1 - c0, r1 - r0,
      c0 * t + panX, r0 * t + panY, (c1 - c0) * t, (r1 - r0) * t);
  } else {
    ctx.fillStyle = `rgb(${DEFAULT_BG[0]},${DEFAULT_BG[1]},${DEFAULT_BG[2]})`;
    ctx.fillRect(panX, panY, width * t, height * t);
  }

  if (renderMode === 'live' && currentBytes && t >= 3) {
    for (let r = r0; r < r1; r++) {
      for (let c = c0; c < c1; c++) {
        const val = currentBytes[r * width + c];
        if (val === 0) continue;
        drawCellAt(val, c * t + panX, r * t + panY, t);
      }
    }
  }
}

heatmapBtn.addEventListener('click', () => {
  if (!biomeFrame) return;
  renderMode = renderMode === 'live' ? 'biome' : 'live';
  heatmapBtn.classList.toggle('active', renderMode === 'biome');
  heatmapBtn.textContent = renderMode === 'biome' ? 'Ver simulación' : 'Ver biomas';
  scheduleRedraw();
});

// ---- Gráfica de población ----

const popChart = document.getElementById('pop-chart');
const popCtx = popChart.getContext('2d');
const MAX_HISTORY = 200;
const popHistory = [];
const CHART_COLORS = ['#00c864', '#dc3c3c', '#3c8cdc', '#a03cc8'];

function drawPopChart() {
  const W = popChart.width;
  const H = popChart.height;
  popCtx.clearRect(0, 0, W, H);
  if (popHistory.length < 2) return;

  const keys = ['herb_a', 'predators', 'herb_b', 'omni'];
  const maxVal = popHistory.reduce((m, d) => Math.max(m, ...keys.map(k => d[k] || 0)), 1);

  popCtx.fillStyle = '#111';
  popCtx.fillRect(0, 0, W, H);

  keys.forEach((key, ki) => {
    popCtx.beginPath();
    popCtx.strokeStyle = CHART_COLORS[ki];
    popCtx.lineWidth = 1.5;
    popHistory.forEach((d, i) => {
      const x = (i / (MAX_HISTORY - 1)) * W;
      const y = H - (d[key] || 0) / maxVal * (H - 2) - 1;
      i === 0 ? popCtx.moveTo(x, y) : popCtx.lineTo(x, y);
    });
    popCtx.stroke();
  });
}

// ---- Stats ----

function pct(n) { return (n / TOTAL_CELLS * 100).toFixed(1) + '%'; }

const GENE_FMT = [
  v => v.toFixed(2),
  v => v.toFixed(0),
  v => v.toFixed(2),
  v => v.toFixed(1),
  v => v.toFixed(3),
];

function updateGenes(prefix, genes) {
  if (!genes) return;
  genes.forEach((v, i) => {
    const el = document.getElementById(`e${prefix}-${i}`);
    if (el) el.textContent = GENE_FMT[i](v);
  });
}

function updateStats(msg) {
  document.getElementById('tick-display').textContent = `Tick ${msg.tick}`;
  document.getElementById('herb-a-count').textContent = msg.herb_a;
  document.getElementById('pred-count').textContent = msg.predators;
  document.getElementById('herb-b-count').textContent = msg.herb_b;
  document.getElementById('omni-count').textContent = msg.omni || 0;
  document.getElementById('infected-count').textContent = msg.infected;
  document.getElementById('food-count').textContent = msg.food;
  document.getElementById('herb-a-bar').style.width = pct(msg.herb_a);
  document.getElementById('pred-bar').style.width = pct(msg.predators);
  document.getElementById('herb-b-bar').style.width = pct(msg.herb_b);
  document.getElementById('omni-bar').style.width = pct(msg.omni || 0);
  document.getElementById('infected-bar').style.width = pct(msg.infected);
  document.getElementById('food-bar').style.width = pct(msg.food);
  updateGenes('a', msg.genome_a);
  updateGenes('p', msg.genome_p);
  updateGenes('b', msg.genome_b);
  updateGenes('o', msg.genome_o);
  if (msg.territory_a !== undefined) {
    document.getElementById('ter-a').textContent = msg.territory_a;
    document.getElementById('ter-p').textContent = msg.territory_p;
    document.getElementById('ter-b').textContent = msg.territory_b;
  }
  if (msg.season !== undefined) {
    document.getElementById('season-display').textContent = msg.season;
    const t = msg.temperature;
    document.getElementById('temp-display').textContent = (t >= 0 ? '+' : '') + t.toFixed(2);
  }

  // historial para la gráfica
  popHistory.push({
    herb_a: msg.herb_a,
    predators: msg.predators,
    herb_b: msg.herb_b,
    omni: msg.omni || 0,
  });
  if (popHistory.length > MAX_HISTORY) popHistory.shift();
  // sincronizar ancho del canvas con su CSS width
  const cw = popChart.offsetWidth;
  if (cw > 0 && popChart.width !== cw) popChart.width = cw;
  drawPopChart();
}

// ---- Inspector de celda ----

const inspector = document.getElementById('inspector');
const inspTitle = document.getElementById('insp-title');
const inspBody  = document.getElementById('insp-body');
document.getElementById('insp-close').addEventListener('click', () => {
  inspector.classList.add('hidden');
});

const GENE_NAMES = ['Velocidad', 'Reprod.', 'Eficienc.', 'Visión', 'Mutación'];
const SP_COLORS  = { 1: '#00c864', 2: '#dc3c3c', 3: '#3c8cdc', 4: '#a03cc8' };

function showCellInfo(msg) {
  const color = SP_COLORS[msg.species] || '#888';
  inspTitle.textContent = `[${msg.row},${msg.col}] ${msg.name}`;
  inspTitle.style.color = color;

  let html = '';
  if (msg.species === 0) {
    html = '<div style="color:#555;text-align:center;padding:8px 0">Celda vacía</div>';
  } else {
    const maxE = msg.species === 2 ? 120 : msg.species === 4 ? 110 : 100;
    const ePct = Math.min(100, Math.round(msg.energy / maxE * 100));
    const maxA = msg.species === 2 ? 120 : msg.species === 4 ? 130 : 150;
    const aPct = Math.min(100, Math.round(msg.age / maxA * 100));

    html += `<div class="insp-row"><span class="insp-label">Género</span><span class="insp-val">${msg.gender || '—'}</span></div>`;
    html += `<div class="insp-row"><span class="insp-label">Energía</span><span class="insp-val">${msg.energy}</span></div>`;
    html += `<div class="insp-bar-bg"><div class="insp-bar" style="background:${color};width:${ePct}%"></div></div>`;
    html += `<div class="insp-row"><span class="insp-label">Edad</span><span class="insp-val">${msg.age}</span></div>`;
    html += `<div class="insp-bar-bg"><div class="insp-bar" style="background:#555;width:${aPct}%"></div></div>`;
    html += `<div class="insp-row"><span class="insp-label">Infectado</span><span class="insp-val" style="color:${msg.infected?'#c8c800':'#444'}">${msg.infected ? 'Sí' : 'No'}</span></div>`;

    if (msg.genome) {
      html += '<div style="margin-top:8px;color:#555;font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">Genes</div>';
      msg.genome.forEach((v, i) => {
        html += `<div class="insp-row"><span class="insp-label insp-gene">${GENE_NAMES[i]}</span><span class="insp-val insp-gene">${GENE_FMT[i](v)}</span></div>`;
      });
    }
  }
  inspBody.innerHTML = html;
  inspector.classList.remove('hidden');
}

// ---- WebSocket ----

let ws = null;

function connect() {
  ws = new WebSocket(WS_URL);
  ws.binaryType = 'arraybuffer';

  ws.onopen = () => { statusEl.textContent = 'Conectado'; };

  ws.onmessage = (event) => {
    if (typeof event.data === 'string') {
      const msg = JSON.parse(event.data);
      if (msg.type === 'init') {
        width  = msg.width;
        height = msg.height;
        canvas.width  = canvas.offsetWidth  || 600;
        canvas.height = canvas.offsetHeight || 600;
        ctx.imageSmoothingEnabled = false;
        zoom = 1; panX = 0; panY = 0;
        colorMap = {};
        for (const [k, v] of Object.entries(msg.colors)) colorMap[parseInt(k)] = v;
        if (msg.biome) {
          const raw = atob(msg.biome);
          biomeFrame = new Uint8Array(raw.length);
          for (let i = 0; i < raw.length; i++) biomeFrame[i] = raw.charCodeAt(i);
          heatmapBtn.disabled = false;
          buildBackground();
        }
      } else if (msg.type === 'stats') {
        updateStats(msg);
      } else if (msg.type === 'cell') {
        showCellInfo(msg);
      }
    } else {
      currentBytes = new Uint8Array(event.data);
      if (renderMode === 'live') scheduleRedraw();
    }
  };

  ws.onclose = () => {
    statusEl.textContent = 'Desconectado — reconectando...';
    setTimeout(connect, 2000);
  };

  ws.onerror = () => { statusEl.textContent = 'Error de conexión'; };
}

fetch('CHANGELOG.md')
  .then(r => r.ok ? r.text() : Promise.reject())
  .then(text => { document.getElementById('changelog').textContent = text; })
  .catch(() => { document.getElementById('changelog').textContent = '—'; });

loadSprites();
connect();

// ---- Zoom / Pan ----

const view = document.getElementById('view');

function resetZoom() {
  zoom = 1; panX = 0; panY = 0;
  view.style.cursor = 'default';
  scheduleRedraw();
}

function zoomAt(factor, clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  const mx = clientX - rect.left;
  const my = clientY - rect.top;
  const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom * factor));
  if (newZoom === zoom) return;
  const scale = newZoom / zoom;
  panX = mx - (mx - panX) * scale;
  panY = my - (my - panY) * scale;
  zoom = newZoom;
  clampPan();
  view.style.cursor = zoom > 1 ? 'grab' : 'default';
  scheduleRedraw();
}

view.addEventListener('wheel', (e) => {
  e.preventDefault();
  zoomAt(e.deltaY < 0 ? 1.15 : 1 / 1.15, e.clientX, e.clientY);
}, { passive: false });

view.addEventListener('dblclick', resetZoom);

let dragging = false;
let didDrag  = false;
let dragX = 0, dragY = 0;

view.addEventListener('mousedown', (e) => {
  didDrag = false;
  if (zoom <= 1 || e.button !== 0) return;
  dragging = true; dragX = e.clientX; dragY = e.clientY;
  view.style.cursor = 'grabbing';
  e.preventDefault();
});
window.addEventListener('mousemove', (e) => {
  if (!dragging) return;
  didDrag = true;
  panX += e.clientX - dragX;
  panY += e.clientY - dragY;
  dragX = e.clientX; dragY = e.clientY;
  clampPan();
  scheduleRedraw();
});
window.addEventListener('mouseup', () => {
  if (!dragging) return;
  dragging = false;
  view.style.cursor = zoom > 1 ? 'grab' : 'default';
});

// Inspector: click en el canvas → enviar solicitud al servidor
canvas.addEventListener('click', (e) => {
  if (didDrag) return;
  const rect = canvas.getBoundingClientRect();
  const t    = ts();
  const col  = Math.floor((e.clientX - rect.left - panX) / t);
  const row  = Math.floor((e.clientY - rect.top  - panY) / t);
  if (col >= 0 && col < width && row >= 0 && row < height) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'inspect', row, col }));
    }
  }
});

// Touch: pinch zoom + drag
const activeTouches = {};

view.addEventListener('touchstart', (e) => {
  e.preventDefault();
  for (const t of e.changedTouches) activeTouches[t.identifier] = { x: t.clientX, y: t.clientY };
}, { passive: false });

view.addEventListener('touchmove', (e) => {
  e.preventDefault();
  const prev = {};
  for (const [id, pos] of Object.entries(activeTouches)) prev[id] = { ...pos };
  for (const t of e.changedTouches) activeTouches[t.identifier] = { x: t.clientX, y: t.clientY };

  const ids = Object.keys(activeTouches);

  if (ids.length >= 2) {
    const [a, b] = [activeTouches[ids[0]], activeTouches[ids[1]]];
    const [pa, pb] = [prev[ids[0]], prev[ids[1]]];
    if (!pa || !pb) return;

    const newDist = Math.hypot(b.x - a.x, b.y - a.y);
    const oldDist = Math.hypot(pb.x - pa.x, pb.y - pa.y);
    if (oldDist === 0) return;

    const midX = (a.x + b.x) / 2, midY = (a.y + b.y) / 2;
    const pmidX = (pa.x + pb.x) / 2, pmidY = (pa.y + pb.y) / 2;

    const rect = canvas.getBoundingClientRect();
    const mx = midX - rect.left, my = midY - rect.top;

    const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom * (newDist / oldDist)));
    const scale = newZoom / zoom;
    panX = mx - (mx - panX) * scale + (midX - pmidX);
    panY = my - (my - panY) * scale + (midY - pmidY);
    zoom = newZoom;
    clampPan();
    scheduleRedraw();
  } else if (ids.length === 1 && zoom > 1) {
    const p = prev[ids[0]], c = activeTouches[ids[0]];
    if (p) {
      panX += c.x - p.x;
      panY += c.y - p.y;
      clampPan();
      scheduleRedraw();
    }
  }
}, { passive: false });

let lastTapTime = 0;
view.addEventListener('touchend', (e) => {
  e.preventDefault();
  for (const t of e.changedTouches) delete activeTouches[t.identifier];
  const now = Date.now();
  if (now - lastTapTime < 300 && e.changedTouches.length === 1) resetZoom();
  lastTapTime = now;
}, { passive: false });

window.addEventListener('resize', () => {
  canvas.width  = canvas.offsetWidth  || 600;
  canvas.height = canvas.offsetHeight || 600;
  ctx.imageSmoothingEnabled = false;
  clampPan();
  scheduleRedraw();
});
