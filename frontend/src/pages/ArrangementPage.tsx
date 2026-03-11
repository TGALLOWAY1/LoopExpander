/**
 * ArrangementPage - Full-song arrangement preview showing generated blocks.
 *
 * Displays the arrangement timeline with color-coded blocks per role,
 * section labels carried over from the Structure Canvas, and controls
 * for generating/regenerating the arrangement.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useProject } from '../context/ProjectContext';
import {
  Arrangement,
  ArrangementBlock,
  generateArrangement,
  getArrangement,
  updateArrangementBlock,
  deleteArrangementBlock,
} from '../api/arrangement';
import { ROLE_COLORS, ROLE_LABELS, StemRole } from '../api/userLoop';
import SuggestionPanel from '../components/arrangement/SuggestionPanel';
import { GuidanceSummary } from '../components/arrangement/GuidanceOverlay';
import GuideMarkerLayer from '../components/arrangement/GuideMarkerLayer';
import BlockToolbar from '../components/arrangement/BlockToolbar';
import './ArrangementPage.css';

interface ArrangementPageProps {
  onBack?: () => void;
}

/** Section type color mapping (matches Structure Canvas). */
const SECTION_COLORS: Record<string, string> = {
  intro: '#4CAF50',
  verse: '#2196F3',
  chorus: '#FF9800',
  bridge: '#9C27B0',
  drop: '#F44336',
  breakdown: '#607D8B',
  build: '#FF5722',
  outro: '#795548',
  low_energy: '#78909C',
  medium_energy: '#42A5F5',
  high_energy: '#EF5350',
};

/** Pixels per bar for the timeline. */
const PX_PER_BAR = 24;
const LANE_HEIGHT = 36;
const SECTION_HEADER_HEIGHT = 32;

export default function ArrangementPage({ onBack }: ArrangementPageProps): JSX.Element {
  const { referenceId } = useProject();

  const [arrangement, setArrangement] = useState<Arrangement | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [suggestionKey, setSuggestionKey] = useState(0);

  // Drag-resize state
  const [resizing, setResizing] = useState<{
    blockId: string;
    edge: 'left' | 'right';
    startX: number;
    originalStart: number;
    originalEnd: number;
  } | null>(null);
  const resizingRef = useRef(resizing);
  resizingRef.current = resizing;

  // Try to load existing arrangement on mount
  useEffect(() => {
    if (!referenceId) return;
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getArrangement(referenceId);
        if (!cancelled) setArrangement(data);
      } catch {
        // No arrangement yet — that's fine
        if (!cancelled) setArrangement(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => { cancelled = true; };
  }, [referenceId]);

  const handleGenerate = useCallback(async () => {
    if (!referenceId) return;
    setGenerating(true);
    setError(null);
    try {
      const data = await generateArrangement(referenceId);
      setArrangement(data);
      setSuggestionKey((k) => k + 1); // Refresh suggestions panel
    } catch (err: any) {
      setError(err.message || 'Failed to generate arrangement');
    } finally {
      setGenerating(false);
    }
  }, [referenceId]);

  const handleSuggestionApplied = useCallback((updatedArrangement: Arrangement) => {
    setArrangement(updatedArrangement);
  }, []);

  const handleToggleBlock = useCallback(async (block: ArrangementBlock) => {
    if (!referenceId || !arrangement) return;
    try {
      const result = await updateArrangementBlock(referenceId, block.id, {
        active: !block.active,
      });
      setArrangement((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          blocks: prev.blocks.map((b) =>
            b.id === block.id ? result.block : b,
          ),
        };
      });
    } catch (err: any) {
      setError(err.message);
    }
  }, [referenceId, arrangement]);

  const handleDeleteBlock = useCallback(async (block: ArrangementBlock) => {
    if (!referenceId || !arrangement) return;
    try {
      await deleteArrangementBlock(referenceId, block.id);
      setArrangement((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          blocks: prev.blocks.filter((b) => b.id !== block.id),
        };
      });
      setSelectedBlockId(null);
    } catch (err: any) {
      setError(err.message);
    }
  }, [referenceId, arrangement]);

  // Drag-resize handlers
  const handleResizeStart = useCallback((
    e: React.MouseEvent,
    blockId: string,
    edge: 'left' | 'right',
    block: ArrangementBlock,
  ) => {
    e.stopPropagation();
    e.preventDefault();
    setResizing({
      blockId,
      edge,
      startX: e.clientX,
      originalStart: block.startBar,
      originalEnd: block.endBar,
    });
  }, []);

  useEffect(() => {
    if (!resizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const r = resizingRef.current;
      if (!r || !arrangement) return;

      const deltaX = e.clientX - r.startX;
      const deltaBars = Math.round(deltaX / PX_PER_BAR);

      setArrangement((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          blocks: prev.blocks.map((b) => {
            if (b.id !== r.blockId) return b;
            if (r.edge === 'left') {
              const newStart = Math.max(0, r.originalStart + deltaBars);
              if (newStart >= b.endBar) return b;
              return { ...b, startBar: newStart };
            } else {
              const newEnd = Math.min(prev.totalBars, r.originalEnd + deltaBars);
              if (newEnd <= b.startBar) return b;
              return { ...b, endBar: newEnd };
            }
          }),
        };
      });
    };

    const handleMouseUp = async () => {
      const r = resizingRef.current;
      if (!r || !referenceId || !arrangement) {
        setResizing(null);
        return;
      }

      // Find the block to save its new position
      const block = arrangement.blocks.find((b) => b.id === r.blockId);
      if (block && (block.startBar !== r.originalStart || block.endBar !== r.originalEnd)) {
        try {
          await updateArrangementBlock(referenceId, r.blockId, {
            startBar: block.startBar,
            endBar: block.endBar,
          });
        } catch (err: any) {
          // Revert on error
          setArrangement((prev) => {
            if (!prev) return prev;
            return {
              ...prev,
              blocks: prev.blocks.map((b) =>
                b.id === r.blockId
                  ? { ...b, startBar: r.originalStart, endBar: r.originalEnd }
                  : b,
              ),
            };
          });
          setError(err.message);
        }
      }
      setResizing(null);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [resizing, referenceId, arrangement]);

  // Deselect on background click
  const handleTimelineClick = useCallback((e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (!target.closest('.arr-block')) {
      setSelectedBlockId(null);
    }
  }, []);

  // Find the selected block and compute its position for the toolbar
  const selectedBlock = arrangement?.blocks.find((b) => b.id === selectedBlockId) ?? null;

  if (!referenceId) {
    return (
      <div className="arr-page">
        <div className="arr-empty">
          <h3>No Reference Loaded</h3>
          <p>Upload and analyze a reference track first, then upload your loop material.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="arr-page">
        <div className="arr-loading">Loading arrangement...</div>
      </div>
    );
  }

  // Get unique roles from blocks, ordered
  const roles = arrangement
    ? Array.from(new Set(arrangement.blocks.map((b) => b.role))).sort()
    : [];

  const totalBars = arrangement?.totalBars ?? 0;
  const timelineWidth = totalBars * PX_PER_BAR;

  return (
    <div className="arr-page">
      {/* Header */}
      <div className="arr-header">
        <div className="arr-header-left">
          {onBack && (
            <button className="arr-back-btn" onClick={onBack}>
              Back
            </button>
          )}
          <h2>Arrangement Preview</h2>
          {arrangement && (
            <span className="arr-meta">
              {arrangement.sections.length} sections | {arrangement.blocks.length} blocks | {arrangement.totalBars} bars | {arrangement.bpm} BPM
            </span>
          )}
        </div>
        <div className="arr-header-right">
          {arrangement && (
            <button
              className={`arr-toggle-btn ${showSuggestions ? 'active' : ''}`}
              onClick={() => setShowSuggestions((v) => !v)}
            >
              {showSuggestions ? 'Hide Suggestions' : 'Show Suggestions'}
            </button>
          )}
          <button
            className="arr-generate-btn"
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating
              ? 'Generating...'
              : arrangement
              ? 'Regenerate'
              : 'Generate Arrangement'}
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="arr-error-banner">
          {error}
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {/* Content */}
      {!arrangement ? (
        <div className="arr-empty-state">
          <h3>No Arrangement Generated</h3>
          <p>
            Make sure you have analyzed a reference track and uploaded loop material,
            then click "Generate Arrangement" to auto-arrange your loops across the
            reference structure.
          </p>
          <button
            className="arr-generate-btn large"
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? 'Generating...' : 'Generate Arrangement'}
          </button>
        </div>
      ) : (
        <>
        <div className="arr-main-layout">
        <div className="arr-content">
          {/* Section header row */}
          <div className="arr-timeline-container">
            <div className="arr-role-label-col" style={{ height: SECTION_HEADER_HEIGHT }}>
              <span className="arr-col-header">Sections</span>
            </div>
            <div className="arr-timeline-scroll">
              <div
                className="arr-section-row"
                style={{ width: timelineWidth, height: SECTION_HEADER_HEIGHT }}
              >
                {arrangement.sections.map((section) => {
                  const left = section.startBar * PX_PER_BAR;
                  const width = (section.endBar - section.startBar) * PX_PER_BAR;
                  const color = SECTION_COLORS[section.type] || '#9E9E9E';
                  return (
                    <div
                      key={section.id}
                      className="arr-section-block"
                      style={{
                        left,
                        width,
                        backgroundColor: color,
                      }}
                      title={`${section.label} (${section.type}): bars ${section.startBar}–${section.endBar}`}
                    >
                      <span className="arr-section-label">{section.label}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Guide markers layer */}
          {referenceId && (
            <div className="arr-timeline-container">
              <div className="arr-role-label-col" style={{ height: 28 }}>
                <span className="arr-col-header">Guides</span>
              </div>
              <div className="arr-timeline-scroll">
                <div style={{ width: timelineWidth, position: 'relative' }}>
                  <GuideMarkerLayer
                    key={`gm-${suggestionKey}`}
                    projectId={referenceId}
                    pxPerBar={PX_PER_BAR}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Role lanes */}
          {roles.map((role, roleIndex) => {
            const roleBlocks = arrangement.blocks.filter((b) => b.role === role);
            const roleLabel = ROLE_LABELS[role as StemRole] || role;
            const roleColor = ROLE_COLORS[role as StemRole] || '#9E9E9E';

            return (
              <div key={role} className="arr-timeline-container">
                <div
                  className="arr-role-label-col"
                  style={{ height: LANE_HEIGHT }}
                >
                  <span
                    className="arr-role-dot"
                    style={{ backgroundColor: roleColor }}
                  />
                  <span className="arr-role-name">{roleLabel}</span>
                </div>
                <div className="arr-timeline-scroll">
                  <div
                    className="arr-lane"
                    style={{ width: timelineWidth, height: LANE_HEIGHT }}
                    onClick={handleTimelineClick}
                  >
                    {/* Bar grid lines */}
                    {Array.from({ length: totalBars }, (_, i) => (
                      <div
                        key={i}
                        className="arr-bar-line"
                        style={{ left: i * PX_PER_BAR }}
                      />
                    ))}

                    {/* Blocks */}
                    {roleBlocks.map((block) => {
                      const left = block.startBar * PX_PER_BAR;
                      const width = (block.endBar - block.startBar) * PX_PER_BAR;
                      const isSelected = block.id === selectedBlockId;

                      return (
                        <div
                          key={block.id}
                          className={`arr-block ${!block.active ? 'muted' : ''} ${isSelected ? 'selected' : ''} ${resizing?.blockId === block.id ? 'resizing' : ''}`}
                          style={{
                            left,
                            width: Math.max(width - 1, 1),
                            backgroundColor: block.active
                              ? roleColor
                              : 'transparent',
                            borderColor: roleColor,
                          }}
                          title={`${role} | bars ${block.startBar.toFixed(1)}–${block.endBar.toFixed(1)}${block.variationType ? ` | ${block.variationType}` : ''}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedBlockId(block.id);
                          }}
                          onDoubleClick={() => handleToggleBlock(block)}
                        >
                          {/* Resize handles */}
                          {isSelected && (
                            <>
                              <div
                                className="arr-resize-handle left"
                                onMouseDown={(e) => handleResizeStart(e, block.id, 'left', block)}
                              />
                              <div
                                className="arr-resize-handle right"
                                onMouseDown={(e) => handleResizeStart(e, block.id, 'right', block)}
                              />
                            </>
                          )}
                          {block.variationType && (
                            <span className="arr-block-badge">
                              {block.variationType}
                            </span>
                          )}
                          {/* Block toolbar for selected block */}
                          {isSelected && selectedBlock && (
                            <BlockToolbar
                              block={selectedBlock}
                              positionLeft={0}
                              positionTop={0}
                              onToggleMute={handleToggleBlock}
                              onDelete={handleDeleteBlock}
                              onClose={() => setSelectedBlockId(null)}
                            />
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Legend */}
          <div className="arr-legend">
            <span className="arr-legend-title">Roles:</span>
            {roles.map((role) => (
              <span key={role} className="arr-legend-item">
                <span
                  className="arr-legend-dot"
                  style={{
                    backgroundColor: ROLE_COLORS[role as StemRole] || '#9E9E9E',
                  }}
                />
                {ROLE_LABELS[role as StemRole] || role}
              </span>
            ))}
            <span className="arr-legend-sep">|</span>
            <span className="arr-legend-hint">
              Click to select | Double-click to mute/unmute | Drag edges to resize
            </span>
          </div>
        </div>

        {/* Suggestion Panel (side panel) */}
        {showSuggestions && referenceId && (
          <SuggestionPanel
            key={suggestionKey}
            projectId={referenceId}
            onArrangementUpdate={handleSuggestionApplied}
          />
        )}
        </div>

        {/* Guidance Summary (below timeline) */}
        {referenceId && (
          <GuidanceSummary key={`guid-${suggestionKey}`} projectId={referenceId} />
        )}
        </>
      )}
    </div>
  );
}
