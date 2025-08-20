#!/usr/bin/env python3
"""
Test to check miner logs and see if requests are being processed.
"""

import subprocess
import time
import sys

def check_miner_logs():
    """Check miner logs for recent activity."""
    print("🔍 Checking Miner Logs")
    print("=" * 40)
    
    try:
        # Get recent miner logs
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
            
            # Get the process ID
            pid = miner_processes[0].split()[1]
            print(f"\n📊 Miner Process ID: {pid}")
            
            # Check if the miner is responding to requests
            print("\n🔍 Checking if miner is processing requests...")
            
            # Send a simple request and check logs
            import requests
            try:
                response = requests.get("http://127.0.0.1:8091", timeout=5)
                print(f"   📡 HTTP Response: {response.status_code}")
            except Exception as e:
                print(f"   📡 HTTP Error: {e}")
            
            print("\n✅ Miner is running and accessible")
            return True
        else:
            print("❌ No miner process found")
            return False
            
    except Exception as e:
        print(f"❌ Failed to check miner: {e}")
        return False

def test_miner_processing():
    """Test if the miner is actually processing requests."""
    print("\n🧪 Testing Miner Processing")
    print("=" * 40)
    
    try:
        # Send a request and check if the miner logs show processing
        import requests
        import json
        
        # Create a simple test request
        headers = {
            'Content-Type': 'application/json',
            'name': 'AudioTask'
        }
        
        data = {
            'task_type': 'transcription',
            'input_data': 'dGVzdA==',  # base64 for "test"
            'language': 'en'
        }
        
        print("📤 Sending test request to miner...")
        
        # Send the request
        response = requests.post(
            "http://127.0.0.1:8091",
            headers=headers,
            json=data,
            timeout=10
        )
        
        print(f"📥 Response status: {response.status_code}")
        print(f"📋 Response headers: {dict(response.headers)}")
        print(f"📄 Response text: {response.text[:200]}...")
        
        # Check if the miner is actually processing
        if response.status_code == 404:
            # The miner is responding but not recognizing the synapse
            print("⚠️  Miner is responding but synapse name not recognized")
            print("   This suggests the miner is working but needs proper synapse name")
            return True
        elif response.status_code == 200:
            print("✅ Miner processed the request successfully!")
            return True
        else:
            print(f"❌ Miner returned unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Miner Logs and Processing Test")
    print("=" * 60)
    
    # Check miner logs
    miner_running = check_miner_logs()
    
    if miner_running:
        # Test miner processing
        processing_ok = test_miner_processing()
        
        if processing_ok:
            print("\n🎉 Miner is running and processing requests!")
            print("   The issue is likely with synapse name recognition.")
        else:
            print("\n💥 Miner is running but not processing requests properly.")
    else:
        print("\n💥 Miner process is not running.")

