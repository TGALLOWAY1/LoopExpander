/**
 * Region Map page for displaying detected regions in a timeline.
 */
import React from 'react';
import { useProject } from '../context/ProjectContext';
import { RegionBlock } from '../components/RegionBlock';
import './RegionMapPage.css';

function RegionMapPage(): JSX.Element {
  const { referenceId, regions } = useProject();

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
          </div>
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

