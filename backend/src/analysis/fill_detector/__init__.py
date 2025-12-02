"""Fill detection module for identifying transient-rich regions near boundaries."""
from .fill_detector import (
    Fill,
    FillConfig,
    detect_fills
)

__all__ = [
    "Fill",
    "FillConfig",
    "detect_fills"
]

