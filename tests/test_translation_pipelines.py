#!/usr/bin/env python3
"""
Test script for Machine Translation Pipelines
Tests both text translation and document translation endpoints
"""

import requests
import json
import time
import os
from pathlib import Path

# Configuration
PROXY_URL = "http://localhost:8000"
TEST_TEXT = "Hello, this is a test of the machine translation pipeline. We are testing both text and document translation capabilities."
TEST_LANGUAGES = [
    ("en", "es"),  # English to Spanish
    ("en", "fr"),  # English to French
    ("en", "de"),  # English to German
    ("en", "it"),  # English to Italian
    ("en", "pt"),  # English to Portuguese
]

def test_text_translation():
    """Test text translation endpoint"""
    print("🌐 Testing Text Translation Pipeline")
    print("=" * 50)
    
    for source_lang, target_lang in TEST_LANGUAGES:
        print(f"\n📝 Testing {source_lang} → {target_lang}")
        
        try:
            # Submit text translation task
            response = requests.post(
                f"{PROXY_URL}/api/v1/text-translation",
                data={
                    "text": TEST_TEXT,
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "priority": "normal"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Task submitted successfully")
                print(f"   📋 Task ID: {result.get('task_id')}")
                print(f"   📝 Text length: {result.get('text_length')} characters")
                print(f"   🔤 Word count: {result.get('word_count')} words")
                print(f"   🤖 Auto-assigned: {result.get('auto_assigned')}")
                
                # Wait a bit for processing
                time.sleep(2)
                
                # Check task status
                task_id = result.get('task_id')
                if task_id:
                    status_response = requests.get(f"{PROXY_URL}/api/v1/tasks/{task_id}")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"   📊 Task status: {status_data.get('status')}")
                        print(f"   👥 Assigned miners: {status_data.get('assigned_miners', [])}")
                    else:
                        print(f"   ⚠️ Could not check task status: {status_response.status_code}")
                
            else:
                print(f"   ❌ Failed to submit task: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)

def create_test_document():
    """Create a test document for document translation"""
    print("📄 Creating test document...")
    
    # Create a simple text file
    test_content = """This is a test document for machine translation.

The document contains multiple paragraphs to test the translation pipeline's ability to handle longer texts.

It includes various types of content:
- Simple sentences
- Lists and bullet points
- Numbers and special characters
- Different formatting styles

This document will be used to test the document translation endpoint and verify that the pipeline can extract text from files and translate it accurately.

The goal is to ensure that both text translation and document translation work seamlessly within the Bittensor subnet framework.
"""
    
    # Write to file
    test_file_path = "test_document.txt"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    print(f"   ✅ Created test document: {test_file_path}")
    print(f"   📊 File size: {len(test_content)} characters")
    return test_file_path

def test_document_translation():
    """Test document translation endpoint"""
    print("\n📄 Testing Document Translation Pipeline")
    print("=" * 50)
    
    # Create test document
    test_file_path = create_test_document()
    
    for source_lang, target_lang in TEST_LANGUAGES[:2]:  # Test with fewer languages for documents
        print(f"\n📝 Testing {source_lang} → {target_lang}")
        
        try:
            # Submit document translation task
            with open(test_file_path, "rb") as f:
                files = {"document_file": f}
                data = {
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "priority": "normal"
                }
                
                response = requests.post(
                    f"{PROXY_URL}/api/v1/document-translation",
                    files=files,
                    data=data,
                    timeout=60  # Longer timeout for document processing
                )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Task submitted successfully")
                print(f"   📋 Task ID: {result.get('task_id')}")
                print(f"   📁 File ID: {result.get('file_id')}")
                print(f"   📄 File name: {result.get('file_name')}")
                print(f"   📊 File size: {result.get('file_size')} bytes")
                print(f"   🔤 File format: {result.get('file_format')}")
                print(f"   🤖 Auto-assigned: {result.get('auto_assigned')}")
                
                # Wait a bit for processing
                time.sleep(3)
                
                # Check task status
                task_id = result.get('task_id')
                if task_id:
                    status_response = requests.get(f"{PROXY_URL}/api/v1/tasks/{task_id}")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"   📊 Task status: {status_data.get('status')}")
                        print(f"   👥 Assigned miners: {status_data.get('assigned_miners', [])}")
                    else:
                        print(f"   ⚠️ Could not check task status: {status_response.status_code}")
                
            else:
                print(f"   ❌ Failed to submit task: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    # Clean up test file
    try:
        os.remove(test_file_path)
        print(f"\n   🧹 Cleaned up test file: {test_file_path}")
    except:
        pass
    
    print("\n" + "=" * 50)

def test_miner_endpoints():
    """Test miner endpoints for translation tasks"""
    print("\n🔧 Testing Miner Endpoints")
    print("=" * 50)
    
    try:
        # Get all tasks to find translation tasks
        response = requests.get(f"{PROXY_URL}/api/v1/tasks")
        
        if response.status_code == 200:
            tasks = response.json()
            translation_tasks = [task for task in tasks if task.get('task_type') in ['text_translation', 'document_translation']]
            
            if translation_tasks:
                print(f"   📋 Found {len(translation_tasks)} translation tasks")
                
                for task in translation_tasks[:2]:  # Test first 2 tasks
                    task_id = task.get('task_id')
                    task_type = task.get('task_type')
                    
                    print(f"\n   🔍 Testing {task_type} task: {task_id}")
                    
                    if task_type == 'text_translation':
                        # Test text translation miner endpoint
                        miner_response = requests.get(f"{PROXY_URL}/api/v1/miner/text-translation/{task_id}")
                        if miner_response.status_code == 200:
                            miner_data = miner_response.json()
                            print(f"      ✅ Miner endpoint accessible")
                            print(f"      📝 Text content available: {bool(miner_data.get('text_content'))}")
                        else:
                            print(f"      ❌ Miner endpoint failed: {miner_response.status_code}")
                    
                    elif task_type == 'document_translation':
                        # Test document translation miner endpoint
                        miner_response = requests.get(f"{PROXY_URL}/api/v1/miner/document-translation/{task_id}")
                        if miner_response.status_code == 200:
                            miner_data = miner_response.json()
                            print(f"      ✅ Miner endpoint accessible")
                            print(f"      📁 File metadata available: {bool(miner_data.get('file_metadata'))}")
                        else:
                            print(f"      ❌ Miner endpoint failed: {miner_response.status_code}")
            else:
                print("   ⚠️ No translation tasks found to test")
        else:
            print(f"   ❌ Could not fetch tasks: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error testing miner endpoints: {str(e)}")
    
    print("\n" + "=" * 50)

def test_system_health():
    """Test system health and endpoints"""
    print("\n🏥 Testing System Health")
    print("=" * 50)
    
    try:
        # Test health endpoint
        response = requests.get(f"{PROXY_URL}/health")
        if response.status_code == 200:
            print("   ✅ Health endpoint: OK")
        else:
            print(f"   ⚠️ Health endpoint: {response.status_code}")
        
        # Test tasks endpoint
        response = requests.get(f"{PROXY_URL}/api/v1/tasks")
        if response.status_code == 200:
            tasks = response.json()
            print(f"   ✅ Tasks endpoint: OK ({len(tasks)} tasks)")
        else:
            print(f"   ⚠️ Tasks endpoint: {response.status_code}")
        
        # Test miners endpoint
        response = requests.get(f"{PROXY_URL}/api/v1/miners")
        if response.status_code == 200:
            miners = response.json()
            print(f"   ✅ Miners endpoint: OK ({len(miners)} miners)")
        else:
            print(f"   ⚠️ Miners endpoint: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error testing system health: {str(e)}")
    
    print("\n" + "=" * 50)

def main():
    """Main test function"""
    print("🚀 Machine Translation Pipeline Test Suite")
    print("=" * 60)
    
    # Check if proxy server is running
    try:
        response = requests.get(f"{PROXY_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Proxy server not responding properly: {response.status_code}")
            return
        print("✅ Proxy server is running")
    except requests.exceptions.RequestException:
        print("❌ Proxy server is not running. Please start the server first.")
        return
    
    # Run tests
    test_system_health()
    test_text_translation()
    test_document_translation()
    test_miner_endpoints()
    
    print("\n🎉 Translation Pipeline Test Suite Completed!")
    print("=" * 60)
    print("\n📋 Summary:")
    print("   • Text translation endpoints tested")
    print("   • Document translation endpoints tested")
    print("   • Miner endpoints verified")
    print("   • System health checked")
    print("\n💡 Next steps:")
    print("   • Check miner logs for task processing")
    print("   • Monitor task completion in proxy server")
    print("   • Verify translation quality and accuracy")

if __name__ == "__main__":
    main()
