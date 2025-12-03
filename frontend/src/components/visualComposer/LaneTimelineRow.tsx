/**
 * LaneTimelineRow component for rendering a single lane's bar grid and blocks.
 * 
 * Displays a grid of bar cells and renders Block components for blocks in this lane.
 * Supports clicking empty cells to create new blocks.
 */
import React from 'react';
import { AnnotationLane, AnnotationBlock } from '../../api/reference';
import { Block } from './Block';
import './LaneTimelineRow.css';

interface LaneTimelineRowProps {
  lane: AnnotationLane;
  blocks: AnnotationBlock[];
  barCount: number;
  onCreateBlock: (laneId: string, startBar: number) => void;
  onSelectBlock: (blockId: string) => void;
  onUpdateBlock: (blockId: string, patch: Partial<AnnotationBlock>) => void;
}

export const LaneTimelineRow: React.FC<LaneTimelineRowProps> = ({
  lane,
  blocks,
  barCount,
  onCreateBlock,
  onSelectBlock,
  onUpdateBlock,
}) => {
  const BAR_WIDTH = 40; // pixels per bar

  // If lane is collapsed, render minimal stub
  if (lane.collapsed) {
    return (
      <div className="lane-timeline-row collapsed">
        <div className="lane-timeline-row-label">{lane.name}</div>
        <div className="lane-timeline-row-stub">Collapsed</div>
      </div>
    );
  }

  const handleBarClick = (barIndex: number) => {
    onCreateBlock(lane.id, barIndex);
  };

  return (
    <div className="lane-timeline-row">
      <div className="lane-timeline-row-label">{lane.name}</div>
      <div className="lane-timeline-row-grid-container">
        <div
          className="lane-timeline-row-grid"
          style={{
            gridTemplateColumns: `repeat(${barCount}, ${BAR_WIDTH}px)`,
            width: `${barCount * BAR_WIDTH}px`,
          }}
        >
          {Array.from({ length: barCount }, (_, i) => {
            const barIndex = i;
            const hasBlock = blocks.some(
              block => barIndex >= block.startBar && barIndex < block.endBar
            );

            return (
              <div
                key={barIndex}
                className={`lane-timeline-bar-cell ${hasBlock ? 'has-block' : ''}`}
                onClick={() => handleBarClick(barIndex)}
                title={`Bar ${barIndex} - Click to create block`}
              >
                {barIndex % 4 === 0 && (
                  <span className="lane-timeline-bar-label">{barIndex}</span>
                )}
              </div>
            );
          })}
        </div>
        <div className="lane-timeline-row-blocks">
          {blocks.map(block => (
            <Block
              key={block.id}
              block={block}
              barWidth={BAR_WIDTH}
              barCount={barCount}
              laneColor={lane.color}
              onClick={onSelectBlock}
              onUpdateBlock={onUpdateBlock}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

