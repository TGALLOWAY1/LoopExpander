/**
 * Main App component.
 *
 * NOTE: This app is wrapped in React.StrictMode (see main.tsx), which double-invokes
 * effects in development. This may cause duplicate effect runs during debugging.
 */
import { useState } from 'react';
import { useProject } from './context/ProjectContext';
import IngestPage from './pages/IngestPage';
import RegionMapPage from './pages/RegionMapPage';
import VisualComposerPage from './pages/VisualComposerPage';
import StructureCanvasPage from './pages/StructureCanvasPage';
import { VISUAL_COMPOSER_ENABLED } from './config';
import './App.css';

type AppView = 'ingest' | 'regionMap' | 'visualComposer' | 'structureCanvas';

function App(): JSX.Element {
  const { referenceId, regions } = useProject();
  const [view, setView] = useState<AppView>('structureCanvas'); // Default to Structure Canvas in dev

  return (
    <div className="app">
      <header>
        <h1>LoopExpander</h1>
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
          <button
            className={view === 'structureCanvas' ? 'nav-button active' : 'nav-button'}
            onClick={() => setView('structureCanvas')}
          >
            Structure Canvas
          </button>
          {VISUAL_COMPOSER_ENABLED && (
            <button
              className="dev-button"
              style={{ margin: '12px', padding: '8px 12px' }}
              onClick={() => setView('visualComposer')}
            >
              [Dev] Visual Composer
            </button>
          )}
        </nav>
      </header>
      <main>
        {view === 'ingest' && <IngestPage onAnalysisComplete={() => setView('structureCanvas')} />}
        {view === 'regionMap' && (
          <>
            <RegionMapPage />
          </>
        )}
        {view === 'structureCanvas' && (
          <StructureCanvasPage
            onBack={() => setView('regionMap')}
            demoMode={!referenceId || regions.length === 0}
          />
        )}
        {view === 'visualComposer' && (
          <VisualComposerPage
            onBack={() => setView('regionMap')}
            demoMode={!referenceId || regions.length === 0}
          />
        )}
      </main>
    </div>
  );
}

export default App;
