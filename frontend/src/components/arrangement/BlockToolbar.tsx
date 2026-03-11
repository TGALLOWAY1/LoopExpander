/**
 * BlockToolbar - Contextual toolbar for editing a selected arrangement block.
 *
 * Appears above the selected block with actions: mute/unmute, delete,
 * and displays block info.
 */
import { useState } from 'react';
import { ArrangementBlock } from '../../api/arrangement';
import { ROLE_LABELS, StemRole } from '../../api/userLoop';
import './BlockToolbar.css';

interface BlockToolbarProps {
  block: ArrangementBlock;
  /** Position in pixels (left offset from timeline start). */
  positionLeft: number;
  /** Position in pixels from the top of the timeline area. */
  positionTop: number;
  onToggleMute: (block: ArrangementBlock) => void;
  onDelete: (block: ArrangementBlock) => void;
  onClose: () => void;
}

export default function BlockToolbar({
  block,
  positionLeft,
  positionTop,
  onToggleMute,
  onDelete,
  onClose,
}: BlockToolbarProps): JSX.Element {
  const [confirmDelete, setConfirmDelete] = useState(false);

  const roleLabel = ROLE_LABELS[block.role as StemRole] || block.role;
  const barRange = `${block.startBar.toFixed(1)}–${block.endBar.toFixed(1)}`;
  const length = (block.endBar - block.startBar).toFixed(1);

  return (
    <div
      className="block-toolbar"
      style={{
        left: Math.max(0, positionLeft - 40),
        top: positionTop - 44,
      }}
    >
      <div className="block-toolbar-info">
        <span className="block-toolbar-role">{roleLabel}</span>
        <span className="block-toolbar-range">
          bars {barRange} ({length} bars)
        </span>
      </div>
      <div className="block-toolbar-actions">
        <button
          className={`block-toolbar-btn ${block.active ? 'mute' : 'unmute'}`}
          onClick={() => onToggleMute(block)}
          title={block.active ? 'Mute this block' : 'Unmute this block'}
        >
          {block.active ? 'Mute' : 'Unmute'}
        </button>
        {!confirmDelete ? (
          <button
            className="block-toolbar-btn delete"
            onClick={() => setConfirmDelete(true)}
            title="Delete this block"
          >
            Delete
          </button>
        ) : (
          <button
            className="block-toolbar-btn delete-confirm"
            onClick={() => onDelete(block)}
            title="Confirm delete"
          >
            Confirm?
          </button>
        )}
        <button
          className="block-toolbar-btn close"
          onClick={onClose}
          title="Close toolbar"
        >
          ×
        </button>
      </div>
    </div>
  );
}
