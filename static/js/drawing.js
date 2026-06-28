/**
 * Drawing engine — all tools, shapes, undo/redo, save.
 */

class Painter {
  constructor(canvas) {
    this.canvas   = canvas;
    this.ctx      = canvas.getContext('2d');
    this._undo    = [];
    this._redo    = [];
    this._rainbowT = 0;
    this.opacity  = 1.0;   // 0.1 – 1.0, set by app
  }

  /* ── History ─────────────────────────────────────────────────────── */
  saveState() {
    this._undo.push(this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height));
    if (this._undo.length > 35) this._undo.shift();
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
  clear() {
    this.saveState();
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }
  save() {
    // Merge bg + drawing onto a temp canvas then download
    const tmp = document.createElement('canvas');
    tmp.width  = this.canvas.width;
    tmp.height = this.canvas.height;
    const tCtx = tmp.getContext('2d');
    const bg   = document.getElementById('bgCanvas');
    if (bg) tCtx.drawImage(bg, 0, 0);
    tCtx.drawImage(this.canvas, 0, 0);
    const a = document.createElement('a');
    a.download = `painting_${Date.now()}.png`;
    a.href     = tmp.toDataURL('image/png');
    a.click();
  }

  /* ── Tool dispatcher ────────────────────────────────────────────── */
  apply(tool, x0, y0, x1, y1, color, size) {
    const ctx = this.ctx;
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    switch (tool) {
      case 'brush':      this._brush     (x0, y0, x1, y1, color, size); break;
      case 'spray':      this._spray     (x1, y1, color, size);          break;
      case 'rainbow':    this._rainbow   (x0, y0, x1, y1, size);         break;
      case 'neon':       this._neon      (x0, y0, x1, y1, color, size); break;
      case 'mirror':     this._mirror    (x0, y0, x1, y1, color, size); break;
      case 'eraser':     this._erase     (x0, y0, x1, y1, size);         break;
      case 'glitter':    this._glitter   (x1, y1, color, size);          break;
      case 'watercolor': this._watercolor(x0, y0, x1, y1, color, size); break;
      case 'pen':        this._pen       (x0, y0, x1, y1, color);        break;
      case 'pixel':      this._pixel     (x1, y1, color, size);          break;
      case 'ink':        this._ink       (x0, y0, x1, y1, color, size); break;
    }
  }

  /* ── Brush ──────────────────────────────────────────────────────── */
  _brush(x0, y0, x1, y1, color, size) {
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha  = this.opacity;
    ctx.strokeStyle  = color;
    ctx.lineWidth    = size;
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
    ctx.globalAlpha  = 1;
  }

  /* ── Spray ──────────────────────────────────────────────────────── */
  _spray(cx, cy, color, size) {
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = this.opacity;
    ctx.fillStyle   = color;
    const radius = size + 12, density = 50;
    for (let i = 0; i < density; i++) {
      const a = Math.random() * 2 * Math.PI;
      const r = Math.pow(Math.random(), 0.5) * radius;
      ctx.fillRect(Math.round(cx + r * Math.cos(a)),
                   Math.round(cy + r * Math.sin(a)), 2, 2);
    }
    ctx.globalAlpha = 1;
  }

  /* ── Rainbow ────────────────────────────────────────────────────── */
  _rainbow(x0, y0, x1, y1, size) {
    this._rainbowT += 0.05;
    const hue = (this._rainbowT * 45) % 360;
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha  = this.opacity;
    ctx.strokeStyle  = `hsl(${hue},100%,60%)`;
    ctx.lineWidth    = size;
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
    ctx.globalAlpha  = 1;
    return `hsl(${hue},100%,60%)`;
  }

  /* ── Neon glow ──────────────────────────────────────────────────── */
  _neon(x0, y0, x1, y1, color, size) {
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'screen';
    ctx.shadowBlur = 24; ctx.shadowColor = color;
    ctx.strokeStyle = color; ctx.lineWidth = size + 6;
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
    ctx.shadowBlur = 6; ctx.lineWidth = size; ctx.stroke();
    ctx.shadowBlur = 2; ctx.strokeStyle = 'rgba(255,255,255,.8)';
    ctx.lineWidth = Math.max(1, size / 2); ctx.stroke();
    ctx.shadowBlur = 0;
    ctx.globalCompositeOperation = 'source-over';
  }

  /* ── Mirror ─────────────────────────────────────────────────────── */
  _mirror(x0, y0, x1, y1, color, size) {
    const cw = this.canvas.width;
    this._brush(x0, y0, x1, y1, color, size);
    this._brush(cw-x0, y0, cw-x1, y1, color, size);
  }

  /* ── Eraser ─────────────────────────────────────────────────────── */
  _erase(x0, y0, x1, y1, size) {
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'destination-out';
    ctx.strokeStyle = 'rgba(0,0,0,1)';
    ctx.lineWidth   = size + 20;
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
    ctx.globalCompositeOperation = 'source-over';
  }

  /* ── Glitter ────────────────────────────────────────────────────── */
  _glitter(cx, cy, color, size) {
    const ctx = this.ctx;
    const count = 22, radius = size + 18;
    ctx.globalCompositeOperation = 'source-over';
    for (let i = 0; i < count; i++) {
      const a = Math.random() * 2 * Math.PI;
      const r = Math.pow(Math.random(), 0.5) * radius;
      const x = cx + r * Math.cos(a), y = cy + r * Math.sin(a);
      const s = Math.random() * 3.5 + 1;
      ctx.globalAlpha = Math.random() * 0.7 + 0.3;
      ctx.fillStyle = Math.random() > 0.5 ? color : '#ffffff';
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(Math.random() * Math.PI);
      // 4-pointed star
      ctx.beginPath();
      for (let j = 0; j < 8; j++) {
        const ang = j * Math.PI / 4;
        const rr  = j % 2 === 0 ? s : s * 0.35;
        j === 0 ? ctx.moveTo(rr*Math.cos(ang), rr*Math.sin(ang))
                : ctx.lineTo(rr*Math.cos(ang), rr*Math.sin(ang));
      }
      ctx.closePath(); ctx.fill();
      ctx.restore();
    }
    ctx.globalAlpha = 1;
  }

  /* ── Watercolor ─────────────────────────────────────────────────── */
  _watercolor(x0, y0, x1, y1, color, size) {
    const ctx = this.ctx;
    const passes = 7;
    for (let i = 0; i < passes; i++) {
      const j  = size * 0.55;
      const nx0 = x0 + (Math.random()-.5)*j*2, ny0 = y0 + (Math.random()-.5)*j*2;
      const nx1 = x1 + (Math.random()-.5)*j*2, ny1 = y1 + (Math.random()-.5)*j*2;
      ctx.globalAlpha = (0.018 + Math.random() * 0.015) * this.opacity;
      ctx.strokeStyle = color;
      ctx.lineWidth   = size * (0.7 + Math.random() * 0.6);
      ctx.lineCap = 'round';
      ctx.globalCompositeOperation = 'source-over';
      ctx.beginPath(); ctx.moveTo(nx0, ny0); ctx.lineTo(nx1, ny1); ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  /* ── Pen (thin calligraphy) ─────────────────────────────────────── */
  _pen(x0, y0, x1, y1, color) {
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha  = this.opacity;
    ctx.strokeStyle  = color;
    ctx.lineWidth    = 1.5;
    ctx.lineCap      = 'round';
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
    ctx.globalAlpha  = 1;
  }

  /* ── Pixel art ──────────────────────────────────────────────────── */
  _pixel(x, y, color, size) {
    const ctx = this.ctx;
    const g   = Math.max(4, Math.round(size * 0.9));
    const gx  = Math.floor(x/g)*g, gy = Math.floor(y/g)*g;
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = this.opacity;
    ctx.fillStyle   = color;
    ctx.fillRect(gx, gy, g, g);
    ctx.globalAlpha = 1;
  }

  /* ── Ink (speed-sensitive width) ────────────────────────────────── */
  _ink(x0, y0, x1, y1, color, size) {
    const speed = Math.hypot(x1-x0, y1-y0);
    const w     = Math.max(0.5, size - speed * 0.12);
    const ctx   = this.ctx;
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = this.opacity;
    ctx.strokeStyle = color;
    ctx.lineWidth   = w;
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
    ctx.globalAlpha = 1;
  }

  /* ── Flood fill ─────────────────────────────────────────────────── */
  fill(x, y, color) {
    const ctx = this.ctx, cw = this.canvas.width, ch = this.canvas.height;
    x = Math.round(x); y = Math.round(y);
    if (x < 0 || x >= cw || y < 0 || y >= ch) return;
    const img   = ctx.getImageData(0, 0, cw, ch);
    const data  = img.data;
    const i0    = (y*cw+x)*4;
    const tR=data[i0],tG=data[i0+1],tB=data[i0+2],tA=data[i0+3];
    const tmp=document.createElement('canvas'); tmp.width=tmp.height=1;
    const tc=tmp.getContext('2d'); tc.fillStyle=color; tc.fillRect(0,0,1,1);
    const fd=tc.getImageData(0,0,1,1).data;
    if(tR===fd[0]&&tG===fd[1]&&tB===fd[2]&&tA===fd[3]) return;
    const stack=[[x,y]];
    while(stack.length){
      const[cx,cy]=stack.pop();
      if(cx<0||cx>=cw||cy<0||cy>=ch) continue;
      const i=(cy*cw+cx)*4;
      if(data[i]!==tR||data[i+1]!==tG||data[i+2]!==tB||data[i+3]!==tA) continue;
      data[i]=fd[0];data[i+1]=fd[1];data[i+2]=fd[2];data[i+3]=fd[3];
      stack.push([cx+1,cy],[cx-1,cy],[cx,cy+1],[cx,cy-1]);
    }
    ctx.putImageData(img,0,0);
  }

  /* ── Eyedropper ─────────────────────────────────────────────────── */
  eyedrop(x, y) {
    const p = this.ctx.getImageData(Math.round(x), Math.round(y), 1, 1).data;
    if (p[3] === 0) return null;
    return `#${[p[0],p[1],p[2]].map(v=>v.toString(16).padStart(2,'0')).join('')}`;
  }

  /* ── Text ───────────────────────────────────────────────────────── */
  drawText(text, x, y, color, size) {
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = this.opacity;
    ctx.fillStyle   = color;
    ctx.font        = `bold ${Math.max(12, size*2.5)}px 'Segoe UI', sans-serif`;
    ctx.fillText(text, x, y);
    ctx.globalAlpha = 1;
  }

  /* ── Shapes ─────────────────────────────────────────────────────── */
  drawShape(type, x0, y0, x1, y1, color, size) {
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = this.opacity;
    ctx.strokeStyle = color; ctx.lineWidth = size;
    ctx.beginPath();
    _shapeGeometry(ctx, type, x0, y0, x1, y1);
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  completeShape(type, points, color, size) {
    if (!points.length) return;
    const ctx = this.ctx;
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = color; ctx.lineWidth = size;
    ctx.beginPath();

    if (type === 'circle') {
      const { cx, cy, r } = minEnclosingCircle(points);
      ctx.arc(cx, cy, Math.max(1,r), 0, 2*Math.PI);
    } else if (type === 'rectangle') {
      const xs=points.map(p=>p.x),ys=points.map(p=>p.y);
      ctx.rect(Math.min(...xs),Math.min(...ys),
               Math.max(...xs)-Math.min(...xs), Math.max(...ys)-Math.min(...ys));
    } else if (type === 'triangle') {
      const hull=convexHull(points), peri=hullPerimeter(hull);
      const app=rdpSimplify(hull,0.07*peri);
      if (app.length>=3){
        ctx.moveTo(app[0].x,app[0].y);
        for(let i=1;i<app.length;i++) ctx.lineTo(app[i].x,app[i].y);
        ctx.closePath();
      }
    }
    ctx.stroke();
  }
}

/* ── Shared geometry helper ──────────────────────────────────────────── */
function _shapeGeometry(ctx, type, x0, y0, x1, y1) {
  const cx=(x0+x1)/2, cy=(y0+y1)/2;
  const w=Math.abs(x1-x0), h=Math.abs(y1-y0);
  const r=Math.hypot(x1-x0,y1-y0)/2;

  switch(type) {
    case 'Circle':
      ctx.arc(cx,cy,Math.max(1,r),0,2*Math.PI); break;

    case 'Rectangle':
      ctx.rect(x0,y0,x1-x0,y1-y0); break;

    case 'Triangle':
      ctx.moveTo(cx,y0); ctx.lineTo(x1,y1); ctx.lineTo(x0,y1); ctx.closePath(); break;

    case 'Line':
      ctx.moveTo(x0,y0); ctx.lineTo(x1,y1); break;

    case 'Star': {
      const outer=r, inner=r*0.4, pts=5;
      for(let i=0;i<pts*2;i++){
        const rr=i%2===0?outer:inner;
        const a=(i*Math.PI/pts)-Math.PI/2;
        i===0?ctx.moveTo(cx+rr*Math.cos(a),cy+rr*Math.sin(a))
             :ctx.lineTo(cx+rr*Math.cos(a),cy+rr*Math.sin(a));
      }
      ctx.closePath(); break;
    }

    case 'Heart':
      ctx.moveTo(cx, cy+h*0.35);
      ctx.bezierCurveTo(cx-w*0.5,cy+h*0.1, cx-w*0.5,cy-h*0.45, cx,cy-h*0.15);
      ctx.bezierCurveTo(cx+w*0.5,cy-h*0.45, cx+w*0.5,cy+h*0.1, cx,cy+h*0.35);
      break;

    case 'Diamond':
      ctx.moveTo(cx,y0); ctx.lineTo(x1,cy);
      ctx.lineTo(cx,y1); ctx.lineTo(x0,cy); ctx.closePath(); break;

    case 'Pentagon':
      _ngon(ctx,cx,cy,r,5); break;

    case 'Hexagon':
      _ngon(ctx,cx,cy,r,6); break;

    case 'Arrow': {
      const angle=Math.atan2(y1-y0,x1-x0);
      const hl=Math.min(r*0.5,45);
      ctx.moveTo(x0,y0); ctx.lineTo(x1,y1);
      ctx.lineTo(x1-hl*Math.cos(angle-Math.PI/6), y1-hl*Math.sin(angle-Math.PI/6));
      ctx.moveTo(x1,y1);
      ctx.lineTo(x1-hl*Math.cos(angle+Math.PI/6), y1-hl*Math.sin(angle+Math.PI/6));
      break;
    }
  }
}

function _ngon(ctx, cx, cy, r, n) {
  for(let i=0;i<n;i++){
    const a=(i*2*Math.PI/n)-Math.PI/2;
    i===0?ctx.moveTo(cx+r*Math.cos(a),cy+r*Math.sin(a))
         :ctx.lineTo(cx+r*Math.cos(a),cy+r*Math.sin(a));
  }
  ctx.closePath();
}
