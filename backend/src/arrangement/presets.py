"""Genre-based arrangement presets defining structure templates.

Each preset specifies:
- Region order (section types in sequence)
- Region lengths in bars
- Density curve (how many roles should be active per section)
- Role activity hints (which roles should be active/muted per section type)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class PresetSection:
    """A section template within a genre preset."""
    type: str  # intro, verse, chorus, bridge, drop, breakdown, build, outro
    label: str
    bars: int
    density: float  # 0.0-1.0, how many roles should be active
    active_roles: List[str] = field(default_factory=list)  # roles that should be on
    muted_roles: List[str] = field(default_factory=list)  # roles that should be off


@dataclass
class ArrangementPreset:
    """A genre-based arrangement template."""
    id: str
    name: str
    genre: str
    description: str
    bpm_range: tuple  # (min_bpm, max_bpm) typical for genre
    sections: List[PresetSection] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "genre": self.genre,
            "description": self.description,
            "bpmRange": list(self.bpm_range),
            "sections": [
                {
                    "type": s.type,
                    "label": s.label,
                    "bars": s.bars,
                    "density": s.density,
                    "activeRoles": s.active_roles,
                    "mutedRoles": s.muted_roles,
                }
                for s in self.sections
            ],
        }


# ── Genre Presets ──────────────────────────────────────────────

PRESET_FUTURE_BASS = ArrangementPreset(
    id="future_bass",
    name="Future Bass",
    genre="Future Bass",
    description="Bright, emotional drops with heavy sidechain. Builds → drops with vocal chops.",
    bpm_range=(140, 160),
    sections=[
        PresetSection("intro", "Intro", 8, 0.3, ["melodic", "vocal"], ["drums", "bass"]),
        PresetSection("verse", "Verse 1", 16, 0.5, ["drums", "melodic", "vocal"], ["bass"]),
        PresetSection("build", "Build 1", 8, 0.6, ["drums", "melodic", "vocal"], []),
        PresetSection("drop", "Drop 1", 16, 1.0, ["drums", "bass", "melodic", "vocal"], []),
        PresetSection("breakdown", "Breakdown", 8, 0.3, ["melodic", "vocal"], ["drums", "bass"]),
        PresetSection("build", "Build 2", 8, 0.6, ["drums", "melodic", "vocal"], []),
        PresetSection("drop", "Drop 2", 16, 1.0, ["drums", "bass", "melodic", "vocal"], []),
        PresetSection("outro", "Outro", 8, 0.3, ["melodic"], ["drums", "bass"]),
    ],
)

PRESET_DUBSTEP = ArrangementPreset(
    id="dubstep",
    name="Dubstep",
    genre="Dubstep",
    description="Heavy bass drops with half-time drums. Long builds into aggressive drops.",
    bpm_range=(140, 150),
    sections=[
        PresetSection("intro", "Intro", 16, 0.3, ["melodic"], ["drums", "bass"]),
        PresetSection("build", "Build 1", 16, 0.5, ["drums", "melodic"], ["bass"]),
        PresetSection("drop", "Drop 1", 16, 1.0, ["drums", "bass", "melodic"], []),
        PresetSection("breakdown", "Breakdown 1", 8, 0.2, ["melodic"], ["drums", "bass"]),
        PresetSection("drop", "Drop 1B", 16, 1.0, ["drums", "bass", "melodic"], []),
        PresetSection("breakdown", "Breakdown 2", 16, 0.3, ["melodic", "vocal"], ["drums", "bass"]),
        PresetSection("build", "Build 2", 16, 0.5, ["drums", "melodic"], ["bass"]),
        PresetSection("drop", "Drop 2", 16, 1.0, ["drums", "bass", "melodic"], []),
        PresetSection("outro", "Outro", 8, 0.2, ["melodic"], ["drums", "bass"]),
    ],
)

PRESET_TRAP = ArrangementPreset(
    id="trap",
    name="Trap",
    genre="Trap",
    description="808-heavy with hi-hat rolls. Verse-hook structure with sparse breakdowns.",
    bpm_range=(130, 170),
    sections=[
        PresetSection("intro", "Intro", 8, 0.3, ["melodic"], ["drums", "bass"]),
        PresetSection("verse", "Verse 1", 16, 0.6, ["drums", "bass", "melodic"], []),
        PresetSection("chorus", "Hook", 8, 0.9, ["drums", "bass", "melodic", "vocal"], []),
        PresetSection("verse", "Verse 2", 16, 0.6, ["drums", "bass", "melodic"], []),
        PresetSection("chorus", "Hook", 8, 0.9, ["drums", "bass", "melodic", "vocal"], []),
        PresetSection("bridge", "Bridge", 8, 0.4, ["melodic", "vocal"], ["drums"]),
        PresetSection("chorus", "Hook (Final)", 8, 1.0, ["drums", "bass", "melodic", "vocal"], []),
        PresetSection("outro", "Outro", 8, 0.3, ["melodic"], ["drums", "bass"]),
    ],
)

PRESET_POP = ArrangementPreset(
    id="pop",
    name="Pop",
    genre="Pop",
    description="Classic verse-chorus structure with bridge. Clean arrangement with dynamic builds.",
    bpm_range=(100, 130),
    sections=[
        PresetSection("intro", "Intro", 8, 0.3, ["melodic"], ["drums", "bass"]),
        PresetSection("verse", "Verse 1", 16, 0.5, ["drums", "bass", "melodic"], []),
        PresetSection("chorus", "Chorus 1", 16, 0.8, ["drums", "bass", "melodic", "vocal"], []),
        PresetSection("verse", "Verse 2", 16, 0.6, ["drums", "bass", "melodic"], []),
        PresetSection("chorus", "Chorus 2", 16, 0.9, ["drums", "bass", "melodic", "vocal"], []),
        PresetSection("bridge", "Bridge", 8, 0.4, ["melodic", "vocal"], ["drums", "bass"]),
        PresetSection("chorus", "Final Chorus", 16, 1.0, ["drums", "bass", "melodic", "vocal"], []),
        PresetSection("outro", "Outro", 8, 0.3, ["melodic"], ["drums", "bass"]),
    ],
)

PRESET_HOUSE = ArrangementPreset(
    id="house",
    name="House",
    genre="House",
    description="Four-on-the-floor with gradual layering. Long builds and filtered breakdowns.",
    bpm_range=(120, 130),
    sections=[
        PresetSection("intro", "Intro", 16, 0.3, ["drums"], ["bass", "melodic"]),
        PresetSection("build", "Build 1", 16, 0.5, ["drums", "bass"], ["melodic"]),
        PresetSection("drop", "Drop 1", 32, 0.9, ["drums", "bass", "melodic", "vocal"], []),
        PresetSection("breakdown", "Breakdown", 16, 0.3, ["melodic", "vocal"], ["drums", "bass"]),
        PresetSection("build", "Build 2", 16, 0.6, ["drums", "bass", "melodic"], []),
        PresetSection("drop", "Drop 2", 32, 1.0, ["drums", "bass", "melodic", "vocal"], []),
        PresetSection("outro", "Outro", 16, 0.3, ["drums"], ["bass", "melodic"]),
    ],
)

# Registry of all available presets
PRESETS: Dict[str, ArrangementPreset] = {
    p.id: p
    for p in [
        PRESET_FUTURE_BASS,
        PRESET_DUBSTEP,
        PRESET_TRAP,
        PRESET_POP,
        PRESET_HOUSE,
    ]
}


def get_preset(preset_id: str) -> Optional[ArrangementPreset]:
    """Get a preset by ID."""
    return PRESETS.get(preset_id)


def list_presets() -> List[ArrangementPreset]:
    """Get all available presets."""
    return list(PRESETS.values())
