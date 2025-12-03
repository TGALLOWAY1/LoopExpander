/**
 * Region Map page for displaying detected regions in a timeline.
 */
import { useEffect, useState, useCallback } from 'react';
import { useProject } from '../context/ProjectContext';
import { FiveLayerRegionMap } from '../components/FiveLayerRegionMap';
import { CallResponsePanel } from '../components/CallResponsePanel';
import { MotifGroupsPanel } from '../components/MotifGroupsPanel';
// MotifSensitivityPanel removed from right sidebar - will be moved to lane headers
// import { MotifSensitivityPanel } from '../components/MotifSensitivityPanel';
import { getMotifs, getCallResponse, getFills, fetchReferenceSubregions, reanalyzeMotifs } from '../api/reference';
import { useCallResponseLanes } from '../hooks/useCallResponseLanes';
import type { CallResponsePair } from '../api/reference';
import './RegionMapPage.css';

function RegionMapPage(): JSX.Element {
  const { 
    referenceId, 
    regions,
    motifs,
    motifGroups,
    callResponsePairs,
    fills,
    subregionsByRegionId,
    setMotifs, 
    setCallResponsePairs, 
    setFills,
    setSubregions
  } = useProject();
  
  const [loadingMotifs, setLoadingMotifs] = useState(false);
  const [loadingCallResponse, setLoadingCallResponse] = useState(false);
  const [loadingFills, setLoadingFills] = useState(false);
  const [loadingSubregions, setLoadingSubregions] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [motifSensitivity, setMotifSensitivity] = useState(0.5);
  const [isMotifPaused, setIsMotifPaused] = useState(false);
  const [highlightedGroupId, setHighlightedGroupId] = useState<string | null>(null);
  const [highlightedPairId, setHighlightedPairId] = useState<string | null>(null);

  // Load call/response lanes for the 5-layer view
  const { data: callResponseLanesData, loading: loadingLanes, error: lanesError } = useCallResponseLanes(referenceId);

  // Load motifs with current sensitivity
  const loadMotifs = useCallback(async (sensitivity: number) => {
    if (!referenceId) return;
    
    // Log before calling getMotifs
    console.log('[RegionMapPage] loadMotifs called:', { referenceId, sensitivity });
    
    setLoadingMotifs(true);
    setError(null);
    try {
      const response = await getMotifs(referenceId, sensitivity);
      setMotifs(response.instances, response.groups);
    } catch (err) {
      console.error('Error loading motifs:', err);
      setError(err instanceof Error ? err.message : 'Failed to load motifs');
    } finally {
      setLoadingMotifs(false);
    }
  }, [referenceId, setMotifs]);

  // Load motifs, call-response, and fills when referenceId and regions are available
  useEffect(() => {
    if (!referenceId || regions.length === 0) {
      return;
    }

    console.log('[RegionMapPage] useEffect triggered:', { referenceId, regionsLength: regions.length, motifSensitivity, isMotifPaused });

    // Skip motif fetch if paused
    if (isMotifPaused) {
      console.log('[Motifs] Skipping motif fetch because analysis is paused');
    } else {
      // Fetch motifs with current sensitivity
      loadMotifs(motifSensitivity);
    }

    // Fetch call-response pairs
    const loadCallResponse = async () => {
      setLoadingCallResponse(true);
      try {
        const response = await getCallResponse(referenceId);
        setCallResponsePairs(response.pairs);
      } catch (err) {
        console.error('Error loading call-response pairs:', err);
        // Don't set error for call-response, just log it
      } finally {
        setLoadingCallResponse(false);
      }
    };

    // Fetch fills
    const loadFills = async () => {
      setLoadingFills(true);
      try {
        const response = await getFills(referenceId);
        setFills(response.fills);
      } catch (err) {
        console.error('Error loading fills:', err);
        // Don't set error for fills, just log it
      } finally {
        setLoadingFills(false);
      }
    };

    loadCallResponse();
    loadFills();

    // Fetch subregions
    const loadSubregions = async () => {
      setLoadingSubregions(true);
      try {
        const response = await fetchReferenceSubregions(referenceId);
        setSubregions(response.regions);
        
        // Log subregions to verify shape
        console.log('Subregions', response.regions);
        if (response.regions.length > 0) {
          const firstRegionLanes = response.regions[0]?.lanes;
          console.log('First region lanes:', firstRegionLanes);
        }
      } catch (err) {
        console.error('Error loading subregions:', err);
        // Don't set error for subregions, just log it
      } finally {
        setLoadingSubregions(false);
      }
    };

    loadSubregions();
    // Only depend on input values, not on the results or setter functions
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [referenceId, regions.length, motifSensitivity, isMotifPaused]);

  // Handle sensitivity change (debounced on slider release)
  const handleSensitivityChange = useCallback((newSensitivity: number) => {
    setMotifSensitivity(newSensitivity);
    // Load motifs will be triggered by the useEffect dependency on motifSensitivity
  }, []);

  // Handle call-response pair click
  const handlePairClick = useCallback((pair: CallResponsePair) => {
    setHighlightedPairId(pair.id);
    // Find the motif group IDs for the call and response
    const fromMotif = motifs.find(m => m.id === pair.fromMotifId);
    const toMotif = motifs.find(m => m.id === pair.toMotifId);
    if (fromMotif?.groupId || toMotif?.groupId) {
      // Highlight the group of the response (or call if no response group)
      setHighlightedGroupId(toMotif?.groupId || fromMotif?.groupId || null);
    }
  }, [motifs]);

  // Handle reanalysis after sensitivity change
  const handleReanalyze = useCallback(async () => {
    if (!referenceId) return;

    try {
      setError(null);
      
      // Re-analyze motifs with new sensitivity (uses stored config)
      await reanalyzeMotifs(referenceId);
      
      // Refetch all dependent data
      // Refetch motifs without sensitivity param to use stored config
      setLoadingMotifs(true);
      try {
        const motifsResponse = await getMotifs(referenceId); // No sensitivity param = uses stored config
        setMotifs(motifsResponse.instances, motifsResponse.groups);
      } catch (err) {
        console.error('Error loading motifs after reanalysis:', err);
      } finally {
        setLoadingMotifs(false);
      }
      
      // Refetch call-response pairs
      setLoadingCallResponse(true);
      try {
        const callResponseResponse = await getCallResponse(referenceId);
        setCallResponsePairs(callResponseResponse.pairs);
      } catch (err) {
        console.error('Error loading call-response after reanalysis:', err);
      } finally {
        setLoadingCallResponse(false);
      }
      
      // Refetch fills
      setLoadingFills(true);
      try {
        const fillsResponse = await getFills(referenceId);
        setFills(fillsResponse.fills);
      } catch (err) {
        console.error('Error loading fills after reanalysis:', err);
      } finally {
        setLoadingFills(false);
      }
      
      // Refetch subregions
      setLoadingSubregions(true);
      try {
        const subregionsResponse = await fetchReferenceSubregions(referenceId);
        setSubregions(subregionsResponse.regions);
      } catch (err) {
        console.error('Error loading subregions after reanalysis:', err);
      } finally {
        setLoadingSubregions(false);
      }
    } catch (err) {
      console.error('Error during reanalysis:', err);
      setError(err instanceof Error ? err.message : 'Failed to reanalyze');
    }
  }, [referenceId, setMotifs, setCallResponsePairs, setFills, setSubregions]);

  // Compute total duration from the last region's end time
  const totalDuration = regions.length > 0
    ? Math.max(...regions.map((r) => r.end))
    : 0;

  if (!referenceId) {
    return (
      <div className="region-map-page">
        <div className="empty-state">
          <h2>No Reference Analyzed</h2>
          <p>No reference analyzed yet. Go to the Ingest page first.</p>
        </div>
      </div>
    );
  }

  if (regions.length === 0) {
    return (
      <div className="region-map-page">
        <div className="empty-state">
          <h2>No Regions Detected</h2>
          <p>Regions have not been detected yet. Run analysis on the Ingest page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="region-map-page">
      <div className="region-map-container">
        <div className="region-map-header">
          <h2>Region Map</h2>
          <div className="region-map-info">
            <span>Reference ID: {referenceId}</span>
            <span>Regions: {regions.length}</span>
            <span>Duration: {totalDuration.toFixed(1)}s</span>
            {(loadingMotifs || loadingCallResponse || loadingFills || loadingSubregions) && (
              <span className="loading-indicator">
                Loading analysis data...
                {loadingSubregions && ' (patterns...)'}
              </span>
            )}
          </div>
          {error && (
            <div className="error-message" style={{ color: 'red', marginTop: '10px' }}>
              {error}
            </div>
          )}
          
          {/* Motif Sensitivity Control */}
          <div className="motif-sensitivity-control">
            <label htmlFor="motif-sensitivity-slider">
              Motif Sensitivity: {motifSensitivity.toFixed(2)}
            </label>
            <input
              id="motif-sensitivity-slider"
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={motifSensitivity}
              onChange={(e) => handleSensitivityChange(parseFloat(e.target.value))}
              className="sensitivity-slider"
            />
            <div className="sensitivity-labels">
              <span>Strict (0.0)</span>
              <span>Loose (1.0)</span>
            </div>
            <div className="motif-pause-control" style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                type="button"
                className="motif-pause-button"
                onClick={() => setIsMotifPaused(prev => !prev)}
              >
                {isMotifPaused ? 'Resume Motif Analysis' : 'Pause Motif Analysis'}
              </button>
              {isMotifPaused && (
                <span className="motif-paused-indicator" style={{ fontSize: '0.75rem', opacity: 0.7 }}>
                  Motif analysis paused
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="region-map-main-content">
          <div className="region-map-timeline-section">
            {/* 5-Layer Region Map View */}
            {loadingLanes ? (
              <div className="loading-state">
                <p>Loading call/response lanes...</p>
              </div>
            ) : lanesError ? (
              <div className="error-state">
                <p>Error loading lanes: {lanesError.message}</p>
              </div>
            ) : (
              <FiveLayerRegionMap
                regions={regions}
                lanes={callResponseLanesData?.lanes ?? []}
                bpm={130} // TODO: Get BPM from context or reference bundle
                totalDuration={totalDuration}
                referenceId={referenceId}
              />
            )}

            <div className="region-list">
              <h3>Region Details</h3>
              <div className="region-list-items">
                {regions.map((region) => (
                  <div key={region.id} className="region-list-item">
                    <div className="region-list-name">{region.name}</div>
                    <div className="region-list-type">{region.type}</div>
                    <div className="region-list-time">
                      {region.start.toFixed(1)}s - {region.end.toFixed(1)}s
                      {' '}
                      ({region.duration.toFixed(1)}s)
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Panel Section */}
          <div className="call-response-section">
            <MotifGroupsPanel
              groups={motifGroups}
              instances={motifs}
              regions={regions}
              onGroupClick={setHighlightedGroupId}
              highlightedGroupId={highlightedGroupId}
              loading={loadingMotifs}
            />
            <CallResponsePanel
              pairs={callResponsePairs}
              regions={regions}
              onPairClick={handlePairClick}
              highlightedPairId={highlightedPairId}
              loading={loadingCallResponse}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default RegionMapPage;

