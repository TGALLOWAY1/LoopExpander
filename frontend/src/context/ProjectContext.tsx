/**
 * Project context for managing reference track and regions state.
 */
import React, { createContext, useContext, useState, ReactNode } from 'react';
import { Region } from '../api/reference';

/**
 * Project state type.
 */
export type ProjectState = {
  referenceId: string | null;
  regions: Region[];
  setReferenceId: (id: string | null) => void;
  setRegions: (regions: Region[]) => void;
};

/**
 * Default project state.
 */
const defaultState: ProjectState = {
  referenceId: null,
  regions: [],
  setReferenceId: () => {
    console.warn('setReferenceId called outside ProjectProvider');
  },
  setRegions: () => {
    console.warn('setRegions called outside ProjectProvider');
  },
};

/**
 * Project context.
 */
const ProjectContext = createContext<ProjectState>(defaultState);

/**
 * Hook to access project context.
 * 
 * @returns ProjectState
 */
export function useProject(): ProjectState {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return context;
}

/**
 * ProjectProvider component props.
 */
interface ProjectProviderProps {
  children: ReactNode;
}

/**
 * ProjectProvider component that wraps the app and provides project state.
 */
export function ProjectProvider({ children }: ProjectProviderProps): JSX.Element {
  const [referenceId, setReferenceId] = useState<string | null>(null);
  const [regions, setRegions] = useState<Region[]>([]);

  const value: ProjectState = {
    referenceId,
    regions,
    setReferenceId,
    setRegions,
  };

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
}

