/**
 * Virtual Painter — Main application.
 * MediaPipe Hands → gesture recognition → Painter drawing engine.
 */

/* ── Definitions ─────────────────────────────────────────────────────── */
const COLORS = [
  {name:'Red',       hex:'#ef4444'},{name:'Orange',   hex:'#f97316'},
  {name:'Yellow',    hex:'#eab308'},{name:'Lime',     hex:'#84cc16'},
  {name:'Green',     hex:'#22c55e'},{name:'Teal',     hex:'#14b8a6'},
  {name:'Cyan',      hex:'#06b6d4'},{name:'Sky',      hex:'#0ea5e9'},
  {name:'Blue',      hex:'#3b82f6'},{name:'Violet',   hex:'#8b5cf6'},
  {name:'Purple',    hex:'#a855f7'},{name:'Fuchsia',  hex:'#d946ef'},
  {name:'Pink',      hex:'#ec4899'},{name:'Rose',     hex:'#f43f5e'},
  {name:'White',     hex:'#ffffff'},{name:'Silver',   hex:'#cbd5e1'},
  {name:'Gray',      hex:'#64748b'},{name:'Dark',     hex:'#334155'},
  {name:'Gold',      hex:'#fbbf24'},{name:'Coral',    hex:'#fb7185'},
];

const TOOLS = [
  {id:'brush',      label:'Brush',      icon:'fa-paintbrush',      accent:'#10b981'},
  {id:'pen',        label:'Pen',         icon:'fa-pen-nib',          accent:'#06b6d4'},
  {id:'spray',      label:'Spray',       icon:'fa-spray-can',        accent:'#f97316'},
  {id:'watercolor', label:'Watercolor',  icon:'fa-droplet',          accent:'#38bdf8'},
  {id:'glitter',    label:'Glitter',     icon:'fa-star',             accent:'#f59e0b'},
  {id:'ink',        label:'Ink',         icon:'fa-feather',          accent:'#c084fc'},
  {id:'rainbow',    label:'Rainbow',     icon:'fa-rainbow',          accent:'#a855f7'},
  {id:'neon',       label:'Neon',        icon:'fa-bolt',             accent:'#34d399'},
  {id:'mirror',     label:'Mirror',      icon:'fa-arrows-left-right',accent:'#eab308'},
  {id:'pixel',      label:'Pixel',       icon:'fa-border-all',       accent:'#94a3b8'},
  {id:'text',       label:'Text',        icon:'fa-font',             accent:'#f472b6'},
  {id:'eyedrop',    label:'Eyedrop',     icon:'fa-eye-dropper',      accent:'#818cf8'},
  {id:'eraser',     label:'Eraser',      icon:'fa-eraser',           accent:'#ef4444'},
  {id:'fill',       label:'Fill',        icon:'fa-fill-drip',        accent:'#3b82f6'},
];

const ACTIONS = [
  {id:'clear',label:'Clear',  icon:'fa-trash',        accent:'#ef4444'},
  {id:'save', label:'Save',   icon:'fa-floppy-disk',  accent:'#10b981'},
  {id:'undo', label:'Undo',   icon:'fa-rotate-left',  accent:'#6366f1'},
  {id:'redo', label:'Redo',   icon:'fa-rotate-right', accent:'#6366f1'},
];

const SHAPES = [
  {id:'Circle',    icon:'○'},{id:'Rectangle', icon:'□'},
  {id:'Triangle',  icon:'△'},{id:'Line',       icon:'╱'},
  {id:'Star',      icon:'★'},{id:'Heart',      icon:'♥'},
  {id:'Diamond',   icon:'◆'},{id:'Pentagon',   icon:'⬠'},
  {id:'Hexagon',   icon:'⬡'},{id:'Arrow',      icon:'→'},
];

const BRUSH_SIZES = [2, 5, 9, 14, 20, 30, 44];
const BG_MODES    = ['camera','black','white','grid'];

/* ── Application state ───────────────────────────────────────────────── */
const state = {
  tool:           'brush',
  color:          '#ef4444',
  colorName:      'Red',
  brushIdx:       3,
  get size()      { return BRUSH_SIZES[this.brushIdx]; },
  selectedShape:  null,
  shapeStart:     null,
  shapeSnap:      null,
  prevX: 0, prevY: 0,
  drawing:        false,
  aiPoints:       [],
  aiActive:       false,
  opacity:        1.0,        // 0.1 – 1.0
  symmetry:       0,          // 0=off, 2=mirror-H, 4=quad
  bgModeIdx:      0,          // index into BG_MODES
  showGrid:       false,
  textPending:    null,       // {x,y} waiting for keyboard
  fps: 0, fpsFrames: 0, fpsLast: performance.now(),
};

/* ── DOM refs ────────────────────────────────────────────────────────── */
const video          = document.getElementById('video');
const landmarkCanvas = document.getElementById('landmarkCanvas');
const drawingCanvas  = document.getElementById('drawingCanvas');
const bgCanvas       = document.getElementById('bgCanvas');
const lCtx           = landmarkCanvas.getContext('2d');
const bgCtx          = bgCanvas.getContext('2d');
const canvasArea     = document.getElementById('canvasArea');
const camStatus      = document.getElementById('camStatus');
const aiHint         = document.getElementById('aiHint');
const textOverlay    = document.getElementById('textOverlay');
const textInput      = document.getElementById('textInput');

const painter = new Painter(drawingCanvas);

/* ── Build UI ────────────────────────────────────────────────────────── */
function buildUI() {
  // Colour palette
  const palette = document.getElementById('palette');
  COLORS.forEach(c => {
    const sw = document.createElement('div');
    sw.className      = 'color-swatch';
    sw.style.background = c.hex;
    sw.title          = c.name;
    sw.dataset.hex    = c.hex;
    sw.dataset.name   = c.name;
    sw.addEventListener('click', () => selectColor(c.hex, c.name));
    palette.appendChild(sw);
  });

  // Tool buttons
  const toolList = document.getElementById('toolList');
  TOOLS.forEach(t => {
    const btn = document.createElement('button');
    btn.className    = 'tool-btn' + (t.id==='brush' ? ' active' : '');
    btn.dataset.tool = t.id;
    btn.style.setProperty('--accent', t.accent);
    btn.innerHTML    = `<i class="fa-solid ${t.icon}"></i>${t.label}`;
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
    btn.className    = 'shape-btn';
    btn.dataset.shape = s.id;
    btn.innerHTML    = `<span class="sh-icon">${s.icon}</span><span>${s.id}</span>`;
    btn.addEventListener('click', () => selectShape(s.id));
    grid.appendChild(btn);
  });

  // Opacity slider
  const opSlider = document.getElementById('opacitySlider');
  const opNum    = document.getElementById('opacityNum');
  if (opSlider) {
    opSlider.addEventListener('input', () => {
      state.opacity = parseFloat(opSlider.value);
      painter.opacity = state.opacity;
      opNum.textContent = Math.round(state.opacity * 100) + '%';
    });
  }

  // Size slider
  const sizeSlider = document.getElementById('sizeSlider');
  const sizeNum    = document.getElementById('sizeNum');
  if (sizeSlider) {
    sizeSlider.addEventListener('input', () => {
      BRUSH_SIZES[state.brushIdx] = parseInt(sizeSlider.value);
      sizeNum.textContent = state.size;
      updateSizeDot();
      updateStatus();
    });
  }

  // Symmetry buttons
  document.querySelectorAll('[data-sym]').forEach(btn => {
    btn.addEventListener('click', () => {
      state.symmetry = parseInt(btn.dataset.sym);
      document.querySelectorAll('[data-sym]').forEach(b =>
        b.classList.toggle('active', b===btn));
      drawSymGuide();
    });
  });

  // BG cycle button
  const bgBtn = document.getElementById('bgBtn');
  if (bgBtn) bgBtn.addEventListener('click', cycleBG);

  // Grid toggle
  const gridBtn = document.getElementById('gridBtn');
  if (gridBtn) gridBtn.addEventListener('click', toggleGrid);

  // Color picker (native)
  const colorPickerInput = document.getElementById('colorPickerInput');
  const activeRing       = document.getElementById('activeRing');
  if (activeRing && colorPickerInput) {
    activeRing.addEventListener('click', () => colorPickerInput.click());
    colorPickerInput.addEventListener('input', () => {
      selectColor(colorPickerInput.value, 'Custom');
    });
  }

  // Text overlay commit
  if (textInput) {
    textInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' && state.textPending) {
        const txt = textInput.value.trim();
        if (txt) {
          painter.saveState();
          painter.drawText(txt, state.textPending.x, state.textPending.y,
                           state.color, state.size);
        }
        hideTextOverlay();
      }
      if (e.key === 'Escape') hideTextOverlay();
      e.stopPropagation();
    });
    textOverlay.addEventListener('click', e => {
      if (e.target === textOverlay) hideTextOverlay();
    });
  }

  // Canvas click → text tool
  canvasArea.addEventListener('click', e => {
    if (state.tool !== 'text') return;
    const r  = drawingCanvas.getBoundingClientRect();
    const sx = drawingCanvas.width  / r.width;
    const sy = drawingCanvas.height / r.height;
    // Account for CSS mirror flip
    const cx = (r.right - e.clientX) * sx;
    const cy = (e.clientY - r.top)   * sy;
    showTextOverlay(cx, cy);
  });

  selectColor('#ef4444', 'Red');
  updateStatus();
}

/* ── Selection helpers ───────────────────────────────────────────────── */
function selectColor(hex, name) {
  state.color     = hex;
  state.colorName = name;
  document.querySelectorAll('.color-swatch').forEach(s =>
    s.classList.toggle('active', s.dataset.hex === hex));
  const ring = document.getElementById('activeRing');
  if (ring) { ring.style.background = hex; ring.style.boxShadow = `0 0 22px ${hex}`; }
  const nameEl = document.getElementById('activeColorName');
  const hexEl  = document.getElementById('activeColorHex');
  if (nameEl) nameEl.textContent = name;
  if (hexEl)  hexEl.textContent  = hex;
  updateSizeDot();
}

function selectTool(id) {
  state.tool = id; state.selectedShape = null;
  document.querySelectorAll('.tool-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.tool === id));
  document.querySelectorAll('.shape-btn').forEach(b => b.classList.remove('active'));
  updateStatus();
}

function selectShape(id) {
  state.selectedShape = id; state.tool = 'shape';
  document.querySelectorAll('.shape-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.shape === id));
  document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
  updateStatus();
}

function handleAction(id) {
  if (id==='clear') painter.clear();
  if (id==='save')  painter.save();
  if (id==='undo')  painter.undo();
  if (id==='redo')  painter.redo();
}

/* ── Background mode ─────────────────────────────────────────────────── */
function cycleBG() {
  state.bgModeIdx = (state.bgModeIdx + 1) % BG_MODES.length;
  applyBG();
  const btn = document.getElementById('bgBtn');
  if (btn) btn.textContent = '🎨 BG: ' + BG_MODES[state.bgModeIdx];
}

function applyBG() {
  const mode = BG_MODES[state.bgModeIdx];
  const cw   = bgCanvas.width, ch = bgCanvas.height;
  bgCtx.clearRect(0, 0, cw, ch);
  video.style.opacity = '1';

  if (mode === 'black') {
    video.style.opacity = '0';
    bgCtx.fillStyle = '#000'; bgCtx.fillRect(0, 0, cw, ch);
  } else if (mode === 'white') {
    video.style.opacity = '0';
    bgCtx.fillStyle = '#fff'; bgCtx.fillRect(0, 0, cw, ch);
  } else if (mode === 'grid') {
    video.style.opacity = '0';
    bgCtx.fillStyle = '#0a0015'; bgCtx.fillRect(0, 0, cw, ch);
    bgCtx.strokeStyle = 'rgba(100,60,160,.4)'; bgCtx.lineWidth = 1;
    const step = Math.round(cw / 20);
    for (let x=0; x<cw; x+=step) { bgCtx.beginPath(); bgCtx.moveTo(x,0); bgCtx.lineTo(x,ch); bgCtx.stroke(); }
    for (let y=0; y<ch; y+=step) { bgCtx.beginPath(); bgCtx.moveTo(0,y); bgCtx.lineTo(cw,y); bgCtx.stroke(); }
  }
}

/* ── Grid overlay ────────────────────────────────────────────────────── */
function toggleGrid() {
  state.showGrid = !state.showGrid;
  canvasArea.classList.toggle('show-grid', state.showGrid);
  const btn = document.getElementById('gridBtn');
  if (btn) btn.classList.toggle('active', state.showGrid);
}

/* ── Symmetry guide ──────────────────────────────────────────────────── */
function drawSymGuide() {
  // Drawn on landmark canvas each frame; just set flag
}

function applySymmetry(x0, y0, x1, y1, tool, color, size) {
  const cw = drawingCanvas.width, ch = drawingCanvas.height;
  if (state.symmetry >= 2) {
    painter.apply(tool, cw-x0, y0, cw-x1, y1, color, size); // H mirror
  }
  if (state.symmetry >= 4) {
    painter.apply(tool, x0, ch-y0, x1, ch-y1, color, size); // V mirror
    painter.apply(tool, cw-x0, ch-y0, cw-x1, ch-y1, color, size); // Quad
  }
}

/* ── Text overlay ────────────────────────────────────────────────────── */
function showTextOverlay(cx, cy) {
  state.textPending = { x: cx, y: cy };
  textOverlay.style.display = 'flex';
  textInput.value = '';
  textInput.style.color = state.color;
  textInput.style.fontSize = Math.max(14, state.size * 2) + 'px';
  textInput.focus();
}

function hideTextOverlay() {
  textOverlay.style.display = 'none';
  state.textPending = null;
}

/* ── Size + status ───────────────────────────────────────────────────── */
function updateSizeDot() {
  const dot = document.getElementById('sizeDot');
  if (!dot) return;
  const s = Math.min(32, Math.max(4, state.size / 1.5));
  dot.style.width = dot.style.height = s + 'px';
  dot.style.background = state.color;
  dot.style.boxShadow  = `0 0 8px ${state.color}`;
}

function updateStatus() {
  const t   = TOOLS.find(x => x.id === state.tool);
  const lbl = state.selectedShape
    ? `${state.selectedShape} — drag to draw, lift to commit`
    : `${t?.label ?? state.tool} — size ${state.size}`;
  const el  = document.getElementById('sbTool');
  if (el) el.innerHTML = `<i class="fa-solid ${t?.icon ?? 'fa-pen'}"></i> ${lbl}`;
}

/* ── Canvas resize ───────────────────────────────────────────────────── */
function resizeCanvases() {
  const r = canvasArea.getBoundingClientRect();
  const w = Math.round(r.width), h = Math.round(r.height);
  [drawingCanvas, landmarkCanvas, bgCanvas].forEach(c => {
    if (c.width !== w || c.height !== h) {
      const snap = c === drawingCanvas
        ? c.getContext('2d').getImageData(0, 0, c.width, c.height) : null;
      c.width = w; c.height = h;
      if (snap) c.getContext('2d').putImageData(snap, 0, 0);
    }
  });
  applyBG();
}
new ResizeObserver(resizeCanvases).observe(canvasArea);

/* ── MediaPipe setup ─────────────────────────────────────────────────── */
const hands = new Hands({
  locateFile: f => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}`
});
hands.setOptions({
  selfieMode: true, maxNumHands: 1, modelComplexity: 1,
  minDetectionConfidence: 0.75, minTrackingConfidence: 0.6,
});
hands.onResults(onResults);

const camera = new Camera(video, {
  onFrame: async () => { await hands.send({ image: video }); },
  width: 1280, height: 720,
});
camera.start().then(() => {
  document.getElementById('camStatus').classList.add('hidden');
  resizeCanvases();
}).catch(err => {
  document.getElementById('camStatus').innerHTML =
    `<i class="fa-solid fa-circle-exclamation"></i> Camera error: ${err.message}`;
});

/* ── Main results callback ───────────────────────────────────────────── */
function onResults(results) {
  // FPS
  state.fpsFrames++;
  const now = performance.now();
  if (now - state.fpsLast > 500) {
    state.fps = Math.round(state.fpsFrames / ((now - state.fpsLast) / 1000));
    state.fpsFrames = 0; state.fpsLast = now;
    document.getElementById('fps').textContent = state.fps;
  }

  lCtx.clearRect(0, 0, landmarkCanvas.width, landmarkCanvas.height);

  // Symmetry guide lines
  if (state.symmetry >= 2) {
    const cw = landmarkCanvas.width, ch = landmarkCanvas.height;
    lCtx.save();
    lCtx.setLineDash([6,4]); lCtx.lineWidth = 1;
    lCtx.strokeStyle = 'rgba(168,85,247,.5)';
    lCtx.beginPath(); lCtx.moveTo(cw/2,0); lCtx.lineTo(cw/2,ch); lCtx.stroke();
    if (state.symmetry >= 4) {
      lCtx.beginPath(); lCtx.moveTo(0,ch/2); lCtx.lineTo(cw,ch/2); lCtx.stroke();
    }
    lCtx.setLineDash([]); lCtx.restore();
  }

  if (!results.multiHandLandmarks?.length) {
    resetDrawState();
    setGestureBadge('No hand', false);
    return;
  }

  const lms = results.multiHandLandmarks[0];
  const cw  = drawingCanvas.width, ch = drawingCanvas.height;

  drawConnectors(lCtx, lms, HAND_CONNECTIONS,
    {color:'rgba(140,80,255,.6)', lineWidth:2});
  drawLandmarks(lCtx, lms,
    {color:'rgba(255,255,255,.8)', lineWidth:1, radius:4});

  const f       = fingersUp(lms);
  const gesture = classifyGesture(f);
  const tip     = landmarkToCanvas(lms[8], cw, ch);

  // ── AI snap ──────────────────────────────────────────────────────
  if (gesture === 'snap') {
    if (state.aiActive && state.aiPoints.length > 4) {
      const kind = detectShape(state.aiPoints);
      if (kind) {
        painter.saveState();
        painter.completeShape(kind, state.aiPoints, state.color, state.size);
        showHint(`✦ AI snapped → ${kind}`, 1800);
      }
    }
    resetDrawState(); setGestureBadge('AI Snap 🤟', true);
    aiHint.classList.add('show'); return;
  }
  aiHint.classList.remove('show');

  // ── Select ───────────────────────────────────────────────────────
  if (gesture === 'select') {
    resetDrawState(); setGestureBadge('Select ✌', false);
    drawCursor(tip.x, tip.y, 'select'); return;
  }

  // ── Draw ─────────────────────────────────────────────────────────
  if (gesture === 'draw') {
    setGestureBadge('Draw ☝', false);
    const x = tip.x, y = tip.y;

    if (!state.drawing) {
      state.prevX = x; state.prevY = y; state.drawing = true;
      if (state.selectedShape) state.shapeStart = {x, y};
    }

    if (state.tool === 'eyedrop') {
      const col = painter.eyedrop(x, y);
      if (col) selectColor(col, 'Sampled');
      resetDrawState(); return;
    }

    if (state.tool === 'text') {
      if (!state.textPending) showTextOverlay(x, y);
      resetDrawState(); return;
    }

    if (state.tool === 'fill') {
      painter.saveState(); painter.fill(x, y, state.color);
      resetDrawState(); return;
    }

    if (state.tool === 'shape' && state.selectedShape && state.shapeStart) {
      if (state.shapeSnap) painter.ctx.putImageData(state.shapeSnap, 0, 0);
      else state.shapeSnap = painter.ctx.getImageData(0, 0, cw, ch);
      painter.drawShape(state.selectedShape,
        state.shapeStart.x, state.shapeStart.y, x, y, state.color, state.size);
    } else {
      painter.apply(state.tool, state.prevX, state.prevY, x, y, state.color, state.size);
      if (state.symmetry) applySymmetry(state.prevX, state.prevY, x, y, state.tool, state.color, state.size);
      if (state.tool === 'brush' || state.tool === 'pen') {
        state.aiPoints.push({x, y}); state.aiActive = true;
      }
    }

    state.prevX = x; state.prevY = y;
    drawCursor(x, y, state.tool); return;
  }

  // ── Finger lifted ─────────────────────────────────────────────────
  if (state.drawing && state.tool==='shape' && state.selectedShape && state.shapeStart)
    painter.saveState();
  resetDrawState();
  setGestureBadge('Idle', false);
}

/* ── Helpers ─────────────────────────────────────────────────────────── */
function resetDrawState() {
  state.prevX=0; state.prevY=0; state.drawing=false;
  state.shapeStart=null; state.shapeSnap=null;
  state.aiPoints=[]; state.aiActive=false;
}

function setGestureBadge(text, hi) {
  const el = document.getElementById('gestureText');
  if (el) el.textContent = text;
  const badge = document.getElementById('gestureBadge');
  if (badge) badge.style.color = hi ? 'var(--a2)' : '';
}

function drawCursor(x, y, tool) {
  const ctx = lCtx, r = Math.max(8, state.size/2);
  ctx.save(); ctx.lineWidth = 2;
  if (tool==='eraser') {
    ctx.strokeStyle='rgba(200,200,200,.8)';
    ctx.beginPath(); ctx.arc(x,y,r,0,2*Math.PI); ctx.stroke();
  } else if (tool==='spray') {
    ctx.strokeStyle=state.color; ctx.setLineDash([3,4]);
    ctx.beginPath(); ctx.arc(x,y,r,0,2*Math.PI); ctx.stroke(); ctx.setLineDash([]);
  } else if (tool==='neon') {
    ctx.shadowBlur=10; ctx.shadowColor=state.color; ctx.strokeStyle=state.color;
    ctx.beginPath(); ctx.arc(x,y,r,0,2*Math.PI); ctx.stroke(); ctx.shadowBlur=0;
  } else if (tool==='text') {
    ctx.strokeStyle='rgba(244,114,182,.8)'; ctx.setLineDash([4,3]);
    ctx.beginPath(); ctx.arc(x,y,r,0,2*Math.PI); ctx.stroke(); ctx.setLineDash([]);
  } else if (tool==='eyedrop') {
    ctx.strokeStyle='rgba(129,140,248,.9)';
    ctx.beginPath(); ctx.arc(x,y,6,0,2*Math.PI); ctx.stroke();
  } else {
    ctx.strokeStyle='#fff'; ctx.beginPath(); ctx.arc(x,y,r,0,2*Math.PI); ctx.stroke();
    ctx.strokeStyle=state.color; ctx.beginPath(); ctx.arc(x,y,r,0,2*Math.PI); ctx.stroke();
  }
  ctx.fillStyle='#fff'; ctx.beginPath(); ctx.arc(x,y,2,0,2*Math.PI); ctx.fill();
  ctx.restore();
}

let _hintTimer=null;
function showHint(msg, ms=2000) {
  aiHint.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> ${msg}`;
  aiHint.classList.add('show');
  clearTimeout(_hintTimer);
  _hintTimer = setTimeout(()=>aiHint.classList.remove('show'), ms);
}

/* ── Keyboard shortcuts ──────────────────────────────────────────────── */
document.addEventListener('keydown', e => {
  if (e.target.tagName==='INPUT') return;
  switch(e.key.toLowerCase()) {
    case 'u': painter.undo(); break;
    case 'r': painter.redo(); break;
    case 's': painter.save(); break;
    case 'c': painter.clear(); break;
    case 'b': cycleBG(); break;
    case 'g': toggleGrid(); break;
    case 'escape': hideTextOverlay(); break;
    case '[':
      state.brushIdx = Math.max(0, state.brushIdx-1);
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

/* ── Boot ────────────────────────────────────────────────────────────── */
buildUI();
updateStatus();
const sbVoice = document.getElementById('sbVoice');
if (sbVoice) {
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    sbVoice.innerHTML = '<i class="fa-solid fa-microphone"></i> Voice ready';
    sbVoice.className = 'sb-voice on';
  } else {
    sbVoice.innerHTML = '<i class="fa-solid fa-microphone-slash"></i> No voice API';
    sbVoice.className = 'sb-voice off';
  }
}
