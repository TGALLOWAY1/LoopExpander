# Region Map View - Nano Banana Prompt

## Overview
A horizontal timeline visualization displaying detected song regions as color-coded blocks. The interface provides a clear, read-only view of song structure with visual energy indicators. Designed for quick comprehension of song architecture.

## Layout Structure

### Main Container
- **Width**: Full viewport width, max 1600px centered
- **Background**: Dark theme (#1a1a1a) or light theme (#f5f5f5)
- **Padding**: 2rem vertical, 3rem horizontal
- **Layout**: Single column, vertically stacked sections

### Header Section
- **Title**: "Region Map" in 24px, bold, left-aligned
- **Metadata Bar**: Horizontal row showing:
  - Reference ID: Monospace font, muted color
  - Region Count: "X regions"
  - Total Duration: "3:45" or "225.0s"
- **Spacing**: 1rem between elements
- **Background**: Subtle card background or transparent

## Timeline Visualization

### Time Scale (Top Section)
- **Position**: Above the region blocks
- **Height**: 40px
- **Background**: Slightly darker/lighter than main background
- **Markers**: Vertical tick marks every 10 seconds
- **Labels**: Time values (0:00, 0:10, 0:20, etc.) below ticks
- **Font**: Monospace, 11px, muted color
- **Border**: Thin bottom border separating from regions

### Energy Curve (Background Layer)
- **Position**: Behind region blocks, subtle
- **Type**: Smooth line graph or filled area chart
- **Data**: RMS energy or spectral centroid over time
- **Color**: Very muted (20% opacity) gradient
  - Low energy: Blue/purple tones
  - High energy: Orange/red tones
- **Height**: Matches region block height
- **Style**: Subtle, non-intrusive, provides context only

### Region Blocks Container
- **Position**: Below time scale
- **Height**: 100-120px
- **Background**: Very subtle (#252525 for dark, #fafafa for light)
- **Layout**: Horizontal flex container, no gaps between blocks
- **Border**: Subtle container border (1px, #333 or #ddd)
- **Border Radius**: 4px on container
- **Padding**: 4px internal padding

### Individual Region Blocks

#### Block Structure
- **Width**: Proportional to region duration (calculated as percentage of total track length)
- **Height**: 100% of container (fills available vertical space)
- **Border**: 2px solid border, color matches region type
- **Border Radius**: 0px (blocks connect seamlessly) OR 2px if gaps desired
- **Padding**: 8px internal padding
- **Layout**: Flex column, centered content

#### Color Coding by Region Type

1. **Intro (low_energy)**
   - **Background**: Soft blue (#e3f2fd) or muted blue-gray (#4a5568)
   - **Border**: Light blue (#2196f3) or soft blue (#5a9fd4)
   - **Opacity**: Slightly transparent (90%)
   - **Mood**: Calm, gentle

2. **Build**
   - **Background**: Warm orange (#fff3e0) or muted orange (#f4a261)
   - **Border**: Orange (#ff9800) or amber (#f59e0b)
   - **Opacity**: Full or 95%
   - **Mood**: Rising energy, anticipation

3. **High Energy / Drop**
   - **Background**: Bright purple (#f3e5f5) or vibrant purple (#a855f7)
   - **Border**: Deep purple (#9c27b0) or electric purple (#9333ea)
   - **Opacity**: Full (100%)
   - **Mood**: Intense, peak energy
   - **Optional**: Subtle glow effect or gradient

4. **Breakdown / Bridge**
   - **Background**: Muted green (#e8f5e9) or gray-green (#6b7280)
   - **Border**: Green (#4caf50) or teal (#14b8a6)
   - **Opacity**: 85-90%
   - **Mood**: Transitional, calmer

5. **Outro (low_energy)**
   - **Background**: Soft blue-gray (#e3f2fd) or muted gray (#9ca3af)
   - **Border**: Light blue (#2196f3) or gray-blue (#64748b)
   - **Opacity**: 80-85%
   - **Mood**: Fading, conclusion

#### Block Content (Labels Inside)
- **Region Name**: 
  - Font: Bold, 14-16px
  - Color: Dark text (#333) on light backgrounds, light text (#fff) on dark backgrounds
  - Position: Top-center or center
  - Examples: "Intro", "Build", "Drop", "Breakdown", "Outro"

- **Time Range**:
  - Font: Regular, 11-12px, monospace
  - Color: Muted (60% opacity of text color)
  - Position: Below name or bottom of block
  - Format: "0:00 - 0:15" or "0.0s - 15.0s"
  - Small enough to not clutter, readable on hover

- **Duration** (Optional):
  - Font: Regular, 10px
  - Color: Very muted (40% opacity)
  - Position: Bottom-right corner
  - Format: "(15s)" or "15s"

#### Hover State
- **Effect**: Slight elevation (box-shadow) or brightness increase
- **Border**: Slightly thicker or brighter
- **Tooltip**: Full region details (name, type, start, end, duration)
- **Cursor**: Pointer (even though read-only, indicates interactivity potential)

## Region List Section (Below Timeline)

### Container
- **Position**: Below timeline, separated by divider
- **Background**: Card background (slightly different from main)
- **Padding**: 2rem
- **Border Top**: 1px solid divider line

### Title
- **Text**: "Region Details" or "All Regions"
- **Font**: 18px, bold
- **Spacing**: 1rem margin bottom

### Grid Layout
- **Type**: Responsive grid (3-4 columns on desktop, 1-2 on tablet, 1 on mobile)
- **Gap**: 1rem between cards
- **Card Size**: Minimum 250px width, auto height

### Region Detail Cards
- **Background**: Card background (#2a2a2a dark, #ffffff light)
- **Border**: Left border accent (4px, matches region type color)
- **Border Radius**: 4px
- **Padding**: 1rem
- **Shadow**: Subtle shadow for depth

#### Card Content
- **Region Name**: 
  - Font: 16px, bold
  - Color: Primary text color
  - Position: Top

- **Region Type**:
  - Font: 12px, regular
  - Color: Muted text
  - Text Transform: Capitalize ("Low Energy", "High Energy")
  - Position: Below name

- **Time Range**:
  - Font: 11px, monospace
  - Color: Very muted
  - Format: "0:00 - 0:15 (15.0s)"
  - Position: Bottom

## Empty States

### No Reference
- **Message**: "No reference analyzed yet. Go to the Ingest page first."
- **Icon**: Large upload or music icon (muted)
- **Action**: Button or link to Ingest page
- **Styling**: Centered, muted colors

### No Regions
- **Message**: "Regions have not been detected yet. Run analysis on the Ingest page."
- **Icon**: Timeline or chart icon (muted)
- **Action**: Button or link to Ingest page
- **Styling**: Centered, muted colors

## Visual Style

### Dark Theme
- Background: #1a1a1a
- Cards: #2a2a2a
- Text: #ffffff
- Muted Text: #b0b0b0
- Borders: #444444

### Light Theme
- Background: #f5f5f5
- Cards: #ffffff
- Text: #333333
- Muted Text: #666666
- Borders: #dddddd

## Typography
- **Headings**: Sans-serif, bold, 18-24px
- **Body**: Sans-serif, regular, 14px
- **Labels**: Sans-serif, medium, 12px
- **Time Values**: Monospace, 11-12px

## Interactive Elements (Read-only in M1)
- **Hover**: Subtle visual feedback (brightness, shadow)
- **No Click Actions**: Cursor remains default (no pointer)
- **No Drag Handles**: No visible editing controls
- **Tooltips**: Optional hover tooltips with full region info

## Accessibility
- High contrast between text and backgrounds
- Color coding supplemented with text labels
- Screen reader friendly structure
- Keyboard navigation support (for future editing)

## Responsive Behavior
- **Desktop**: Full timeline visible, 3-4 column grid
- **Tablet**: Timeline scrollable horizontally, 2 column grid
- **Mobile**: Timeline scrollable, 1 column grid, stacked layout

