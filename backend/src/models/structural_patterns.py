"""Unified structural pattern data model combining all analysis results."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class LoopInstance:
    """An exact repetition of a motif pattern."""
    motif_id: str
    group_id: str
    stem_role: str
    start_time: float
    end_time: float
    similarity_type: str  # "exact" | "variation" | "unique"

    def to_dict(self) -> dict:
        return {
            "motifId": self.motif_id,
            "groupId": self.group_id,
            "stemRole": self.stem_role,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "similarityType": self.similarity_type,
        }


@dataclass
class MotifGroupSummary:
    """Summary of a motif group with member counts."""
    id: str
    member_count: int
    exact_count: int
    variation_count: int
    stem_role: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "memberCount": self.member_count,
            "exactCount": self.exact_count,
            "variationCount": self.variation_count,
            "stemRole": self.stem_role,
        }


@dataclass
class CallResponsePairSummary:
    """Summary of a call-response pair."""
    id: str
    from_stem: str
    to_stem: str
    from_time: float
    to_time: float
    time_offset: float
    confidence: float
    region_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "fromStem": self.from_stem,
            "toStem": self.to_stem,
            "fromTime": self.from_time,
            "toTime": self.to_time,
            "timeOffset": self.time_offset,
            "confidence": self.confidence,
            "regionId": self.region_id,
        }


@dataclass
class RegionSummary:
    """Summary of a detected region."""
    id: str
    name: str
    type: str
    start: float
    end: float
    start_bar: float
    end_bar: float
    label: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "start": self.start,
            "end": self.end,
            "startBar": self.start_bar,
            "endBar": self.end_bar,
            "label": self.label,
        }


@dataclass
class MultiEnergyCurvesSummary:
    """Multi-dimensional energy curves."""
    lufs: List[float] = field(default_factory=list)
    spectral_centroid: List[float] = field(default_factory=list)
    bass_energy: List[float] = field(default_factory=list)
    transient_density: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lufs": self.lufs,
            "spectralCentroid": self.spectral_centroid,
            "bassEnergy": self.bass_energy,
            "transientDensity": self.transient_density,
        }


@dataclass
class RegionTonalBalanceSummary:
    """Tonal balance for a single region."""
    region_id: str
    low: float
    low_mid: float
    mid: float
    high_mid: float
    high: float

    def to_dict(self) -> dict:
        return {
            "regionId": self.region_id,
            "low": self.low,
            "lowMid": self.low_mid,
            "mid": self.mid,
            "highMid": self.high_mid,
            "high": self.high,
        }


@dataclass
class StructuralPatternBundle:
    """Unified model combining all structural analysis results."""
    loops: List[LoopInstance] = field(default_factory=list)
    motif_groups: List[MotifGroupSummary] = field(default_factory=list)
    call_response_pairs: List[CallResponsePairSummary] = field(default_factory=list)
    regions: List[RegionSummary] = field(default_factory=list)
    energy_curves: Optional[MultiEnergyCurvesSummary] = None
    tonal_balance: List[RegionTonalBalanceSummary] = field(default_factory=list)
    bar_energies: List[float] = field(default_factory=list)
    total_bars: int = 0

    def to_dict(self) -> dict:
        return {
            "loops": [l.to_dict() for l in self.loops],
            "motifGroups": [g.to_dict() for g in self.motif_groups],
            "callResponsePairs": [p.to_dict() for p in self.call_response_pairs],
            "regions": [r.to_dict() for r in self.regions],
            "energyCurves": self.energy_curves.to_dict() if self.energy_curves else None,
            "tonalBalance": [t.to_dict() for t in self.tonal_balance],
            "barEnergies": self.bar_energies,
            "totalBars": self.total_bars,
        }
