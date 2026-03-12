/**
 * EnergyOverlay renders multi-layer energy curves as stacked area charts
 * and transition markers as vertical indicators on the timeline.
 *
 * Supported layers:
 * - Loudness (RMS/LUFS) — blue
 * - Brightness (Spectral Centroid) — orange
 * - Bass Energy (20-80Hz) — red
 * - Transient Rate — green
 */
import React, { useRef, useEffect, useState, useCallback } from 'react';
import { EnergyCurveResponse } from '../../api/referenceMix';

interface EnergyOverlayProps {
  energyCurve: EnergyCurveResponse;
  totalBars: number;
  barWidth: number;
}

interface CurveLayer {
  id: string;
  label: string;
  color: string;
  fillAlpha: number;
  strokeAlpha: number;
  getData: (curve: EnergyCurveResponse) => number[] | undefined;
}

const CURVE_LAYERS: CurveLayer[] = [
  {
    id: 'loudness',
    label: 'Loudness',
    color: '25, 118, 210',   // blue
    fillAlpha: 0.25,
    strokeAlpha: 0.7,
    getData: (c) => c.multiCurves?.lufs ?? c.barEnergies,
  },
  {
    id: 'brightness',
    label: 'Brightness',
    color: '255, 152, 0',    // orange
    fillAlpha: 0.2,
    strokeAlpha: 0.7,
    getData: (c) => c.multiCurves?.spectralCentroid,
  },
  {
    id: 'bass',
    label: 'Bass',
    color: '244, 67, 54',    // red
    fillAlpha: 0.2,
    strokeAlpha: 0.7,
    getData: (c) => c.multiCurves?.bassEnergy,
  },
  {
    id: 'transients',
    label: 'Transients',
    color: '76, 175, 80',    // green
    fillAlpha: 0.2,
    strokeAlpha: 0.7,
    getData: (c) => c.multiCurves?.transientDensity,
  },
];

export const EnergyOverlay: React.FC<EnergyOverlayProps> = ({
  energyCurve,
  totalBars,
  barWidth,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [visibleLayers, setVisibleLayers] = useState<Set<string>>(
    new Set(['loudness'])
  );
  const height = 80;
  const width = totalBars * barWidth;

  const hasMultiCurves = !!energyCurve.multiCurves;

  const toggleLayer = useCallback((layerId: string) => {
    setVisibleLayers((prev) => {
      const next = new Set(prev);
      if (next.has(layerId)) {
        // Don't allow removing all layers
        if (next.size > 1) next.delete(layerId);
      } else {
        next.add(layerId);
      }
      return next;
    });
  }, []);

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

    // Draw each visible layer
    const layersToDraw = CURVE_LAYERS.filter(
      (l) => visibleLayers.has(l.id) && l.getData(energyCurve)
    );

    for (const layer of layersToDraw) {
      const values = layer.getData(energyCurve);
      if (!values || values.length === 0) continue;

      // Area fill
      ctx.beginPath();
      ctx.moveTo(0, height);
      for (let i = 0; i < values.length && i < totalBars; i++) {
        const x = (i + 0.5) * barWidth;
        const y = height - values[i] * (height - 4);
        ctx.lineTo(x, y);
      }
      const lastIdx = Math.min(values.length, totalBars) - 1;
      ctx.lineTo((lastIdx + 0.5) * barWidth, height);
      ctx.closePath();

      const gradient = ctx.createLinearGradient(0, 0, 0, height);
      gradient.addColorStop(0, `rgba(${layer.color}, ${layer.fillAlpha})`);
      gradient.addColorStop(1, `rgba(${layer.color}, 0.02)`);
      ctx.fillStyle = gradient;
      ctx.fill();

      // Stroke line
      ctx.beginPath();
      for (let i = 0; i < values.length && i < totalBars; i++) {
        const x = (i + 0.5) * barWidth;
        const y = height - values[i] * (height - 4);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = `rgba(${layer.color}, ${layer.strokeAlpha})`;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }, [energyCurve, totalBars, barWidth, width, height, visibleLayers]);

  return (
    <div className="sc-energy-overlay-row">
      <div
        className="sc-lane-label"
        style={{ flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}
      >
        Energy
        <div className="sc-energy-toggle-group">
          {CURVE_LAYERS.map((layer) => {
            // Only show multi-curve toggles if data exists
            if (layer.id !== 'loudness' && !hasMultiCurves) return null;
            const active = visibleLayers.has(layer.id);
            return (
              <button
                key={layer.id}
                className={`sc-energy-toggle ${active ? 'active' : ''}`}
                style={
                  active
                    ? { background: `rgb(${layer.color})`, borderColor: `rgb(${layer.color})` }
                    : undefined
                }
                onClick={() => toggleLayer(layer.id)}
                title={`Toggle ${layer.label} curve`}
              >
                {layer.label}
              </button>
            );
          })}
        </div>
      </div>
      <div className="sc-timeline-scroll">
        <div
          className="sc-energy-canvas-container"
          style={{ width: `${width}px`, height: `${height}px`, position: 'relative' }}
        >
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
