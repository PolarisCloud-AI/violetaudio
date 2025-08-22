#!/usr/bin/env python3
"""
Test script for the task distribution system
Tests the complete flow: proxy → miner assignment → miner processing → response collection
"""

import asyncio
import httpx
import json
from datetime import datetime

# Configuration
PROXY_URL = "http://localhost:8000"
MINER_URL = "http://localhost:8091"  # Adjust based on your miner port

async def test_miner_status_reporting():
    """Test validator reporting miner status to proxy"""
    print("🧪 Testing miner status reporting...")
    
    # Mock validator data
    validator_uid = 123
    miner_statuses = [
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
                "transcription": {"total": 10, "successful": 9, "avg_time": 2.5, "success_rate": 0.9},
                "tts": {"total": 8, "successful": 7, "avg_time": 3.1, "success_rate": 0.875}
            }
        },
        {
            "uid": 2,
            "hotkey": "test_hotkey_2",
            "ip": "127.0.0.1",
            "port": 8092,
            "external_ip": "127.0.0.1",
            "external_port": 8092,
            "is_serving": True,
            "stake": 800.0,
            "performance_score": 0.88,
            "current_load": 1,
            "max_capacity": 5,
            "task_type_specialization": {
                "transcription": {"total": 8, "successful": 7, "avg_time": 3.0, "success_rate": 0.875},
                "tts": {"total": 6, "successful": 5, "avg_time": 3.5, "success_rate": 0.833}
            }
        }
    ]
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{PROXY_URL}/api/v1/validators/miner-status",
                json={
                    "validator_uid": validator_uid,
                    "miner_statuses": miner_statuses,
                    "epoch": 1
                }
            )
            
            if response.status_code == 200:
                print("✅ Miner status reporting successful")
                return True
            else:
                print(f"❌ Miner status reporting failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        import traceback
        print(f"❌ Error testing miner status reporting: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def test_miner_status_retrieval():
    """Test retrieving miner status from proxy"""
    print("🧪 Testing miner status retrieval...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{PROXY_URL}/api/v1/miners/status")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Miner status retrieval successful")
                print(f"   Total miners: {data['statistics']['total_miners']}")
                print(f"   Serving miners: {data['statistics']['serving_miners']}")
                return True
            else:
                print(f"❌ Miner status retrieval failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing miner status retrieval: {e}")
        return False

async def test_task_submission():
    """Test submitting a transcription task"""
    print("🧪 Testing task submission...")
    
    # Create a mock audio file
    mock_audio_data = b"mock_audio_content_for_testing"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Submit transcription task
            files = {"audio_file": ("test_audio.wav", mock_audio_data, "audio/wav")}
            data = {"source_language": "en", "priority": "normal"}
            
            response = await client.post(
                f"{PROXY_URL}/api/v1/transcription",
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get("task_id")
                print(f"✅ Task submission successful: {task_id}")
                return task_id
            else:
                print(f"❌ Task submission failed: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Error testing task submission: {e}")
        return None

async def test_task_assignment_status(task_id: str):
    """Test checking task assignment status"""
    print(f"🧪 Testing task assignment status for {task_id}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{PROXY_URL}/api/v1/tasks/{task_id}/assignments")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Task assignment status retrieved")
                print(f"   Total assignments: {data['total_assignments']}")
                print(f"   Assigned: {data['assigned']}")
                print(f"   Completed: {data['completed']}")
                print(f"   Failed: {data['failed']}")
                return True
            else:
                print(f"❌ Task assignment status retrieval failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing task assignment status: {e}")
        return False

async def test_miner_health():
    """Test miner health endpoint"""
    print("🧪 Testing miner health...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{MINER_URL}/health")
            
            if response.status_code == 200:
                print("✅ Miner health check successful")
                return True
            else:
                print(f"❌ Miner health check failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing miner health: {e}")
        return False

async def test_miner_task_reception():
    """Test miner receiving a task"""
    print("🧪 Testing miner task reception...")
    
    # Mock task data
    task_data = {
        "task_id": "test_task_123",
        "task_type": "transcription",
        "input_file_url": f"{PROXY_URL}/api/v1/files/test_file/download",
        "source_language": "en",
        "target_language": "en",
        "priority": "normal",
        "deadline": datetime.now().isoformat(),
        "callback_url": f"{PROXY_URL}/api/v1/miner/response"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{MINER_URL}/api/v1/task", json=task_data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Miner task reception successful: {result}")
                return True
            else:
                print(f"❌ Miner task reception failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing miner task reception: {e}")
        return False

async def run_all_tests():
    """Run all tests in sequence"""
    print("🚀 Starting task distribution system tests...")
    print("=" * 60)
    
    # Add a delay to ensure proxy server is fully ready
    print("⏳ Waiting for proxy server to be ready...")
    await asyncio.sleep(3)
    
    # Test 1: Miner status reporting
    if not await test_miner_status_reporting():
        print("❌ Test 1 failed - stopping")
        return False
    
    # Test 2: Miner status retrieval
    if not await test_miner_status_retrieval():
        print("❌ Test 2 failed - stopping")
        return False
    
    # Test 3: Task submission
    task_id = await test_task_submission()
    if not task_id:
        print("❌ Test 3 failed - stopping")
        return False
    
    # Test 4: Task assignment status
    if not await test_task_assignment_status(task_id):
        print("❌ Test 4 failed - stopping")
        return False
    
    # Test 5: Miner health
    if not await test_miner_health():
        print("❌ Test 5 failed - stopping")
        return False
    
    # Test 6: Miner task reception
    if not await test_miner_task_reception():
        print("❌ Test 6 failed - stopping")
        return False
    
    print("=" * 60)
    print("🎉 All tests passed! Task distribution system is working correctly.")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        if success:
            print("✅ Test suite completed successfully")
        else:
            print("❌ Test suite failed")
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error during tests: {e}")

Test script for the task distribution system
Tests the complete flow: proxy → miner assignment → miner processing → response collection
"""

import asyncio
import httpx
import json
from datetime import datetime

# Configuration
PROXY_URL = "http://localhost:8000"
MINER_URL = "http://localhost:8091"  # Adjust based on your miner port

async def test_miner_status_reporting():
    """Test validator reporting miner status to proxy"""
    print("🧪 Testing miner status reporting...")
    
    # Mock validator data
    validator_uid = 123
    miner_statuses = [
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
                "transcription": {"total": 10, "successful": 9, "avg_time": 2.5, "success_rate": 0.9},
                "tts": {"total": 8, "successful": 7, "avg_time": 3.1, "success_rate": 0.875}
            }
        },
        {
            "uid": 2,
            "hotkey": "test_hotkey_2",
            "ip": "127.0.0.1",
            "port": 8092,
            "external_ip": "127.0.0.1",
            "external_port": 8092,
            "is_serving": True,
            "stake": 800.0,
            "performance_score": 0.88,
            "current_load": 1,
            "max_capacity": 5,
            "task_type_specialization": {
                "transcription": {"total": 8, "successful": 7, "avg_time": 3.0, "success_rate": 0.875},
                "tts": {"total": 6, "successful": 5, "avg_time": 3.5, "success_rate": 0.833}
            }
        }
    ]
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{PROXY_URL}/api/v1/validators/miner-status",
                json={
                    "validator_uid": validator_uid,
                    "miner_statuses": miner_statuses,
                    "epoch": 1
                }
            )
            
            if response.status_code == 200:
                print("✅ Miner status reporting successful")
                return True
            else:
                print(f"❌ Miner status reporting failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        import traceback
        print(f"❌ Error testing miner status reporting: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def test_miner_status_retrieval():
    """Test retrieving miner status from proxy"""
    print("🧪 Testing miner status retrieval...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{PROXY_URL}/api/v1/miners/status")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Miner status retrieval successful")
                print(f"   Total miners: {data['statistics']['total_miners']}")
                print(f"   Serving miners: {data['statistics']['serving_miners']}")
                return True
            else:
                print(f"❌ Miner status retrieval failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing miner status retrieval: {e}")
        return False

async def test_task_submission():
    """Test submitting a transcription task"""
    print("🧪 Testing task submission...")
    
    # Create a mock audio file
    mock_audio_data = b"mock_audio_content_for_testing"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Submit transcription task
            files = {"audio_file": ("test_audio.wav", mock_audio_data, "audio/wav")}
            data = {"source_language": "en", "priority": "normal"}
            
            response = await client.post(
                f"{PROXY_URL}/api/v1/transcription",
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get("task_id")
                print(f"✅ Task submission successful: {task_id}")
                return task_id
            else:
                print(f"❌ Task submission failed: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Error testing task submission: {e}")
        return None

async def test_task_assignment_status(task_id: str):
    """Test checking task assignment status"""
    print(f"🧪 Testing task assignment status for {task_id}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{PROXY_URL}/api/v1/tasks/{task_id}/assignments")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Task assignment status retrieved")
                print(f"   Total assignments: {data['total_assignments']}")
                print(f"   Assigned: {data['assigned']}")
                print(f"   Completed: {data['completed']}")
                print(f"   Failed: {data['failed']}")
                return True
            else:
                print(f"❌ Task assignment status retrieval failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing task assignment status: {e}")
        return False

async def test_miner_health():
    """Test miner health endpoint"""
    print("🧪 Testing miner health...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{MINER_URL}/health")
            
            if response.status_code == 200:
                print("✅ Miner health check successful")
                return True
            else:
                print(f"❌ Miner health check failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing miner health: {e}")
        return False

async def test_miner_task_reception():
    """Test miner receiving a task"""
    print("🧪 Testing miner task reception...")
    
    # Mock task data
    task_data = {
        "task_id": "test_task_123",
        "task_type": "transcription",
        "input_file_url": f"{PROXY_URL}/api/v1/files/test_file/download",
        "source_language": "en",
        "target_language": "en",
        "priority": "normal",
        "deadline": datetime.now().isoformat(),
        "callback_url": f"{PROXY_URL}/api/v1/miner/response"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{MINER_URL}/api/v1/task", json=task_data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Miner task reception successful: {result}")
                return True
            else:
                print(f"❌ Miner task reception failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing miner task reception: {e}")
        return False

async def run_all_tests():
    """Run all tests in sequence"""
    print("🚀 Starting task distribution system tests...")
    print("=" * 60)
    
    # Add a delay to ensure proxy server is fully ready
    print("⏳ Waiting for proxy server to be ready...")
    await asyncio.sleep(3)
    
    # Test 1: Miner status reporting
    if not await test_miner_status_reporting():
        print("❌ Test 1 failed - stopping")
        return False
    
    # Test 2: Miner status retrieval
    if not await test_miner_status_retrieval():
        print("❌ Test 2 failed - stopping")
        return False
    
    # Test 3: Task submission
    task_id = await test_task_submission()
    if not task_id:
        print("❌ Test 3 failed - stopping")
        return False
    
    # Test 4: Task assignment status
    if not await test_task_assignment_status(task_id):
        print("❌ Test 4 failed - stopping")
        return False
    
    # Test 5: Miner health
    if not await test_miner_health():
        print("❌ Test 5 failed - stopping")
        return False
    
    # Test 6: Miner task reception
    if not await test_miner_task_reception():
        print("❌ Test 6 failed - stopping")
        return False
    
    print("=" * 60)
    print("🎉 All tests passed! Task distribution system is working correctly.")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        if success:
            print("✅ Test suite completed successfully")
        else:
            print("❌ Test suite failed")
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error during tests: {e}")
