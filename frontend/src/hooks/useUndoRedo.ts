import { useState, useCallback } from 'react';

interface UseUndoRedo<T> {
    state: T;
    setState: (newState: T | ((prev: T) => T)) => void;
    undo: () => void;
    redo: () => void;
    canUndo: boolean;
    canRedo: boolean;
    history: T[];
    pointer: number;
}

export function useUndoRedo<T>(initialState: T, maxHistory: number = 50): UseUndoRedo<T> {
    const [history, setHistory] = useState<T[]>([initialState]);
    const [pointer, setPointer] = useState(0);

    const state = history[pointer];

    const setState = useCallback(
        (newStateOrFn: T | ((prev: T) => T)) => {
            setHistory((prevHistory) => {
                const currentPointer = pointer; // Capture current pointer
                const currentState = prevHistory[currentPointer];

                const newState =
                    typeof newStateOrFn === 'function'
                        ? (newStateOrFn as (prev: T) => T)(currentState)
                        : newStateOrFn;

                // If new state is identical, don't push
                if (JSON.stringify(newState) === JSON.stringify(currentState)) {
                    return prevHistory;
                }

                const newHistory = [
                    ...prevHistory.slice(0, currentPointer + 1),
                    newState,
                ];

                // Limit history size
                if (newHistory.length > maxHistory) {
                    // If we exceed max, slice from the end minus max
                    // But simpler: just slice(1) if we are appending
                    // However, slicing from start shifts indices.
                    // Let's rely on slice(newHistory.length - maxHistory) if needed
                    // efficient:
                    return newHistory.slice(-maxHistory);
                }

                return newHistory;
            });

            // Update pointer to end (use functional update to ensure sync if needed, 
            // but here we just need to know the new length)
            setPointer((prevPointer) => {
                // We can't easily know the new length here inside setState's closure without redundant calculation
                // A safer way: Calculate new history first, then set both.
                return pointer + 1; // This is risky if history update logic changes logic
            });
        },
        [history, pointer, maxHistory]
    );

    // Refactored setState to be safer with state updates
    const safeSetState = useCallback((newStateOrFn: T | ((prev: T) => T)) => {
        setHistory(prev => {
            const currentState = prev[pointer];
            const newState = typeof newStateOrFn === 'function'
                ? (newStateOrFn as (prev: T) => T)(currentState)
                : newStateOrFn;

            if (JSON.stringify(newState) === JSON.stringify(currentState)) return prev;

            const nextHistory = [...prev.slice(0, pointer + 1), newState];
            const truncated = nextHistory.slice(-maxHistory);

            setPointer(truncated.length - 1);
            return truncated;
        });
    }, [pointer, maxHistory]); // pointer is dependency

    const undo = useCallback(() => {
        setPointer((prev) => Math.max(0, prev - 1));
    }, []);

    const redo = useCallback(() => {
        setPointer((prev) => Math.min(history.length - 1, prev + 1));
    }, [history.length]);

    return {
        state: history[pointer],
        setState: safeSetState,
        undo,
        redo,
        canUndo: pointer > 0,
        canRedo: pointer < history.length - 1,
        history,
        pointer,
    };
}
