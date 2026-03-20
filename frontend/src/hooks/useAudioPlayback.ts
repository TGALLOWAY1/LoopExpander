import { useState, useEffect, useRef, useCallback } from 'react';

interface UseAudioPlaybackProps {
    initialVolume?: number;
}

export const useAudioPlayback = ({ initialVolume = 0.8 }: UseAudioPlaybackProps = {}) => {
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [audioSource, setAudioSource] = useState<string | null>(null);

    const audioRef = useRef<HTMLAudioElement | null>(null);

    useEffect(() => {
        audioRef.current = new Audio();
        audioRef.current.volume = initialVolume;

        // Listeners
        const onTimeUpdate = () => setCurrentTime(audioRef.current?.currentTime || 0);
        const onEnded = () => setIsPlaying(false);
        const onLoadedMetadata = () => setDuration(audioRef.current?.duration || 0);

        audioRef.current.addEventListener('timeupdate', onTimeUpdate);
        audioRef.current.addEventListener('ended', onEnded);
        audioRef.current.addEventListener('loadedmetadata', onLoadedMetadata);

        return () => {
            audioRef.current?.pause();
            audioRef.current?.removeEventListener('timeupdate', onTimeUpdate);
            audioRef.current?.removeEventListener('ended', onEnded);
            audioRef.current?.removeEventListener('loadedmetadata', onLoadedMetadata);
        };
    }, [initialVolume]);

    const loadAudio = useCallback((url: string) => {
        if (audioRef.current) {
            audioRef.current.src = url;
            audioRef.current.load();
            setAudioSource(url);
        }
    }, []);

    const togglePlay = useCallback(() => {
        if (!audioRef.current) return;

        if (isPlaying) {
            audioRef.current.pause();
            setIsPlaying(false);
        } else {
            audioRef.current.play().catch(console.error);
            setIsPlaying(true);
        }
    }, [isPlaying]);

    return {
        isPlaying,
        currentTime,
        duration,
        togglePlay,
        loadAudio,
        activeSource: audioSource
    };
};
