#!/usr/bin/env python3
"""
Test with a different approach to fix the synapse routing issue.
This test will try different methods to ensure the synapse name is properly set.
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

async def test_fixed_protocol():
    """Test with fixed protocol approach."""
    print("🔧 TEST: Fixed Protocol Approach")
    print("=" * 50)
    
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
            print(f"   🟢 Serving: {axon.is_serving}")
            
            if axon.is_serving:
                print("4. Testing with explicit synapse type...")
                
                # Create test audio
                audio_bytes = create_test_audio()
                dummy_task = AudioTask(
                    task_type="transcription",
                    input_data="dGVzdA==",  # base64 for "test"
                    language="en"
                )
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
                
                start_time = time.time()
                
                # Try different approaches to ensure synapse name is set
                
                # Approach 1: Use the synapse directly without deserialize
                print("\n   🔧 Approach 1: Direct synapse call...")
                try:
                    responses = await dendrite(
                        axons=[axon],
                        synapse=transcription_task,
                        deserialize=False,  # Don't deserialize to see raw response
                        timeout=60
                    )
                    
                    if responses and len(responses) > 0:
                        response = responses[0]
                        print(f"   📥 Raw response type: {type(response)}")
                        
                        if hasattr(response, 'output_data'):
                            print(f"   📥 Output data: {response.output_data}")
                            if response.output_data:
                                output_text = dummy_task.decode_text(response.output_data)
                                print(f"   📝 Decoded output: {output_text}")
                                print("   ✅ SUCCESS! Forward function was called!")
                                return True
                        else:
                            print("   ❌ No output_data attribute")
                    else:
                        print("   ❌ No responses received")
                        
                except Exception as e:
                    print(f"   ❌ Approach 1 failed: {e}")
                
                # Approach 2: Try with different timeout
                print("\n   🔧 Approach 2: Different timeout...")
                try:
                    responses = await dendrite(
                        axons=[axon],
                        synapse=transcription_task,
                        deserialize=True,
                        timeout=120  # Longer timeout
                    )
                    
                    if responses and len(responses) > 0:
                        response = responses[0]
                        print(f"   📥 Response type: {type(response)}")
                        
                        if isinstance(response, dict):
                            for key, value in response.items():
                                if value is not None:
                                    print(f"   📋 {key}: {value}")
                                    if key == 'output_data' and value:
                                        output_text = dummy_task.decode_text(value)
                                        print(f"   📝 Decoded output: {output_text}")
                                        print("   ✅ SUCCESS! Forward function was called!")
                                        return True
                        else:
                            print("   ❌ Unexpected response type")
                    else:
                        print("   ❌ No responses received")
                        
                except Exception as e:
                    print(f"   ❌ Approach 2 failed: {e}")
                
                print("\n   ❌ All approaches failed")
                return False
                    
            else:
                print(f"   ❌ Miner at UID {target_uid} is not serving")
                return False
                
        else:
            print(f"   ❌ UID {target_uid} not found in metagraph")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fixed_protocol())
    if success:
        print("\n🎉 Protocol test succeeded!")
    else:
        print("\n💥 Protocol test failed.")
    sys.exit(0 if success else 1)
