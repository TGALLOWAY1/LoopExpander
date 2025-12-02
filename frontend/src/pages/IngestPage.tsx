/**
 * Ingest page for uploading and analyzing reference tracks.
 */
import { useState } from 'react';
import { useProject } from '../context/ProjectContext';
import { uploadReference, analyzeReference, fetchRegions, createGalliumDevReference } from '../api/reference';
import './IngestPage.css';

type Status = 'idle' | 'uploading' | 'analyzing' | 'complete' | 'error';

interface IngestPageProps {
  onAnalysisComplete?: () => void;
}

interface FileState {
  file: File | null;
  name: string;
}

function IngestPage({ onAnalysisComplete }: IngestPageProps): JSX.Element {
  const { setReferenceId, setRegions } = useProject();
  
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

