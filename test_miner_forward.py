#!/usr/bin/env python3
"""
Test to verify if the miner's forward function is being called.
This will help us understand if the issue is in the forward function or elsewhere.
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

async def test_miner_forward():
    """Test if the miner's forward function is being called."""
    print("🔍 TEST: Miner Forward Function")
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
                print("4. Testing forward function...")
                
                # Create a simple test task
                test_task = AudioTask(
                    task_type="transcription",
                    input_data="dGVzdA==",  # base64 for "test"
                    language="en"
                )
                
                print("   📤 Sending test task...")
                
                # Send the request
                responses = await dendrite(
                    axons=[axon],
                    synapse=test_task,
                    deserialize=True,
                    timeout=60
                )
                
                print(f"   📥 Responses received: {len(responses) if responses else 0}")
                
                if responses and len(responses) > 0:
                    response = responses[0]
                    
                    # Check if this is a dictionary (deserialized response)
                    if isinstance(response, dict):
                        print("   📋 Response is a dictionary (deserialized)")
                        
                        # Check if any fields have been processed
                        processed_fields = []
                        for key, value in response.items():
                            if value is not None:
                                processed_fields.append(f"{key}: {value}")
                        
                        if processed_fields:
                            print("   ✅ Forward function was called and processed data!")
                            print("   📊 Processed fields:")
                            for field in processed_fields:
                                print(f"      - {field}")
                        else:
                            print("   ❌ Forward function was not called or did not process data")
                            print("   📊 All fields are None")
                            
                    else:
                        print(f"   📋 Response type: {type(response)}")
                        print("   ❌ Unexpected response type")
                        
                else:
                    print("   ❌ No responses received")
                    
            else:
                print(f"   ❌ Miner at UID {target_uid} is not serving")
                
        else:
            print(f"   ❌ UID {target_uid} not found in metagraph")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_miner_forward())

