"""
Vision processing module for froth flotation control system.

Provides camera interface, image preprocessing, bubble detection, and froth analysis.
"""

from .camera import Camera, robust_camera_init
from .preprocessor import ImagePreprocessor, preprocess_frame
from .bubble_detector import BubbleDetector
from .froth_analyzer import FrothAnalyzer

__all__ = [
    'Camera',
    'robust_camera_init',
    'ImagePreprocessor',
    'preprocess_frame',
    'BubbleDetector',
    'FrothAnalyzer',
]

__version__ = '1.0.0'
