/**
 * TonalBalanceDisplay renders a horizontal 5-band bar chart showing
 * the tonal balance for a selected section/region.
 */
import React from 'react';
import { RegionTonalBalance } from '../../api/referenceMix';

interface TonalBalanceDisplayProps {
  tonalBalance: RegionTonalBalance | null;
  sectionLabel?: string;
}

const BANDS = [
  { key: 'low' as const, label: 'Low', range: '20-250Hz', color: '#F44336' },
  { key: 'lowMid' as const, label: 'Low-Mid', range: '250-500Hz', color: '#FF9800' },
  { key: 'mid' as const, label: 'Mid', range: '0.5-2kHz', color: '#4CAF50' },
  { key: 'highMid' as const, label: 'Hi-Mid', range: '2-6kHz', color: '#2196F3' },
  { key: 'high' as const, label: 'High', range: '6-20kHz', color: '#9C27B0' },
];

export const TonalBalanceDisplay: React.FC<TonalBalanceDisplayProps> = ({
  tonalBalance,
  sectionLabel,
}) => {
  if (!tonalBalance) {
    return null;
  }

  const maxVal = Math.max(
    tonalBalance.low,
    tonalBalance.lowMid,
    tonalBalance.mid,
    tonalBalance.highMid,
    tonalBalance.high,
    0.01,
  );

  return (
    <div className="sc-tonal-balance">
      {sectionLabel && (
        <div className="sc-tonal-balance-header">
          Tonal Balance: {sectionLabel}
        </div>
      )}
      <div className="sc-tonal-bands">
        {BANDS.map((band) => {
          const value = tonalBalance[band.key];
          const widthPct = (value / maxVal) * 100;
          return (
            <div key={band.key} className="sc-tonal-band-row">
              <div className="sc-tonal-band-label">
                <span className="sc-tonal-band-name">{band.label}</span>
                <span className="sc-tonal-band-range">{band.range}</span>
              </div>
              <div className="sc-tonal-band-bar-container">
                <div
                  className="sc-tonal-band-bar"
                  style={{
                    width: `${widthPct}%`,
                    background: band.color,
                  }}
                />
                <span className="sc-tonal-band-value">
                  {(value * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
