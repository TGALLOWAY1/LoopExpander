import React, { useState, useCallback, useRef } from 'react';
import {
  InteractionLabel,
  InteractionLabelCreate,
  LABEL_COLORS,
  InteractionLabelType,
} from '../../api/interactions';

interface InteractionLabelerProps {
  labels: InteractionLabel[];
  totalBars: number;
  barWidth: number;
  activeLabelType: InteractionLabelType;
  role: string;
  onCreateLabel: (label: InteractionLabelCreate) => void;
  onDeleteLabel: (labelId: string) => void;
  onUpdateLabel: (labelId: string, updates: Partial<InteractionLabel>) => void;
}

export const InteractionLabeler: React.FC<InteractionLabelerProps> = ({
  labels,
  totalBars,
  barWidth,
  activeLabelType,
  role,
  onCreateLabel,
  onDeleteLabel,
  onUpdateLabel,
}) => {
  const timelineWidth = totalBars * barWidth;
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);
  const [selectedLabelId, setSelectedLabelId] = useState<string | null>(null);
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
      // Just pass empty sectionId since labels are tied to roles now
      onCreateLabel({
        sectionId: '',
        role,
        startBar,
        endBar,
        label: activeLabelType,
        color: LABEL_COLORS[activeLabelType] || '#9E9E9E',
      });
    }

    setDragStart(null);
    setDragEnd(null);
  }, [dragStart, dragEnd, activeLabelType, role, onCreateLabel]);

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

  // Filter labels for this specific role
  const roleLabels = labels.filter((lbl) => lbl.role === role);

  return (
    <div
      ref={rowRef}
      className="sc-interaction-canvas sc-role-segments-row"
      style={{ width: `${timelineWidth}px`, height: '28px', position: 'relative', background: 'transparent' }}
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
      {/* Existing labels */}
      {roleLabels.map((label) => (
        <div
          key={label.id}
          className={`sc-interaction-label ${selectedLabelId === label.id ? 'selected' : ''}`}
          style={{
            left: `${label.startBar * barWidth}px`,
            width: `${(label.endBar - label.startBar) * barWidth}px`,
            backgroundColor: label.color || LABEL_COLORS[label.label] || '#9E9E9E',
          }}
          onClick={(e) => handleLabelClick(e, label.id)}
        >
          <span className="sc-interaction-label-text">{label.label}</span>
        </div>
      ))}

      {/* Drag preview */}
      {dragStart !== null && dragEnd !== null && Math.abs(dragEndBar - dragStartBar) >= 1 && (
        <div
          className="sc-interaction-label preview"
          style={{
            left: `${dragStartBar * barWidth}px`,
            width: `${(dragEndBar - dragStartBar) * barWidth}px`,
            borderColor: LABEL_COLORS[activeLabelType] || '#9E9E9E',
            backgroundColor: `${LABEL_COLORS[activeLabelType] || '#9E9E9E'}40`, // 40 is hex opacity
          }}
        >
          <span className="sc-interaction-label-text">{activeLabelType}</span>
        </div>
      )}

      {/* Label Editor Popover */}
      {selectedLabelId && (
        <div
          className="sc-section-editor"
          style={{
            position: 'absolute',
            top: '32px',
            left: `${((roleLabels.find((l) => l.id === selectedLabelId)?.startBar) || 0) * barWidth}px`,
            zIndex: 100,
            width: '240px',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="sc-editor-field">
            <label>Notes</label>
            <input
              type="text"
              value={roleLabels.find((l) => l.id === selectedLabelId)?.notes || ''}
              onChange={(e) => onUpdateLabel(selectedLabelId, { notes: e.target.value })}
              placeholder="e.g. build up energy"
            />
          </div>
          <div className="sc-editor-actions" style={{ justifyContent: 'space-between' }}>
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
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
