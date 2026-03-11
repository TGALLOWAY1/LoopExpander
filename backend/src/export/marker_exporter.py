"""Marker and structure exporter (Phase 9B).

Exports arrangement structure as:
- JSON (full structure with sections, blocks, labels, markers)
- MIDI markers (section boundaries as MIDI marker events)
- CSV markers (section boundaries in CSV format)
"""
import io
import json
import struct
from typing import Optional

from arrangement.models import Arrangement
from arrangement.guide_content import GuideMarker
from arrangement.variation_engine import VariationSuggestion
from models.interaction_label import InteractionLabel
from utils.logger import get_logger

logger = get_logger(__name__)


def export_arrangement_json(
    arrangement: Arrangement,
    interaction_labels: list | None = None,
    guide_markers: list | None = None,
    suggestions: list | None = None,
) -> bytes:
    """Export the full arrangement as a JSON document.

    Args:
        arrangement: The full arrangement.
        interaction_labels: Optional interaction labels.
        guide_markers: Optional guide markers.
        suggestions: Optional variation suggestions.

    Returns:
        JSON bytes.
    """
    data = {
        "bpm": arrangement.bpm,
        "totalBars": arrangement.total_bars,
        "sections": [s.to_dict() for s in arrangement.sections],
        "blocks": [b.to_dict() for b in arrangement.blocks],
        "interactionLabels": [
            _label_to_dict(l) for l in (interaction_labels or [])
        ],
        "guideMarkers": [
            m.to_dict() if hasattr(m, 'to_dict') else _marker_to_dict(m)
            for m in (guide_markers or [])
        ],
        "suggestions": [
            s.to_dict() if hasattr(s, 'to_dict') else _suggestion_to_dict(s)
            for s in (suggestions or [])
        ],
    }

    return json.dumps(data, indent=2).encode("utf-8")


def export_midi_markers(arrangement: Arrangement) -> bytes:
    """Export section boundaries as a Standard MIDI file with marker events.

    Creates a Type 0 MIDI file with tempo and marker meta events.
    """
    bpm = arrangement.bpm if arrangement.bpm > 0 else 120.0
    ticks_per_beat = 480
    ticks_per_bar = ticks_per_beat * 4  # 4/4 time

    # Build MIDI events
    events: list[tuple[int, bytes]] = []

    # Tempo event at tick 0
    microseconds_per_beat = int(60_000_000 / bpm)
    tempo_bytes = struct.pack(">I", microseconds_per_beat)[1:]  # 3 bytes
    events.append((0, b"\xFF\x51\x03" + tempo_bytes))

    # Time signature: 4/4
    events.append((0, b"\xFF\x58\x04\x04\x02\x18\x08"))

    # Marker events for each section
    for section in arrangement.sections:
        tick = int(section.start_bar * ticks_per_bar)
        label = section.label.encode("ascii", errors="replace")
        length = len(label)
        # Marker meta event: FF 06 len text
        marker = b"\xFF\x06" + _encode_variable_length(length) + label
        events.append((tick, marker))

    # End-of-track marker at the last bar
    end_tick = int(arrangement.total_bars * ticks_per_bar)
    events.append((end_tick, b"\xFF\x2F\x00"))

    # Sort by tick
    events.sort(key=lambda e: e[0])

    # Build track data with delta times
    track_data = bytearray()
    last_tick = 0
    for tick, event_data in events:
        delta = tick - last_tick
        track_data.extend(_encode_variable_length(delta))
        track_data.extend(event_data)
        last_tick = tick

    # MIDI file header: MThd
    header = b"MThd"
    header += struct.pack(">I", 6)  # header length
    header += struct.pack(">HHH", 0, 1, ticks_per_beat)  # format, tracks, division

    # Track chunk: MTrk
    track_chunk = b"MTrk"
    track_chunk += struct.pack(">I", len(track_data))
    track_chunk += bytes(track_data)

    return header + track_chunk


def export_csv_markers(arrangement: Arrangement) -> bytes:
    """Export section boundaries as CSV.

    Format: Name, Start (bars), End (bars), Type, Start (seconds), End (seconds)
    """
    bpm = arrangement.bpm if arrangement.bpm > 0 else 120.0
    seconds_per_bar = (60.0 / bpm) * 4.0

    lines = ["Name,Start Bar,End Bar,Type,Start Time (s),End Time (s)"]

    for section in arrangement.sections:
        start_time = section.start_bar * seconds_per_bar
        end_time = section.end_bar * seconds_per_bar
        # Escape commas in labels
        name = section.label.replace(",", ";")
        lines.append(
            f"{name},{section.start_bar:.1f},{section.end_bar:.1f},"
            f"{section.type},{start_time:.3f},{end_time:.3f}"
        )

    return "\n".join(lines).encode("utf-8")


def _label_to_dict(label) -> dict:
    """Convert an interaction label to dict."""
    if hasattr(label, "to_dict"):
        return label.to_dict()
    return {
        "id": getattr(label, "id", ""),
        "sectionId": getattr(label, "section_id", ""),
        "startBar": getattr(label, "start_bar", 0),
        "endBar": getattr(label, "end_bar", 0),
        "label": getattr(label, "label", ""),
    }


def _marker_to_dict(marker) -> dict:
    """Convert a guide marker to dict."""
    return {
        "id": getattr(marker, "id", ""),
        "type": getattr(marker, "type", ""),
        "barPosition": getattr(marker, "bar_position", 0),
        "sectionId": getattr(marker, "section_id", ""),
        "label": getattr(marker, "label", ""),
        "description": getattr(marker, "description", ""),
    }


def _suggestion_to_dict(suggestion) -> dict:
    """Convert a variation suggestion to dict."""
    return {
        "id": getattr(suggestion, "id", ""),
        "type": getattr(suggestion, "type", ""),
        "targetBlockId": getattr(suggestion, "target_block_id", ""),
        "sectionId": getattr(suggestion, "section_id", ""),
        "description": getattr(suggestion, "description", ""),
        "applied": getattr(suggestion, "applied", False),
    }


def _encode_variable_length(value: int) -> bytes:
    """Encode an integer as MIDI variable-length quantity."""
    if value < 0:
        value = 0

    result = bytearray()
    result.append(value & 0x7F)
    value >>= 7

    while value > 0:
        result.append((value & 0x7F) | 0x80)
        value >>= 7

    result.reverse()
    return bytes(result)
