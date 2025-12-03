/**
 * API client for call/response lanes endpoints.
 */

import { CallResponseByStemResponse } from "../types/callResponseLanes";

// Base URL for API (assumes same origin for now, can be configured via env)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Fetch call/response patterns organized by stem lanes.
 * 
 * @param referenceId - ID of the reference bundle
 * @returns Promise with call/response lanes data
 * @throws Error if the request fails or reference is not found
 */
export async function fetchCallResponseByStem(
  referenceId: string
): Promise<CallResponseByStemResponse> {
  const url = `${API_BASE_URL}/api/reference/${referenceId}/call-response-by-stem`;
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch call/response lanes' }));
    throw new Error(error.detail || `Failed to fetch call/response lanes with status ${response.status}`);
  }

  return response.json();
}

