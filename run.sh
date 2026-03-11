#!/bin/bash
# Run EFDAnalyzer Web application locally

cd "$(dirname "$0")"

echo "Starting EFDAnalyzer Web Application..."
echo "========================================"

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
echo "Starting server at http://localhost:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
