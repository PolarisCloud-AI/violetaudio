#!/usr/bin/env python3
"""
Test script for video transcription endpoint
"""

import requests
import time
import os
from pathlib import Path

def test_video_transcription_endpoint():
    """Test the video transcription endpoint"""
    print("🎬 Testing Video Transcription Endpoint")
    print("=" * 50)
    
    # Proxy server URL
    proxy_url = "http://localhost:8000"
    
    try:
        print("1️⃣ Checking if proxy server is running...")
        response = requests.get(f"{proxy_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Proxy server is running")
        else:
            print(f"⚠️ Proxy server responded with status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to proxy server: {e}")
        print("   Make sure the proxy server is running on localhost:8000")
        return False
    
    # Create a simple test video file (or use existing one)
    test_video_path = "test_video.mp4"
    
    if not os.path.exists(test_video_path):
        print(f"2️⃣ Creating test video file: {test_video_path}")
        print("   Note: This creates a minimal test video file")
        
        # Create a minimal test video using ffmpeg if available
        try:
            import subprocess
            # Create a 5-second test video with audio
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=320x240:rate=1',
                '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=5',
                '-c:v', 'libx264', '-c:a', 'aac', '-shortest',
                test_video_path, '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"✅ Test video created: {test_video_path}")
            else:
                print(f"⚠️ Failed to create test video: {result.stderr}")
                print("   Will use a dummy file for testing")
                # Create a dummy file
                with open(test_video_path, 'wb') as f:
                    f.write(b'dummy video content for testing')
        except Exception as e:
            print(f"⚠️ Could not create test video: {e}")
            print("   Creating dummy file for testing")
            with open(test_video_path, 'wb') as f:
                f.write(b'dummy video content for testing')
    else:
        print(f"✅ Test video file exists: {test_video_path}")
    
    print(f"3️⃣ Submitting video transcription task...")
    
    # Submit video transcription task
    try:
        with open(test_video_path, 'rb') as f:
            files = {'video_file': (test_video_path, f, 'video/mp4')}
            data = {
                'source_language': 'en',
                'priority': 'normal'
            }
            
            response = requests.post(
                f"{proxy_url}/api/v1/video-transcription",
                files=files,
                data=data,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Video transcription task submitted successfully!")
            print(f"   Task ID: {result.get('task_id')}")
            print(f"   File ID: {result.get('file_id')}")
            print(f"   File Name: {result.get('file_name')}")
            print(f"   File Size: {result.get('file_size')} bytes")
            print(f"   Source Language: {result.get('source_language')}")
            print(f"   Auto Assigned: {result.get('auto_assigned')}")
            
            task_id = result.get('task_id')
            
            # Wait a bit for processing
            print("4️⃣ Waiting for task processing...")
            time.sleep(5)
            
            # Check task status
            print("5️⃣ Checking task status...")
            try:
                status_response = requests.get(f"{proxy_url}/api/v1/tasks/{task_id}", timeout=10)
                if status_response.status_code == 200:
                    task_status = status_response.json()
                    print(f"✅ Task status retrieved:")
                    print(f"   Status: {task_status.get('status')}")
                    print(f"   Task Type: {task_status.get('task_type')}")
                    print(f"   Created At: {task_status.get('created_at')}")
                else:
                    print(f"⚠️ Could not retrieve task status: {status_response.status_code}")
            except Exception as e:
                print(f"⚠️ Error checking task status: {e}")
            
            return True
            
        else:
            print(f"❌ Failed to submit video transcription task: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error submitting video transcription task: {e}")
        return False
    
    finally:
        # Clean up test file if we created it
        if os.path.exists(test_video_path) and test_video_path == "test_video.mp4":
            try:
                os.remove(test_video_path)
                print(f"🧹 Cleaned up test video file: {test_video_path}")
            except Exception as e:
                print(f"⚠️ Could not clean up test file: {e}")

def test_miner_endpoint():
    """Test the miner endpoint for video transcription tasks"""
    print("\n🔧 Testing Miner Endpoint for Video Transcription")
    print("=" * 50)
    
    proxy_url = "http://localhost:8000"
    
    try:
        print("1️⃣ Getting available tasks...")
        response = requests.get(f"{proxy_url}/api/v1/tasks", timeout=10)
        
        if response.status_code == 200:
            tasks = response.json()
            video_tasks = [t for t in tasks if t.get('task_type') == 'video_transcription']
            
            if video_tasks:
                print(f"✅ Found {len(video_tasks)} video transcription tasks")
                task = video_tasks[0]
                task_id = task.get('task_id')
                
                print(f"2️⃣ Testing miner endpoint for task {task_id}...")
                
                # Test miner endpoint
                miner_response = requests.get(
                    f"{proxy_url}/api/v1/miner/video-transcription/{task_id}",
                    timeout=10
                )
                
                if miner_response.status_code == 200:
                    miner_data = miner_response.json()
                    print("✅ Miner endpoint working correctly!")
                    print(f"   Task ID: {miner_data.get('task_id')}")
                    print(f"   File Content Available: {bool(miner_data.get('file_content'))}")
                    print(f"   File Metadata: {miner_data.get('file_metadata', {}).get('file_name')}")
                else:
                    print(f"❌ Miner endpoint failed: {miner_response.status_code}")
                    print(f"   Response: {miner_response.text}")
                    
            else:
                print("⚠️ No video transcription tasks found")
                print("   Create a task first using the main endpoint")
                
        else:
            print(f"❌ Could not retrieve tasks: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing miner endpoint: {e}")

if __name__ == "__main__":
    print("🚀 Starting Video Transcription Endpoint Tests")
    print("=" * 60)
    
    # Test main endpoint
    success = test_video_transcription_endpoint()
    
    if success:
        print("\n🎉 Main endpoint test completed successfully!")
        
        # Test miner endpoint
        test_miner_endpoint()
        
        print("\n✅ All tests completed!")
    else:
        print("\n❌ Main endpoint test failed!")
        print("   Check the proxy server logs for more details")
