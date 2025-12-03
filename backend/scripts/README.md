# Backend Scripts

## motif_sensitivity_sweep.py

Diagnostic script to sweep through motif sensitivity configurations and generate a report.

### Usage

```bash
# From the backend directory
cd backend
python -m scripts.motif_sensitivity_sweep <reference_id>
```

**Quick Start (Test Data):**
```bash
cd backend
python -m scripts.motif_sensitivity_sweep gallium
```

This will automatically load the Gallium test data from disk and run the sweep.

### Getting a Reference ID

You can use either:
1. **"gallium" or "test"** - Automatically loads test data from disk (recommended for quick testing)
2. **A UUID reference ID** - From a reference that has already been analyzed in the server

For UUID reference IDs, you can get one in several ways:

#### Option 1: From the UI
1. Start the app: `./run.sh`
2. Upload a reference or use the dev endpoint to load test data
3. Run analysis
4. Check the browser console or network tab to see the `referenceId` in API responses

#### Option 2: Using the Dev Endpoint
```bash
# Create a test reference using the Gallium test data
curl -X POST http://localhost:8000/api/reference/dev/gallium

# Response will include a referenceId like:
# {"referenceId": "1c430928-c0cf-49c4-b655-6e5ff48fbbbc", ...}
```

#### Option 3: Check Backend Logs
When you upload/analyze a reference, the backend logs will show the reference ID.

### Example

```bash
# Make sure backend server is running and you have a reference ID
python -m scripts.motif_sensitivity_sweep 1c430928-c0cf-49c4-b655-6e5ff48fbbbc
```

### Requirements

- The reference must already be loaded and analyzed (regions must exist)
- The script will run motif detection, grouping, and call/response analysis multiple times with different sensitivity configs
- Output is a tabular report showing motifs, groups, compression ratios, and call/response pairs per stem

