/**
 * API client for variation suggestions and arrangement guidance (Phase 6).
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * A variation suggestion for the arrangement.
 */
export interface VariationSuggestion {
  id: string;
  type: 'mute_layer' | 'dropout' | 'density_shift' | 'alternate' | 'gap';
  targetBlockId: string;
  sectionId: string;
  description: string;
  applied: boolean;
  dismissed: boolean;
  parameters: Record<string, unknown>;
}

/**
 * Response from the suggestions endpoint.
 */
export interface SuggestionsResponse {
  projectId: string;
  suggestions: VariationSuggestion[];
  total: number;
  applied: number;
  dismissed: number;
}

/**
 * A guidance message for the arrangement.
 */
export interface GuidanceMessage {
  id: string;
  type: 'density_warning' | 'transition_cue' | 'missing_role' | 'interaction' | 'purpose';
  sectionId: string;
  severity: 'info' | 'suggestion' | 'warning';
  message: string;
  actionHint: string | null;
}

/**
 * Response from the guidance endpoint.
 */
export interface GuidanceResponse {
  projectId: string;
  messages: GuidanceMessage[];
  total: number;
  warnings: number;
  suggestions: number;
  info: number;
}

/**
 * Get variation suggestions for the current arrangement.
 */
export async function getSuggestions(
  projectId: string,
): Promise<SuggestionsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/suggestions`,
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch suggestions' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Force regeneration of variation suggestions.
 */
export async function regenerateSuggestions(
  projectId: string,
): Promise<SuggestionsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/suggestions/regenerate`,
    { method: 'POST' },
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to regenerate suggestions' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Apply a variation suggestion to the arrangement.
 */
export async function applySuggestion(
  projectId: string,
  suggestionId: string,
): Promise<{ suggestion: VariationSuggestion; arrangement: import('./arrangement').Arrangement }> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/suggestions/${suggestionId}/apply`,
    { method: 'POST' },
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to apply suggestion' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Dismiss a variation suggestion.
 */
export async function dismissSuggestion(
  projectId: string,
  suggestionId: string,
): Promise<{ suggestion: VariationSuggestion }> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/suggestions/${suggestionId}/dismiss`,
    { method: 'POST' },
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to dismiss suggestion' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Get arrangement guidance messages.
 */
export async function getGuidance(
  projectId: string,
): Promise<GuidanceResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/guidance`,
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch guidance' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Force regeneration of guidance messages.
 */
export async function regenerateGuidance(
  projectId: string,
): Promise<GuidanceResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/project/${projectId}/guidance/regenerate`,
    { method: 'POST' },
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to regenerate guidance' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }

  return response.json();
}

/** Severity badge colors. */
export const SEVERITY_COLORS: Record<string, string> = {
  info: '#2196F3',
  suggestion: '#FF9800',
  warning: '#F44336',
};

/** Suggestion type labels. */
export const SUGGESTION_TYPE_LABELS: Record<string, string> = {
  mute_layer: 'Mute Layer',
  dropout: 'Dropout',
  density_shift: 'Density Shift',
  alternate: 'Alternate Stem',
  gap: 'Transition Gap',
};

/** Guidance type labels. */
export const GUIDANCE_TYPE_LABELS: Record<string, string> = {
  density_warning: 'Density',
  transition_cue: 'Transition',
  missing_role: 'Missing Role',
  interaction: 'Interaction',
  purpose: 'Section Purpose',
};
