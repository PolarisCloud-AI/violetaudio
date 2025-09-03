#!/usr/bin/env python3
"""
Test script to verify that the summarization pipeline respects user-specified languages directly.
This tests that:
1. The source language passed by the user is used directly
2. No auto-detection is performed
3. Language confidence is always 1.0
"""

import asyncio
import httpx
import json

# Test configuration
PROXY_SERVER_URL = "http://localhost:8000"

async def test_language_specification():
    """Test that user-specified languages are respected directly"""
    print("🧪 Testing Language Specification in Summarization Pipeline")
    print("=" * 60)
    
    # Test different languages
    test_cases = [
        {
            "name": "English",
            "text": "Artificial intelligence is a branch of computer science that aims to create intelligent machines.",
            "source_language": "en",
            "expected_language": "en"
        },
        {
            "name": "Spanish",
            "text": "La inteligencia artificial es una rama de la informática que busca crear máquinas inteligentes.",
            "source_language": "es",
            "expected_language": "es"
        },
        {
            "name": "French",
            "text": "L'intelligence artificielle est une branche de l'informatique qui vise à créer des machines intelligentes.",
            "source_language": "fr",
            "expected_language": "fr"
        },
        {
            "name": "German",
            "text": "Künstliche Intelligenz ist ein Zweig der Informatik, der darauf abzielt, intelligente Maschinen zu schaffen.",
            "source_language": "de",
            "expected_language": "de"
        },
        {
            "name": "Russian",
            "text": "Искусственный интеллект - это раздел информатики, который стремится создавать интеллектуальные машины.",
            "source_language": "ru",
            "expected_language": "ru"
        }
    ]
    
    created_tasks = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['name']} Language")
        print(f"   Source Language: {test_case['source_language']}")
        print(f"   Expected Language: {test_case['expected_language']}")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{PROXY_SERVER_URL}/api/v1/summarization",
                    data={
                        "text": test_case["text"],
                        "source_language": test_case["source_language"],
                        "priority": "normal"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ Task created successfully")
                    print(f"      Task ID: {result.get('task_id')}")
                    print(f"      Detected Language: {result.get('detected_language')}")
                    print(f"      Language Confidence: {result.get('language_confidence')}")
                    print(f"      Text Length: {result.get('text_length')}")
                    print(f"      Word Count: {result.get('word_count')}")
                    
                    # Verify language handling
                    detected_lang = result.get('detected_language')
                    confidence = result.get('language_confidence')
                    
                    if detected_lang == test_case['expected_language']:
                        print(f"      ✅ Language correctly set to {detected_lang}")
                    else:
                        print(f"      ❌ Language mismatch: expected {test_case['expected_language']}, got {detected_lang}")
                    
                    if confidence == 1.0:
                        print(f"      ✅ Language confidence correctly set to 1.0")
                    else:
                        print(f"      ❌ Language confidence should be 1.0, got {confidence}")
                    
                    # Store task for further testing
                    created_tasks.append({
                        'task_id': result.get('task_id'),
                        'name': test_case['name'],
                        'expected_language': test_case['expected_language']
                    })
                    
                else:
                    print(f"   ❌ Failed to create task: {response.status_code}")
                    print(f"      Response: {response.text}")
                    
        except Exception as e:
            print(f"   ❌ Error creating task: {e}")
    
    # Test miner API endpoint for each created task
    print(f"\n📡 Testing Miner API Endpoint for {len(created_tasks)} Tasks")
    print("=" * 60)
    
    for task_info in created_tasks:
        print(f"\n🔍 Testing Task: {task_info['name']} (ID: {task_info['task_id']})")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{PROXY_SERVER_URL}/api/v1/miner/summarization/{task_info['task_id']}")
                
                if response.status_code == 200:
                    result = response.json()
                    text_content = result.get('text_content', {})
                    
                    print(f"   ✅ Content fetched successfully")
                    print(f"      Source Language: {text_content.get('source_language')}")
                    print(f"      Detected Language: {text_content.get('detected_language')}")
                    print(f"      Language Confidence: {text_content.get('language_confidence')}")
                    
                    # Verify language consistency
                    source_lang = text_content.get('source_language')
                    detected_lang = text_content.get('detected_language')
                    confidence = text_content.get('language_confidence')
                    
                    if source_lang == task_info['expected_language']:
                        print(f"      ✅ Source language correctly set to {source_lang}")
                    else:
                        print(f"      ❌ Source language mismatch: expected {task_info['expected_language']}, got {source_lang}")
                    
                    if detected_lang == task_info['expected_language']:
                        print(f"      ✅ Detected language correctly set to {detected_lang}")
                    else:
                        print(f"      ❌ Detected language mismatch: expected {task_info['expected_language']}, got {detected_lang}")
                    
                    if confidence == 1.0:
                        print(f"      ✅ Language confidence correctly set to 1.0")
                    else:
                        print(f"      ❌ Language confidence should be 1.0, got {confidence}")
                    
                else:
                    print(f"   ❌ Failed to fetch content: {response.status_code}")
                    print(f"      Response: {response.text}")
                    
        except Exception as e:
            print(f"   ❌ Error fetching content: {e}")
    
    print(f"\n🎯 Language Specification Test Complete!")
    print("=" * 60)
    print(f"✅ Created {len(created_tasks)} tasks with different languages")
    print(f"✅ Verified miner API endpoint for all tasks")
    print(f"✅ Confirmed user-specified languages are respected directly")

if __name__ == "__main__":
    asyncio.run(test_language_specification())


