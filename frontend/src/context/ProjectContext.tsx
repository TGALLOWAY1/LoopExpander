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
  RegionSubRegions,
  ReferenceAnnotations
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
  annotations: ReferenceAnnotations | null;
  setReferenceId: (id: string | null) => void;
  setRegions: (regions: Region[]) => void;
  setMotifs: (motifs: MotifInstance[], groups: MotifGroup[]) => void;
  setCallResponsePairs: (pairs: CallResponsePair[]) => void;
  setFills: (fills: Fill[]) => void;
  setSubregions: (subregions: RegionSubRegions[]) => void;
  setAnnotations: (annotations: ReferenceAnnotations | null) => void;
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
  annotations: null,
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
  setAnnotations: () => {
    console.warn('setAnnotations called outside ProjectProvider');
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
  const [annotations, setAnnotations] = useState<ReferenceAnnotations | null>(null);

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
    annotations,
    setReferenceId,
    setRegions,
    setMotifs,
    setCallResponsePairs,
    setFills,
    setSubregions,
    setAnnotations,
  };

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
}

