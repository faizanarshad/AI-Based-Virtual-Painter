"""
UI drawing helpers: gradient, glassmorphism panel, buttons, shapes, cursor.
"""

import math

import cv2
import numpy as np


# ── Backgrounds ───────────────────────────────────────────────────────────────

def create_gradient(width, height, color1, color2, direction="horizontal"):
    """Return an (H, W, 3) uint8 gradient array — fully vectorised."""
    bg = np.empty((height, width, 3), dtype=np.float32)
    if direction == "horizontal":
        t = np.linspace(0.0, 1.0, width, dtype=np.float32)  # (W,)
        for i in range(3):
            bg[:, :, i] = color1[i] * (1.0 - t) + color2[i] * t
    else:
        t = np.linspace(0.0, 1.0, height, dtype=np.float32).reshape(-1, 1)  # (H,1)
        for i in range(3):
            bg[:, :, i] = color1[i] * (1.0 - t) + color2[i] * t
    return bg.astype(np.uint8)


def create_grid(width, height, cell=40,
                bg=(18, 12, 35), line=(40, 30, 65)):
    """Return a dark grid background."""
    canvas = np.full((height, width, 3), bg, dtype=np.uint8)
    for x in range(0, width, cell):
        cv2.line(canvas, (x, 0), (x, height), line, 1)
    for y in range(0, height, cell):
        cv2.line(canvas, (0, y), (width, y), line, 1)
    return canvas


# ── Glassmorphism panel ───────────────────────────────────────────────────────

def draw_glass_panel(img, x, y, w, h,
                     alpha=0.72,
                     bg=(15, 10, 38),
                     border=(110, 65, 160)):
    """Overlay a frosted-glass–style semi-transparent panel."""
    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), bg, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    # Outer border
    cv2.rectangle(img, (x, y), (x + w, y + h), border, 1)
    # Inner highlight edge (top + left gives 3-D lift)
    cv2.line(img, (x + 1, y + 1), (x + w - 2, y + 1), (190, 150, 220), 1)
    cv2.line(img, (x + 1, y + 1), (x + 1,     y + h - 2), (190, 150, 220), 1)


# ── Buttons ───────────────────────────────────────────────────────────────────

def draw_button(img, x, y, w, h, label, color,
                active=False, proximity=0.0):
    """
    Draw a labelled button.
    active    : highlights with outer glow
    proximity : 0‥1  — brightens as the finger approaches
    """
    boost   = int(proximity * 60)
    display = tuple(min(255, c + boost) for c in color)
    cv2.rectangle(img, (x, y), (x + w, y + h), display, -1)

    if active:
        glow = tuple(min(255, c + 130) for c in color)
        cv2.rectangle(img, (x - 3, y - 3), (x + w + 3, y + h + 3), (255, 255, 255), 2)
        cv2.rectangle(img, (x - 1, y - 1), (x + w + 1, y + h + 1), glow, 2)
    else:
        cv2.rectangle(img, (x, y), (x + w, y + h), (165, 130, 200), 1)

    font  = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.56
    (tw, th), _ = cv2.getTextSize(label, font, scale, 2)
    tx = x + (w - tw) // 2
    ty = y + (h + th) // 2
    # Drop shadow then label
    cv2.putText(img, label, (tx + 1, ty + 1), font, scale, (0,   0,   0), 2)
    cv2.putText(img, label, (tx,     ty),     font, scale, (255, 255, 255), 1)


def draw_separator(img, x, y, w, color=(80, 60, 110)):
    """Draw a thin horizontal rule across a panel."""
    cv2.line(img, (x + 4, y), (x + w - 4, y), color, 1)


# ── Cursor ────────────────────────────────────────────────────────────────────

def draw_cursor(img, cx, cy, tool, size, color):
    """
    Draw a context-aware cursor ring showing tool type, size, and colour.
    """
    r = max(8, size // 2)

    if tool == "eraser":
        cv2.circle(img, (cx, cy), r, (200, 200, 200), 2)
        cv2.circle(img, (cx, cy), r, (0,   0,   0),   1)

    elif tool == "spray":
        # Dashed ring
        segs = 12
        for i in range(segs):
            if i % 2 == 0:
                a1 = math.radians(i * (360 / segs))
                a2 = math.radians((i + 1) * (360 / segs))
                for a in np.linspace(a1, a2, 6):
                    px = int(cx + r * math.cos(a))
                    py = int(cy + r * math.sin(a))
                    cv2.circle(img, (px, py), 1, color, -1)

    elif tool in ("rainbow", "neon"):
        cv2.circle(img, (cx, cy), r + 4, (255, 255, 255), 1)
        cv2.circle(img, (cx, cy), r,     color,           2)

    elif tool == "mirror":
        cv2.circle(img, (cx, cy), r, color, 2)
        # Vertical symmetry axis hint
        cv2.line(img, (cx, cy - r - 5), (cx, cy + r + 5), (255, 255, 255), 1)

    else:  # brush / fill / shape
        cv2.circle(img, (cx, cy), r, (255, 255, 255), 2)
        cv2.circle(img, (cx, cy), r, color,           1)

    # Crosshair dot
    cv2.circle(img, (cx, cy), 2, (255, 255, 255), -1)


# ── Shapes ────────────────────────────────────────────────────────────────────

def draw_shape(canvas, shape_type, start, end, color, thickness=2):
    """Draw a geometric shape from *start* to *end* on *canvas*."""
    if shape_type == "Circle":
        cx = (start[0] + end[0]) // 2
        cy = (start[1] + end[1]) // 2
        r  = int(math.sqrt((end[0] - start[0]) ** 2 +
                            (end[1] - start[1]) ** 2) // 2)
        cv2.circle(canvas, (cx, cy), max(1, r), color, thickness)

    elif shape_type == "Rectangle":
        cv2.rectangle(canvas, start, end, color, thickness)

    elif shape_type == "Triangle":
        x1, y1 = start
        x2, y2 = end
        pts = np.array([[x1, y2], [x2, y2], [(x1 + x2) // 2, y1]], np.int32)
        cv2.polylines(canvas, [pts], True, color, thickness)

    elif shape_type == "Line":
        cv2.line(canvas, start, end, color, thickness)
