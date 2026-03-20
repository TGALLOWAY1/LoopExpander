import React, { useEffect, useRef, useState } from 'react';
import '../../pages/VisualComposerPage.css'; // Shared styles

interface ComposerWaveformProps {
    audioUrl?: string;
    pixelsPerBar: number;
    totalBars: number;
    startBar?: number;
    bpm?: number;
    height?: number;
}

export const ComposerWaveform: React.FC<ComposerWaveformProps> = ({
    audioUrl,
    pixelsPerBar,
    totalBars,
    startBar = 0,
    bpm = 130, // Default to 130 as per user context
    height = 64
}) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [audioBuffer, setAudioBuffer] = useState<AudioBuffer | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    // Fetch and decode audio
    useEffect(() => {
        if (!audioUrl) return;

        let cancelled = false;

        const loadAudio = async () => {
            try {
                setLoading(true);
                setError(null);
                const response = await fetch(audioUrl);
                if (!response.ok) throw new Error('Failed to fetch audio');
                const arrayBuffer = await response.arrayBuffer();

                const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
                const decodedBuffer = await audioContext.decodeAudioData(arrayBuffer);

                if (!cancelled) {
                    setAudioBuffer(decodedBuffer);
                }
            } catch (err) {
                if (!cancelled) {
                    console.error('Waveform load error:', err);
                    setError('Failed to load waveform');
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        };

        loadAudio();

        return () => {
            cancelled = true;
        };
    }, [audioUrl]);

    // Draw waveform
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || !audioBuffer) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const width = totalBars * pixelsPerBar;

        // Handle Retina displays
        const dpr = window.devicePixelRatio || 1;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        ctx.scale(dpr, dpr);

        ctx.clearRect(0, 0, width, height);

        const data = audioBuffer.getChannelData(0); // Use first channel
        const sampleRate = audioBuffer.sampleRate;

        // Calculate window into audio buffer
        // 60 / BPM = seconds per beat
        // seconds per bar = (60/BPM) * 4
        const secondsPerBar = (60 / bpm) * 4;
        const startSample = Math.floor(startBar * secondsPerBar * sampleRate);
        const totalSampleDuration = Math.floor(totalBars * secondsPerBar * sampleRate);
        const endSample = Math.min(data.length, startSample + totalSampleDuration);

        // If startSample is beyond data, nothing to draw
        if (startSample >= data.length) return;

        const samplesToDraw = endSample - startSample;
        const step = Math.ceil(samplesToDraw / width);
        const amp = height / 2;

        ctx.fillStyle = '#4a90e2'; // Waveform color
        ctx.beginPath();

        // Draw PCM data
        for (let i = 0; i < width; i++) {
            let min = 1.0;
            let max = -1.0;

            // Calculate min/max for this pixel slice within the window
            const sliceStart = startSample + (i * step);

            for (let j = 0; j < step; j++) {
                const idx = sliceStart + j;
                if (idx >= data.length) break;

                const datum = data[idx];
                if (datum < min) min = datum;
                if (datum > max) max = datum;
            }

            // If silent/no data
            if (min > max) {
                min = 0; max = 0;
            }

            ctx.fillRect(i, (1 + min) * amp, 1, Math.max(1, (max - min) * amp));
        }
    }, [audioBuffer, pixelsPerBar, totalBars, startBar, bpm, height]);

    return (
        <div className="composer-waveform" style={{ width: totalBars * pixelsPerBar, height }}>
            {loading && <div className="waveform-loading">Loading Audio...</div>}
            {error && <div className="waveform-error">{error}</div>}
            {!audioUrl && <div className="waveform-placeholder">No Audio Source</div>}
            <canvas ref={canvasRef} />
        </div>
    );
};
