"""API routes for export (Phase 9)."""
import io
import zipfile
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

from models.store import (
    ARRANGEMENTS,
    USER_LOOPS,
    INTERACTION_LABELS,
    GUIDE_MARKERS,
    VARIATION_SUGGESTIONS,
)
from export.stem_exporter import render_all_stems
from export.marker_exporter import (
    export_arrangement_json,
    export_midi_markers,
    export_csv_markers,
)
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/project", tags=["export"])


class ExportRequest(BaseModel):
    """Request payload for export."""
    includeStems: bool = True
    includeMarkersMidi: bool = True
    includeStructureJson: bool = True
    includeMarkersCsv: bool = False
    stemFormat: str = "wav16"  # "wav16", "wav24", "aiff"


@router.post("/{project_id}/export")
async def export_arrangement(project_id: str, request: ExportRequest):
    """Export the arrangement as a ZIP bundle.

    Includes per-role WAV stems, MIDI markers, and structure JSON
    based on the request options.

    Returns:
        ZIP file as download.
    """
    arrangement = ARRANGEMENTS.get(project_id)
    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No arrangement found for project {project_id}.",
        )

    zip_buffer = io.BytesIO()

    try:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Stem exports
            if request.includeStems:
                loop_bundle = USER_LOOPS.get(project_id)
                if loop_bundle and loop_bundle.stems:
                    logger.info(f"Rendering stems for export ({request.stemFormat})")
                    stems = render_all_stems(
                        arrangement=arrangement,
                        loop_bundle=loop_bundle,
                        export_format=request.stemFormat,
                    )
                    for filename, audio_bytes in stems.items():
                        zf.writestr(f"stems/{filename}", audio_bytes)
                    logger.info(f"Added {len(stems)} stem files to export")
                else:
                    logger.warning("No user loops available for stem export")

            # Structure JSON
            if request.includeStructureJson:
                interaction_labels = INTERACTION_LABELS.get(project_id, [])
                guide_markers = GUIDE_MARKERS.get(project_id, [])
                suggestions = VARIATION_SUGGESTIONS.get(project_id, [])

                json_bytes = export_arrangement_json(
                    arrangement=arrangement,
                    interaction_labels=interaction_labels,
                    guide_markers=guide_markers,
                    suggestions=suggestions,
                )
                zf.writestr("arrangement.json", json_bytes)

            # MIDI markers
            if request.includeMarkersMidi:
                midi_bytes = export_midi_markers(arrangement)
                zf.writestr("markers.mid", midi_bytes)

            # CSV markers
            if request.includeMarkersCsv:
                csv_bytes = export_csv_markers(arrangement)
                zf.writestr("markers.csv", csv_bytes)

        zip_buffer.seek(0)
        zip_bytes = zip_buffer.read()

        logger.info(
            f"Export complete for {project_id}: "
            f"{len(zip_bytes)} bytes ZIP"
        )

        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="loopexpander_export_{project_id[:8]}.zip"',
            },
        )

    except Exception as e:
        logger.error(f"Export failed for {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )
