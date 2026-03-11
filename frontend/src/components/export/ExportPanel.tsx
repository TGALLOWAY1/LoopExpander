/**
 * ExportPanel - Export dialog for downloading arranged stems, markers, and structure.
 *
 * Shows checkboxes for what to include and format selection,
 * then triggers a download of the ZIP bundle.
 */
import { useState, useCallback } from 'react';
import './ExportPanel.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface ExportPanelProps {
  projectId: string;
  onClose: () => void;
}

type StemFormat = 'wav16' | 'wav24' | 'aiff';

const FORMAT_LABELS: Record<StemFormat, string> = {
  wav16: 'WAV 16-bit',
  wav24: 'WAV 24-bit',
  aiff: 'AIFF 16-bit',
};

export default function ExportPanel({
  projectId,
  onClose,
}: ExportPanelProps): JSX.Element {
  const [includeStems, setIncludeStems] = useState(true);
  const [includeMidi, setIncludeMidi] = useState(true);
  const [includeJson, setIncludeJson] = useState(true);
  const [includeCsv, setIncludeCsv] = useState(false);
  const [stemFormat, setStemFormat] = useState<StemFormat>('wav16');
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = useCallback(async () => {
    setExporting(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/project/${projectId}/export`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            includeStems,
            includeMarkersMidi: includeMidi,
            includeStructureJson: includeJson,
            includeMarkersCsv: includeCsv,
            stemFormat,
          }),
        },
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Export failed' }));
        throw new Error(err.detail || `Export failed with status ${response.status}`);
      }

      // Download the ZIP
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `loopexpander_export_${projectId.slice(0, 8)}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setExporting(false);
    }
  }, [projectId, includeStems, includeMidi, includeJson, includeCsv, stemFormat, onClose]);

  const nothingSelected = !includeStems && !includeMidi && !includeJson && !includeCsv;

  return (
    <div className="export-overlay" onClick={onClose}>
      <div className="export-panel" onClick={(e) => e.stopPropagation()}>
        <div className="export-panel-header">
          <h3>Export Arrangement</h3>
          <button className="export-close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="export-panel-body">
          {/* Content checkboxes */}
          <div className="export-section">
            <h4>Include in export:</h4>
            <label className="export-checkbox">
              <input
                type="checkbox"
                checked={includeStems}
                onChange={(e) => setIncludeStems(e.target.checked)}
              />
              <span>Audio stems (one file per role)</span>
            </label>
            <label className="export-checkbox">
              <input
                type="checkbox"
                checked={includeMidi}
                onChange={(e) => setIncludeMidi(e.target.checked)}
              />
              <span>MIDI markers (section boundaries)</span>
            </label>
            <label className="export-checkbox">
              <input
                type="checkbox"
                checked={includeJson}
                onChange={(e) => setIncludeJson(e.target.checked)}
              />
              <span>Structure JSON (full arrangement data)</span>
            </label>
            <label className="export-checkbox">
              <input
                type="checkbox"
                checked={includeCsv}
                onChange={(e) => setIncludeCsv(e.target.checked)}
              />
              <span>CSV markers (section boundaries)</span>
            </label>
          </div>

          {/* Format selection */}
          {includeStems && (
            <div className="export-section">
              <h4>Stem format:</h4>
              <div className="export-format-options">
                {(Object.keys(FORMAT_LABELS) as StemFormat[]).map((fmt) => (
                  <label key={fmt} className="export-radio">
                    <input
                      type="radio"
                      name="stemFormat"
                      value={fmt}
                      checked={stemFormat === fmt}
                      onChange={() => setStemFormat(fmt)}
                    />
                    <span>{FORMAT_LABELS[fmt]}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* What will be included summary */}
          <div className="export-summary">
            <span className="export-summary-label">ZIP will contain:</span>
            <ul>
              {includeStems && <li>stems/*.{stemFormat === 'aiff' ? 'aif' : 'wav'}</li>}
              {includeJson && <li>arrangement.json</li>}
              {includeMidi && <li>markers.mid</li>}
              {includeCsv && <li>markers.csv</li>}
              {nothingSelected && <li className="export-nothing">Nothing selected</li>}
            </ul>
          </div>

          {/* Error */}
          {error && (
            <div className="export-error">
              {error}
              <button onClick={() => setError(null)}>×</button>
            </div>
          )}
        </div>

        <div className="export-panel-footer">
          <button className="export-cancel-btn" onClick={onClose}>
            Cancel
          </button>
          <button
            className="export-download-btn"
            onClick={handleExport}
            disabled={exporting || nothingSelected}
          >
            {exporting ? 'Exporting...' : 'Download ZIP'}
          </button>
        </div>
      </div>
    </div>
  );
}
