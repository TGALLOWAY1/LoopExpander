/**
 * Main App component.
 */
import { useState } from 'react';
import { useProject } from './context/ProjectContext';
import IngestPage from './pages/IngestPage';
import RegionMapPage from './pages/RegionMapPage';
import VisualComposerPage from './pages/VisualComposerPage';
import './App.css';

type Page = 'ingest' | 'regions' | 'visualComposer';

// Feature flag for Visual Composer
const VISUAL_COMPOSER_ENABLED = import.meta.env.VITE_VISUAL_COMPOSER_ENABLED === 'true';

function App(): JSX.Element {
  const { referenceId, regions } = useProject();
  const [currentPage, setCurrentPage] = useState<Page>('ingest');

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
            className={currentPage === 'ingest' ? 'nav-button active' : 'nav-button'}
            onClick={() => setCurrentPage('ingest')}
          >
            Ingest
          </button>
          <button
            className={currentPage === 'regions' ? 'nav-button active' : 'nav-button'}
            onClick={() => setCurrentPage('regions')}
            disabled={!referenceId || regions.length === 0}
          >
            Region Map
          </button>
        </nav>
      </header>
      <main>
        {currentPage === 'ingest' && <IngestPage onAnalysisComplete={() => setCurrentPage('regions')} />}
        {currentPage === 'regions' && (
          <RegionMapPage 
            onVisualComposerClick={
              VISUAL_COMPOSER_ENABLED && referenceId && regions.length > 0
                ? () => setCurrentPage('visualComposer')
                : undefined
            }
          />
        )}
        {currentPage === 'visualComposer' && (
          <VisualComposerPage onBack={() => setCurrentPage('regions')} />
        )}
      </main>
    </div>
  );
}

export default App;

