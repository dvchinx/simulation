'use strict';

// ---------------------------------------------------------------------------
// Configuración
// ---------------------------------------------------------------------------

const $ = (id) => document.getElementById(id);

const WS_URL = new URLSearchParams(location.search).get('ws') || (
  location.protocol === 'https:'
    ? `wss://${location.hostname}/ws`
    : `ws://${location.hostname || 'localhost'}:8765`
);

// Código de render (byte por celda, ver SPECIES_COLORS en config.py) → sprite
const SPRITE_IDS = {
  1: 'herb_a', 2: 'predator', 3: 'herb_b', 4: 'omnivore',
  5: 'herb_a_infected', 6: 'herb_b_infected', 7: 'omnivore_infected',
  10: 'grass', 30: 'water', 31: 'rock', 32: 'swamp', 40: 'fire', 41: 'flood',
};
const SPRITE_RES = 48;        // resolución a la que se rasterizan los SVG
const SPRITE_MIN_TILE = 9;    // px de dispositivo por celda a partir de los cuales se usan sprites
const MAX_ZOOM = 16;
const MAX_HISTORY = 300;
const DELTA_WINDOW = 20;      // ticks para la tendencia de población
const MAX_EVENTS = 30;

const BIOME_BG = { 60: [80, 160, 100], 61: [60, 80, 180], 62: [180, 130, 40], 63: [30, 180, 80] };
const DEFAULT_BG = [20, 20, 20];
const SHORT_NAMES = { herb_a: 'Herb A', predator: 'Depred.', herb_b: 'Herb B', omnivore: 'Omni' };
const GENE_DESC = [
  'Probabilidad de moverse en cada tick',
  'Energía mínima para reproducirse',
  'Multiplicador de la energía obtenida al comer',
  'Rango de visión en celdas',
  'Desviación estándar del ruido de mutación',
];
const GENE_FMT = [(v) => v.toFixed(2), (v) => v.toFixed(0), (v) => v.toFixed(2), (v) => v.toFixed(1), (v) => v.toFixed(3)];

// ---------------------------------------------------------------------------
// Estado
// ---------------------------------------------------------------------------

const canvas = $('canvas');
const ctx = canvas.getContext('2d');

const world = {
  width: 200, height: 200, fps: 4,
  colors: {}, species: [], genes: [], biomes: [], periods: {},
};
let biomeFrame = null;        // Uint8Array: bioma + terreno (estático)
let frame = null;             // Uint8Array: último frame recibido
let frameDirty = false;
let viewMode = 'live';
const layers = { pheromone: true, territory: true, border: true };

const sprites = {};
let spritesReady = false;

let dpr = window.devicePixelRatio || 1;
let zoom = 1, panX = 0, panY = 0;
let selected = null;          // {row, col} de la celda inspeccionada
const pings = [];             // marcas animadas de eventos sobre el mapa

const history = [];           // [[herb_a, predator, herb_b, omnivore], ...]
let lastTick = 0;
const hiddenSeries = new Set();
let chartScale = 'log';
let events = [];

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------

function makeCanvas(w, h) {
  if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h);
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
}

const rgb = (c, a = 1) => `rgb(${c[0]} ${c[1]} ${c[2]} / ${a})`;
// Píxel RGBA empaquetado para Uint32Array (little-endian: ABGR)
const packColor = (c, a = 255) => ((a << 24) | (c[2] << 16) | (c[1] << 8) | c[0]) >>> 0;

const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (ch) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
));
const fmtInt = (n) => n.toLocaleString('es');
const speciesById = (id) => world.species.find((s) => s.id === id);

// ---------------------------------------------------------------------------
// Rasterización: fondo estático + capa dinámica en ImageData (sin un
// drawImage por celda a zoom bajo)
// ---------------------------------------------------------------------------

let bgCanvas = null;          // biomas a color completo (vista "Biomas")
let bgDimCanvas = null;       // biomas atenuados: los organismos resaltan (vista "Simulación")
let fgLow = null, fgHigh = null;      // capas dinámicas para zoom bajo / alto
const lutLow = new Uint32Array(256);  // zoom bajo: todo como píxeles de color
const lutHigh = new Uint32Array(256); // zoom alto: solo overlays; organismos y terreno son sprites

const BG_DIM = 0.42;

function renderBiomeLayer(dim) {
  const { width: w, height: h } = world;
  const layer = makeCanvas(w, h);
  const lctx = layer.getContext('2d');
  const img = lctx.createImageData(w, h);
  const px = new Uint32Array(img.data.buffer);
  const cache = {};
  for (let i = 0; i < w * h; i++) {
    const v = biomeFrame[i];
    if (cache[v] === undefined) {
      const c = ((v >= 30 && v <= 32) ? world.colors[v] : BIOME_BG[v]) || DEFAULT_BG;
      cache[v] = packColor(c.map((ch) => Math.round(ch * dim)));
    }
    px[i] = cache[v];
  }
  lctx.putImageData(img, 0, 0);
  return layer;
}

function buildBackground() {
  bgCanvas = renderBiomeLayer(1);
  bgDimCanvas = renderBiomeLayer(BG_DIM);
}

function buildLUTs() {
  const C = world.colors;
  lutLow.fill(0);
  lutHigh.fill(0);
  const both = (code, color, alpha) => { lutLow[code] = lutHigh[code] = packColor(color, alpha); };

  for (const code of [1, 2, 3, 4, 5, 6, 7]) if (C[code]) lutLow[code] = packColor(C[code]);
  lutLow[10] = packColor([46, 120, 52], 150);  // pasto: velo verde sobre el bioma
  if (layers.pheromone) for (const code of [11, 12, 13]) both(code, C[code], 130);
  if (layers.territory) for (const code of [20, 21, 22]) both(code, C[code], 90);
  if (layers.border) both(50, [150, 140, 130], 70);
  // Fuego/inundación: color sólido debajo del sprite
  for (const code of [40, 41]) both(code, C[code], 255);
  // 30–32 (agua/roca/pantano) ya están en el fondo a zoom bajo
  frameDirty = true;
}

function makeLayer() {
  const c = makeCanvas(world.width, world.height);
  const img = new ImageData(world.width, world.height);
  return { canvas: c, ctx: c.getContext('2d'), img, px: new Uint32Array(img.data.buffer) };
}

function rasterizeFrame() {
  if (!frame || !fgLow) return;
  const lo = fgLow.px, hi = fgHigh.px;
  for (let i = 0; i < frame.length; i++) {
    const v = frame[i];
    lo[i] = lutLow[v];
    hi[i] = lutHigh[v];
  }
  fgLow.ctx.putImageData(fgLow.img, 0, 0);
  fgHigh.ctx.putImageData(fgHigh.img, 0, 0);
  frameDirty = false;
}

async function loadSprites() {
  await Promise.all(Object.entries(SPRITE_IDS).map(([code, name]) => new Promise((resolve) => {
    const img = new Image();
    img.onload = () => createImageBitmap(img, { resizeWidth: SPRITE_RES, resizeHeight: SPRITE_RES, resizeQuality: 'high' })
      .then((bm) => { sprites[code] = bm; })
      .catch(() => {})
      .finally(resolve);
    img.onerror = resolve;
    img.src = `sprites/${name}.svg`;
  })));
  spritesReady = true;
  scheduleRedraw();
}

// ---------------------------------------------------------------------------
// Viewport
// ---------------------------------------------------------------------------

const fitScale = () => Math.min(canvas.width / world.width, canvas.height / world.height);
const tileSize = () => fitScale() * zoom;

function clampPan() {
  const t = tileSize();
  const worldW = world.width * t, worldH = world.height * t;
  panX = worldW <= canvas.width ? (canvas.width - worldW) / 2 : Math.min(0, Math.max(canvas.width - worldW, panX));
  panY = worldH <= canvas.height ? (canvas.height - worldH) / 2 : Math.min(0, Math.max(canvas.height - worldH, panY));
}

function zoomAt(factor, cx, cy) {
  const newZoom = Math.max(1, Math.min(MAX_ZOOM, zoom * factor));
  if (newZoom === zoom) return;
  const scale = newZoom / zoom;
  panX = cx - (cx - panX) * scale;
  panY = cy - (cy - panY) * scale;
  zoom = newZoom;
  clampPan();
  scheduleRedraw();
}

function resetView() {
  zoom = 1;
  clampPan();
  scheduleRedraw();
}

function focusCell(row, col, targetZoom = 5) {
  zoom = Math.max(zoom, targetZoom);
  const t = tileSize();
  panX = canvas.width / 2 - (col + 0.5) * t;
  panY = canvas.height / 2 - (row + 0.5) * t;
  clampPan();
  scheduleRedraw();
}

// Coordenadas de cliente (CSS px) → px de dispositivo del canvas
function toCanvas(clientX, clientY) {
  const r = canvas.getBoundingClientRect();
  return [(clientX - r.left) * dpr, (clientY - r.top) * dpr];
}

function cellAt(clientX, clientY) {
  const [x, y] = toCanvas(clientX, clientY);
  const t = tileSize();
  const col = Math.floor((x - panX) / t), row = Math.floor((y - panY) / t);
  return (col >= 0 && col < world.width && row >= 0 && row < world.height) ? { row, col } : null;
}

function resizeCanvas() {
  dpr = window.devicePixelRatio || 1;
  const w = Math.max(1, Math.round(canvas.clientWidth * dpr));
  const h = Math.max(1, Math.round(canvas.clientHeight * dpr));
  if (w === canvas.width && h === canvas.height) return;
  // conservar el centro de la vista
  const t0 = tileSize();
  const cx = (canvas.width / 2 - panX) / t0, cy = (canvas.height / 2 - panY) / t0;
  canvas.width = w; canvas.height = h;
  const t = tileSize();
  panX = w / 2 - cx * t; panY = h / 2 - cy * t;
  clampPan();
  redraw();
}

// ---------------------------------------------------------------------------
// Dibujo
// ---------------------------------------------------------------------------

let rafId = 0;
function scheduleRedraw() {
  if (!rafId) rafId = requestAnimationFrame(() => { rafId = 0; redraw(); });
}

function blit(src, c0, r0, c1, r1, t) {
  ctx.drawImage(src, c0, r0, c1 - c0, r1 - r0, c0 * t + panX, r0 * t + panY, (c1 - c0) * t, (r1 - r0) * t);
}

function redraw() {
  const t = tileSize();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.imageSmoothingEnabled = false;

  const c0 = Math.max(0, Math.floor(-panX / t));
  const r0 = Math.max(0, Math.floor(-panY / t));
  const c1 = Math.min(world.width, Math.ceil((canvas.width - panX) / t));
  const r1 = Math.min(world.height, Math.ceil((canvas.height - panY) / t));
  if (c1 <= c0 || r1 <= r0) return;

  const bg = viewMode === 'live' ? bgDimCanvas : bgCanvas;
  if (bg) blit(bg, c0, r0, c1, r1, t);

  if (viewMode === 'live' && frame) {
    if (frameDirty) rasterizeFrame();
    const useSprites = spritesReady && t >= SPRITE_MIN_TILE;
    blit(useSprites ? fgHigh.canvas : fgLow.canvas, c0, r0, c1, r1, t);

    if (useSprites) {
      ctx.imageSmoothingEnabled = true;
      const w = world.width;
      for (let r = r0; r < r1; r++) {
        const y = r * t + panY;
        for (let c = c0; c < c1; c++) {
          const spr = sprites[frame[r * w + c]];
          if (spr) ctx.drawImage(spr, c * t + panX, y, t, t);
        }
      }
      ctx.imageSmoothingEnabled = false;
    }
  }

  drawSelection(t);
  drawPings(t);
}

function drawSelection(t) {
  if (!selected) return;
  const x = selected.col * t + panX, y = selected.row * t + panY;
  const pad = Math.max(2, t * 0.15);
  ctx.lineWidth = Math.max(1.5, 1.5 * dpr);
  ctx.strokeStyle = 'rgba(0,0,0,0.6)';
  ctx.strokeRect(x - pad - 1, y - pad - 1, t + 2 * pad + 2, t + 2 * pad + 2);
  ctx.strokeStyle = '#ffffff';
  ctx.strokeRect(x - pad, y - pad, t + 2 * pad, t + 2 * pad);
}

const PING_MS = 2600;
function drawPings(t) {
  const now = performance.now();
  for (let i = pings.length - 1; i >= 0; i--) {
    const p = pings[i];
    const k = (now - p.start) / PING_MS;
    if (k >= 1) { pings.splice(i, 1); continue; }
    const cx = (p.col + 0.5) * t + panX, cy = (p.row + 0.5) * t + panY;
    for (const offset of [0, 0.35]) {
      const kk = k - offset;
      if (kk <= 0) continue;
      ctx.beginPath();
      ctx.arc(cx, cy, Math.max(6 * dpr, t * 2) + kk * 40 * dpr, 0, Math.PI * 2);
      ctx.lineWidth = 2 * dpr;
      ctx.strokeStyle = rgb(p.color, (1 - kk) * 0.9);
      ctx.stroke();
    }
  }
  if (pings.length) scheduleRedraw();
}

// ---------------------------------------------------------------------------
// Interacción con el mapa (Pointer Events: ratón, táctil y lápiz)
// ---------------------------------------------------------------------------

const pointers = new Map();
let gesture = null;
let lastTap = 0;

function hideHint() { $('map-hint').classList.add('hidden'); }
setTimeout(hideHint, 9000);

canvas.addEventListener('pointerdown', (e) => {
  canvas.setPointerCapture(e.pointerId);
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pointers.size === 1) gesture = { x: e.clientX, y: e.clientY, moved: false };
  else if (gesture) gesture.moved = true;
  hideHint();
});

canvas.addEventListener('pointermove', (e) => {
  const prev = pointers.get(e.pointerId);
  if (!prev) return;
  const cur = { x: e.clientX, y: e.clientY };

  if (pointers.size === 1) {
    if (!gesture.moved && Math.hypot(cur.x - gesture.x, cur.y - gesture.y) > 4) {
      gesture.moved = true;
      canvas.classList.add('grabbing');
    }
    if (gesture.moved) {
      panX += (cur.x - prev.x) * dpr;
      panY += (cur.y - prev.y) * dpr;
      clampPan();
      scheduleRedraw();
    }
  } else if (pointers.size === 2) {
    const [idA, idB] = [...pointers.keys()];
    const a0 = pointers.get(idA), b0 = pointers.get(idB);
    const a1 = idA === e.pointerId ? cur : a0, b1 = idB === e.pointerId ? cur : b0;
    const d0 = Math.hypot(b0.x - a0.x, b0.y - a0.y), d1 = Math.hypot(b1.x - a1.x, b1.y - a1.y);
    if (d0 > 0) {
      const [mx, my] = toCanvas((a1.x + b1.x) / 2, (a1.y + b1.y) / 2);
      panX += ((a1.x + b1.x) - (a0.x + b0.x)) / 2 * dpr;
      panY += ((a1.y + b1.y) - (a0.y + b0.y)) / 2 * dpr;
      zoomAt(d1 / d0, mx, my);
      clampPan();
      scheduleRedraw();
    }
  }
  pointers.set(e.pointerId, cur);
});

function endPointer(e) {
  if (!pointers.delete(e.pointerId)) return;
  if (pointers.size > 0) return;
  canvas.classList.remove('grabbing');
  if (e.type === 'pointerup' && gesture && !gesture.moved) {
    const now = performance.now();
    if (e.pointerType !== 'mouse' && now - lastTap < 300) resetView();
    else inspect(cellAt(e.clientX, e.clientY));
    lastTap = now;
  }
  gesture = null;
}
canvas.addEventListener('pointerup', endPointer);
canvas.addEventListener('pointercancel', endPointer);
canvas.addEventListener('dblclick', resetView);

canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  hideHint();
  const [x, y] = toCanvas(e.clientX, e.clientY);
  const delta = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
  zoomAt(Math.exp(-Math.max(-300, Math.min(300, delta)) * 0.0018), x, y);
}, { passive: false });

const zoomCenter = (f) => zoomAt(f, canvas.width / 2, canvas.height / 2);
$('zoom-in').addEventListener('click', () => zoomCenter(1.5));
$('zoom-out').addEventListener('click', () => zoomCenter(1 / 1.5));
$('zoom-fit').addEventListener('click', resetView);

document.addEventListener('keydown', (e) => {
  if (e.target instanceof HTMLInputElement || e.metaKey || e.ctrlKey || e.altKey) return;
  const step = Math.min(canvas.width, canvas.height) * 0.15;
  const actions = {
    '+': () => zoomCenter(1.5), '=': () => zoomCenter(1.5), '-': () => zoomCenter(1 / 1.5),
    '0': resetView, Escape: closeInspector,
    ArrowLeft: () => { panX += step; }, ArrowRight: () => { panX -= step; },
    ArrowUp: () => { panY += step; }, ArrowDown: () => { panY -= step; },
  };
  const action = actions[e.key];
  if (!action) return;
  if (e.key.startsWith('Arrow') && document.activeElement !== canvas) return;
  e.preventDefault();
  action();
  clampPan();
  scheduleRedraw();
});

document.querySelectorAll('.seg-btn').forEach((btn) => btn.addEventListener('click', () => {
  viewMode = btn.dataset.view;
  document.querySelectorAll('.seg-btn').forEach((b) => {
    b.classList.toggle('active', b === btn);
    b.setAttribute('aria-pressed', String(b === btn));
  });
  scheduleRedraw();
}));

document.querySelectorAll('[data-layer]').forEach((input) => input.addEventListener('change', () => {
  layers[input.dataset.layer] = input.checked;
  buildLUTs();
  scheduleRedraw();
}));

new ResizeObserver(resizeCanvas).observe(canvas);

// ---------------------------------------------------------------------------
// Inspector de celda (se actualiza en vivo mientras está abierto)
// ---------------------------------------------------------------------------

const inspector = $('inspector');

function inspect(cell) {
  if (!cell) return;
  selected = cell;
  requestCell();
  scheduleRedraw();
}

function requestCell() {
  if (selected && ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'inspect', row: selected.row, col: selected.col }));
  }
}

function closeInspector() {
  inspector.hidden = true;
  selected = null;
  scheduleRedraw();
}
$('insp-close').addEventListener('click', closeInspector);

const row = (label, value, style = '') =>
  `<div class="insp-row"><span>${label}</span><span class="num" style="${style}">${value}</span></div>`;
const bar = (pct, color) =>
  `<div class="insp-bar"><span style="width:${Math.max(0, Math.min(100, pct))}%;background:${color}"></span></div>`;

function showCellInfo(msg) {
  if (!selected || msg.row !== selected.row || msg.col !== selected.col) return;
  const spec = speciesById(msg.species);
  const color = spec ? rgb(spec.color) : 'var(--muted)';
  const icon = $('insp-icon');
  icon.hidden = !spec;
  if (spec) icon.src = `sprites/${spec.key}${msg.infected && spec.key !== 'predator' ? '_infected' : ''}.svg`;
  $('insp-title').textContent = msg.name;
  $('insp-title').style.color = color;
  $('insp-sub').textContent = `Celda (${msg.row}, ${msg.col}) · en vivo`;

  let html = '';
  if (spec) {
    html += row('Género', escapeHtml(msg.gender));
    html += row('Energía', `${msg.energy} / ${spec.max_energy}`) + bar(msg.energy / spec.max_energy * 100, color);
    html += row('Edad', `${msg.age} / ${spec.max_age}`) + bar(msg.age / spec.max_age * 100, 'var(--faint)');
    html += row('Infectado', msg.infected ? 'Sí' : 'No', msg.infected ? 'color:var(--infected)' : '');
    html += '<div class="insp-section">Genoma</div>';
    msg.genome.forEach((v, i) => {
      const g = world.genes[i];
      html += row(escapeHtml(g.name), GENE_FMT[i](v)) + bar((v - g.min) / (g.max - g.min) * 100, color);
    });
  } else {
    html += '<div class="insp-empty">Sin organismo en esta celda.</div>';
  }
  html += '<div class="insp-section">Entorno</div>';
  html += row('Bioma', escapeHtml(msg.biome));
  html += row('Terreno', escapeHtml(msg.terrain));
  html += row('Temperatura', (msg.temperature >= 0 ? '+' : '') + msg.temperature.toFixed(2));
  html += row('Pasto', msg.food ? 'Sí' : 'No');
  html += row('Nutriente', msg.nutrient.toFixed(2));
  $('insp-body').innerHTML = html;
  inspector.hidden = false;
}

// ---------------------------------------------------------------------------
// Panel lateral
// ---------------------------------------------------------------------------

function buildSidebar() {
  const root = document.documentElement;
  for (const s of world.species) root.style.setProperty(`--sp-${s.key}`, rgb(s.color));
  if (world.colors[5]) root.style.setProperty('--infected', rgb(world.colors[5]));

  $('species-list').innerHTML = world.species.map((s) => `
    <li class="species-row" id="sp-${s.key}">
      <img src="sprites/${s.key}.svg" alt="">
      <span class="species-name">${escapeHtml(s.name)}</span>
      <span class="species-delta num" title="Cambio en los últimos ${DELTA_WINDOW} ticks"></span>
      <span class="species-count num">—</span>
      <div class="species-bar"><span style="background:var(--sp-${s.key})"></span></div>
    </li>`).join('');

  $('chart-legend').innerHTML = world.species.map((s, i) => `
    <button class="legend-btn" data-series="${i}" aria-pressed="${!hiddenSeries.has(i)}">
      <i style="background:var(--sp-${s.key})"></i>${escapeHtml(SHORT_NAMES[s.key] || s.name)}
    </button>`).join('') +
    `<button class="legend-btn" id="scale-btn" title="Cambiar escala del eje Y">${chartScale === 'log' ? 'Escala log' : 'Escala lineal'}</button>`;
  $('chart-legend').querySelectorAll('[data-series]').forEach((btn) => btn.addEventListener('click', () => {
    const i = Number(btn.dataset.series);
    hiddenSeries.has(i) ? hiddenSeries.delete(i) : hiddenSeries.add(i);
    btn.setAttribute('aria-pressed', String(!hiddenSeries.has(i)));
    drawChart();
  }));
  $('scale-btn').addEventListener('click', () => {
    chartScale = chartScale === 'log' ? 'lin' : 'log';
    $('scale-btn').textContent = chartScale === 'log' ? 'Escala log' : 'Escala lineal';
    drawChart();
  });

  const head = world.species.map((s) =>
    `<th style="color:var(--sp-${s.key})">${escapeHtml(SHORT_NAMES[s.key] || s.name)}</th>`).join('');
  const body = world.genes.map((g, i) =>
    `<tr><td title="${escapeHtml(GENE_DESC[i] || '')}">${escapeHtml(g.name)}</td>` +
    world.species.map((s) => `<td class="num" id="gene-${s.key}-${i}">—</td>`).join('') + '</tr>').join('');
  $('evo-table').innerHTML = `<thead><tr><th></th>${head}</tr></thead><tbody>${body}</tbody>`;

  const terrainNames = { 30: 'Agua', 31: 'Roca', 32: 'Pantano' };
  $('biome-legend').innerHTML =
    world.biomes.map((name, i) => `<span><i class="dot" style="background:${rgb(BIOME_BG[60 + i])}"></i>${escapeHtml(name)}</span>`).join('') +
    Object.entries(terrainNames).map(([code, name]) => `<span><i class="dot" style="background:${rgb(world.colors[code])}"></i>${name}</span>`).join('');
}

function updateStats(msg) {
  lastTick = msg.tick;
  $('tick').textContent = fmtInt(msg.tick);
  $('tick-ms').textContent = `${msg.tick_ms.toFixed(1)} ms`;
  setStatus('live', msg.clients > 1 ? `En vivo · ${msg.clients} conectados` : 'En vivo');

  const counts = world.species.map((s) => msg.counts[s.key] || 0);
  const total = counts.reduce((a, b) => a + b, 0) || 1;
  const ref = history.length > DELTA_WINDOW ? history[history.length - 1 - DELTA_WINDOW] : null;
  world.species.forEach((s, i) => {
    const el = $(`sp-${s.key}`);
    if (!el) return;
    el.classList.toggle('extinct', counts[i] === 0);
    el.querySelector('.species-count').textContent = fmtInt(counts[i]);
    el.querySelector('.species-bar > span').style.width = `${counts[i] / total * 100}%`;
    const delta = el.querySelector('.species-delta');
    const d = ref ? counts[i] - ref[i] : 0;
    delta.textContent = !ref || d === 0 ? '' : `${d > 0 ? '▲' : '▼'} ${fmtInt(Math.abs(d))}`;
    delta.className = `species-delta num ${d > 0 ? 'up' : d < 0 ? 'down' : ''}`;
  });
  $('infected-count').textContent = fmtInt(msg.infected);
  $('food-count').textContent = fmtInt(msg.food);

  world.species.forEach((s) => {
    const genes = msg.genes[s.key];
    world.genes.forEach((_, i) => {
      const el = $(`gene-${s.key}-${i}`);
      if (el) el.textContent = genes ? GENE_FMT[i](genes[i]) : '—';
    });
  });

  const temp = msg.temperature;
  $('season').textContent = msg.season;
  $('temp-value').textContent = `${temp >= 0 ? '+' : ''}${temp.toFixed(2)}`;
  $('temp-marker').style.left = `${(temp + 1) / 2 * 100}%`;
  const { fire, flood } = world.periods;
  if (fire) $('next-fire').textContent = `${fire - (msg.tick % fire)} ticks`;
  if (flood) $('next-flood').textContent = `${flood - (msg.tick % flood)} ticks`;

  const ter = msg.territory;
  $('territory-counts').textContent = `A ${fmtInt(ter.herb_a)} · P ${fmtInt(ter.predator)} · B ${fmtInt(ter.herb_b)}`;

  history.push(counts);
  if (history.length > MAX_HISTORY) history.shift();
  drawChart();

  if (msg.events && msg.events.length) addEvents(msg.events, true);
}

// ---------------------------------------------------------------------------
// Gráfica de población
// ---------------------------------------------------------------------------

const chart = $('pop-chart');
const chartCtx = chart.getContext('2d');
let chartHover = null;

function drawChart() {
  const cw = Math.round(chart.clientWidth * dpr), ch = Math.round(chart.clientHeight * dpr);
  if (!cw || !ch) return;
  if (chart.width !== cw || chart.height !== ch) { chart.width = cw; chart.height = ch; }
  const g = chartCtx;
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.clearRect(0, 0, cw, ch);
  g.fillStyle = '#0f1512';
  g.fillRect(0, 0, cw, ch);

  const n = history.length;
  $('chart-range').textContent = n > 1 ? `últimos ${n} ticks` : '';
  if (n < 2) return;

  let max = 1;
  for (const counts of history) counts.forEach((v, i) => { if (!hiddenSeries.has(i) && v > max) max = v; });
  const f = chartScale === 'log' ? Math.log1p : (v) => v;
  const fMax = f(max);
  const padTop = 6 * dpr, padBottom = 4 * dpr;
  const y = (v) => ch - padBottom - f(v) / fMax * (ch - padTop - padBottom);
  const x = (i) => i / (n - 1) * cw;

  // líneas guía con etiqueta
  // guías intermedias, omitiendo las que quedarían pegadas a la del máximo
  const guides = (chartScale === 'log' ? [10, 100, 1000, 10000] : [max / 2])
    .filter((v) => v < max && y(v) - y(max) > 14 * dpr);
  guides.push(max);
  g.font = `${10 * dpr}px ui-monospace, monospace`;
  g.textBaseline = 'top';
  for (const v of guides) {
    const gy = Math.round(y(v)) + 0.5;
    g.strokeStyle = 'rgba(255,255,255,0.06)';
    g.lineWidth = 1;
    g.beginPath(); g.moveTo(0, gy); g.lineTo(cw, gy); g.stroke();
    g.fillStyle = 'rgba(255,255,255,0.32)';
    g.fillText(fmtInt(Math.round(v)), 4 * dpr, Math.min(ch - 12 * dpr, gy + 2 * dpr));
  }

  world.species.forEach((s, si) => {
    if (hiddenSeries.has(si)) return;
    g.beginPath();
    history.forEach((counts, i) => (i ? g.lineTo(x(i), y(counts[si])) : g.moveTo(x(i), y(counts[si]))));
    g.strokeStyle = rgb(s.color);
    g.lineWidth = 1.6 * dpr;
    g.lineJoin = 'round';
    g.stroke();
  });

  if (chartHover !== null && chartHover < n) {
    const hx = x(chartHover);
    g.strokeStyle = 'rgba(255,255,255,0.35)';
    g.lineWidth = 1;
    g.beginPath(); g.moveTo(hx, 0); g.lineTo(hx, ch); g.stroke();
    world.species.forEach((s, si) => {
      if (hiddenSeries.has(si)) return;
      g.fillStyle = rgb(s.color);
      g.beginPath(); g.arc(hx, y(history[chartHover][si]), 2.5 * dpr, 0, Math.PI * 2); g.fill();
    });
  }
  updateChartTooltip();
}

function updateChartTooltip() {
  const tip = $('chart-tooltip');
  const n = history.length;
  if (chartHover === null || chartHover >= n) { tip.hidden = true; return; }
  const counts = history[chartHover];
  tip.innerHTML = `<div class="num" style="color:var(--faint)">Tick ${fmtInt(lastTick - (n - 1 - chartHover))}</div>` +
    world.species.map((s, i) => hiddenSeries.has(i) ? '' :
      `<div class="tt-row"><i class="dot" style="background:var(--sp-${s.key})"></i>${escapeHtml(SHORT_NAMES[s.key])}<b class="num">${fmtInt(counts[i])}</b></div>`).join('');
  tip.hidden = false;
  const px = chartHover / (n - 1) * chart.clientWidth;
  const left = px > chart.clientWidth / 2 ? px - tip.offsetWidth - 10 : px + 10;
  tip.style.left = `${left}px`;
}

chart.addEventListener('pointermove', (e) => {
  const n = history.length;
  if (n < 2) return;
  const r = chart.getBoundingClientRect();
  const i = Math.round((e.clientX - r.left) / r.width * (n - 1));
  chartHover = Math.max(0, Math.min(n - 1, i));
  drawChart();
});
chart.addEventListener('pointerleave', () => { chartHover = null; drawChart(); });

// ---------------------------------------------------------------------------
// Eventos
// ---------------------------------------------------------------------------

function describeEvent(ev) {
  if (ev.kind === 'fire') return { icon: 'sprites/fire.svg', text: 'Incendio forestal', color: world.colors[40] };
  if (ev.kind === 'flood') return { icon: 'sprites/flood.svg', text: 'Inundación', color: world.colors[41] };
  const s = speciesById(ev.species);
  return {
    icon: `sprites/${s ? s.key : 'herb_a'}.svg`,
    text: `Migración: llegan ${ev.count} × ${s ? s.name : '?'}`,
    color: s ? s.color : [200, 200, 200],
  };
}

function addEvents(newEvents, live) {
  events = [...newEvents.slice().reverse(), ...events].slice(0, MAX_EVENTS);
  renderEvents();
  if (!live) return;
  for (const ev of newEvents) {
    const d = describeEvent(ev);
    pings.push({ row: ev.row, col: ev.col, color: d.color, start: performance.now() });
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = d.text;
    $('toasts').appendChild(toast);
    setTimeout(() => toast.remove(), 4100);
  }
  scheduleRedraw();
}

function renderEvents() {
  const list = $('event-log');
  if (!events.length) { list.innerHTML = '<li class="empty">Sin eventos todavía</li>'; return; }
  list.innerHTML = events.map((ev, i) => {
    const d = describeEvent(ev);
    return `<li><button class="event-item" data-i="${i}" title="Ir al lugar del evento">
      <img src="${d.icon}" alt="" width="16" height="16"><span>${escapeHtml(d.text)}</span>
      <span class="ev-tick num">t${fmtInt(ev.tick)}</span></button></li>`;
  }).join('');
}

$('event-log').addEventListener('click', (e) => {
  const btn = e.target.closest('.event-item');
  if (!btn) return;
  const ev = events[Number(btn.dataset.i)];
  const d = describeEvent(ev);
  focusCell(ev.row, ev.col, 4);
  pings.push({ row: ev.row, col: ev.col, color: d.color, start: performance.now() });
  scheduleRedraw();
});

// ---------------------------------------------------------------------------
// WebSocket
// ---------------------------------------------------------------------------

let ws = null;
let retryDelay = 1000;

function setStatus(state, text) {
  $('status').dataset.state = state;
  $('status-text').textContent = text;
}

function handleInit(msg) {
  world.width = msg.width;
  world.height = msg.height;
  world.fps = msg.fps;
  world.species = msg.species;
  world.genes = msg.genes;
  world.biomes = msg.biomes;
  world.periods = msg.periods;
  world.colors = {};
  for (const [k, v] of Object.entries(msg.colors)) world.colors[Number(k)] = v;

  const raw = atob(msg.biome);
  biomeFrame = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) biomeFrame[i] = raw.charCodeAt(i);

  buildBackground();
  fgLow = makeLayer();
  fgHigh = makeLayer();
  buildLUTs();
  buildSidebar();

  history.length = 0;
  history.push(...msg.history);
  events = [];
  addEvents(msg.events || [], false);

  resizeCanvas();
  clampPan();
  scheduleRedraw();
}

function connect() {
  setStatus(ws ? 'retry' : 'connecting', ws ? 'Reconectando…' : 'Conectando…');
  ws = new WebSocket(WS_URL);
  ws.binaryType = 'arraybuffer';

  ws.onopen = () => { retryDelay = 1000; setStatus('live', 'En vivo'); };

  ws.onmessage = (event) => {
    if (typeof event.data !== 'string') {
      frame = new Uint8Array(event.data);
      frameDirty = true;
      if (viewMode === 'live') scheduleRedraw();
      requestCell();
      return;
    }
    const msg = JSON.parse(event.data);
    if (msg.type === 'init') handleInit(msg);
    else if (msg.type === 'stats') updateStats(msg);
    else if (msg.type === 'cell') showCellInfo(msg);
  };

  ws.onclose = () => {
    setStatus('retry', `Desconectado — reintentando en ${Math.round(retryDelay / 1000)} s`);
    setTimeout(connect, retryDelay);
    retryDelay = Math.min(retryDelay * 2, 15000);
  };
}

// ---------------------------------------------------------------------------
// Changelog (Markdown mínimo y seguro: se escapa antes de dar formato)
// ---------------------------------------------------------------------------

function renderMarkdown(md) {
  const inline = (s) => escapeHtml(s)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
  let html = '', inList = false;
  for (const line of md.split('\n')) {
    const t = line.trim();
    if (t.startsWith('- ')) {
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${inline(t.slice(2))}</li>`;
      continue;
    }
    if (inList && t) { html += '</ul>'; inList = false; }
    if (t.startsWith('## ')) html += `<h3>${inline(t.slice(3))}</h3>`;
  }
  return html + (inList ? '</ul>' : '');
}

fetch('CHANGELOG.md')
  .then((r) => (r.ok ? r.text() : Promise.reject()))
  .then((text) => { $('changelog').innerHTML = renderMarkdown(text); })
  .catch(() => { $('changelog').textContent = 'Changelog no disponible.'; });

loadSprites();
resizeCanvas();
connect();
