/**
 * RegionBlock component for displaying a single region in the timeline.
 * 
 * Component structure:
 * - Top half: Region title, type, duration/time summary
 * - Bottom half: DNA lanes showing subregion patterns per stem category
 */
import { Region, MotifInstance, MotifGroup, RegionSubRegions, StemCategory } from '../api/reference';
import { SubRegionLanes } from './SubRegionLanes';
import './RegionBlock.css';

export type RegionBlockProps = {
  region: Region;
  totalDuration: number;
  motifs?: MotifInstance[];
  motifGroups?: MotifGroup[];
  highlightedGroupId?: string | null;
  onMotifHover?: (groupId: string | null) => void;
  subregions?: RegionSubRegions | null;
  bpm?: number; // BPM for bar calculations
  showMotifDots?: boolean; // Feature flag to show/hide old motif dot overlay
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

/**
 * Convert seconds to bars (assuming 4/4 time signature).
 */
function secondsToBars(seconds: number, bpm: number): number {
  const beatsPerBar = 4.0;
  const beats = (seconds * bpm) / 60.0;
  return beats / beatsPerBar;
}

export function RegionBlock({ 
  region, 
  totalDuration, 
  motifs = [],
  motifGroups = [],
  highlightedGroupId = null,
  onMotifHover,
  subregions,
  bpm = 120, // Default BPM if not provided
  showMotifDots = false, // Default to false - use DNA lanes instead
}: RegionBlockProps): JSX.Element {
  const widthPercent = (region.duration / totalDuration) * 100;
  const backgroundColor = getRegionColor(region.type);
  const borderColor = getRegionBorderColor(region.type);

  // Get lanes for this region from subregions
  const lanes = subregions?.lanes || {
    drums: [],
    bass: [],
    instruments: [],
    vocals: [],
  };

  // Calculate region bar positions from subregion patterns (if available)
  // Fall back to time-based calculation if no patterns
  let regionStartBar = 0;
  let regionEndBar = 0;
  
  if (subregions) {
    // Find min startBar and max endBar across all lanes
    const allPatterns = [
      ...lanes.drums,
      ...lanes.bass,
      ...lanes.instruments,
      ...lanes.vocals,
    ];
    
    if (allPatterns.length > 0) {
      regionStartBar = Math.min(...allPatterns.map(p => p.startBar));
      regionEndBar = Math.max(...allPatterns.map(p => p.endBar));
    } else {
      // Fallback to time-based calculation
      regionStartBar = secondsToBars(region.start, bpm);
      regionEndBar = secondsToBars(region.end, bpm);
    }
  } else {
    // No subregions yet - use time-based calculation
    regionStartBar = secondsToBars(region.start, bpm);
    regionEndBar = secondsToBars(region.end, bpm);
  }

  // Filter motifs that fall within this region (for old dot overlay if enabled)
  const regionMotifs = motifs.filter(
    (motif) => 
      motif.startTime >= region.start && 
      motif.startTime < region.end &&
      motif.regionIds.includes(region.id)
  );

  // Create a map of groupId to color (for old dot overlay)
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
      {/* Top half: Region info */}
      <div className="region-block-content">
        <div className="region-name">{region.name}</div>
        <div className="region-time">
          {region.start.toFixed(1)}s - {region.end.toFixed(1)}s
        </div>
      </div>
      
      {/* Bottom half: DNA lanes */}
      {subregions ? (
        <div className="region-block-lanes">
          <SubRegionLanes
            regionId={region.id}
            lanes={lanes}
            regionStartBar={regionStartBar}
            regionEndBar={regionEndBar}
            onPatternHover={(pattern) => {
              // Highlight motif group when hovering over pattern
              if (pattern?.motifGroupId) {
                onMotifHover?.(pattern.motifGroupId);
              } else {
                onMotifHover?.(null);
              }
            }}
            highlightedMotifGroupId={highlightedGroupId}
          />
        </div>
      ) : (
        <div className="region-block-lanes-loading">
          <div className="loading-patterns">Loading patterns...</div>
        </div>
      )}

      {/* Old motif dot overlay (gated by feature flag) */}
      {showMotifDots && regionMotifs.length > 0 && (
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

