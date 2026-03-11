/**
 * GuidanceOverlay - Inline guidance indicators on the arrangement timeline (Phase 6C).
 *
 * Shows colored markers/badges on timeline sections with expandable messages.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  GuidanceMessage,
  GuidanceResponse,
  getGuidance,
  SEVERITY_COLORS,
  GUIDANCE_TYPE_LABELS,
} from '../../api/suggestions';
import './GuidanceOverlay.css';

interface GuidanceOverlayProps {
  projectId: string;
  /** Mapping of section ID to pixel-left position on the timeline. */
  sectionPositions: Record<string, { left: number; width: number }>;
}

export default function GuidanceOverlay({
  projectId,
  sectionPositions,
}: GuidanceOverlayProps): JSX.Element {
  const [messages, setMessages] = useState<GuidanceMessage[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadGuidance = useCallback(async () => {
    setLoading(true);
    try {
      const data: GuidanceResponse = await getGuidance(projectId);
      setMessages(data.messages);
    } catch {
      // Guidance is non-critical
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadGuidance();
  }, [loadGuidance]);

  if (loading || messages.length === 0) {
    return <></>;
  }

  // Group messages by section
  const bySection: Record<string, GuidanceMessage[]> = {};
  for (const msg of messages) {
    if (!bySection[msg.sectionId]) {
      bySection[msg.sectionId] = [];
    }
    bySection[msg.sectionId].push(msg);
  }

  return (
    <div className="guid-overlay">
      {Object.entries(bySection).map(([sectionId, sectionMsgs]) => {
        const pos = sectionPositions[sectionId];
        if (!pos) return null;

        // Use highest severity for the badge color
        const maxSeverity = sectionMsgs.some((m) => m.severity === 'warning')
          ? 'warning'
          : sectionMsgs.some((m) => m.severity === 'suggestion')
          ? 'suggestion'
          : 'info';

        const badgeColor = SEVERITY_COLORS[maxSeverity] || '#9E9E9E';
        const isExpanded = sectionMsgs.some((m) => m.id === expandedId);

        return (
          <div
            key={sectionId}
            className="guid-section-markers"
            style={{ left: pos.left + pos.width - 16 }}
          >
            <div
              className="guid-badge"
              style={{ backgroundColor: badgeColor }}
              title={`${sectionMsgs.length} guidance message(s)`}
              onClick={() =>
                setExpandedId(isExpanded ? null : sectionMsgs[0].id)
              }
            >
              {sectionMsgs.length}
            </div>

            {isExpanded && (
              <div className="guid-popup">
                {sectionMsgs.map((msg) => (
                  <div key={msg.id} className={`guid-msg severity-${msg.severity}`}>
                    <div className="guid-msg-header">
                      <span
                        className="guid-severity-dot"
                        style={{ backgroundColor: SEVERITY_COLORS[msg.severity] }}
                      />
                      <span className="guid-msg-type">
                        {GUIDANCE_TYPE_LABELS[msg.type] || msg.type}
                      </span>
                    </div>
                    <p className="guid-msg-text">{msg.message}</p>
                    {msg.actionHint && (
                      <p className="guid-msg-hint">{msg.actionHint}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/**
 * GuidanceSummary - Compact summary of all guidance messages, shown below timeline.
 */
interface GuidanceSummaryProps {
  projectId: string;
}

export function GuidanceSummary({ projectId }: GuidanceSummaryProps): JSX.Element {
  const [messages, setMessages] = useState<GuidanceMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadGuidance = useCallback(async () => {
    setLoading(true);
    try {
      const data: GuidanceResponse = await getGuidance(projectId);
      setMessages(data.messages);
    } catch {
      // Non-critical
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadGuidance();
  }, [loadGuidance]);

  if (loading || messages.length === 0) {
    return <></>;
  }

  const warnings = messages.filter((m) => m.severity === 'warning');
  const suggestionsOnly = messages.filter((m) => m.severity === 'suggestion');
  const info = messages.filter((m) => m.severity === 'info');

  return (
    <div className="guid-summary">
      <div className="guid-summary-header">
        <span className="guid-summary-title">Guidance</span>
        {warnings.length > 0 && (
          <span className="guid-count-badge warning">{warnings.length} warnings</span>
        )}
        {suggestionsOnly.length > 0 && (
          <span className="guid-count-badge suggestion">{suggestionsOnly.length} suggestions</span>
        )}
        {info.length > 0 && (
          <span className="guid-count-badge info">{info.length} info</span>
        )}
      </div>
      <div className="guid-summary-list">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`guid-summary-item severity-${msg.severity}`}
            onClick={() => setExpandedId(expandedId === msg.id ? null : msg.id)}
          >
            <span
              className="guid-severity-dot"
              style={{ backgroundColor: SEVERITY_COLORS[msg.severity] }}
            />
            <span className="guid-summary-text">{msg.message}</span>
            {expandedId === msg.id && msg.actionHint && (
              <p className="guid-summary-hint">{msg.actionHint}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
