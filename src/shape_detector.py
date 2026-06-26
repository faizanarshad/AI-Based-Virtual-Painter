import math
import cv2


class ShapeDetector:
    """Detects whether a set of freehand stroke points form a circle or rectangle
    and redraws them as a clean geometric shape."""

    @staticmethod
    def detect(points, tolerance=0.1):
        """Return 'circle', 'rectangle', or None."""
        if len(points) < 3:
            return None

        distances = [
            math.sqrt((points[i + 1][0] - points[i][0]) ** 2 + (points[i + 1][1] - points[i][1]) ** 2)
            for i in range(len(points) - 1)
        ]

        # Circle: many points with similar step distances (closed stroke)
        if len(points) >= 8:
            avg = sum(distances) / len(distances)
            if avg > 0:
                variance = sum((d - avg) ** 2 for d in distances) / len(distances)
                if variance < avg * tolerance:
                    return "circle"

        # Rectangle: exactly 4 corner points with roughly 90-degree angles
        if len(points) == 4:
            angles = []
            for i in range(4):
                p1, p2, p3 = points[i], points[(i + 1) % 4], points[(i + 2) % 4]
                v1 = (p1[0] - p2[0], p1[1] - p2[1])
                v2 = (p3[0] - p2[0], p3[1] - p2[1])
                dot = v1[0] * v2[0] + v1[1] * v2[1]
                mag1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
                mag2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)
                if mag1 > 0 and mag2 > 0:
                    cos_a = max(-1.0, min(1.0, dot / (mag1 * mag2)))
                    angles.append(math.acos(cos_a))
            if all(abs(a - math.pi / 2) < 0.3 for a in angles):
                return "rectangle"

        return None

    @staticmethod
    def complete(shape_type, points, canvas, color, thickness):
        """Draw the snapped shape onto *canvas*. Returns True on success."""
        if shape_type == "circle":
            cx = sum(p[0] for p in points) // len(points)
            cy = sum(p[1] for p in points) // len(points)
            radius = int(
                sum(math.sqrt((p[0] - cx) ** 2 + (p[1] - cy) ** 2) for p in points) / len(points)
            )
            cv2.circle(canvas, (cx, cy), radius, color, thickness)
            return True

        if shape_type == "rectangle":
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            cv2.rectangle(canvas, (min(xs), min(ys)), (max(xs), max(ys)), color, thickness)
            return True

        return False
