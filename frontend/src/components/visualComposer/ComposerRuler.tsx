import React from 'react';
import '../../pages/VisualComposerPage.css'; // Shared styles (or specific ones)

interface ComposerRulerProps {
    barCount: number;
    pixelsPerBar: number;
    subdivisions?: number; // e.g., 4 for beats, 8 for eighths
}

export const ComposerRuler: React.FC<ComposerRulerProps> = ({
    barCount,
    pixelsPerBar,
    subdivisions = 4
}) => {
    const rulerWidth = barCount * pixelsPerBar;

    return (
        <div
            className="composer-ruler"
            style={{ width: `${rulerWidth}px` }}
        >
            {Array.from({ length: barCount }, (_, i) => {
                const barIndex = i + 1; // 1-based labels
                const leftPos = i * pixelsPerBar;

                return (
                    <React.Fragment key={barIndex}>
                        {/* Main Bar Label */}
                        <div
                            className="ruler-bar-label"
                            style={{ left: `${leftPos}px`, width: `${pixelsPerBar}px` }}
                        >
                            {barIndex}
                        </div>

                        {/* Subdivisions (Ticks) */}
                        {Array.from({ length: subdivisions - 1 }, (_, subIndex) => {
                            // Calculate offset for subdivision ticks (1/4, 2/4, 3/4...)
                            const tickOffset = ((subIndex + 1) / subdivisions) * pixelsPerBar;
                            const isBeat = (subIndex + 1) % 2 !== 0; // Simple logic for major/minor ticks if needed

                            return (
                                <div
                                    key={`sub-${barIndex}-${subIndex}`}
                                    className="ruler-tick"
                                    style={{
                                        left: `${leftPos + tickOffset}px`,
                                        height: isBeat ? '6px' : '4px', // Beats taller than eighths? Logic can be refined
                                        opacity: 0.5
                                    }}
                                />
                            );
                        })}
                    </React.Fragment>
                );
            })}
        </div>
    );
};
