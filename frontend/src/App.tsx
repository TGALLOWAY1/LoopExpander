/**
 * Main App component.
 */
import { useState } from 'react';
import { useProject } from './context/ProjectContext';
import IngestPage from './pages/IngestPage';
import RegionMapPage from './pages/RegionMapPage';
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
        </nav>
      </header>
      <main>
        {view === 'ingest' && <IngestPage onAnalysisComplete={() => setView('regionMap')} />}
        {view === 'regionMap' && (
          <>
            <RegionMapPage />
            {VISUAL_COMPOSER_ENABLED && view === 'regionMap' && referenceId && (
              <button
                style={{ margin: '12px', padding: '8px 12px' }}
                onClick={() => setView('visualComposer')}
              >
                [Dev] Open Visual Composer
              </button>
            )}
          </>
        )}
        {view === 'visualComposer' && (
          <div style={{ padding: 40 }}>
            <h2>Visual Composer (placeholder)</h2>
            <button onClick={() => setView('regionMap')}>Back</button>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

