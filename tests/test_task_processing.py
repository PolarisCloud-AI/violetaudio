#!/usr/bin/env python3
"""
Comprehensive test for the complete task processing and evaluation system.
This test verifies that:
1. Miner receives tasks and applies appropriate pipelines
2. Miner returns proper feedback with output data
3. Validator evaluates responses and scores miners
4. Complete end-to-end task processing works
"""

import sys
import os
import asyncio
import bittensor as bt
import numpy as np
import soundfile as sf
import io
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from template.protocol import AudioTask
from template.validator.reward import run_validator_pipeline, calculate_accuracy_score, calculate_speed_score, calculate_stake_score

def create_test_audio(duration=2.0, sample_rate=16000, frequency=440.0):
    """Create a simple test audio file."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(2 * np.pi * frequency * t) * 0.3
    
    # Save to bytes
    audio_bytes = io.BytesIO()
    sf.write(audio_bytes, audio_data, sample_rate, format='WAV')
    audio_bytes.seek(0)
    return audio_bytes.read()

async def test_complete_task_processing():
    """Test the complete task processing pipeline."""
    print("🚀 Complete Task Processing Test")
    print("=" * 80)
    
    try:
        # Initialize Bittensor components
        print("1. Initializing Bittensor components...")
        wallet = bt.wallet(name="luno", hotkey="arusha")
        subtensor = bt.subtensor(network="finney")
        metagraph = subtensor.metagraph(netuid=49)
        dendrite = bt.dendrite(wallet=wallet)
        
        print("   ✅ Components initialized")
        
        # Sync metagraph
        print("2. Syncing metagraph...")
        metagraph.sync(subtensor=subtensor)
        print(f"   ✅ Metagraph synced - {len(metagraph.hotkeys)} total miners")
        
        # Find our miner (UID 48)
        target_uid = 48
        if target_uid < len(metagraph.hotkeys):
            axon = metagraph.axons[target_uid]
            if axon.is_serving:
                print(f"3. Testing complete task processing with our miner at UID {target_uid}...")
                
                # Test 1: Transcription Task
                print("\n📝 TEST 1: TRANSCRIPTION TASK")
                print("-" * 40)
                
                # Create test audio
                audio_bytes = create_test_audio()
                dummy_task = AudioTask()
                encoded_audio = dummy_task.encode_audio(audio_bytes)
                
                # Create transcription task
                transcription_task = AudioTask(
                    task_type="transcription",
                    input_data=encoded_audio,
                    language="en"
                )
                
                print("   📤 Sending transcription task to miner...")
                start_time = time.time()
                
                responses = await dendrite(
                    axons=[axon],
                    synapse=transcription_task,
                    deserialize=True,
                    timeout=60,
                    headers={'bt_header_synapse_name': 'AudioTask'}
                )
                
                end_time = time.time()
                total_time = end_time - start_time
                
                if responses and len(responses) > 0:
                    response = responses[0]
                    status = response.dendrite.status_code if hasattr(response, 'dendrite') else "Unknown"
                    print(f"   📥 Received response - Status: {status}")
                    print(f"   ⏱️  Total communication time: {total_time:.2f}s")
                    
                    if status == 200:
                        print("   ✅ Communication successful!")
                        
                        # Check response data
                        if hasattr(response, 'output_data') and response.output_data:
                            try:
                                output_text = dummy_task.decode_text(response.output_data)
                                processing_time = getattr(response, 'processing_time', None)
                                model_used = getattr(response, 'pipeline_model', None)
                                error_msg = getattr(response, 'error_message', None)
                                
                                print(f"   📝 Miner output: {output_text}")
                                print(f"   ⏱️  Processing time: {processing_time:.2f}s" if processing_time else "   ⏱️  Processing time: Unknown")
                                print(f"   🔧 Model used: {model_used}" if model_used else "   🔧 Model used: Unknown")
                                
                                if error_msg:
                                    print(f"   ❌ Error message: {error_msg}")
                                else:
                                    print("   ✅ No errors reported")
                                
                                # Run validator pipeline for comparison
                                print("\n   🔬 Running validator pipeline for comparison...")
                                validator_output, validator_time, validator_model = run_validator_pipeline(
                                    "transcription", encoded_audio, "en"
                                )
                                
                                if validator_output:
                                    expected_text = dummy_task.decode_text(validator_output)
                                    print(f"   📝 Validator expected: {expected_text}")
                                    
                                    # Calculate accuracy
                                    accuracy = calculate_accuracy_score(output_text, expected_text, "transcription")
                                    print(f"   📊 Accuracy score: {accuracy:.4f}")
                                    
                                    # Calculate speed score
                                    speed_score = calculate_speed_score(processing_time if processing_time else 10.0)
                                    print(f"   ⚡ Speed score: {speed_score:.4f}")
                                    
                                    # Overall assessment
                                    if accuracy > 0.5:
                                        print("   🎉 Transcription task completed successfully!")
                                        transcription_success = True
                                    else:
                                        print("   ⚠️  Transcription accuracy is low")
                                        transcription_success = False
                                else:
                                    print("   ❌ Validator pipeline failed")
                                    transcription_success = False
                                    
                            except Exception as e:
                                print(f"   ❌ Error decoding response: {str(e)}")
                                transcription_success = False
                        else:
                            print("   ❌ No output data received")
                            transcription_success = False
                    else:
                        print(f"   ❌ Communication failed with status: {status}")
                        transcription_success = False
                else:
                    print("   ❌ No response received")
                    transcription_success = False
                
                # Test 2: Summarization Task
                print("\n📋 TEST 2: SUMMARIZATION TASK")
                print("-" * 40)
                
                # Create test text for summarization
                test_text = "This is a long text that needs to be summarized. It contains multiple sentences and should be reduced to a shorter version while preserving the key information. The summarization process should extract the key points and create a concise version of the original text."
                encoded_text = dummy_task.encode_text(test_text)
                
                # Create summarization task
                summarization_task = AudioTask(
                    task_type="summarization",
                    input_data=encoded_text,
                    language="en"
                )
                
                print("   📤 Sending summarization task to miner...")
                start_time = time.time()
                
                responses = await dendrite(
                    axons=[axon],
                    synapse=summarization_task,
                    deserialize=True,
                    timeout=60,
                    headers={'bt_header_synapse_name': 'AudioTask'}
                )
                
                end_time = time.time()
                total_time = end_time - start_time
                
                if responses and len(responses) > 0:
                    response = responses[0]
                    status = response.dendrite.status_code if hasattr(response, 'dendrite') else "Unknown"
                    print(f"   📥 Received response - Status: {status}")
                    print(f"   ⏱️  Total communication time: {total_time:.2f}s")
                    
                    if status == 200:
                        print("   ✅ Communication successful!")
                        
                        # Check response data
                        if hasattr(response, 'output_data') and response.output_data:
                            try:
                                output_text = dummy_task.decode_text(response.output_data)
                                processing_time = getattr(response, 'processing_time', None)
                                model_used = getattr(response, 'pipeline_model', None)
                                error_msg = getattr(response, 'error_message', None)
                                
                                print(f"   📝 Miner summary: {output_text}")
                                print(f"   ⏱️  Processing time: {processing_time:.2f}s" if processing_time else "   ⏱️  Processing time: Unknown")
                                print(f"   🔧 Model used: {model_used}" if model_used else "   🔧 Model used: Unknown")
                                
                                if error_msg:
                                    print(f"   ❌ Error message: {error_msg}")
                                else:
                                    print("   ✅ No errors reported")
                                
                                # Run validator pipeline for comparison
                                print("\n   🔬 Running validator pipeline for comparison...")
                                validator_output, validator_time, validator_model = run_validator_pipeline(
                                    "summarization", encoded_text, "en"
                                )
                                
                                if validator_output:
                                    expected_text = dummy_task.decode_text(validator_output)
                                    print(f"   📝 Validator expected: {expected_text}")
                                    
                                    # Calculate accuracy
                                    accuracy = calculate_accuracy_score(output_text, expected_text, "summarization")
                                    print(f"   📊 Accuracy score: {accuracy:.4f}")
                                    
                                    # Calculate speed score
                                    speed_score = calculate_speed_score(processing_time if processing_time else 10.0)
                                    print(f"   ⚡ Speed score: {speed_score:.4f}")
                                    
                                    # Overall assessment
                                    if accuracy > 0.3:  # Lower threshold for summarization
                                        print("   🎉 Summarization task completed successfully!")
                                        summarization_success = True
                                    else:
                                        print("   ⚠️  Summarization accuracy is low")
                                        summarization_success = False
                                else:
                                    print("   ❌ Validator pipeline failed")
                                    summarization_success = False
                                    
                            except Exception as e:
                                print(f"   ❌ Error decoding response: {str(e)}")
                                summarization_success = False
                        else:
                            print("   ❌ No output data received")
                            summarization_success = False
                    else:
                        print(f"   ❌ Communication failed with status: {status}")
                        summarization_success = False
                else:
                    print("   ❌ No response received")
                    summarization_success = False
                
                # Summary
                print("\n" + "=" * 80)
                print("📋 TASK PROCESSING SUMMARY")
                print("=" * 80)
                
                results = [
                    ("Transcription Task", transcription_success),
                    ("Summarization Task", summarization_success)
                ]
                
                passed = 0
                total = len(results)
                
                for test_name, result in results:
                    status = "✅ PASSED" if result else "❌ FAILED"
                    print(f"{test_name:20s}: {status}")
                    if result:
                        passed += 1
                
                print(f"\nOverall: {passed}/{total} tasks completed successfully")
                
                if passed == total:
                    print("🎉 All tasks completed successfully! The miner is working correctly.")
                    return True
                else:
                    print("💥 Some tasks failed. Check the errors above.")
                    return False
                    
            else:
                print(f"   ❌ Miner at UID {target_uid} is not serving")
                return False
        else:
            print(f"   ❌ UID {target_uid} not found in metagraph")
            return False
            
    except Exception as e:
        print(f"❌ Task processing test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_complete_task_processing())
    sys.exit(0 if success else 1)
