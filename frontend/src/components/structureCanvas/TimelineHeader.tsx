/**
 * TimelineHeader renders the bar number ruler at the top of the timeline.
 */
import React from 'react';

interface TimelineHeaderProps {
  totalBars: number;
  barWidth: number;
}

export const TimelineHeader: React.FC<TimelineHeaderProps> = ({
  totalBars,
  barWidth,
}) => {
  const markers: number[] = [];
  for (let i = 0; i < totalBars; i++) {
    if (i % 4 === 0) {
      markers.push(i);
    }
  }

  return (
    <div
      className="sc-timeline-header"
      style={{ width: `${totalBars * barWidth}px` }}
    >
      {markers.map((bar) => (
        <div
          key={bar}
          className="sc-bar-marker"
          style={{ left: `${bar * barWidth}px` }}
        >
          <div className="sc-bar-tick" />
          <span className="sc-bar-number">{bar}</span>
        </div>
      ))}
    </div>
  );
};
