"""Energy curve computation for reference tracks."""
from typing import List, Dict
from dataclasses import dataclass, field

import numpy as np
import librosa

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TransitionMarker:
    """A detected transition moment (large energy delta)."""
    bar: float
    time_seconds: float
    energy_delta: float
    type: str  # "lift", "drop", "breakdown"

    def to_dict(self) -> dict:
        return {
            "bar": self.bar,
            "timeSeconds": self.time_seconds,
            "energyDelta": self.energy_delta,
            "type": self.type,
        }


@dataclass
class EnergyCurveResult:
    """Complete energy analysis result."""
    bar_energies: List[float] = field(default_factory=list)
    section_densities: List[Dict] = field(default_factory=list)
    transition_markers: List[TransitionMarker] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "barEnergies": self.bar_energies,
            "sectionDensities": self.section_densities,
            "transitionMarkers": [m.to_dict() for m in self.transition_markers],
        }


def _ensure_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio
    if audio.ndim == 2:
        if audio.shape[0] < audio.shape[1]:
            return np.mean(audio, axis=0)
        return np.mean(audio, axis=1)
    return audio


def compute_energy_curve(
    audio: np.ndarray,
    sr: int,
    bpm: float,
    duration: float,
    regions: list = None,
    hop_length: int = 512,
) -> EnergyCurveResult:
    """Compute per-bar energy values and transition markers.

    Args:
        audio: Audio samples.
        sr: Sample rate.
        bpm: Beats per minute.
        duration: Track duration in seconds.
        regions: Optional list of Region objects for section density.
        hop_length: Hop length for RMS computation.

    Returns:
        EnergyCurveResult with bar energies, section densities, and transitions.
    """
    logger.info(f"Computing energy curve: bpm={bpm}, duration={duration:.1f}s")
    audio_mono = _ensure_mono(audio)

    # Compute RMS envelope
    rms = librosa.feature.rms(y=audio_mono, frame_length=2048, hop_length=hop_length)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

    # Compute bar timing
    seconds_per_beat = 60.0 / bpm
    seconds_per_bar = seconds_per_beat * 4.0
    total_bars = int(np.ceil(duration / seconds_per_bar))

    # Per-bar average energy
    bar_energies = []
    for bar_idx in range(total_bars):
        bar_start = bar_idx * seconds_per_bar
        bar_end = (bar_idx + 1) * seconds_per_bar
        frame_mask = (times >= bar_start) & (times < bar_end)
        if np.any(frame_mask):
            bar_energies.append(float(np.mean(rms[frame_mask])))
        else:
            bar_energies.append(0.0)

    # Normalize to 0-1
    max_energy = max(bar_energies) if bar_energies else 1.0
    if max_energy > 0:
        bar_energies = [e / max_energy for e in bar_energies]

    # Detect transition markers (large energy deltas between adjacent bars)
    transition_markers: List[TransitionMarker] = []
    if len(bar_energies) > 1:
        deltas = [bar_energies[i + 1] - bar_energies[i] for i in range(len(bar_energies) - 1)]
        delta_std = np.std(deltas) if len(deltas) > 1 else 0.1
        threshold = max(0.15, delta_std * 1.5)

        for i, delta in enumerate(deltas):
            bar_pos = float(i + 1)
            time_pos = bar_pos * seconds_per_bar
            if delta > threshold:
                marker_type = "lift"
                transition_markers.append(
                    TransitionMarker(
                        bar=bar_pos,
                        time_seconds=time_pos,
                        energy_delta=delta,
                        type=marker_type,
                    )
                )
            elif delta < -threshold:
                marker_type = "breakdown" if bar_energies[i + 1] < 0.3 else "drop"
                transition_markers.append(
                    TransitionMarker(
                        bar=bar_pos,
                        time_seconds=time_pos,
                        energy_delta=delta,
                        type=marker_type,
                    )
                )

    # Section-level density scores (if regions provided)
    section_densities: List[Dict] = []
    if regions:
        for region in regions:
            region_start_bar = region.start / seconds_per_bar
            region_end_bar = region.end / seconds_per_bar
            start_idx = max(0, int(region_start_bar))
            end_idx = min(len(bar_energies), int(np.ceil(region_end_bar)))
            if start_idx < end_idx:
                section_energy = bar_energies[start_idx:end_idx]
                density = float(np.mean(section_energy))
            else:
                density = 0.0
            section_densities.append({
                "regionId": region.id,
                "density": density,
                "meanEnergy": density,
            })

    logger.info(
        f"Energy curve computed: {len(bar_energies)} bars, "
        f"{len(transition_markers)} transitions"
    )

    return EnergyCurveResult(
        bar_energies=bar_energies,
        section_densities=section_densities,
        transition_markers=transition_markers,
    )
