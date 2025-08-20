#!/usr/bin/env python3
"""
Test script for the Bittensor Audio Processing Proxy Server
Tests the new service-specific endpoints for transcription, TTS, and summarization
"""

import requests
import base64
import time
import json
import os
from pathlib import Path

# Server configuration
SERVER_URL = "http://localhost:8000"
API_BASE = f"{SERVER_URL}/api/v1"

def test_health_check():
    """Test the health check endpoint"""
    print("🏥 Testing health check...")
    
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"   Bittensor connected: {data['bittensor_connected']}")
            print(f"   Queue size: {data['queue_size']}")
            print(f"   Pending tasks: {data['pending_tasks']}")
            print(f"   Processing tasks: {data['processing_tasks']}")
            print(f"   Completed tasks: {data['completed_tasks']}")
            print(f"   Failed tasks: {data['failed_tasks']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        return False

def create_test_audio():
    """Create a simple test audio file for transcription testing"""
    try:
        # Create a simple WAV file with sine wave
        import numpy as np
        import soundfile as sf
        import io
        
        # Generate 2 seconds of 440 Hz sine wave
        sample_rate = 16000
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * 440 * t) * 0.3
        
        # Save to bytes
        audio_bytes = io.BytesIO()
        sf.write(audio_bytes, audio_data, sample_rate, format='WAV')
        audio_bytes.seek(0)
        
        return audio_bytes.read(), "test_audio.wav"
    except ImportError:
        # Fallback: create a dummy audio file
        dummy_audio = b"RIFF" + b"\x00" * 40 + b"WAVE"
        return dummy_audio, "test_audio.wav"

def test_transcription_endpoint():
    """Test the transcription endpoint"""
    print("\n🎵 Testing transcription endpoint...")
    
    try:
        # Create test audio file
        audio_content, filename = create_test_audio()
        
        # Prepare form data
        files = {'audio_file': (filename, audio_content, 'audio/wav')}
        data = {
            'source_language': 'en',
            'priority': 'normal'
        }
        
        response = requests.post(f"{API_BASE}/transcription", files=files, data=data)
        
        if response.status_code == 200:
            data = response.json()
            task_id = data['task_id']
            print(f"✅ Transcription task submitted successfully: {task_id}")
            print(f"   Status: {data['status']}")
            print(f"   Task type: {data['task_type']}")
            print(f"   Language: {data['source_language']}")
            print(f"   Estimated completion: {data['estimated_completion_time']}s")
            return task_id
        else:
            print(f"❌ Transcription task submission failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Transcription test error: {str(e)}")
        return None

def test_tts_endpoint():
    """Test the TTS endpoint"""
    print("\n🔊 Testing TTS endpoint...")
    
    try:
        # Prepare request data
        tts_data = {
            "text": "Hello, this is a test for text-to-speech conversion. The system should process this text and convert it to audio.",
            "source_language": "en",
            "priority": "normal"
        }
        
        response = requests.post(f"{API_BASE}/tts", json=tts_data)
        
        if response.status_code == 200:
            data = response.json()
            task_id = data['task_id']
            print(f"✅ TTS task submitted successfully: {task_id}")
            print(f"   Status: {data['status']}")
            print(f"   Task type: {data['task_type']}")
            print(f"   Language: {data['source_language']}")
            print(f"   Estimated completion: {data['estimated_completion_time']}s")
            return task_id
        else:
            print(f"❌ TTS task submission failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ TTS test error: {str(e)}")
        return None

def test_summarization_endpoint():
    """Test the summarization endpoint"""
    print("\n📝 Testing summarization endpoint...")
    
    try:
        # Prepare request data with longer text for summarization
        long_text = """
        Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to the natural intelligence displayed by humans and animals. 
        Leading AI textbooks define the field as the study of "intelligent agents": any device that perceives its environment and takes actions that maximize its chance of successfully achieving its goals. 
        Colloquially, the term "artificial intelligence" is often used to describe machines that mimic "cognitive" functions that humans associate with the human mind, such as "learning" and "problem solving".
        
        As machines become increasingly capable, tasks considered to require "intelligence" are often removed from the definition of AI, a phenomenon known as the AI effect. 
        A quip in Tesler's Theorem says "AI is whatever hasn't been done yet." For instance, optical character recognition is frequently excluded from things considered to be AI, having become a routine technology.
        
        Modern machine learning capabilities, however, have achieved narrow AI surpassing humans in specific tasks such as playing chess, proving mathematical theorems, driving cars, and detecting fraudulent credit card transactions.
        """
        
        summarization_data = {
            "text": long_text.strip(),
            "source_language": "en",
            "priority": "normal"
        }
        
        response = requests.post(f"{API_BASE}/summarization", json=summarization_data)
        
        if response.status_code == 200:
            data = response.json()
            task_id = data['task_id']
            print(f"✅ Summarization task submitted successfully: {task_id}")
            print(f"   Status: {data['status']}")
            print(f"   Task type: {data['task_type']}")
            print(f"   Language: {data['source_language']}")
            print(f"   Estimated completion: {data['estimated_completion_time']}s")
            return task_id
        else:
            print(f"❌ Summarization task submission failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Summarization test error: {str(e)}")
        return False

def test_task_status_check(task_id, task_type):
    """Test task status checking"""
    print(f"\n🔍 Testing task status check for {task_type} task {task_id}...")
    
    if not task_id:
        print("❌ No task ID provided")
        return False
    
    try:
        # Wait a bit for processing to start
        time.sleep(2)
        
        # Check status multiple times
        for attempt in range(15):  # Increased attempts for longer processing
            response = requests.get(f"{API_BASE}/tasks/{task_id}")
            
            if response.status_code == 200:
                data = response.json()
                status = data['status']
                print(f"   Attempt {attempt + 1}: Status = {status}")
                
                if status == 'completed':
                    print("✅ Task completed successfully!")
                    if data.get('result'):
                        result = data['result']
                        print(f"   Model used: {result.get('model_used', 'Unknown')}")
                        print(f"   Processing time: {result.get('processing_time', 'Unknown')}s")
                        print(f"   Accuracy score: {result.get('accuracy_score', 'Unknown')}")
                        print(f"   Speed score: {result.get('speed_score', 'Unknown')}")
                        print(f"   Miner UID: {result.get('miner_uid', 'Unknown')}")
                    return True
                elif status == 'failed':
                    print(f"❌ Task failed: {data.get('error_message', 'Unknown error')}")
                    return False
                elif status == 'processing':
                    print("   Task is being processed...")
                elif status == 'pending':
                    print("   Task is pending...")
                
                # Wait before next check
                time.sleep(3)
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return False
        
        print("⏰ Task status check timed out")
        return False
        
    except Exception as e:
        print(f"❌ Task status check error: {str(e)}")
        return False

def test_list_tasks():
    """Test listing tasks"""
    print("\n📋 Testing task listing...")
    
    try:
        response = requests.get(f"{API_BASE}/tasks?limit=5")
        
        if response.status_code == 200:
            tasks = response.json()
            print(f"✅ Retrieved {len(tasks)} tasks")
            
            for i, task in enumerate(tasks[:3]):  # Show first 3
                print(f"   Task {i+1}: {task.get('task_id', 'Unknown')[:8]}... - {task.get('task_type', 'Unknown')} - {task.get('status', 'Unknown')}")
            
            return True
        else:
            print(f"❌ Task listing failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Task listing error: {str(e)}")
        return False

def test_invalid_requests():
    """Test invalid request handling"""
    print("\n🚫 Testing invalid request handling...")
    
    tests_passed = 0
    total_tests = 0
    
    try:
        # Test 1: Invalid language for transcription
        total_tests += 1
        print("   Testing invalid language for transcription...")
        files = {'audio_file': ('test.wav', b'test', 'audio/wav')}
        data = {'source_language': 'invalid_lang', 'priority': 'normal'}
        
        response = requests.post(f"{API_BASE}/transcription", files=files, data=data)
        if response.status_code == 422:  # Validation error
            print("     ✅ Invalid language properly rejected")
            tests_passed += 1
        else:
            print(f"     ❌ Invalid language should have been rejected: {response.status_code}")
        
        # Test 2: Empty text for TTS
        total_tests += 1
        print("   Testing empty text for TTS...")
        tts_data = {"text": "", "source_language": "en", "priority": "normal"}
        
        response = requests.post(f"{API_BASE}/tts", json=tts_data)
        if response.status_code == 422:  # Validation error
            print("     ✅ Empty text properly rejected")
            tests_passed += 1
        else:
            print(f"     ❌ Empty text should have been rejected: {response.status_code}")
        
        # Test 3: Text too short for summarization
        total_tests += 1
        print("   Testing text too short for summarization...")
        summarization_data = {"text": "Too short", "source_language": "en", "priority": "normal"}
        
        response = requests.post(f"{API_BASE}/summarization", json=summarization_data)
        if response.status_code == 422:  # Validation error
            print("     ✅ Short text properly rejected")
            tests_passed += 1
        else:
            print(f"     ❌ Short text should have been rejected: {response.status_code}")
        
        print(f"   📊 Invalid request tests: {tests_passed}/{total_tests} passed")
        return tests_passed == total_tests
        
    except Exception as e:
        print(f"❌ Invalid request test error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🧪 Bittensor Audio Processing Proxy Server Test Suite")
    print("=" * 70)
    
    # Check if server is running
    print("🔍 Checking if server is running...")
    try:
        response = requests.get(f"{SERVER_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print("❌ Server is not responding properly")
            return
    except:
        print("❌ Server is not running. Please start the server first:")
        print("   cd proxy_server")
        print("   python start_server.py")
        return
    
    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("Transcription Endpoint", test_transcription_endpoint),
        ("TTS Endpoint", test_tts_endpoint),
        ("Summarization Endpoint", test_summarization_endpoint),
        ("Invalid Request Handling", test_invalid_requests),
        ("List Tasks", test_list_tasks)
    ]
    
    results = []
    task_ids = {}
    
    for test_name, test_func in tests:
        try:
            if "Endpoint" in test_name:
                result = test_func()
                if result:
                    if "transcription" in test_name.lower():
                        task_ids['transcription'] = result
                    elif "tts" in test_name.lower():
                        task_ids['tts'] = result
                    elif "summarization" in test_name.lower():
                        task_ids['summarization'] = result
                    results.append((test_name, "PASS"))
                else:
                    results.append((test_name, "FAIL"))
            else:
                result = test_func()
                results.append((test_name, "PASS" if result else "FAIL"))
                
        except Exception as e:
            print(f"❌ {test_name} test error: {str(e)}")
            results.append((test_name, "ERROR"))
    
    # Test task status checking for submitted tasks
    if task_ids:
        print("\n⏳ Waiting for tasks to process...")
        time.sleep(5)  # Give tasks time to start processing
        
        for task_type, task_id in task_ids.items():
            test_name = f"{task_type.title()} Status Check"
            try:
                result = test_task_status_check(task_id, task_type)
                results.append((test_name, "PASS" if result else "FAIL"))
            except Exception as e:
                print(f"❌ {test_name} test error: {str(e)}")
                results.append((test_name, "ERROR"))
    
    # Print results summary
    print("\n" + "=" * 70)
    print("📊 Test Results Summary")
    print("=" * 70)
    
    passed = 0
    failed = 0
    errors = 0
    
    for test_name, result in results:
        status_emoji = {
            "PASS": "✅",
            "FAIL": "❌",
            "ERROR": "💥"
        }
        
        print(f"{status_emoji.get(result, '❓')} {test_name}: {result}")
        
        if result == "PASS":
            passed += 1
        elif result == "FAIL":
            failed += 1
        else:
            errors += 1
    
    print(f"\n📈 Summary: {passed} passed, {failed} failed, {errors} errors")
    
    if failed == 0 and errors == 0:
        print("🎉 All tests passed! The proxy server is working correctly.")
        print("\n🚀 Your service-specific endpoints are ready:")
        print("   ✅ POST /api/v1/transcription - Audio transcription")
        print("   ✅ POST /api/v1/tts - Text-to-speech")
        print("   ✅ POST /api/v1/summarization - Text summarization")
        print("   ✅ GET /api/v1/tasks/{id} - Task status")
        print("   ✅ GET /api/v1/tasks - List all tasks")
        print("   ✅ GET /api/v1/health - Health check")
    else:
        print("⚠️  Some tests failed. Please check the server logs for details.")

if __name__ == "__main__":
    main()
