/**
 * ComposerTimeline component for rendering the complete timeline view.
 * 
 * Displays all lanes with their bar grids and blocks, allowing block creation
 * and selection.
 */
import React, { useMemo } from 'react';
import { RegionAnnotations, AnnotationBlock } from '../../api/reference';
import { LaneTimelineRow } from './LaneTimelineRow';
import './ComposerTimeline.css';

interface ComposerTimelineProps {
  regionAnnotations: RegionAnnotations;
  barCount: number;
  onCreateBlock: (laneId: string, startBar: number) => void;
  onSelectBlock: (blockId: string) => void;
  onUpdateBlock: (blockId: string, patch: Partial<AnnotationBlock>) => void;
}

export const ComposerTimeline: React.FC<ComposerTimelineProps> = ({
  regionAnnotations,
  barCount,
  onCreateBlock,
  onSelectBlock,
  onUpdateBlock,
}) => {
  // DEV: Debug logging
  if (import.meta.env.MODE !== 'production') {
    console.log('[ComposerTimeline] render', {
      barCount,
      regionId: regionAnnotations.regionId,
      lanesLength: regionAnnotations.lanes?.length || 0,
    });
  }

  // Sort lanes by order
  const sortedLanes = useMemo(() => {
    return [...(regionAnnotations.lanes || [])].sort(
      (a, b) => (a.order ?? 0) - (b.order ?? 0)
    );
  }, [regionAnnotations.lanes]);

  // Group blocks by laneId
  const blocksByLaneId = useMemo(() => {
    const map = new Map<string, AnnotationBlock[]>();
    (regionAnnotations.blocks || []).forEach(block => {
      const existing = map.get(block.laneId) || [];
      map.set(block.laneId, [...existing, block]);
    });
    return map;
  }, [regionAnnotations.blocks]);

  // Always render the timeline structure, even with 0 lanes
  // This ensures the bar grid is visible for block creation
  if (sortedLanes.length === 0) {
    return (
      <div className="composer-timeline empty">
        <div className="composer-timeline-header">
          <div className="composer-timeline-header-label">Lane</div>
          <div className="composer-timeline-header-grid">
            <div className="composer-timeline-bar-numbers">
              {barCount > 0 && Array.from({ length: barCount }, (_, i) => {
                if (i % 4 === 0) {
                  return (
                    <div key={i} className="composer-timeline-bar-number">
                      {i}
                    </div>
                  );
                }
                return null;
              })}
            </div>
          </div>
        </div>
        <div className="composer-timeline-lanes">
          <div className="composer-timeline-empty-message">
            <p>No lanes available. Add lanes to start creating blocks.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="composer-timeline">
      <div className="composer-timeline-header">
        <div className="composer-timeline-header-label">Lane</div>
        <div className="composer-timeline-header-grid">
          <div className="composer-timeline-bar-numbers">
            {Array.from({ length: barCount }, (_, i) => {
              if (i % 4 === 0) {
                return (
                  <div key={i} className="composer-timeline-bar-number">
                    {i}
                  </div>
                );
              }
              return null;
            })}
          </div>
        </div>
      </div>
      <div className="composer-timeline-lanes">
        {sortedLanes.map(lane => {
          const laneBlocks = blocksByLaneId.get(lane.id) || [];
          return (
            <LaneTimelineRow
              key={lane.id}
              lane={lane}
              blocks={laneBlocks}
              barCount={barCount}
              onCreateBlock={onCreateBlock}
              onSelectBlock={onSelectBlock}
              onUpdateBlock={onUpdateBlock}
            />
          );
        })}
      </div>
    </div>
  );
};

