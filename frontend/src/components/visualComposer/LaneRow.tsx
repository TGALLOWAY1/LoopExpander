/**
 * LaneRow component for displaying and editing a single annotation lane.
 * 
 * Provides UI for:
 * - Color swatch (with optional color picker)
 * - Editable lane name
 * - Collapse/expand toggle
 * - Move up/down buttons
 * - Delete button
 */
import React, { useState, useRef, useEffect } from 'react';
import { AnnotationLane } from '../../api/reference';
import './LaneRow.css';

interface LaneRowProps {
  lane: AnnotationLane;
  onChange: (id: string, patch: Partial<AnnotationLane>) => void;
  onDelete: (id: string) => void;
  onMoveUp?: (id: string) => void;
  onMoveDown?: (id: string) => void;
}

export const LaneRow: React.FC<LaneRowProps> = ({
  lane,
  onChange,
  onDelete,
  onMoveUp,
  onMoveDown,
}) => {
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameValue, setNameValue] = useState(lane.name);
  const [showColorPicker, setShowColorPicker] = useState(false);
  const nameInputRef = useRef<HTMLInputElement>(null);

  // Sync nameValue when lane.name changes externally
  useEffect(() => {
    setNameValue(lane.name);
  }, [lane.name]);

  // Focus input when editing starts
  useEffect(() => {
    if (isEditingName && nameInputRef.current) {
      nameInputRef.current.focus();
      nameInputRef.current.select();
    }
  }, [isEditingName]);

  const handleNameClick = () => {
    setIsEditingName(true);
  };

  const handleNameBlur = () => {
    setIsEditingName(false);
    const trimmed = nameValue.trim();
    if (trimmed && trimmed !== lane.name) {
      onChange(lane.id, { name: trimmed });
    } else {
      setNameValue(lane.name); // Reset if empty or unchanged
    }
  };

  const handleNameKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.currentTarget.blur();
    } else if (e.key === 'Escape') {
      setNameValue(lane.name);
      setIsEditingName(false);
    }
  };

  const handleColorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(lane.id, { color: e.target.value });
    setShowColorPicker(false);
  };

  const handleToggleCollapse = () => {
    onChange(lane.id, { collapsed: !lane.collapsed });
  };

  const handleDelete = () => {
    if (window.confirm(`Delete lane "${lane.name}"? This will also delete all blocks in this lane.`)) {
      onDelete(lane.id);
    }
  };

  return (
    <div className="lane-row">
      <div className="lane-row-main">
        {/* Color swatch */}
        <div className="lane-row-color-container">
          <div
            className="lane-row-color-swatch"
            style={{ backgroundColor: lane.color }}
            onClick={() => setShowColorPicker(!showColorPicker)}
            title="Click to change color"
          />
          {showColorPicker && (
            <div className="lane-row-color-picker-wrapper">
              <input
                type="color"
                value={lane.color}
                onChange={handleColorChange}
                onBlur={() => setShowColorPicker(false)}
                className="lane-row-color-picker"
                autoFocus
              />
            </div>
          )}
        </div>

        {/* Lane name (editable) */}
        <div className="lane-row-name-container">
          {isEditingName ? (
            <input
              ref={nameInputRef}
              type="text"
              value={nameValue}
              onChange={(e) => setNameValue(e.target.value)}
              onBlur={handleNameBlur}
              onKeyDown={handleNameKeyDown}
              className="lane-row-name-input"
            />
          ) : (
            <span
              className="lane-row-name"
              onClick={handleNameClick}
              title="Click to edit name"
            >
              {lane.name}
            </span>
          )}
        </div>

        {/* Collapse/expand toggle */}
        <button
          className="lane-row-collapse-button"
          onClick={handleToggleCollapse}
          title={lane.collapsed ? 'Expand lane' : 'Collapse lane'}
        >
          {lane.collapsed ? '▼' : '▲'}
        </button>

        {/* Move buttons */}
        <div className="lane-row-move-buttons">
          {onMoveUp && (
            <button
              className="lane-row-move-button"
              onClick={() => onMoveUp(lane.id)}
              title="Move up"
            >
              ↑
            </button>
          )}
          {onMoveDown && (
            <button
              className="lane-row-move-button"
              onClick={() => onMoveDown(lane.id)}
              title="Move down"
            >
              ↓
            </button>
          )}
        </div>

        {/* Delete button */}
        <button
          className="lane-row-delete-button"
          onClick={handleDelete}
          title="Delete lane"
        >
          ×
        </button>
      </div>
    </div>
  );
};

