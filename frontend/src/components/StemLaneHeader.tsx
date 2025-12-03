/**
 * StemLaneHeader component for displaying lane name and optional sensitivity slider.
 * 
 * This component is used inline with each stem lane in the 5-layer Region Map.
 */
import React from "react";
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
  return (
    <div className="stem-lane-header">
      <span className="stem-lane-label">{label}</span>
      {showSlider && typeof sensitivityValue === "number" && onSensitivityChange && (
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
      )}
    </div>
  );
};

