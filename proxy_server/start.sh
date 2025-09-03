#!/bin/bash

echo "🚀 Starting Bittensor Audio Processing Proxy Server..."

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed or not in PATH"
    exit 1
fi

# Check if required files exist
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found"
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found"
    exit 1
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
pip install -r requirements.txt

# Start the server
echo "🌐 Starting server on http://localhost:8000"
echo "📚 API documentation: http://localhost:8000/docs"
echo "🔄 Press Ctrl+C to stop"

python main.py
