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
    create_gradient, create_grid,
    draw_glass_panel, draw_button, draw_separator,
    draw_cursor, draw_shape,
    spray_paint, neon_stroke, mirror_stroke, rainbow_color,
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
HDR_H    = 116          # header height (2 swatch rows + padding)

# Colour swatches  (2 rows × 10, left portion of header)
CLR_SZ   = 49           # swatch square size
CLR_GAP  = 5
CLR_X0   = 14
CLR_R1_Y = 8            # row-1 top
CLR_R2_Y = CLR_R1_Y + CLR_SZ + CLR_GAP   # row-2 top

# Right panel
RP_X     = W - 158
RP_W     = 155
BTN_X    = RP_X + 6
BTN_W    = RP_W - 12
BTN_H    = 36
BTN_GAP  = 7

# Left panel (shapes)
LP_X     = 2
LP_W     = 148
SHP_X    = LP_X + 6
SHP_W    = LP_W - 12
SHP_H    = 36
SHP_GAP  = 7

# Button Y start (below header)
BY0      = HDR_H + 14   # first button top-y

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

                    # Colour swatches
                    if fy < HDR_H:
                        for i, c in enumerate(COLORS):
                            row = i // 10
                            col = i % 10
                            cx0 = CLR_X0 + col * (CLR_SZ + CLR_GAP)
                            cy0 = CLR_R1_Y + row * (CLR_SZ + CLR_GAP)
                            if cx0 < fx < cx0 + CLR_SZ and cy0 < fy < cy0 + CLR_SZ:
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
                        sep_y    = BY0 + len(TOOL_BUTTONS) * (BTN_H + BTN_GAP) + 4
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

        # ── Header ─────────────────────────────────────────────────────
        header = create_gradient(W, HDR_H,
                                 (60, 20, 100), (20, 10, 70), "horizontal")

        # Colour swatches (2 rows × 10)
        for i, c in enumerate(COLORS):
            row = i // 10
            col = i % 10
            cx0 = CLR_X0 + col * (CLR_SZ + CLR_GAP)
            cy0 = CLR_R1_Y + row * (CLR_SZ + CLR_GAP)
            swatch = create_gradient(CLR_SZ, CLR_SZ,
                                     tuple(max(0, v - 35) for v in c),
                                     c, "vertical")
            header[cy0:cy0 + CLR_SZ, cx0:cx0 + CLR_SZ] = swatch
            # Active colour: bright outer ring
            bw  = 3 if c == draw_color else 1
            col_ = tuple(min(255, v + 80) for v in c) if c == draw_color else (220, 200, 240)
            cv2.rectangle(header, (cx0, cy0),
                          (cx0 + CLR_SZ, cy0 + CLR_SZ), col_, bw)

        # Title
        title = "Virtual Painter"
        tsz   = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
        tx    = CLR_X0 + 10 * (CLR_SZ + CLR_GAP) + (W - CLR_X0 - 10 * (CLR_SZ + CLR_GAP) - tsz[0]) // 2
        ty    = HDR_H // 2 + 10
        cv2.putText(header, title, (tx + 2, ty + 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 4)
        cv2.putText(header, title, (tx, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 215, 50), 3)

        # FPS counter
        fps_buf.append(t0)
        fps = (len(fps_buf) / (fps_buf[-1] - fps_buf[0])) if len(fps_buf) > 1 else 0
        cv2.putText(header, f"FPS {fps:.0f}", (W - 90, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 200, 255), 1)

        # Animated sparkles across header
        for i in range(8):
            px = int(20 + (t0 * 70 + i * 140) % (W - 40))
            py = int(5 + 6 * np.sin(t0 * 2.5 + i * 1.1))
            cv2.circle(header, (px, py), 2, (255, 255, 200), -1)

        img[0:HDR_H, 0:W] = header

        # ── Side panels (glass) ────────────────────────────────────────
        # Right panel
        rp_bottom = (BY0 + len(TOOL_BUTTONS) * (BTN_H + BTN_GAP) + 24
                     + len(ACTION_BUTTONS)  * (BTN_H + BTN_GAP) + 60)
        draw_glass_panel(img, RP_X, HDR_H, RP_W, rp_bottom - HDR_H)

        # Left panel
        lp_bottom = BY0 + len(SHAPE_BUTTONS) * (SHP_H + SHP_GAP) + 20
        draw_glass_panel(img, LP_X, HDR_H, LP_W, lp_bottom - HDR_H)

        # ── Right panel buttons ────────────────────────────────────────
        sep_y  = BY0 + len(TOOL_BUTTONS) * (BTN_H + BTN_GAP) + 4
        act_y0 = sep_y + 14

        for idx, (label, tool, color) in enumerate(TOOL_BUTTONS):
            by     = BY0 + idx * (BTN_H + BTN_GAP)
            prox   = (_proximity(finger_pos[0], finger_pos[1], BTN_X, by, BTN_W, BTN_H)
                      if finger_pos else 0.0)
            active = (current_tool == tool and not shape_mode)
            draw_button(img, BTN_X, by, BTN_W, BTN_H, label, color, active, prox)

        draw_separator(img, RP_X, sep_y + 6, RP_W)

        for idx, (label, action, color) in enumerate(ACTION_BUTTONS):
            by   = act_y0 + idx * (BTN_H + BTN_GAP)
            prox = (_proximity(finger_pos[0], finger_pos[1], BTN_X, by, BTN_W, BTN_H)
                    if finger_pos else 0.0)
            draw_button(img, BTN_X, by, BTN_W, BTN_H, label, color, False, prox)

        # Size indicator in right panel
        si_y  = act_y0 + len(ACTION_BUTTONS) * (BTN_H + BTN_GAP) + 8
        si_cx = BTN_X + BTN_W // 2
        si_cy = si_y + 22
        r_show = min(22, brush_thick // 2 + 4)
        cv2.circle(img, (si_cx, si_cy), r_show, draw_color, -1)
        cv2.circle(img, (si_cx, si_cy), r_show, (220, 200, 240), 1)
        cv2.putText(img, f"size {brush_thick}", (BTN_X + 4, si_cy + r_show + 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 185, 225), 1)

        # ── Left panel shape buttons ───────────────────────────────────
        lp_label_y = HDR_H + 8
        cv2.putText(img, "Shapes", (SHP_X + 12, lp_label_y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 170, 230), 1)

        for idx, (label, color) in enumerate(SHAPE_BUTTONS):
            by     = BY0 + idx * (SHP_H + SHP_GAP)
            prox   = (_proximity(finger_pos[0], finger_pos[1], SHP_X, by, SHP_W, SHP_H)
                      if finger_pos else 0.0)
            active = shape_mode and selected_shape == label
            draw_button(img, SHP_X, by, SHP_W, SHP_H, label, color, active, prox)

        # ── Status bar (bottom) ────────────────────────────────────────
        bar_y = H - 28
        bar   = create_gradient(W, 28, (25, 12, 50), (12, 6, 35), "horizontal")
        img[bar_y:H, 0:W] = bar

        if shape_mode and selected_shape:
            status = f"Shape: {selected_shape}  |  drag 1 finger to draw, lift to commit"
            scol   = (240, 130, 255)
        else:
            labels = {
                TOOL_BRUSH:   f"Brush  (size {brush_thick})  |  raise 3 fingers to AI-snap",
                TOOL_SPRAY:   f"Spray  (radius {brush_thick+12})",
                TOOL_RAINBOW: "Rainbow  — colour cycles automatically",
                TOOL_NEON:    f"Neon Glow  (size {brush_thick})",
                TOOL_MIRROR:  f"Mirror Draw  (size {brush_thick})",
                TOOL_ERASER:  f"Eraser  (size {eraser_thick})",
                TOOL_FILL:    "Fill  — point at region to flood-fill",
            }
            scol_map = {
                TOOL_BRUSH: (100, 255, 100), TOOL_SPRAY: (200, 160, 80),
                TOOL_RAINBOW: (200, 100, 220), TOOL_NEON: (80, 240, 240),
                TOOL_MIRROR: (240, 220, 80), TOOL_ERASER: (255, 100, 100),
                TOOL_FILL: (100, 160, 255),
            }
            status = labels.get(current_tool, current_tool)
            scol   = scol_map.get(current_tool, (200, 200, 200))

        cv2.putText(img, status, (10, bar_y + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, scol, 1)

        hint = ("q:quit  u:undo  r:redo  s:save  c:clear  b:bg  "
                "[:size-  ]:size+   Voice: " + ("ON" if voice else "OFF"))
        cv2.putText(img, hint, (W - 640, bar_y + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 110, 160), 1)

        # ── Mirror centre line (visual guide) ─────────────────────────
        if current_tool == TOOL_MIRROR:
            cv2.line(img, (W // 2, HDR_H), (W // 2, H - 28), (60, 60, 100), 1)

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
