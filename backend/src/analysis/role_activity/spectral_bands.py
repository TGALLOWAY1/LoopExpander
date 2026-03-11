"""Spectral band energy analysis for role activity detection."""
import numpy as np
import librosa

from utils.logger import get_logger

logger = get_logger(__name__)


def compute_band_energy(
    stft_mag: np.ndarray,
    freqs: np.ndarray,
    low_hz: float,
    high_hz: float,
) -> np.ndarray:
    """Compute energy in a frequency band over time.

    Args:
        stft_mag: Magnitude spectrogram (freq_bins x frames).
        freqs: Frequency array for each bin.
        low_hz: Lower bound of the band in Hz.
        high_hz: Upper bound of the band in Hz.

    Returns:
        Per-frame energy in the band (1D array).
    """
    band_mask = (freqs >= low_hz) & (freqs <= high_hz)
    if not np.any(band_mask):
        return np.zeros(stft_mag.shape[1])
    return np.mean(stft_mag[band_mask, :] ** 2, axis=0)


def compute_percussive_energy(
    audio_mono: np.ndarray,
    sr: int,
    hop_length: int = 512,
) -> np.ndarray:
    """Compute percussive component energy using HPSS.

    Args:
        audio_mono: Mono audio signal.
        sr: Sample rate.
        hop_length: Hop length for STFT.

    Returns:
        Per-frame RMS of the percussive component.
    """
    stft = librosa.stft(audio_mono, hop_length=hop_length)
    _, S_perc = librosa.decompose.hpss(stft)
    perc_rms = librosa.feature.rms(S=np.abs(S_perc), hop_length=hop_length)[0]
    return perc_rms


def compute_harmonic_ratio(
    audio_mono: np.ndarray,
    sr: int,
    hop_length: int = 512,
) -> np.ndarray:
    """Compute harmonic-to-total energy ratio using HPSS.

    Args:
        audio_mono: Mono audio signal.
        sr: Sample rate.
        hop_length: Hop length for STFT.

    Returns:
        Per-frame harmonic ratio (0.0-1.0).
    """
    stft = librosa.stft(audio_mono, hop_length=hop_length)
    S_harm, S_perc = librosa.decompose.hpss(stft)
    harm_energy = np.sum(np.abs(S_harm) ** 2, axis=0)
    total_energy = np.sum(np.abs(stft) ** 2, axis=0)
    # Avoid division by zero
    ratio = np.where(total_energy > 1e-10, harm_energy / total_energy, 0.0)
    return ratio


def compute_spectral_flatness_per_frame(
    audio_mono: np.ndarray,
    sr: int,
    hop_length: int = 512,
) -> np.ndarray:
    """Compute per-frame spectral flatness.

    Low spectral flatness indicates tonal content (voice, melody).
    High spectral flatness indicates noise-like content.

    Args:
        audio_mono: Mono audio signal.
        sr: Sample rate.
        hop_length: Hop length.

    Returns:
        Per-frame spectral flatness (1D array).
    """
    flatness = librosa.feature.spectral_flatness(
        y=audio_mono, hop_length=hop_length
    )
    return flatness[0]
