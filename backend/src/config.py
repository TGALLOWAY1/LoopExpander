"""Configuration module for Song Structure Replicator."""
import os
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


APP_NAME = "Song Structure Replicator"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Region detection thresholds
MIN_BOUNDARY_GAP_SEC = float(os.environ.get("MIN_BOUNDARY_GAP_SEC", "4.0"))
MIN_REGION_DURATION_SEC = float(os.environ.get("MIN_REGION_DURATION_SEC", "8.0"))

# Motif detection parameters
DEFAULT_MOTIF_SENSITIVITY = float(os.environ.get("DEFAULT_MOTIF_SENSITIVITY", "0.5"))
DEFAULT_MOTIF_BARS = float(os.environ.get("DEFAULT_MOTIF_BARS", "2.0"))
DEFAULT_MOTIF_HOP_BARS = float(os.environ.get("DEFAULT_MOTIF_HOP_BARS", "1.0"))

# Call-response detection parameters
DEFAULT_CALL_RESPONSE_MIN_OFFSET_BARS = float(os.environ.get("DEFAULT_CALL_RESPONSE_MIN_OFFSET_BARS", "0.5"))
DEFAULT_CALL_RESPONSE_MAX_OFFSET_BARS = float(os.environ.get("DEFAULT_CALL_RESPONSE_MAX_OFFSET_BARS", "4.0"))
DEFAULT_CALL_RESPONSE_MIN_SIMILARITY = float(os.environ.get("DEFAULT_CALL_RESPONSE_MIN_SIMILARITY", "0.7"))
DEFAULT_CALL_RESPONSE_MIN_CONFIDENCE = float(os.environ.get("DEFAULT_CALL_RESPONSE_MIN_CONFIDENCE", "0.5"))

# Fill detection parameters
DEFAULT_FILL_PRE_BOUNDARY_WINDOW_BARS = float(os.environ.get("DEFAULT_FILL_PRE_BOUNDARY_WINDOW_BARS", "2.0"))
DEFAULT_FILL_TRANSIENT_DENSITY_THRESHOLD_MULTIPLIER = float(os.environ.get("DEFAULT_FILL_TRANSIENT_DENSITY_THRESHOLD_MULTIPLIER", "1.5"))
DEFAULT_FILL_MIN_TRANSIENT_DENSITY = float(os.environ.get("DEFAULT_FILL_MIN_TRANSIENT_DENSITY", "0.3"))

# Subregion analysis parameters
DEFAULT_SUBREGION_BARS_PER_CHUNK = int(os.environ.get("DEFAULT_SUBREGION_BARS_PER_CHUNK", "2"))
DEFAULT_SUBREGION_SILENCE_INTENSITY_THRESHOLD = float(os.environ.get("DEFAULT_SUBREGION_SILENCE_INTENSITY_THRESHOLD", "0.15"))


def get_settings() -> dict:
    """Get application settings as a dictionary."""
    return {
        "app_name": APP_NAME,
        "log_level": LOG_LEVEL,
    }

