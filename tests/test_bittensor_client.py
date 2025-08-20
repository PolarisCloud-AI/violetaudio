#!/usr/bin/env python3
"""
Proper Bittensor client test using the correct protocol.
This test uses the actual Bittensor dendrite to communicate with the miner.
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

async def test_bittensor_protocol():
    """Test the Bittensor protocol communication."""
    print("🚀 Bittensor Protocol Test")
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
            if axon.is_serving:
                print(f"3. Testing Bittensor protocol with our miner at UID {target_uid}...")
                
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
                
                # Use the proper Bittensor dendrite call
                responses = await dendrite(
                    axons=[axon],
                    synapse=transcription_task,
                    deserialize=True,
                    timeout=60
                )
                
                end_time = time.time()
                total_time = end_time - start_time
                
                if responses and len(responses) > 0:
                    response = responses[0]
                    
                    # Check if we have a dendrite object with status
                    if hasattr(response, 'dendrite'):
                        status = response.dendrite.status_code
                        print(f"   📥 Received response - Status: {status}")
                    else:
                        status = "Unknown"
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
                                    print("   🎉 Transcription task completed successfully!")
                                    return True
                                    
                            except Exception as e:
                                print(f"   ❌ Error decoding response: {str(e)}")
                                return False
                        else:
                            print("   ❌ No output data received")
                            return False
                    else:
                        print(f"   ❌ Communication failed with status: {status}")
                        
                        # Try to get more details about the error
                        if hasattr(response, 'dendrite') and hasattr(response.dendrite, 'status_message'):
                            print(f"   📋 Error message: {response.dendrite.status_message}")
                        
                        return False
                else:
                    print("   ❌ No response received")
                    return False
                    
            else:
                print(f"   ❌ Miner at UID {target_uid} is not serving")
                return False
        else:
            print(f"   ❌ UID {target_uid} not found in metagraph")
            return False
            
    except Exception as e:
        print(f"❌ Bittensor protocol test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_bittensor_protocol())
    if success:
        print("\n🎉 Bittensor protocol test passed!")
    else:
        print("\n💥 Bittensor protocol test failed.")
    sys.exit(0 if success else 1)

