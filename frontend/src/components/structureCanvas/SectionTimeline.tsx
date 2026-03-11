/**
 * SectionTimeline renders the full-song sections as color-coded blocks
 * on a horizontal timeline with bar grid.
 */
import React from 'react';
import { CanvasSection } from '../../api/structureCanvas';
import { SectionBlock } from './SectionBlock';
import { TimelineHeader } from './TimelineHeader';

interface SectionTimelineProps {
  sections: CanvasSection[];
  totalBars: number;
  barWidth: number;
  selectedSectionId: string | null;
  onSelectSection: (sectionId: string | null) => void;
}

export const SectionTimeline: React.FC<SectionTimelineProps> = ({
  sections,
  totalBars,
  barWidth,
  selectedSectionId,
  onSelectSection,
}) => {
  const timelineWidth = totalBars * barWidth;

  return (
    <div className="sc-section-timeline">
      <div className="sc-lane-label">Sections</div>
      <div className="sc-timeline-scroll">
        <TimelineHeader totalBars={totalBars} barWidth={barWidth} />
        <div
          className="sc-sections-row"
          style={{ width: `${timelineWidth}px` }}
          onClick={() => onSelectSection(null)}
        >
          {/* Background grid lines */}
          {Array.from({ length: totalBars }, (_, i) => (
            <div
              key={i}
              className={`sc-grid-line ${i % 4 === 0 ? 'major' : 'minor'}`}
              style={{ left: `${i * barWidth}px` }}
            />
          ))}
          {/* Section blocks */}
          {sections.map((section) => (
            <SectionBlock
              key={section.id}
              section={section}
              barWidth={barWidth}
              selected={selectedSectionId === section.id}
              onClick={onSelectSection}
            />
          ))}
        </div>
      </div>
    </div>
  );
};
