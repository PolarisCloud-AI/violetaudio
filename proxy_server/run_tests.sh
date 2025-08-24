#!/bin/bash

# Enhanced Proxy Server Test Runner
# This script runs all tests to ensure system reliability

echo "🧪 Running Enhanced Proxy Server Tests..."

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

# Install test requirements
echo "📦 Installing test requirements..."
pip install -r requirements_enhanced.txt

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export ENVIRONMENT="testing"

# Run tests
echo "🧪 Running tests..."
echo "📊 Test results:"

# Run pytest with coverage
python -m pytest tests/test_enhanced_system.py -v --tb=short

# Check test exit code
if [ $? -eq 0 ]; then
    echo "✅ All tests passed successfully!"
    echo "🚀 System is ready for production use."
else
    echo "❌ Some tests failed. Please review the output above."
    echo "🔧 Fix the issues before deploying to production."
    exit 1
fi

echo "🎉 Test run completed!"
