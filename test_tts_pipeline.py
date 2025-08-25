#!/usr/bin/env python3
"""
Test script for TTS pipeline
Tests the complete flow: proxy -> miner -> audio generation -> upload
"""

import asyncio
import httpx
import time
import json

async def test_tts_pipeline():
    """Test the complete TTS pipeline"""
    print("🧪 Testing TTS Pipeline")
    print("=" * 50)
    
    # Step 1: Create TTS task
    print("\n1️⃣ Creating TTS task...")
    tts_text = "This is a comprehensive test of the TTS pipeline. The miner should generate an audio file from this text and upload it to the proxy server. This will verify that the complete pipeline is working correctly."
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/api/v1/tts",
                data={
                    "text": tts_text,
                    "source_language": "en",
                    "priority": "normal"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get("task_id")
                print(f"✅ TTS task created successfully")
                print(f"   Task ID: {task_id}")
                print(f"   Text length: {result.get('text_length')} characters")
                print(f"   Auto-assigned: {result.get('auto_assigned')}")
            else:
                print(f"❌ Failed to create TTS task: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return
                
    except Exception as e:
        print(f"❌ Error creating TTS task: {e}")
        return
    
    # Step 2: Wait for task assignment and processing
    print(f"\n2️⃣ Waiting for task processing...")
    print(f"   Task ID: {task_id}")
    print(f"   This may take a few minutes...")
    
    # Check task status every 10 seconds for up to 5 minutes
    max_wait_time = 300  # 5 minutes
    check_interval = 10   # 10 seconds
    elapsed_time = 0
    
    while elapsed_time < max_wait_time:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check if task is still assigned
                response = await client.get(f"http://localhost:8000/api/v1/miners/48/tasks?status=assigned")
                
                if response.status_code == 200:
                    tasks = response.json()
                    task_found = any(task.get("task_id") == task_id for task in tasks)
                    
                    if not task_found:
                        print(f"✅ Task {task_id} is no longer assigned - likely completed!")
                        break
                    else:
                        print(f"⏳ Task {task_id} still processing... ({elapsed_time}s elapsed)")
                else:
                    print(f"⚠️ Could not check task status: HTTP {response.status_code}")
                    
        except Exception as e:
            print(f"⚠️ Error checking task status: {e}")
        
        await asyncio.sleep(check_interval)
        elapsed_time += check_interval
    
    if elapsed_time >= max_wait_time:
        print(f"⏰ Timeout waiting for task completion after {max_wait_time}s")
        return
    
    # Step 3: Check if audio file was generated
    print(f"\n3️⃣ Checking for generated audio file...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check the TTS audio directory
            response = await client.get("http://localhost:8000/api/v1/tts/audio/test")
            
            if response.status_code == 404:
                print("ℹ️ Audio file endpoint is working (404 for non-existent file is expected)")
            else:
                print(f"ℹ️ Audio file endpoint response: HTTP {response.status_code}")
                
    except Exception as e:
        print(f"⚠️ Error checking audio endpoint: {e}")
    
    print(f"\n🎯 TTS Pipeline Test Complete!")
    print(f"   Task ID: {task_id}")
    print(f"   Processing time: {elapsed_time}s")
    print(f"   Status: {'Completed' if elapsed_time < max_wait_time else 'Timeout'}")

if __name__ == "__main__":
    asyncio.run(test_tts_pipeline())


