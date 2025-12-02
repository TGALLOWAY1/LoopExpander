/**
 * RegionBlock component for displaying a single region in the timeline.
 */
import React from 'react';
import { Region } from '../api/reference';
import './RegionBlock.css';

export type RegionBlockProps = {
  region: Region;
  totalDuration: number;
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

export function RegionBlock({ region, totalDuration }: RegionBlockProps): JSX.Element {
  const widthPercent = (region.duration / totalDuration) * 100;
  const backgroundColor = getRegionColor(region.type);
  const borderColor = getRegionBorderColor(region.type);

  return (
    <div
      className="region-block"
      style={{
        width: `${widthPercent}%`,
        backgroundColor,
        borderColor,
      }}
      title={`${region.name} (${region.type}): ${region.start.toFixed(1)}s - ${region.end.toFixed(1)}s`}
    >
      <div className="region-block-content">
        <div className="region-name">{region.name}</div>
        <div className="region-time">
          {region.start.toFixed(1)}s - {region.end.toFixed(1)}s
        </div>
      </div>
    </div>
  );
}

