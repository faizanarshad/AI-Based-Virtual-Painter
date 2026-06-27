/**
 * Drawing engine — all tools + undo/redo + save.
 * Works directly on an HTML5 Canvas 2D context.
 */

class Painter {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx    = canvas.getContext('2d');
    this._undo  = [];   // array of ImageData
    this._redo  = [];
    this._rainbowT = 0;
  }

  // ── State helpers ────────────────────────────────────────────────────
  saveState() {
    this._undo.push(this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height));
    if (this._undo.length > 30) this._undo.shift();
    this._redo = [];
  }

  undo() {
    if (!this._undo.length) return;
    this._redo.push(this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height));
    this.ctx.putImageData(this._undo.pop(), 0, 0);
  }

  redo() {
    if (!this._redo.length) return;
    this._undo.push(this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height));
    this.ctx.putImageData(this._redo.pop(), 0, 0);
  }

  clear() { this.saveState(); this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height); }

  save() {
    const a = document.createElement('a');
    a.download = `painting_${Date.now()}.png`;
    a.href     = this.canvas.toDataURL('image/png');
    a.click();
  }

  // ── Tool dispatcher ──────────────────────────────────────────────────
  apply(tool, x0, y0, x1, y1, color, size) {
    const ctx = this.ctx;
    ctx.lineCap     = 'round';
    ctx.lineJoin    = 'round';

    switch (tool) {
      case 'brush':   this._brush(x0, y0, x1, y1, color, size);   break;
      case 'spray':   this._spray(x1, y1, color, size);            break;
      case 'rainbow': this._rainbow(x0, y0, x1, y1, size);         break;
      case 'neon':    this._neon(x0, y0, x1, y1, color, size);     break;
      case 'mirror':  this._mirror(x0, y0, x1, y1, color, size);   break;
      case 'eraser':  this._erase(x0, y0, x1, y1, size);           break;
    }
  }

  // ── Brush ────────────────────────────────────────────────────────────
  _brush(x0, y0, x1, y1, color, size) {
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = color;
    ctx.lineWidth   = size;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.stroke();
  }

  // ── Spray paint ──────────────────────────────────────────────────────
  _spray(cx, cy, color, size) {
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = color;
    const radius  = size + 12;
    const density = 45;
    for (let i = 0; i < density; i++) {
      const angle = Math.random() * 2 * Math.PI;
      const r     = Math.pow(Math.random(), 0.5) * radius;
      ctx.fillRect(Math.round(cx + r * Math.cos(angle)),
                   Math.round(cy + r * Math.sin(angle)), 2, 2);
    }
  }

  // ── Rainbow brush ────────────────────────────────────────────────────
  _rainbow(x0, y0, x1, y1, size) {
    this._rainbowT += 0.05;
    const hue = (this._rainbowT * 40) % 360;
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = `hsl(${hue},100%,60%)`;
    ctx.lineWidth   = size;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.stroke();
    // Return the current colour so the UI can track it
    return `hsl(${hue},100%,60%)`;
  }

  // ── Neon glow ────────────────────────────────────────────────────────
  _neon(x0, y0, x1, y1, color, size) {
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'screen';
    // Wide soft halo
    ctx.shadowBlur  = 24;
    ctx.shadowColor = color;
    ctx.strokeStyle = color;
    ctx.lineWidth   = size + 6;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.stroke();
    // Crisp core
    ctx.shadowBlur  = 6;
    ctx.lineWidth   = size;
    ctx.stroke();
    // White centre
    ctx.shadowBlur  = 2;
    ctx.strokeStyle = `rgba(255,255,255,.8)`;
    ctx.lineWidth   = Math.max(1, size / 2);
    ctx.stroke();
    // Reset
    ctx.shadowBlur  = 0;
    ctx.globalCompositeOperation = 'source-over';
  }

  // ── Mirror draw ──────────────────────────────────────────────────────
  _mirror(x0, y0, x1, y1, color, size) {
    const cw = this.canvas.width;
    this._brush(x0, y0, x1, y1, color, size);
    this._brush(cw - x0, y0, cw - x1, y1, color, size);
  }

  // ── Eraser ───────────────────────────────────────────────────────────
  _erase(x0, y0, x1, y1, size) {
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'destination-out';
    ctx.strokeStyle = 'rgba(0,0,0,1)';
    ctx.lineWidth   = size + 20;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.stroke();
    ctx.globalCompositeOperation = 'source-over';
  }

  // ── Shape drawing (drag-to-draw) ─────────────────────────────────────
  drawShape(type, x0, y0, x1, y1, color, size) {
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = color;
    ctx.lineWidth   = size;
    ctx.beginPath();

    if (type === 'Circle') {
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
      const r  = Math.hypot(x1 - x0, y1 - y0) / 2;
      ctx.arc(cx, cy, Math.max(1, r), 0, 2 * Math.PI);

    } else if (type === 'Rectangle') {
      ctx.rect(x0, y0, x1 - x0, y1 - y0);

    } else if (type === 'Triangle') {
      ctx.moveTo((x0 + x1) / 2, y0);
      ctx.lineTo(x1, y1);
      ctx.lineTo(x0, y1);
      ctx.closePath();

    } else if (type === 'Line') {
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y1);
    }
    ctx.stroke();
  }

  // ── AI shape snap ────────────────────────────────────────────────────
  completeShape(type, points, color, size) {
    if (!points.length) return;
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = color;
    ctx.lineWidth   = size;
    ctx.beginPath();

    if (type === 'circle') {
      const { cx, cy, r } = minEnclosingCircle(points);
      ctx.arc(cx, cy, Math.max(1, r), 0, 2 * Math.PI);

    } else if (type === 'rectangle') {
      const xs = points.map(p => p.x), ys = points.map(p => p.y);
      const x0 = Math.min(...xs), x1 = Math.max(...xs);
      const y0 = Math.min(...ys), y1 = Math.max(...ys);
      ctx.rect(x0, y0, x1 - x0, y1 - y0);

    } else if (type === 'triangle') {
      const hull    = convexHull(points);
      const peri    = hullPerimeter(hull);
      const approx  = rdpSimplify(hull, 0.07 * peri);
      if (approx.length >= 3) {
        ctx.moveTo(approx[0].x, approx[0].y);
        for (let i = 1; i < approx.length; i++) ctx.lineTo(approx[i].x, approx[i].y);
        ctx.closePath();
      }
    }
    ctx.stroke();
  }

  // ── Flood fill ───────────────────────────────────────────────────────
  fill(x, y, color) {
    const ctx = this.ctx;
    const cw  = this.canvas.width;
    const ch  = this.canvas.height;
    x = Math.round(x); y = Math.round(y);
    if (x < 0 || x >= cw || y < 0 || y >= ch) return;

    const imageData = ctx.getImageData(0, 0, cw, ch);
    const data      = imageData.data;
    const startIdx  = (y * cw + x) * 4;
    const tR = data[startIdx], tG = data[startIdx+1],
          tB = data[startIdx+2], tA = data[startIdx+3];

    // Parse fill colour
    const tmp = document.createElement('canvas');
    tmp.width = tmp.height = 1;
    const tc  = tmp.getContext('2d');
    tc.fillStyle = color; tc.fillRect(0,0,1,1);
    const fd = tc.getImageData(0,0,1,1).data;
    if (tR===fd[0]&&tG===fd[1]&&tB===fd[2]&&tA===fd[3]) return;

    const stack = [[x, y]];
    while (stack.length) {
      const [cx, cy] = stack.pop();
      if (cx<0||cx>=cw||cy<0||cy>=ch) continue;
      const i = (cy*cw+cx)*4;
      if (data[i]!==tR||data[i+1]!==tG||data[i+2]!==tB||data[i+3]!==tA) continue;
      data[i]=fd[0]; data[i+1]=fd[1]; data[i+2]=fd[2]; data[i+3]=fd[3];
      stack.push([cx+1,cy],[cx-1,cy],[cx,cy+1],[cx,cy-1]);
    }
    ctx.putImageData(imageData, 0, 0);
  }
}
