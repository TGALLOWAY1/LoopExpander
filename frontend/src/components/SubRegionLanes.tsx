/**
 * SubRegionLanes component for displaying DNA-style lane visualization of subregion patterns.
 * 
 * This component renders 4 horizontal lanes (Drums, Bass, Instruments, Vocals) with
 * adjacent blocks representing subregion patterns. Each block shows:
 * - Repetition: same motif group → visually identical blocks
 * - Variation: altered pattern → dashed border/hatched
 * - Silence: empty gaps or faint outlines
 * - Density: intensity mapped to opacity
 */
import { SubRegionPattern, StemCategory } from '../api/reference';
import './SubRegionLanes.css';

export type SubRegionLanesProps = {
  regionId: string;
  lanes: Record<StemCategory, SubRegionPattern[]>;
  regionStartBar: number;
  regionEndBar: number;
  onPatternHover?: (pattern: SubRegionPattern | null) => void;
  highlightedMotifGroupId?: string | null;
};

/**
 * Get base color for a stem category.
 */
function getStemCategoryColor(stemCategory: StemCategory): string {
  switch (stemCategory) {
    case 'drums':
      return '#ff6b6b'; // Red
    case 'bass':
      return '#4ecdc4'; // Teal
    case 'instruments':
      return '#95e1d3'; // Light teal
    case 'vocals':
      return '#f38181'; // Pink
    default:
      return '#999';
  }
}

/**
 * Get label for a stem category.
 */
function getStemCategoryLabel(stemCategory: StemCategory): string {
  switch (stemCategory) {
    case 'drums':
      return 'Drums';
    case 'bass':
      return 'Bass';
    case 'instruments':
      return 'Inst';
    case 'vocals':
      return 'Vox';
    default:
      return stemCategory;
  }
}

/**
 * Calculate width percentage for a pattern block within the region.
 */
function calculateBlockWidth(
  pattern: SubRegionPattern,
  regionStartBar: number,
  regionEndBar: number
): number {
  const regionBarSpan = regionEndBar - regionStartBar;
  if (regionBarSpan <= 0) return 0;
  const patternBarSpan = pattern.endBar - pattern.startBar;
  return (patternBarSpan / regionBarSpan) * 100;
}

/**
 * Calculate left offset percentage for a pattern block within the region.
 */
function calculateBlockLeft(
  pattern: SubRegionPattern,
  regionStartBar: number,
  regionEndBar: number
): number {
  const regionBarSpan = regionEndBar - regionStartBar;
  if (regionBarSpan <= 0) return 0;
  const offsetBars = pattern.startBar - regionStartBar;
  return (offsetBars / regionBarSpan) * 100;
}

export function SubRegionLanes({
  regionId,
  lanes,
  regionStartBar,
  regionEndBar,
  onPatternHover,
  highlightedMotifGroupId,
}: SubRegionLanesProps): JSX.Element {
  const stemCategories: StemCategory[] = ['drums', 'bass', 'instruments', 'vocals'];

  return (
    <div className="subregion-lanes">
      {stemCategories.map((stemCategory) => {
        const patterns = lanes[stemCategory] || [];
        const baseColor = getStemCategoryColor(stemCategory);
        const label = getStemCategoryLabel(stemCategory);

        return (
          <div key={stemCategory} className="subregion-lane">
            <div className="subregion-lane-label">{label}</div>
            <div className="subregion-lane-blocks">
              {patterns.map((pattern) => {
                const widthPercent = calculateBlockWidth(pattern, regionStartBar, regionEndBar);
                const leftPercent = calculateBlockLeft(pattern, regionStartBar, regionEndBar);
                const opacity = pattern.intensity ?? 0.5;
                const isHighlighted = highlightedMotifGroupId === pattern.motifGroupId;
                const isVariation = pattern.isVariation ?? false;
                const isSilence = pattern.isSilence ?? false;

                // For silence, render a faint border-only block or gap
                // We'll render a very faint block with border only
                const blockStyle: React.CSSProperties = {
                  position: 'absolute',
                  left: `${leftPercent}%`,
                  width: `${widthPercent}%`,
                  backgroundColor: isSilence ? 'transparent' : baseColor,
                  opacity: isSilence ? 0.2 : opacity,
                  borderColor: baseColor,
                  borderWidth: isSilence ? '1px' : '0',
                  borderStyle: isVariation ? 'dashed' : 'solid',
                };

                const displayLabel = pattern.label || pattern.motifGroupId || '';

                return (
                  <div
                    key={pattern.id}
                    className={`subregion-block ${isVariation ? 'subregion-block--variation' : ''} ${isSilence ? 'subregion-block--silence' : ''} ${isHighlighted ? 'subregion-block--highlighted' : ''}`}
                    style={blockStyle}
                    onMouseEnter={() => onPatternHover?.(pattern)}
                    onMouseLeave={() => onPatternHover?.(null)}
                    title={`${stemCategory}: ${displayLabel || 'No label'}\nBars: ${pattern.startBar.toFixed(1)} - ${pattern.endBar.toFixed(1)}\n${isVariation ? 'Variation' : ''}${isSilence ? 'Silence' : ''}\nIntensity: ${(opacity * 100).toFixed(0)}%`}
                  >
                    {!isSilence && displayLabel && widthPercent > 5 && (
                      <span className="subregion-block-label">{displayLabel}</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

