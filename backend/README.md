# LoopExpander Backend

FastAPI backend for the Song Structure Replicator.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

**Important**: You must run uvicorn from the `backend/src` directory.

### Option 1: Using the startup script (recommended)
From the project root:
```bash
./backend/run.sh
```

### Option 2: Manual command
From the `backend/src` directory:
```bash
cd backend/src
uvicorn main:app --reload
```

### Option 3: One-liner from project root
```bash
cd backend/src && uvicorn main:app --reload
```

The server will start on `http://127.0.0.1:8000`

**Note**: If you get import errors, make sure you're in the `backend/src` directory where `main.py` is located.

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/reference/ping` - Reference API health check
- `POST /api/reference/upload` - Upload reference stems
- `POST /api/reference/{id}/analyze` - Analyze reference
- `GET /api/reference/{id}/regions` - Get detected regions

## Project Structure

```
backend/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py             # Configuration
│   ├── api/                  # API routes
│   ├── models/              # Data models
│   ├── stem_ingest/         # Audio ingestion
│   ├── analysis/            # Analysis modules
│   └── utils/               # Utilities
└── tests/                   # Test files
```

