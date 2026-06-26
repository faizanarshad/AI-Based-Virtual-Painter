"""
UI Renderer — all visual panel and element drawing for Virtual Painter.
Keeps presentation separate from application logic in main.py.

Design language: deep-space dark theme, vivid accents, glassmorphism panels.
"""

import math
import time

import cv2
import numpy as np

from .ui_utils import create_gradient

# ── Design tokens ──────────────────────────────────────────────────────────────
PANEL_BG    = (14,  8,  38)     # deep-space dark
PANEL_BDR   = (70, 42, 118)     # panel border
PANEL_HL    = (140, 90, 195)    # inner highlight edge
TEXT_HI     = (240, 228, 255)   # bright text
TEXT_LO     = (115, 100, 155)   # dim text
ACCENT_GOLD = ( 50, 210, 255)   # gold
ACCENT_PINK = (220,  80, 255)   # pink

# ── Tool icon painter ──────────────────────────────────────────────────────────

def draw_tool_icon(img, name, cx, cy, sz=13, color=(220, 210, 255)):
    """Draw a small iconic glyph for the given tool name, centred at (cx, cy)."""
    h = sz // 2

    if name == "Brush":
        cv2.line(img, (cx - h, cy + h), (cx + h, cy - h), color, 2)
        cv2.circle(img, (cx - h, cy + h), 3, color, -1)
        cv2.line(img, (cx - h - 3, cy + h + 2), (cx - h - 1, cy + h + 5), color, 1)

    elif name == "Spray":
        cv2.circle(img, (cx, cy), 2, color, -1)
        for i in range(8):
            a = math.radians(i * 45)
            px, py = int(cx + (h + 2) * math.cos(a)), int(cy + (h + 2) * math.sin(a))
            cv2.circle(img, (px, py), 1, color, -1)

    elif name == "Rainbow":
        for i in range(7):
            hue = i * 25
            bgr = cv2.cvtColor(np.uint8([[[hue, 255, 215]]]),
                               cv2.COLOR_HSV2BGR)[0][0]
            a = math.radians(185 + i * 24)
            px, py = int(cx + (h + 1) * math.cos(a)), int(cy + (h + 1) * math.sin(a))
            cv2.circle(img, (px, py), 2, tuple(int(v) for v in bgr), -1)

    elif name == "Neon":
        cv2.line(img, (cx - h, cy + h), (cx + h, cy - h), color, 2)
        bright = tuple(min(255, c + 140) for c in color)
        cv2.line(img, (cx - h + 1, cy + h - 1), (cx + h - 1, cy - h + 1), bright, 1)

    elif name == "Mirror":
        cv2.line(img, (cx, cy - h), (cx, cy + h), PANEL_HL, 1)
        cv2.line(img, (cx - h, cy + 2), (cx - 1, cy - h + 3), color, 2)
        cv2.line(img, (cx + 1, cy - h + 3), (cx + h, cy + 2), color, 2)

    elif name == "Eraser":
        cv2.rectangle(img, (cx - h, cy - h // 2), (cx + h, cy + h // 2),
                      (145, 138, 178), -1)
        cv2.rectangle(img, (cx - h, cy - h // 2), (cx + h, cy + h // 2),
                      (210, 198, 240), 1)
        cv2.line(img, (cx - h // 2, cy - h // 2), (cx - h // 2, cy + h // 2),
                 (210, 198, 240), 1)

    elif name == "Fill":
        pts = np.array([(cx - h, cy + h), (cx, cy - h), (cx + h, cy + h)],
                       np.int32)
        cv2.fillPoly(img, [pts], color)
        cv2.polylines(img, [pts], True,
                      tuple(min(255, c + 60) for c in color), 1)

    elif name == "Circle":
        cv2.circle(img, (cx, cy), h, color, 2)

    elif name == "Rectangle":
        cv2.rectangle(img, (cx - h, cy - h // 2), (cx + h, cy + h // 2), color, 2)

    elif name == "Triangle":
        pts = np.array([(cx, cy - h), (cx + h, cy + h), (cx - h, cy + h)],
                       np.int32)
        cv2.polylines(img, [pts], True, color, 2)

    elif name == "Line":
        cv2.line(img, (cx - h, cy + h // 2), (cx + h, cy - h // 2), color, 2)

    elif name == "Clear":
        cv2.line(img, (cx - h, cy - h), (cx + h, cy + h), color, 2)
        cv2.line(img, (cx + h, cy - h), (cx - h, cy + h), color, 2)

    elif name == "Save":
        cv2.rectangle(img, (cx - h, cy - h), (cx + h, cy + h), color, 1)
        cv2.rectangle(img, (cx - h // 2, cy - h), (cx + h // 2, cy - h // 3),
                      color, -1)
        cv2.rectangle(img, (cx - h // 3, cy), (cx + h // 3, cy + h), color, 1)

    elif name == "Undo":
        cv2.ellipse(img, (cx + 1, cy), (h, h // 2), 0, 35, 215, color, 1)
        ex = int(cx + 1 + h * math.cos(math.radians(215)))
        ey = int(cy + (h // 2) * math.sin(math.radians(215)))
        cv2.circle(img, (ex, ey), 2, color, -1)

    elif name == "Redo":
        cv2.ellipse(img, (cx - 1, cy), (h, h // 2), 0, -215, -35, color, 1)
        ex = int(cx - 1 + h * math.cos(math.radians(-35)))
        ey = int(cy + (h // 2) * math.sin(math.radians(-35)))
        cv2.circle(img, (ex, ey), 2, color, -1)


# ── Circular colour swatch ─────────────────────────────────────────────────────

def draw_circular_swatch(img, cx, cy, r, color, selected):
    cv2.circle(img, (cx, cy), r, color, -1)
    # Inner specular highlight
    light = tuple(min(255, c + 70) for c in color)
    cv2.circle(img, (cx - r // 3, cy - r // 3), r // 3 + 1, light, -1)
    if selected:
        glow = tuple(min(255, c + 90) for c in color)
        cv2.circle(img, (cx, cy), r + 5, glow, 2)
        cv2.circle(img, (cx, cy), r + 3, (255, 255, 255), 1)
    else:
        cv2.circle(img, (cx, cy), r, (60, 45, 95), 1)


# ── Glow button ────────────────────────────────────────────────────────────────

def draw_glow_button(img, x, y, w, h, icon_name, label, accent,
                     active=False, proximity=0.0):
    """
    Glassmorphism button with icon + label.
    active    → left accent strip + tinted background
    proximity → 0‥1 brightness lift as finger approaches
    """
    boost = int(proximity * 55)

    # Semi-transparent background
    bg = (tuple(min(255, c // 3 + 35 + boost) for c in accent)
          if active else (22 + boost, 14 + boost, 48 + boost))
    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), bg, -1)
    cv2.addWeighted(overlay, 0.82, img, 0.18, 0, img)

    # Border
    bdr = (tuple(min(255, c // 2 + 80 + boost) for c in accent)
           if active else tuple(min(255, c + boost // 2) for c in PANEL_BDR))
    cv2.rectangle(img, (x, y), (x + w, y + h), bdr, 1)

    # Left accent strip
    if active:
        cv2.rectangle(img, (x, y + 3), (x + 3, y + h - 3), accent, -1)

    # Icon
    ic = (accent if active
          else tuple(min(255, c + boost // 2) for c in TEXT_HI))
    draw_tool_icon(img, icon_name, x + 20, y + h // 2, sz=12, color=ic)

    # Label
    tc = (TEXT_HI if active
          else tuple(min(255, c + boost // 3) for c in TEXT_LO))
    cv2.putText(img, label, (x + 36, y + h // 2 + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.53, tc, 1)


# ── Panel background ───────────────────────────────────────────────────────────

def draw_panel(img, x, y, w, h):
    """Deep glassmorphism panel with inner highlight edges."""
    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), PANEL_BG, -1)
    cv2.addWeighted(overlay, 0.78, img, 0.22, 0, img)
    cv2.rectangle(img, (x, y), (x + w, y + h), PANEL_BDR, 1)
    cv2.line(img, (x + 1, y + 1), (x + w - 2, y + 1), PANEL_HL, 1)
    cv2.line(img, (x + 1, y + 1), (x + 1, y + h - 2), PANEL_HL, 1)


# ── Proximity helper ───────────────────────────────────────────────────────────

def _prox(finger_pos, bx, by, bw, bh, aura=190):
    if finger_pos is None:
        return 0.0
    fx, fy = finger_pos
    cx, cy = bx + bw // 2, by + bh // 2
    d = math.sqrt((fx - cx) ** 2 + (fy - cy) ** 2)
    return max(0.0, 1.0 - d / aura)


# ── Header ─────────────────────────────────────────────────────────────────────

def render_header(img, W, HDR_H, COLORS, draw_color, fps, bg_mode):
    # Base gradient — very dark purple
    hdr = create_gradient(W, HDR_H, (8, 4, 25), (22, 10, 60), "horizontal")

    # Subtle grid-dot texture
    for gx in range(0, W, 32):
        for gy in range(0, HDR_H, 32):
            cv2.circle(hdr, (gx, gy), 1, (28, 16, 55), -1)

    # ── Colour swatches (2 rows × 10 circles) ────────────────────────────
    R    = 19        # radius
    STEP = R * 2 + 9 # centre-to-centre distance
    X0   = 16 + R    # first circle centre x
    Y1   = HDR_H // 4       # row-1 centre y
    Y2   = HDR_H * 3 // 4   # row-2 centre y

    for i, c in enumerate(COLORS):
        col = i % 10
        row = i // 10
        draw_circular_swatch(hdr,
                              X0 + col * STEP,
                              Y1 if row == 0 else Y2,
                              R, c, c == draw_color)

    # ── App title ─────────────────────────────────────────────────────────
    swatch_right = X0 + 9 * STEP + R + 20
    title_zone   = W - swatch_right - 110   # leave room for badge

    title    = "VIRTUAL PAINTER"
    subtitle = "AI Hand-Gesture Drawing"
    t_scale  = 1.25
    tw       = cv2.getTextSize(title, cv2.FONT_HERSHEY_DUPLEX, t_scale, 2)[0][0]
    sw       = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0][0]

    tx = swatch_right + (title_zone - tw) // 2
    sx = swatch_right + (title_zone - sw) // 2
    ty = HDR_H // 2 - 2
    sy = ty + 22

    # Title shadow → gold text
    cv2.putText(hdr, title, (tx + 2, ty + 2),
                cv2.FONT_HERSHEY_DUPLEX, t_scale, (0, 0, 0), 3)
    cv2.putText(hdr, title, (tx, ty),
                cv2.FONT_HERSHEY_DUPLEX, t_scale, (50, 210, 255), 2)
    # Subtitle
    cv2.putText(hdr, subtitle, (sx, sy),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 120, 195), 1)

    # ── FPS / BG badge (top right) ────────────────────────────────────────
    bx, by = W - 108, HDR_H // 2 - 26
    bw, bh = 100, 42
    cv2.rectangle(hdr, (bx, by), (bx + bw, by + bh), (20, 12, 50), -1)
    cv2.rectangle(hdr, (bx, by), (bx + bw, by + bh), (75, 45, 125), 1)
    cv2.putText(hdr, f"FPS {fps:>3.0f}", (bx + 6, by + 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (100, 210, 255), 1)
    cv2.putText(hdr, f"BG {bg_mode}", (bx + 6, by + 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (140, 170, 210), 1)

    # ── Animated star sparkles ────────────────────────────────────────────
    t = time.time()
    for i in range(12):
        px = int(15 + (t * 90 + i * 95) % (W - 30))
        py = int(5 + 5 * math.sin(t * 2.8 + i * 1.15))
        brightness = int(180 + 75 * math.sin(t * 4 + i))
        cv2.circle(hdr, (px, py), 1, (brightness, brightness, brightness), -1)

    # ── Bottom accent line ────────────────────────────────────────────────
    for x in range(0, W, 1):
        ratio = x / W
        r = int(80  * (1 - ratio) + 200 * ratio)
        g = int(40  * (1 - ratio) +  60 * ratio)
        b = int(160 * (1 - ratio) + 255 * ratio)
        hdr[HDR_H - 2, x] = (b, g, r)
    cv2.line(hdr, (0, HDR_H - 1), (W, HDR_H - 1), (40, 20, 80), 1)

    img[0:HDR_H, 0:W] = hdr


# ── Right tool panel ───────────────────────────────────────────────────────────

def render_right_panel(img, HDR_H, W,
                       RP_X, RP_W, BTN_X, BTN_W, BTN_H, BTN_GAP,
                       TOOL_BUTTONS, ACTION_BUTTONS,
                       current_tool, shape_mode,
                       brush_thick, draw_color, finger_pos):

    # Group Y positions
    BY0      = HDR_H + 12
    sep1_y   = BY0 + len(TOOL_BUTTONS) * (BTN_H + BTN_GAP) + 2
    act_y0   = sep1_y + 14
    sep2_y   = act_y0 + len(ACTION_BUTTONS) * (BTN_H + BTN_GAP) + 2
    size_y   = sep2_y + 14

    panel_h  = size_y + 56 - HDR_H
    draw_panel(img, RP_X, HDR_H, RP_W, panel_h)

    # Section label
    cv2.putText(img, "TOOLS", (BTN_X + 4, HDR_H + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, TEXT_LO, 1)

    # ── Tool buttons ──────────────────────────────────────────────────────
    for idx, (label, tool, accent) in enumerate(TOOL_BUTTONS):
        by     = BY0 + idx * (BTN_H + BTN_GAP)
        prox   = _prox(finger_pos, BTN_X, by, BTN_W, BTN_H)
        active = (current_tool == tool and not shape_mode)
        draw_glow_button(img, BTN_X, by, BTN_W, BTN_H,
                         label, label, accent, active, prox)

    # Separator
    _draw_sep(img, RP_X, RP_W, sep1_y)

    # ── Action buttons ────────────────────────────────────────────────────
    cv2.putText(img, "ACTIONS", (BTN_X + 4, act_y0 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, TEXT_LO, 1)
    for idx, (label, action, accent) in enumerate(ACTION_BUTTONS):
        by   = act_y0 + idx * (BTN_H + BTN_GAP)
        prox = _prox(finger_pos, BTN_X, by, BTN_W, BTN_H)
        draw_glow_button(img, BTN_X, by, BTN_W, BTN_H,
                         label, label, accent, False, prox)

    # Separator
    _draw_sep(img, RP_X, RP_W, sep2_y)

    # ── Brush size indicator ──────────────────────────────────────────────
    cv2.putText(img, "SIZE", (BTN_X + 4, size_y + 1),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, TEXT_LO, 1)
    si_cx = BTN_X + BTN_W // 2
    si_cy = size_y + 30
    r_show = min(20, max(4, brush_thick // 2))
    cv2.circle(img, (si_cx, si_cy), r_show, draw_color, -1)
    cv2.circle(img, (si_cx, si_cy), r_show, (210, 195, 240), 1)
    cv2.putText(img, str(brush_thick), (si_cx - 8, si_cy + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, TEXT_HI, 1)

    return BY0, sep1_y, act_y0  # expose for hit-testing


# ── Left shape panel ───────────────────────────────────────────────────────────

def render_left_panel(img, HDR_H,
                      LP_X, LP_W, SHP_X, SHP_W, SHP_H, SHP_GAP,
                      SHAPE_BUTTONS, selected_shape, shape_mode, finger_pos):

    BY0     = HDR_H + 12
    panel_h = BY0 + len(SHAPE_BUTTONS) * (SHP_H + SHP_GAP) + 24 - HDR_H
    draw_panel(img, LP_X, HDR_H, LP_W, panel_h)

    cv2.putText(img, "SHAPES", (SHP_X + 4, HDR_H + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, TEXT_LO, 1)

    for idx, (label, accent) in enumerate(SHAPE_BUTTONS):
        by     = BY0 + idx * (SHP_H + SHP_GAP)
        prox   = _prox(finger_pos, SHP_X, by, SHP_W, SHP_H)
        active = shape_mode and selected_shape == label
        draw_glow_button(img, SHP_X, by, SHP_W, SHP_H,
                         label, label, accent, active, prox)

    return BY0


# ── Status bar ─────────────────────────────────────────────────────────────────

def render_status_bar(img, W, H,
                      current_tool, brush_thick, eraser_thick,
                      shape_mode, selected_shape,
                      voice_on, TOOL_COLORS):

    bar_y = H - 30
    bar   = create_gradient(W, 30, (14, 8, 38), (8, 4, 25), "horizontal")

    # Top separator line
    for x in range(W):
        r = x / W
        bar[0, x] = (int(118*(1-r)+80*r), int(70*(1-r)+40*r), int(195*(1-r)+140*r))

    # Status text
    if shape_mode and selected_shape:
        status = f"{selected_shape}  —  drag to draw, lift finger to commit"
        scol   = (220, 100, 255)
    else:
        labels = {
            "brush":   f"Brush  sz:{brush_thick}  |  raise 3 fingers → AI shape snap",
            "spray":   f"Spray  radius:{brush_thick + 12}",
            "rainbow": "Rainbow  — hue cycles as you draw",
            "neon":    f"Neon Glow  sz:{brush_thick}",
            "mirror":  f"Mirror Draw  sz:{brush_thick}  (symmetric)",
            "eraser":  f"Eraser  sz:{eraser_thick}",
            "fill":    "Fill  —  point at enclosed region",
        }
        scol = TOOL_COLORS.get(current_tool, TEXT_HI)
        status = labels.get(current_tool, current_tool.title())

    cv2.putText(bar, status, (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, scol, 1)

    # Keyboard hints (right)
    hint = "q:quit  u:undo  r:redo  s:save  c:clear  b:bg  [ ]:size"
    hw = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.36, 1)[0][0]
    cv2.putText(bar, hint, (W - hw - 10, 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, TEXT_LO, 1)

    # Voice indicator
    v_col = (50, 220, 120) if voice_on else (100, 80, 140)
    v_txt = "● VOICE ON" if voice_on else "○ VOICE OFF"
    cv2.putText(bar, v_txt, (W - hw - 10, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, v_col, 1)

    img[bar_y:H, 0:W] = bar


# ── Internal helpers ───────────────────────────────────────────────────────────

def _draw_sep(img, px, pw, y):
    """Thin horizontal separator inside a panel."""
    for x in range(px + 6, px + pw - 6):
        r = (x - px) / pw
        col = tuple(int(PANEL_BDR[i] * (1 - r) + PANEL_HL[i] * r) for i in range(3))
        if 0 <= y < img.shape[0] and 0 <= x < img.shape[1]:
            img[y, x] = col
