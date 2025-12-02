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


def get_settings() -> dict:
    """Get application settings as a dictionary."""
    return {
        "app_name": APP_NAME,
        "log_level": LOG_LEVEL,
    }

