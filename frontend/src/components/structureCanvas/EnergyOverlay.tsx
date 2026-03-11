/**
 * EnergyOverlay renders the energy curve as an area chart and
 * transition markers as vertical indicators on the timeline.
 */
import React, { useRef, useEffect, useState } from 'react';
import { EnergyCurveResponse } from '../../api/referenceMix';

interface EnergyOverlayProps {
  energyCurve: EnergyCurveResponse;
  totalBars: number;
  barWidth: number;
}

type ViewMode = 'energy' | 'density';

export const EnergyOverlay: React.FC<EnergyOverlayProps> = ({
  energyCurve,
  totalBars,
  barWidth,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('energy');
  const height = 64;
  const width = totalBars * barWidth;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const values = energyCurve.barEnergies;
    if (!values || values.length === 0) return;

    // Draw area chart
    ctx.beginPath();
    ctx.moveTo(0, height);

    for (let i = 0; i < values.length && i < totalBars; i++) {
      const x = (i + 0.5) * barWidth;
      const y = height - values[i] * (height - 4);
      if (i === 0) {
        ctx.lineTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }

    // Close the area
    const lastIdx = Math.min(values.length, totalBars) - 1;
    ctx.lineTo((lastIdx + 0.5) * barWidth, height);
    ctx.closePath();

    // Fill gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, 'rgba(25, 118, 210, 0.3)');
    gradient.addColorStop(1, 'rgba(25, 118, 210, 0.05)');
    ctx.fillStyle = gradient;
    ctx.fill();

    // Stroke line
    ctx.beginPath();
    for (let i = 0; i < values.length && i < totalBars; i++) {
      const x = (i + 0.5) * barWidth;
      const y = height - values[i] * (height - 4);
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.strokeStyle = 'rgba(25, 118, 210, 0.6)';
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }, [energyCurve.barEnergies, totalBars, barWidth, width, height, viewMode]);

  return (
    <div className="sc-energy-overlay-row">
      <div className="sc-lane-label" style={{ flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
        Energy
        <div className="sc-energy-toggle-group">
          <button
            className={`sc-energy-toggle ${viewMode === 'energy' ? 'active' : ''}`}
            onClick={() => setViewMode('energy')}
          >
            RMS
          </button>
          <button
            className={`sc-energy-toggle ${viewMode === 'density' ? 'active' : ''}`}
            onClick={() => setViewMode('density')}
          >
            Density
          </button>
        </div>
      </div>
      <div className="sc-timeline-scroll">
        <div className="sc-energy-canvas-container" style={{ width: `${width}px`, height: `${height}px`, position: 'relative' }}>
          <canvas
            ref={canvasRef}
            className="sc-energy-canvas"
            style={{ width: `${width}px`, height: `${height}px` }}
          />
          {/* Transition markers */}
          {energyCurve.transitionMarkers.map((marker, i) => (
            <div
              key={i}
              className={`sc-transition-marker ${marker.type}`}
              style={{ left: `${marker.bar * barWidth}px` }}
              title={`${marker.type} at bar ${marker.bar} (delta: ${marker.energyDelta.toFixed(2)})`}
            >
              <span className="sc-transition-label">{marker.type}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
