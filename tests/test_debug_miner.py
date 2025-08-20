#!/usr/bin/env python3
"""
Debug test to see exactly what's happening with the miner.
This test will show us the complete flow and identify where the issue is.
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

def create_test_audio(duration=2.0, sample_rate=16000, frequency=440.0):
    """Create a simple test audio file."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(2 * np.pi * frequency * t) * 0.3
    
    # Save to bytes
    audio_bytes = io.BytesIO()
    sf.write(audio_bytes, audio_data, sample_rate, format='WAV')
    audio_bytes.seek(0)
    return audio_bytes.read()

async def debug_miner_communication():
    """Debug the miner communication step by step."""
    print("🔍 DEBUG: Miner Communication Analysis")
    print("=" * 60)
    
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
            print(f"3. Found miner at UID {target_uid}")
            print(f"   📍 IP: {axon.ip}")
            print(f"   🔌 Port: {axon.port}")
            print(f"   🔑 Hotkey: {axon.hotkey}")
            print(f"   🟢 Serving: {axon.is_serving}")
            
            if axon.is_serving:
                print("4. Testing communication...")
                
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
                print(f"   📝 Task type: {transcription_task.task_type}")
                print(f"   📊 Input data length: {len(transcription_task.input_data)}")
                print(f"   🌍 Language: {transcription_task.language}")
                
                start_time = time.time()
                
                # Use the proper Bittensor dendrite call
                responses = await dendrite(
                    axons=[axon],
                    synapse=transcription_task,
                    deserialize=True,
                    timeout=60
                )
                
                end_time = time.time()
                total_time = end_time - start_time
                
                print(f"   ⏱️  Total communication time: {total_time:.2f}s")
                print(f"   📥 Number of responses: {len(responses) if responses else 0}")
                
                if responses and len(responses) > 0:
                    response = responses[0]
                    print("   ✅ Received response from miner!")
                    
                    # Debug response object
                    print("\n   🔍 RESPONSE DEBUG:")
                    print(f"   📋 Response type: {type(response)}")
                    print(f"   📋 Response dir: {[attr for attr in dir(response) if not attr.startswith('_')]}")
                    
                    # Check if we have a dendrite object with status
                    if hasattr(response, 'dendrite'):
                        print(f"   📥 Dendrite status: {response.dendrite.status_code}")
                        print(f"   📥 Dendrite message: {getattr(response.dendrite, 'status_message', 'No message')}")
                    else:
                        print("   ❌ No dendrite object in response")
                    
                    # Check all attributes
                    for attr in ['output_data', 'processing_time', 'pipeline_model', 'error_message', 'task_type', 'input_data', 'language']:
                        value = getattr(response, attr, None)
                        print(f"   📋 {attr}: {value}")
                    
                    # Check if we got output data
                    if hasattr(response, 'output_data') and response.output_data:
                        print("   ✅ Output data received!")
                        try:
                            output_text = dummy_task.decode_text(response.output_data)
                            print(f"   📝 Decoded output: {output_text}")
                        except Exception as e:
                            print(f"   ❌ Error decoding output: {e}")
                    else:
                        print("   ❌ No output data in response")
                        
                else:
                    print("   ❌ No responses received")
                    
            else:
                print(f"   ❌ Miner at UID {target_uid} is not serving")
                
        else:
            print(f"   ❌ UID {target_uid} not found in metagraph")
            
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_miner_communication())

