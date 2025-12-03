/**
 * Main App component.
 */
import { useState } from 'react';
import { useProject } from './context/ProjectContext';
import IngestPage from './pages/IngestPage';
import RegionMapPage from './pages/RegionMapPage';
import VisualComposerPage from './pages/VisualComposerPage';
import { VISUAL_COMPOSER_ENABLED } from './config';
import './App.css';

type AppView = 'ingest' | 'regionMap' | 'visualComposer';

function App(): JSX.Element {
  const { referenceId, regions } = useProject();
  const [view, setView] = useState<AppView>('ingest');

  return (
    <div className="app">
      <header>
        <h1>Song Structure Replicator</h1>
        <div className="header-info">
          {referenceId && <span>Reference ID: {referenceId}</span>}
          {regions.length > 0 && <span>Regions: {regions.length}</span>}
        </div>
        <nav className="header-nav">
          <button
            className={view === 'ingest' ? 'nav-button active' : 'nav-button'}
            onClick={() => setView('ingest')}
          >
            Ingest
          </button>
          <button
            className={view === 'regionMap' ? 'nav-button active' : 'nav-button'}
            onClick={() => setView('regionMap')}
            disabled={!referenceId || regions.length === 0}
          >
            Region Map
          </button>
          {VISUAL_COMPOSER_ENABLED && referenceId && regions.length > 0 && (
            <button
              className="dev-button"
              style={{ margin: '12px', padding: '8px 12px' }}
              onClick={() => setView('visualComposer')}
            >
              [Dev] Open Visual Composer
            </button>
          )}
        </nav>
      </header>
      <main>
        {view === 'ingest' && <IngestPage onAnalysisComplete={() => setView('regionMap')} />}
        {view === 'regionMap' && (
          <>
            <RegionMapPage />
          </>
        )}
        {view === 'visualComposer' && (
          <VisualComposerPage onBack={() => setView('regionMap')} />
        )}
      </main>
    </div>
  );
}

export default App;

