#!/usr/bin/env python3
"""
Complete Workflow Test: Proxy Server → Validator → Miner → Response
This script tests the entire audio processing pipeline from user input to final response
"""

import asyncio
import requests
import time
import json
import base64
import threading
from datetime import datetime

# Configuration
PROXY_SERVER_URL = "http://localhost:8000"
VALIDATOR_URL = "http://localhost:8092"  # Validator axon port
MINER_URL = "http://localhost:8091"     # Miner axon port

class CompleteWorkflowTest:
    def __init__(self):
        self.test_results = {}
        self.task_ids = {}
        
    def log_step(self, step, message, status="ℹ️"):
        """Log a step in the workflow"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{status} [{timestamp}] {step}: {message}")
        
    def test_proxy_server_health(self):
        """Test 1: Check if proxy server is running"""
        self.log_step("PROXY_HEALTH", "Checking proxy server health...")
        
        try:
            response = requests.get(f"{PROXY_SERVER_URL}/api/v1/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                self.log_step("PROXY_HEALTH", f"✅ Server healthy - {health_data.get('status')}", "✅")
                self.log_step("PROXY_HEALTH", f"   Pending tasks: {health_data.get('pending_tasks')}", "ℹ️")
                self.log_step("PROXY_HEALTH", f"   Bittensor connected: {health_data.get('bittensor_connected')}", "ℹ️")
                return True
            else:
                self.log_step("PROXY_HEALTH", f"❌ Server unhealthy - Status {response.status_code}", "❌")
                return False
        except Exception as e:
            self.log_step("PROXY_HEALTH", f"❌ Connection failed - {str(e)}", "❌")
            return False
    
    def test_validator_integration(self):
        """Test 2: Check validator integration endpoint"""
        self.log_step("VALIDATOR_INTEGRATION", "Checking validator integration...")
        
        try:
            response = requests.get(f"{PROXY_SERVER_URL}/api/v1/validator/integration", timeout=10)
            if response.status_code == 200:
                integration_data = response.json()
                
                network_info = integration_data.get('network_info', {})
                self.log_step("VALIDATOR_INTEGRATION", f"✅ Integration successful", "✅")
                self.log_step("VALIDATOR_INTEGRATION", f"   Network: {network_info.get('network')}", "ℹ️")
                self.log_step("VALIDATOR_INTEGRATION", f"   NetUID: {network_info.get('netuid')}", "ℹ️")
                self.log_step("VALIDATOR_INTEGRATION", f"   Available miners: {network_info.get('available_miners')}", "ℹ️")
                
                # Store miner info for later use
                self.miners = integration_data.get('miners', [])
                return True
            else:
                self.log_step("VALIDATOR_INTEGRATION", f"❌ Integration failed - Status {response.status_code}", "❌")
                return False
        except Exception as e:
            self.log_step("VALIDATOR_INTEGRATION", f"❌ Integration error - {str(e)}", "❌")
            return False
    
    def create_test_audio(self):
        """Create a simple test audio file for transcription"""
        try:
            # Create a simple WAV file with sine wave
            import numpy as np
            import soundfile as sf
            import io
            
            # Generate 2 seconds of 440 Hz sine wave
            sample_rate = 16000
            duration = 2.0
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            audio_data = np.sin(2 * np.pi * 440 * t) * 0.3
            
            # Save to bytes
            audio_bytes = io.BytesIO()
            sf.write(audio_bytes, audio_data, sample_rate, format='WAV')
            audio_bytes.seek(0)
            
            return audio_bytes.read(), "test_audio.wav"
        except ImportError:
            # Fallback: create a dummy audio file
            dummy_audio = b"RIFF" + b"\x00" * 40 + b"WAVE"
            return dummy_audio, "test_audio.wav"
    
    def test_task_submission(self):
        """Test 3: Submit tasks to proxy server"""
        self.log_step("TASK_SUBMISSION", "Submitting test tasks...")
        
        tasks_submitted = 0
        
        # Test 1: Transcription task
        try:
            self.log_step("TASK_SUBMISSION", "Submitting transcription task...")
            audio_content, filename = self.create_test_audio()
            
            files = {'audio_file': (filename, audio_content, 'audio/wav')}
            data = {
                'source_language': 'en',
                'priority': 'normal'
            }
            
            response = requests.post(f"{PROXY_SERVER_URL}/api/v1/transcription", files=files, data=data)
            
            if response.status_code == 200:
                data = response.json()
                task_id = data['task_id']
                self.task_ids['transcription'] = task_id
                self.log_step("TASK_SUBMISSION", f"✅ Transcription task submitted: {task_id[:8]}...", "✅")
                tasks_submitted += 1
            else:
                self.log_step("TASK_SUBMISSION", f"❌ Transcription failed: {response.status_code}", "❌")
        except Exception as e:
            self.log_step("TASK_SUBMISSION", f"❌ Transcription error: {str(e)}", "❌")
        
        # Test 2: TTS task
        try:
            self.log_step("TASK_SUBMISSION", "Submitting TTS task...")
            tts_data = {
                "text": "Hello, this is a test for text-to-speech conversion. The system should process this text and convert it to audio.",
                "source_language": "en",
                "priority": "normal"
            }
            
            response = requests.post(f"{PROXY_SERVER_URL}/api/v1/tts", json=tts_data)
            
            if response.status_code == 200:
                data = response.json()
                task_id = data['task_id']
                self.task_ids['tts'] = task_id
                self.log_step("TASK_SUBMISSION", f"✅ TTS task submitted: {task_id[:8]}...", "✅")
                tasks_submitted += 1
            else:
                self.log_step("TASK_SUBMISSION", f"❌ TTS failed: {response.status_code}", "❌")
        except Exception as e:
            self.log_step("TASK_SUBMISSION", f"❌ TTS error: {str(e)}", "❌")
        
        # Test 3: Summarization task
        try:
            self.log_step("TASK_SUBMISSION", "Submitting summarization task...")
            long_text = """
            Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to the natural intelligence displayed by humans and animals. 
            Leading AI textbooks define the field as the study of "intelligent agents": any device that perceives its environment and takes actions that maximize its chance of successfully achieving its goals. 
            Colloquially, the term "artificial intelligence" is often used to describe machines that mimic "cognitive" functions that humans associate with the human mind, such as "learning" and "problem solving".
            
            As machines become increasingly capable, tasks considered to require "intelligence" are often removed from the definition of AI, a phenomenon known as the AI effect. 
            A quip in Tesler's Theorem says "AI is whatever hasn't been done yet." For instance, optical character recognition is frequently excluded from things considered to be AI, having become a routine technology.
            
            Modern machine learning capabilities, however, have achieved narrow AI surpassing humans in specific tasks such as playing chess, proving mathematical theorems, driving cars, and detecting fraudulent credit card transactions.
            """
            
            summarization_data = {
                "text": long_text.strip(),
                "source_language": "en",
                "priority": "normal"
            }
            
            response = requests.post(f"{PROXY_SERVER_URL}/api/v1/summarization", json=summarization_data)
            
            if response.status_code == 200:
                data = response.json()
                task_id = data['task_id']
                self.task_ids['summarization'] = task_id
                self.log_step("TASK_SUBMISSION", f"✅ Summarization task submitted: {task_id[:8]}...", "✅")
                tasks_submitted += 1
            else:
                self.log_step("TASK_SUBMISSION", f"❌ Summarization failed: {response.status_code}", "❌")
        except Exception as e:
            self.log_step("TASK_SUBMISSION", f"❌ Summarization error: {str(e)}", "❌")
        
        self.log_step("TASK_SUBMISSION", f"📊 Total tasks submitted: {tasks_submitted}/3", "📊")
        return tasks_submitted > 0
    
    def test_task_distribution(self):
        """Test 4: Distribute tasks to validator"""
        self.log_step("TASK_DISTRIBUTION", "Distributing tasks to validator...")
        
        try:
            response = requests.post(f"{PROXY_SERVER_URL}/api/v1/validator/distribute", timeout=10)
            
            if response.status_code == 200:
                distribute_data = response.json()
                self.log_step("TASK_DISTRIBUTION", f"✅ Tasks distributed successfully", "✅")
                self.log_step("TASK_DISTRIBUTION", f"   Tasks distributed: {distribute_data.get('task_count')}", "ℹ️")
                self.log_step("TASK_DISTRIBUTION", f"   Message: {distribute_data.get('message')}", "ℹ️")
                return True
            else:
                self.log_step("TASK_DISTRIBUTION", f"❌ Distribution failed - Status {response.status_code}", "❌")
                return False
        except Exception as e:
            self.log_step("TASK_DISTRIBUTION", f"❌ Distribution error - {str(e)}", "❌")
            return False
    
    def monitor_task_processing(self, max_wait_time=120):
        """Test 5: Monitor task processing and completion"""
        self.log_step("TASK_MONITORING", f"Monitoring task processing (max wait: {max_wait_time}s)...")
        
        start_time = time.time()
        completed_tasks = 0
        total_tasks = len(self.task_ids)
        
        while time.time() - start_time < max_wait_time:
            current_time = time.time()
            elapsed = current_time - start_time
            
            self.log_step("TASK_MONITORING", f"Checking task status... (elapsed: {elapsed:.0f}s)", "⏳")
            
            # Check each task
            for task_type, task_id in self.task_ids.items():
                if task_id in self.test_results:
                    continue  # Already completed
                
                try:
                    response = requests.get(f"{PROXY_SERVER_URL}/api/v1/tasks/{task_id}")
                    
                    if response.status_code == 200:
                        task_data = response.json()
                        status = task_data.get('status')
                        
                        if status == 'completed':
                            self.test_results[task_id] = task_data
                            completed_tasks += 1
                            
                            result = task_data.get('result', {})
                            self.log_step("TASK_MONITORING", f"✅ {task_type} completed!", "✅")
                            self.log_step("TASK_MONITORING", f"   Processing time: {result.get('processing_time', 'Unknown')}s", "ℹ️")
                            self.log_step("TASK_MONITORING", f"   Accuracy score: {result.get('accuracy_score', 'Unknown')}", "ℹ️")
                            self.log_step("TASK_MONITORING", f"   Miner UID: {result.get('miner_uid', 'Unknown')}", "ℹ️")
                            
                        elif status == 'failed':
                            self.test_results[task_id] = task_data
                            completed_tasks += 1
                            
                            error_msg = task_data.get('error_message', 'Unknown error')
                            self.log_step("TASK_MONITORING", f"❌ {task_type} failed: {error_msg}", "❌")
                            
                        elif status == 'processing':
                            self.log_step("TASK_MONITORING", f"⏳ {task_type} processing...", "⏳")
                            
                        else:  # pending
                            self.log_step("TASK_MONITORING", f"⏳ {task_type} pending...", "⏳")
                    
                    else:
                        self.log_step("TASK_MONITORING", f"⚠️  Could not check {task_type} status: {response.status_code}", "⚠️")
                        
                except Exception as e:
                    self.log_step("TASK_MONITORING", f"⚠️  Error checking {task_type}: {str(e)}", "⚠️")
            
            # Check if all tasks are completed
            if completed_tasks >= total_tasks:
                self.log_step("TASK_MONITORING", f"🎉 All tasks completed! ({completed_tasks}/{total_tasks})", "🎉")
                break
            
            # Wait before next check
            time.sleep(5)
        
        # Final status check
        if completed_tasks >= total_tasks:
            self.log_step("TASK_MONITORING", "✅ All tasks processed successfully", "✅")
            return True
        else:
            self.log_step("TASK_MONITORING", f"⚠️  Only {completed_tasks}/{total_tasks} tasks completed", "⚠️")
            return False
    
    def test_final_results(self):
        """Test 6: Verify final results and response quality"""
        self.log_step("FINAL_RESULTS", "Analyzing final results...")
        
        successful_tasks = 0
        total_tasks = len(self.test_results)
        
        for task_id, task_data in self.test_results.items():
            if task_data.get('status') == 'completed':
                successful_tasks += 1
                
                result = task_data.get('result', {})
                task_type = task_data.get('task_type', 'unknown')
                
                self.log_step("FINAL_RESULTS", f"📊 {task_type.upper()} Results:", "📊")
                self.log_step("FINAL_RESULTS", f"   Processing time: {result.get('processing_time', 'Unknown')}s", "ℹ️")
                self.log_step("FINAL_RESULTS", f"   Accuracy score: {result.get('accuracy_score', 'Unknown')}", "ℹ️")
                self.log_step("FINAL_RESULTS", f"   Speed score: {result.get('speed_score', 'Unknown')}", "ℹ️")
                self.log_step("FINAL_RESULTS", f"   Miner UID: {result.get('miner_uid', 'Unknown')}", "ℹ️")
                
                # Check if we have actual output data
                if result.get('output_data'):
                    self.log_step("FINAL_RESULTS", f"   Output data: Available", "✅")
                else:
                    self.log_step("FINAL_RESULTS", f"   Output data: Missing", "❌")
        
        self.log_step("FINAL_RESULTS", f"📈 Success Rate: {successful_tasks}/{total_tasks} ({successful_tasks/total_tasks*100:.1f}%)", "📈")
        
        return successful_tasks > 0
    
    def run_complete_workflow(self):
        """Run the complete workflow test"""
        print("🚀 COMPLETE WORKFLOW TEST")
        print("=" * 80)
        print("Testing: Proxy Server → Validator → Miner → Response")
        print("=" * 80)
        
        # Step 1: Check proxy server health
        if not self.test_proxy_server_health():
            print("❌ Cannot proceed - Proxy server is not healthy")
            return False
        
        # Step 2: Check validator integration
        if not self.test_validator_integration():
            print("❌ Cannot proceed - Validator integration failed")
            return False
        
        # Step 3: Submit tasks
        if not self.test_task_submission():
            print("❌ Cannot proceed - Task submission failed")
            return False
        
        # Step 4: Distribute tasks to validator
        if not self.test_task_distribution():
            print("❌ Cannot proceed - Task distribution failed")
            return False
        
        # Step 5: Monitor task processing
        if not self.monitor_task_processing():
            print("⚠️  Task monitoring completed with some issues")
        
        # Step 6: Analyze final results
        if not self.test_final_results():
            print("⚠️  Final results analysis completed with some issues")
        
        # Summary
        print("\n" + "=" * 80)
        print("🎯 WORKFLOW TEST SUMMARY")
        print("=" * 80)
        
        total_tasks = len(self.task_ids)
        completed_tasks = len([t for t in self.test_results.values() if t.get('status') == 'completed'])
        failed_tasks = len([t for t in self.test_results.values() if t.get('status') == 'failed'])
        
        print(f"📊 Total tasks submitted: {total_tasks}")
        print(f"✅ Successfully completed: {completed_tasks}")
        print(f"❌ Failed: {failed_tasks}")
        print(f"📈 Success rate: {completed_tasks/total_tasks*100:.1f}%" if total_tasks > 0 else "📈 Success rate: N/A")
        
        if completed_tasks > 0:
            print("\n🎉 WORKFLOW TEST PASSED!")
            print("   The complete pipeline is working: Proxy → Validator → Miner → Response")
        else:
            print("\n❌ WORKFLOW TEST FAILED!")
            print("   Some issues were encountered in the pipeline")
        
        return completed_tasks > 0

def main():
    """Main function to run the complete workflow test"""
    print("🧪 Starting Complete Workflow Test...")
    print("Make sure you have:")
    print("1. Proxy server running on http://localhost:8000")
    print("2. Validator running with proxy integration enabled")
    print("3. Miner running and connected to the network")
    print("4. Bittensor network connectivity")
    print()
    
    # Create and run test
    test = CompleteWorkflowTest()
    success = test.run_complete_workflow()
    
    if success:
        print("\n🚀 Ready to test with real data!")
        print("You can now submit real audio/text files through the proxy server endpoints.")
    else:
        print("\n⚠️  Some issues were found. Check the logs above for details.")

if __name__ == "__main__":
    main()
