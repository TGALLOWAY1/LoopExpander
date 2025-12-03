/**
 * NotesPanel component for editing block notes.
 * 
 * Displays a textarea for editing notes on the selected block.
 */
import React, { useState, useEffect } from 'react';
import { AnnotationBlock } from '../../api/reference';
import './NotesPanel.css';

interface NotesPanelProps {
  selectedBlock?: AnnotationBlock;
  onChangeNotes: (blockId: string, notes: string) => void;
}

export const NotesPanel: React.FC<NotesPanelProps> = ({
  selectedBlock,
  onChangeNotes,
}) => {
  const [notesValue, setNotesValue] = useState(selectedBlock?.notes || '');

  // Sync notesValue when selectedBlock changes
  useEffect(() => {
    setNotesValue(selectedBlock?.notes || '');
  }, [selectedBlock?.id, selectedBlock?.notes]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setNotesValue(newValue);
  };

  const handleBlur = () => {
    if (selectedBlock) {
      onChangeNotes(selectedBlock.id, notesValue);
    }
  };

  if (!selectedBlock) {
    return (
      <div className="notes-panel empty">
        <h3>Block Notes</h3>
        <p className="notes-panel-empty-message">
          Select a block to edit its notes.
        </p>
      </div>
    );
  }

  return (
    <div className="notes-panel">
      <h3>Block Notes</h3>
      <div className="notes-panel-block-info">
        <span className="notes-panel-block-type">{selectedBlock.type}</span>
        <span className="notes-panel-block-range">
          Bar {selectedBlock.startBar} - {selectedBlock.endBar}
        </span>
        {selectedBlock.label && (
          <span className="notes-panel-block-label">{selectedBlock.label}</span>
        )}
      </div>
      <textarea
        className="notes-panel-textarea"
        value={notesValue}
        onChange={handleChange}
        onBlur={handleBlur}
        placeholder="Add notes about this block..."
        rows={8}
      />
    </div>
  );
};

