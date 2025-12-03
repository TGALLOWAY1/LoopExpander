/**
 * FiveLayerRegionMap component for displaying regions and call/response lanes.
 * 
 * Layout:
 * - Layer 1 (top): Full song region lane showing region blocks
 * - Layers 2-5: Stem lanes (Drums, Bass, Instruments, Vocals) showing call/response events
 * 
 * All layers share a common time scale (bars) for vertical alignment.
 */
import React, { useState } from 'react';
import { Region } from '../api/reference';
import { StemCallResponseLane, StemCategory } from '../types/callResponseLanes';
import { useMotifSensitivity } from '../hooks/useMotifSensitivity';
import { StemLaneHeader } from './StemLaneHeader';
import './FiveLayerRegionMap.css';

export type FiveLayerRegionMapProps = {
  regions: Region[];
  lanes: StemCallResponseLane[];
  bpm?: number; // BPM for bar-to-pixel calculations (default: 130)
  totalDuration?: number; // Total duration in seconds (optional, computed from regions if not provided)
  referenceId?: string | null; // Reference ID for loading sensitivity config
};

/**
 * Convert seconds to bars (assuming 4/4 time signature).
 */
function secondsToBars(seconds: number, bpm: number): number {
  const beatsPerBar = 4.0;
  const beats = (seconds * bpm) / 60.0;
  return beats / beatsPerBar;
}

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
 * Get base color for a stem category.
 */
function getStemColor(stem: string): string {
  switch (stem) {
    case 'drums':
      return '#4caf50'; // Green
    case 'bass':
      return '#2196f3'; // Blue
    case 'instruments':
      return '#ff9800'; // Orange
    case 'vocals':
      return '#9c27b0'; // Purple
    default:
      return '#9e9e9e'; // Gray
  }
}

/**
 * Get stem display name.
 */
function getStemDisplayName(stem: string): string {
  return stem.charAt(0).toUpperCase() + stem.slice(1);
}

export function FiveLayerRegionMap({
  regions,
  lanes,
  bpm = 130,
  totalDuration: providedTotalDuration,
  referenceId,
}: FiveLayerRegionMapProps): JSX.Element {
  // State for focused stem mode
  const [focusedStem, setFocusedStem] = useState<StemCategory | 'all'>('all');
  const [hoveredGroupId, setHoveredGroupId] = useState<string | null>(null);

  // Load sensitivity configuration
  const { config, setConfig } = useMotifSensitivity(referenceId || '');

  // Helper to update sensitivity for a specific stem
  const updateStemSensitivity = (stem: StemCategory, value: number) => {
    if (!config) return;
    const updated = { ...config, [stem]: value };
    setConfig(updated);
    // Note: We do NOT auto-save here; saving will be handled by a separate "Apply" button
  };

  // Compute total duration from regions if not provided
  const totalDuration = providedTotalDuration ?? (
    regions.length > 0
      ? Math.max(...regions.map((r) => r.end))
      : 0
  );

  // Compute total bars for the entire song
  const totalBars = totalDuration > 0 ? secondsToBars(totalDuration, bpm) : 0;

  // Create a map of stem to lane for quick lookup
  const laneMap = new Map<string, StemCallResponseLane>();
  lanes.forEach((lane) => {
    laneMap.set(lane.stem, lane);
  });

  // Ensure all 4 stem lanes exist (even if empty)
  const stemOrder: Array<'drums' | 'bass' | 'instruments' | 'vocals'> = [
    'drums',
    'bass',
    'instruments',
    'vocals',
  ];

  // Calculate bar positions for regions
  const regionsWithBars = regions.map((region) => ({
    ...region,
    startBar: secondsToBars(region.start, bpm),
    endBar: secondsToBars(region.end, bpm),
  }));

  // Helper to convert bar position to percentage
  const barToPercent = (bar: number): number => {
    if (totalBars === 0) return 0;
    return (bar / totalBars) * 100;
  };

  // Helper to calculate width percentage from start and end bars
  const barWidthPercent = (startBar: number, endBar: number): number => {
    if (totalBars === 0) return 0;
    return ((endBar - startBar) / totalBars) * 100;
  };

  if (totalDuration === 0 || regions.length === 0) {
    return (
      <div className="five-layer-region-map">
        <div className="five-layer-empty-state">
          No regions available to display.
        </div>
      </div>
    );
  }

  // Stem options for the control UI
  const stemOptions: Array<{ value: StemCategory | 'all'; label: string }> = [
    { value: 'all', label: 'All' },
    { value: 'drums', label: 'Drums' },
    { value: 'bass', label: 'Bass' },
    { value: 'instruments', label: 'Instruments' },
    { value: 'vocals', label: 'Vocals' },
  ];

  return (
    <div className="five-layer-region-map">
      {/* Focus control toolbar */}
      <div className="five-layer-focus-control">
        <span className="five-layer-focus-label">Focus:</span>
        <div className="five-layer-focus-buttons" role="group" aria-label="Focus on stem lane">
          {stemOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`five-layer-focus-button ${focusedStem === option.value ? 'five-layer-focus-button--active' : ''}`}
              onClick={() => setFocusedStem(option.value)}
              aria-pressed={focusedStem === option.value}
              aria-label={`Focus on ${option.label.toLowerCase()}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Timeline scale header */}
      <div className="five-layer-timeline-header">
        <div className="five-layer-timeline-scale">
          {Array.from({ length: Math.ceil(totalBars / 4) + 1 }, (_, i) => i * 4).map((bar) => {
            const percent = barToPercent(bar);
            return (
              <div
                key={bar}
                className="five-layer-timeline-marker"
                style={{ left: `${percent}%` }}
              >
                <span className="five-layer-timeline-label">{bar}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Layer 1: Region Lane */}
      <div className="five-layer-row">
        <div className="five-layer-label">Song Regions</div>
        <div className="five-layer-content five-layer-region-lane">
          {regionsWithBars.map((region) => {
            const leftPercent = barToPercent(region.startBar);
            const widthPercent = barWidthPercent(region.startBar, region.endBar);
            const backgroundColor = getRegionColor(region.type);
            const borderColor = getRegionBorderColor(region.type);

            return (
              <div
                key={region.id}
                className="five-layer-region-block"
                style={{
                  left: `${leftPercent}%`,
                  width: `${widthPercent}%`,
                  backgroundColor,
                  borderColor,
                }}
                title={`${region.name} (${region.type}): ${region.start.toFixed(1)}s - ${region.end.toFixed(1)}s`}
              >
                <div className="five-layer-region-block-label">{region.name}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Layers 2-5: Stem Lanes */}
      {stemOrder.map((stem) => {
        const lane = laneMap.get(stem) || { stem, events: [] };
        const stemColor = getStemColor(stem);
        const stemDisplayName = getStemDisplayName(stem);
        
        // Determine if this lane should be focused, dimmed, or hidden
        const isFocused = focusedStem === 'all' || focusedStem === stem;
        const isDimmed = focusedStem !== 'all' && focusedStem !== stem;
        
        // Skip rendering if not focused and we're in focus mode (hide instead of dim)
        // For now, we'll dim instead of hide for better UX
        // if (focusedStem !== 'all' && focusedStem !== stem) {
        //   return null;
        // }

        return (
          <div 
            key={stem} 
            className={`five-layer-row ${isFocused ? 'five-layer-row--focused' : ''} ${isDimmed ? 'five-layer-row--dimmed' : ''}`}
          >
            <div className={`five-layer-label ${isFocused ? 'five-layer-label--focused' : ''} ${isDimmed ? 'five-layer-label--dimmed' : ''}`}>
              <StemLaneHeader
                stem={stem}
                label={stemDisplayName}
                sensitivityValue={config?.[stem]}
                onSensitivityChange={(val) => updateStemSensitivity(stem, val)}
                showSlider={focusedStem === stem}
              />
            </div>
            <div className={`five-layer-content five-layer-stem-lane ${isFocused ? 'five-layer-stem-lane--focused' : ''} ${isDimmed ? 'five-layer-stem-lane--dimmed' : ''}`}>
              {lane.events.length === 0 && (
                <div className="stem-lane-empty">
                  No call/response for {stemDisplayName}
                </div>
              )}
              {lane.events.map((event) => {
                const leftPercent = barToPercent(event.startBar);
                const widthPercent = barWidthPercent(event.startBar, event.endBar);
                
                // Encode role: call = solid, response = outlined
                const isCall = event.role === 'call';
                const baseOpacity = event.intensity != null ? Math.max(0.3, Math.min(1.0, event.intensity)) : (isCall ? 0.8 : 0.5);
                
                // Apply focus/dim opacity
                let finalOpacity = baseOpacity;
                if (isDimmed) {
                  finalOpacity = baseOpacity * 0.2; // Dim to 20% of original opacity
                }
                
                // Check if this event should be highlighted (same groupId as hovered)
                const isHighlighted = hoveredGroupId !== null && hoveredGroupId === event.groupId;
                
                return (
                  <div
                    key={event.id}
                    className={`five-layer-event-block ${isCall ? 'five-layer-event-call' : 'five-layer-event-response'} ${isHighlighted ? 'five-layer-event-block--highlighted' : ''}`}
                    style={{
                      left: `${leftPercent}%`,
                      width: `${widthPercent}%`,
                      backgroundColor: isCall ? stemColor : 'transparent',
                      borderColor: stemColor,
                      opacity: finalOpacity,
                    }}
                    onMouseEnter={() => setHoveredGroupId(event.groupId)}
                    onMouseLeave={() => setHoveredGroupId(null)}
                    title={`${stemDisplayName} ${event.role}${event.label ? `: ${event.label}` : ''}\n${event.startBar.toFixed(1)} - ${event.endBar.toFixed(1)} bars${event.intensity != null ? `\nIntensity: ${(event.intensity * 100).toFixed(0)}%` : ''}\nGroup: ${event.groupId}`}
                  >
                    {widthPercent > 2 && (
                      <div className="five-layer-event-label">
                        {event.role === 'call' ? 'C' : 'R'}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      {/* Debug panel (development only) */}
      {process.env.NODE_ENV === 'development' && lanes && (
        <div className="debug-lanes-panel" style={{
          marginTop: '2rem',
          padding: '1rem',
          backgroundColor: '#f5f5f5',
          border: '1px solid #ddd',
          borderRadius: '4px',
          fontSize: '0.8rem',
          maxHeight: '400px',
          overflow: 'auto'
        }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem' }}>Debug: Call/Response Lanes Data</h3>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {JSON.stringify(lanes, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

