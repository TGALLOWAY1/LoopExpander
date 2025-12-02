/**
 * Main App component.
 */
import React from 'react';
import { useProject } from './context/ProjectContext';
import IngestPage from './pages/IngestPage';

function App(): JSX.Element {
  const { referenceId, regions } = useProject();

  return (
    <div className="app">
      <header>
        <h1>Song Structure Replicator</h1>
        <div className="header-info">
          {referenceId && <span>Reference ID: {referenceId}</span>}
          {regions.length > 0 && <span>Regions: {regions.length}</span>}
        </div>
      </header>
      <main>
        <IngestPage />
      </main>
    </div>
  );
}

export default App;

