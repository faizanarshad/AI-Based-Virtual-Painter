from .hand_detector import HandDetector
from .shape_detector import ShapeDetector
from .ui_utils import create_gradient, draw_button, draw_shape

try:
    from .voice_controller import VoiceController
    VOICE_AVAILABLE = True
except (ImportError, RuntimeError):
    VoiceController = None
    VOICE_AVAILABLE = False

__all__ = [
    "HandDetector",
    "ShapeDetector",
    "VoiceController",
    "VOICE_AVAILABLE",
    "create_gradient",
    "draw_button",
    "draw_shape",
]
