/**
 * GuideMarkerLayer - Renders guide markers as labeled flags/pins on the timeline (Phase 7B).
 *
 * Guide markers have a distinct visual style from arrangement blocks
 * (dashed borders, lighter colors). Tooltip with description on hover.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  GuideMarker,
  getGuideMarkers,
  MARKER_TYPE_COLORS,
  MARKER_TYPE_ICONS,
} from '../../api/suggestions';
import './GuideMarkerLayer.css';

interface GuideMarkerLayerProps {
  projectId: string;
  pxPerBar: number;
  /** Top offset in pixels for positioning markers. */
  topOffset?: number;
}

export default function GuideMarkerLayer({
  projectId,
  pxPerBar,
  topOffset = 0,
}: GuideMarkerLayerProps): JSX.Element {
  const [markers, setMarkers] = useState<GuideMarker[]>([]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadMarkers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getGuideMarkers(projectId);
      setMarkers(data.markers);
    } catch {
      // Non-critical
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadMarkers();
  }, [loadMarkers]);

  if (loading || markers.length === 0) {
    return <></>;
  }

  return (
    <div className="gm-layer" style={{ top: topOffset }}>
      {markers.map((marker) => {
        const left = marker.barPosition * pxPerBar;
        const color = MARKER_TYPE_COLORS[marker.type] || '#9E9E9E';
        const icon = MARKER_TYPE_ICONS[marker.type] || '?';
        const isHovered = marker.id === hoveredId;

        return (
          <div
            key={marker.id}
            className="gm-marker"
            style={{ left }}
            onMouseEnter={() => setHoveredId(marker.id)}
            onMouseLeave={() => setHoveredId(null)}
          >
            <div className="gm-stem" style={{ borderColor: color }} />
            <div
              className="gm-flag"
              style={{
                backgroundColor: color,
                borderColor: color,
              }}
              title={marker.description}
            >
              <span className="gm-icon">{icon}</span>
            </div>

            {isHovered && (
              <div className="gm-tooltip">
                <div className="gm-tooltip-label">{marker.label}</div>
                <div className="gm-tooltip-desc">{marker.description}</div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
