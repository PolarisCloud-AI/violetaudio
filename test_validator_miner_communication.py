#!/usr/bin/env python3
"""
Test script to verify validator-miner communication on the Bittensor network.
This script will check if the validator can see the miner and send a test request.
"""

import sys
import os
import asyncio
import bittensor as bt

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from template.protocol import AudioTask, TaskType


async def test_validator_miner_communication():
    """Test communication between validator and miner."""
    print("🔍 Testing Validator-Miner Communication")
    print("=" * 60)
    
    try:
        # Initialize validator components
        print("1. Initializing validator components...")
        
        # Use simple initialization
        wallet = bt.wallet(name="luno", hotkey="arusha")
        subtensor = bt.subtensor(network="finney")
        metagraph = subtensor.metagraph(netuid=49)
        dendrite = bt.dendrite(wallet=wallet)
        
        print("✅ Validator components initialized")
        
        # Sync metagraph
        print("\n2. Syncing metagraph...")
        metagraph.sync(subtensor=subtensor)
        print(f"✅ Metagraph synced - {len(metagraph.hotkeys)} total miners")
        
        # Find available miners
        print("\n3. Scanning for available miners...")
        available_miners = []
        
        for uid in range(len(metagraph.hotkeys)):
            axon = metagraph.axons[uid]
            if axon.is_serving:
                available_miners.append(uid)
                hotkey = metagraph.hotkeys[uid]
                stake = metagraph.S[uid]
                ip = axon.ip
                port = axon.port
                
                # Convert IP from int to string if needed
                if isinstance(ip, int):
                    ip = f"{ip >> 24}.{(ip >> 16) & 255}.{(ip >> 8) & 255}.{ip & 255}"
                
                print(f"   ✅ UID {uid}: {ip}:{port} | Hotkey: {hotkey[:20]}... | Stake: {stake:,.0f} TAO")
        
        print(f"\n📊 Found {len(available_miners)} available miners")
        
        if not available_miners:
            print("❌ No miners are currently serving!")
            return False
        
        # Test communication with our miner (UID 48)
        target_uid = 48  # Our miner
        if target_uid in available_miners:
            print(f"\n4. Testing communication with our miner at UID {target_uid}...")
        else:
            print(f"\n4. Testing communication with UID {available_miners[0]}...")
            target_uid = available_miners[0]
        
        # Create a simple test task
        test_task = AudioTask(
            task_type="transcription",
            input_data="test_audio_data_base64_encoded",
            language="en"
        )
        
        # Send test request
        print("   📤 Sending test request...")
        responses = await dendrite(
            axons=[metagraph.axons[target_uid]],
            synapse=test_task,
            deserialize=True,
            timeout=10
        )
        
        if responses and len(responses) > 0:
            response = responses[0]
            status = response.dendrite.status_code if hasattr(response, 'dendrite') else "Unknown"
            print(f"   📥 Received response - Status: {status}")
            
            # Print more details about the response
            if hasattr(response, 'dendrite'):
                print(f"   📋 Response details:")
                print(f"      - Status message: {getattr(response.dendrite, 'status_message', 'N/A')}")
                print(f"      - Process time: {getattr(response.dendrite, 'process_time', 'N/A')}")
                print(f"      - Output data: {getattr(response, 'output_data', 'N/A')}")
                print(f"      - Processing time: {getattr(response, 'processing_time', 'N/A')}")
                print(f"      - Error message: {getattr(response, 'error_message', 'N/A')}")
            
            if status == 200:
                print("✅ Communication successful!")
                return True
            elif status in [400, 500]:
                print(f"⚠️  Communication reached miner but got error: {status}")
                return True  # Still consider it successful communication
            else:
                print(f"⚠️  Communication failed with status: {status}")
                return False
        else:
            print("❌ No response received")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Validator-Miner Communication Test")
    print("=" * 60)
    
    success = asyncio.run(test_validator_miner_communication())
    
    if success:
        print("\n🎉 Communication test passed! Validator can see and communicate with miners.")
    else:
        print("\n💥 Communication test failed. Check the error messages above.")
