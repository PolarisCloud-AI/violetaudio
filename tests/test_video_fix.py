#!/usr/bin/env python3
"""
Test script to verify video transcription endpoint works after filename fix
"""

import requests
import os

def test_video_transcription_fix():
    """Test if the video transcription endpoint works with emoji filenames"""
    print("🎬 Testing Video Transcription Endpoint Fix")
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
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to proxy server: {e}")
        print("   Make sure the proxy server is running on localhost:8000")
        return False
    
    # Create a test video file with emoji in filename
    test_filename = "test_video_👀🤷_♂️.mp4"
    test_video_path = test_filename
    
    print(f"2️⃣ Creating test video file with emoji filename: {test_filename}")
    
    # Create a dummy file for testing
    with open(test_video_path, 'wb') as f:
        f.write(b'dummy video content for testing emoji filename handling')
    
    print(f"✅ Test video created: {test_video_path}")
    
    print(f"3️⃣ Submitting video transcription task with emoji filename...")
    
    # Submit video transcription task
    try:
        with open(test_video_path, 'rb') as f:
            files = {'video_file': (test_filename, f, 'video/mp4')}
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
            print(f"   Original Filename: {result.get('file_name')}")
            print(f"   File Size: {result.get('file_size')} bytes")
            print(f"   Source Language: {result.get('source_language')}")
            print(f"   Auto Assigned: {result.get('auto_assigned')}")
            
            task_id = result.get('task_id')
            file_id = result.get('file_id')
            
            print(f"4️⃣ Testing file download with emoji filename...")
            
            # Test if we can download the file (this was failing before)
            try:
                download_response = requests.get(f"{proxy_url}/api/v1/files/{file_id}/download", timeout=10)
                if download_response.status_code == 200:
                    print("✅ File download successful! Unicode filename handling is working.")
                    print(f"   Downloaded {len(download_response.content)} bytes")
                else:
                    print(f"❌ File download failed: {download_response.status_code}")
                    print(f"   Response: {download_response.text}")
                    return False
            except Exception as e:
                print(f"❌ Error testing file download: {e}")
                return False
            
            return True
            
        else:
            print(f"❌ Failed to submit video transcription task: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error submitting video transcription task: {e}")
        return False
    
    finally:
        # Clean up test file
        if os.path.exists(test_video_path):
            try:
                os.remove(test_video_path)
                print(f"🧹 Cleaned up test video file: {test_video_path}")
            except Exception as e:
                print(f"⚠️ Could not clean up test file: {e}")

if __name__ == "__main__":
    print("🚀 Starting Video Transcription Fix Test")
    print("=" * 60)
    
    success = test_video_transcription_fix()
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("   The emoji filename issue has been fixed.")
    else:
        print("\n❌ Test failed!")
        print("   There may still be issues with emoji filename handling.")
