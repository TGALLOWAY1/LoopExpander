/**
 * Region Map page for displaying detected regions in a timeline.
 */
import React, { useEffect, useState } from 'react';
import { useProject } from '../context/ProjectContext';
import { RegionBlock } from '../components/RegionBlock';
import { getMotifs, getCallResponse, getFills } from '../api/reference';
import './RegionMapPage.css';

function RegionMapPage(): JSX.Element {
  const { 
    referenceId, 
    regions, 
    setMotifs, 
    setCallResponsePairs, 
    setFills 
  } = useProject();
  
  const [loadingMotifs, setLoadingMotifs] = useState(false);
  const [loadingCallResponse, setLoadingCallResponse] = useState(false);
  const [loadingFills, setLoadingFills] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load motifs, call-response, and fills when referenceId and regions are available
  useEffect(() => {
    if (!referenceId || regions.length === 0) {
      return;
    }

    // Fetch motifs with default sensitivity
    const loadMotifs = async () => {
      setLoadingMotifs(true);
      setError(null);
      try {
        const response = await getMotifs(referenceId, 0.5);
        setMotifs(response.instances, response.groups);
      } catch (err) {
        console.error('Error loading motifs:', err);
        setError(err instanceof Error ? err.message : 'Failed to load motifs');
      } finally {
        setLoadingMotifs(false);
      }
    };

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

    loadMotifs();
    loadCallResponse();
    loadFills();
  }, [referenceId, regions.length, setMotifs, setCallResponsePairs, setFills]);

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
            {(loadingMotifs || loadingCallResponse || loadingFills) && (
              <span className="loading-indicator">Loading analysis data...</span>
            )}
          </div>
          {error && (
            <div className="error-message" style={{ color: 'red', marginTop: '10px' }}>
              {error}
            </div>
          )}
        </div>

        <div className="region-timeline">
          <div className="timeline-header">
            <div className="timeline-scale">
              {Array.from({ length: Math.ceil(totalDuration / 10) + 1 }, (_, i) => i * 10).map((time) => (
                <div key={time} className="timeline-marker">
                  <span className="timeline-label">{time}s</span>
                </div>
              ))}
            </div>
          </div>

          <div className="region-blocks-container">
            {regions.map((region) => (
              <RegionBlock
                key={region.id}
                region={region}
                totalDuration={totalDuration}
              />
            ))}
          </div>
        </div>

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
    </div>
  );
}

export default RegionMapPage;

