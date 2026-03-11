"""Service for loading and validating reference bundles."""
from pathlib import Path
from typing import Dict, Optional

import librosa
import numpy as np

from .audio_file import load_audio_file, AudioFile
from models.reference_bundle import ReferenceBundle
from models.reference_mix import ReferenceMix
from utils.logger import get_logger

logger = get_logger(__name__)


def snap_bpm_to_grid(raw_bpm: float) -> float:
    """
    Snap a raw BPM estimate to a musically sensible grid.
    
    Heuristic:
    - Round to nearest integer.
    - If result is below 70, assume we detected half-time and double it.
    - If result is above 180, assume we detected double-time and halve it.
    
    Args:
        raw_bpm: Raw BPM estimate from tempo detection
    
    Returns:
        Snapped BPM value
    """
    if raw_bpm <= 0:
        return raw_bpm
    
    snapped = float(round(raw_bpm))
    
    # Simple half-time / double-time correction
    if snapped < 70.0:
        snapped *= 2.0
        logger.debug(f"BPM below 70, assuming half-time: {snapped:.2f}")
    elif snapped > 180.0:
        snapped *= 0.5
        logger.debug(f"BPM above 180, assuming double-time: {snapped:.2f}")
    
    logger.info(f"Snapped raw BPM {raw_bpm:.2f} -> {snapped:.2f}")
    return snapped


def estimate_bpm(audio_file: AudioFile) -> float:
    """
    Estimate BPM from the full_mix audio.
    
    - Convert to mono.
    - Use librosa.beat.tempo with a median aggregate for robustness.
    - Snap the resulting BPM to a sensible grid.
    
    Args:
        audio_file: AudioFile instance to analyze
    
    Returns:
        Snapped BPM as float
    """
    logger.info(f"Estimating BPM from {audio_file.role} stem with librosa.beat.tempo")
    
    y = audio_file.samples
    sr = audio_file.sr
    
    # Ensure mono
    if y.ndim == 2:
        # (channels, samples) or (samples, channels); handle most common shape
        if y.shape[0] < y.shape[1]:
            y_mono = np.mean(y, axis=0)
        else:
            y_mono = np.mean(y, axis=1)
    else:
        y_mono = y
    
    # Use librosa.beat.tempo with median aggregate for robustness
    tempo_array = librosa.beat.tempo(y=y_mono, sr=sr, aggregate=np.median)
    
    if isinstance(tempo_array, (list, np.ndarray)):
        raw_bpm = float(tempo_array[0])
    else:
        raw_bpm = float(tempo_array)
    
    logger.info(f"Estimated raw BPM from librosa.beat.tempo: {raw_bpm:.2f}")
    
    snapped_bpm = snap_bpm_to_grid(raw_bpm)
    logger.info(f"Final BPM (snapped): {snapped_bpm:.2f}")
    
    return snapped_bpm


def estimate_key(audio_file: AudioFile) -> Optional[str]:
    """
    Estimate musical key from an audio file.
    
    This is a stub implementation that returns None for now.
    Can be implemented later using librosa or other key detection libraries.
    
    Args:
        audio_file: AudioFile instance to analyze
    
    Returns:
        Estimated key as string (e.g., "C major", "A minor") or None
    """
    # TODO: Implement key estimation
    # Possible approaches:
    # - Use librosa's chroma features + template matching
    # - Use essentia library
    # - Use other key detection algorithms
    return None


def compute_beat_grid(audio_file: AudioFile, bpm: float) -> list:
    """Compute beat grid timestamps for a track.

    Args:
        audio_file: AudioFile to analyze.
        bpm: BPM to use for beat grid.

    Returns:
        List of beat times in seconds.
    """
    y = audio_file.samples
    sr = audio_file.sr
    if y.ndim == 2:
        if y.shape[0] < y.shape[1]:
            y_mono = np.mean(y, axis=0)
        else:
            y_mono = np.mean(y, axis=1)
    else:
        y_mono = y

    _, beat_frames = librosa.beat.beat_track(y=y_mono, sr=sr, bpm=bpm)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    return [float(t) for t in beat_times]


def load_reference_mix(
    file_path: Path,
    user_bpm_override: Optional[float] = None,
) -> ReferenceMix:
    """Load a single full-mix reference track.

    Args:
        file_path: Path to the audio file.
        user_bpm_override: Optional BPM override from the user.

    Returns:
        ReferenceMix instance.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If duration is outside valid range (30s–600s).
    """
    logger.info(f"Loading reference mix: {file_path}")
    audio = load_audio_file(file_path, role="reference_mix")

    # Validate duration
    if audio.duration < 30.0:
        raise ValueError(
            f"Reference track too short: {audio.duration:.1f}s (minimum 30s)"
        )
    if audio.duration > 600.0:
        raise ValueError(
            f"Reference track too long: {audio.duration:.1f}s (maximum 600s)"
        )

    # Estimate BPM
    logger.info("Estimating BPM from reference mix...")
    detected_bpm = estimate_bpm(audio)

    effective_bpm = user_bpm_override if user_bpm_override else detected_bpm
    logger.info(f"Using BPM: {effective_bpm} (detected: {detected_bpm})")

    # Compute beat grid
    logger.info("Computing beat grid...")
    beat_grid = compute_beat_grid(audio, effective_bpm)
    logger.info(f"Beat grid: {len(beat_grid)} beats")

    mix = ReferenceMix(
        audio=audio,
        bpm=detected_bpm,
        beat_grid=beat_grid,
        key=estimate_key(audio),
        user_bpm_override=user_bpm_override,
    )

    logger.info(f"Successfully loaded reference mix: {mix}")
    return mix


def load_reference_bundle(file_paths: Dict[str, Path]) -> ReferenceBundle:
    """
    Load a reference bundle from file paths.
    
    Args:
        file_paths: Dictionary with keys 'drums', 'bass', 'vocals', 'instruments', 'full_mix'
                   and values as Path objects to the audio files
    
    Returns:
        ReferenceBundle instance with loaded audio files and metadata
    
    Raises:
        KeyError: If required file paths are missing
        ValueError: If audio file durations don't match within tolerance
    """
    required_keys = ['drums', 'bass', 'vocals', 'instruments', 'full_mix']
    
    # Validate that all required keys are present
    missing_keys = [key for key in required_keys if key not in file_paths]
    if missing_keys:
        raise KeyError(f"Missing required file paths: {missing_keys}")
    
    logger.info("Loading reference bundle...")
    
    # Load all audio files
    audio_files = {}
    for role in required_keys:
        path = file_paths[role]
        logger.info(f"Loading {role}: {path}")
        audio_files[role] = load_audio_file(path, role=role)
    
    # Estimate BPM from full mix
    logger.info("Estimating BPM from full mix...")
    bpm = estimate_bpm(audio_files['full_mix'])
    
    # Estimate key (stub for now)
    logger.info("Estimating key from full mix...")
    key = estimate_key(audio_files['full_mix'])
    if key:
        logger.info(f"Estimated key: {key}")
    else:
        logger.info("Key estimation not implemented yet")
    
    # Create ReferenceBundle
    bundle = ReferenceBundle(
        drums=audio_files['drums'],
        bass=audio_files['bass'],
        vocals=audio_files['vocals'],
        instruments=audio_files['instruments'],
        full_mix=audio_files['full_mix'],
        bpm=bpm,
        key=key
    )
    
    # Validate lengths
    logger.info("Validating audio file durations...")
    bundle.validate_lengths()
    logger.info("All audio files have matching durations")
    
    logger.info(f"Successfully loaded reference bundle: {bundle}")
    return bundle

