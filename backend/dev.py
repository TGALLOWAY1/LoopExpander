#!/usr/bin/env python3
"""
Development server entry point for the backend.
Provides a convenient way to start the FastAPI server with uvicorn.

Usage:
    python dev.py
    # or
    python -m backend.dev
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Start the FastAPI development server."""
    import os
    
    # Get the backend directory and src subdirectory
    backend_dir = Path(__file__).parent
    src_dir = backend_dir / "src"
    
    # Verify src directory exists
    if not src_dir.exists():
        print(f"Error: Source directory not found at {src_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Change to src directory so imports work correctly
    # This ensures that 'config', 'api', 'models', etc. can be imported directly
    os.chdir(src_dir)
    
    # Run uvicorn from src directory
    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--reload",
        "--host", "127.0.0.1",
        "--port", "8000"
    ]
    
    # Use current environment (no need to set PYTHONPATH since we're in src directory)
    env = os.environ.copy()
    
    print("Starting FastAPI development server...")
    print("Server will be available at http://localhost:8000")
    print("API documentation at http://localhost:8000/docs")
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        subprocess.run(cmd, check=True, env=env)
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

