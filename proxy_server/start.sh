#!/bin/bash

# Bittensor Audio Processing Proxy Server Startup Script

echo "🚀 Starting Bittensor Audio Processing Proxy Server..."

# Check if Redis is running
echo "🔍 Checking Redis connection..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running. Starting Redis..."
    
    # Try to start Redis based on OS
    if command -v brew > /dev/null 2>&1; then
        # macOS
        brew services start redis
    elif command -v systemctl > /dev/null 2>&1; then
        # Linux with systemd
        sudo systemctl start redis-server
    elif command -v service > /dev/null 2>&1; then
        # Linux with service
        sudo service redis-server start
    else
        echo "❌ Could not start Redis automatically. Please start Redis manually:"
        echo "   - macOS: brew services start redis"
        echo "   - Ubuntu/Debian: sudo systemctl start redis-server"
        echo "   - Or use Docker: docker run -d -p 6379:6379 redis:alpine"
        exit 1
    fi
    
    # Wait for Redis to start
    echo "⏳ Waiting for Redis to start..."
    sleep 3
    
    if ! redis-cli ping > /dev/null 2>&1; then
        echo "❌ Redis failed to start"
        exit 1
    fi
fi

echo "✅ Redis is running"

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  No virtual environment detected. Consider using one:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate  # On Unix/macOS"
    echo "   venv\\Scripts\\activate     # On Windows"
fi

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the server
echo "🚀 Starting proxy server..."
python start_server.py
