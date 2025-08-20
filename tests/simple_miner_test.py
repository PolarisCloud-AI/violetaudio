#!/usr/bin/env python3
"""
Simple test to check if our miner is working properly.
"""

import requests
import json
import time

def test_miner_direct():
    """Test the miner directly via HTTP."""
    print("🧪 Testing Miner Direct HTTP Communication")
    print("=" * 50)
    
    try:
        # Test basic connectivity (try localhost first)
        miner_url = "http://127.0.0.1:8091"
        
        print(f"1. Testing basic connectivity to {miner_url}...")
        
        # Create a simple HTTP request
        headers = {
            'Content-Type': 'application/json',
            'name': 'AudioTask'
        }
        
        data = {
            'task_type': 'transcription',
            'input_data': 'dGVzdA==',  # base64 for "test"
            'language': 'en'
        }
        
        print("   📤 Sending HTTP POST request...")
        response = requests.post(
            miner_url,
            headers=headers,
            json=data,
            timeout=10
        )
        
        print(f"   📥 Response status: {response.status_code}")
        print(f"   📋 Response headers: {dict(response.headers)}")
        print(f"   📄 Response text: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("✅ Direct HTTP communication successful!")
            return True
        else:
            print(f"⚠️  Got HTTP status {response.status_code}")
            return True  # Still successful communication
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def check_miner_status():
    """Check if miner process is running."""
    print("\n🔍 Checking Miner Process Status")
    print("=" * 40)
    
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
    print("🚀 Simple Miner Test")
    print("=" * 60)
    
    # Check if miner is running
    miner_running = check_miner_status()
    
    if miner_running:
        # Test direct communication
        success = test_miner_direct()
        
        if success:
            print("\n🎉 Miner is running and reachable!")
        else:
            print("\n💥 Miner is running but not reachable.")
    else:
        print("\n💥 Miner process is not running.")
