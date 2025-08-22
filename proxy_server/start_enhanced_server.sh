#!/bin/bash

# Enhanced Proxy Server Startup Script
# This script starts the enhanced proxy server with proper environment setup

echo "🚀 Starting Enhanced Bittensor Proxy Server..."

# Check if Python 3.8+ is available
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8+ is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade pip
echo "📥 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📦 Installing requirements..."
pip install -r requirements_enhanced.txt

# Check if database credentials exist
if [ ! -f "db/violet.json" ]; then
    echo "❌ Database credentials not found at db/violet.json"
    echo "Please ensure your Firebase credentials are properly configured."
    exit 1
fi

echo "✅ Database credentials found"

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export ENVIRONMENT="production"

# Start the enhanced server
echo "🚀 Starting Enhanced Proxy Server..."
echo "🔗 Server will be available at: http://localhost:8000"
echo "📚 API documentation at: http://localhost:8000/docs"
echo "🛑 Press Ctrl+C to stop the server"

python enhanced_main.py
