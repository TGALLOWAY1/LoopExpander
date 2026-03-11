/**
 * SectionEditor - Sidebar panel for editing the selected section.
 *
 * Supports renaming, retyping, splitting, and merging sections.
 */
import React, { useState, useEffect } from 'react';
import { CanvasSection } from '../../api/structureCanvas';

const SECTION_TYPES = [
  'intro',
  'verse',
  'chorus',
  'bridge',
  'drop',
  'breakdown',
  'build',
  'outro',
  'custom',
];

interface SectionEditorProps {
  section: CanvasSection;
  sections: CanvasSection[];
  onUpdate: (sectionId: string, patch: Partial<CanvasSection>) => void;
  onSplit: (sectionId: string, splitBar: number) => void;
  onMerge: (sectionId: string) => void;
  onDeselect: () => void;
}

export const SectionEditor: React.FC<SectionEditorProps> = ({
  section,
  sections,
  onUpdate,
  onSplit,
  onMerge,
  onDeselect,
}) => {
  const [label, setLabel] = useState(section.label || section.name);
  const [type, setType] = useState(section.type);
  const [splitBar, setSplitBar] = useState(
    Math.floor((section.startBar + section.endBar) / 2),
  );

  // Reset local state when section changes
  useEffect(() => {
    setLabel(section.label || section.name);
    setType(section.type);
    setSplitBar(Math.floor((section.startBar + section.endBar) / 2));
  }, [section.id, section.label, section.name, section.type, section.startBar, section.endBar]);

  const sectionIndex = sections.findIndex((s) => s.id === section.id);
  const canMerge = sectionIndex >= 0 && sectionIndex < sections.length - 1;
  const sectionLength = Math.round(section.endBar - section.startBar);
  const canSplit = sectionLength > 2;

  const handleLabelBlur = () => {
    if (label.trim() && label !== section.label) {
      onUpdate(section.id, { label: label.trim(), name: label.trim() });
    }
  };

  const handleTypeChange = (newType: string) => {
    setType(newType);
    onUpdate(section.id, { type: newType });
  };

  return (
    <div className="sc-section-editor">
      <h3>
        <span
          className="sc-section-color-dot"
          style={{ background: section.color, width: 12, height: 12, borderRadius: '50%', display: 'inline-block' }}
        />
        Edit Section
        <button
          className="sc-editor-btn"
          onClick={onDeselect}
          style={{ marginLeft: 'auto', fontSize: '0.75rem' }}
        >
          Close
        </button>
      </h3>

      {/* Name */}
      <div className="sc-editor-field">
        <label>Name</label>
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onBlur={handleLabelBlur}
          onKeyDown={(e) => { if (e.key === 'Enter') handleLabelBlur(); }}
        />
      </div>

      {/* Type */}
      <div className="sc-editor-field">
        <label>Type</label>
        <select value={type} onChange={(e) => handleTypeChange(e.target.value)}>
          {SECTION_TYPES.map((t) => (
            <option key={t} value={t}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Bar range (read-only info) */}
      <div className="sc-editor-field">
        <label>Bar Range</label>
        <input
          type="text"
          value={`${Math.round(section.startBar)} - ${Math.round(section.endBar)} (${sectionLength} bars)`}
          readOnly
          style={{ background: '#f5f5f5', cursor: 'default' }}
        />
      </div>

      {/* Actions */}
      <div className="sc-editor-actions">
        {canSplit && (
          <>
            <div className="sc-editor-field" style={{ flex: 1, marginBottom: 0 }}>
              <label>Split at bar</label>
              <div style={{ display: 'flex', gap: 4 }}>
                <input
                  type="number"
                  min={Math.ceil(section.startBar) + 1}
                  max={Math.floor(section.endBar) - 1}
                  value={splitBar}
                  onChange={(e) => setSplitBar(Number(e.target.value))}
                  style={{ width: 70 }}
                />
                <button
                  className="sc-editor-btn primary"
                  onClick={() => onSplit(section.id, splitBar)}
                >
                  Split
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      <div className="sc-editor-actions" style={{ marginTop: 8 }}>
        {canMerge && (
          <button
            className="sc-editor-btn"
            onClick={() => onMerge(section.id)}
            title={`Merge with "${sections[sectionIndex + 1]?.label || sections[sectionIndex + 1]?.name}"`}
          >
            Merge with next
          </button>
        )}
      </div>
    </div>
  );
};
