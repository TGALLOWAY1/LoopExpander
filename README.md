# LoopExpander - Song Structure Replicator

A full-stack web application that uses machine learning and signal processing to automatically analyze and replicate the structural patterns of reference music tracks. The system identifies musical regions, detects repeated motifs, discovers call-and-response relationships, and locates fills—enabling musicians and producers to understand and recreate complex song structures.

## 🎯 Project Overview

LoopExpander is an intelligent audio analysis engine that breaks down songs into their fundamental structural components. By processing multi-stem audio files (drums, bass, vocals, instruments, and full mix), the system applies advanced signal processing and unsupervised learning techniques to map out a song's architecture, making it easier to study, remix, or recreate similar arrangements.

### Key Capabilities

- **Region Detection**: Automatically identifies song sections (intro, verse, chorus, bridge, outro) using spectral analysis and novelty detection
- **Motif Discovery**: Clusters repeated musical patterns across stems using MFCC feature extraction and DBSCAN clustering
- **Call-Response Analysis**: Detects lead-lag relationships between motifs, identifying musical conversations within and across instrument stems
- **Fill Detection**: Locates high-transient density regions (drum fills, bass slides, vocal ad-libs) near section boundaries
- **Interactive Visualization**: Real-time region map with motif markers, sensitivity controls, and call-response conversation panels

## 🛠️ Technology Stack

### Backend
- **Python 3.7+** with FastAPI for RESTful API
- **Audio Processing**: librosa, numpy, scipy for signal processing and feature extraction
- **Machine Learning**: scikit-learn (DBSCAN clustering, StandardScaler) for pattern recognition
- **Architecture**: Modular design with separation of concerns (ingest, analysis, API layers)

### Frontend
- **React 18** with TypeScript for type-safe component development
- **Vite** for fast development and optimized builds
- **Context API** for global state management
- **Responsive Design** with custom CSS and modern UI patterns

## 🏗️ Architecture

The application follows a clean, modular architecture:

```
LoopExpander/
├── backend/          # FastAPI analysis engine
│   ├── analysis/     # Core ML algorithms
│   │   ├── region_detector/    # Section boundary detection
│   │   ├── motif_detector/      # Pattern clustering
│   │   ├── call_response_detector/  # Relationship analysis
│   │   └── fill_detector/      # Transient detection
│   ├── stem_ingest/  # Audio file processing
│   └── api/          # REST endpoints
├── frontend/         # React SPA
│   ├── pages/        # Route components
│   ├── components/   # Reusable UI components
│   └── api/          # API client layer
└── docs/             # Documentation & mockups
```

## 🚀 Getting Started

### Prerequisites

- Python 3.7+
- Node.js 18+
- npm or pnpm

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
cd src
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000` with interactive docs at `/docs`.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

## 📊 Technical Highlights

### Signal Processing
- **MFCC Feature Extraction**: 13-dimensional feature vectors for motif characterization
- **Spectral Analysis**: RMS envelopes, spectral centroids, and novelty curves for region detection
- **Onset Detection**: Transient density computation for fill identification
- **BPM Estimation**: Automatic tempo detection using librosa's beat tracking

### Machine Learning
- **Unsupervised Clustering**: DBSCAN algorithm with adaptive epsilon based on sensitivity parameters
- **Feature Normalization**: StandardScaler for consistent clustering across different audio characteristics
- **Similarity Metrics**: Cosine similarity and Euclidean distance for call-response pattern matching
- **Confidence Scoring**: Multi-factor confidence calculation combining similarity, rhythmic alignment, and temporal proximity

### Software Engineering
- **Type Safety**: Full TypeScript coverage in frontend, type hints throughout Python backend
- **Modular Design**: Pluggable analysis modules with clear interfaces
- **Comprehensive Testing**: Unit tests for all analysis algorithms and API endpoints
- **Performance Optimization**: Configurable debug caps, timing logs, and efficient feature caching

## 🎨 Features

### Region Map Visualization
- Interactive timeline showing detected song sections
- Color-coded region types (intro, build, high-energy, breakdown, outro)
- Motif markers with group-based color coding
- Fill indicators at section boundaries
- Real-time sensitivity adjustment for motif clustering

### Call-Response Panel
- Grouped conversation view by region
- Inter-stem and intra-stem relationship detection
- Confidence scores and time offsets
- Click-to-highlight motif pairs on timeline

### Developer Tools
- Dev-only test file loader for rapid iteration
- Comprehensive logging with timing metrics
- Debug mode with configurable segment caps
- API documentation via Swagger UI

## 📈 Project Status

**Current Milestone**: Milestone 2 - Motif & Call-Response Detection ✅

- ✅ Audio ingestion and validation
- ✅ Region detection with probabilistic priors
- ✅ Motif detection with configurable sensitivity
- ✅ Call-response relationship discovery
- ✅ Fill detection at boundaries
- ✅ Interactive visualization UI
- 🔄 Arrangement generation (planned)
- 🔄 Export functionality (planned)

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend build check
cd frontend
npm run build
```

## 📝 API Endpoints

- `POST /api/reference/upload` - Upload reference track stems
- `POST /api/reference/{id}/analyze` - Run full analysis pipeline
- `GET /api/reference/{id}/regions` - Get detected regions
- `GET /api/reference/{id}/motifs` - Get motifs (with optional sensitivity re-clustering)
- `GET /api/reference/{id}/call-response` - Get call-response pairs
- `GET /api/reference/{id}/fills` - Get detected fills
- `POST /api/reference/dev/gallium` - Dev endpoint for test files

## 🎓 Learning Outcomes

This project demonstrates expertise in:

- **Audio Signal Processing**: Feature extraction, spectral analysis, onset detection
- **Machine Learning**: Unsupervised clustering, similarity metrics, pattern recognition
- **Full-Stack Development**: RESTful API design, React state management, TypeScript
- **Software Architecture**: Modular design, separation of concerns, testability
- **Performance Engineering**: Timing analysis, optimization strategies, debugging tools

## 📄 License

This project is part of a portfolio demonstration.

---

**Built with passion for music technology and machine learning** 🎵🤖
