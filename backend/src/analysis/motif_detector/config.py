"""Configuration for motif detection sensitivity per stem."""
from typing import TypedDict, Literal

StemCategory = Literal["drums", "bass", "vocals", "instruments"]

class MotifSensitivityConfig(TypedDict, total=False):
    """Configuration for motif detection sensitivity per stem category.
    
    Higher sensitivity values = more tolerant grouping (looser clustering, fewer groups)
    Lower sensitivity values = stricter grouping (tighter clustering, more groups)
    
    Values should be in the range [0.0, 1.0]:
    - 0.0: Very strict, only very similar motifs are grouped together
    - 1.0: Very loose, many different motifs are grouped together
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

