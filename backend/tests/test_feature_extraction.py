"""Tests for feature extraction functions."""
import numpy as np
import pytest

from src.analysis.region_detector.features import (
    compute_rms_envelope,
    compute_spectral_centroid,
    compute_transient_density,
    compute_novelty_curve,
    _ensure_mono
)


def test_ensure_mono():
    """Test mono conversion helper."""
    # Mono input should remain unchanged
    mono = np.array([1.0, 2.0, 3.0])
    assert np.array_equal(_ensure_mono(mono), mono)
    
    # Stereo input should be averaged
    stereo = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    expected = np.array([2.5, 3.5, 4.5])
    assert np.allclose(_ensure_mono(stereo), expected)


def test_compute_rms_envelope_amplitude_change():
    """Test that RMS envelope changes when amplitude changes."""
    sr = 44100
    duration = 1.0  # 1 second
    t = np.linspace(0, duration, int(sr * duration))
    
    # Create signal with amplitude change: first half quiet, second half loud
    amplitude1 = 0.1
    amplitude2 = 0.9
    signal = np.concatenate([
        amplitude1 * np.sin(2 * np.pi * 440 * t[:len(t)//2]),
        amplitude2 * np.sin(2 * np.pi * 440 * t[len(t)//2:])
    ])
    
    rms = compute_rms_envelope(signal, frame_length=2048, hop_length=512)
    
    # RMS should be higher in the second half
    first_half_avg = np.mean(rms[:len(rms)//2])
    second_half_avg = np.mean(rms[len(rms)//2:])
    
    assert second_half_avg > first_half_avg, \
        "RMS envelope should be higher for louder signal"


def test_compute_spectral_centroid_frequency_difference():
    """Test that spectral centroid differs for low vs high frequency tones."""
    sr = 44100
    duration = 1.0
    
    # Low frequency tone (220 Hz)
    t_low = np.linspace(0, duration, int(sr * duration))
    low_freq_signal = np.sin(2 * np.pi * 220 * t_low)
    
    # High frequency tone (2000 Hz)
    high_freq_signal = np.sin(2 * np.pi * 2000 * t_low)
    
    centroid_low = compute_spectral_centroid(low_freq_signal, sr=sr)
    centroid_high = compute_spectral_centroid(high_freq_signal, sr=sr)
    
    # High frequency signal should have higher spectral centroid
    avg_centroid_low = np.mean(centroid_low)
    avg_centroid_high = np.mean(centroid_high)
    
    assert avg_centroid_high > avg_centroid_low, \
        "High frequency tone should have higher spectral centroid"


def test_compute_transient_density_with_attacks():
    """Test that transient density is higher when sharp attacks are added."""
    sr = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration))
    
    # Smooth signal (sine wave)
    smooth_signal = 0.5 * np.sin(2 * np.pi * 440 * t)
    
    # Signal with sharp attacks (impulses)
    signal_with_attacks = smooth_signal.copy()
    # Add impulses at regular intervals
    impulse_indices = np.arange(0, len(signal_with_attacks), int(sr * 0.5))  # Every 0.5 seconds
    for idx in impulse_indices:
        if idx < len(signal_with_attacks):
            signal_with_attacks[idx] = 1.0
    
    density_smooth = compute_transient_density(smooth_signal, sr=sr)
    density_attacks = compute_transient_density(signal_with_attacks, sr=sr)
    
    # Signal with attacks should have higher transient density
    avg_density_smooth = np.mean(density_smooth)
    avg_density_attacks = np.mean(density_attacks)
    
    assert avg_density_attacks > avg_density_smooth, \
        "Signal with attacks should have higher transient density"


def test_compute_novelty_curve_with_abrupt_changes():
    """Test that novelty curve has peaks where signal changes abruptly."""
    sr = 44100
    duration = 3.0
    t = np.linspace(0, duration, int(sr * duration))
    
    # Create signal with abrupt changes at 1s and 2s
    signal = np.concatenate([
        np.sin(2 * np.pi * 440 * t[:int(sr * 1.0)]),  # 440 Hz for first second
        np.sin(2 * np.pi * 880 * t[int(sr * 1.0):int(sr * 2.0)]),  # 880 Hz for second second
        np.sin(2 * np.pi * 220 * t[int(sr * 2.0):])  # 220 Hz for third second
    ])
    
    novelty = compute_novelty_curve(signal, sr=sr)
    
    # Find peaks in novelty curve
    # Simple peak detection: values above mean + std
    threshold = np.mean(novelty) + np.std(novelty)
    peaks = np.where(novelty > threshold)[0]
    
    # Convert peak frame indices to time
    hop_length = 512
    peak_times = peaks * hop_length / sr
    
    # Should have peaks near 1s and 2s (with some tolerance)
    has_peak_near_1s = np.any(np.abs(peak_times - 1.0) < 0.5)
    has_peak_near_2s = np.any(np.abs(peak_times - 2.0) < 0.5)
    
    assert has_peak_near_1s or has_peak_near_2s, \
        "Novelty curve should have peaks near abrupt signal changes"


def test_feature_extraction_output_shapes():
    """Test that all feature extraction functions return 1D arrays."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration))
    signal = np.sin(2 * np.pi * 440 * t)
    
    rms = compute_rms_envelope(signal)
    centroid = compute_spectral_centroid(signal, sr=sr)
    density = compute_transient_density(signal, sr=sr)
    novelty = compute_novelty_curve(signal, sr=sr)
    
    # All should be 1D arrays
    assert rms.ndim == 1, "RMS envelope should be 1D"
    assert centroid.ndim == 1, "Spectral centroid should be 1D"
    assert density.ndim == 1, "Transient density should be 1D"
    assert novelty.ndim == 1, "Novelty curve should be 1D"
    
    # All should have reasonable length (non-empty)
    assert len(rms) > 0, "RMS envelope should not be empty"
    assert len(centroid) > 0, "Spectral centroid should not be empty"
    assert len(density) > 0, "Transient density should not be empty"
    assert len(novelty) > 0, "Novelty curve should not be empty"


def test_feature_extraction_with_stereo():
    """Test that feature extraction works with stereo input."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration))
    
    # Create stereo signal
    left_channel = np.sin(2 * np.pi * 440 * t)
    right_channel = np.sin(2 * np.pi * 440 * t) * 0.8
    stereo_signal = np.array([left_channel, right_channel])
    
    # All functions should handle stereo input
    rms = compute_rms_envelope(stereo_signal)
    centroid = compute_spectral_centroid(stereo_signal, sr=sr)
    density = compute_transient_density(stereo_signal, sr=sr)
    novelty = compute_novelty_curve(stereo_signal, sr=sr)
    
    # Should all return valid 1D arrays
    assert rms.ndim == 1 and len(rms) > 0
    assert centroid.ndim == 1 and len(centroid) > 0
    assert density.ndim == 1 and len(density) > 0
    assert novelty.ndim == 1 and len(novelty) > 0

