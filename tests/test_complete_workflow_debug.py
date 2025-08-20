#!/usr/bin/env python3
"""
Complete Workflow Debug Test

This script tests the complete subnet workflow:
1. Proxy Server receives user input
2. Validator picks up tasks
3. Validator distributes tasks to miners
4. Miners process tasks and return responses
5. Validator evaluates responses and ranks miners
6. Validator sends best result back to proxy server
"""

import requests
import time
import json
import base64
import numpy as np
import soundfile as sf
import io

def create_test_audio():
    """Create a simple test audio file"""
    # Generate 2 seconds of 440 Hz sine wave
    sample_rate = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(2 * np.pi * 440 * t) * 0.3
    
    # Save to bytes
    audio_bytes = io.BytesIO()
    sf.write(audio_bytes, audio_data, sample_rate, format='WAV')
    audio_bytes.seek(0)
    
    return audio_bytes.read()

def test_complete_workflow():
    """Test the complete subnet workflow"""
    print("🚀 Starting Complete Workflow Test")
    print("=" * 60)
    
    # Step 1: Check system health
    print("\n1️⃣ Checking system health...")
    try:
        health_response = requests.get("http://localhost:8000/api/v1/health")
        health_data = health_response.json()
        print(f"✅ Proxy Server Status: {health_data['status']}")
        print(f"   - Bittensor Connected: {health_data['bittensor_connected']}")
        print(f"   - Queue Size: {health_data['queue_size']}")
        print(f"   - Pending Tasks: {health_data['pending_tasks']}")
        print(f"   - Processing Tasks: {health_data['processing_tasks']}")
        print(f"   - Completed Tasks: {health_data['completed_tasks']}")
    except Exception as e:
        print(f"❌ Failed to check health: {e}")
        return False
    
    # Step 2: Submit a transcription task
    print("\n2️⃣ Submitting transcription task...")
    try:
        test_audio = create_test_audio()
        
        # Submit task
        task_response = requests.post(
            "http://localhost:8000/api/v1/transcription?source_language=en&priority=normal",
            files={"audio_file": ("test_audio.wav", test_audio, "audio/wav")}
        )
        task_data = task_response.json()
        task_id = task_data['task_id']
        print(f"✅ Task submitted successfully")
        print(f"   - Task ID: {task_id}")
        print(f"   - Status: {task_data['status']}")
        print(f"   - Type: {task_data['task_type']}")
    except Exception as e:
        print(f"❌ Failed to submit task: {e}")
        return False
    
    # Step 3: Wait for task to be picked up
    print("\n3️⃣ Waiting for task to be picked up...")
    time.sleep(5)
    
    # Check task status
    try:
        status_response = requests.get(f"http://localhost:8000/api/v1/task/{task_id}/result")
        status_data = status_response.json()
        print(f"✅ Task Status Checked")
        print(f"   - Status: {status_data['status']}")
        print(f"   - Type: {status_data['task_type']}")
    except Exception as e:
        print(f"❌ Failed to check task status: {e}")
    
    # Step 4: Distribute task to validator
    print("\n4️⃣ Distributing task to validator...")
    try:
        distribute_response = requests.post("http://localhost:8000/api/v1/validator/distribute")
        distribute_data = distribute_response.json()
        print(f"✅ Task distributed to validator")
        print(f"   - Message: {distribute_data['message']}")
        print(f"   - Task Count: {distribute_data['task_count']}")
    except Exception as e:
        print(f"❌ Failed to distribute task: {e}")
        return False
    
    # Step 5: Monitor task processing
    print("\n5️⃣ Monitoring task processing...")
    max_wait_time = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            # Check health status
            health_response = requests.get("http://localhost:8000/api/v1/health")
            health_data = health_response.json()
            
            # Check task status
            status_response = requests.get(f"http://localhost:8000/api/v1/task/{task_id}/result")
            status_data = status_response.json()
            
            print(f"⏱️  Time elapsed: {int(time.time() - start_time)}s")
            print(f"   - Health: {health_data['status']}")
            print(f"   - Queue: {health_data['queue_size']}")
            print(f"   - Pending: {health_data['pending_tasks']}")
            print(f"   - Processing: {health_data['processing_tasks']}")
            print(f"   - Completed: {health_data['completed_tasks']}")
            print(f"   - Task Status: {status_data['status']}")
            
            # Check if task is completed
            if status_data['status'] == 'completed':
                print(f"\n🎉 TASK COMPLETED SUCCESSFULLY!")
                print(f"   - Result: {status_data.get('result', 'N/A')}")
                print(f"   - Processing Time: {status_data.get('processing_time', 'N/A')}")
                print(f"   - Accuracy Score: {status_data.get('accuracy_score', 'N/A')}")
                print(f"   - Speed Score: {status_data.get('speed_score', 'N/A')}")
                return True
            
            # Check if task failed
            if status_data['status'] == 'failed':
                print(f"\n❌ TASK FAILED!")
                print(f"   - Error: {status_data.get('error_message', 'N/A')}")
                return False
            
            # Wait before next check
            time.sleep(10)
            
        except Exception as e:
            print(f"❌ Error during monitoring: {e}")
            time.sleep(10)
    
    print(f"\n⏰ Timeout reached after {max_wait_time}s")
    return False

def test_validator_integration():
    """Test validator integration endpoint"""
    print("\n🔍 Testing validator integration...")
    try:
        integration_response = requests.get("http://localhost:8000/api/v1/validator/integration")
        integration_data = integration_response.json()
        print(f"✅ Validator Integration Checked")
        print(f"   - Network Status: {integration_data.get('network_status', 'N/A')}")
        print(f"   - Available Miners: {len(integration_data.get('available_miners', []))}")
        print(f"   - Pending Tasks: {len(integration_data.get('pending_tasks', []))}")
        print(f"   - Processing Tasks: {len(integration_data.get('processing_tasks', []))}")
        print(f"   - Completed Tasks: {len(integration_data.get('completed_tasks', []))}")
    except Exception as e:
        print(f"❌ Failed to check validator integration: {e}")

def test_tts_workflow():
    """Test the TTS (Text-to-Speech) workflow"""
    print("\n🎵 Testing TTS Workflow")
    print("-" * 40)
    
    # Step 1: Submit a TTS task
    print("\n1️⃣ Submitting TTS task...")
    try:
        test_text = "Hello, this is a test for text to speech conversion. The quick brown fox jumps over the lazy dog."
        
        # Submit TTS task
        tts_response = requests.post(
            "http://localhost:8000/api/v1/tts",
            json={
                "text": test_text,
                "source_language": "en",
                "priority": "normal"
            }
        )
        tts_data = tts_response.json()
        tts_task_id = tts_data['task_id']
        print(f"✅ TTS Task submitted successfully")
        print(f"   - Task ID: {tts_task_id}")
        print(f"   - Status: {tts_data['status']}")
        print(f"   - Type: {tts_data['task_type']}")
        print(f"   - Text: {test_text[:50]}...")
    except Exception as e:
        print(f"❌ Failed to submit TTS task: {e}")
        return False
    
    # Step 2: Wait for task to be picked up
    print("\n2️⃣ Waiting for TTS task to be picked up...")
    time.sleep(5)
    
    # Step 3: Distribute TTS task to validator
    print("\n3️⃣ Distributing TTS task to validator...")
    try:
        distribute_response = requests.post("http://localhost:8000/api/v1/validator/distribute")
        distribute_data = distribute_response.json()
        print(f"✅ TTS Task distributed to validator")
        print(f"   - Message: {distribute_data['message']}")
        print(f"   - Task Count: {distribute_data['task_count']}")
    except Exception as e:
        print(f"❌ Failed to distribute TTS task: {e}")
        return False
    
    # Step 4: Monitor TTS task processing
    print("\n4️⃣ Monitoring TTS task processing...")
    max_wait_time = 180  # 3 minutes for TTS
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            # Check task status
            status_response = requests.get(f"http://localhost:8000/api/v1/task/{tts_task_id}/result")
            status_data = status_response.json()
            
            print(f"⏱️  TTS Time elapsed: {int(time.time() - start_time)}s")
            print(f"   - Status: {status_data['status']}")
            
            # Check if task is completed
            if status_data['status'] == 'completed':
                print(f"\n🎉 TTS TASK COMPLETED SUCCESSFULLY!")
                print(f"   - Result: {status_data.get('result', 'N/A')}")
                print(f"   - Processing Time: {status_data.get('processing_time', 'N/A')}")
                print(f"   - Audio Length: {len(status_data.get('result', ''))} characters (base64)")
                return True
            
            # Check if task failed
            if status_data['status'] == 'failed':
                print(f"\n❌ TTS TASK FAILED!")
                print(f"   - Error: {status_data.get('error_message', 'N/A')}")
                return False
            
            # Wait before next check
            time.sleep(10)
            
        except Exception as e:
            print(f"❌ Error during TTS monitoring: {e}")
            time.sleep(10)
    
    print(f"\n⏰ TTS Timeout reached after {max_wait_time}s")
    return False

def test_summarization_workflow():
    """Test the summarization workflow"""
    print("\n📝 Testing Summarization Workflow")
    print("-" * 40)
    
    # Step 1: Submit a summarization task
    print("\n1️⃣ Submitting summarization task...")
    try:
        test_text = """This is a comprehensive text that needs to be summarized. It contains multiple sentences and paragraphs with various topics including artificial intelligence, machine learning, and natural language processing. The summarization process should extract the key points and create a concise version while preserving the essential information. This text demonstrates the ability of the system to handle longer inputs and produce meaningful summaries."""
        
        # Submit summarization task
        summary_response = requests.post(
            "http://localhost:8000/api/v1/summarization",
            json={
                "text": test_text,
                "source_language": "en",
                "priority": "normal"
            }
        )
        summary_data = summary_response.json()
        summary_task_id = summary_data['task_id']
        print(f"✅ Summarization Task submitted successfully")
        print(f"   - Task ID: {summary_task_id}")
        print(f"   - Status: {summary_data['status']}")
        print(f"   - Type: {summary_data['task_type']}")
        print(f"   - Text Length: {len(test_text)} characters")
    except Exception as e:
        print(f"❌ Failed to submit summarization task: {e}")
        return False
    
    # Step 2: Wait for task to be picked up
    print("\n2️⃣ Waiting for summarization task to be picked up...")
    time.sleep(5)
    
    # Step 3: Distribute summarization task to validator
    print("\n3️⃣ Distributing summarization task to validator...")
    try:
        distribute_response = requests.post("http://localhost:8000/api/v1/validator/distribute")
        distribute_data = distribute_response.json()
        print(f"✅ Summarization Task distributed to validator")
        print(f"   - Message: {distribute_data['message']}")
        print(f"   - Task Count: {distribute_data['task_count']}")
    except Exception as e:
        print(f"❌ Failed to distribute summarization task: {e}")
        return False
    
    # Step 4: Monitor summarization task processing
    print("\n4️⃣ Monitoring summarization task processing...")
    max_wait_time = 180  # 3 minutes for summarization
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            # Check task status
            status_response = requests.get(f"http://localhost:8000/api/v1/task/{summary_task_id}/result")
            status_data = status_response.json()
            
            print(f"⏱️  Summarization Time elapsed: {int(time.time() - start_time)}s")
            print(f"   - Status: {status_data['status']}")
            
            # Check if task is completed
            if status_data['status'] == 'completed':
                print(f"\n🎉 SUMMARIZATION TASK COMPLETED SUCCESSFULLY!")
                print(f"   - Result: {status_data.get('result', 'N/A')}")
                print(f"   - Processing Time: {status_data.get('processing_time', 'N/A')}")
                print(f"   - Summary Length: {len(status_data.get('result', ''))} characters")
                return True
            
            # Check if task failed
            if status_data['status'] == 'failed':
                print(f"\n❌ SUMMARIZATION TASK FAILED!")
                print(f"   - Error: {status_data.get('error_message', 'N/A')}")
                return False
            
            # Wait before next check
            time.sleep(10)
            
        except Exception as e:
            print(f"❌ Error during summarization monitoring: {e}")
            time.sleep(10)
    
    print(f"\n⏰ Summarization timeout reached after {max_wait_time}s")
    return False

if __name__ == "__main__":
    print("🔧 Complete Workflow Debug Test - All Models")
    print("=" * 60)
    
    # Test validator integration
    test_validator_integration()
    
    # Test all workflows
    print("\n🚀 Testing All Workflows")
    print("=" * 60)
    
    # Test 1: Transcription
    print("\n🎯 TEST 1: TRANSCRIPTION WORKFLOW")
    transcription_success = test_complete_workflow()
    
    # Test 2: TTS
    print("\n🎯 TEST 2: TTS WORKFLOW")
    tts_success = test_tts_workflow()
    
    # Test 3: Summarization
    print("\n🎯 TEST 3: SUMMARIZATION WORKFLOW")
    summarization_success = test_summarization_workflow()
    
    # Summary of results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"🎯 Transcription: {'✅ PASSED' if transcription_success else '❌ FAILED'}")
    print(f"🎵 TTS: {'✅ PASSED' if tts_success else '❌ FAILED'}")
    print(f"📝 Summarization: {'✅ PASSED' if summarization_success else '❌ FAILED'}")
    
    if transcription_success and tts_success and summarization_success:
        print("\n🎉 ALL WORKFLOWS PASSED! Complete system is working correctly.")
    else:
        print("\n❌ SOME WORKFLOWS FAILED! Check the logs for issues.")
    
    print("\n" + "=" * 60)
    print("🏁 All tests completed")
