"""Pydantic models for call/response lane visualization."""
from pydantic import BaseModel
from typing import Literal, List, Optional

StemCategory = Literal["drums", "bass", "instruments", "vocals"]


class StemCallResponseEvent(BaseModel):
    """A single call or response event in a stem lane."""
    id: str
    region_id: str
    stem: StemCategory
    start_bar: float
    end_bar: float
    role: Literal["call", "response"]
    group_id: str  # Groups calls + responses that belong together
    label: Optional[str] = None
    intensity: Optional[float] = None  # Optional density/energy


class StemCallResponseLane(BaseModel):
    """A lane containing call/response events for a specific stem."""
    stem: StemCategory
    events: List[StemCallResponseEvent]


class CallResponseByStemResponse(BaseModel):
    """Response containing call/response data organized by stem lanes."""
    reference_id: str
    regions: List[str]  # Region ids in timeline order
    lanes: List[StemCallResponseLane]

