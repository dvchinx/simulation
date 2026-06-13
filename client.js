const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const statusEl = document.getElementById('status');

const TOTAL_CELLS = 200 * 200;
const WS_URL = window.location.protocol === 'https:'
  ? `wss://${window.location.hostname}/ws`
  : `ws://${window.location.hostname}:8765`;

let width = 200;
let height = 200;
let colorMap = {};

function pct(n) { return (n / TOTAL_CELLS * 100).toFixed(1) + '%'; }

const GENE_FMT = [
  v => v.toFixed(2),   // velocidad
  v => v.toFixed(0),   // reprod.
  v => v.toFixed(2),   // eficiencia
  v => v.toFixed(1),   // visión
  v => v.toFixed(3),   // mutación
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
  document.getElementById('infected-count').textContent = msg.infected;
  document.getElementById('food-count').textContent = msg.food;
  document.getElementById('herb-a-bar').style.width = pct(msg.herb_a);
  document.getElementById('pred-bar').style.width = pct(msg.predators);
  document.getElementById('herb-b-bar').style.width = pct(msg.herb_b);
  document.getElementById('infected-bar').style.width = pct(msg.infected);
  document.getElementById('food-bar').style.width = pct(msg.food);
  updateGenes('a', msg.genome_a);
  updateGenes('p', msg.genome_p);
  updateGenes('b', msg.genome_b);
}

function render(bytes) {
  const img = ctx.createImageData(width, height);
  const px = img.data;
  for (let i = 0; i < bytes.length; i++) {
    const c = colorMap[bytes[i]] || [255, 0, 255];
    px[i * 4]     = c[0];
    px[i * 4 + 1] = c[1];
    px[i * 4 + 2] = c[2];
    px[i * 4 + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
}

function connect() {
  const ws = new WebSocket(WS_URL);
  ws.binaryType = 'arraybuffer';

  ws.onopen = () => { statusEl.textContent = 'Conectado'; };

  ws.onmessage = (event) => {
    if (typeof event.data === 'string') {
      const msg = JSON.parse(event.data);
      if (msg.type === 'init') {
        width = msg.width;
        height = msg.height;
        canvas.width = width;
        canvas.height = height;
        colorMap = {};
        for (const [k, v] of Object.entries(msg.colors)) {
          colorMap[parseInt(k)] = v;
        }
      } else if (msg.type === 'stats') {
        updateStats(msg);
      }
    } else {
      render(new Uint8Array(event.data));
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

connect();

// ---- Zoom / Pan ----
const view = document.getElementById('view');
let zoom = 1;
let panX = 0;
let panY = 0;
const MIN_ZOOM = 1;
const MAX_ZOOM = 10;

function applyTransform() {
  canvas.style.transform = `translate(${panX}px, ${panY}px) scale(${zoom})`;
  view.style.cursor = zoom > 1 ? 'grab' : 'default';
}

function resetZoom() {
  zoom = 1; panX = 0; panY = 0;
  applyTransform();
}

// Zoom hacia un punto (clientX, clientY) en coordenadas de viewport
function zoomAt(factor, clientX, clientY) {
  const rect = view.getBoundingClientRect();
  // mx/my relativo al centro del view (transform-origin: center center)
  const mx = clientX - (rect.left + rect.width / 2);
  const my = clientY - (rect.top + rect.height / 2);
  const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom * factor));
  if (newZoom === zoom) return;
  panX = mx - (mx - panX) * (newZoom / zoom);
  panY = my - (my - panY) * (newZoom / zoom);
  zoom = newZoom;
  if (zoom <= MIN_ZOOM) { zoom = MIN_ZOOM; panX = 0; panY = 0; }
  applyTransform();
}

// Scroll wheel
view.addEventListener('wheel', (e) => {
  e.preventDefault();
  zoomAt(e.deltaY < 0 ? 1.15 : 1 / 1.15, e.clientX, e.clientY);
}, { passive: false });

// Doble click para resetear
view.addEventListener('dblclick', resetZoom);

// Drag con mouse
let dragging = false;
let dragX = 0, dragY = 0;

view.addEventListener('mousedown', (e) => {
  if (zoom <= 1 || e.button !== 0) return;
  dragging = true;
  dragX = e.clientX;
  dragY = e.clientY;
  view.style.cursor = 'grabbing';
  e.preventDefault();
});
window.addEventListener('mousemove', (e) => {
  if (!dragging) return;
  panX += e.clientX - dragX;
  panY += e.clientY - dragY;
  dragX = e.clientX;
  dragY = e.clientY;
  applyTransform();
});
window.addEventListener('mouseup', () => {
  if (!dragging) return;
  dragging = false;
  view.style.cursor = zoom > 1 ? 'grab' : 'default';
});

// Touch: pinch zoom + drag con un dedo
const activeTouches = {};

view.addEventListener('touchstart', (e) => {
  e.preventDefault();
  for (const t of e.changedTouches) {
    activeTouches[t.identifier] = { x: t.clientX, y: t.clientY };
  }
}, { passive: false });

view.addEventListener('touchmove', (e) => {
  e.preventDefault();
  const prev = {};
  for (const [id, pos] of Object.entries(activeTouches)) prev[id] = { ...pos };
  for (const t of e.changedTouches) {
    activeTouches[t.identifier] = { x: t.clientX, y: t.clientY };
  }

  const ids = Object.keys(activeTouches);

  if (ids.length >= 2) {
    const [a, b] = [activeTouches[ids[0]], activeTouches[ids[1]]];
    const [pa, pb] = [prev[ids[0]], prev[ids[1]]];
    if (!pa || !pb) return;

    const newDist = Math.hypot(b.x - a.x, b.y - a.y);
    const oldDist = Math.hypot(pb.x - pa.x, pb.y - pa.y);
    if (oldDist === 0) return;

    const midX = (a.x + b.x) / 2;
    const midY = (a.y + b.y) / 2;
    const prevMidX = (pa.x + pb.x) / 2;
    const prevMidY = (pa.y + pb.y) / 2;

    const rect = view.getBoundingClientRect();
    const mx = midX - (rect.left + rect.width / 2);
    const my = midY - (rect.top + rect.height / 2);

    const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom * (newDist / oldDist)));
    panX = mx - (mx - panX) * (newZoom / zoom);
    panY = my - (my - panY) * (newZoom / zoom);
    zoom = newZoom;
    // Pan adicional por movimiento del punto medio
    panX += midX - prevMidX;
    panY += midY - prevMidY;
    if (zoom <= MIN_ZOOM) { zoom = MIN_ZOOM; panX = 0; panY = 0; }
    applyTransform();
  } else if (ids.length === 1 && zoom > 1) {
    const id = ids[0];
    const p = prev[id];
    const c = activeTouches[id];
    if (p) {
      panX += c.x - p.x;
      panY += c.y - p.y;
      applyTransform();
    }
  }
}, { passive: false });

let lastTapTime = 0;
view.addEventListener('touchend', (e) => {
  e.preventDefault();
  for (const t of e.changedTouches) delete activeTouches[t.identifier];
  // Doble tap para resetear
  const now = Date.now();
  if (now - lastTapTime < 300 && e.changedTouches.length === 1) resetZoom();
  lastTapTime = now;
}, { passive: false });
