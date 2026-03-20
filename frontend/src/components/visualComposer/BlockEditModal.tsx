import React, { useState, useEffect } from 'react';
import type { AnnotationBlock } from '../../api/reference';
import './BlockEditModal.css';

interface BlockEditModalProps {
    block: AnnotationBlock;
    laneColor: string;
    isOpen: boolean;
    onClose: () => void;
    onSave: (blockId: string, updates: Partial<AnnotationBlock>) => void;
    onDelete: (blockId: string) => void;
}

const BLOCK_TYPES = [
    { value: 'motif', label: 'Motif' },
    { value: 'variation', label: 'Variation' },
    { value: 'call', label: 'Call' },
    { value: 'response', label: 'Response' },
    { value: 'fill', label: 'Fill' },
    { value: 'other', label: 'Other/Custom' },
];

export function BlockEditModal({
    block,
    laneColor,
    isOpen,
    onClose,
    onSave,
    onDelete,
}: BlockEditModalProps): JSX.Element {
    const [startBar, setStartBar] = useState(block.startBar);
    const [endBar, setEndBar] = useState(block.endBar);
    const [type, setType] = useState(block.type || 'motif');
    const [notes, setNotes] = useState(block.notes || '');

    // Reset state when block changes
    useEffect(() => {
        if (isOpen) {
            setStartBar(block.startBar);
            setEndBar(block.endBar);
            setType(block.type || 'motif');
            setNotes(block.notes || '');
        }
    }, [block, isOpen]);

    if (!isOpen) return <></>;

    const handleSave = (e: React.FormEvent) => {
        e.preventDefault();
        onSave(block.id, {
            startBar: Number(startBar),
            endBar: Number(endBar),
            type,
            notes: notes.trim() || undefined,
        });
        onClose();
    };

    const handleDelete = () => {
        if (window.confirm('Are you sure you want to delete this block?')) {
            onDelete(block.id);
            onClose();
        }
    };

    return (
        <div className="block-edit-modal-overlay" onClick={onClose}>
            <div
                className="block-edit-modal"
                onClick={(e) => e.stopPropagation()}
                style={{ borderTopColor: laneColor }}
            >
                <div className="modal-header">
                    <h3>Edit Block</h3>
                    <button className="close-button" onClick={onClose}>&times;</button>
                </div>

                <form onSubmit={handleSave}>
                    <div className="form-row">
                        <div className="form-group">
                            <label>Start Bar</label>
                            <input
                                type="number"
                                step="0.125"
                                value={startBar}
                                onChange={(e) => setStartBar(Math.max(1, Number(e.target.value)))}
                            />
                        </div>
                        <div className="form-group">
                            <label>End Bar</label>
                            <input
                                type="number"
                                step="0.125"
                                value={endBar}
                                onChange={(e) => setEndBar(Math.max(startBar + 0.125, Number(e.target.value)))}
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Type</label>
                        <select value={type} onChange={(e) => setType(e.target.value as any)}>
                            {BLOCK_TYPES.map((t) => (
                                <option key={t.value} value={t.value}>{t.label}</option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group">
                        <label>Notes</label>
                        <textarea
                            rows={3}
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder="Describe sound characteristics..."
                        />
                    </div>

                    <div className="modal-actions">
                        <button type="button" className="delete-button" onClick={handleDelete}>
                            Delete Block
                        </button>
                        <div className="right-actions">
                            <button type="button" className="cancel-button" onClick={onClose}>
                                Cancel
                            </button>
                            <button type="submit" className="save-button" style={{ backgroundColor: laneColor }}>
                                Save Changes
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    );
}
