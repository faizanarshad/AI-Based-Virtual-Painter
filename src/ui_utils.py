import math
import cv2
import numpy as np


def create_gradient(width, height, color1, color2, direction="horizontal"):
    """Return an (height, width, 3) uint8 gradient array."""
    bg = np.zeros((height, width, 3), dtype=np.uint8)
    if direction == "horizontal":
        for x in range(width):
            r = x / width
            bg[:, x] = tuple(int(color1[i] * (1 - r) + color2[i] * r) for i in range(3))
    else:
        for y in range(height):
            r = y / height
            bg[y, :] = tuple(int(color1[i] * (1 - r) + color2[i] * r) for i in range(3))
    return bg


def draw_button(img, x, y, w, h, label, color, active=False):
    """Draw a rounded-style button with optional active glow."""
    cv2.rectangle(img, (x, y), (x + w, y + h), color, -1)
    if active:
        cv2.rectangle(img, (x - 2, y - 2), (x + w + 2, y + h + 2), (255, 255, 255), 3)
    cv2.rectangle(img, (x, y), (x + w, y + h), (255, 255, 255), 2)
    tw, th = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
    cv2.putText(img, label, (x + (w - tw) // 2, y + (h + th) // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


def draw_shape(canvas, shape_type, start, end, color, thickness=2):
    """Draw a geometric shape from *start* to *end* on *canvas*."""
    if shape_type == "Circle":
        cx = (start[0] + end[0]) // 2
        cy = (start[1] + end[1]) // 2
        radius = int(math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) // 2)
        cv2.circle(canvas, (cx, cy), radius, color, thickness)

    elif shape_type == "Rectangle":
        cv2.rectangle(canvas, start, end, color, thickness)

    elif shape_type == "Triangle":
        x1, y1 = start
        x2, y2 = end
        pts = np.array([[x1, y2], [x2, y2], [(x1 + x2) // 2, y1]], np.int32)
        cv2.polylines(canvas, [pts], True, color, thickness)

    elif shape_type == "Line":
        cv2.line(canvas, start, end, color, thickness)
