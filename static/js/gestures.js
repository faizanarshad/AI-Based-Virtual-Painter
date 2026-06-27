/**
 * Hand landmark gesture recognition helpers.
 * Mirrors the Python HandDetector logic in the browser.
 */

const TIP_IDS = [4, 8, 12, 16, 20];

/**
 * Returns [thumb, index, middle, ring, pinky] — 1 = up, 0 = down.
 * landmarks: array of {x,y,z} from MediaPipe (normalised 0-1).
 */
function fingersUp(landmarks) {
  const f = [];
  // Thumb: compare x positions (hand is mirrored with selfieMode)
  f.push(landmarks[TIP_IDS[0]].x < landmarks[TIP_IDS[0] - 1].x ? 1 : 0);
  // Four fingers: tip y < pip y  (lower y = higher on screen)
  for (let i = 1; i <= 4; i++) {
    f.push(landmarks[TIP_IDS[i]].y < landmarks[TIP_IDS[i] - 2].y ? 1 : 0);
  }
  return f;
}

/**
 * Returns 'draw' | 'select' | 'snap' | null
 */
function classifyGesture(f) {
  if (f[1] && f[2] && f[3]) return 'snap';      // 3+ fingers → AI snap
  if (f[1] && f[2] && !f[3]) return 'select';   // 2 fingers  → select
  if (f[1] && !f[2])         return 'draw';      // 1 finger   → draw
  return null;
}

/**
 * Convert normalised landmark to canvas pixel coords.
 * Video is CSS-flipped (scaleX(-1)), so x uses landmark.x directly.
 */
function landmarkToCanvas(lm, cw, ch) {
  return { x: Math.round(lm.x * cw), y: Math.round(lm.y * ch) };
}
