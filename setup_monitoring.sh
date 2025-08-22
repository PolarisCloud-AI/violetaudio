#!/bin/bash

echo "🚀 Setting up Bittensor Subnet Monitoring System..."

# Install Python dependencies
echo "📦 Installing monitoring dependencies..."
pip install -r requirements_monitoring.txt

# Set wandb environment variables
echo "🔑 Configuring Weights & Biases..."
export WANDB_API_KEY="XXXXXXX"
export WANDB_MODE="online"
export WANDB_SILENT="true"

# Create wandb configuration directory
echo "📁 Setting up wandb configuration..."
mkdir -p ~/.wandb

# Create wandb settings file
cat > ~/.wandb/settings << EOF
[default]
project = bittensor-inference-subnet
entity = 
base_url = https://api.wandb.ai
api_key = XXXXXX
EOF

echo "✅ Wandb configuration created at ~/.wandb/settings"

# Test wandb connection
echo "🧪 Testing wandb connection..."
python -c "
import wandb
import os
os.environ['WANDB_API_KEY'] = '2ac90cd4163f5b61805b142b04396e7190a47972'
try:
    api = wandb.Api()
    print('✅ Wandb connection successful!')
    print(f'🔑 API key: {os.environ[\"WANDB_API_KEY\"][:8]}...')
except Exception as e:
    print(f'❌ Wandb connection failed: {e}')
"

echo ""
echo "🎉 Monitoring setup complete!"
echo ""
echo "📊 Available monitoring features:"
echo "   • Weights & Biases (wandb) - Automatic performance tracking"
echo "   • Grafana-ready metrics - /api/v1/metrics endpoint"
echo "   • System performance monitoring"
echo "   • Cache performance tracking"
echo "   • Database operation monitoring"
echo ""
echo "🔗 Grafana Dashboard:"
echo "   • Import grafana_dashboard.json to Grafana"
echo "   • Connect to /api/v1/metrics endpoint"
echo ""
echo "🚀 Start the server with: python proxy_server/enhanced_main.py"
