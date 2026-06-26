"""
AI shape detector — converts freehand strokes into clean geometric shapes.

Detection strategy (data-driven):
  At tight epsilon, a freehand circle hull → 6-8 vertices
  A freehand rectangle hull              → 4 vertices
  A freehand triangle hull               → 3 vertices

  So: run approxPolyDP at tight epsilon first.
  • 3 verts → triangle
  • 4 verts → rectangle
  • 5+ verts → fallback min-enclosing-circle test → circle or None
"""

import math
import cv2
import numpy as np


class ShapeDetector:

    @staticmethod
    def detect(points, min_size=30):
        """
        Return 'circle', 'rectangle', 'triangle', or None.

        Parameters
        ----------
        points   : list of (x, y) tuples collected during the stroke
        min_size : ignore shapes whose bounding box is smaller than this
        """
        if len(points) < 10:
            return None

        pts = np.array(points, dtype=np.int32)
        _, _, bw, bh = cv2.boundingRect(pts)
        if bw < min_size and bh < min_size:
            return None

        hull = cv2.convexHull(pts)
        peri = cv2.arcLength(hull, closed=True)
        if peri == 0:
            return None

        # ── Step 1: polygon test at tight epsilon ─────────────────────────
        approx = cv2.approxPolyDP(hull, 0.04 * peri, closed=True)
        n = len(approx)

        if n == 3:
            return "triangle"

        if n == 4:
            _, _, aw, ah = cv2.boundingRect(approx)
            if aw > min_size and ah > min_size:
                return "rectangle"

        # ── Step 2: circle fallback (5+ polygon vertices) ─────────────────
        # Check how closely all stroke points hug their min-enclosing circle.
        if n >= 5:
            (cx, cy), radius = cv2.minEnclosingCircle(pts)
            if radius > min_size:
                deviations = [
                    abs(math.sqrt((p[0] - cx) ** 2 + (p[1] - cy) ** 2) - radius)
                    for p in points
                ]
                avg_dev = sum(deviations) / len(deviations)
                if avg_dev / radius < 0.25:
                    return "circle"

        return None

    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def complete(shape_type, points, canvas, color, thickness):
        """Draw the clean snapped shape onto *canvas*. Returns True on success."""
        pts = np.array(points, dtype=np.int32)

        if shape_type == "circle":
            (cx, cy), radius = cv2.minEnclosingCircle(pts)
            cv2.circle(canvas,
                       (int(cx), int(cy)), max(1, int(radius)),
                       color, thickness)
            return True

        if shape_type == "rectangle":
            x, y, w, h = cv2.boundingRect(pts)
            cv2.rectangle(canvas, (x, y), (x + w, y + h), color, thickness)
            return True

        if shape_type == "triangle":
            hull   = cv2.convexHull(pts)
            peri   = cv2.arcLength(hull, closed=True)
            approx = cv2.approxPolyDP(hull, 0.07 * peri, closed=True)
            cv2.polylines(canvas, [approx], True, color, thickness)
            return True

        return False
