#!/bin/bash

# Complete System Stop Script
# This script stops all components of the complete system

echo "🛑 Stopping Complete Bittensor Audio Processing System"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to stop a service by PID file
stop_service() {
    local service_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${BLUE}🛑 Stopping $service_name (PID: $pid)...${NC}"
            kill $pid
            
            # Wait for process to stop
            local wait_time=0
            while ps -p $pid > /dev/null 2>&1 && [ $wait_time -lt 10 ]; do
                sleep 1
                wait_time=$((wait_time + 1))
            done
            
            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                echo -e "${YELLOW}⚠️  Force killing $service_name...${NC}"
                kill -9 $pid
            fi
            
            rm -f "$pid_file"
            echo -e "${GREEN}✅ $service_name stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  $service_name PID file exists but process not running${NC}"
            rm -f "$pid_file"
        fi
    else
        echo -e "${YELLOW}⚠️  No PID file found for $service_name${NC}"
    fi
}

# Function to stop service by port
stop_service_by_port() {
    local port=$1
    local service_name=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        local pids=$(lsof -Pi :$port -sTCP:LISTEN -t)
        echo -e "${BLUE}🛑 Stopping $service_name on port $port...${NC}"
        
        for pid in $pids; do
            echo -e "${BLUE}   Stopping process $pid...${NC}"
            kill $pid
            
            # Wait for process to stop
            local wait_time=0
            while ps -p $pid > /dev/null 2>&1 && [ $wait_time -lt 10 ]; do
                sleep 1
                wait_time=$((wait_time + 1))
            done
            
            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                echo -e "${YELLOW}⚠️  Force killing process $pid...${NC}"
                kill -9 $pid
            fi
        done
        
        echo -e "${GREEN}✅ $service_name stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  $service_name not running on port $port${NC}"
    fi
}

# Stop Proxy Server
echo -e "${BLUE}🛑 Stopping Proxy Server...${NC}"
stop_service "Proxy Server" "logs/proxy_server.pid"
stop_service_by_port 8000 "Proxy Server"

# Stop Miner
echo -e "${BLUE}🛑 Stopping Miner...${NC}"
stop_service "Miner" "logs/miner.pid"
stop_service_by_port 8091 "Miner"

# Stop Validator
echo -e "${BLUE}🛑 Stopping Validator...${NC}"
stop_service "Validator" "logs/validator.pid"
stop_service_by_port 8092 "Validator"

# Clean up any remaining processes
echo -e "${BLUE}🧹 Cleaning up remaining processes...${NC}"

# Kill any remaining Python processes related to our services
pkill -f "neurons/miner.py" 2>/dev/null || true
pkill -f "neurons/validator.py" 2>/dev/null || true
pkill -f "proxy_server/main.py" 2>/dev/null || true

# Wait a moment for processes to fully stop
sleep 2

# Final port check
echo -e "${BLUE}🔍 Final port status check...${NC}"

if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}❌ Port 8000 still in use${NC}"
else
    echo -e "${GREEN}✅ Port 8000 (Proxy Server) is free${NC}"
fi

if lsof -Pi :8091 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}❌ Port 8091 still in use${NC}"
else
    echo -e "${GREEN}✅ Port 8091 (Miner) is free${NC}"
fi

if lsof -Pi :8092 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}❌ Port 8092 still in use${NC}"
else
    echo -e "${GREEN}✅ Port 8092 (Validator) is free${NC}"
fi

echo ""
echo -e "${GREEN}🎉 All services stopped successfully!${NC}"
echo "=================================================="
echo -e "${BLUE}📝 Log files are preserved in the logs/ directory${NC}"
echo -e "${BLUE}🚀 To restart the system, run: ./start_complete_system.sh${NC}"
