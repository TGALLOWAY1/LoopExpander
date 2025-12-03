/**
 * Types for call/response lanes visualization.
 * 
 * These types represent call/response patterns organized by stem lanes
 * for timeline-based visualization, excluding full-mix motifs.
 */

/**
 * Valid stem categories for call/response lanes (excludes full_mix).
 */
export type StemCategory = "drums" | "bass" | "instruments" | "vocals";

/**
 * A single call or response event in a stem lane.
 */
export interface StemCallResponseEvent {
  id: string;
  regionId: string;
  stem: StemCategory;
  startBar: number;
  endBar: number;
  role: "call" | "response";
  groupId: string; // Groups calls + responses that belong together
  label?: string | null;
  intensity?: number | null; // Optional density/energy
}

/**
 * A lane containing call/response events for a specific stem.
 */
export interface StemCallResponseLane {
  stem: StemCategory;
  events: StemCallResponseEvent[];
}

/**
 * Response containing call/response data organized by stem lanes.
 */
export interface CallResponseByStemResponse {
  referenceId: string;
  regions: string[]; // Region ids in timeline order
  lanes: StemCallResponseLane[];
}

