/**
 * InteractionLabeler - Draw and manage interaction labels on the timeline.
 *
 * Allows users to create labeled regions (A, B, call, response, fill, etc.)
 * directly on the timeline with drag-to-create, resize, and delete functionality.
 */
import React, { useState, useCallback, useRef } from 'react';
import {
  InteractionLabel,
  InteractionLabelCreate,
  INTERACTION_LABEL_TYPES,
  LABEL_COLORS,
  InteractionLabelType,
} from '../../api/interactions';
import { CanvasSection } from '../../api/structureCanvas';

interface InteractionLabelerProps {
  labels: InteractionLabel[];
  sections: CanvasSection[];
  totalBars: number;
  barWidth: number;
  activeLabelType: InteractionLabelType;
  onLabelTypeChange: (type: InteractionLabelType) => void;
  onCreateLabel: (label: InteractionLabelCreate) => void;
  onDeleteLabel: (labelId: string) => void;
  onUpdateLabel: (labelId: string, updates: Partial<InteractionLabel>) => void;
  onDuplicatePattern: (sourceSectionId: string, targetSectionId: string) => void;
}

export const InteractionLabeler: React.FC<InteractionLabelerProps> = ({
  labels,
  sections,
  totalBars,
  barWidth,
  activeLabelType,
  onLabelTypeChange,
  onCreateLabel,
  onDeleteLabel,
  onUpdateLabel,
  onDuplicatePattern,
}) => {
  const timelineWidth = totalBars * barWidth;
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);
  const [selectedLabelId, setSelectedLabelId] = useState<string | null>(null);
  const [duplicateSource, setDuplicateSource] = useState<string | null>(null);
  const rowRef = useRef<HTMLDivElement>(null);

  const getBarFromMouse = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!rowRef.current) return 0;
      const rect = rowRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left + rowRef.current.scrollLeft;
      return Math.max(0, Math.min(totalBars, Math.round(x / barWidth)));
    },
    [barWidth, totalBars],
  );

  const findSectionForBar = useCallback(
    (bar: number): CanvasSection | undefined => {
      return sections.find((s) => bar >= s.startBar && bar < s.endBar);
    },
    [sections],
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.button !== 0) return;
      const bar = getBarFromMouse(e);
      setDragStart(bar);
      setDragEnd(bar);
      setSelectedLabelId(null);
    },
    [getBarFromMouse],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (dragStart === null) return;
      setDragEnd(getBarFromMouse(e));
    },
    [dragStart, getBarFromMouse],
  );

  const handleMouseUp = useCallback(() => {
    if (dragStart === null || dragEnd === null) return;

    const startBar = Math.min(dragStart, dragEnd);
    const endBar = Math.max(dragStart, dragEnd);

    if (endBar - startBar >= 1) {
      // Find which section this belongs to
      const section = findSectionForBar(startBar);
      const sectionId = section?.id || '';

      onCreateLabel({
        sectionId,
        startBar,
        endBar,
        label: activeLabelType,
        color: LABEL_COLORS[activeLabelType] || '#9E9E9E',
      });
    }

    setDragStart(null);
    setDragEnd(null);
  }, [dragStart, dragEnd, activeLabelType, findSectionForBar, onCreateLabel]);

  const handleLabelClick = useCallback(
    (e: React.MouseEvent, labelId: string) => {
      e.stopPropagation();
      setSelectedLabelId(labelId === selectedLabelId ? null : labelId);
    },
    [selectedLabelId],
  );

  // Compute drag preview
  const dragStartBar = dragStart !== null && dragEnd !== null ? Math.min(dragStart, dragEnd) : 0;
  const dragEndBar = dragStart !== null && dragEnd !== null ? Math.max(dragStart, dragEnd) : 0;

  return (
    <div className="sc-interaction-labeler">
      {/* Label type selector toolbar */}
      <div className="sc-interaction-toolbar">
        <div className="sc-lane-label">Labels</div>
        <div className="sc-interaction-type-selector">
          {INTERACTION_LABEL_TYPES.map((type) => (
            <button
              key={type}
              className={`sc-label-type-btn ${activeLabelType === type ? 'active' : ''}`}
              style={{
                borderColor: activeLabelType === type ? LABEL_COLORS[type] : '#ddd',
                background: activeLabelType === type ? LABEL_COLORS[type] : '#fff',
                color: activeLabelType === type ? '#fff' : '#555',
              }}
              onClick={() => onLabelTypeChange(type as InteractionLabelType)}
            >
              {type}
            </button>
          ))}
        </div>
        {/* Duplicate pattern controls */}
        {duplicateSource && (
          <div className="sc-duplicate-controls">
            <span className="sc-duplicate-hint">Select target section:</span>
            {sections
              .filter((s) => s.id !== duplicateSource)
              .map((s) => (
                <button
                  key={s.id}
                  className="sc-editor-btn"
                  onClick={() => {
                    onDuplicatePattern(duplicateSource, s.id);
                    setDuplicateSource(null);
                  }}
                >
                  {s.label || s.name}
                </button>
              ))}
            <button
              className="sc-editor-btn danger"
              onClick={() => setDuplicateSource(null)}
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* Label timeline row */}
      <div className="sc-interaction-row">
        <div className="sc-lane-label" style={{ fontSize: '0.7rem' }}>
          Interactions
        </div>
        <div className="sc-timeline-scroll">
          <div
            ref={rowRef}
            className="sc-interaction-canvas"
            style={{ width: `${timelineWidth}px` }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={() => {
              if (dragStart !== null) {
                setDragStart(null);
                setDragEnd(null);
              }
            }}
          >
            {/* Grid lines */}
            {Array.from({ length: totalBars }, (_, i) => (
              <div
                key={i}
                className={`sc-grid-line ${i % 4 === 0 ? 'major' : 'minor'}`}
                style={{ left: `${i * barWidth}px` }}
              />
            ))}

            {/* Existing labels */}
            {labels.map((label) => (
              <div
                key={label.id}
                className={`sc-interaction-label ${selectedLabelId === label.id ? 'selected' : ''}`}
                style={{
                  left: `${label.startBar * barWidth}px`,
                  width: `${(label.endBar - label.startBar) * barWidth}px`,
                  background: label.color || LABEL_COLORS[label.label] || '#9E9E9E',
                }}
                onClick={(e) => handleLabelClick(e, label.id)}
                title={`${label.label} (bars ${label.startBar}-${label.endBar})${label.notes ? '\n' + label.notes : ''}`}
              >
                <span className="sc-interaction-label-text">{label.label}</span>
              </div>
            ))}

            {/* Drag preview */}
            {dragStart !== null && dragEnd !== null && dragEndBar - dragStartBar >= 1 && (
              <div
                className="sc-interaction-label preview"
                style={{
                  left: `${dragStartBar * barWidth}px`,
                  width: `${(dragEndBar - dragStartBar) * barWidth}px`,
                  background: LABEL_COLORS[activeLabelType] || '#9E9E9E',
                }}
              >
                <span className="sc-interaction-label-text">{activeLabelType}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Selected label actions */}
      {selectedLabelId && (
        <div className="sc-interaction-actions">
          <span className="sc-interaction-actions-label">Selected:</span>
          <select
            value={labels.find((l) => l.id === selectedLabelId)?.label || ''}
            onChange={(e) =>
              onUpdateLabel(selectedLabelId, {
                label: e.target.value,
                color: LABEL_COLORS[e.target.value] || null,
              })
            }
          >
            {INTERACTION_LABEL_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
          {(() => {
            const label = labels.find((l) => l.id === selectedLabelId);
            if (!label) return null;
            const section = sections.find((s) => s.id === label.sectionId);
            return section ? (
              <button
                className="sc-editor-btn"
                onClick={() => setDuplicateSource(label.sectionId)}
              >
                Duplicate to...
              </button>
            ) : null;
          })()}
          <button
            className="sc-editor-btn danger"
            onClick={() => {
              onDeleteLabel(selectedLabelId);
              setSelectedLabelId(null);
            }}
          >
            Delete
          </button>
          <button
            className="sc-editor-btn"
            onClick={() => setSelectedLabelId(null)}
          >
            Deselect
          </button>
        </div>
      )}
    </div>
  );
};
