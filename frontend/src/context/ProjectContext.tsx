/**
 * Project context for managing reference track and regions state.
 */
import { createContext, useContext, useState, ReactNode } from 'react';
import { 
  Region, 
  MotifInstance, 
  MotifGroup, 
  CallResponsePair, 
  Fill,
  RegionSubRegions
} from '../api/reference';

/**
 * Project state type.
 */
export type ProjectState = {
  referenceId: string | null;
  regions: Region[];
  motifs: MotifInstance[];
  motifGroups: MotifGroup[];
  callResponsePairs: CallResponsePair[];
  fills: Fill[];
  subregionsByRegionId: Record<string, RegionSubRegions>;
  setReferenceId: (id: string | null) => void;
  setRegions: (regions: Region[]) => void;
  setMotifs: (motifs: MotifInstance[], groups: MotifGroup[]) => void;
  setCallResponsePairs: (pairs: CallResponsePair[]) => void;
  setFills: (fills: Fill[]) => void;
  setSubregions: (subregions: RegionSubRegions[]) => void;
};

/**
 * Default project state.
 */
const defaultState: ProjectState = {
  referenceId: null,
  regions: [],
  motifs: [],
  motifGroups: [],
  callResponsePairs: [],
  fills: [],
  subregionsByRegionId: {},
  setReferenceId: () => {
    console.warn('setReferenceId called outside ProjectProvider');
  },
  setRegions: () => {
    console.warn('setRegions called outside ProjectProvider');
  },
  setMotifs: () => {
    console.warn('setMotifs called outside ProjectProvider');
  },
  setCallResponsePairs: () => {
    console.warn('setCallResponsePairs called outside ProjectProvider');
  },
  setFills: () => {
    console.warn('setFills called outside ProjectProvider');
  },
  setSubregions: () => {
    console.warn('setSubregions called outside ProjectProvider');
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
  const [motifs, setMotifsState] = useState<MotifInstance[]>([]);
  const [motifGroups, setMotifGroupsState] = useState<MotifGroup[]>([]);
  const [callResponsePairs, setCallResponsePairs] = useState<CallResponsePair[]>([]);
  const [fills, setFills] = useState<Fill[]>([]);
  const [subregionsByRegionId, setSubregionsByRegionId] = useState<Record<string, RegionSubRegions>>({});

  const setMotifs = (newMotifs: MotifInstance[], newGroups: MotifGroup[]) => {
    setMotifsState(newMotifs);
    setMotifGroupsState(newGroups);
  };

  const setSubregions = (subregions: RegionSubRegions[]) => {
    const byRegionId: Record<string, RegionSubRegions> = {};
    subregions.forEach((subregion) => {
      byRegionId[subregion.regionId] = subregion;
    });
    setSubregionsByRegionId(byRegionId);
  };

  const value: ProjectState = {
    referenceId,
    regions,
    motifs,
    motifGroups,
    callResponsePairs,
    fills,
    subregionsByRegionId,
    setReferenceId,
    setRegions,
    setMotifs,
    setCallResponsePairs,
    setFills,
    setSubregions,
  };

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
}

