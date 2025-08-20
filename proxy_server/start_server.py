#!/usr/bin/env python3
"""
Startup script for the Bittensor Audio Processing Proxy Server
"""

import asyncio
import sys
import os
import signal
import uvicorn
from pathlib import Path

# Add the parent directory to the path so we can import template modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from task_queue import TaskQueueManager
from bittensor_client import bittensor_client

config = get_config()

async def initialize_services():
    """Initialize all required services"""
    print("🚀 Initializing Bittensor Audio Processing Proxy Server...")
    
    # Initialize task queue manager
    print("📋 Initializing task queue manager...")
    queue_manager = TaskQueueManager()
    
    if not queue_manager.health_check():
        print("❌ Task queue manager health check failed")
        return False
    
    print("✅ Task queue manager initialized")
    
    # Initialize Bittensor client
    print("🌐 Initializing Bittensor client...")
    if not await bittensor_client.initialize():
        print("❌ Bittensor client initialization failed")
        return False
    
    print("✅ Bittensor client initialized")
    
    # Print configuration
    print("\n📊 Server Configuration:")
    print(f"   Host: {config.HOST}")
    print(f"   Port: {config.PORT}")
    print(f"   Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"   Bittensor Network: {config.BT_NETWORK}")
    print(f"   Subnet UID: {config.BT_NETUID}")
    print(f"   Redis: {config.REDIS_HOST}:{config.REDIS_PORT}")
    
    # Print network stats
    network_stats = bittensor_client.get_network_stats()
    if network_stats:
        print(f"\n🌐 Network Statistics:")
        print(f"   Total Miners: {network_stats.get('total_miners', 0)}")
        print(f"   Available Miners: {network_stats.get('available_miners', 0)}")
        print(f"   Total Stake: {network_stats.get('total_stake', 0):.2f}")
    
    # Print queue stats
    queue_stats = queue_manager.get_queue_stats()
    if queue_stats:
        print(f"\n📋 Queue Statistics:")
        print(f"   Pending Tasks: {queue_stats.get('pending_count', 0)}")
        print(f"   Processing Tasks: {queue_stats.get('processing_count', 0)}")
        print(f"   Completed Tasks: {queue_stats.get('completed_count', 0)}")
        print(f"   Failed Tasks: {queue_stats.get('failed_count', 0)}")
    
    print("\n🎉 All services initialized successfully!")
    return True

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    
    # Close Bittensor client
    asyncio.create_task(bittensor_client.close())
    
    print("👋 Server shutdown complete")
    sys.exit(0)

async def main():
    """Main startup function"""
    try:
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Initialize services
        if not await initialize_services():
            print("❌ Service initialization failed")
            sys.exit(1)
        
        print(f"\n🚀 Starting FastAPI server on {config.HOST}:{config.PORT}")
        print("📚 API documentation available at:")
        print(f"   http://{config.HOST}:{config.PORT}/docs")
        print(f"   http://{config.HOST}:{config.PORT}/redoc")
        print("\n🔄 Server is running... Press Ctrl+C to stop")
        
        # Start the server
        uvicorn.run(
            "main:app",
            host=config.HOST,
            port=config.PORT,
            reload=config.DEBUG,
            log_level=config.LOG_LEVEL.lower(),
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server startup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
