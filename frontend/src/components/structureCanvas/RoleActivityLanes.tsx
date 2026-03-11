/**
 * RoleActivityLanes renders one horizontal lane per detected role
 * (drums, bass, melodic, vocal) with active/inactive segments.
 *
 * Users can click segments to toggle activity on/off.
 */
import React from 'react';
import { RoleActivityTimeline, ActivitySegment } from '../../api/referenceMix';

interface RoleActivityLanesProps {
  timelines: RoleActivityTimeline[];
  totalBars: number;
  barWidth: number;
  onToggleSegment: (
    role: string,
    startBar: number,
    endBar: number,
    active: boolean,
  ) => void;
}

const ROLE_COLORS: Record<string, string> = {
  drums: '#E91E63',
  bass: '#673AB7',
  melodic: '#00BCD4',
  vocal: '#FF9800',
};

export const RoleActivityLanes: React.FC<RoleActivityLanesProps> = ({
  timelines,
  totalBars,
  barWidth,
  onToggleSegment,
}) => {
  const width = totalBars * barWidth;

  return (
    <div className="sc-role-lanes-container">
      {timelines.map((timeline) => (
        <div key={timeline.role} className="sc-role-lane">
          <div className="sc-role-lane-label">
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: ROLE_COLORS[timeline.role] || '#999',
                display: 'inline-block',
                marginRight: 6,
              }}
            />
            {timeline.role}
          </div>
          <div className="sc-role-segments-container">
            <div
              className="sc-role-segments-row"
              style={{ width: `${width}px` }}
            >
              {timeline.segments.map((seg, i) => (
                <div
                  key={i}
                  className={`sc-role-segment ${seg.active ? 'active' : 'inactive'}`}
                  data-role={timeline.role}
                  style={{
                    left: `${seg.startBar * barWidth}px`,
                    width: `${(seg.endBar - seg.startBar) * barWidth}px`,
                    backgroundColor: seg.active
                      ? ROLE_COLORS[timeline.role] || '#999'
                      : undefined,
                  }}
                  onClick={() =>
                    onToggleSegment(
                      timeline.role,
                      seg.startBar,
                      seg.endBar,
                      !seg.active,
                    )
                  }
                  title={`${timeline.role}: ${seg.active ? 'active' : 'inactive'} (bars ${seg.startBar}-${seg.endBar}, confidence: ${(seg.confidence * 100).toFixed(0)}%)`}
                />
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
