/**
 * MotifGroupsPanel component for displaying motif groups as collapsible cards.
 */
import { useState, useMemo } from 'react';
import { MotifGroup, MotifInstance, Region } from '../api/reference';
import './MotifGroupsPanel.css';

export type MotifGroupsPanelProps = {
  groups: MotifGroup[];
  instances: MotifInstance[];
  regions: Region[];
  onGroupClick?: (groupId: string) => void;
  highlightedGroupId?: string | null;
  loading?: boolean;
};

/**
 * Find region name for a motif instance.
 */
function findRegionName(instance: MotifInstance, regions: Region[]): string | null {
  if (instance.regionIds.length === 0) return null;
  const region = regions.find(r => r.id === instance.regionIds[0]);
  return region ? region.name : null;
}

export function MotifGroupsPanel({
  groups,
  instances,
  regions,
  onGroupClick,
  highlightedGroupId,
  loading = false
}: MotifGroupsPanelProps): JSX.Element {
  const [expandedGroupId, setExpandedGroupId] = useState<string | null>(null);

  // Create a map of instance ID to instance for quick lookup
  const instanceMap = useMemo(() => {
    const map = new Map<string, MotifInstance>();
    instances.forEach(inst => {
      map.set(inst.id, inst);
    });
    return map;
  }, [instances]);

  // Create groups with their instances
  const groupsWithInstances = useMemo(() => {
    return groups.map(group => ({
      ...group,
      instances: group.memberIds
        .map(id => instanceMap.get(id))
        .filter((inst): inst is MotifInstance => inst !== undefined)
    }));
  }, [groups, instanceMap]);

  if (!loading && groups.length === 0) {
    return (
      <div className="motif-groups-panel">
        <h3>Motif Groups</h3>
        <div className="motif-groups-empty">
          <p>No motif groups were detected for this reference.</p>
          <p className="motif-groups-empty-hint">
            Try lowering motif sensitivity for the relevant stem lanes and re-running analysis.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="motif-groups-panel">
      <h3>Motif Groups</h3>
      <div className="motif-groups-content">
        {groupsWithInstances.map((group) => {
          const isExpanded = expandedGroupId === group.id;
          const isHighlighted = highlightedGroupId === group.id;
          
          return (
            <div
              key={group.id}
              className={`motif-group-card ${isHighlighted ? 'highlighted' : ''}`}
            >
              <div
                className="motif-group-header"
                onClick={() => {
                  setExpandedGroupId(isExpanded ? null : group.id);
                  onGroupClick?.(group.id);
                }}
              >
                <div className="motif-group-header-content">
                  <span className="motif-group-id">{group.label || group.id}</span>
                  <span className="motif-group-count">
                    {group.memberCount} instance{group.memberCount !== 1 ? 's' : ''}
                    {group.variationCount > 0 && ` (${group.variationCount} variation${group.variationCount !== 1 ? 's' : ''})`}
                  </span>
                </div>
                <span className="motif-group-toggle">
                  {isExpanded ? '▼' : '▶'}
                </span>
              </div>
              
              {isExpanded && (
                <div className="motif-group-instances">
                  <ul>
                    {group.instances.map((instance) => {
                      const regionName = findRegionName(instance, regions);
                      
                      return (
                        <li key={instance.id} className="motif-instance-item">
                          <div className="motif-instance-stem">
                            {instance.stemRole}
                            {instance.isVariation && (
                              <span className="motif-variation-badge">variation</span>
                            )}
                          </div>
                          <div className="motif-instance-time">
                            {instance.startTime.toFixed(1)}s - {instance.endTime.toFixed(1)}s
                          </div>
                          {regionName && (
                            <div className="motif-instance-region">
                              {regionName}
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

