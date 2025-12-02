/**
 * CallResponsePanel component for displaying call-response conversations.
 */
import { useMemo } from 'react';
import { CallResponsePair, Region } from '../api/reference';
import './CallResponsePanel.css';

export type CallResponsePanelProps = {
  pairs: CallResponsePair[];
  regions: Region[];
  onPairClick?: (pair: CallResponsePair) => void;
  highlightedPairId?: string | null;
};

/**
 * Convert seconds to approximate bars (assuming 4/4 time, 130 BPM default).
 */
function secondsToBars(seconds: number, bpm: number = 130): number {
  const beatsPerSecond = bpm / 60;
  const barsPerSecond = beatsPerSecond / 4;
  return seconds * barsPerSecond;
}

export function CallResponsePanel({ 
  pairs, 
  regions, 
  onPairClick,
  highlightedPairId 
}: CallResponsePanelProps): JSX.Element {
  // Group pairs by region
  const pairsByRegion = useMemo(() => {
    const grouped = new Map<string, CallResponsePair[]>();
    
    pairs.forEach((pair) => {
      const regionId = pair.regionId || 'unassigned';
      if (!grouped.has(regionId)) {
        grouped.set(regionId, []);
      }
      grouped.get(regionId)!.push(pair);
    });
    
    return grouped;
  }, [pairs]);

  // Create region lookup map
  const regionMap = useMemo(() => {
    const map = new Map<string, Region>();
    regions.forEach((region) => {
      map.set(region.id, region);
    });
    return map;
  }, [regions]);

  if (pairs.length === 0) {
    return (
      <div className="call-response-panel">
        <h3>Call & Response</h3>
        <div className="call-response-empty">
          <p>No call-response pairs detected.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="call-response-panel">
      <h3>Call & Response</h3>
      <div className="call-response-content">
        {Array.from(pairsByRegion.entries()).map(([regionId, regionPairs]) => {
          const region = regionMap.get(regionId);
          const regionName = region ? region.name : (regionId === 'unassigned' ? 'Unassigned' : `Region ${regionId}`);
          
          return (
            <div key={regionId} className="call-response-region-group">
              <div className="call-response-region-header">{regionName}</div>
              <div className="call-response-pairs">
                {regionPairs.map((pair) => {
                  const fromBars = secondsToBars(pair.fromTime).toFixed(1);
                  const toBars = secondsToBars(pair.toTime).toFixed(1);
                  const isHighlighted = highlightedPairId === pair.id;
                  
                  return (
                    <div
                      key={pair.id}
                      className={`call-response-pair ${isHighlighted ? 'highlighted' : ''}`}
                      onClick={() => onPairClick?.(pair)}
                    >
                      <div className="call-response-pair-content">
                        <div className="call-response-pair-arrow">
                          <span className="call-stem">{pair.fromStemRole}</span>
                          <span className="arrow">→</span>
                          <span className="response-stem">{pair.toStemRole}</span>
                        </div>
                        <div className="call-response-pair-time">
                          Bar {fromBars} → Bar {toBars}
                        </div>
                        <div className="call-response-pair-meta">
                          <span className={`call-response-type ${pair.isInterStem ? 'inter-stem' : 'intra-stem'}`}>
                            {pair.isInterStem ? 'Inter-stem' : 'Intra-stem'}
                          </span>
                          <span className="call-response-confidence">
                            {(pair.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

