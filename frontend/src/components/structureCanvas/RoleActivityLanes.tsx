/**
 * RoleActivityLanes renders one horizontal lane per detected role
 * (drums, bass, melodic, vocal) with active/inactive segments.
 *
 * Users can click segments to toggle activity on/off.
 */
import React from 'react';
import { ActivitySegment, RoleActivityTimeline } from '../../api/referenceMix';
import { InteractionLabeler } from './InteractionLabeler';
import { InteractionLabel, InteractionLabelCreate, InteractionLabelType } from '../../api/interactions';

interface RoleActivityLanesProps {
  timelines: RoleActivityTimeline[];
  totalBars: number;
  barWidth: number;
  onUpdateSegment: (role: string, index: number, patch: Partial<ActivitySegment>) => void;
  interactionLabels: InteractionLabel[];
  activeLabelType: InteractionLabelType;
  onCreateLabel: (label: InteractionLabelCreate) => void;
  onUpdateLabel: (id: string, updates: Partial<InteractionLabel>) => void;
  onDeleteLabel: (id: string) => void;
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
  onUpdateSegment,
  interactionLabels,
  activeLabelType,
  onCreateLabel,
  onUpdateLabel,
  onDeleteLabel,
}) => {
  const width = totalBars * barWidth;

  return (
    <div className="sc-role-lanes-container">
      {timelines.map((timeline) => (
        <div key={timeline.role} className="sc-role-group" style={{ display: 'flex', flexDirection: 'column', borderBottom: '1px solid #ddd' }}>
          <div className="sc-role-lane" style={{ position: 'relative', borderBottom: 'none' }}>
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
                      onUpdateSegment(
                        timeline.role,
                        i,
                        { active: !seg.active },
                      )
                    }
                    title={`${timeline.role}: ${seg.active ? 'active' : 'inactive'} (bars ${seg.startBar}-${seg.endBar}, confidence: ${(seg.confidence * 100).toFixed(0)}%)`}
                  />
                ))}
              </div>
            </div>
          </div>
          
          {/* Interaction Label Canvas for this lane */}
          <div className="sc-role-lane" style={{ position: 'relative', borderBottom: 'none', minHeight: '28px', background: '#fcfcfc' }}>
            <div className="sc-role-lane-label" style={{ fontSize: '0.65rem', color: '#aaa', paddingLeft: '24px', background: 'transparent', borderRight: '1px solid #eee' }}>
              Labels
            </div>
            <div className="sc-role-segments-container" style={{ background: 'transparent' }}>
              <InteractionLabeler
                labels={interactionLabels.filter(label => label.role === timeline.role)}
                totalBars={totalBars}
                barWidth={barWidth}
                activeLabelType={activeLabelType}
                role={timeline.role}
                onCreateLabel={onCreateLabel}
                onUpdateLabel={onUpdateLabel}
                onDeleteLabel={onDeleteLabel}
              />
            </div>
          </div>
          
        </div>
      ))}
    </div>
  );
};
