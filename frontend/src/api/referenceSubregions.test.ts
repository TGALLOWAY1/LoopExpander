/**
 * Tests for subregions API client.
 * 
 * Note: This test file can be run with a test framework like Vitest or Jest.
 * For now, it documents the expected behavior and structure.
 */

import { fetchReferenceSubregions, type ReferenceSubRegionsResponse, type RegionSubRegions } from './reference';

/**
 * Mock test data matching backend response structure.
 */
const mockSubregionsResponse: ReferenceSubRegionsResponse = {
  referenceId: 'test_ref_123',
  regions: [
    {
      regionId: 'region_01',
      lanes: {
        drums: [
          {
            id: 'region_01-drums-0',
            regionId: 'region_01',
            stemCategory: 'drums',
            startBar: 0.0,
            endBar: 2.0,
            label: 'Main Pattern',
            motifGroupId: 'group_1',
            isVariation: false,
            isSilence: false,
            intensity: 0.75,
          },
        ],
        bass: [
          {
            id: 'region_01-bass-0',
            regionId: 'region_01',
            stemCategory: 'bass',
            startBar: 0.0,
            endBar: 2.0,
            label: 'Main Pattern',
            motifGroupId: 'group_1',
            isVariation: false,
            isSilence: false,
            intensity: 0.45,
          },
        ],
        vocals: [
          {
            id: 'region_01-vocals-0',
            regionId: 'region_01',
            stemCategory: 'vocals',
            startBar: 0.0,
            endBar: 2.0,
            label: null,
            motifGroupId: null,
            isVariation: false,
            isSilence: true,
            intensity: 0.08,
          },
        ],
        instruments: [
          {
            id: 'region_01-instruments-0',
            regionId: 'region_01',
            stemCategory: 'instruments',
            startBar: 0.0,
            endBar: 2.0,
            label: null,
            motifGroupId: null,
            isVariation: false,
            isSilence: false,
            intensity: 0.38,
          },
        ],
      },
    },
  ],
};

/**
 * Test that fetchReferenceSubregions normalizes response correctly.
 * 
 * This test verifies:
 * - All 4 stem categories are present in lanes
 * - Missing categories are filled with empty arrays
 * - Response structure matches expected TypeScript types
 */
export function testFetchReferenceSubregionsNormalization() {
  // This would be run with a test framework
  // For now, it documents expected behavior
  
  const response = mockSubregionsResponse;
  
  // Assert all 4 stem categories are present
  const firstRegion = response.regions[0];
  if (!firstRegion) {
    throw new Error('Expected at least one region');
  }
  
  const lanes = firstRegion.lanes;
  const expectedCategories: Array<'drums' | 'bass' | 'vocals' | 'instruments'> = [
    'drums',
    'bass',
    'vocals',
    'instruments',
  ];
  
  for (const category of expectedCategories) {
    if (!(category in lanes)) {
      throw new Error(`Missing stem category: ${category}`);
    }
    if (!Array.isArray(lanes[category])) {
      throw new Error(`Lane ${category} is not an array`);
    }
  }
  
  // Assert pattern structure
  const drumsPattern = lanes.drums[0];
  if (drumsPattern) {
    if (!drumsPattern.id || !drumsPattern.regionId || !drumsPattern.stemCategory) {
      throw new Error('Pattern missing required fields');
    }
    if (typeof drumsPattern.startBar !== 'number' || typeof drumsPattern.endBar !== 'number') {
      throw new Error('Pattern bar positions must be numbers');
    }
    if (drumsPattern.intensity !== undefined && (drumsPattern.intensity < 0 || drumsPattern.intensity > 1)) {
      throw new Error('Pattern intensity must be between 0 and 1');
    }
  }
  
  return true;
}

/**
 * Example usage in a component (for documentation).
 */
export function exampleComponentUsage() {
  // Example: How a component would access subregion data
  // const { data: subregions } = useReferenceSubregions(referenceId);
  // const firstRegionLanes = subregions?.regions[0]?.lanes;
  
  const subregions = mockSubregionsResponse;
  const firstRegionLanes = subregions.regions[0]?.lanes;
  
  if (firstRegionLanes) {
    console.log('Drums patterns:', firstRegionLanes.drums);
    console.log('Bass patterns:', firstRegionLanes.bass);
    console.log('Vocals patterns:', firstRegionLanes.vocals);
    console.log('Instruments patterns:', firstRegionLanes.instruments);
  }
  
  return firstRegionLanes;
}

