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


def get_settings() -> dict:
    """Get application settings as a dictionary."""
    return {
        "app_name": APP_NAME,
        "log_level": LOG_LEVEL,
    }

