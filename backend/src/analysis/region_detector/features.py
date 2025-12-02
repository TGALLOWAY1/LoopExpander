"""Feature extraction utilities for region detection."""
import numpy as np
import librosa

from utils.logger import get_logger

logger = get_logger(__name__)


def _ensure_mono(audio: np.ndarray) -> np.ndarray:
    """
    Convert multi-channel audio to mono by averaging channels.
    
    Args:
        audio: Audio array (1D for mono, 2D for multi-channel)
    
    Returns:
        Mono audio array (1D)
    """
    if audio.ndim == 1:
        return audio
    elif audio.ndim == 2:
        # Multi-channel: average across channels
        return np.mean(audio, axis=0)
    else:
        raise ValueError(f"Unexpected audio shape: {audio.shape}. Expected 1D or 2D array.")


def compute_rms_envelope(
    audio: np.ndarray,
    frame_length: int = 2048,
    hop_length: int = 512
) -> np.ndarray:
    """
    Compute frame-wise RMS (Root Mean Square) energy envelope.
    
    Args:
        audio: Audio signal (mono or multi-channel, will be converted to mono)
        frame_length: Frame length for analysis window
        hop_length: Hop length between frames
    
    Returns:
        Frame-wise RMS energy values (1D array)
    """
    # Convert to mono if needed
    audio_mono = _ensure_mono(audio)
    
    # Compute RMS using librosa
    rms = librosa.feature.rms(
        y=audio_mono,
        frame_length=frame_length,
        hop_length=hop_length
    )
    
    # librosa.feature.rms returns shape (1, n_frames), squeeze to 1D
    return rms[0]


def compute_spectral_centroid(
    audio: np.ndarray,
    sr: int,
    hop_length: int = 512
) -> np.ndarray:
    """
    Compute frame-wise spectral centroid.
    
    The spectral centroid indicates the "brightness" of the sound.
    Higher values indicate more high-frequency content.
    
    Args:
        audio: Audio signal (mono or multi-channel, will be converted to mono)
        sr: Sample rate in Hz
        hop_length: Hop length between frames
    
    Returns:
        Frame-wise spectral centroid values in Hz (1D array)
    """
    # Convert to mono if needed
    audio_mono = _ensure_mono(audio)
    
    # Compute spectral centroid using librosa
    centroid = librosa.feature.spectral_centroid(
        y=audio_mono,
        sr=sr,
        hop_length=hop_length
    )
    
    # librosa.feature.spectral_centroid returns shape (1, n_frames), squeeze to 1D
    return centroid[0]


def compute_transient_density(
    audio: np.ndarray,
    sr: int,
    hop_length: int = 512,
    window_size: int = 2048
) -> np.ndarray:
    """
    Estimate transient density over time using onset strength.
    
    This function computes onset strength and then averages it over windows
    to get a density measure. Higher values indicate more transients/attacks.
    
    Args:
        audio: Audio signal (mono or multi-channel, will be converted to mono)
        sr: Sample rate in Hz
        hop_length: Hop length between frames
        window_size: Window size for averaging onset strength (in samples)
    
    Returns:
        Frame-wise transient density values (1D array, normalized)
    """
    # Convert to mono if needed
    audio_mono = _ensure_mono(audio)
    
    # Compute onset strength using librosa
    onset_strength = librosa.onset.onset_strength(
        y=audio_mono,
        sr=sr,
        hop_length=hop_length
    )
    
    # Convert window_size from samples to frames
    # hop_length samples per frame, so window_size / hop_length frames
    window_frames = max(1, window_size // hop_length)
    
    # Average onset strength over windows to get density
    # Use a simple moving average
    if len(onset_strength) < window_frames:
        # If signal is shorter than window, just return the onset strength
        density = onset_strength
    else:
        # Apply moving average
        density = np.convolve(
            onset_strength,
            np.ones(window_frames) / window_frames,
            mode='same'
        )
    
    # Normalize to [0, 1] range
    if density.max() > 0:
        density = density / density.max()
    
    return density


def compute_novelty_curve(
    audio: np.ndarray,
    sr: int,
    hop_length: int = 512
) -> np.ndarray:
    """
    Compute a novelty curve using spectral flux.
    
    The novelty curve indicates points of change in the audio signal.
    Peaks in the novelty curve often correspond to structural boundaries.
    
    This implementation uses spectral flux (difference in spectral magnitude
    between consecutive frames) as the novelty measure.
    
    Args:
        audio: Audio signal (mono or multi-channel, will be converted to mono)
        sr: Sample rate in Hz
        hop_length: Hop length between frames
    
    Returns:
        Frame-wise novelty values (1D array, normalized)
    """
    # Convert to mono if needed
    audio_mono = _ensure_mono(audio)
    
    # Compute short-time Fourier transform
    stft = librosa.stft(
        audio_mono,
        hop_length=hop_length,
        n_fft=2048
    )
    
    # Get magnitude spectrogram
    magnitude = np.abs(stft)
    
    # Compute spectral flux: difference between consecutive frames
    # Sum the differences across frequency bins
    flux = np.diff(magnitude, axis=1)
    
    # Sum across frequency bins and take only positive differences
    # (negative differences indicate decrease, which is less novel)
    novelty = np.sum(np.maximum(flux, 0), axis=0)
    
    # Normalize to [0, 1] range
    if novelty.max() > 0:
        novelty = novelty / novelty.max()
    
    return novelty

