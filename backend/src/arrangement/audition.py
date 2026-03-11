"""Section audition renderer (Phase 8B).

Renders a section's audio by concatenating user loop stems according to
arrangement blocks. Returns a WAV buffer for playback.
"""
import io
import numpy as np
import soundfile as sf

from arrangement.models import Arrangement
from models.user_loop import UserLoopBundle, UserLoopStem
from stem_ingest.audio_file import load_audio_file
from utils.logger import get_logger

logger = get_logger(__name__)

# Standard sample rate for audition output
AUDITION_SR = 44100


def render_section_audio(
    arrangement: Arrangement,
    loop_bundle: UserLoopBundle,
    section_id: str,
    solo_roles: list[str] | None = None,
    mute_roles: list[str] | None = None,
) -> bytes:
    """Render audio for a single section of the arrangement.

    Args:
        arrangement: The full arrangement.
        loop_bundle: The user's loop stems.
        section_id: Which section to render.
        solo_roles: If provided, only render these roles.
        mute_roles: If provided, mute these roles.

    Returns:
        WAV audio as bytes.
    """
    # Find the section
    section = next((s for s in arrangement.sections if s.id == section_id), None)
    if not section:
        raise ValueError(f"Section {section_id} not found in arrangement")

    section_length_bars = section.end_bar - section.start_bar
    bpm = arrangement.bpm
    if bpm <= 0:
        bpm = 120.0

    seconds_per_bar = (60.0 / bpm) * 4.0
    section_duration = section_length_bars * seconds_per_bar
    total_samples = int(section_duration * AUDITION_SR)

    # Create mix buffer
    mix = np.zeros(total_samples, dtype=np.float32)

    # Get blocks for this section
    section_blocks = [
        b for b in arrangement.blocks
        if b.section_id == section_id and b.active
    ]

    # Apply solo/mute filters
    if solo_roles:
        section_blocks = [b for b in section_blocks if b.role in solo_roles]
    elif mute_roles:
        section_blocks = [b for b in section_blocks if b.role not in mute_roles]

    # Build a cache of loaded stem audio
    stem_cache: dict[str, np.ndarray] = {}

    for block in section_blocks:
        stem = _find_stem(loop_bundle, block.stem_id)
        if not stem:
            logger.warning(f"Stem {block.stem_id} not found, skipping block {block.id}")
            continue

        # Load stem audio (cached)
        if stem.id not in stem_cache:
            try:
                audio_data = _load_stem_audio(stem, AUDITION_SR)
                stem_cache[stem.id] = audio_data
            except Exception as e:
                logger.warning(f"Failed to load stem {stem.id}: {e}")
                continue

        stem_audio = stem_cache[stem.id]
        if len(stem_audio) == 0:
            continue

        # Calculate block position relative to section start
        block_start_in_section = block.start_bar - section.start_bar
        block_length_bars = block.end_bar - block.start_bar

        start_sample = int(block_start_in_section * seconds_per_bar * AUDITION_SR)
        block_samples = int(block_length_bars * seconds_per_bar * AUDITION_SR)

        if start_sample < 0 or start_sample >= total_samples:
            continue

        # Loop the stem audio to fill the block
        filled = _loop_fill(stem_audio, block_samples)

        # Mix into the output buffer
        end_sample = min(start_sample + len(filled), total_samples)
        length = end_sample - start_sample
        mix[start_sample:end_sample] += filled[:length]

    # Normalize to prevent clipping
    peak = np.max(np.abs(mix))
    if peak > 0.95:
        mix = mix * (0.95 / peak)

    # Encode as WAV
    buffer = io.BytesIO()
    sf.write(buffer, mix, AUDITION_SR, format='WAV', subtype='PCM_16')
    buffer.seek(0)
    return buffer.read()


def _find_stem(bundle: UserLoopBundle, stem_id: str) -> UserLoopStem | None:
    """Find a stem by ID in the loop bundle."""
    return next((s for s in bundle.stems if s.id == stem_id), None)


def _load_stem_audio(stem: UserLoopStem, target_sr: int) -> np.ndarray:
    """Load a stem's audio file and convert to mono at target sample rate."""
    audio = load_audio_file(stem.audio_path, role="user_loop")
    samples = audio.samples

    # Convert to mono if stereo
    if samples.ndim > 1:
        samples = np.mean(samples, axis=0 if samples.shape[0] <= 2 else 1)
        if samples.ndim > 1:
            samples = samples[0]

    # Resample if needed
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
