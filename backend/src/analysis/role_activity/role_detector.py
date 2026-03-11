"""Broad role activity detection from a full mix."""
from typing import List

import numpy as np
import librosa

from models.role_activity import RoleActivityTimeline, ActivitySegment
from .spectral_bands import (
    compute_band_energy,
    compute_percussive_energy,
    compute_harmonic_ratio,
    compute_spectral_flatness_per_frame,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Frequency band boundaries
BASS_LOW_HZ = 20.0
BASS_HIGH_HZ = 250.0
MID_LOW_HZ = 250.0
MID_HIGH_HZ = 4000.0
MID_HIGH_LOW_HZ = 2000.0
MID_HIGH_HIGH_HZ = 8000.0

# Activity thresholds (relative to max energy)
DEFAULT_ACTIVITY_THRESHOLD = 0.15


def _ensure_mono(audio: np.ndarray) -> np.ndarray:
    """Convert to mono if needed."""
    if audio.ndim == 1:
        return audio
    if audio.ndim == 2:
        if audio.shape[0] < audio.shape[1]:
            return np.mean(audio, axis=0)
        return np.mean(audio, axis=1)
    return audio


def _smooth_curve(curve: np.ndarray, window: int = 21) -> np.ndarray:
    """Apply median + moving average smoothing."""
    if len(curve) < window:
        return curve
    # Median filter for spike removal
    from scipy.ndimage import median_filter
    smoothed = median_filter(curve, size=window)
    # Moving average for final smoothing
    kernel = np.ones(window) / window
    smoothed = np.convolve(smoothed, kernel, mode="same")
    return smoothed


def _curve_to_segments(
    curve: np.ndarray,
    frames_per_bar: float,
    total_bars: float,
    threshold: float = DEFAULT_ACTIVITY_THRESHOLD,
) -> List[ActivitySegment]:
    """Convert a per-frame activity curve into bar-aligned on/off segments.

    Args:
        curve: Per-frame activity values (normalized 0-1).
        frames_per_bar: Number of frames per bar.
        total_bars: Total number of bars.
        threshold: Activity threshold.

    Returns:
        List of ActivitySegment.
    """
    if len(curve) == 0 or total_bars <= 0:
        return []

    # Compute per-bar average activity
    n_bars = int(np.ceil(total_bars))
    bar_activity = np.zeros(n_bars)
    bar_confidence = np.zeros(n_bars)

    for bar_idx in range(n_bars):
        start_frame = int(bar_idx * frames_per_bar)
        end_frame = int((bar_idx + 1) * frames_per_bar)
        end_frame = min(end_frame, len(curve))
        if start_frame >= len(curve):
            break
        segment = curve[start_frame:end_frame]
        if len(segment) > 0:
            bar_activity[bar_idx] = np.mean(segment)
            bar_confidence[bar_idx] = np.mean(segment)

    # Normalize
    max_val = bar_activity.max()
    if max_val > 0:
        bar_activity /= max_val
        bar_confidence /= max_val

    # Threshold to active/inactive
    active_flags = bar_activity >= threshold

    # Merge consecutive same-state bars into segments
    segments: List[ActivitySegment] = []
    if n_bars == 0:
        return segments

    current_active = bool(active_flags[0])
    current_start = 0
    current_confidences = [float(bar_confidence[0])]

    for i in range(1, n_bars):
        if bool(active_flags[i]) != current_active:
            segments.append(
                ActivitySegment(
                    start_bar=float(current_start),
                    end_bar=float(i),
                    active=current_active,
                    confidence=float(np.mean(current_confidences)),
                )
            )
            current_active = bool(active_flags[i])
            current_start = i
            current_confidences = [float(bar_confidence[i])]
        else:
            current_confidences.append(float(bar_confidence[i]))

    # Final segment
    segments.append(
        ActivitySegment(
            start_bar=float(current_start),
            end_bar=float(n_bars),
            active=current_active,
            confidence=float(np.mean(current_confidences)),
        )
    )

    return segments


def detect_role_activity(
    audio: np.ndarray,
    sr: int,
    bpm: float,
    duration: float,
    hop_length: int = 512,
) -> List[RoleActivityTimeline]:
    """Detect broad role activity from a full mix.

    Uses spectral band analysis and HPSS to estimate when drums, bass,
    melodic, and vocal elements are active.

    Args:
        audio: Audio samples (mono or stereo).
        sr: Sample rate.
        bpm: Beats per minute.
        duration: Track duration in seconds.
        hop_length: Hop length for analysis.

    Returns:
        List of RoleActivityTimeline (one per role).
    """
    logger.info(f"Detecting role activity: bpm={bpm}, duration={duration:.1f}s")
    audio_mono = _ensure_mono(audio)

    # Compute bars info
    beats_per_second = bpm / 60.0
    bars_per_second = beats_per_second / 4.0
    total_bars = bars_per_second * duration
    frames_per_second = sr / hop_length
    frames_per_bar = frames_per_second / bars_per_second

    logger.info(f"Total bars: {total_bars:.1f}, frames_per_bar: {frames_per_bar:.1f}")

    # --- Drums detection: percussive energy via HPSS ---
    logger.info("Computing percussive energy for drums detection...")
    perc_energy = compute_percussive_energy(audio_mono, sr, hop_length)
    perc_smoothed = _smooth_curve(perc_energy)
    drums_segments = _curve_to_segments(
        perc_smoothed, frames_per_bar, total_bars, threshold=0.12
    )
    drums_timeline = RoleActivityTimeline(role="drums", segments=drums_segments)
    logger.info(f"Drums: {len(drums_segments)} segments")

    # --- Bass detection: low-frequency band energy ---
    logger.info("Computing bass band energy...")
    stft = librosa.stft(audio_mono, hop_length=hop_length)
    stft_mag = np.abs(stft)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

    bass_energy = compute_band_energy(stft_mag, freqs, BASS_LOW_HZ, BASS_HIGH_HZ)
    bass_smoothed = _smooth_curve(bass_energy)
    bass_segments = _curve_to_segments(
        bass_smoothed, frames_per_bar, total_bars, threshold=0.12
    )
    bass_timeline = RoleActivityTimeline(role="bass", segments=bass_segments)
    logger.info(f"Bass: {len(bass_segments)} segments")

    # --- Melodic detection: mid-frequency harmonic content ---
    logger.info("Computing melodic activity...")
    mid_energy = compute_band_energy(stft_mag, freqs, MID_LOW_HZ, MID_HIGH_HZ)
    harmonic_ratio = compute_harmonic_ratio(audio_mono, sr, hop_length)
    # Melodic = mid energy weighted by harmonic ratio
    min_len = min(len(mid_energy), len(harmonic_ratio))
    melodic_curve = mid_energy[:min_len] * harmonic_ratio[:min_len]
    melodic_smoothed = _smooth_curve(melodic_curve)
    melodic_segments = _curve_to_segments(
        melodic_smoothed, frames_per_bar, total_bars, threshold=0.15
    )
    melodic_timeline = RoleActivityTimeline(role="melodic", segments=melodic_segments)
    logger.info(f"Melodic: {len(melodic_segments)} segments")

    # --- Vocal detection: mid-high frequency with low spectral flatness ---
    logger.info("Computing vocal activity...")
    mid_high_energy = compute_band_energy(
        stft_mag, freqs, MID_HIGH_LOW_HZ, MID_HIGH_HIGH_HZ
    )
    flatness = compute_spectral_flatness_per_frame(audio_mono, sr, hop_length)
    # Vocal likelihood: mid-high energy * (1 - flatness) — tonal mid-high content
    min_len = min(len(mid_high_energy), len(flatness))
    vocal_curve = mid_high_energy[:min_len] * (1.0 - flatness[:min_len])
    vocal_smoothed = _smooth_curve(vocal_curve)
    vocal_segments = _curve_to_segments(
        vocal_smoothed, frames_per_bar, total_bars, threshold=0.20
    )
    vocal_timeline = RoleActivityTimeline(role="vocal", segments=vocal_segments)
    logger.info(f"Vocal: {len(vocal_segments)} segments")

    return [drums_timeline, bass_timeline, melodic_timeline, vocal_timeline]
