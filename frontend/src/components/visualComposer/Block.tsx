/**
 * Block component for rendering a single annotation block on the timeline.
 * 
 * Supports:
 * - Drag to move horizontally
 * - Resize via left/right handles
 * - Type and label editing via context menu
 */
import React, { useState, useRef, useEffect } from 'react';
import { AnnotationBlock } from '../../api/reference';
import './Block.css';

interface BlockProps {
  block: AnnotationBlock;
  barWidth: number;
  barCount: number;
  laneColor?: string;
  onClick?: (blockId: string) => void;
  onUpdateBlock: (blockId: string, patch: Partial<AnnotationBlock>) => void;
}

type DragMode = 'move' | 'resize-left' | 'resize-right' | null;

export const Block: React.FC<BlockProps> = ({
  block,
  barWidth,
  barCount,
  laneColor,
  onClick,
  onUpdateBlock,
}) => {
  const [dragMode, setDragMode] = useState<DragMode>(null);
  const [dragStartX, setDragStartX] = useState(0);
  const [dragStartBar, setDragStartBar] = useState({ start: 0, end: 0 });
  const [showMenu, setShowMenu] = useState(false);
  const [editingLabel, setEditingLabel] = useState(false);
  const [labelValue, setLabelValue] = useState(block.label || '');
  const blockRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Compute block color (use variation shade for variation type)
  const blockColor = React.useMemo(() => {
    if (block.color) return block.color;
    if (block.type === 'variation' && laneColor) {
      // Create a lighter/darker shade
      return adjustColorBrightness(laneColor, -20);
    }
    return laneColor || '#4a90e2';
  }, [block.color, block.type, laneColor]);

  // Sync label value when block changes
  useEffect(() => {
    setLabelValue(block.label || '');
  }, [block.label]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
        setEditingLabel(false);
      }
    };
    if (showMenu || editingLabel) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showMenu, editingLabel]);

  const left = block.startBar * barWidth;
  const width = (block.endBar - block.startBar) * barWidth;

  // Snap pixel position to bar
  const snapToBar = (pixels: number): number => {
    return Math.round(pixels / barWidth);
  };

  // Clamp bar value to valid range
  const clampBar = (bar: number): number => {
    return Math.max(0, Math.min(bar, barCount));
  };

  const handleMouseDown = (e: React.MouseEvent, mode: DragMode) => {
    e.stopPropagation();
    e.preventDefault();
    setDragMode(mode);
    setDragStartX(e.clientX);
    setDragStartBar({ start: block.startBar, end: block.endBar });
    if (onClick) {
      onClick(block.id);
    }
  };

  useEffect(() => {
    if (!dragMode) return;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = e.clientX - dragStartX;
      const deltaBars = snapToBar(deltaX);

      if (dragMode === 'move') {
        const newStart = clampBar(dragStartBar.start + deltaBars);
        const newEnd = clampBar(dragStartBar.end + deltaBars);
        if (newEnd > newStart) {
          onUpdateBlock(block.id, { startBar: newStart, endBar: newEnd });
        }
      } else if (dragMode === 'resize-left') {
        const newStart = clampBar(dragStartBar.start + deltaBars);
        if (newStart < dragStartBar.end) {
          onUpdateBlock(block.id, { startBar: newStart });
        }
      } else if (dragMode === 'resize-right') {
        const newEnd = clampBar(dragStartBar.end + deltaBars);
        if (newEnd > dragStartBar.start) {
          onUpdateBlock(block.id, { endBar: newEnd });
        }
      }
    };

    const handleMouseUp = () => {
      setDragMode(null);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [dragMode, dragStartX, dragStartBar, block.id, onUpdateBlock]);

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowMenu(true);
    if (onClick) {
      onClick(block.id);
    }
  };

  const handleTypeChange = (type: AnnotationBlock['type']) => {
    let update: Partial<AnnotationBlock> = { type };
    
    // For variation type, adjust color if not already set
    if (type === 'variation' && !block.color && laneColor) {
      update.color = adjustColorBrightness(laneColor, -20);
    }
    
    // Clear label if not custom
    if (type !== 'custom') {
      update.label = null;
    }
    
    onUpdateBlock(block.id, update);
    setShowMenu(false);
  };

  const handleLabelSave = () => {
    onUpdateBlock(block.id, { label: labelValue.trim() || null });
    setEditingLabel(false);
    setShowMenu(false);
  };

  const handleLabelKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleLabelSave();
    } else if (e.key === 'Escape') {
      setLabelValue(block.label || '');
      setEditingLabel(false);
      setShowMenu(false);
    }
  };

  return (
    <div
      ref={blockRef}
      className="composer-block"
      style={{
        left: `${left}px`,
        width: `${width}px`,
        backgroundColor: blockColor,
      }}
      onMouseDown={(e) => handleMouseDown(e, 'move')}
      onContextMenu={handleContextMenu}
      title={block.label || `${block.type} (${block.startBar}-${block.endBar})`}
    >
      {/* Resize handles */}
      <div
        className="composer-block-resize-handle composer-block-resize-left"
        onMouseDown={(e) => handleMouseDown(e, 'resize-left')}
      />
      <div
        className="composer-block-resize-handle composer-block-resize-right"
        onMouseDown={(e) => handleMouseDown(e, 'resize-right')}
      />

      {/* Block content */}
      <div className="composer-block-content">
        {block.label && (
          <span className="composer-block-label">{block.label}</span>
        )}
        {!block.label && (
          <span className="composer-block-type">{block.type}</span>
        )}
      </div>

      {/* Context menu */}
      {showMenu && (
        <div ref={menuRef} className="composer-block-menu">
          <div className="composer-block-menu-section">
            <div className="composer-block-menu-label">Type:</div>
            <div className="composer-block-menu-types">
              {(['call', 'response', 'variation', 'fill', 'custom'] as const).map(type => (
                <button
                  key={type}
                  className={`composer-block-menu-type ${block.type === type ? 'active' : ''}`}
                  onClick={() => handleTypeChange(type)}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>
          {block.type === 'custom' && (
            <div className="composer-block-menu-section">
              <div className="composer-block-menu-label">Label:</div>
              {editingLabel ? (
                <input
                  type="text"
                  value={labelValue}
                  onChange={(e) => setLabelValue(e.target.value)}
                  onBlur={handleLabelSave}
                  onKeyDown={handleLabelKeyDown}
                  className="composer-block-menu-label-input"
                  autoFocus
                />
              ) : (
                <button
                  className="composer-block-menu-edit-label"
                  onClick={() => setEditingLabel(true)}
                >
                  {block.label || 'Add label...'}
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Helper to adjust color brightness
function adjustColorBrightness(color: string, percent: number): string {
  const num = parseInt(color.replace('#', ''), 16);
  const r = Math.max(0, Math.min(255, (num >> 16) + percent));
  const g = Math.max(0, Math.min(255, ((num >> 8) & 0x00FF) + percent));
  const b = Math.max(0, Math.min(255, (num & 0x0000FF) + percent));
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}

