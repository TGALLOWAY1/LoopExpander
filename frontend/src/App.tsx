/**
 * Main App component.
 */
import React from 'react';
import { useProject } from './context/ProjectContext';

function App(): JSX.Element {
  const { referenceId, regions } = useProject();

  return (
    <div className="app">
      <header>
        <h1>Song Structure Replicator</h1>
      </header>
      <main>
        <div>
          <p>Reference ID: {referenceId || 'None'}</p>
          <p>Regions: {regions.length}</p>
        </div>
      </main>
    </div>
  );
}

export default App;

