"""
Virtual Painter — AI-powered hand-gesture drawing application.

Usage:
    python main.py           # normal mode (requires webcam)
    python main.py --demo    # demo / no-camera mode

Keyboard shortcuts:
    q / ESC   quit
    u         undo
    r         redo
    s         save painting
    c         clear canvas
    b         cycle background  (black → white → grid)
    [ / ]     decrease / increase brush & eraser size
"""

import argparse
import math
import os
import threading
import time
from collections import deque

import cv2
import numpy as np

from src import (
    HandDetector, ShapeDetector, VOICE_AVAILABLE,
    create_grid, draw_cursor, draw_shape,
    spray_paint, neon_stroke, mirror_stroke, rainbow_color,
)
from src.ui_renderer import (
    render_header, render_right_panel, render_left_panel, render_status_bar,
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# ── Tool IDs ──────────────────────────────────────────────────────────────────
TOOL_BRUSH   = "brush"
TOOL_SPRAY   = "spray"
TOOL_RAINBOW = "rainbow"
TOOL_NEON    = "neon"
TOOL_MIRROR  = "mirror"
TOOL_ERASER  = "eraser"
TOOL_FILL    = "fill"
TOOL_SHAPE   = "shape"

# ── 20-colour palette (2 rows of 10, BGR) ────────────────────────────────────
COLORS = [
    # Row 0 — warm spectrum
    (0,   0,   255),   # Red
    (0,   60,  255),   # Red-Orange
    (0,   140, 255),   # Orange
    (0,   215, 255),   # Gold
    (0,   255, 200),   # Yellow-Green
    (0,   220,   0),   # Green
    (255, 255,   0),   # Cyan
    (255, 130,   0),   # Sky Blue
    (255,   0,   0),   # Blue
    (200,   0, 200),   # Violet
    # Row 1 — cool / special
    (255,   0, 180),   # Magenta
    (200,   0, 255),   # Purple
    (150,  50, 255),   # Indigo
    (30,  110, 200),   # Brown
    (180, 210, 230),   # Beige
    (255, 255, 255),   # White
    (180, 180, 180),   # Light Gray
    (80,   80,  80),   # Dark Gray
    (0,   215, 255),   # Gold (2)
    (0,   255, 127),   # Spring Green
]

# ── Canvas dimensions ─────────────────────────────────────────────────────────
W, H     = 1280, 720
HDR_H    = 130          # header: 2 rows of circular swatches + title

# Colour swatches hit-test (circular, renderer uses R=19, STEP=48)
_CLR_R    = 19
_CLR_STEP = _CLR_R * 2 + 9   # 47
_CLR_X0   = 16 + _CLR_R      # 35
_CLR_Y1   = HDR_H // 4       # 32
_CLR_Y2   = HDR_H * 3 // 4   # 97

# Right panel
RP_X  = W - 168
RP_W  = 165
BTN_X = RP_X + 8
BTN_W = RP_W - 16
BTN_H = 38
BTN_GAP = 7

# Left panel (shapes)
LP_X  = 0
LP_W  = 158
SHP_X = LP_X + 8
SHP_W = LP_W - 16
SHP_H = 38
SHP_GAP = 7

# Button Y start (below header) — must match renderer
BY0 = HDR_H + 12

TOOL_BUTTONS = [
    ("Brush",   TOOL_BRUSH,   ( 40, 180,  70)),
    ("Spray",   TOOL_SPRAY,   (170, 110,  40)),
    ("Rainbow", TOOL_RAINBOW, (160,  50, 180)),
    ("Neon",    TOOL_NEON,    ( 20, 200, 220)),
    ("Mirror",  TOOL_MIRROR,  (200, 160,  30)),
    ("Eraser",  TOOL_ERASER,  (180,  60,  60)),
    ("Fill",    TOOL_FILL,    ( 60, 100, 220)),
]
ACTION_BUTTONS = [
    ("Clear", "clear", (200,  90,  40)),
    ("Save",  "save",  ( 40, 190,  90)),
    ("Undo",  "undo",  ( 90,  90, 180)),
    ("Redo",  "redo",  ( 90,  90, 180)),
]
SHAPE_BUTTONS = [
    ("Circle",    (220,  90,  90)),
    ("Rectangle", ( 90, 220,  90)),
    ("Triangle",  ( 90,  90, 220)),
    ("Line",      (220, 210,  60)),
]

BRUSH_SIZES  = [4, 7, 12, 18, 25, 35]
ERASER_SIZES = [18, 28, 40, 55, 75]
BACKGROUNDS  = ["black", "white", "grid"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save(canvas):
    path = os.path.join(OUTPUT_DIR, f"painting_{int(time.time())}.png")
    cv2.imwrite(path, canvas)
    print(f"[Save] {path}")
    return path


def _flood_fill(canvas, sx, sy, replacement):
    """Iterative 4-connected flood fill."""
    target = canvas[sy, sx].copy()
    rep    = np.array(replacement, dtype=np.uint8)
    if np.array_equal(target, rep):
        return
    ch, cw = canvas.shape[:2]
    stack  = [(sx, sy)]
    while stack:
        x, y = stack.pop()
        if x < 0 or x >= cw or y < 0 or y >= ch:
            continue
        if np.array_equal(canvas[y, x], target):
            canvas[y, x] = rep
            stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]


def _bg_frame(bg_mode):
    """Return a blank background frame for the chosen mode."""
    if bg_mode == "white":
        return np.full((H, W, 3), 255, dtype=np.uint8)
    if bg_mode == "grid":
        return create_grid(W, H)
    return np.zeros((H, W, 3), dtype=np.uint8)   # black


def _proximity(fx, fy, bx, by, bw, bh, aura=200):
    """0‥1 proximity of finger to a button (1 = touching centre)."""
    cx = bx + bw // 2
    cy = by + bh // 2
    d  = math.sqrt((fx - cx) ** 2 + (fy - cy) ** 2)
    return max(0.0, 1.0 - d / aura)


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
            print("[Camera] Not found — demo mode")
            cap = None

    detector       = HandDetector(detectionCon=0.85)
    shape_detector = ShapeDetector()

    # Voice — initialise in a background thread so the window opens immediately
    voice        = None
    last_voice_t = 0.0
    VOICE_COOL   = 2.0

    def _init_voice():
        nonlocal voice
        if not VOICE_AVAILABLE:
            return
        try:
            from src.voice_controller import VoiceController
            vc = VoiceController()
            vc.start_listening()
            voice = vc
            print("[Voice] Active")
        except Exception as e:
            print(f"[Voice] Unavailable: {e}")

    threading.Thread(target=_init_voice, daemon=True).start()

    # ── State ──────────────────────────────────────────────────────────────
    canvas       = np.zeros((H, W, 3), np.uint8)
    draw_color   = (255, 0, 255)
    current_tool = TOOL_BRUSH
    bg_mode_idx  = 0   # index into BACKGROUNDS

    brush_idx    = 2
    eraser_idx   = 2
    brush_thick  = BRUSH_SIZES[brush_idx]
    eraser_thick = ERASER_SIZES[eraser_idx]

    undo_stack   = deque(maxlen=25)
    redo_stack   = deque(maxlen=25)

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

    # Shape drawing
    shape_mode     = False
    selected_shape = None
    shape_start    = None

    # AI snap
    ai_points  = []
    ai_active  = False

    # Smooth cursor (EMA)
    sx, sy     = 0.0, 0.0   # smoothed finger position
    xp, yp     = 0, 0       # previous draw position

    # FPS
    fps_buf    = deque(maxlen=30)

    # Finger position for proximity (shared between display and gestures)
    finger_pos = None

    # ── Loop ───────────────────────────────────────────────────────────────
    while True:
        t0 = time.time()

        # Frame
        if cap is not None:
            ok, img = cap.read()
            if not ok:
                img = _bg_frame(BACKGROUNDS[bg_mode_idx])
        else:
            img = _bg_frame(BACKGROUNDS[bg_mode_idx])
            cv2.putText(img, "DEMO MODE  (no camera)",
                        (W // 2 - 220, H // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (130, 120, 180), 2)

        img = cv2.flip(img, 1)

        # ── Voice commands ─────────────────────────────────────────────
        if voice:
            cmd = voice.get_command()
            now = time.time()
            if cmd and (now - last_voice_t) >= VOICE_COOL:
                last_voice_t = now
                cmd_l = cmd.lower()
                if   "brush"   in cmd_l: current_tool = TOOL_BRUSH;   shape_mode = False
                elif "spray"   in cmd_l: current_tool = TOOL_SPRAY;   shape_mode = False
                elif "rainbow" in cmd_l: current_tool = TOOL_RAINBOW; shape_mode = False
                elif "neon"    in cmd_l: current_tool = TOOL_NEON;    shape_mode = False
                elif "mirror"  in cmd_l: current_tool = TOOL_MIRROR;  shape_mode = False
                elif "eraser"  in cmd_l: current_tool = TOOL_ERASER;  shape_mode = False
                elif "fill"    in cmd_l: current_tool = TOOL_FILL;    shape_mode = False
                elif "clear"   in cmd_l: save_state(); canvas[:] = 0
                elif "save"    in cmd_l: _save(canvas)
                elif "undo"    in cmd_l: undo()
                elif "redo"    in cmd_l: redo()
                elif "red"     in cmd_l: draw_color = (0,   0,   255)
                elif "green"   in cmd_l: draw_color = (0,   255,   0)
                elif "blue"    in cmd_l: draw_color = (255,   0,   0)
                elif "yellow"  in cmd_l: draw_color = (0,   255, 255)
                elif "purple"  in cmd_l: draw_color = (128,   0, 128)
                elif "white"   in cmd_l: draw_color = (255, 255, 255)
                elif "orange"  in cmd_l: draw_color = (0,   140, 255)
                elif "cyan"    in cmd_l: draw_color = (255, 255,   0)

        # ── Hand tracking ──────────────────────────────────────────────
        if cap is not None:
            img = detector.findHands(img)
            lms = detector.findPosition(img, draw=False)

            if lms:
                rx, ry = lms[8][1], lms[8][2]   # raw index tip

                # Exponential moving average → smooth cursor
                alpha_ema = 0.45
                sx = sx * (1 - alpha_ema) + rx * alpha_ema
                sy = sy * (1 - alpha_ema) + ry * alpha_ema
                fx, fy = int(sx), int(sy)
                finger_pos = (fx, fy)

                fingers = detector.fingersUp()

                # ── AI snap: index + middle + ring (pinky may be up too) ──
                if fingers[1] and fingers[2] and fingers[3]:
                    xp, yp = 0, 0
                    if ai_active and len(ai_points) > 4:
                        kind = shape_detector.detect(ai_points)
                        if kind:
                            save_state()
                            shape_detector.complete(kind, ai_points,
                                                    canvas, draw_color, brush_thick)
                            print(f"[AI] snapped → {kind}")
                    ai_points.clear()
                    ai_active = False

                # ── Selection: index + middle, ring must be down ───────
                elif fingers[1] and fingers[2] and not fingers[3]:
                    xp, yp = 0, 0
                    shape_start = None
                    ai_points.clear()
                    ai_active = False

                    # Colour swatches (circular hit-test)
                    if fy < HDR_H:
                        for i, c in enumerate(COLORS):
                            col = i % 10
                            row = i // 10
                            scx = _CLR_X0 + col * _CLR_STEP
                            scy = _CLR_Y1 if row == 0 else _CLR_Y2
                            if math.sqrt((fx-scx)**2 + (fy-scy)**2) < _CLR_R + 4:
                                draw_color   = c
                                current_tool = TOOL_BRUSH
                                shape_mode   = False

                    # Right panel — tool buttons
                    if fx > RP_X:
                        # Tool buttons (first block)
                        for idx, (label, tool, _) in enumerate(TOOL_BUTTONS):
                            by = BY0 + idx * (BTN_H + BTN_GAP)
                            if BTN_X < fx < BTN_X + BTN_W and by < fy < by + BTN_H:
                                current_tool = tool
                                shape_mode   = False

                        # Action buttons (second block, after separator)
                        sep_y    = BY0 + len(TOOL_BUTTONS) * (BTN_H + BTN_GAP) + 2
                        act_y0   = sep_y + 14
                        for idx, (label, action, _) in enumerate(ACTION_BUTTONS):
                            by = act_y0 + idx * (BTN_H + BTN_GAP)
                            if BTN_X < fx < BTN_X + BTN_W and by < fy < by + BTN_H:
                                if action == "clear":
                                    save_state(); canvas[:] = 0
                                elif action == "save":
                                    _save(canvas)
                                elif action == "undo":
                                    undo()
                                elif action == "redo":
                                    redo()

                    # Left panel — shape buttons
                    if fx < LP_X + LP_W:
                        for idx, (label, _) in enumerate(SHAPE_BUTTONS):
                            by = BY0 + idx * (SHP_H + SHP_GAP)
                            if SHP_X < fx < SHP_X + SHP_W and by < fy < by + SHP_H:
                                selected_shape = label
                                shape_mode     = True
                                current_tool   = TOOL_SHAPE

                    draw_cursor(img, fx, fy, "select", 12, draw_color)

                # ── Draw: only index finger ─────────────────────────────
                elif fingers[1] and not fingers[2]:
                    if xp == 0 and yp == 0:
                        xp, yp = fx, fy
                        if shape_mode:
                            shape_start = (fx, fy)

                    if current_tool == TOOL_BRUSH:
                        cv2.line(canvas, (xp, yp), (fx, fy), draw_color, brush_thick)
                        ai_points.append((fx, fy))
                        ai_active = True

                    elif current_tool == TOOL_SPRAY:
                        spray_paint(canvas, fx, fy, draw_color,
                                    radius=brush_thick + 12, density=50)
                        ai_points.clear(); ai_active = False

                    elif current_tool == TOOL_RAINBOW:
                        rc = rainbow_color()
                        cv2.line(canvas, (xp, yp), (fx, fy), rc, brush_thick)
                        draw_color = rc
                        ai_points.clear(); ai_active = False

                    elif current_tool == TOOL_NEON:
                        neon_stroke(canvas, (xp, yp), (fx, fy),
                                    draw_color, brush_thick)
                        ai_points.clear(); ai_active = False

                    elif current_tool == TOOL_MIRROR:
                        mirror_stroke(canvas, (xp, yp), (fx, fy),
                                      draw_color, brush_thick)
                        ai_points.clear(); ai_active = False

                    elif current_tool == TOOL_ERASER:
                        mask = np.zeros(canvas.shape[:2], np.uint8)
                        cv2.line(mask, (xp, yp), (fx, fy), 255, eraser_thick)
                        canvas[mask == 255] = 0
                        ai_points.clear(); ai_active = False

                    elif current_tool == TOOL_FILL:
                        save_state()
                        _flood_fill(canvas, fx, fy, list(draw_color))
                        ai_points.clear(); ai_active = False

                    elif (current_tool == TOOL_SHAPE and shape_mode
                          and selected_shape and shape_start):
                        tmp = canvas.copy()
                        draw_shape(tmp, selected_shape,
                                   shape_start, (fx, fy), draw_color, 3)
                        canvas[:] = tmp

                    xp, yp = fx, fy
                    draw_cursor(img, fx, fy, current_tool, brush_thick, draw_color)

                # ── Finger lifted → commit drag-to-draw shape ───────────
                elif (not fingers[1] and shape_mode
                      and selected_shape and shape_start):
                    save_state()
                    shape_start = None
                    xp, yp = 0, 0

                else:
                    xp, yp = 0, 0
                    ai_points.clear()
                    ai_active = False

        # ── Canvas overlay ─────────────────────────────────────────────
        gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
        _, inv = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
        inv = cv2.cvtColor(inv, cv2.COLOR_GRAY2BGR)
        img = cv2.bitwise_and(img, inv)
        img = cv2.bitwise_or(img, canvas)

        # ── FPS ────────────────────────────────────────────────────────
        fps_buf.append(t0)
        fps = (len(fps_buf) / (fps_buf[-1] - fps_buf[0])) if len(fps_buf) > 1 else 0

        # ── Premium UI ─────────────────────────────────────────────────
        render_header(img, W, HDR_H, COLORS, draw_color, fps,
                      BACKGROUNDS[bg_mode_idx])

        render_right_panel(img, HDR_H, W,
                           RP_X, RP_W, BTN_X, BTN_W, BTN_H, BTN_GAP,
                           TOOL_BUTTONS, ACTION_BUTTONS,
                           current_tool, shape_mode,
                           brush_thick, draw_color, finger_pos)

        render_left_panel(img, HDR_H,
                          LP_X, LP_W, SHP_X, SHP_W, SHP_H, SHP_GAP,
                          SHAPE_BUTTONS, selected_shape, shape_mode, finger_pos)

        TOOL_COLORS = {
            TOOL_BRUSH: (100, 255, 100), TOOL_SPRAY: (200, 160, 80),
            TOOL_RAINBOW: (200, 80, 220), TOOL_NEON: (50, 230, 230),
            TOOL_MIRROR: (230, 210, 60), TOOL_ERASER: (255, 100, 100),
            TOOL_FILL: (100, 160, 255),
        }
        render_status_bar(img, W, H,
                          current_tool, brush_thick, eraser_thick,
                          shape_mode, selected_shape,
                          voice is not None, TOOL_COLORS)

        # ── Mirror centre line visual guide ────────────────────────────
        if current_tool == TOOL_MIRROR:
            cv2.line(img, (W // 2, HDR_H), (W // 2, H - 30), (60, 50, 100), 1)

        # ── Display ────────────────────────────────────────────────────
        cv2.imshow("Virtual Painter", img)

        # ── Keyboard shortcuts ─────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):   # q or ESC
            break
        elif key == ord("u"):
            undo()
        elif key == ord("r"):
            redo()
        elif key == ord("s"):
            _save(canvas)
        elif key == ord("c"):
            save_state(); canvas[:] = 0
        elif key == ord("b"):
            bg_mode_idx = (bg_mode_idx + 1) % len(BACKGROUNDS)
            print(f"[BG] {BACKGROUNDS[bg_mode_idx]}")
        elif key == ord("["):
            if current_tool == TOOL_ERASER:
                eraser_idx  = max(0, eraser_idx - 1)
                eraser_thick = ERASER_SIZES[eraser_idx]
            else:
                brush_idx  = max(0, brush_idx - 1)
                brush_thick = BRUSH_SIZES[brush_idx]
        elif key == ord("]"):
            if current_tool == TOOL_ERASER:
                eraser_idx  = min(len(ERASER_SIZES) - 1, eraser_idx + 1)
                eraser_thick = ERASER_SIZES[eraser_idx]
            else:
                brush_idx  = min(len(BRUSH_SIZES) - 1, brush_idx + 1)
                brush_thick = BRUSH_SIZES[brush_idx]

    # ── Cleanup ────────────────────────────────────────────────────────────
    if voice:
        voice.stop_listening()
    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Virtual Painter — AI-powered hand-gesture drawing app")
    parser.add_argument("--demo", action="store_true",
                        help="Run without webcam (demo / no-camera mode)")
    args = parser.parse_args()
    run(demo_mode=args.demo)
