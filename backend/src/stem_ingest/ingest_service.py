"""Service for loading and validating reference bundles."""
from pathlib import Path
from typing import Dict, Optional

import librosa
import numpy as np

from .audio_file import load_audio_file, AudioFile
from models.reference_bundle import ReferenceBundle
from utils.logger import get_logger

logger = get_logger(__name__)


def estimate_bpm(audio_file: AudioFile) -> float:
    """
    Estimate BPM from an audio file.
    
    Args:
        audio_file: AudioFile instance to analyze
    
    Returns:
        Estimated BPM as float
    """
    logger.info(f"Estimating BPM from {audio_file.role} stem")
    
    # Convert to mono if needed for librosa tempo estimation
    if audio_file.samples.ndim > 1:
        # Multi-channel: use first channel or convert to mono
        if audio_file.samples.shape[0] > 1:
            samples = np.mean(audio_file.samples, axis=0)
        else:
            samples = audio_file.samples[0]
    else:
        samples = audio_file.samples
    
    # Use librosa's tempo estimation
    # This returns a tempo estimate in BPM
    tempo, _ = librosa.beat.beat_track(y=samples, sr=audio_file.sr)
    
    # librosa.beat.beat_track returns tempo as a numpy array, get the first value
    bpm = float(tempo) if isinstance(tempo, (np.ndarray, list)) else float(tempo)
    
    logger.info(f"Estimated BPM: {bpm:.1f}")
    return bpm


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

