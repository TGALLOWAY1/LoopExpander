# Ingest View - Nano Banana Prompt

## Overview
A clean, modern, DAW-inspired interface for uploading and analyzing reference track stems. The layout emphasizes clarity and workflow efficiency, with visual feedback at each stage of the process.

## Layout Structure

### Main Container
- **Width**: Full viewport width, max 1400px centered
- **Background**: Dark theme (#1a1a1a) with subtle texture, or light theme (#f5f5f5) with minimal shadows
- **Padding**: 2rem on all sides
- **Grid Layout**: Two-column layout (60% left, 40% right) on desktop, stacked on mobile

### Left Panel: File Upload Zone (60% width)

#### Drag-and-Drop Area
- **Container**: Large rectangular area spanning most of left panel
- **Background**: Subtle gradient or solid color (#2a2a2a for dark, #ffffff for light)
- **Border**: 2px dashed border, color changes on hover (from #666 to accent color)
- **Border Radius**: 8px
- **Padding**: 3rem
- **Min Height**: 400px

#### Five Labeled Drop Zones
Arrange in a 2x3 grid (or vertical stack):

1. **Drums Zone**
   - **Color Theme**: Orange (#ff9800 or #ff6b35)
   - **Icon**: Drum kit silhouette or waveform icon
   - **Label**: "Drums" in bold, 14px
   - **State Indicators**: 
     - Empty: Light border, dashed
     - Filled: Solid border, checkmark icon, file name displayed
   - **Size**: Equal width, ~150px height each

2. **Bass Zone**
   - **Color Theme**: Blue (#2196f3 or #0066cc)
   - **Icon**: Bass guitar or low-frequency waveform
   - **Label**: "Bass" in bold
   - Same state indicators as Drums

3. **Vocals Zone**
   - **Color Theme**: Purple (#9c27b0 or #7b1fa2)
   - **Icon**: Microphone or vocal waveform
   - **Label**: "Vocals" in bold
   - Same state indicators

4. **Instruments Zone**
   - **Color Theme**: Green (#4caf50 or #2e7d32)
   - **Icon**: Musical note or instrument waveform
   - **Label**: "Instruments" in bold
   - Same state indicators

5. **Full Mix Zone**
   - **Color Theme**: White/Gray (#ffffff or #e0e0e0) with subtle border
   - **Icon**: Full waveform or mixer icon
   - **Label**: "Full Mix" in bold, slightly larger
   - **Position**: Centered at bottom, slightly wider than others
   - Same state indicators

#### File Input Alternative
- Traditional file input buttons below each zone
- Styled to match the color theme of each zone
- Text: "Choose File" or "Browse..."

### Right Panel: Metadata & Status (40% width)

#### Header Section
- **Title**: "Reference Track Info" in 18px, bold
- **Divider**: Thin line below title

#### BPM Display
- **Label**: "BPM" in 12px, muted color
- **Value**: Large number, 32px, bold, accent color
- **Icon**: Metronome or tempo icon to the left
- **Background**: Subtle card background with border radius

#### Key Display
- **Label**: "Key" in 12px, muted color
- **Value**: "C Major" or "Not Detected" in 16px
- **Icon**: Musical key signature icon
- Same card styling as BPM

#### File Metadata Section
- **Title**: "File Details" in 14px
- **List**: 
  - Sample Rate: 44100 Hz
  - Duration: 3:45
  - Format: WAV
  - Channels: Stereo
- **Styling**: Compact list, muted text, 12px font

#### Analysis Status
- **Container**: Card with rounded corners
- **States**:
  - **Idle**: "Ready to analyze" message
  - **Uploading**: Progress bar (0-100%), "Uploading files..." text
  - **Analyzing**: Animated spinner, "Analyzing structure..." text
  - **Complete**: Checkmark icon, "Analysis complete" message, region count
- **Colors**: 
  - Idle: Gray
  - Processing: Blue accent
  - Complete: Green

#### Action Button
- **"Analyze Reference"** button
- **Position**: Bottom of right panel
- **Size**: Full width, 48px height
- **Color**: Primary accent (blue or green)
- **State**: 
  - Enabled: Full opacity, hover effect
  - Disabled: 50% opacity, grayed out
- **Icon**: Play or analyze icon on left side

## Visual States

### Empty State
- All drop zones show dashed borders
- Placeholder text: "Drop audio file here" or "Click to browse"
- Icons are outlined/grayed
- Right panel shows "No files selected" message
- Analyze button is disabled

### Files Selected State
- Drop zones show solid borders in their theme colors
- File names displayed below each zone (truncated if long)
- Waveform thumbnails or file size shown
- Checkmark icons appear
- Right panel updates with detected BPM (if available)
- Analyze button becomes enabled

### Analyzing State
- Drop zones become disabled (reduced opacity)
- Loading spinner in center of upload area
- Progress indicator in right panel
- Status text: "Uploading..." → "Analyzing structure..."
- Analyze button shows "Processing..." and is disabled

### Complete State
- All zones show success checkmarks
- Right panel displays:
  - Final BPM value
  - Key (if detected)
  - "Analysis complete - X regions detected"
- Success message with link/button to view Region Map
- Analyze button changes to "View Results" or similar

## Color Palette

### Dark Theme
- Background: #1a1a1a
- Cards: #2a2a2a
- Text Primary: #ffffff
- Text Secondary: #b0b0b0
- Accent: #007bff
- Success: #4caf50
- Error: #f44336

### Light Theme
- Background: #f5f5f5
- Cards: #ffffff
- Text Primary: #333333
- Text Secondary: #666666
- Accent: #007bff
- Success: #4caf50
- Error: #f44336

## Typography
- **Headings**: Sans-serif, bold, 16-24px
- **Body**: Sans-serif, regular, 14px
- **Labels**: Sans-serif, medium, 12px
- **Values**: Sans-serif, bold, 16-32px

## Interactive Elements
- **Hover Effects**: Subtle scale (1.02x) or brightness increase
- **Drop Hover**: Border becomes solid, background slightly lighter
- **Button Hover**: Slight elevation, color darkens
- **Transitions**: All state changes use 0.2s ease transitions

## Accessibility
- High contrast ratios (WCAG AA minimum)
- Clear focus indicators on interactive elements
- Keyboard navigation support
- Screen reader labels on all icons and buttons

