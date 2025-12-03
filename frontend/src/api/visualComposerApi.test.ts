/**
 * Tests for Visual Composer API client.
 * 
 * Note: This test file documents expected behavior and structure.
 * For a full test suite, consider adding Vitest or Jest to the project.
 */

import type { VcAnnotations } from './visualComposerApi';

/**
 * Mock test data matching backend response structure.
 */
const mockVcAnnotations: VcAnnotations = {
  projectId: 'test_project_123',
  regions: [
    {
      regionId: 'region_01',
      regionName: 'Intro',
      notes: 'Region notes here',
      lanes: [
        {
          id: 'lane_01',
          name: 'Growl Bass',
          color: '#FF4A4A',
          collapsed: false,
          order: 0,
        },
        {
          id: 'lane_02',
          name: 'Drums',
          color: '#4A4AFF',
          collapsed: false,
          order: 1,
        },
      ],
      blocks: [
        {
          id: 'block_01',
          laneId: 'lane_01',
          startBar: 0.0,
          endBar: 4.0,
          color: '#FF7A7A',
          type: 'call',
          notes: 'formant sweep / gritty tail',
        },
        {
          id: 'block_02',
          laneId: 'lane_01',
          startBar: 4.0,
          endBar: 8.0,
          color: '#FF7A7A',
          type: 'response',
          notes: 'variation with more grit',
        },
        {
          id: 'block_03',
          laneId: 'lane_02',
          startBar: 0.0,
          endBar: 8.0,
          color: '#6A6AFF',
          type: 'custom',
          notes: null,
        },
      ],
    },
    {
      regionId: 'region_02',
      regionName: 'Verse',
      notes: null,
      lanes: [
        {
          id: 'lane_03',
          name: 'Vocals',
          color: '#4AFF4A',
          collapsed: true,
          order: 0,
        },
      ],
      blocks: [
        {
          id: 'block_04',
          laneId: 'lane_03',
          startBar: 8.0,
          endBar: 16.0,
          color: null,
          type: 'variation',
          notes: 'vocal variation',
        },
      ],
    },
  ],
};

/**
 * Test that VcAnnotations structure matches expected format.
 * 
 * This test verifies:
 * - projectId is present
 * - regions is an array
 * - Each region has required fields
 * - Lanes and blocks are properly structured
 */
export function testVcAnnotationsStructure() {
  const annotations = mockVcAnnotations;
  
  // Assert top-level structure
  if (!annotations.projectId) {
    throw new Error('Missing projectId');
  }
  if (!Array.isArray(annotations.regions)) {
    throw new Error('regions must be an array');
  }
  
  // Assert region structure
  const firstRegion = annotations.regions[0];
  if (!firstRegion) {
    throw new Error('Expected at least one region');
  }
  
  if (!firstRegion.regionId) {
    throw new Error('Region missing regionId');
  }
  if (!Array.isArray(firstRegion.lanes)) {
    throw new Error('Region lanes must be an array');
  }
  if (!Array.isArray(firstRegion.blocks)) {
    throw new Error('Region blocks must be an array');
  }
  
  // Assert lane structure
  const firstLane = firstRegion.lanes[0];
  if (firstLane) {
    if (!firstLane.id || !firstLane.name) {
      throw new Error('Lane missing required fields (id, name)');
    }
    if (typeof firstLane.order !== 'number') {
      throw new Error('Lane order must be a number');
    }
    if (typeof firstLane.collapsed !== 'boolean') {
      throw new Error('Lane collapsed must be a boolean');
    }
  }
  
  // Assert block structure
  const firstBlock = firstRegion.blocks[0];
  if (firstBlock) {
    if (!firstBlock.id || !firstBlock.laneId) {
      throw new Error('Block missing required fields (id, laneId)');
    }
    if (typeof firstBlock.startBar !== 'number' || typeof firstBlock.endBar !== 'number') {
      throw new Error('Block bar positions must be numbers');
    }
    if (firstBlock.endBar <= firstBlock.startBar) {
      throw new Error('Block endBar must be greater than startBar');
    }
    const validTypes = ['call', 'response', 'variation', 'fill', 'custom'];
    if (!validTypes.includes(firstBlock.type)) {
      throw new Error(`Block type must be one of: ${validTypes.join(', ')}`);
    }
  }
  
  return true;
}

/**
 * Test that empty annotations structure is valid.
 */
export function testEmptyVcAnnotations() {
  const emptyAnnotations: VcAnnotations = {
    projectId: 'test_project',
    regions: [],
  };
  
  if (!emptyAnnotations.projectId) {
    throw new Error('Empty annotations must have projectId');
  }
  if (!Array.isArray(emptyAnnotations.regions)) {
    throw new Error('Empty annotations regions must be an array');
  }
  if (emptyAnnotations.regions.length !== 0) {
    throw new Error('Empty annotations should have no regions');
  }
  
  return true;
}

/**
 * Example usage in a component (for documentation).
 */
export function exampleComponentUsage() {
  // Example: How a component would access Visual Composer annotations
  // import { getVisualComposerAnnotations, saveVisualComposerAnnotations } from './api/visualComposerApi';
  // 
  // const annotations = await getVisualComposerAnnotations(projectId);
  // const firstRegion = annotations.regions[0];
  // if (firstRegion) {
  //   console.log('Lanes:', firstRegion.lanes);
  //   console.log('Blocks:', firstRegion.blocks);
  // }
  
  const annotations = mockVcAnnotations;
  const firstRegion = annotations.regions[0];
  
  if (firstRegion) {
    console.log('Region ID:', firstRegion.regionId);
    console.log('Region Name:', firstRegion.regionName);
    console.log('Lanes:', firstRegion.lanes);
    console.log('Blocks:', firstRegion.blocks);
  }
  
  return firstRegion;
}

