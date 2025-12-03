/**
 * LaneList component for managing a list of annotation lanes.
 * 
 * Provides:
 * - List of LaneRow components sorted by order
 * - Move up/down functionality
 * - Add lane button
 */
import React, { useMemo } from 'react';
import { AnnotationLane } from '../../api/reference';
import { LaneRow } from './LaneRow';
import './LaneList.css';

interface LaneListProps {
  lanes: AnnotationLane[];
  onChangeLane: (id: string, patch: Partial<AnnotationLane>) => void;
  onDeleteLane: (id: string) => void;
  onReorderLanes: (orderedIds: string[]) => void;
  onAddLane: () => void;
}

export const LaneList: React.FC<LaneListProps> = ({
  lanes,
  onChangeLane,
  onDeleteLane,
  onReorderLanes,
  onAddLane,
}) => {
  // Sort lanes by order property
  const sortedLanes = useMemo(() => {
    return [...lanes].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  }, [lanes]);

  const handleMoveUp = (id: string) => {
    const currentIndex = sortedLanes.findIndex(lane => lane.id === id);
    if (currentIndex <= 0) return; // Already at top

    const newOrder = [...sortedLanes];
    [newOrder[currentIndex - 1], newOrder[currentIndex]] = [
      newOrder[currentIndex],
      newOrder[currentIndex - 1],
    ];

    const orderedIds = newOrder.map(lane => lane.id);
    onReorderLanes(orderedIds);
  };

  const handleMoveDown = (id: string) => {
    const currentIndex = sortedLanes.findIndex(lane => lane.id === id);
    if (currentIndex < 0 || currentIndex >= sortedLanes.length - 1) return; // Already at bottom

    const newOrder = [...sortedLanes];
    [newOrder[currentIndex], newOrder[currentIndex + 1]] = [
      newOrder[currentIndex + 1],
      newOrder[currentIndex],
    ];

    const orderedIds = newOrder.map(lane => lane.id);
    onReorderLanes(orderedIds);
  };

  return (
    <div className="lane-list">
      <div className="lane-list-header">
        <h3>Annotation Lanes</h3>
      </div>
      <div className="lane-list-items">
        {sortedLanes.length === 0 ? (
          <div className="lane-list-empty">
            <p>No lanes yet. Click "Add Lane" to create one.</p>
          </div>
        ) : (
          sortedLanes.map((lane) => (
            <LaneRow
              key={lane.id}
              lane={lane}
              onChange={onChangeLane}
              onDelete={onDeleteLane}
              onMoveUp={handleMoveUp}
              onMoveDown={handleMoveDown}
            />
          ))
        )}
      </div>
      <div className="lane-list-footer">
        <button className="lane-list-add-button" onClick={onAddLane}>
          + Add Lane
        </button>
      </div>
    </div>
  );
};

