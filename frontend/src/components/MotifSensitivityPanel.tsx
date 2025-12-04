/**
 * MotifSensitivityPanel component for adjusting per-stem motif sensitivity.
 * 
 * TODO: This panel is deprecated as a global sidebar; see lane-level sensitivity controls.
 * The component logic will be re-used in lane headers for per-lane sensitivity adjustment.
 */
import { useState, useEffect } from 'react';
import { useMotifSensitivity } from '../hooks/useMotifSensitivity';
import { MotifSensitivityConfig } from '../types/motifSensitivity';
import { reanalyzeMotifs, getMotifs, getCallResponse, getFills, fetchReferenceSubregions } from '../api/reference';
import './MotifSensitivityPanel.css';

export type MotifSensitivityPanelProps = {
  referenceId: string | null;
  onReanalyze?: () => void;
  onDataRefetch?: (data: {
    motifs: { instances: any[]; groups: any[] };
    callResponse: { pairs: any[] };
    fills: { fills: any[] };
    subregions: { regions: any[] };
  }) => void;
};

export function MotifSensitivityPanel({
  referenceId,
  onReanalyze,
  onDataRefetch
}: MotifSensitivityPanelProps): JSX.Element {
  const { config, save, loading, saving, error } = useMotifSensitivity(referenceId || '');
  
  // Local state for slider values (optimistic updates)
  const [localConfig, setLocalConfig] = useState<MotifSensitivityConfig | null>(null);
  
  // State for reanalysis status
  const [reanalyzing, setReanalyzing] = useState(false);
  const [reanalyzeStatus, setReanalyzeStatus] = useState<string | null>(null);

  // Sync local config when hook config changes
  useEffect(() => {
    if (config) {
      setLocalConfig(config);
    }
  }, [config]);

  // Don't render if no referenceId
  if (!referenceId) {
    return (
      <div className="motif-sensitivity-panel">
        <h3>Motif Sensitivity</h3>
        <div className="motif-sensitivity-empty">
          <p>No reference selected.</p>
        </div>
      </div>
    );
  }

  // Show loading state
  if (loading) {
    return (
      <div className="motif-sensitivity-panel">
        <h3>Motif Sensitivity</h3>
        <div className="motif-sensitivity-loading">
          <p>Loading sensitivity settings...</p>
        </div>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="motif-sensitivity-panel">
        <h3>Motif Sensitivity</h3>
        <div className="motif-sensitivity-error">
          <p>Error loading sensitivity: {error instanceof Error ? error.message : 'Unknown error'}</p>
        </div>
      </div>
    );
  }

  // Don't render if no config loaded
  if (!localConfig) {
    return (
      <div className="motif-sensitivity-panel">
        <h3>Motif Sensitivity</h3>
        <div className="motif-sensitivity-empty">
          <p>No sensitivity configuration available.</p>
        </div>
      </div>
    );
  }

  // Handle slider change
  const handleSliderChange = (stem: keyof MotifSensitivityConfig, value: number) => {
    setLocalConfig({
      ...localConfig,
      [stem]: value
    });
  };

  // Handle Apply & Re-Analyze button click
  const handleApplyAndReanalyze = async () => {
    if (!localConfig || !referenceId) return;

    try {
      // Save the configuration
      await save(localConfig);
      
      // Start reanalysis
      setReanalyzing(true);
      setReanalyzeStatus('Re-analyzing...');
      
      // Call reanalyze endpoint
      await reanalyzeMotifs(referenceId);
      
      // Refetch all dependent data
      const [motifsResponse, callResponseResponse, fillsResponse, subregionsResponse] = await Promise.all([
        getMotifs(referenceId), // Uses stored config automatically
        getCallResponse(referenceId),
        getFills(referenceId),
        fetchReferenceSubregions(referenceId)
      ]);
      
      // Pass refetched data to parent if callback provided
      if (onDataRefetch) {
        onDataRefetch({
          motifs: { instances: motifsResponse.instances, groups: motifsResponse.groups },
          callResponse: { pairs: callResponseResponse.pairs },
          fills: { fills: fillsResponse.fills },
          subregions: { regions: subregionsResponse.regions }
        });
      }
      
      // Also call legacy callback if provided
      if (onReanalyze) {
        onReanalyze();
      }
      
      // Show success status
      setReanalyzeStatus('Updated.');
      
      // Clear status after 2 seconds
      setTimeout(() => {
        setReanalyzeStatus(null);
      }, 2000);
      
    } catch (err) {
      console.error('Error during reanalysis:', err);
      setReanalyzeStatus(err instanceof Error ? `Error: ${err.message}` : 'Error during reanalysis');
      
      // Clear error status after 5 seconds
      setTimeout(() => {
        setReanalyzeStatus(null);
      }, 5000);
    } finally {
      setReanalyzing(false);
    }
  };

  // Render slider for a stem
  const renderSlider = (stem: keyof MotifSensitivityConfig, label: string) => {
    const value = localConfig[stem];
    
    return (
      <div key={stem} className="motif-sensitivity-slider-group">
        <div className="motif-sensitivity-slider-header">
          <label htmlFor={`sensitivity-${stem}`} className="motif-sensitivity-label">
            {label}
          </label>
          <span className="motif-sensitivity-value">{value.toFixed(2)}</span>
        </div>
        <input
          id={`sensitivity-${stem}`}
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={value}
          onChange={(e) => handleSliderChange(stem, parseFloat(e.target.value))}
          className="motif-sensitivity-slider"
        />
        <div className="motif-sensitivity-slider-labels">
          <span>Strict</span>
          <span>Loose</span>
        </div>
      </div>
    );
  };

  return (
    <div className="motif-sensitivity-panel">
      <h3>Motif Sensitivity</h3>
      <div className="motif-sensitivity-help">
        <p>Lower sensitivity = stricter grouping. Higher sensitivity = looser grouping.</p>
      </div>
      
      <div className="motif-sensitivity-content">
        {renderSlider('drums', 'Drums')}
        {renderSlider('bass', 'Bass')}
        {renderSlider('vocals', 'Vocals')}
        {renderSlider('instruments', 'Instruments')}
      </div>

      <div className="motif-sensitivity-actions">
        <button
          type="button"
          onClick={handleApplyAndReanalyze}
          disabled={saving || reanalyzing || !localConfig}
          className="motif-sensitivity-apply-button"
        >
          {saving ? 'Saving...' : reanalyzing ? 'Re-analyzing...' : 'Apply & Re-Analyze'}
        </button>
        {reanalyzeStatus && (
          <div className={`motif-sensitivity-status ${reanalyzeStatus.startsWith('Error') ? 'error' : 'success'}`}>
            {reanalyzeStatus}
          </div>
        )}
      </div>

      {error && (
        <div className="motif-sensitivity-error-message">
          {error instanceof Error ? error.message : 'An error occurred'}
        </div>
      )}
    </div>
  );
}

