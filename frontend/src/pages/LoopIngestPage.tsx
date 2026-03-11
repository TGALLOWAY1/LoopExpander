/**
 * LoopIngestPage - Upload and manage user loop stems.
 *
 * Allows users to upload audio files, assign roles (drums, bass, etc.),
 * view loop details, and manage BPM alignment with the reference track.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useProject } from '../context/ProjectContext';
import {
  UserLoopStem,
  UserLoopBundle,
  StemRole,
  VALID_ROLES,
  ROLE_LABELS,
  ROLE_COLORS,
  uploadUserLoops,
  getUserLoops,
  updateStemRole,
  updateStemBounds,
  deleteUserStem,
  updateLoopBpm,
} from '../api/userLoop';
import './LoopIngestPage.css';

interface LoopIngestPageProps {
  onComplete?: () => void;
}

const LoopIngestPage: React.FC<LoopIngestPageProps> = ({ onComplete }) => {
  const { referenceId } = useProject();
  const [bundle, setBundle] = useState<UserLoopBundle | null>(null);
  const [stems, setStems] = useState<UserLoopStem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bpmInput, setBpmInput] = useState('');
  const [bpmMismatch, setBpmMismatch] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load existing loops on mount
  useEffect(() => {
    if (!referenceId) return;
    getUserLoops(referenceId)
      .then((res) => {
        if (res.bundle) {
          setBundle(res.bundle);
          setStems(res.bundle.stems);
          setBpmInput(String(res.bundle.bpm));
          setBpmMismatch(
            Math.abs(res.bundle.bpmRatio - 1.0) > 0.01,
          );
        }
      })
      .catch((err) => {
        console.error('Failed to load loops:', err);
      });
  }, [referenceId]);

  const handleFileUpload = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0 || !referenceId) return;

      setUploading(true);
      setError(null);

      try {
        const fileArray = Array.from(files);
        const res = await uploadUserLoops(referenceId, fileArray);
        setStems(res.allStems);
        setBpmInput(String(res.bpm));
        setBpmMismatch(Math.abs(res.bpmRatio - 1.0) > 0.01);
        setBundle({
          id: res.bundleId,
          projectId: res.projectId,
          stems: res.allStems,
          bpm: res.bpm,
          detectedBpm: res.detectedBpm,
          bpmRatio: res.bpmRatio,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed');
      } finally {
        setUploading(false);
      }
    },
    [referenceId],
  );

  const handleRoleChange = useCallback(
    async (stemId: string, role: StemRole) => {
      if (!referenceId) return;
      try {
        const res = await updateStemRole(referenceId, stemId, role);
        setStems((prev) =>
          prev.map((s) => (s.id === stemId ? res.stem : s)),
        );
      } catch (err) {
        console.error('Failed to update role:', err);
      }
    },
    [referenceId],
  );

  const handleLoopLengthChange = useCallback(
    async (stemId: string, loopLengthBars: number) => {
      if (!referenceId) return;
      try {
        const res = await updateStemBounds(referenceId, stemId, {
          loopLengthBars,
          endBar: loopLengthBars,
        });
        setStems((prev) =>
          prev.map((s) => (s.id === stemId ? res.stem : s)),
        );
      } catch (err) {
        console.error('Failed to update loop length:', err);
      }
    },
    [referenceId],
  );

  const handleDeleteStem = useCallback(
    async (stemId: string) => {
      if (!referenceId) return;
      try {
        await deleteUserStem(referenceId, stemId);
        setStems((prev) => prev.filter((s) => s.id !== stemId));
      } catch (err) {
        console.error('Failed to delete stem:', err);
      }
    },
    [referenceId],
  );

  const handleBpmOverride = useCallback(async () => {
    if (!referenceId || !bpmInput) return;
    const newBpm = parseFloat(bpmInput);
    if (isNaN(newBpm) || newBpm <= 0) return;

    try {
      const res = await updateLoopBpm(referenceId, newBpm);
      setStems(res.bundle.stems);
      setBpmMismatch(Math.abs(res.bpmRatio - 1.0) > 0.01);
      setBundle(res.bundle);
    } catch (err) {
      console.error('Failed to update BPM:', err);
    }
  }, [referenceId, bpmInput]);

  if (!referenceId) {
    return (
      <div className="loop-ingest-page">
        <div className="loop-ingest-empty">
          <h3>No Reference Track</h3>
          <p>Upload and analyze a reference track first before adding your loops.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="loop-ingest-page">
      <div className="loop-ingest-header">
        <h2>Loop Material</h2>
        <p className="loop-ingest-subtitle">
          Upload your loop stems and assign each to a role for arrangement mapping.
        </p>
      </div>

      {/* Upload area */}
      <div className="loop-upload-area">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".wav,.aiff,.aif,.mp3"
          style={{ display: 'none' }}
          onChange={(e) => handleFileUpload(e.target.files)}
        />
        <button
          className="loop-upload-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? 'Uploading...' : 'Upload Loop Stems'}
        </button>
        <span className="loop-upload-hint">WAV, AIFF, or MP3</span>
        {error && <div className="loop-upload-error">{error}</div>}
      </div>

      {/* BPM controls */}
      {bundle && (
        <div className="loop-bpm-section">
          <div className="loop-bpm-info">
            <span className="loop-bpm-label">Loop BPM:</span>
            <input
              type="number"
              className="loop-bpm-input"
              value={bpmInput}
              onChange={(e) => setBpmInput(e.target.value)}
              onBlur={handleBpmOverride}
              onKeyDown={(e) => e.key === 'Enter' && handleBpmOverride()}
              min={40}
              max={300}
              step={1}
            />
            {bundle.detectedBpm > 0 && (
              <span className="loop-bpm-detected">
                (detected: {bundle.detectedBpm.toFixed(1)})
              </span>
            )}
          </div>
          {bpmMismatch && (
            <div className="loop-bpm-warning">
              BPM mismatch with reference. Loops will be time-stretched at export
              (ratio: {bundle.bpmRatio.toFixed(3)}x).
            </div>
          )}
        </div>
      )}

      {/* Stem list */}
      {stems.length > 0 && (
        <div className="loop-stems-list">
          <h3>Uploaded Stems ({stems.length})</h3>
          <div className="loop-stems-table">
            <div className="loop-stem-header">
              <span className="col-filename">File</span>
              <span className="col-role">Role</span>
              <span className="col-length">Bars</span>
              <span className="col-duration">Duration</span>
              <span className="col-actions">Actions</span>
            </div>
            {stems.map((stem) => (
              <div
                key={stem.id}
                className="loop-stem-row"
                style={{ borderLeft: `4px solid ${ROLE_COLORS[stem.role]}` }}
              >
                <span className="col-filename" title={stem.filename}>
                  {stem.filename}
                </span>
                <span className="col-role">
                  <select
                    value={stem.role}
                    onChange={(e) =>
                      handleRoleChange(stem.id, e.target.value as StemRole)
                    }
                  >
                    {VALID_ROLES.map((role) => (
                      <option key={role} value={role}>
                        {ROLE_LABELS[role]}
                      </option>
                    ))}
                  </select>
                </span>
                <span className="col-length">
                  <select
                    value={stem.loopLengthBars}
                    onChange={(e) =>
                      handleLoopLengthChange(stem.id, parseInt(e.target.value))
                    }
                  >
                    {[1, 2, 4, 8, 16, 32, 64].map((len) => (
                      <option key={len} value={len}>
                        {len}
                      </option>
                    ))}
                  </select>
                </span>
                <span className="col-duration">
                  {stem.durationSeconds.toFixed(1)}s
                </span>
                <span className="col-actions">
                  <button
                    className="loop-stem-delete-btn"
                    onClick={() => handleDeleteStem(stem.id)}
                    title="Remove stem"
                  >
                    x
                  </button>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Continue button */}
      {stems.length > 0 && onComplete && (
        <div className="loop-ingest-footer">
          <button className="loop-continue-btn" onClick={onComplete}>
            Continue to Arrangement
          </button>
        </div>
      )}
    </div>
  );
};

export default LoopIngestPage;
