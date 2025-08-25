#!/usr/bin/env python3
"""
Complete Pipeline Test for Summarization with Different Languages
This script tests the entire workflow:
1. Submit text files in different languages
2. Test miner API endpoint for fetching content
3. Test validator evaluation with the same text
4. Verify end-to-end processing
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

# Test configuration
PROXY_SERVER_URL = "http://localhost:8000"

# Test texts in different languages
TEST_TEXTS = {
    "en": {
        "text": """Artificial intelligence (AI) is a branch of computer science that aims to create intelligent machines that work and react like humans. 
        Some of the activities computers with artificial intelligence are designed for include speech recognition, learning, planning, and problem solving. 
        AI has been used in various applications such as virtual assistants, autonomous vehicles, medical diagnosis, and financial trading. 
        The field continues to evolve rapidly with new breakthroughs in machine learning, deep learning, and neural networks.""",
        "expected_summary_length": 50,  # Expected minimum summary length
        "language": "en"
    },
    "es": {
        "text": """La inteligencia artificial (IA) es una rama de la informática que busca crear máquinas inteligentes que trabajen y reaccionen como humanos. 
        Algunas de las actividades para las que están diseñadas las computadoras con inteligencia artificial incluyen reconocimiento de voz, aprendizaje, planificación y resolución de problemas. 
        La IA se ha utilizado en diversas aplicaciones como asistentes virtuales, vehículos autónomos, diagnóstico médico y comercio financiero. 
        El campo continúa evolucionando rápidamente con nuevos avances en aprendizaje automático, aprendizaje profundo y redes neuronales.""",
        "expected_summary_length": 50,
        "language": "es"
    },
    "fr": {
        "text": """L'intelligence artificielle (IA) est une branche de l'informatique qui vise à créer des machines intelligentes qui travaillent et réagissent comme des humains. 
        Certaines des activités pour lesquelles les ordinateurs avec intelligence artificielle sont conçus incluent la reconnaissance vocale, l'apprentissage, la planification et la résolution de problèmes. 
        L'IA a été utilisée dans diverses applications telles que les assistants virtuels, les véhicules autonomes, le diagnostic médical et le trading financier. 
        Le domaine continue d'évoluer rapidement avec de nouvelles avancées en apprentissage automatique, apprentissage profond et réseaux de neurones.""",
        "expected_summary_length": 50,
        "language": "fr"
    },
    "de": {
        "text": """Künstliche Intelligenz (KI) ist ein Zweig der Informatik, der darauf abzielt, intelligente Maschinen zu schaffen, die wie Menschen arbeiten und reagieren. 
        Zu den Aktivitäten, für die Computer mit künstlicher Intelligenz entwickelt wurden, gehören Spracherkennung, Lernen, Planung und Problemlösung. 
        KI wurde in verschiedenen Anwendungen eingesetzt, wie virtuelle Assistenten, autonome Fahrzeuge, medizinische Diagnose und Finanzhandel. 
        Das Gebiet entwickelt sich weiterhin rasch mit neuen Durchbrüchen im maschinellen Lernen, Deep Learning und neuronalen Netzen.""",
        "expected_summary_length": 50,
        "language": "de"
    },
    "ru": {
        "text": """Искусственный интеллект (ИИ) - это раздел информатики, который стремится создавать интеллектуальные машины, работающие и реагирующие как люди. 
        Некоторые из видов деятельности, для которых предназначены компьютеры с искусственным интеллектом, включают распознавание речи, обучение, планирование и решение проблем. 
        ИИ использовался в различных приложениях, таких как виртуальные помощники, автономные транспортные средства, медицинская диагностика и финансовые операции. 
        Эта область продолжает быстро развиваться с новыми прорывами в машинном обучении, глубоком обучении и нейронных сетях.""",
        "expected_summary_length": 50,
        "language": "ru"
    }
}

async def test_complete_pipeline():
    """Test the complete summarization pipeline end-to-end"""
    print("🚀 Testing Complete Summarization Pipeline")
    print("=" * 60)
    print("📋 Test Coverage:")
    print("   1. Text submission in 5 languages")
    print("   2. Miner API content fetching")
    print("   3. Validator evaluation simulation")
    print("   4. End-to-end workflow verification")
    print("=" * 60)
    
    created_tasks = []
    
    # Phase 1: Submit text files in different languages
    print("\n📝 PHASE 1: Text Submission in Different Languages")
    print("-" * 50)
    
    for lang_code, test_data in TEST_TEXTS.items():
        print(f"\n🌍 Testing {lang_code.upper()} Language")
        print(f"   Language: {test_data['language']}")
        print(f"   Text Length: {len(test_data['text'])} characters")
        print(f"   Word Count: {len(test_data['text'].split())}")
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{PROXY_SERVER_URL}/api/v1/summarization",
                    data={
                        "text": test_data["text"],
                        "source_language": test_data["language"],
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
                    if result.get('detected_language') == test_data['language']:
                        print(f"      ✅ Language correctly set to {result.get('detected_language')}")
                    else:
                        print(f"      ❌ Language mismatch: expected {test_data['language']}, got {result.get('detected_language')}")
                    
                    if result.get('language_confidence') == 1.0:
                        print(f"      ✅ Language confidence correctly set to 1.0")
                    else:
                        print(f"      ❌ Language confidence should be 1.0, got {result.get('language_confidence')}")
                    
                    # Store task for further testing
                    created_tasks.append({
                        'task_id': result.get('task_id'),
                        'language': lang_code,
                        'test_data': test_data,
                        'result': result
                    })
                    
                else:
                    print(f"   ❌ Failed to create task: {response.status_code}")
                    print(f"      Response: {response.text}")
                    
        except Exception as e:
            print(f"   ❌ Error creating task: {e}")
    
    print(f"\n📊 Phase 1 Results: {len(created_tasks)}/{len(TEST_TEXTS)} tasks created successfully")
    
    # Phase 2: Test miner API endpoint for fetching content
    print(f"\n📡 PHASE 2: Miner API Content Fetching")
    print("-" * 50)
    
    miner_api_results = []
    
    for task_info in created_tasks:
        print(f"\n🔍 Testing Miner API for {task_info['language'].upper()} Task")
        print(f"   Task ID: {task_info['task_id']}")
        
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
                    print(f"      Text Length: {len(text_content.get('text', ''))}")
                    print(f"      Word Count: {text_content.get('word_count')}")
                    
                    # Verify content integrity
                    original_text = task_info['test_data']['text']
                    fetched_text = text_content.get('text', '')
                    
                    if len(fetched_text) == len(original_text):
                        print(f"      ✅ Text length preserved: {len(fetched_text)} characters")
                    else:
                        print(f"      ⚠️ Text length mismatch: original {len(original_text)}, fetched {len(fetched_text)}")
                    
                    if text_content.get('source_language') == task_info['test_data']['language']:
                        print(f"      ✅ Language preserved correctly")
                    else:
                        print(f"      ❌ Language mismatch in fetched content")
                    
                    miner_api_results.append({
                        'task_id': task_info['task_id'],
                        'language': task_info['language'],
                        'success': True,
                        'content': text_content
                    })
                    
                else:
                    print(f"   ❌ Failed to fetch content: {response.status_code}")
                    print(f"      Response: {response.text}")
                    
                    miner_api_results.append({
                        'task_id': task_info['task_id'],
                        'language': task_info['language'],
                        'success': False,
                        'error': f"HTTP {response.status_code}"
                    })
                    
        except Exception as e:
            print(f"   ❌ Error fetching content: {e}")
            miner_api_results.append({
                'task_id': task_info['task_id'],
                'language': task_info['language'],
                'success': False,
                'error': str(e)
            })
    
    print(f"\n📊 Phase 2 Results: {sum(1 for r in miner_api_results if r['success'])}/{len(created_tasks)} miner API calls successful")
    
    # Phase 3: Test validator evaluation simulation
    print(f"\n✅ PHASE 3: Validator Evaluation Simulation")
    print("-" * 50)
    
    validator_results = []
    
    for task_info in created_tasks:
        print(f"\n🔬 Simulating Validator Evaluation for {task_info['language'].upper()} Task")
        print(f"   Task ID: {task_info['task_id']}")
        
        # Simulate validator processing the same text
        original_text = task_info['test_data']['text']
        source_language = task_info['test_data']['language']
        
        print(f"   📝 Processing text in {source_language.upper()}")
        print(f"      Original Length: {len(original_text)} characters")
        print(f"      Source Language: {source_language}")
        
        # Simulate summarization processing time
        processing_time = 2.0 + (len(original_text) / 1000)  # Simulate realistic processing time
        
        # Simulate summary generation (this would normally use the actual pipeline)
        summary_length = max(50, len(original_text) // 4)  # Simulate 25% compression
        simulated_summary = f"[{source_language.upper()}] Summary of {len(original_text)} characters in {source_language}"
        
        print(f"   ⏱️ Simulated Processing Time: {processing_time:.2f}s")
        print(f"   📊 Simulated Summary Length: {len(simulated_summary)} characters")
        print(f"   🎯 Compression Ratio: {len(simulated_summary) / len(original_text):.2%}")
        
        # Calculate simulated scores
        accuracy_score = 0.85 + (0.1 * (1.0 - abs(len(simulated_summary) - task_info['test_data']['expected_summary_length']) / 100))
        speed_score = max(0.5, 1.0 - (processing_time / 10.0))
        
        print(f"   📈 Simulated Accuracy Score: {accuracy_score:.3f}")
        print(f"   🚀 Simulated Speed Score: {speed_score:.3f}")
        
        validator_results.append({
            'task_id': task_info['task_id'],
            'language': task_info['language'],
            'processing_time': processing_time,
            'summary_length': len(simulated_summary),
            'compression_ratio': len(simulated_summary) / len(original_text),
            'accuracy_score': accuracy_score,
            'speed_score': speed_score,
            'source_language': source_language
        })
        
        print(f"   ✅ Validator evaluation simulation completed")
    
    print(f"\n📊 Phase 3 Results: {len(validator_results)}/{len(created_tasks)} validator evaluations simulated")
    
    # Phase 4: End-to-end workflow verification
    print(f"\n🔄 PHASE 4: End-to-End Workflow Verification")
    print("-" * 50)
    
    print(f"\n📋 Workflow Summary:")
    print(f"   • Text Submission: {len(created_tasks)}/{len(TEST_TEXTS)} successful")
    print(f"   • Miner API: {sum(1 for r in miner_api_results if r['success'])}/{len(created_tasks)} successful")
    print(f"   • Validator Simulation: {len(validator_results)}/{len(created_tasks)} completed")
    
    # Language-specific results
    print(f"\n🌍 Language-Specific Results:")
    for lang_code in TEST_TEXTS.keys():
        lang_tasks = [t for t in created_tasks if t['language'] == lang_code]
        lang_miner = [r for r in miner_api_results if r['language'] == lang_code and r['success']]
        lang_validator = [r for r in validator_results if r['language'] == lang_code]
        
        print(f"   {lang_code.upper()}: {len(lang_tasks)} tasks, {len(lang_miner)} miner API, {len(lang_validator)} validator")
    
    # Overall pipeline health
    overall_success_rate = len(created_tasks) / len(TEST_TEXTS)
    miner_success_rate = sum(1 for r in miner_api_results if r['success']) / len(created_tasks) if created_tasks else 0
    
    print(f"\n📊 Overall Pipeline Health:")
    print(f"   • Task Creation Success Rate: {overall_success_rate:.1%}")
    print(f"   • Miner API Success Rate: {miner_success_rate:.1%}")
    print(f"   • Pipeline Completeness: {'✅ FULLY OPERATIONAL' if overall_success_rate == 1.0 and miner_success_rate == 1.0 else '⚠️ PARTIALLY OPERATIONAL'}")
    
    print(f"\n🎯 Complete Pipeline Test Finished!")
    print("=" * 60)
    
    return {
        'created_tasks': created_tasks,
        'miner_api_results': miner_api_results,
        'validator_results': validator_results,
        'overall_success_rate': overall_success_rate,
        'miner_success_rate': miner_success_rate
    }

if __name__ == "__main__":
    asyncio.run(test_complete_pipeline())


