"""Configuration for motif detection sensitivity per stem."""
try:
    from typing import TypedDict, Literal, Mapping
except ImportError:
    # Python < 3.8 compatibility
    from typing_extensions import TypedDict, Literal
    from typing import Mapping

StemCategory = Literal["drums", "bass", "vocals", "instruments"]

class MotifSensitivityConfig(TypedDict, total=False):
    """Configuration for motif detection sensitivity per stem category.
    
    Higher sensitivity values = more tolerant grouping (looser clustering, fewer groups)
    Lower sensitivity values = stricter grouping (tighter clustering, more groups)
    
    Values should be in the range [0.0, 1.0]:
    - 0.0: Very strict, only very similar motifs are grouped together
    - 1.0: Very loose, many different motifs are grouped together
    
    Note: Values are clamped to [0.05, 0.95] to prevent extreme values that could
    lead to no motifs being detected or everything being grouped together.
    """
    drums: float
    bass: float
    vocals: float
    instruments: float

DEFAULT_MOTIF_SENSITIVITY: MotifSensitivityConfig = {
    "drums": 0.5,
    "bass": 0.5,
    "vocals": 0.5,
    "instruments": 0.5,
}


def clamp_sensitivity(value: float, min_val: float = 0.05, max_val: float = 0.95) -> float:
    """
    Clamp motif sensitivity to a safe range. Extremely low or high values
    can lead to no motifs being detected or everything being grouped.
    
    Args:
        value: Raw sensitivity value (may be outside safe range)
        min_val: Minimum allowed value (default: 0.05)
        max_val: Maximum allowed value (default: 0.95)
    
    Returns:
        Clamped value in range [min_val, max_val]
    """
    return max(min_val, min(max_val, value))


def normalize_sensitivity_config(cfg: Mapping[str, float]) -> MotifSensitivityConfig:
    """
    Normalize a sensitivity configuration dictionary by clamping all values
    to a safe range and ensuring all required keys are present.
    
    Args:
        cfg: Configuration dictionary (may have missing keys or extreme values)
    
    Returns:
        Normalized MotifSensitivityConfig with all values clamped to [0.05, 0.95]
    """
    normalized: MotifSensitivityConfig = {}
    for key in ("drums", "bass", "vocals", "instruments"):
        raw = cfg.get(key, DEFAULT_MOTIF_SENSITIVITY[key])
        normalized[key] = clamp_sensitivity(float(raw))
    return normalized

