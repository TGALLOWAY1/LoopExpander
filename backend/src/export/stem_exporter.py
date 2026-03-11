"""Stem exporter (Phase 9A).

Renders the full arrangement into per-role WAV files.
Each role gets a continuous WAV file for the full song length,
with user loop material placed according to arrangement blocks.
"""
import io
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

from arrangement.models import Arrangement
from models.user_loop import UserLoopBundle, UserLoopStem
from stem_ingest.audio_file import load_audio_file
from utils.logger import get_logger

logger = get_logger(__name__)

# Default sample rate for exports
EXPORT_SR = 44100

# Supported export formats
EXPORT_FORMATS = {
    "wav16": {"format": "WAV", "subtype": "PCM_16"},
    "wav24": {"format": "WAV", "subtype": "PCM_24"},
    "aiff": {"format": "AIFF", "subtype": "PCM_16"},
}


def render_all_stems(
    arrangement: Arrangement,
    loop_bundle: UserLoopBundle,
    export_format: str = "wav16",
) -> dict[str, bytes]:
    """Render one WAV file per role for the full arrangement.

    Args:
        arrangement: The full arrangement with blocks.
        loop_bundle: The user's loop stems.
        export_format: One of "wav16", "wav24", "aiff".

    Returns:
        Dict mapping role name to rendered audio bytes (e.g. {"drums": b"..."}).
    """
    if export_format not in EXPORT_FORMATS:
        raise ValueError(f"Unsupported format: {export_format}. Use one of: {list(EXPORT_FORMATS.keys())}")

    fmt = EXPORT_FORMATS[export_format]
    ext = "aif" if export_format == "aiff" else "wav"

    bpm = arrangement.bpm if arrangement.bpm > 0 else 120.0
    seconds_per_bar = (60.0 / bpm) * 4.0
    total_duration = arrangement.total_bars * seconds_per_bar
    total_samples = int(total_duration * EXPORT_SR)

    # Get unique roles from blocks
    roles = sorted(set(b.role for b in arrangement.blocks))

    # Load stem audio into cache
    stem_cache: dict[str, np.ndarray] = {}
    for stem in loop_bundle.stems:
        try:
            audio_data = _load_stem_audio(stem, EXPORT_SR)
            stem_cache[stem.id] = audio_data
        except Exception as e:
            logger.warning(f"Failed to load stem {stem.id} ({stem.filename}): {e}")

    result: dict[str, bytes] = {}

    for role in roles:
        role_blocks = [
            b for b in arrangement.blocks
            if b.role == role and b.active
        ]

        buffer = np.zeros(total_samples, dtype=np.float32)

        for block in role_blocks:
            stem_audio = stem_cache.get(block.stem_id)
            if stem_audio is None or len(stem_audio) == 0:
                continue

            start_sample = int(block.start_bar * seconds_per_bar * EXPORT_SR)
            block_samples = int(
                (block.end_bar - block.start_bar) * seconds_per_bar * EXPORT_SR
            )

            if start_sample < 0 or start_sample >= total_samples:
                continue

            filled = _loop_fill(stem_audio, block_samples)
            end_sample = min(start_sample + len(filled), total_samples)
            length = end_sample - start_sample
            buffer[start_sample:end_sample] += filled[:length]

        # Normalize
        peak = np.max(np.abs(buffer))
        if peak > 0.95:
            buffer = buffer * (0.95 / peak)

        # Encode
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, buffer, EXPORT_SR, format=fmt["format"], subtype=fmt["subtype"])
        wav_buffer.seek(0)

        filename = f"{role}.{ext}"
        result[filename] = wav_buffer.read()

        logger.info(f"Rendered stem '{filename}': {total_duration:.1f}s, {len(role_blocks)} blocks")

    return result


def _load_stem_audio(stem: UserLoopStem, target_sr: int) -> np.ndarray:
    """Load a stem's audio file and convert to mono at target sample rate."""
    audio = load_audio_file(stem.audio_path, role="user_loop")
    samples = audio.samples

    if samples.ndim > 1:
        samples = np.mean(samples, axis=0 if samples.shape[0] <= 2 else 1)
        if samples.ndim > 1:
            samples = samples[0]

    if audio.sr != target_sr:
        import librosa
        samples = librosa.resample(samples, orig_sr=audio.sr, target_sr=target_sr)

    return samples.astype(np.float32)


def _loop_fill(audio: np.ndarray, target_length: int) -> np.ndarray:
    """Repeat audio to fill a target length in samples."""
    if len(audio) == 0:
        return np.zeros(target_length, dtype=np.float32)

    if len(audio) >= target_length:
        return audio[:target_length]

    repeats = (target_length // len(audio)) + 1
    tiled = np.tile(audio, repeats)
    return tiled[:target_length]
