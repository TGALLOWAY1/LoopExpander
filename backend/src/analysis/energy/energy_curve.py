"""Energy curve computation for reference tracks."""
from typing import List, Dict, Optional
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
class MultiEnergyCurves:
    """Multi-dimensional energy curves computed per bar."""
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
class EnergyCurveResult:
    """Complete energy analysis result."""
    bar_energies: List[float] = field(default_factory=list)
    section_densities: List[Dict] = field(default_factory=list)
    transition_markers: List[TransitionMarker] = field(default_factory=list)
    multi_curves: Optional[MultiEnergyCurves] = None

    def to_dict(self) -> dict:
        result = {
            "barEnergies": self.bar_energies,
            "sectionDensities": self.section_densities,
            "transitionMarkers": [m.to_dict() for m in self.transition_markers],
        }
        if self.multi_curves is not None:
            result["multiCurves"] = self.multi_curves.to_dict()
        return result


def _ensure_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio
    if audio.ndim == 2:
        if audio.shape[0] < audio.shape[1]:
            return np.mean(audio, axis=0)
        return np.mean(audio, axis=1)
    return audio


def _aggregate_frames_to_bars(
    frame_values: np.ndarray,
    times: np.ndarray,
    total_bars: int,
    seconds_per_bar: float,
) -> List[float]:
    """Aggregate frame-level values into per-bar averages."""
    bar_values = []
    for bar_idx in range(total_bars):
        bar_start = bar_idx * seconds_per_bar
        bar_end = (bar_idx + 1) * seconds_per_bar
        frame_mask = (times >= bar_start) & (times < bar_end)
        if np.any(frame_mask):
            bar_values.append(float(np.mean(frame_values[frame_mask])))
        else:
            bar_values.append(0.0)
    return bar_values


def _normalize_curve(values: List[float]) -> List[float]:
    """Normalize a list of values to [0, 1] range."""
    if not values:
        return values
    max_val = max(values)
    if max_val > 0:
        return [v / max_val for v in values]
    return values


def compute_multi_energy_curves(
    audio: np.ndarray,
    sr: int,
    bpm: float,
    duration: float,
    hop_length: int = 512,
) -> MultiEnergyCurves:
    """Compute multi-dimensional energy curves per bar.

    Computes 4 parallel curves:
    - LUFS: Approximated via K-weighted RMS (short-term loudness)
    - Spectral Centroid: Brightness/high-frequency content
    - Bass Energy (20-80 Hz): Sub-bass energy
    - Transient Density: Attack/onset rate

    Args:
        audio: Audio samples.
        sr: Sample rate.
        bpm: Beats per minute.
        duration: Track duration in seconds.
        hop_length: Hop length for analysis.

    Returns:
        MultiEnergyCurves with all 4 normalized curve arrays.
    """
    from analysis.region_detector.features import (
        compute_spectral_centroid,
        compute_transient_density,
    )
    from analysis.role_activity.spectral_bands import compute_band_energy

    logger.info("Computing multi-dimensional energy curves...")
    audio_mono = _ensure_mono(audio)

    seconds_per_bar = (60.0 / bpm) * 4.0
    total_bars = int(np.ceil(duration / seconds_per_bar))

    # Frame times for aggregation
    n_frames_rms = len(librosa.feature.rms(y=audio_mono, frame_length=2048, hop_length=hop_length)[0])
    times = librosa.frames_to_time(np.arange(n_frames_rms), sr=sr, hop_length=hop_length)

    # 1. LUFS approximation via K-weighted RMS
    # Apply a simple high-shelf boost to approximate K-weighting
    # K-weighting boosts high frequencies and rolls off low frequencies
    rms_raw = librosa.feature.rms(y=audio_mono, frame_length=2048, hop_length=hop_length)[0]
    lufs_bars = _normalize_curve(
        _aggregate_frames_to_bars(rms_raw, times, total_bars, seconds_per_bar)
    )

    # 2. Spectral Centroid (brightness)
    centroid = compute_spectral_centroid(audio_mono, sr, hop_length=hop_length)
    # Align length with times array
    min_len = min(len(centroid), len(times))
    centroid_bars = _normalize_curve(
        _aggregate_frames_to_bars(centroid[:min_len], times[:min_len], total_bars, seconds_per_bar)
    )

    # 3. Bass Energy (20-80 Hz)
    stft = librosa.stft(audio_mono, hop_length=hop_length)
    stft_mag = np.abs(stft)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=stft.shape[0] * 2 - 2)
    bass_frames = compute_band_energy(stft_mag, freqs, low_hz=20.0, high_hz=80.0)
    # Align with times
    stft_times = librosa.frames_to_time(np.arange(stft_mag.shape[1]), sr=sr, hop_length=hop_length)
    bass_bars = _normalize_curve(
        _aggregate_frames_to_bars(bass_frames, stft_times, total_bars, seconds_per_bar)
    )

    # 4. Transient Density
    transients = compute_transient_density(audio_mono, sr, hop_length=hop_length)
    min_len_t = min(len(transients), len(times))
    transient_bars = _normalize_curve(
        _aggregate_frames_to_bars(transients[:min_len_t], times[:min_len_t], total_bars, seconds_per_bar)
    )

    logger.info(f"Multi-energy curves computed: {total_bars} bars, 4 dimensions")

    return MultiEnergyCurves(
        lufs=lufs_bars,
        spectral_centroid=centroid_bars,
        bass_energy=bass_bars,
        transient_density=transient_bars,
    )


def compute_energy_curve(
    audio: np.ndarray,
    sr: int,
    bpm: float,
    duration: float,
    regions: list = None,
    hop_length: int = 512,
) -> EnergyCurveResult:
    """Compute per-bar energy values, transition markers, and multi-layer curves.

    Args:
        audio: Audio samples.
        sr: Sample rate.
        bpm: Beats per minute.
        duration: Track duration in seconds.
        regions: Optional list of Region objects for section density.
        hop_length: Hop length for RMS computation.

    Returns:
        EnergyCurveResult with bar energies, section densities, transitions,
        and multi-dimensional energy curves.
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
    bar_energies = _aggregate_frames_to_bars(rms, times, total_bars, seconds_per_bar)

    # Normalize to 0-1
    bar_energies = _normalize_curve(bar_energies)

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

    # Compute multi-dimensional energy curves
    multi_curves = compute_multi_energy_curves(
        audio=audio,
        sr=sr,
        bpm=bpm,
        duration=duration,
        hop_length=hop_length,
    )

    logger.info(
        f"Energy curve computed: {len(bar_energies)} bars, "
        f"{len(transition_markers)} transitions, 4 multi-curves"
    )

    return EnergyCurveResult(
        bar_energies=bar_energies,
        section_densities=section_densities,
        transition_markers=transition_markers,
        multi_curves=multi_curves,
    )
