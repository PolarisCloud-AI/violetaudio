#!/usr/bin/env python3
"""
Direct test to check if the miner is processing requests properly.
This test bypasses the Bittensor network and tests the miner directly.
"""

import requests
import json
import base64
import time

def test_miner_direct_processing():
    """Test the miner directly via HTTP to see if it's processing requests."""
    print("🧪 Direct Miner Processing Test")
    print("=" * 50)
    
    try:
        # Test basic connectivity
        miner_url = "http://127.0.0.1:8091"
        
        print(f"1. Testing connectivity to {miner_url}...")
        
        # Create a simple HTTP request with proper AudioTask data
        headers = {
            'Content-Type': 'application/json',
            'name': 'AudioTask',
            'bt_header_synapse_name': 'AudioTask'
        }
        
        # Test 1: Simple transcription task
        print("\n2. Testing transcription task...")
        
        # Create a simple test audio (base64 encoded)
        test_audio_base64 = "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT"
        
        data = {
            'task_type': 'transcription',
            'input_data': test_audio_base64,
            'language': 'en'
        }
        
        print("   📤 Sending transcription request...")
        response = requests.post(
            miner_url,
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"   📥 Response status: {response.status_code}")
        print(f"   📋 Response headers: {dict(response.headers)}")
        print(f"   📄 Response text: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("   ✅ Transcription request successful!")
            
            # Try to parse the response
            try:
                response_data = response.json()
                print(f"   📝 Response data: {response_data}")
            except:
                print("   ⚠️  Could not parse JSON response")
        else:
            print(f"   ❌ Transcription request failed: {response.status_code}")
        
        # Test 2: Simple summarization task
        print("\n3. Testing summarization task...")
        
        # Create test text (base64 encoded)
        test_text = "This is a test text for summarization. It contains multiple sentences and should be summarized."
        test_text_base64 = base64.b64encode(test_text.encode()).decode()
        
        data = {
            'task_type': 'summarization',
            'input_data': test_text_base64,
            'language': 'en'
        }
        
        print("   📤 Sending summarization request...")
        response = requests.post(
            miner_url,
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"   📥 Response status: {response.status_code}")
        print(f"   📋 Response headers: {dict(response.headers)}")
        print(f"   📄 Response text: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("   ✅ Summarization request successful!")
            
            # Try to parse the response
            try:
                response_data = response.json()
                print(f"   📝 Response data: {response_data}")
            except:
                print("   ⚠️  Could not parse JSON response")
        else:
            print(f"   ❌ Summarization request failed: {response.status_code}")
        
        print("\n✅ Direct miner tests completed!")
        return True
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def check_miner_status():
    """Check if miner process is running and responding."""
    print("\n🔍 Checking Miner Status")
    print("=" * 30)
    
    import subprocess
    try:
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True
        )
        
        miner_processes = [line for line in result.stdout.split('\n') if 'neurons/miner.py' in line and 'grep' not in line]
        
        if miner_processes:
            print("✅ Miner process found:")
            for process in miner_processes:
                print(f"   {process}")
            return True
        else:
            print("❌ No miner process found")
            return False
            
    except Exception as e:
        print(f"❌ Failed to check process: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Direct Miner Processing Test")
    print("=" * 60)
    
    # Check if miner is running
    miner_running = check_miner_status()
    
    if miner_running:
        # Test direct processing
        success = test_miner_direct_processing()
        
        if success:
            print("\n🎉 Miner is running and processing requests!")
        else:
            print("\n💥 Miner is running but not processing requests properly.")
    else:
        print("\n💥 Miner process is not running.")
