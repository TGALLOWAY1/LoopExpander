/**
 * Project context for managing reference track and regions state.
 */
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { 
  Region, 
  MotifInstance, 
  MotifGroup, 
  CallResponsePair, 
  Fill,
  RegionSubRegions,
  ReferenceAnnotations,
  getAnnotations
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
 * Project context.
 * Use null as default to detect when used outside a provider.
 */
const ProjectContext = createContext<ProjectState | null>(null);

/**
 * Hook to access project context.
 * 
 * @returns ProjectState
 * @throws Error if used outside a ProjectProvider
 */
export function useProject(): ProjectState {
  const context = useContext(ProjectContext);
  if (context === null) {
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
 * 
 * Made robust to handle edge cases where props might be undefined.
 */
export function ProjectProvider(
  props: ProjectProviderProps = { children: null }
): JSX.Element {
  // Temporary debug logging to verify props are received correctly
  if (import.meta.env.MODE !== 'production') {
    console.log('[ProjectProvider] props received:', props);
  }
  
  // Defensive destructuring with logging for debugging
  const { children } = props;
  
  // Log warning if mounted without children (helps catch misuse)
  if (!children && import.meta.env.MODE !== 'production') {
    console.warn(
      '[ProjectProvider] Mounted without children. Check usage - ProjectProvider should wrap your app components.'
    );
  }
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

  // Load annotations when referenceId changes
  useEffect(() => {
    if (!referenceId) {
      setAnnotations(null);
      return;
    }

    let cancelled = false;

    const loadAnnotations = async () => {
      try {
        const data = await getAnnotations(referenceId);
        if (!cancelled) {
          setAnnotations(data);
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Error loading annotations:', err);
          // On error, set to empty structure to avoid breaking UI
          setAnnotations({
            referenceId,
            regions: [],
          });
        }
      }
    };

    loadAnnotations();

    return () => {
      cancelled = true;
    };
  }, [referenceId]);

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

