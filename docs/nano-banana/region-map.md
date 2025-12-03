**Nano Banana 3 Prompt — Region Map View (Strict "Screen Only" UI Mockup)**

Render a **flat 2D UI screenshot** of the Region Map view.  
Do **NOT** include computers, desks, hands, controllers, or physical instruments.

### Layout:

- **Main Container**: Two-column grid layout
  - **Left Column (70% width)**: Timeline and region visualization
  - **Right Column (30% width)**: Call-Response Conversation Panel

### Top Header Section:

- **Title**: "Region Map" (large, bold, top-left)
- **Info Bar**: Small text showing:
  - Reference ID
  - Region count
  - Total duration
- **Motif Sensitivity Control** (top-right area):
  - Label: "Motif Sensitivity: 0.50"
  - Horizontal slider (range 0.0 to 1.0)
  - Labels below: "Strict (0.0)" on left, "Loose (1.0)" on right
  - Slider thumb positioned at middle (0.5)
  - Light gray background box with subtle border

### Timeline Section (Left Column):

- **Timeline Scale**: Horizontal bar with time markers (0s, 10s, 20s, etc.)
  - Small tick marks and labels
  - Thin border line beneath

- **Fill Markers Row**: Just above region blocks
  - Small lightning bolt icons (⚡) positioned at specific time points
  - Icons appear at region boundaries where fills are detected
  - Subtle hover state (slightly larger, with shadow)

- **Region Blocks Container**: Full-width horizontal bar
  - Divide into distinct colored blocks for each Arrangement Region:
    - Intro
    - Build
    - High-Energy / Drop
    - Breakdown
    - Outro
  - Each block shows:
    - Region Name (centered, bold)
    - Start–End time (e.g., "0:00–0:14")
    - **Motif Markers**: Small colored circular dots positioned within the block
      - Each dot represents a detected motif instance
      - Color-coding: Each motif group has a consistent color (e.g., green, blue, orange, purple, red, cyan)
      - Dots positioned horizontally based on their time position within the region
      - Variation motifs shown with dashed border circles
      - Hover state: When hovering over a dot, all dots in the same group highlight (slightly larger, with shadow)
      - Dots appear as small 8px circles at the top edge of region blocks

### Call-Response Conversation Panel (Right Column):

- **Panel Header**: "Call & Response" (bold, with underline border)
- **Scrollable Content Area**: List of conversation groups
  - Each group has a **Region Header** (e.g., "Intro", "Build") with colored left border
  - Under each region, **Call-Response Pairs** displayed as chat-like rows:
    - Each row shows: `[Stem Role] → [Stem Role]`
      - Call stem in blue text
      - Arrow (→) in gray
      - Response stem in green text
    - Below: "Bar X.X → Bar Y.Y" (time information)
    - Meta info: Badge showing "Inter-stem" (blue) or "Intra-stem" (purple)
    - Confidence percentage on the right
  - Rows have light gray background, rounded corners
  - Hover state: Row background changes to lighter gray, border highlights in blue
  - Clicked/highlighted row: Blue-tinted background with stronger border

### Region Details Section (Below Timeline):

- **Section Header**: "Region Details"
- Grid of region cards showing:
  - Region name
  - Type label
  - Time range

### Visual Style:

- 2D only, flat design.
- Region color suggestions:
  - Intro = soft blue (#e3f2fd)
  - Build = yellow-gold (#fff3e0)
  - High-Energy/Drop = saturated red or hot pink (#ffebee)
  - Breakdown = teal or muted green
  - Outro = soft gray or lavender
- Motif marker colors (distinct, vibrant):
  - Green (#4caf50)
  - Blue (#2196f3)
  - Orange (#ff9800)
  - Purple (#9c27b0)
  - Red (#f44336)
  - Cyan (#00bcd4)
- Panel backgrounds: White with subtle shadows
- Borders: Light gray (#e0e0e0)
- Text: Dark gray (#333) for primary, medium gray (#666) for secondary

### STRICT RULES:

- Do not render:
  - Laptops  
  - Desks  
  - Keyboards  
  - Audio gear  
  - Rooms  
  - People  
- Only render the UI panels as if they were captured from inside a design system.
- Show the UI in a clean, modern interface style
- All interactive elements should appear in their default state (not hovered/clicked unless specifically mentioned)

