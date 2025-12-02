# LoopExpander Frontend

React + TypeScript frontend for the Song Structure Replicator.

## Setup

```bash
npm install
```

## Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173`.

## API Client

The API client is located in `src/api/reference.ts` and provides:

- `uploadReference()` - Upload reference track stems
- `analyzeReference()` - Run region detection
- `fetchRegions()` - Get detected regions

## Project Context

The `ProjectContext` provides shared state for:

- `referenceId` - Current reference track ID
- `regions` - Detected regions array

Use the `useProject()` hook to access project state in any component.

## Environment Variables

Create a `.env` file to configure:

```
VITE_API_BASE_URL=http://localhost:8000
```

