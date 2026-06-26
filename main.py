"""
Virtual Painter — entry point.

Usage:
    python main.py          # normal mode (requires webcam)
    python main.py --demo   # demo mode (no webcam needed)
"""

import argparse
import os
import time

import cv2
import numpy as np

from src import (
    HandDetector, ShapeDetector, VOICE_AVAILABLE,
    create_gradient, draw_button, draw_shape,
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


# ── Gesture constants ─────────────────────────────────────────────────────────
TOOL_BRUSH  = "brush"
TOOL_ERASER = "eraser"
TOOL_FILL   = "fill"
TOOL_SHAPE  = "shape"

# ── Palette ───────────────────────────────────────────────────────────────────
COLORS = [
    (0,   0,   255),   # Red
    (0,   255,   0),   # Green
    (255,   0,   0),   # Blue
    (0,   255, 255),   # Yellow
    (255,   0, 255),   # Magenta
    (255, 255,   0),   # Cyan
    (255, 255, 255),   # White
    (0,   165, 255),   # Orange
    (128,   0, 128),   # Purple
    (0,   255, 128),   # Lime
]

# ── Layout constants ──────────────────────────────────────────────────────────
W, H        = 1280, 720
HDR_H       = 100

COLOR_X0    = 50
COLOR_Y     = 20
COLOR_SZ    = 50
COLOR_GAP   = 15

BTN_W, BTN_H  = 120, 50
BTN_GAP       = 15
BTN_X         = W - BTN_W - 20   # right edge

SHP_W, SHP_H  = 120, 50
SHP_GAP       = 15
SHP_X         = 20               # left edge

TOOL_BUTTONS = [
    ("Brush",  TOOL_BRUSH,  (0,   255, 100)),
    ("Eraser", TOOL_ERASER, (255, 100, 100)),
    ("Fill",   TOOL_FILL,   (0,   200, 255)),
    ("Clear",  None,        (255, 150,   0)),
    ("Save",   None,        (0,   200, 100)),
]

SHAPE_BUTTONS = [
    ("Circle",    (255, 100, 100)),
    ("Rectangle", (100, 255, 100)),
    ("Triangle",  (100, 100, 255)),
    ("Line",      (255, 255, 100)),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _flood_fill(canvas, sx, sy, replacement):
    target = canvas[sy, sx].copy()
    if np.array_equal(target, replacement):
        return
    ch, cw = canvas.shape[:2]
    stack = [(sx, sy)]
    while stack:
        x, y = stack.pop()
        if x < 0 or x >= cw or y < 0 or y >= ch:
            continue
        if np.array_equal(canvas[y, x], target):
            canvas[y, x] = replacement
            stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]


def _save(canvas):
    ts = int(time.time())
    path = os.path.join(OUTPUT_DIR, f"painting_{ts}.png")
    cv2.imwrite(path, canvas)
    print(f"[Save] {path}")


# ── Main application ──────────────────────────────────────────────────────────

def run(demo_mode=False):
    # Camera
    cap = None
    if not demo_mode:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  W)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
        else:
            print("[Camera] Not available — switching to demo mode")
            cap = None

    detector       = HandDetector(detectionCon=0.85)
    shape_detector = ShapeDetector()

    # Voice
    voice = None
    last_voice_t  = 0.0
    VOICE_COOLDOWN = 2.0
    if VOICE_AVAILABLE:
        from src.voice_controller import VoiceController
        try:
            voice = VoiceController()
            voice.start_listening()
            print("[Voice] Active")
        except Exception as e:
            print(f"[Voice] Unavailable: {e}")

    # Canvas & drawing state
    canvas     = np.zeros((H, W, 3), np.uint8)
    xp, yp     = 0, 0
    draw_color = (255, 0, 255)

    brush_sizes  = [5, 10, 15, 20, 25, 30]
    eraser_sizes = [20, 30, 40, 50, 60, 70]
    brush_idx    = 2
    eraser_idx   = 3
    brush_thick  = brush_sizes[brush_idx]
    eraser_thick = eraser_sizes[eraser_idx]

    from collections import deque
    undo_stack = deque(maxlen=20)
    redo_stack = deque(maxlen=20)

    def save_state():
        undo_stack.append(canvas.copy())
        redo_stack.clear()

    def undo():
        if undo_stack:
            redo_stack.append(canvas.copy())
            canvas[:] = undo_stack.pop()

    def redo():
        if redo_stack:
            undo_stack.append(canvas.copy())
            canvas[:] = redo_stack.pop()

    save_state()

    current_tool   = TOOL_BRUSH
    shape_mode     = False
    selected_shape = None
    shape_start    = None

    ai_points      = []
    ai_active      = False

    # ── Loop ─────────────────────────────────────────────────────────────────
    while True:
        # Frame
        if cap is not None:
            ok, img = cap.read()
            if not ok:
                img = create_gradient(W, H, (50, 50, 100), (100, 50, 150), "vertical")
        else:
            img = create_gradient(W, H, (40, 40, 80), (80, 40, 120), "vertical")
            cv2.putText(img, "DEMO MODE  —  no camera", (W // 2 - 230, H // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 200), 2)

        img = cv2.flip(img, 1)

        # ── Voice ─────────────────────────────────────────────────────────
        if voice:
            cmd = voice.get_command()
            now = time.time()
            if cmd and (now - last_voice_t) >= VOICE_COOLDOWN:
                last_voice_t = now
                if   "brush"  in cmd: current_tool = TOOL_BRUSH;  shape_mode = False
                elif "eraser" in cmd: current_tool = TOOL_ERASER; shape_mode = False
                elif "fill"   in cmd: current_tool = TOOL_FILL;   shape_mode = False
                elif "clear"  in cmd: save_state(); canvas[:] = 0
                elif "save"   in cmd: _save(canvas)
                elif "undo"   in cmd: undo()
                elif "redo"   in cmd: redo()
                elif "red"    in cmd: draw_color = (0,   0,   255)
                elif "green"  in cmd: draw_color = (0,   255,   0)
                elif "blue"   in cmd: draw_color = (255,   0,   0)
                elif "yellow" in cmd: draw_color = (0,   255, 255)
                elif "purple" in cmd: draw_color = (128,   0, 128)
                elif "white"  in cmd: draw_color = (255, 255, 255)

        # ── Hand tracking ─────────────────────────────────────────────────
        if cap is not None:
            img = detector.findHands(img)
            lms = detector.findPosition(img, draw=False)

            if lms:
                x1, y1 = lms[8][1],  lms[8][2]   # index tip
                fingers = detector.fingersUp()

                # 3-finger AI snap (index + middle + ring)
                if fingers[1] and fingers[2] and fingers[3] and not fingers[4]:
                    xp, yp = 0, 0
                    if ai_active and len(ai_points) > 4:
                        kind = shape_detector.detect(ai_points)
                        if kind:
                            save_state()
                            shape_detector.complete(kind, ai_points, canvas, draw_color, brush_thick)
                            print(f"[AI] snapped to {kind}")
                    ai_points.clear()
                    ai_active = False

                # Selection mode (index + middle, ring down)
                elif fingers[1] and fingers[2] and not fingers[3]:
                    xp, yp = 0, 0
                    shape_start = None
                    ai_points.clear()
                    ai_active = False

                    # Color palette
                    if y1 < HDR_H:
                        for i, c in enumerate(COLORS):
                            cx0 = COLOR_X0 + i * (COLOR_SZ + COLOR_GAP)
                            if cx0 < x1 < cx0 + COLOR_SZ and COLOR_Y < y1 < COLOR_Y + COLOR_SZ:
                                draw_color   = c
                                current_tool = TOOL_BRUSH
                                shape_mode   = False

                    # Right-side tool buttons
                    if x1 > BTN_X:
                        idx = (y1 - HDR_H - 20) // (BTN_H + BTN_GAP)
                        if 0 <= idx < len(TOOL_BUTTONS):
                            label, tool, _ = TOOL_BUTTONS[idx]
                            if label == "Clear":
                                save_state(); canvas[:] = 0
                            elif label == "Save":
                                _save(canvas)
                            else:
                                current_tool = tool
                                shape_mode   = False

                    # Left-side shape buttons
                    if x1 < SHP_X + SHP_W:
                        idx = (y1 - HDR_H - 20) // (SHP_H + SHP_GAP)
                        if 0 <= idx < len(SHAPE_BUTTONS):
                            selected_shape = SHAPE_BUTTONS[idx][0]
                            shape_mode     = True
                            current_tool   = TOOL_SHAPE

                    cv2.circle(img, (x1, y1), 15, draw_color, cv2.FILLED)

                # Draw mode (only index finger)
                elif fingers[1] and not fingers[2]:
                    cv2.circle(img, (x1, y1), 15, draw_color, cv2.FILLED)

                    if xp == 0 and yp == 0:
                        xp, yp = x1, y1
                        if shape_mode:
                            shape_start = (x1, y1)

                    if current_tool == TOOL_BRUSH:
                        cv2.line(canvas, (xp, yp), (x1, y1), draw_color, brush_thick)
                        ai_points.append((x1, y1))
                        ai_active = True

                    elif current_tool == TOOL_ERASER:
                        mask = np.zeros(canvas.shape[:2], np.uint8)
                        cv2.line(mask, (xp, yp), (x1, y1), 255, eraser_thick)
                        canvas[mask == 255] = 0
                        ai_points.clear(); ai_active = False

                    elif current_tool == TOOL_FILL:
                        save_state()
                        _flood_fill(canvas, x1, y1, list(draw_color))
                        ai_points.clear(); ai_active = False

                    elif current_tool == TOOL_SHAPE and shape_mode and selected_shape and shape_start:
                        tmp = canvas.copy()
                        draw_shape(tmp, selected_shape, shape_start, (x1, y1), draw_color, 3)
                        canvas[:] = tmp

                    xp, yp = x1, y1

                # Finger lifted — commit drag-to-draw shape
                elif not fingers[1] and shape_mode and selected_shape and shape_start:
                    save_state()
                    shape_start = None
                    xp, yp = 0, 0

                else:
                    xp, yp = 0, 0
                    ai_points.clear(); ai_active = False

        # ── Header ────────────────────────────────────────────────────────
        header = create_gradient(W, HDR_H, (80, 40, 120), (120, 60, 180), "horizontal")

        # Color swatches
        for i, c in enumerate(COLORS):
            cx0 = COLOR_X0 + i * (COLOR_SZ + COLOR_GAP)
            swatch = create_gradient(COLOR_SZ, COLOR_SZ,
                                     tuple(max(0, v - 30) for v in c), c, "vertical")
            header[COLOR_Y:COLOR_Y + COLOR_SZ, cx0:cx0 + COLOR_SZ] = swatch
            bw = 3 if c == draw_color else 2
            col = (255, 255, 255) if c != draw_color else tuple(min(255, v + 80) for v in c)
            cv2.rectangle(header, (cx0, COLOR_Y), (cx0 + COLOR_SZ, COLOR_Y + COLOR_SZ), col, bw)

        # Title
        title = "Virtual Painter"
        tw = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.4, 3)[0][0]
        tx = (W - tw) // 2
        ty = HDR_H // 2 + 10
        cv2.putText(header, title, (tx + 2, ty + 2), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 3)
        cv2.putText(header, title, (tx, ty),         cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 220, 50), 3)

        # Animated sparkles
        t = time.time()
        for i in range(6):
            px = int(30 + (t * 60 + i * 120) % (W - 60))
            py = int(10 + 8 * np.sin(t * 2 + i))
            cv2.circle(header, (px, py), 2, (255, 255, 255), -1)

        img[0:HDR_H, 0:W] = header

        # ── Right-side tool buttons ────────────────────────────────────────
        y0 = HDR_H + 20
        for i, (label, tool, color) in enumerate(TOOL_BUTTONS):
            by = y0 + i * (BTN_H + BTN_GAP)
            active = (tool is not None and current_tool == tool and not shape_mode)
            draw_button(img, BTN_X, by, BTN_W, BTN_H, label, color, active)

        # ── Left-side shape buttons ────────────────────────────────────────
        for i, (label, color) in enumerate(SHAPE_BUTTONS):
            sy_ = y0 + i * (SHP_H + SHP_GAP)
            active = shape_mode and selected_shape == label
            draw_button(img, SHP_X, sy_, SHP_W, SHP_H, label, color, active)

        # ── Canvas overlay ─────────────────────────────────────────────────
        gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
        _, inv = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
        inv = cv2.cvtColor(inv, cv2.COLOR_GRAY2BGR)
        img = cv2.bitwise_and(img, inv)
        img = cv2.bitwise_or(img, canvas)

        # ── Status bar ────────────────────────────────────────────────────
        if shape_mode and selected_shape:
            status = f"Shape: {selected_shape}  —  drag to draw, lift to commit"
            scol   = (255, 80, 255)
        elif current_tool == TOOL_BRUSH:
            status = f"Brush  size {brush_thick}  |  raise 3 fingers to AI-snap shape"
            scol   = (80, 255, 80)
        elif current_tool == TOOL_ERASER:
            status = f"Eraser  size {eraser_thick}"
            scol   = (80, 120, 255)
        else:
            status = "Fill  —  point at area to flood-fill"
            scol   = (0, 220, 255)

        cv2.putText(img, status, (10, HDR_H + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, scol, 2)

        vstext = "Voice: ON" if voice else "Voice: OFF"
        cv2.putText(img, vstext, (10, HDR_H + 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 220), 1)

        cv2.putText(img, "Q: quit  |  2 fingers: select  |  1 finger: draw  |  3 fingers: AI snap",
                    (10, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)

        cv2.imshow("Virtual Painter", img)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # ── Cleanup ───────────────────────────────────────────────────────────────
    if voice:
        voice.stop_listening()
    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Virtual Painter — hand-gesture drawing app")
    parser.add_argument("--demo", action="store_true", help="Run without webcam (demo mode)")
    args = parser.parse_args()
    run(demo_mode=args.demo)
