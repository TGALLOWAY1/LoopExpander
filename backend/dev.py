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
    # Get the backend directory
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent
    src_dir = backend_dir / "src"
    
    # Change to project root to ensure relative imports work
    import os
    os.chdir(project_root)
    
    # Set PYTHONPATH to include backend/src so imports work correctly
    env = os.environ.copy()
    pythonpath = str(src_dir)
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{pythonpath}:{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = pythonpath
    
    # Run uvicorn
    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.src.main:app",
        "--reload",
        "--port", "8000"
    ]
    
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

