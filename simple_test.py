#!/usr/bin/env python3
"""
Simple test script to verify basic connectivity to the proxy server
"""

import asyncio
import httpx
import json

async def test_basic_connectivity():
    """Test basic connectivity to proxy server"""
    print("🧪 Testing basic connectivity to proxy server...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test health endpoint
            print("  Testing health endpoint...")
            response = await client.get("http://localhost:8000/health")
            print(f"    Health endpoint: {response.status_code}")
            
            # Test miner status endpoint
            print("  Testing miner status endpoint...")
            test_data = {
                "validator_uid": 123,
                "miner_statuses": [
                    {
                        "uid": 1,
                        "hotkey": "test_hotkey_1",
                        "ip": "127.0.0.1",
                        "port": 8091,
                        "external_ip": "127.0.0.1",
                        "external_port": 8091,
                        "is_serving": True,
                        "stake": 1000.0,
                        "performance_score": 0.95,
                        "current_load": 0,
                        "max_capacity": 5,
                        "task_type_specialization": {
                            "transcription": {"total": 10, "successful": 9, "avg_time": 2.5, "success_rate": 0.9}
                        }
                    }
                ],
                "epoch": 1
            }
            
            response = await client.post(
                "http://localhost:8000/api/v1/validators/miner-status",
                json=test_data,
                timeout=30.0
            )
            print(f"    Miner status endpoint: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"    Response: {result}")
                return True
            else:
                print(f"    Error response: {response.text}")
                return False
                
    except httpx.TimeoutException:
        print("  ❌ Timeout connecting to proxy server")
        return False
    except httpx.ConnectError:
        print("  ❌ Connection error to proxy server")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False

async def main():
    print("🚀 Starting basic connectivity test...")
    
    # Wait a bit for server to be ready
    print("⏳ Waiting for server to be ready...")
    await asyncio.sleep(5)
    
    success = await test_basic_connectivity()
    
    if success:
        print("✅ Basic connectivity test passed!")
    else:
        print("❌ Basic connectivity test failed!")

if __name__ == "__main__":
    asyncio.run(main())

"""
Simple test script to verify basic connectivity to the proxy server
"""

import asyncio
import httpx
import json

async def test_basic_connectivity():
    """Test basic connectivity to proxy server"""
    print("🧪 Testing basic connectivity to proxy server...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test health endpoint
            print("  Testing health endpoint...")
            response = await client.get("http://localhost:8000/health")
            print(f"    Health endpoint: {response.status_code}")
            
            # Test miner status endpoint
            print("  Testing miner status endpoint...")
            test_data = {
                "validator_uid": 123,
                "miner_statuses": [
                    {
                        "uid": 1,
                        "hotkey": "test_hotkey_1",
                        "ip": "127.0.0.1",
                        "port": 8091,
                        "external_ip": "127.0.0.1",
                        "external_port": 8091,
                        "is_serving": True,
                        "stake": 1000.0,
                        "performance_score": 0.95,
                        "current_load": 0,
                        "max_capacity": 5,
                        "task_type_specialization": {
                            "transcription": {"total": 10, "successful": 9, "avg_time": 2.5, "success_rate": 0.9}
                        }
                    }
                ],
                "epoch": 1
            }
            
            response = await client.post(
                "http://localhost:8000/api/v1/validators/miner-status",
                json=test_data,
                timeout=30.0
            )
            print(f"    Miner status endpoint: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"    Response: {result}")
                return True
            else:
                print(f"    Error response: {response.text}")
                return False
                
    except httpx.TimeoutException:
        print("  ❌ Timeout connecting to proxy server")
        return False
    except httpx.ConnectError:
        print("  ❌ Connection error to proxy server")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False

async def main():
    print("🚀 Starting basic connectivity test...")
    
    # Wait a bit for server to be ready
    print("⏳ Waiting for server to be ready...")
    await asyncio.sleep(5)
    
    success = await test_basic_connectivity()
    
    if success:
        print("✅ Basic connectivity test passed!")
    else:
        print("❌ Basic connectivity test failed!")

if __name__ == "__main__":
    asyncio.run(main())






