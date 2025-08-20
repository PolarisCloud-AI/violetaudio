#!/usr/bin/env python3
"""
Test script to demonstrate validator-proxy server integration
This script shows how the validator can check for tasks from the proxy server
"""

import asyncio
import requests
import time
import json

# Configuration
PROXY_SERVER_URL = "http://localhost:8000"
VALIDATOR_CHECK_INTERVAL = 30  # seconds

async def simulate_validator_proxy_integration():
    """Simulate how the validator would check the proxy server for tasks"""
    
    print("🧪 Testing Validator-Proxy Server Integration")
    print("=" * 60)
    
    # Check if proxy server is running
    try:
        response = requests.get(f"{PROXY_SERVER_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ Proxy server is running")
            health_data = response.json()
            print(f"   Status: {health_data.get('status')}")
            print(f"   Bittensor connected: {health_data.get('bittensor_connected')}")
            print(f"   Pending tasks: {health_data.get('pending_tasks')}")
        else:
            print(f"❌ Proxy server returned status {response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not connect to proxy server: {str(e)}")
        print("   Make sure the proxy server is running on http://localhost:8000")
        return
    
    # Get integration info
    try:
        print("\n🔍 Getting validator integration info...")
        response = requests.get(f"{PROXY_SERVER_URL}/api/v1/validator/integration", timeout=10)
        
        if response.status_code == 200:
            integration_data = response.json()
            
            print("✅ Integration info retrieved:")
            print(f"   Network: {integration_data.get('network_info', {}).get('network')}")
            print(f"   NetUID: {integration_data.get('network_info', {}).get('netuid')}")
            print(f"   Total miners: {integration_data.get('network_info', {}).get('total_miners')}")
            print(f"   Available miners: {integration_data.get('network_info', {}).get('available_miners')}")
            
            # Show pending tasks
            pending_tasks = integration_data.get('pending_tasks', [])
            if pending_tasks:
                print(f"\n📋 Pending tasks ({len(pending_tasks)}):")
                for i, task in enumerate(pending_tasks[:5]):  # Show first 5
                    print(f"   {i+1}. {task.get('task_type')} ({task.get('language')}) - {task.get('task_id')[:8]}...")
            else:
                print("\n📭 No pending tasks")
            
            # Show queue stats
            queue_stats = integration_data.get('queue_stats', {})
            print(f"\n📊 Queue statistics:")
            print(f"   Pending: {queue_stats.get('pending_count', 0)}")
            print(f"   Processing: {queue_stats.get('processing_count', 0)}")
            print(f"   Completed: {queue_stats.get('completed_count', 0)}")
            print(f"   Failed: {queue_stats.get('failed_count', 0)}")
            
        else:
            print(f"❌ Failed to get integration info: {response.status_code}")
            return
            
    except Exception as e:
        print(f"❌ Error getting integration info: {str(e)}")
        return
    
    # Simulate task distribution
    try:
        print("\n🔄 Simulating task distribution...")
        response = requests.post(f"{PROXY_SERVER_URL}/api/v1/validator/distribute", timeout=10)
        
        if response.status_code == 200:
            distribute_data = response.json()
            print(f"✅ Task distribution: {distribute_data.get('message')}")
            print(f"   Tasks distributed: {distribute_data.get('task_count')}")
        else:
            print(f"❌ Task distribution failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error distributing tasks: {str(e)}")
    
    print("\n🎯 Integration Test Complete!")
    print("\nTo run the validator with proxy integration:")
    print("python neurons/validator.py --netuid 49 --subtensor.network finney --wallet.name luno --wallet.hotkey arusha")
    print("   --logging.debug --axon.ip 0.0.0.0 --axon.port 8092 --axon.external_ip 102.134.149.117 --axon.external_port 8092")
    print("   --proxy_server_url http://localhost:8000 --enable_proxy_integration --proxy_check_interval 30")

def test_proxy_endpoints():
    """Test the proxy server endpoints directly"""
    
    print("\n🧪 Testing Proxy Server Endpoints")
    print("=" * 50)
    
    # Test health endpoint
    try:
        response = requests.get(f"{PROXY_SERVER_URL}/api/v1/health")
        print(f"✅ Health check: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Pending tasks: {data.get('pending_tasks')}")
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
    
    # Test integration endpoint
    try:
        response = requests.get(f"{PROXY_SERVER_URL}/api/v1/validator/integration")
        print(f"✅ Integration endpoint: {response.status_code}")
    except Exception as e:
        print(f"❌ Integration endpoint failed: {str(e)}")
    
    # Test distribute endpoint
    try:
        response = requests.post(f"{PROXY_SERVER_URL}/api/v1/validator/distribute")
        print(f"✅ Distribute endpoint: {response.status_code}")
    except Exception as e:
        print(f"❌ Distribute endpoint failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Validator-Proxy Integration Test")
    print("=" * 60)
    
    # Test proxy endpoints first
    test_proxy_endpoints()
    
    # Run integration simulation
    asyncio.run(simulate_validator_proxy_integration())
