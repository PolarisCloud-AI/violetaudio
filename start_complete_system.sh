#!/bin/bash

# Complete System Startup Script
# This script starts all components needed for the complete workflow test

echo "🚀 Starting Complete Bittensor Audio Processing System"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Function to wait for a service to be ready
wait_for_service() {
    local port=$1
    local service_name=$2
    local max_wait=30
    local wait_time=0
    
    echo -e "${BLUE}⏳ Waiting for $service_name to be ready on port $port...${NC}"
    
    while [ $wait_time -lt $max_wait ]; do
        if check_port $port; then
            echo -e "${GREEN}✅ $service_name is ready on port $port${NC}"
            return 0
        fi
        sleep 1
        wait_time=$((wait_time + 1))
    done
    
    echo -e "${RED}❌ Timeout waiting for $service_name on port $port${NC}"
    return 1
}

# Check if required ports are available
echo -e "${BLUE}🔍 Checking port availability...${NC}"

if check_port 8000; then
    echo -e "${YELLOW}⚠️  Port 8000 is already in use (proxy server)${NC}"
else
    echo -e "${GREEN}✅ Port 8000 is available (proxy server)${NC}"
fi

if check_port 8091; then
    echo -e "${YELLOW}⚠️  Port 8091 is already in use (miner)${NC}"
else
    echo -e "${GREEN}✅ Port 8091 is available (miner)${NC}"
fi

if check_port 8092; then
    echo -e "${YELLOW}⚠️  Port 8092 is already in use (validator)${NC}"
else
    echo -e "${GREEN}✅ Port 8092 is available (validator)${NC}"
fi

echo ""

# Start Proxy Server
echo -e "${BLUE}🚀 Starting Proxy Server...${NC}"
if check_port 8000; then
    echo -e "${YELLOW}⚠️  Proxy server already running on port 8000${NC}"
else
    cd proxy_server
    echo -e "${BLUE}   Starting proxy server in background...${NC}"
    python main.py > ../logs/proxy_server.log 2>&1 &
    PROXY_PID=$!
    echo $PROXY_PID > ../logs/proxy_server.pid
    cd ..
    
    # Wait for proxy server to be ready
    if wait_for_service 8000 "Proxy Server"; then
        echo -e "${GREEN}✅ Proxy server started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start proxy server${NC}"
        exit 1
    fi
fi

# Start Miner
echo -e "${BLUE}🚀 Starting Miner...${NC}"
if check_port 8091; then
    echo -e "${YELLOW}⚠️  Miner already running on port 8091${NC}"
else
    echo -e "${BLUE}   Starting miner in background...${NC}"
    python neurons/miner.py \
        --netuid 49 \
        --subtensor.network finney \
        --wallet.name mokoai \
        --wallet.hotkey default \
        --logging.debug \
        --axon.ip 0.0.0.0 \
        --axon.port 8091 \
        --axon.external_ip 102.134.149.117 \
        --axon.external_port 8091 > logs/miner.log 2>&1 &
    MINER_PID=$!
    echo $MINER_PID > logs/miner.pid
    
    # Wait for miner to be ready
    if wait_for_service 8091 "Miner"; then
        echo -e "${GREEN}✅ Miner started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start miner${NC}"
        exit 1
    fi
fi

# Start Validator
echo -e "${BLUE}🚀 Starting Validator...${NC}"
if check_port 8092; then
    echo -e "${YELLOW}⚠️  Validator already running on port 8092${NC}"
else
    echo -e "${BLUE}   Starting validator in background...${NC}"
    python neurons/validator.py \
        --netuid 49 \
        --subtensor.network finney \
        --wallet.name luno \
        --wallet.hotkey arusha \
        --logging.debug \
        --axon.ip 0.0.0.0 \
        --axon.port 8092 \
        --axon.external_ip 102.134.149.117 \
        --axon.external_port 8092 \
        --proxy_server_url http://localhost:8000 \
        --enable_proxy_integration \
        --proxy_check_interval 30 > logs/validator.log 2>&1 &
    VALIDATOR_PID=$!
    echo $VALIDATOR_PID > logs/validator.pid
    
    # Wait for validator to be ready
    if wait_for_service 8092 "Validator"; then
        echo -e "${GREEN}✅ Validator started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start validator${NC}"
        exit 1
    fi
fi

# Create logs directory if it doesn't exist
mkdir -p logs

echo ""
echo -e "${GREEN}🎉 All components started successfully!${NC}"
echo "=================================================="
echo -e "${BLUE}📊 System Status:${NC}"
echo -e "   Proxy Server: ${GREEN}Running on port 8000${NC}"
echo -e "   Miner:        ${GREEN}Running on port 8091${NC}"
echo -e "   Validator:    ${GREEN}Running on port 8092${NC}"
echo ""
echo -e "${BLUE}📝 Log Files:${NC}"
echo -e "   Proxy Server: logs/proxy_server.log"
echo -e "   Miner:        logs/miner.log"
echo -e "   Validator:    logs/validator.log"
echo ""
echo -e "${BLUE}🧪 Run the complete workflow test:${NC}"
echo -e "   python test_complete_workflow.py"
echo ""
echo -e "${BLUE}🛑 To stop all services:${NC}"
echo -e "   ./stop_complete_system.sh"
echo ""
echo -e "${YELLOW}⚠️  Note: Make sure you have the correct wallet names and hotkeys configured${NC}"
echo -e "${YELLOW}⚠️  Note: Ensure Bittensor network connectivity and sufficient TAO balance${NC}"
