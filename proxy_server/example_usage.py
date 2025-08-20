#!/usr/bin/env python3
"""
Example Usage Script for Bittensor Audio Processing Proxy Server
Demonstrates how to use the service-specific endpoints
"""

import requests
import time
import json
from pathlib import Path

# Server configuration
SERVER_URL = "http://localhost:8000"
API_BASE = f"{SERVER_URL}/api/v1"

def create_sample_audio():
    """Create a sample audio file for testing"""
    try:
        import numpy as np
        import soundfile as sf
        import io
        
        # Generate 3 seconds of 440 Hz sine wave
        sample_rate = 16000
        duration = 3.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * 440 * t) * 0.3
        
        # Save to bytes
        audio_bytes = io.BytesIO()
        sf.write(audio_bytes, audio_data, sample_rate, format='WAV')
        audio_bytes.seek(0)
        
        return audio_bytes.read(), "sample_audio.wav"
    except ImportError:
        print("⚠️  numpy or soundfile not available, using dummy audio")
        # Create a dummy WAV file
        dummy_audio = b"RIFF" + b"\x00" * 40 + b"WAVE"
        return dummy_audio, "sample_audio.wav"

def submit_transcription_task():
    """Submit a transcription task"""
    print("🎵 Submitting transcription task...")
    
    try:
        # Create sample audio
        audio_content, filename = create_sample_audio()
        
        # Prepare form data
        files = {'audio_file': (filename, audio_content, 'audio/wav')}
        data = {
            'source_language': 'en',
            'priority': 'normal'
        }
        
        response = requests.post(f"{API_BASE}/transcription", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Transcription task submitted: {result['task_id']}")
            print(f"   Status: {result['status']}")
            print(f"   Estimated completion: {result['estimated_completion_time']}s")
            return result['task_id']
        else:
            print(f"❌ Transcription submission failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Transcription error: {str(e)}")
        return None

def submit_tts_task():
    """Submit a TTS task"""
    print("\n🔊 Submitting TTS task...")
    
    try:
        tts_data = {
            "text": "Hello! This is a test of the text-to-speech service. The system should convert this text into audio using the Bittensor network.",
            "source_language": "en",
            "priority": "normal"
        }
        
        response = requests.post(f"{API_BASE}/tts", json=tts_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ TTS task submitted: {result['task_id']}")
            print(f"   Status: {result['status']}")
            print(f"   Estimated completion: {result['estimated_completion_time']}s")
            return result['task_id']
        else:
            print(f"❌ TTS submission failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ TTS error: {str(e)}")
        return None

def submit_summarization_task():
    """Submit a summarization task"""
    print("\n📝 Submitting summarization task...")
    
    try:
        long_text = """
        Artificial intelligence (AI) represents one of the most transformative technologies of our time. 
        It encompasses machine learning, deep learning, natural language processing, computer vision, and robotics.
        
        Machine learning, a subset of AI, enables computers to learn and improve from experience without being explicitly programmed. 
        Deep learning, a subset of machine learning, uses neural networks with multiple layers to model complex patterns in data.
        
        Natural language processing allows computers to understand, interpret, and generate human language. 
        Computer vision enables machines to interpret and make decisions based on visual information.
        
        The applications of AI are vast and growing, from healthcare and finance to transportation and entertainment. 
        In healthcare, AI helps diagnose diseases, predict patient outcomes, and discover new drugs. 
        In finance, it detects fraud, optimizes trading strategies, and provides personalized financial advice.
        
        However, AI also presents challenges including ethical concerns, job displacement, and the need for robust safety measures. 
        As AI continues to advance, it's crucial to develop it responsibly and ensure it benefits all of humanity.
        """
        
        summarization_data = {
            "text": long_text.strip(),
            "source_language": "en",
            "priority": "normal"
        }
        
        response = requests.post(f"{API_BASE}/summarization", json=summarization_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Summarization task submitted: {result['task_id']}")
            print(f"   Status: {result['status']}")
            print(f"   Estimated completion: {result['estimated_completion_time']}s")
            return result['task_id']
        else:
            print(f"❌ Summarization submission failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Summarization error: {str(e)}")
        return None

def check_task_status(task_id, task_type):
    """Check the status of a task"""
    print(f"\n🔍 Checking {task_type} task status: {task_id}")
    
    try:
        response = requests.get(f"{API_BASE}/tasks/{task_id}")
        
        if response.status_code == 200:
            data = response.json()
            status = data['status']
            print(f"   Status: {status}")
            
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
            
            return False  # Not completed yet
            
        else:
            print(f"❌ Status check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Status check error: {str(e)}")
        return False

def monitor_tasks(task_ids):
    """Monitor multiple tasks until completion"""
    print(f"\n⏳ Monitoring {len(task_ids)} tasks for completion...")
    
    completed_tasks = {}
    max_attempts = 30  # Maximum monitoring attempts
    
    for attempt in range(max_attempts):
        print(f"\n📊 Monitoring attempt {attempt + 1}/{max_attempts}")
        
        for task_type, task_id in task_ids.items():
            if task_id not in completed_tasks:
                if check_task_status(task_id, task_type):
                    completed_tasks[task_id] = task_type
                    print(f"✅ {task_type.title()} task completed!")
        
        # Check if all tasks are completed
        if len(completed_tasks) == len(task_ids):
            print("\n🎉 All tasks completed successfully!")
            break
        
        # Wait before next check
        print("   Waiting 10 seconds before next check...")
        time.sleep(10)
    
    if len(completed_tasks) < len(task_ids):
        print(f"\n⚠️  {len(task_ids) - len(completed_tasks)} tasks did not complete within the monitoring period")
    
    return completed_tasks

def get_queue_stats():
    """Get current queue statistics"""
    print("\n📊 Getting queue statistics...")
    
    try:
        response = requests.get(f"{API_BASE}/health")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Queue size: {data['queue_size']}")
            print(f"   Pending tasks: {data['pending_tasks']}")
            print(f"   Processing tasks: {data['processing_tasks']}")
            print(f"   Completed tasks: {data['completed_tasks']}")
            print(f"   Failed tasks: {data['failed_tasks']}")
            print(f"   Bittensor connected: {data['bittensor_connected']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")

def main():
    """Main example function"""
    print("🚀 Bittensor Audio Processing Proxy Server - Example Usage")
    print("=" * 70)
    
    # Check if server is running
    try:
        response = requests.get(f"{SERVER_URL}/docs", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not responding properly")
            return
    except:
        print("❌ Server is not running. Please start the server first:")
        print("   cd proxy_server")
        print("   python start_server.py")
        return
    
    print("✅ Server is running")
    
    # Submit tasks
    task_ids = {}
    
    # Submit transcription task
    transcription_id = submit_transcription_task()
    if transcription_id:
        task_ids['transcription'] = transcription_id
    
    # Submit TTS task
    tts_id = submit_tts_task()
    if tts_id:
        task_ids['tts'] = tts_id
    
    # Submit summarization task
    summarization_id = submit_summarization_task()
    if summarization_id:
        task_ids['summarization'] = summarization_id
    
    if not task_ids:
        print("❌ No tasks were submitted successfully")
        return
    
    # Show initial queue stats
    get_queue_stats()
    
    # Monitor tasks
    print(f"\n🎯 Monitoring {len(task_ids)} submitted tasks...")
    completed_tasks = monitor_tasks(task_ids)
    
    # Show final queue stats
    get_queue_stats()
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 Example Usage Summary")
    print("=" * 70)
    
    print(f"✅ Successfully submitted {len(task_ids)} tasks:")
    for task_type, task_id in task_ids.items():
        status = "✅ Completed" if task_id in completed_tasks else "⏳ Still processing"
        print(f"   {task_type.title()}: {task_id[:8]}... - {status}")
    
    print(f"\n🎉 Example completed! {len(completed_tasks)}/{len(task_ids)} tasks finished successfully.")
    print("\n💡 You can now use these endpoints in your applications:")
    print("   - POST /api/v1/transcription - For audio transcription")
    print("   - POST /api/v1/tts - For text-to-speech")
    print("   - POST /api/v1/summarization - For text summarization")
    print("   - GET /api/v1/tasks/{id} - To check task status")

if __name__ == "__main__":
    main()
