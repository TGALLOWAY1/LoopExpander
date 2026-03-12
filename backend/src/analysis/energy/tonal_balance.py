"""Tonal balance computation per region using 5-band spectral analysis."""
from typing import List, Dict
from dataclasses import dataclass, field

import numpy as np
import librosa

from analysis.role_activity.spectral_bands import compute_band_energy
from utils.logger import get_logger

logger = get_logger(__name__)

# 5-band frequency ranges (Hz)
TONAL_BANDS = {
    "low": (20.0, 250.0),
    "lowMid": (250.0, 500.0),
    "mid": (500.0, 2000.0),
    "highMid": (2000.0, 6000.0),
    "high": (6000.0, 20000.0),
}


@dataclass
class RegionTonalBalance:
    """Tonal balance for a single region."""
    region_id: str
    low: float = 0.0
    low_mid: float = 0.0
    mid: float = 0.0
    high_mid: float = 0.0
    high: float = 0.0

    def to_dict(self) -> dict:
        return {
            "regionId": self.region_id,
            "low": self.low,
            "lowMid": self.low_mid,
            "mid": self.mid,
            "highMid": self.high_mid,
            "high": self.high,
        }


def compute_tonal_balance(
    audio: np.ndarray,
    sr: int,
    regions: list,
    hop_length: int = 512,
) -> List[RegionTonalBalance]:
    """Compute 5-band tonal balance per region.

    Args:
        audio: Audio samples (mono or multi-channel).
        sr: Sample rate.
        regions: List of Region objects with start/end in seconds.
        hop_length: Hop length for STFT.

    Returns:
        List of RegionTonalBalance, one per region.
    """
    if not regions:
        return []

    # Ensure mono
    if audio.ndim == 2:
        audio = np.mean(audio, axis=0) if audio.shape[0] < audio.shape[1] else np.mean(audio, axis=1)

    logger.info(f"Computing tonal balance for {len(regions)} regions")

    # Compute STFT once for entire track
    stft = librosa.stft(audio, hop_length=hop_length)
    stft_mag = np.abs(stft)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=stft.shape[0] * 2 - 2)
    stft_times = librosa.frames_to_time(np.arange(stft_mag.shape[1]), sr=sr, hop_length=hop_length)

    # Compute band energies for entire track
    band_energies = {}
    for band_name, (low_hz, high_hz) in TONAL_BANDS.items():
        band_energies[band_name] = compute_band_energy(stft_mag, freqs, low_hz, high_hz)

    results = []
    for region in regions:
        # Find frames within this region
        frame_mask = (stft_times >= region.start) & (stft_times < region.end)

        if not np.any(frame_mask):
            results.append(RegionTonalBalance(region_id=region.id))
            continue

        # Average energy per band within the region
        band_values = {}
        for band_name in TONAL_BANDS:
            band_values[band_name] = float(np.mean(band_energies[band_name][frame_mask]))

        # Normalize: make values relative to total energy
        total = sum(band_values.values())
        if total > 0:
            for band_name in band_values:
                band_values[band_name] /= total

        results.append(RegionTonalBalance(
            region_id=region.id,
            low=band_values["low"],
            low_mid=band_values["lowMid"],
            mid=band_values["mid"],
            high_mid=band_values["highMid"],
            high=band_values["high"],
        ))

    logger.info(f"Tonal balance computed for {len(results)} regions")
    return results
