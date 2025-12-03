/**
 * Block component for rendering a single annotation block on the timeline.
 * 
 * Renders an absolutely-positioned div representing the block's position
 * based on startBar and endBar values.
 */
import React from 'react';
import { AnnotationBlock } from '../../api/reference';
import './Block.css';

interface BlockProps {
  block: AnnotationBlock;
  barWidth: number;
  onClick?: (blockId: string) => void;
}

export const Block: React.FC<BlockProps> = ({
  block,
  barWidth,
  onClick,
}) => {
  const left = block.startBar * barWidth;
  const width = (block.endBar - block.startBar) * barWidth;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onClick) {
      onClick(block.id);
    }
  };

  return (
    <div
      className="composer-block"
      style={{
        left: `${left}px`,
        width: `${width}px`,
        backgroundColor: block.color || '#4a90e2',
      }}
      onClick={handleClick}
      title={block.label || `${block.type} (${block.startBar}-${block.endBar})`}
    >
      {block.label && (
        <span className="composer-block-label">{block.label}</span>
      )}
    </div>
  );
};

