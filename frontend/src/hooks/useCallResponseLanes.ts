/**
 * Hook for loading call/response lanes data for a reference.
 * 
 * Provides state management for loading call/response patterns organized
 * by stem lanes for timeline visualization.
 */

import React from "react";
import { fetchCallResponseByStem } from "../api/callResponseLanes";
import { CallResponseByStemResponse } from "../types/callResponseLanes";

/**
 * Hook to load call/response lanes data for a reference.
 * 
 * @param referenceId - ID of the reference bundle
 * @returns Object with:
 *   - data: Call/response lanes data (null while loading or if error)
 *   - loading: Whether data is being loaded
 *   - error: Any error that occurred during loading
 */
export function useCallResponseLanes(referenceId: string | null) {
  const [data, setData] = React.useState<CallResponseByStemResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    if (!referenceId) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    
    fetchCallResponseByStem(referenceId)
      .then((res) => {
        if (!cancelled) {
          setData(res);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error(String(err)));
          setData(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [referenceId]);

  // Debug logging: Log lane data when it changes
  React.useEffect(() => {
    if (data) {
      console.log("[DEBUG] Call/Response lanes:", data);
      console.log("[DEBUG] Number of lanes:", data.lanes.length);
      data.lanes.forEach((lane) => {
        console.log(`[DEBUG] Lane ${lane.stem}: ${lane.events.length} events`);
        if (lane.events.length > 0) {
          console.log(`[DEBUG] Sample event from ${lane.stem}:`, lane.events[0]);
        }
      });
    }
  }, [data]);

  return { data, loading, error };
}

