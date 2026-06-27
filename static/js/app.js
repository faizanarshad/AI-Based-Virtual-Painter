/**
 * Virtual Painter — Main application.
 * Wires MediaPipe Hands → gesture recognition → Painter drawing engine.
 */

/* ── Palette & tool definitions ─────────────────────────────────────── */
const COLORS = [
  { name:'Red',       hex:'#ef4444' }, { name:'Orange',    hex:'#f97316' },
  { name:'Yellow',    hex:'#eab308' }, { name:'Lime',       hex:'#84cc16' },
  { name:'Green',     hex:'#22c55e' }, { name:'Teal',       hex:'#14b8a6' },
  { name:'Cyan',      hex:'#06b6d4' }, { name:'Sky',        hex:'#0ea5e9' },
  { name:'Blue',      hex:'#3b82f6' }, { name:'Violet',     hex:'#8b5cf6' },
  { name:'Purple',    hex:'#a855f7' }, { name:'Fuchsia',    hex:'#d946ef' },
  { name:'Pink',      hex:'#ec4899' }, { name:'Rose',       hex:'#f43f5e' },
  { name:'White',     hex:'#ffffff' }, { name:'Silver',     hex:'#cbd5e1' },
  { name:'Gray',      hex:'#64748b' }, { name:'Dark',       hex:'#334155' },
  { name:'Gold',      hex:'#fbbf24' }, { name:'Coral',      hex:'#fb7185' },
];

const TOOLS = [
  { id:'brush',   label:'Brush',   icon:'fa-paintbrush',    accent:'#10b981' },
  { id:'spray',   label:'Spray',   icon:'fa-spray-can',     accent:'#f97316' },
  { id:'rainbow', label:'Rainbow', icon:'fa-rainbow',        accent:'#a855f7' },
  { id:'neon',    label:'Neon',    icon:'fa-star',           accent:'#06b6d4' },
  { id:'mirror',  label:'Mirror',  icon:'fa-arrows-left-right', accent:'#eab308' },
  { id:'eraser',  label:'Eraser',  icon:'fa-eraser',         accent:'#ef4444' },
  { id:'fill',    label:'Fill',    icon:'fa-fill-drip',      accent:'#3b82f6' },
];
const ACTIONS = [
  { id:'clear', label:'Clear',  icon:'fa-trash',         accent:'#ef4444' },
  { id:'save',  label:'Save',   icon:'fa-floppy-disk',   accent:'#10b981' },
  { id:'undo',  label:'Undo',   icon:'fa-rotate-left',   accent:'#6366f1' },
  { id:'redo',  label:'Redo',   icon:'fa-rotate-right',  accent:'#6366f1' },
];
const SHAPES = [
  { id:'Circle',    icon:'○' },
  { id:'Rectangle', icon:'□' },
  { id:'Triangle',  icon:'△' },
  { id:'Line',      icon:'╱' },
];
const BRUSH_SIZES  = [3, 6, 10, 15, 22, 32, 45];

/* ── State ──────────────────────────────────────────────────────────── */
const state = {
  tool:         'brush',
  color:        '#ff00ff',
  colorName:    'Magenta',
  brushIdx:     3,
  get size()    { return BRUSH_SIZES[this.brushIdx]; },
  selectedShape: null,
  shapeStart:   null,
  shapePreviewSnap: null,   // ImageData snapshot before shape preview
  prevX: 0, prevY: 0,
  drawing: false,
  aiPoints: [],
  aiActive: false,
  fpsFrames: 0, fpsLast: performance.now(), fps: 0,
};

/* ── DOM refs ────────────────────────────────────────────────────────── */
const video          = document.getElementById('video');
const landmarkCanvas = document.getElementById('landmarkCanvas');
const drawingCanvas  = document.getElementById('drawingCanvas');
const lCtx           = landmarkCanvas.getContext('2d');
const canvasArea     = document.getElementById('canvasArea');
const camStatus      = document.getElementById('camStatus');
const aiHint         = document.getElementById('aiHint');

/* ── Init painter ───────────────────────────────────────────────────── */
const painter = new Painter(drawingCanvas);

/* ── Build UI ───────────────────────────────────────────────────────── */
function buildUI() {
  // Colour palette
  const palette = document.getElementById('palette');
  COLORS.forEach(c => {
    const sw = document.createElement('div');
    sw.className = 'color-swatch';
    sw.style.background = c.hex;
    sw.title = c.name;
    sw.dataset.hex  = c.hex;
    sw.dataset.name = c.name;
    if (c.name === 'Magenta') sw.classList.add('active');
    sw.addEventListener('click', () => selectColor(c.hex, c.name));
    palette.appendChild(sw);
  });

  // Tool buttons
  const toolList = document.getElementById('toolList');
  TOOLS.forEach(t => {
    const btn = document.createElement('button');
    btn.className = 'tool-btn' + (t.id === 'brush' ? ' active' : '');
    btn.dataset.tool = t.id;
    btn.style.setProperty('--accent', t.accent);
    btn.innerHTML = `<i class="fa-solid ${t.icon}"></i>${t.label}`;
    btn.addEventListener('click', () => selectTool(t.id));
    toolList.appendChild(btn);
  });

  // Action buttons
  const actionList = document.getElementById('actionList');
  ACTIONS.forEach(a => {
    const btn = document.createElement('button');
    btn.className = 'action-btn';
    btn.style.setProperty('--accent', a.accent);
    btn.innerHTML = `<i class="fa-solid ${a.icon}"></i>${a.label}`;
    btn.addEventListener('click', () => handleAction(a.id));
    actionList.appendChild(btn);
  });

  // Shape buttons
  const grid = document.getElementById('shapeGrid');
  SHAPES.forEach(s => {
    const btn = document.createElement('button');
    btn.className = 'shape-btn';
    btn.dataset.shape = s.id;
    btn.innerHTML = `<span class="sh-icon">${s.icon}</span><span>${s.id}</span>`;
    btn.addEventListener('click', () => selectShape(s.id));
    grid.appendChild(btn);
  });

  // Size slider
  const slider  = document.getElementById('sizeSlider');
  const sizeNum = document.getElementById('sizeNum');
  const sizeDot = document.getElementById('sizeDot');
  slider.value  = state.size;
  slider.addEventListener('input', () => {
    const v = parseInt(slider.value);
    state.brushIdx = BRUSH_SIZES.findIndex(s => s >= v) ?? BRUSH_SIZES.length-1;
    if (state.brushIdx < 0) state.brushIdx = BRUSH_SIZES.length - 1;
    // Allow free value from slider
    const custom = v;
    BRUSH_SIZES[state.brushIdx] = custom;
    sizeNum.textContent = v;
    sizeDot.style.width = sizeDot.style.height = Math.min(32, Math.max(4, v/1.5)) + 'px';
    updateStatus();
  });
  updateSizeDot();
}

function updateSizeDot() {
  const dot = document.getElementById('sizeDot');
  const s   = Math.min(32, Math.max(4, state.size / 1.5));
  dot.style.width = dot.style.height = s + 'px';
  dot.style.background = state.color;
  dot.style.boxShadow  = `0 0 8px ${state.color}`;
}

/* ── Selection helpers ──────────────────────────────────────────────── */
function selectColor(hex, name) {
  state.color     = hex;
  state.colorName = name;
  document.querySelectorAll('.color-swatch').forEach(s => {
    s.classList.toggle('active', s.dataset.hex === hex);
  });
  document.getElementById('activeRing').style.background    = hex;
  document.getElementById('activeRing').style.boxShadow     = `0 0 20px ${hex}`;
  document.getElementById('activeColorName').textContent     = name;
  document.getElementById('activeColorHex').textContent      = hex;
  updateSizeDot();
}

function selectTool(id) {
  state.tool = id;
  state.selectedShape = null;
  document.querySelectorAll('.tool-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.tool === id));
  document.querySelectorAll('.shape-btn').forEach(b =>
    b.classList.remove('active'));
  updateStatus();
}

function selectShape(id) {
  state.selectedShape = id;
  state.tool          = 'shape';
  document.querySelectorAll('.shape-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.shape === id));
  document.querySelectorAll('.tool-btn').forEach(b =>
    b.classList.remove('active'));
  updateStatus();
}

function handleAction(id) {
  if (id === 'clear') painter.clear();
  if (id === 'save')  painter.save();
  if (id === 'undo')  painter.undo();
  if (id === 'redo')  painter.redo();
}

/* ── Status bar ─────────────────────────────────────────────────────── */
function updateStatus() {
  const label = state.selectedShape
    ? `${state.selectedShape} — drag to draw, lift to commit`
    : `${TOOLS.find(t=>t.id===state.tool)?.label ?? state.tool} — size ${state.size}`;
  document.getElementById('sbTool').innerHTML =
    `<i class="fa-solid ${TOOLS.find(t=>t.id===state.tool)?.icon ?? 'fa-pen'}"></i> ${label}`;
}

/* ── Canvas resize ──────────────────────────────────────────────────── */
function resizeCanvases() {
  const r = canvasArea.getBoundingClientRect();
  const w = Math.round(r.width), h = Math.round(r.height);
  [drawingCanvas, landmarkCanvas].forEach(c => {
    if (c.width !== w || c.height !== h) {
      const snap = c.getContext('2d').getImageData(0, 0, c.width, c.height);
      c.width = w; c.height = h;
      c.getContext('2d').putImageData(snap, 0, 0);
    }
  });
}
new ResizeObserver(resizeCanvases).observe(canvasArea);

/* ── MediaPipe setup ────────────────────────────────────────────────── */
const hands = new Hands({
  locateFile: f => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}`
});
hands.setOptions({
  selfieMode:            true,
  maxNumHands:           1,
  modelComplexity:       1,
  minDetectionConfidence: 0.75,
  minTrackingConfidence:  0.6,
});
hands.onResults(onResults);

const camera = new Camera(video, {
  onFrame: async () => { await hands.send({ image: video }); },
  width: 1280, height: 720,
});
camera.start().then(() => {
  camStatus.classList.add('hidden');
  resizeCanvases();
}).catch(err => {
  camStatus.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> Camera error: ${err.message}`;
});

/* ── Main results callback ──────────────────────────────────────────── */
function onResults(results) {
  // FPS
  state.fpsFrames++;
  const now = performance.now();
  if (now - state.fpsLast > 500) {
    state.fps = Math.round(state.fpsFrames / ((now - state.fpsLast) / 1000));
    state.fpsFrames = 0; state.fpsLast = now;
    document.getElementById('fps').textContent = state.fps;
  }

  // Clear landmark overlay
  lCtx.clearRect(0, 0, landmarkCanvas.width, landmarkCanvas.height);

  if (!results.multiHandLandmarks?.length) {
    resetDrawState();
    setGestureLabel('No hand', false);
    return;
  }

  const lms = results.multiHandLandmarks[0];
  const cw  = drawingCanvas.width;
  const ch  = drawingCanvas.height;

  // Draw hand skeleton on landmark canvas
  drawConnectors(lCtx, lms, HAND_CONNECTIONS,
    { color: 'rgba(140,80,255,.6)', lineWidth: 2 });
  drawLandmarks(lCtx, lms,
    { color: 'rgba(255,255,255,.8)', lineWidth: 1, radius: 4 });

  const f   = fingersUp(lms);
  const tip = landmarkToCanvas(lms[8], cw, ch);   // index tip
  const gesture = classifyGesture(f);

  // ── AI snap: 3+ fingers ────────────────────────────────────────────
  if (gesture === 'snap') {
    if (state.aiActive && state.aiPoints.length > 4) {
      const kind = detectShape(state.aiPoints);
      if (kind) {
        painter.saveState();
        painter.completeShape(kind, state.aiPoints, state.color, state.size);
        showHint(`✦ AI snapped → ${kind}`, 1800);
      }
    }
    resetDrawState();
    setGestureLabel('AI Snap 🤟', true);
    aiHint.classList.add('show');
    return;
  }
  aiHint.classList.remove('show');

  // ── Select mode: 2 fingers ─────────────────────────────────────────
  if (gesture === 'select') {
    resetDrawState();
    setGestureLabel('Select ✌', false);
    drawCursor(tip.x, tip.y, 'select');
    return;
  }

  // ── Draw mode: 1 finger ────────────────────────────────────────────
  if (gesture === 'draw') {
    setGestureLabel('Draw ☝', false);
    const x = tip.x, y = tip.y;

    if (!state.drawing) {
      state.prevX = x; state.prevY = y;
      state.drawing = true;
      if (state.selectedShape) state.shapeStart = { x, y };
    }

    if (state.tool === 'shape' && state.selectedShape && state.shapeStart) {
      // Restore pre-shape snapshot so preview doesn't compound
      if (state.shapePreviewSnap) {
        painter.ctx.putImageData(state.shapePreviewSnap, 0, 0);
      } else {
        state.shapePreviewSnap = painter.ctx.getImageData(
          0, 0, cw, ch);
      }
      painter.drawShape(state.selectedShape,
        state.shapeStart.x, state.shapeStart.y, x, y,
        state.color, state.size);

    } else if (state.tool === 'fill') {
      painter.saveState();
      painter.fill(x, y, state.color);
      resetDrawState();

    } else {
      painter.apply(state.tool, state.prevX, state.prevY, x, y,
                    state.color, state.size);
      if (state.tool === 'brush') {
        state.aiPoints.push({ x, y });
        state.aiActive = true;
      }
    }

    state.prevX = x; state.prevY = y;
    drawCursor(x, y, state.tool);
    return;
  }

  // ── Finger lifted / fist ────────────────────────────────────────────
  if (state.drawing && state.tool === 'shape'
      && state.selectedShape && state.shapeStart) {
    painter.saveState();
    state.shapePreviewSnap = null;
  }
  resetDrawState();
  setGestureLabel('Idle', false);
}

/* ── Helpers ────────────────────────────────────────────────────────── */
function resetDrawState() {
  state.prevX = 0; state.prevY = 0;
  state.drawing = false;
  state.shapeStart = null;
  state.shapePreviewSnap = null;
  state.aiPoints  = [];
  state.aiActive  = false;
  lCtx.clearRect(0, 0, landmarkCanvas.width, landmarkCanvas.height);
}

function setGestureLabel(text, highlight) {
  const el = document.getElementById('gestureText');
  el.textContent = text;
  document.getElementById('gestureBadge').style.color =
    highlight ? 'var(--a2)' : '';
}

function drawCursor(x, y, tool) {
  const ctx = lCtx;
  const r   = Math.max(8, state.size / 2);
  ctx.save();
  ctx.lineWidth = 2;

  if (tool === 'eraser') {
    ctx.strokeStyle = 'rgba(200,200,200,.8)';
    ctx.beginPath(); ctx.arc(x, y, r, 0, 2*Math.PI); ctx.stroke();
  } else if (tool === 'spray') {
    ctx.strokeStyle = state.color;
    ctx.setLineDash([3, 4]);
    ctx.beginPath(); ctx.arc(x, y, r, 0, 2*Math.PI); ctx.stroke();
    ctx.setLineDash([]);
  } else if (tool === 'neon') {
    ctx.shadowBlur = 10; ctx.shadowColor = state.color;
    ctx.strokeStyle = state.color;
    ctx.beginPath(); ctx.arc(x, y, r, 0, 2*Math.PI); ctx.stroke();
    ctx.shadowBlur = 0;
  } else {
    ctx.strokeStyle = '#ffffff';
    ctx.beginPath(); ctx.arc(x, y, r, 0, 2*Math.PI); ctx.stroke();
    ctx.strokeStyle = state.color;
    ctx.beginPath(); ctx.arc(x, y, r, 0, 2*Math.PI); ctx.stroke();
  }
  // Centre dot
  ctx.fillStyle = '#fff';
  ctx.beginPath(); ctx.arc(x, y, 2, 0, 2*Math.PI); ctx.fill();
  ctx.restore();
}

let _hintTimer = null;
function showHint(msg, ms = 2000) {
  aiHint.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> ${msg}`;
  aiHint.classList.add('show');
  clearTimeout(_hintTimer);
  _hintTimer = setTimeout(() => aiHint.classList.remove('show'), ms);
}

/* ── Keyboard shortcuts ─────────────────────────────────────────────── */
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  switch(e.key.toLowerCase()) {
    case 'u': painter.undo(); break;
    case 'r': painter.redo(); break;
    case 's': painter.save(); break;
    case 'c': painter.clear(); break;
    case '[':
      state.brushIdx = Math.max(0, state.brushIdx - 1);
      document.getElementById('sizeSlider').value = state.size;
      document.getElementById('sizeNum').textContent = state.size;
      updateSizeDot(); updateStatus(); break;
    case ']':
      state.brushIdx = Math.min(BRUSH_SIZES.length-1, state.brushIdx+1);
      document.getElementById('sizeSlider').value = state.size;
      document.getElementById('sizeNum').textContent = state.size;
      updateSizeDot(); updateStatus(); break;
  }
});

/* ── Boot ───────────────────────────────────────────────────────────── */
buildUI();
selectColor('#ff00ff', 'Magenta');
updateStatus();

// Voice status (not available in browser, show info)
const sbVoice = document.getElementById('sbVoice');
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  sbVoice.innerHTML = '<i class="fa-solid fa-microphone"></i> Voice ready';
  sbVoice.className = 'sb-voice on';
} else {
  sbVoice.innerHTML = '<i class="fa-solid fa-microphone-slash"></i> No voice API';
  sbVoice.className = 'sb-voice off';
}
