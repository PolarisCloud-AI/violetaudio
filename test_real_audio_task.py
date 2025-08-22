#!/usr/bin/env python3
"""
Test real audio task workflow - create task and verify miner processes it
"""

import requests
import json
import time
import os

def test_real_audio_workflow():
    proxy_url = "http://localhost:8000"
    
    # Check proxy health
    try:
        health_response = requests.get(f"{proxy_url}/health")
        if health_response.status_code == 200:
            print("✅ Proxy server is running")
        else:
            print(f"❌ Proxy server health check failed: {health_response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to proxy server: {e}")
        return
    
    # Create transcription task with real audio file
    print("\n🎯 Creating transcription task with real audio file...")
    
    audio_file_path = "proxy_server/local_storage/user_audio/7290cb3e-3c5c-4b53-8e49-c182e3357f5d_LJ037-0171.wav"
    
    if not os.path.exists(audio_file_path):
        print(f"❌ Audio file not found: {audio_file_path}")
        return
    
    print(f"📁 Using audio file: {audio_file_path}")
    print(f"📊 File size: {os.path.getsize(audio_file_path)} bytes")
    
    try:
        # Read the audio file
        with open(audio_file_path, 'rb') as f:
            audio_content = f.read()
        
        # Create the file upload
        files = {
            'audio_file': ('LJ037-0171.wav', audio_content, 'audio/wav')
        }
        
        # Additional parameters
        data = {
            'priority': 'high',
            'expected_duration': '120',
            'min_accuracy': '0.8',
            'language': 'en'
        }
        
        response = requests.post(
            f"{proxy_url}/api/v1/transcription",
            files=files,
            data=data
        )
        
        if response.status_code == 201:
            task_result = response.json()
            task_id = task_result.get("task_id")
            print(f"✅ Task created successfully!")
            print(f"   📋 Task ID: {task_id}")
            print(f"   🎵 Audio File: LJ037-0171.wav")
            
            # Wait for task distribution
            print("\n⏳ Waiting for task distribution...")
            time.sleep(5)
            
            # Check task status
            status_response = requests.get(f"{proxy_url}/api/v1/task/{task_id}/status")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"📊 Task Status: {status_data.get('status', 'Unknown')}")
                print(f"🎯 Assigned Miners: {status_data.get('assigned_miners', [])}")
                
                # Check miner 48 tasks
                miner_response = requests.get(f"{proxy_url}/api/v1/miners/48/tasks?status=assigned")
                if miner_response.status_code == 200:
                    miner_tasks = miner_response.json()
                    print(f"\n🔍 Miner 48 Tasks: {len(miner_tasks.get('tasks', []))}")
                    for task in miner_tasks.get('tasks', []):
                        print(f"   📋 Task {task.get('task_id')}: {task.get('status')}")
                else:
                    print(f"⚠️ Could not get miner 48 tasks: {miner_response.status_code}")
                
            else:
                print(f"⚠️ Could not get task status: {status_response.status_code}")
                
        else:
            print(f"❌ Task creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error creating task: {e}")
    
    # Check available miners
    print("\n🔍 Checking available miners...")
    try:
        miners_response = requests.get(f"{proxy_url}/api/v1/miners/available")
        if miners_response.status_code == 200:
            miners_data = miners_response.json()
            print(f"✅ Available miners: {len(miners_data.get('miners', []))}")
            for miner in miners_data.get('miners', []):
                print(f"   🖥️  Miner {miner.get('uid')}: {miner.get('status')} (Load: {miner.get('current_load')})")
        else:
            print(f"⚠️ Could not get available miners: {miners_response.status_code}")
    except Exception as e:
        print(f"❌ Error checking miners: {e}")

if __name__ == "__main__":
    print("🚀 Testing Real Audio Task Workflow")
    print("=" * 50)
    
    test_real_audio_workflow()
    
    print("\n" + "=" * 50)
    print("🏁 Workflow test completed")
