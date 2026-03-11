/**
 * SectionBlock renders a single section as a colored block on the timeline.
 * Supports click-to-select and displays the section label.
 */
import React from 'react';
import { CanvasSection } from '../../api/structureCanvas';

interface SectionBlockProps {
  section: CanvasSection;
  barWidth: number;
  selected: boolean;
  onClick: (sectionId: string) => void;
}

export const SectionBlock: React.FC<SectionBlockProps> = ({
  section,
  barWidth,
  selected,
  onClick,
}) => {
  const left = section.startBar * barWidth;
  const width = (section.endBar - section.startBar) * barWidth;

  return (
    <div
      className={`sc-section-block ${selected ? 'selected' : ''}`}
      style={{
        left: `${left}px`,
        width: `${width}px`,
        backgroundColor: section.color,
        borderColor: selected ? '#fff' : 'transparent',
      }}
      onClick={(e) => {
        e.stopPropagation();
        onClick(section.id);
      }}
      title={`${section.label || section.name} (${Math.round(section.startBar)}-${Math.round(section.endBar)} bars)`}
    >
      <span className="sc-section-label">
        {section.label || section.name}
      </span>
      <span className="sc-section-bars">
        {Math.round(section.endBar - section.startBar)} bars
      </span>
    </div>
  );
};
