"""
Visual drawing effects: spray paint, neon glow, mirror stroke, rainbow colour.
"""

import math
import random
import time

import cv2
import numpy as np


def spray_paint(canvas, cx, cy, color, radius=30, density=45):
    """Spray semi-random dots in a circle — denser toward the centre."""
    h, w = canvas.shape[:2]
    for _ in range(density):
        angle = random.uniform(0, 2 * math.pi)
        # Square-root distribution → denser core
        r = random.random() ** 0.5 * radius
        x = int(cx + r * math.cos(angle))
        y = int(cy + r * math.sin(angle))
        if 0 <= x < w and 0 <= y < h:
            cv2.circle(canvas, (x, y), random.randint(1, 2), color, -1)


def neon_stroke(canvas, p1, p2, color, thickness):
    """Additive neon glow: wide soft halo → tight glow → crisp core → white centre."""
    # Wide halo
    halo = np.zeros_like(canvas)
    cv2.line(halo, p1, p2, color, thickness + 14)
    halo = cv2.GaussianBlur(halo, (19, 19), 0)
    canvas[:] = cv2.add(canvas, halo)

    # Mid glow
    mid = np.zeros_like(canvas)
    cv2.line(mid, p1, p2, color, thickness + 5)
    mid = cv2.GaussianBlur(mid, (7, 7), 0)
    canvas[:] = cv2.add(canvas, mid)

    # Crisp stroke
    cv2.line(canvas, p1, p2, color, thickness)

    # Bright white core
    bright = tuple(min(255, c + 190) for c in color)
    cv2.line(canvas, p1, p2, bright, max(1, thickness // 2))


def mirror_stroke(canvas, p1, p2, color, thickness):
    """Draw a stroke and its horizontal mirror simultaneously."""
    cw = canvas.shape[1]
    cv2.line(canvas, p1, p2, color, thickness)
    mp1 = (cw - 1 - p1[0], p1[1])
    mp2 = (cw - 1 - p2[0], p2[1])
    cv2.line(canvas, mp1, mp2, color, thickness)
    return mp1, mp2


def rainbow_color(t=None):
    """Return a vivid cycling BGR colour based on time (full saturation HSV)."""
    if t is None:
        t = time.time()
    hue = int((t * 45) % 180)
    bgr = cv2.cvtColor(np.uint8([[[hue, 255, 255]]]), cv2.COLOR_HSV2BGR)[0][0]
    return (int(bgr[0]), int(bgr[1]), int(bgr[2]))
