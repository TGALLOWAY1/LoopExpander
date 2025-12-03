/**
 * StemLaneHeader component for displaying lane name and optional sensitivity slider.
 * 
 * This component is used inline with each stem lane in the 5-layer Region Map.
 * The slider appears in a collapsible section below the lane name when the lane is focused.
 */
import React, { useState } from "react";
import { StemCategory } from "../types/callResponseLanes";
import './StemLaneHeader.css';

interface StemLaneHeaderProps {
  stem: StemCategory;
  label: string;
  sensitivityValue?: number;
  onSensitivityChange?: (value: number) => void;
  showSlider?: boolean;
}

export const StemLaneHeader: React.FC<StemLaneHeaderProps> = ({
  stem,
  label,
  sensitivityValue,
  onSensitivityChange,
  showSlider = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Auto-expand when slider should be shown
  React.useEffect(() => {
    if (showSlider) {
      setIsExpanded(true);
    }
  }, [showSlider]);

  const handleToggle = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="stem-lane-header">
      <div className="stem-lane-header-main">
        <span className="stem-lane-label">{label}</span>
        {showSlider && (
          <button
            type="button"
            className="stem-lane-chevron"
            onClick={handleToggle}
            aria-label={isExpanded ? `Collapse ${label} sensitivity controls` : `Expand ${label} sensitivity controls`}
            aria-expanded={isExpanded}
          >
            <span className={`stem-lane-chevron-icon ${isExpanded ? 'expanded' : ''}`}>▼</span>
          </button>
        )}
      </div>
      {showSlider && isExpanded && typeof sensitivityValue === "number" && onSensitivityChange && (
        <div className="stem-lane-slider-section">
          <div className="stem-lane-slider-container">
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={sensitivityValue}
              onChange={(e) => onSensitivityChange(parseFloat(e.target.value))}
              className="stem-lane-sensitivity-slider"
              aria-label={`${label} sensitivity`}
              title={`${label} sensitivity: ${sensitivityValue.toFixed(2)}`}
            />
            <span className="stem-lane-sensitivity-value">{sensitivityValue.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  );
};

