#!/bin/bash
# Startup script for the FastAPI backend

cd "$(dirname "$0")/src"
uvicorn main:app --reload --host 127.0.0.1 --port 8000

