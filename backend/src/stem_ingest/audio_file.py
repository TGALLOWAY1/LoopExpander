"""Audio file loading and validation."""
from dataclasses import dataclass
from pathlib import Path
from typing import Union

try:
    from typing import Literal
except ImportError:
    # Python < 3.8 compatibility
    from typing_extensions import Literal

import librosa
import numpy as np
import soundfile as sf

from utils.logger import get_logger

logger = get_logger(__name__)


# Role type for audio files
AudioRole = Union[Literal["drums"], Literal["bass"], Literal["vocals"], Literal["instruments"], Literal["full_mix"]]


class UnsupportedFormatError(Exception):
    """Raised when audio file format is not supported."""
    pass


@dataclass
class AudioFile:
    """Represents a loaded audio file with metadata."""
    path: Path
    role: str
    sr: int
    duration: float
    channels: int
    samples: np.ndarray

    def __post_init__(self):
        """Validate audio file data after initialization."""
        if self.samples is None or self.samples.size == 0:
            raise ValueError(f"Audio file {self.path} has no samples")
        if self.duration <= 0:
            raise ValueError(f"Audio file {self.path} has invalid duration: {self.duration}")
        if self.sr <= 0:
            raise ValueError(f"Audio file {self.path} has invalid sample rate: {self.sr}")


def load_audio_file(
    path: Path,
    role: str,
    target_sample_rates=(44100, 48000, 96000)
) -> AudioFile:
    """
    Load an audio file and return an AudioFile instance.
    
    Args:
        path: Path to the audio file
        role: Role of the audio file (drums, bass, vocals, instruments, full_mix)
        target_sample_rates: Tuple of acceptable sample rates. If file's SR is not in this list,
                           it will be resampled to the first target rate.
    
    Returns:
        AudioFile instance with loaded audio data
    
    Raises:
        UnsupportedFormatError: If file format is not WAV or AIFF
        FileNotFoundError: If file does not exist
        ValueError: If audio data is invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    
    # Validate file format
    suffix = path.suffix.lower()
    if suffix not in ['.wav', '.aiff', '.aif']:
        raise UnsupportedFormatError(
            f"Unsupported audio format: {suffix}. Only WAV and AIFF are supported."
        )
    
    logger.info(f"Loading audio file: {path} (role: {role})")
    
    # Load audio file using soundfile for format detection, then librosa for processing
    try:
        # First, read metadata to get original sample rate
        with sf.SoundFile(str(path)) as f:
            original_sr = f.samplerate
            channels = f.channels
            frames = f.frames
            duration = frames / original_sr
        
        # Load audio data
        # librosa.load always returns mono, so we'll handle stereo separately if needed
        samples, sr = librosa.load(str(path), sr=None, mono=False)
        
        # If stereo, keep it; librosa.load with mono=False returns shape (channels, samples)
        # If mono, samples is 1D array
        if samples.ndim == 1:
            # Mono audio
            channels = 1
        else:
            # Multi-channel audio (samples.shape = (channels, samples))
            channels = samples.shape[0]
            # For now, we'll keep multi-channel as-is
            # Later analysis can convert to mono if needed
        
        # Check if resampling is needed
        if sr not in target_sample_rates:
            target_sr = target_sample_rates[0]
            logger.info(f"Resampling from {sr} Hz to {target_sr} Hz")
            
            if samples.ndim == 1:
                # Mono: resample directly
                samples = librosa.resample(samples, orig_sr=sr, target_sr=target_sr)
            else:
                # Multi-channel: resample each channel
                resampled_channels = []
                for ch in range(channels):
                    resampled_ch = librosa.resample(
                        samples[ch], orig_sr=sr, target_sr=target_sr
                    )
                    resampled_channels.append(resampled_ch)
                samples = np.array(resampled_channels)
            
            sr = target_sr
            duration = samples.shape[-1] / sr
        
        logger.info(
            f"Loaded audio: {duration:.2f}s, {channels} channel(s), {sr} Hz, "
            f"shape: {samples.shape}"
        )
        
        return AudioFile(
            path=path,
            role=role,
            sr=sr,
            duration=duration,
            channels=channels,
            samples=samples
        )
    
    except Exception as e:
        logger.error(f"Error loading audio file {path}: {e}")
        raise

