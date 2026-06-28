/**
 * AI Shape Detector + confidence scorer.
 * Exports: detectShape(points), plus geometry helpers used by drawing.js.
 */

/* ── Convex Hull (Gift Wrapping) ──────────────────────────────────── */
function convexHull(pts) {
  if (pts.length < 3) return pts.slice();
  // Deduplicate
  const unique = [];
  const seen   = new Set();
  for (const p of pts) {
    const k = `${Math.round(p.x)},${Math.round(p.y)}`;
    if (!seen.has(k)) { seen.add(k); unique.push(p); }
  }
  if (unique.length < 3) return unique;

  // Leftmost point
  let start = unique.reduce((m, p) => p.x < m.x ? p : m, unique[0]);
  const hull = [];
  let cur    = start;

  do {
    hull.push(cur);
    let next = unique[0];
    for (const p of unique) {
      if (p === cur) continue;
      const cross = (next.x-cur.x)*(p.y-cur.y) - (next.y-cur.y)*(p.x-cur.x);
      if (next === cur || cross < 0 ||
          (cross === 0 && Math.hypot(p.x-cur.x,p.y-cur.y) > Math.hypot(next.x-cur.x,next.y-cur.y))) {
        next = p;
      }
    }
    cur = next;
  } while (cur !== start && hull.length <= unique.length);

  return hull;
}

/* ── Hull geometry ──────────────────────────────────────────────────── */
function hullPerimeter(hull) {
  let p = 0;
  for (let i = 0; i < hull.length; i++) {
    const a = hull[i], b = hull[(i+1)%hull.length];
    p += Math.hypot(b.x-a.x, b.y-a.y);
  }
  return p;
}

function hullArea(hull) {
  let a = 0;
  for (let i = 0; i < hull.length; i++) {
    const p = hull[i], q = hull[(i+1)%hull.length];
    a += p.x*q.y - q.x*p.y;
  }
  return Math.abs(a) / 2;
}

/* ── Ramer-Douglas-Peucker simplification ───────────────────────────── */
function rdpSimplify(pts, eps) {
  if (pts.length <= 2) return pts.slice();
  const first = pts[0], last = pts[pts.length-1];
  let maxD = 0, maxI = 0;
  for (let i = 1; i < pts.length-1; i++) {
    const d = _ptLineDist(pts[i], first, last);
    if (d > maxD) { maxD = d; maxI = i; }
  }
  if (maxD > eps) {
    const l = rdpSimplify(pts.slice(0, maxI+1), eps);
    const r = rdpSimplify(pts.slice(maxI),      eps);
    return [...l.slice(0,-1), ...r];
  }
  return [first, last];
}
function _ptLineDist(p, a, b) {
  const dx = b.x-a.x, dy = b.y-a.y;
  if (!dx && !dy) return Math.hypot(p.x-a.x, p.y-a.y);
  const t  = ((p.x-a.x)*dx+(p.y-a.y)*dy)/(dx*dx+dy*dy);
  return Math.hypot(p.x-(a.x+t*dx), p.y-(a.y+t*dy));
}

/* ── Min-enclosing circle (Welzl / naive) ───────────────────────────── */
function minEnclosingCircle(pts) {
  let cx = pts.reduce((s,p)=>s+p.x,0)/pts.length;
  let cy = pts.reduce((s,p)=>s+p.y,0)/pts.length;
  let r  = pts.reduce((m,p)=>Math.max(m,Math.hypot(p.x-cx,p.y-cy)),0);
  // One refinement pass
  for (let iter = 0; iter < 20; iter++) {
    let furthest = null, fd = 0;
    for (const p of pts) {
      const d = Math.hypot(p.x-cx, p.y-cy);
      if (d > fd) { fd = d; furthest = p; }
    }
    if (fd <= r * 1.001) break;
    cx += (furthest.x - cx) * 0.1;
    cy += (furthest.y - cy) * 0.1;
    r   = pts.reduce((m,p)=>Math.max(m,Math.hypot(p.x-cx,p.y-cy)),0);
  }
  return { cx, cy, r };
}

/* ── Shape detector ─────────────────────────────────────────────────── */
/**
 * Returns 'circle' | 'rectangle' | 'triangle' | null.
 * Same algorithm as Python ShapeDetector.detect():
 *   1. approxPolyDP on convex hull → 3 verts → triangle, 4 → rectangle
 *   2. min-enclosing-circle deviation test → circle
 */
function detectShape(points, minSize = 30) {
  if (points.length < 10) return null;

  const xs = points.map(p=>p.x), ys = points.map(p=>p.y);
  const bw = Math.max(...xs)-Math.min(...xs);
  const bh = Math.max(...ys)-Math.min(...ys);
  if (bw < minSize && bh < minSize) return null;

  const hull = convexHull(points);
  const peri = hullPerimeter(hull);
  if (peri === 0) return null;

  // Polygon test at tight epsilon
  const approx = rdpSimplify(hull, 0.04 * peri);
  const n = approx.length;

  if (n === 3) return 'triangle';
  if (n === 4) {
    const axs = approx.map(p=>p.x), ays = approx.map(p=>p.y);
    const aw = Math.max(...axs)-Math.min(...axs);
    const ah = Math.max(...ays)-Math.min(...ays);
    if (aw > minSize && ah > minSize) return 'rectangle';
  }

  // Circle fallback (5+ verts)
  if (n >= 5) {
    const { cx, cy, r } = minEnclosingCircle(points);
    if (r > minSize) {
      const devs = points.map(p => Math.abs(Math.hypot(p.x-cx,p.y-cy)-r));
      const avg  = devs.reduce((s,d)=>s+d,0)/devs.length;
      if (avg/r < 0.25) return 'circle';
    }
  }

  return null;
}

/* ── Confidence scorer ───────────────────────────────────────────────── */
/**
 * Returns a 0–1 score for how well the points match the detected shape.
 */
function calculateConfidence(shape, points) {
  if (!shape || points.length < 6) return 0;

  if (shape === 'circle') {
    const { cx, cy, r } = minEnclosingCircle(points);
    if (r === 0) return 0;
    const devs  = points.map(p => Math.abs(Math.hypot(p.x - cx, p.y - cy) - r));
    const avg   = devs.reduce((s, d) => s + d, 0) / devs.length;
    const maxDev = Math.max(...devs);
    const score = 1 - (avg * 0.7 + maxDev * 0.3) / (r * 0.25);
    return Math.max(0, Math.min(1, score));
  }

  if (shape === 'rectangle') {
    const hull   = convexHull(points);
    const peri   = hullPerimeter(hull);
    if (!peri) return 0;
    const approx = rdpSimplify(hull, 0.04 * peri);
    const n      = approx.length;
    // 4 corners is perfect; penalise deviation
    const cornerScore = Math.max(0, 1 - Math.abs(n - 4) * 0.2);
    // Also check bounding-box fill ratio (tighter = more rectangular)
    const area  = hullArea(hull);
    const xs    = approx.map(p => p.x), ys = approx.map(p => p.y);
    const bbox  = (Math.max(...xs) - Math.min(...xs)) * (Math.max(...ys) - Math.min(...ys));
    const fill  = bbox > 0 ? Math.min(1, area / bbox) : 0;
    return Math.max(0, Math.min(1, cornerScore * 0.5 + fill * 0.5));
  }

  if (shape === 'triangle') {
    const hull   = convexHull(points);
    const peri   = hullPerimeter(hull);
    if (!peri) return 0;
    const approx = rdpSimplify(hull, 0.04 * peri);
    const n      = approx.length;
    const score  = Math.max(0, 1 - Math.abs(n - 3) * 0.25);
    return Math.min(0.98, score + 0.1);
  }

  return 0;
}

/* ── Live preview helper ─────────────────────────────────────────────── */
/**
 * Draws a translucent preview of the detected shape on a canvas 2D context.
 * Used by the Shape Detect tool to give real-time feedback.
 */
function drawDetectionPreview(ctx, shape, points, color = '#22d3ee') {
  if (!shape || !points.length) return;
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth   = 2.5;
  ctx.setLineDash([7, 5]);
  ctx.shadowBlur  = 14;
  ctx.shadowColor = color;
  ctx.globalAlpha = 0.85;
  ctx.beginPath();

  if (shape === 'circle') {
    const { cx, cy, r } = minEnclosingCircle(points);
    ctx.arc(cx, cy, Math.max(1, r), 0, 2 * Math.PI);

  } else if (shape === 'rectangle') {
    const xs = points.map(p => p.x), ys = points.map(p => p.y);
    ctx.rect(Math.min(...xs), Math.min(...ys),
             Math.max(...xs) - Math.min(...xs),
             Math.max(...ys) - Math.min(...ys));

  } else if (shape === 'triangle') {
    const hull   = convexHull(points);
    const peri   = hullPerimeter(hull);
    const approx = rdpSimplify(hull, 0.07 * peri);
    if (approx.length >= 3) {
      ctx.moveTo(approx[0].x, approx[0].y);
      for (let i = 1; i < approx.length; i++) ctx.lineTo(approx[i].x, approx[i].y);
      ctx.closePath();
    }
  }

  ctx.stroke();
  ctx.setLineDash([]);
  ctx.shadowBlur  = 0;
  ctx.globalAlpha = 1;
  ctx.restore();
}
