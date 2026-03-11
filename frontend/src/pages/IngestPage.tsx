/**
 * Ingest page for uploading and analyzing reference tracks.
 */
import { useState } from 'react';
import { useProject } from '../context/ProjectContext';
import { uploadReference, analyzeReference, fetchRegions, createGalliumDevReference } from '../api/reference';
import { uploadReferenceMix, analyzeReferenceMix, getMixRegions } from '../api/referenceMix';
import './IngestPage.css';

type Status = 'idle' | 'uploading' | 'analyzing' | 'complete' | 'error';
type UploadMode = 'single-mix' | 'stems';

interface IngestPageProps {
  onAnalysisComplete?: () => void;
}

interface FileState {
  file: File | null;
  name: string;
}

function IngestPage({ onAnalysisComplete }: IngestPageProps): JSX.Element {
  const { setReferenceId, setRegions } = useProject();

  const [uploadMode, setUploadMode] = useState<UploadMode>('single-mix');

  // Single-mix state
  const [mixFile, setMixFile] = useState<FileState>({ file: null, name: '' });
  const [bpmOverride, setBpmOverride] = useState<string>('');

  // Stems state
  const [files, setFiles] = useState<{
    drums: FileState;
    bass: FileState;
    vocals: FileState;
    instruments: FileState;
    full_mix: FileState;
  }>({
    drums: { file: null, name: '' },
    bass: { file: null, name: '' },
    vocals: { file: null, name: '' },
    instruments: { file: null, name: '' },
    full_mix: { file: null, name: '' },
  });

  const [status, setStatus] = useState<Status>('idle');
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [isGalliumLoading, setIsGalliumLoading] = useState(false);

  // Check if we're in dev mode
  const isDev = import.meta.env.DEV || import.meta.env.MODE !== 'production';

  const handleFileChange = (role: keyof typeof files, event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    setFiles((prev) => ({
      ...prev,
      [role]: {
        file,
        name: file ? file.name : '',
      },
    }));
    setErrorMessage('');
  };

  const allFilesSelected = (): boolean => {
    return Object.values(files).every((f) => f.file !== null);
  };

  const handleMixFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    setMixFile({ file, name: file ? file.name : '' });
    setErrorMessage('');
  };

  const handleAnalyzeMix = async () => {
    if (!mixFile.file) {
      setErrorMessage('Please select an audio file.');
      return;
    }

    setStatus('uploading');
    setStatusMessage('Uploading reference mix...');
    setErrorMessage('');

    try {
      const bpmValue = bpmOverride ? parseFloat(bpmOverride) : undefined;
      const uploadResult = await uploadReferenceMix(mixFile.file, bpmValue);

      setReferenceId(uploadResult.referenceId);
      setStatusMessage(`Upload complete. BPM: ${uploadResult.bpm.toFixed(1)}. Analyzing...`);
      setStatus('analyzing');

      // Run full analysis
      const analysisResult = await analyzeReferenceMix(uploadResult.referenceId);
      setStatusMessage('Analysis complete. Fetching regions...');

      // Fetch regions
      const regionsResponse = await getMixRegions(uploadResult.referenceId);
      // Convert to the Region type expected by ProjectContext
      const regions = regionsResponse.regions.map((r) => ({
        id: r.id,
        name: r.name,
        type: r.type,
        start: r.start,
        end: r.end,
        duration: r.duration,
        motifs: [],
        fills: [],
        callResponse: [],
      }));
      setRegions(regions);

      setStatus('complete');
      setStatusMessage(
        `Analysis complete – ${analysisResult.regionCount} regions, ` +
        `${analysisResult.totalBars} bars, ${analysisResult.transitionCount} transitions detected.`
      );

      if (onAnalysisComplete) {
        onAnalysisComplete();
      }
    } catch (error) {
      setStatus('error');
      setErrorMessage(error instanceof Error ? error.message : 'An error occurred during analysis.');
      setStatusMessage('');
      console.error('Mix analysis error:', error);
    }
  };

  const handleAnalyze = async () => {
    if (!allFilesSelected()) {
      setErrorMessage('Please select all 5 files before analyzing.');
      return;
    }

    setStatus('uploading');
    setStatusMessage('Uploading files...');
    setErrorMessage('');

    try {
      // Step 1: Upload files
      const uploadResult = await uploadReference({
        drums: files.drums.file!,
        bass: files.bass.file!,
        vocals: files.vocals.file!,
        instruments: files.instruments.file!,
        full_mix: files.full_mix.file!,
      });

      setReferenceId(uploadResult.referenceId);
      setStatusMessage(`Upload complete. BPM: ${uploadResult.bpm.toFixed(1)}. Analyzing...`);
      setStatus('analyzing');

      // Step 2: Analyze
      await analyzeReference(uploadResult.referenceId);
      setStatusMessage(`Analysis complete. Fetching regions...`);

      // Step 3: Fetch regions
      const regions = await fetchRegions(uploadResult.referenceId);
      setRegions(regions);

      setStatus('complete');
      setStatusMessage(`Analysis complete – ${regions.length} regions detected.`);
      
      // Call callback to navigate to region map
      if (onAnalysisComplete) {
        onAnalysisComplete();
      }
    } catch (error) {
      setStatus('error');
      setErrorMessage(error instanceof Error ? error.message : 'An error occurred during analysis.');
      setStatusMessage('');
      console.error('Analysis error:', error);
    }
  };

  const handleUseGalliumDevReference = async () => {
    setIsGalliumLoading(true);
    setStatus('uploading');
    setStatusMessage('Loading Gallium test files...');
    setErrorMessage('');

    try {
      // Step 1: Create reference from test files
      const uploadResult = await createGalliumDevReference();

      setReferenceId(uploadResult.referenceId);
      setStatusMessage(`Upload complete. BPM: ${uploadResult.bpm.toFixed(1)}. Analyzing...`);
      setStatus('analyzing');

      // Step 2: Analyze
      await analyzeReference(uploadResult.referenceId);
      setStatusMessage(`Analysis complete. Fetching regions...`);

      // Step 3: Fetch regions
      const regions = await fetchRegions(uploadResult.referenceId);
      setRegions(regions);

      setStatus('complete');
      setStatusMessage(`Analysis complete – ${regions.length} regions detected.`);
      
      // Call callback to navigate to region map
      if (onAnalysisComplete) {
        onAnalysisComplete();
      }
    } catch (error) {
      setStatus('error');
      setErrorMessage(error instanceof Error ? error.message : 'An error occurred while loading Gallium test files.');
      setStatusMessage('');
      console.error('Gallium dev reference error:', error);
    } finally {
      setIsGalliumLoading(false);
    }
  };

  return (
    <div className="ingest-page">
      <div className="ingest-container">
        <h2>Upload Reference Track</h2>

        <div className="upload-mode-toggle" style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
          <button
            className={uploadMode === 'single-mix' ? 'nav-button active' : 'nav-button'}
            onClick={() => setUploadMode('single-mix')}
            disabled={status === 'uploading' || status === 'analyzing'}
          >
            Single Mix
          </button>
          <button
            className={uploadMode === 'stems' ? 'nav-button active' : 'nav-button'}
            onClick={() => setUploadMode('stems')}
            disabled={status === 'uploading' || status === 'analyzing'}
          >
            Stems (Advanced)
          </button>
        </div>

        {uploadMode === 'single-mix' ? (
          <>
            <p className="ingest-description">
              Upload a single full-mix reference track (WAV, AIFF, or MP3) to analyze its structure.
            </p>

            <div className="file-inputs">
              <div className="file-input-group">
                <label htmlFor="reference_mix">Reference Mix</label>
                <input
                  type="file"
                  id="reference_mix"
                  accept="audio/*,.wav,.aiff,.aif,.mp3"
                  onChange={handleMixFileChange}
                  disabled={status === 'uploading' || status === 'analyzing'}
                />
                {mixFile.name && (
                  <span className="file-name">{mixFile.name}</span>
                )}
              </div>

              <div className="file-input-group">
                <label htmlFor="bpm_override">BPM Override (optional)</label>
                <input
                  type="number"
                  id="bpm_override"
                  placeholder="Auto-detect"
                  value={bpmOverride}
                  onChange={(e) => setBpmOverride(e.target.value)}
                  disabled={status === 'uploading' || status === 'analyzing'}
                  min="40"
                  max="300"
                  step="0.1"
                  style={{ maxWidth: '160px' }}
                />
              </div>
            </div>

            <div className="ingest-actions">
              <button
                onClick={handleAnalyzeMix}
                disabled={!mixFile.file || status === 'uploading' || status === 'analyzing' || isGalliumLoading}
                className="analyze-button"
              >
                {status === 'uploading' || status === 'analyzing' ? 'Processing...' : 'Analyze Reference'}
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="ingest-description">
              Upload 4 stems (drums, bass, vocals, instruments) and the full mix to analyze song structure.
            </p>

            <div className="file-inputs">
              <div className="file-input-group">
                <label htmlFor="drums">Drums</label>
                <input
                  type="file"
                  id="drums"
                  accept="audio/*,.wav,.aiff,.aif"
                  onChange={(e) => handleFileChange('drums', e)}
                  disabled={status === 'uploading' || status === 'analyzing'}
                />
                {files.drums.name && (
                  <span className="file-name">{files.drums.name}</span>
                )}
              </div>

              <div className="file-input-group">
                <label htmlFor="bass">Bass</label>
                <input
                  type="file"
                  id="bass"
                  accept="audio/*,.wav,.aiff,.aif"
                  onChange={(e) => handleFileChange('bass', e)}
                  disabled={status === 'uploading' || status === 'analyzing'}
                />
                {files.bass.name && (
                  <span className="file-name">{files.bass.name}</span>
                )}
              </div>

              <div className="file-input-group">
                <label htmlFor="vocals">Vocals</label>
                <input
                  type="file"
                  id="vocals"
                  accept="audio/*,.wav,.aiff,.aif"
                  onChange={(e) => handleFileChange('vocals', e)}
                  disabled={status === 'uploading' || status === 'analyzing'}
                />
                {files.vocals.name && (
                  <span className="file-name">{files.vocals.name}</span>
                )}
              </div>

              <div className="file-input-group">
                <label htmlFor="instruments">Instruments</label>
                <input
                  type="file"
                  id="instruments"
                  accept="audio/*,.wav,.aiff,.aif"
                  onChange={(e) => handleFileChange('instruments', e)}
                  disabled={status === 'uploading' || status === 'analyzing'}
                />
                {files.instruments.name && (
                  <span className="file-name">{files.instruments.name}</span>
                )}
              </div>

              <div className="file-input-group">
                <label htmlFor="full_mix">Full Mix</label>
                <input
                  type="file"
                  id="full_mix"
                  accept="audio/*,.wav,.aiff,.aif"
                  onChange={(e) => handleFileChange('full_mix', e)}
                  disabled={status === 'uploading' || status === 'analyzing'}
                />
                {files.full_mix.name && (
                  <span className="file-name">{files.full_mix.name}</span>
                )}
              </div>
            </div>

            <div className="ingest-actions">
              <button
                onClick={handleAnalyze}
                disabled={!allFilesSelected() || status === 'uploading' || status === 'analyzing' || isGalliumLoading}
                className="analyze-button"
              >
                {status === 'uploading' || status === 'analyzing' ? 'Processing...' : 'Analyze Reference'}
              </button>
            </div>
          </>
        )}

        {isDev && (
          <div className="dev-shortcut">
            <div className="dev-shortcut-header">Dev Shortcut</div>
            <p className="dev-shortcut-description">
              Use the bundled test stems from{' '}
              <code>2. Test Data/Song-1-Gallium-MakeEmWatch-130BPM</code>.
            </p>
            <button
              type="button"
              onClick={handleUseGalliumDevReference}
              disabled={isGalliumLoading || status === 'uploading' || status === 'analyzing'}
              className="dev-shortcut-button"
            >
              {isGalliumLoading ? 'Loading Gallium...' : 'Use Gallium Test Files'}
            </button>
          </div>
        )}

        {statusMessage && (
          <div className={`status-message ${status === 'complete' ? 'success' : ''}`}>
            {statusMessage}
          </div>
        )}

        {errorMessage && (
          <div className="error-message">
            Error: {errorMessage}
          </div>
        )}
      </div>
    </div>
  );
}

export default IngestPage;

