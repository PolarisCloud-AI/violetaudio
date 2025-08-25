#!/usr/bin/env python3
"""
Test script for the new summarization pipeline with database storage and language detection.
This script tests:
1. Creating summarization tasks with text stored in database
2. Fetching task content via miner API
3. Processing summarization with language support
"""

import asyncio
import httpx
import json
from datetime import datetime

# Test configuration
PROXY_SERVER_URL = "http://localhost:8000"

async def test_summarization_pipeline():
    """Test the complete summarization pipeline"""
    print("🧪 Testing New Summarization Pipeline")
    print("=" * 50)
    
    # Test 1: Submit summarization task with English text
    print("\n📝 Test 1: Submit English summarization task")
    english_text = """
    Artificial intelligence (AI) is a branch of computer science that aims to create intelligent machines that work and react like humans. 
    Some of the activities computers with artificial intelligence are designed for include speech recognition, learning, planning, and problem solving. 
    AI has been used in various applications such as virtual assistants, autonomous vehicles, medical diagnosis, and financial trading. 
    The field continues to evolve rapidly with new breakthroughs in machine learning, deep learning, and neural networks.
    """
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{PROXY_SERVER_URL}/api/v1/summarization",
                data={
                    "text": english_text.strip(),
                    "source_language": "en",
                    "priority": "normal"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ English task created successfully")
                print(f"   Task ID: {result.get('task_id')}")
                print(f"   Detected Language: {result.get('detected_language')}")
                print(f"   Language Confidence: {result.get('language_confidence')}")
                print(f"   Text Length: {result.get('text_length')}")
                print(f"   Word Count: {result.get('word_count')}")
                
                english_task_id = result.get('task_id')
            else:
                print(f"❌ Failed to create English task: {response.status_code}")
                print(f"   Response: {response.text}")
                return
                
    except Exception as e:
        print(f"❌ Error creating English task: {e}")
        return
    
    # Test 2: Submit summarization task with Spanish text
    print("\n📝 Test 2: Submit Spanish summarization task")
    spanish_text = """
    La inteligencia artificial (IA) es una rama de la informática que busca crear máquinas inteligentes que trabajen y reaccionen como humanos. 
    Algunas de las actividades para las que están diseñadas las computadoras con inteligencia artificial incluyen reconocimiento de voz, aprendizaje, planificación y resolución de problemas. 
    La IA se ha utilizado en diversas aplicaciones como asistentes virtuales, vehículos autónomos, diagnóstico médico y comercio financiero. 
    El campo continúa evolucionando rápidamente con nuevos avances en aprendizaje automático, aprendizaje profundo y redes neuronales.
    """
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{PROXY_SERVER_URL}/api/v1/summarization",
                data={
                    "text": spanish_text.strip(),
                    "source_language": "es",  # Explicitly specify Spanish
                    "priority": "normal"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Spanish task created successfully")
                print(f"   Task ID: {result.get('task_id')}")
                print(f"   Source Language: {result.get('detected_language')}")
                print(f"   Language Confidence: {result.get('language_confidence')}")
                print(f"   Text Length: {result.get('text_length')}")
                print(f"   Word Count: {result.get('word_count')}")
                
                spanish_task_id = result.get('task_id')
            else:
                print(f"❌ Failed to create Spanish task: {response.status_code}")
                print(f"   Response: {response.text}")
                return
                
    except Exception as e:
        print(f"❌ Error creating Spanish task: {e}")
        return
    
    # Test 3: Test miner API endpoint for fetching task content
    print("\n📡 Test 3: Test miner API endpoint for fetching task content")
    
    # Test English task
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{PROXY_SERVER_URL}/api/v1/miner/summarization/{english_task_id}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ English task content fetched successfully")
                print(f"   Task ID: {result.get('task_id')}")
                text_content = result.get('text_content', {})
                print(f"   Text Length: {len(text_content.get('text', ''))}")
                print(f"   Source Language: {text_content.get('source_language')}")
                print(f"   Detected Language: {text_content.get('detected_language')}")
                print(f"   Language Confidence: {text_content.get('language_confidence')}")
            else:
                print(f"❌ Failed to fetch English task content: {response.status_code}")
                print(f"   Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error fetching English task content: {e}")
    
    # Test Spanish task
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{PROXY_SERVER_URL}/api/v1/miner/summarization/{spanish_task_id}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Spanish task content fetched successfully")
                print(f"   Task ID: {result.get('task_id')}")
                text_content = result.get('text_content', {})
                print(f"   Text Length: {len(text_content.get('text', ''))}")
                print(f"   Source Language: {text_content.get('source_language')}")
                print(f"   Detected Language: {text_content.get('detected_language')}")
                print(f"   Language Confidence: {text_content.get('language_confidence')}")
            else:
                print(f"❌ Failed to fetch Spanish task content: {response.status_code}")
                print(f"   Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error fetching Spanish task content: {e}")
    
    # Test 4: Check available tasks
    print("\n📋 Test 4: Check available tasks")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{PROXY_SERVER_URL}/api/v1/tasks/available")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Available tasks fetched successfully")
                print(f"   Total Tasks: {len(result)}")
                
                # Count summarization tasks
                summarization_tasks = [t for t in result if t.get('task_type') == 'summarization']
                print(f"   Summarization Tasks: {len(summarization_tasks)}")
                
                for i, task in enumerate(summarization_tasks[:3]):  # Show first 3
                    print(f"   Task {i+1}: {task.get('task_id')} - {task.get('status')}")
                    
            else:
                print(f"❌ Failed to fetch available tasks: {response.status_code}")
                print(f"   Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error fetching available tasks: {e}")
    
    print("\n🎯 Summarization Pipeline Test Complete!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_summarization_pipeline())
