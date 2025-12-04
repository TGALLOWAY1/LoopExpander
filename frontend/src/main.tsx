/**
 * Main entry point for the React application.
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { ProjectProvider } from './context/ProjectContext';
import App from './App';
import './index.css';

// NOTE: React.StrictMode double-invokes effects in development to help detect side effects.
// This may cause duplicate effect runs during debugging. We're currently debugging a sync loop
// in VisualComposerPage between localRegionAnnotations and vcAnnotations.
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ProjectProvider>
      <App />
    </ProjectProvider>
  </React.StrictMode>
);

