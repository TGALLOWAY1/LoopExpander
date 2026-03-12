/**
 * API client for single full-mix reference track endpoints.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Upload response for a single full-mix reference.
 */
export interface ReferenceMixUploadResponse {
  referenceId: string;
  bpm: number;
  detectedBpm: number;
  duration: number;
  totalBars: number;
  beatGrid: number[];
  key: string | null;
}

/**
 * Analysis response for a single full-mix reference.
 */
export interface ReferenceMixAnalysisResponse {
  referenceId: string;
  regionCount: number;
  roles: string[];
  totalBars: number;
  transitionCount: number;
  status: string;
}

/**
 * Activity segment for a role.
 */
export interface ActivitySegment {
  startBar: number;
  endBar: number;
  active: boolean;
  confidence: number;
}

/**
 * Role activity timeline.
 */
export interface RoleActivityTimeline {
  role: string;
  segments: ActivitySegment[];
}

/**
 * Role activity response.
 */
export interface RoleActivityResponse {
  referenceId: string;
  timelines: RoleActivityTimeline[];
}

/**
 * Transition marker from energy analysis.
 */
export interface TransitionMarker {
  bar: number;
  timeSeconds: number;
  energyDelta: number;
  type: 'lift' | 'drop' | 'breakdown';
}

/**
 * Multi-dimensional energy curves (per bar, normalized 0-1).
 */
export interface MultiEnergyCurves {
  lufs: number[];
  spectralCentroid: number[];
  bassEnergy: number[];
  transientDensity: number[];
}

/**
 * Energy curve response.
 */
export interface EnergyCurveResponse {
  referenceId: string;
  barEnergies: number[];
  sectionDensities: Array<{
    regionId: string;
    density: number;
    meanEnergy: number;
  }>;
  transitionMarkers: TransitionMarker[];
  multiCurves?: MultiEnergyCurves;
}

/**
 * Mix region with bar positions and labels.
 */
/**
 * Tonal balance for a single region (normalized to sum=1).
 */
export interface RegionTonalBalance {
  regionId: string;
  low: number;
  lowMid: number;
  mid: number;
  highMid: number;
  high: number;
}

/**
 * Tonal balance response.
 */
export interface TonalBalanceResponse {
  referenceId: string;
  tonalBalance: RegionTonalBalance[];
}

export interface MixRegion {
  id: string;
  name: string;
  type: string;
  start: number;
  end: number;
  duration: number;
  startBar: number;
  endBar: number;
  label: string;
  provisionalLabel: string;
}

/**
 * Mix regions response.
 */
export interface MixRegionsResponse {
  referenceId: string;
  regions: MixRegion[];
  count: number;
}

/**
 * Upload a single full-mix reference track.
 */
export async function uploadReferenceMix(
  file: File,
  bpmOverride?: number,
): Promise<ReferenceMixUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  let url = `${API_BASE_URL}/api/reference/upload-mix`;
  if (bpmOverride !== undefined) {
    url += `?bpm_override=${bpmOverride}`;
  }

  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || `Upload failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Run full analysis on a reference mix.
 */
export async function analyzeReferenceMix(
  referenceId: string,
): Promise<ReferenceMixAnalysisResponse> {
  const response = await fetch(`${API_BASE_URL}/api/reference/${referenceId}/analyze-mix`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Analysis failed' }));
    throw new Error(error.detail || `Analysis failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch role activity timelines.
 */
export async function getRoleActivity(
  referenceId: string,
): Promise<RoleActivityResponse> {
  const response = await fetch(`${API_BASE_URL}/api/reference/${referenceId}/role-activity`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch role activity' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch energy curve and transition markers.
 */
export async function getEnergyCurve(
  referenceId: string,
): Promise<EnergyCurveResponse> {
  const response = await fetch(`${API_BASE_URL}/api/reference/${referenceId}/energy`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch energy curve' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch detected regions with labels for a reference mix.
 */
export async function getMixRegions(
  referenceId: string,
): Promise<MixRegionsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/reference/${referenceId}/mix-regions`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch regions' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch tonal balance per region.
 */
export async function getTonalBalance(
  referenceId: string,
): Promise<TonalBalanceResponse> {
  const response = await fetch(`${API_BASE_URL}/api/reference/${referenceId}/tonal-balance`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch tonal balance' }));
    throw new Error(error.detail || `Failed with status ${response.status}`);
  }

  return response.json();
}
