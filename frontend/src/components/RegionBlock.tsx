/**
 * RegionBlock component for displaying a single region in the timeline.
 */
import { Region, MotifInstance, MotifGroup } from '../api/reference';
import './RegionBlock.css';

export type RegionBlockProps = {
  region: Region;
  totalDuration: number;
  motifs?: MotifInstance[];
  motifGroups?: MotifGroup[];
  highlightedGroupId?: string | null;
  onMotifHover?: (groupId: string | null) => void;
};

/**
 * Get background color based on region type.
 */
function getRegionColor(type: string): string {
  switch (type) {
    case 'low_energy':
      return '#e3f2fd'; // Light blue
    case 'build':
      return '#fff3e0'; // Light orange
    case 'high_energy':
      return '#f3e5f5'; // Light purple
    case 'drop':
      return '#ffebee'; // Light red
    default:
      return '#f5f5f5'; // Light gray
  }
}

/**
 * Get border color based on region type.
 */
function getRegionBorderColor(type: string): string {
  switch (type) {
    case 'low_energy':
      return '#2196f3'; // Blue
    case 'build':
      return '#ff9800'; // Orange
    case 'high_energy':
      return '#9c27b0'; // Purple
    case 'drop':
      return '#f44336'; // Red
    default:
      return '#9e9e9e'; // Gray
  }
}

/**
 * Get color for a motif group (consistent color per group).
 */
function getMotifGroupColor(groupId: string | null): string {
  if (!groupId) return '#999';
  const colors = [
    '#4caf50', // Green
    '#2196f3', // Blue
    '#ff9800', // Orange
    '#9c27b0', // Purple
    '#f44336', // Red
    '#00bcd4', // Cyan
    '#ffc107', // Amber
    '#e91e63', // Pink
  ];
  // Use hash of groupId to get consistent color
  const hash = groupId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

export function RegionBlock({ 
  region, 
  totalDuration, 
  motifs = [],
  motifGroups = [],
  highlightedGroupId = null,
  onMotifHover
}: RegionBlockProps): JSX.Element {
  const widthPercent = (region.duration / totalDuration) * 100;
  const backgroundColor = getRegionColor(region.type);
  const borderColor = getRegionBorderColor(region.type);

  // Filter motifs that fall within this region
  const regionMotifs = motifs.filter(
    (motif) => 
      motif.startTime >= region.start && 
      motif.startTime < region.end &&
      motif.regionIds.includes(region.id)
  );

  // Create a map of groupId to color
  const groupColorMap = new Map<string, string>();
  motifGroups.forEach((group) => {
    groupColorMap.set(group.id, getMotifGroupColor(group.id));
  });

  return (
    <div
      className="region-block"
      style={{
        width: `${widthPercent}%`,
        backgroundColor,
        borderColor,
        position: 'relative',
      }}
      title={`${region.name} (${region.type}): ${region.start.toFixed(1)}s - ${region.end.toFixed(1)}s`}
    >
      <div className="region-block-content">
        <div className="region-name">{region.name}</div>
        <div className="region-time">
          {region.start.toFixed(1)}s - {region.end.toFixed(1)}s
        </div>
      </div>
      
      {/* Motif markers */}
      {regionMotifs.length > 0 && (
        <div className="motif-markers">
          {regionMotifs.map((motif) => {
            const positionPercent = ((motif.startTime - region.start) / region.duration) * 100;
            const groupColor = motif.groupId ? groupColorMap.get(motif.groupId) || '#999' : '#999';
            const isHighlighted = highlightedGroupId === motif.groupId;
            
            return (
              <div
                key={motif.id}
                className={`motif-marker ${isHighlighted ? 'highlighted' : ''} ${motif.isVariation ? 'variation' : ''}`}
                style={{
                  left: `${positionPercent}%`,
                  backgroundColor: groupColor,
                  borderColor: groupColor,
                }}
                onMouseEnter={() => onMotifHover?.(motif.groupId)}
                onMouseLeave={() => onMotifHover?.(null)}
                title={`${motif.stemRole} motif${motif.isVariation ? ' (variation)' : ''}\n${motif.startTime.toFixed(1)}s - ${motif.endTime.toFixed(1)}s\nGroup: ${motif.groupId || 'none'}`}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

