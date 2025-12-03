/**
 * Types for motif sensitivity configuration.
 * 
 * Sensitivity values control how motifs are grouped during clustering:
 * - Lower values (closer to 0.0) = stricter grouping (more groups, tighter clustering)
 * - Higher values (closer to 1.0) = looser grouping (fewer groups, more tolerant clustering)
 * 
 * All values must be in the range [0.0, 1.0].
 */

/**
 * Complete motif sensitivity configuration for all stem types.
 * Each value represents the sensitivity for that specific stem category.
 */
export type MotifSensitivityConfig = {
  drums: number;
  bass: number;
  vocals: number;
  instruments: number;
};

/**
 * Partial update for motif sensitivity configuration.
 * Only provided keys will be updated; omitted keys remain unchanged.
 * All values must be in the range [0.0, 1.0].
 */
export type MotifSensitivityUpdate = Partial<MotifSensitivityConfig>;

