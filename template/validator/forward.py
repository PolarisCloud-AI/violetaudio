# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import time
import random
import bittensor as bt
import numpy as np

from template.protocol import AudioTask
from template.validator.reward import get_rewards, run_validator_pipeline
from template.utils.uids import get_random_uids


async def forward(self):
    """
    The forward function is called by the validator every time step.
    It is responsible for querying the network and scoring the responses.

    This implementation:
    1. Logs all available miners with their details
    2. Selects a random task type (transcription, TTS, or summarization)
    3. Generates appropriate test data for the task
    4. Queries miners with the task
    5. Evaluates responses using the same pipelines
    6. Rewards miners based on speed, accuracy, and stake
    """
    
    # Log all available miners and test connectivity
    await log_available_miners(self)
    
    # Check if we have any reachable miners
    if not hasattr(self, 'reachable_miners') or not self.reachable_miners:
        bt.logging.warning("No reachable miners available. Skipping this round.")
        return
    
    # Select random task type
    task_types = ["transcription", "tts", "summarization"]
    selected_task = random.choice(task_types)
    
    # Generate test data based on task type
    test_data, placeholder_expected = generate_test_data(selected_task)
    
    # Run validator pipeline to get actual expected output
    bt.logging.info(f"🔬 Running validator pipeline for {selected_task}...")
    validator_output, validator_time, validator_model = run_validator_pipeline(
        selected_task, test_data, "en"
    )
    
    if validator_output:
        # Decode validator output for comparison
        dummy_task = AudioTask()
        if selected_task in ["transcription", "summarization"]:
            expected_output = dummy_task.decode_text(validator_output)
        else:
            expected_output = "audio_output_placeholder"  # For TTS
        
        bt.logging.info(f"✅ Validator pipeline completed in {validator_time:.2f}s using {validator_model}")
        bt.logging.info(f"📝 Expected output: {expected_output[:100]}...")
    else:
        bt.logging.warning(f"⚠️  Validator pipeline failed, using placeholder output")
        expected_output = placeholder_expected
    
    # Get random miner UIDs from reachable miners only (top 5 miners based on stake)
    available_uids = self.reachable_miners
    miner_uids = sorted(available_uids, key=lambda x: self.metagraph.S[x], reverse=True)[:min(5, len(available_uids))]
    
    bt.logging.info(f"🎯 SELECTED MINERS FOR QUERYING:")
    bt.logging.info(f"   - Task type: {selected_task}")
    bt.logging.info(f"   - Number of miners: {len(miner_uids)}")
    bt.logging.info(f"   - Selected UIDs: {miner_uids}")
    
    # Log details of selected miners
    for uid in miner_uids:
        if uid < len(self.metagraph.hotkeys):
            axon = self.metagraph.axons[uid]
            hotkey = self.metagraph.hotkeys[uid]
            stake = self.metagraph.S[uid]
            ip = axon.ip
            port = axon.port
            
            # Convert IP from int to string if needed
            if isinstance(ip, int):
                ip = f"{ip >> 24}.{(ip >> 16) & 255}.{(ip >> 8) & 255}.{ip & 255}"
            
            bt.logging.info(f"   📡 UID {uid}: {ip}:{port} | Hotkey: {hotkey[:20]}... | Stake: {stake:,.0f} TAO")
    
    bt.logging.info(f"\n🚀 SENDING {selected_task.upper()} TASK TO MINERS...")
    
    # Create synapse with test data
    synapse = AudioTask(
        task_type=selected_task,
        input_data=test_data,
        language="en"  # Default to English for testing
    )
    
    # Query miners
    responses = await self.dendrite(
        axons=[self.metagraph.axons[uid] for uid in miner_uids],
        synapse=synapse,
        deserialize=True,
    )

    # Log responses for monitoring
    bt.logging.info(f"📥 RECEIVED {len(responses)} RESPONSES:")
    for i, response in enumerate(responses):
        uid = miner_uids[i] if i < len(miner_uids) else "Unknown"
        status = response.dendrite.status_code if hasattr(response, 'dendrite') else "Unknown"
        bt.logging.info(f"   - UID {uid}: Status {status}")
    
    bt.logging.info(f"✅ Task completed: {selected_task}")
    
    # Evaluate responses and calculate rewards
    bt.logging.info(f"\n📊 EVALUATING MINER RESPONSES...")
    bt.logging.info("=" * 60)
    
    rewards = get_rewards(
        self, 
        task_type=selected_task,
        query=test_data,
        responses=responses,
        expected_output=expected_output,
        miner_uids=miner_uids
    )
    
        # Create ranking of miners based on rewards
    miner_rankings = []
    for i, reward in enumerate(rewards):
        if i < len(miner_uids):
            uid = miner_uids[i]
            stake = self.metagraph.S[uid]
            
            # Extract response data properly
            response_data = None
            if i < len(responses):
                response = responses[i]
                if hasattr(response, 'output_data'):
                    response_data = {
                        'output_data': response.output_data,
                        'processing_time': getattr(response, 'processing_time', None),
                        'pipeline_model': getattr(response, 'pipeline_model', None),
                        'error_message': getattr(response, 'error_message', None)
                    }
            
            miner_rankings.append({
                'uid': uid,
                'reward': reward,
                'stake': stake,
                'response': response_data
            })
    
    # Sort by reward (descending)
    miner_rankings.sort(key=lambda x: x['reward'], reverse=True)
    
    # Log rankings
    bt.logging.info(f"🏆 MINER RANKINGS FOR {selected_task.upper()} TASK:")
    bt.logging.info("-" * 60)
    
    for rank, miner in enumerate(miner_rankings, 1):
        uid = miner['uid']
        reward = miner['reward']
        stake = miner['stake']
        response = miner['response']
        
        # Get miner details
        hotkey = self.metagraph.hotkeys[uid] if uid < len(self.metagraph.hotkeys) else "Unknown"
        processing_time = response.get('processing_time', 0.0) if response else 0.0
        model_used = response.get('pipeline_model', 'Unknown') if response else 'Unknown'
        error_msg = response.get('error_message', None) if response else None
        
        status_icon = "✅" if reward > 0 and not error_msg else "❌"
        
        bt.logging.info(f"{rank:2d}. {status_icon} UID {uid:3d} | Reward: {reward:.4f} | Stake: {stake:,.0f} TAO")
        bt.logging.info(f"    🔑 Hotkey: {hotkey[:20]}...")
        bt.logging.info(f"    ⏱️  Time: {processing_time:.2f}s | Model: {model_used}")
        
        if error_msg:
            bt.logging.info(f"    ❌ Error: {error_msg}")
        elif response and response.get('output_data'):
            # Show sample of output
            try:
                dummy_task = AudioTask()
                if selected_task in ["transcription", "summarization"]:
                    output_text = dummy_task.decode_text(response['output_data'])
                    bt.logging.info(f"    📝 Output: {output_text[:80]}...")
                else:
                    bt.logging.info(f"    🎵 Output: Audio data ({len(response['output_data'])} chars)")
            except Exception as e:
                bt.logging.info(f"    📝 Output: [Decode error: {str(e)}]")
        
        bt.logging.info("")
    
    # Reward top 5 miners
    top_miners = miner_rankings[:5]
    bt.logging.info(f"🎁 REWARDING TOP {len(top_miners)} MINERS:")
    bt.logging.info("-" * 40)
    
    for rank, miner in enumerate(top_miners, 1):
        uid = miner['uid']
        reward = miner['reward']
        stake = miner['stake']
        
        # Calculate final reward (normalized)
        final_reward = reward / sum(m['reward'] for m in top_miners) if sum(m['reward'] for m in top_miners) > 0 else 0
        
        bt.logging.info(f"{rank}. UID {uid:3d} | Final Reward: {final_reward:.4f} | Stake: {stake:,.0f} TAO")
        
        # Update scores
        self.scores[uid] = final_reward
    
    # Log summary
    total_reward = sum(m['reward'] for m in miner_rankings)
    avg_reward = total_reward / len(miner_rankings) if miner_rankings else 0
    
    bt.logging.info(f"\n📈 EVALUATION SUMMARY:")
    bt.logging.info(f"   - Total miners evaluated: {len(miner_rankings)}")
    bt.logging.info(f"   - Average reward: {avg_reward:.4f}")
    bt.logging.info(f"   - Top reward: {miner_rankings[0]['reward']:.4f} (UID {miner_rankings[0]['uid']})")
    bt.logging.info(f"   - Bottom reward: {miner_rankings[-1]['reward']:.4f} (UID {miner_rankings[-1]['uid']})")
    bt.logging.info("=" * 60)
    
    # Sleep between iterations
    time.sleep(5)


async def log_available_miners(self):
    """
    Log only active and reachable miners with their details including IPs, ports, hotkeys, and stake.
    """
    bt.logging.info("=" * 80)
    bt.logging.info("🔍 SCANNING ACTIVE & REACHABLE MINERS")
    bt.logging.info("=" * 80)
    
    total_miners = len(self.metagraph.hotkeys)
    serving_miners = 0
    reachable_miners = []
    
    bt.logging.info(f"📊 Network Overview:")
    bt.logging.info(f"   - Total registered miners: {total_miners}")
    bt.logging.info(f"   - Current block: {self.block}")
    bt.logging.info(f"   - Network: {self.subtensor.chain_endpoint}")
    bt.logging.info(f"   - NetUID: {self.config.netuid}")
    
    bt.logging.info("\n🏗️  Testing Miner Connectivity...")
    bt.logging.info("-" * 80)
    
    # Test connectivity to each serving miner
    for uid in range(total_miners):
        axon = self.metagraph.axons[uid]
        hotkey = self.metagraph.hotkeys[uid]
        stake = self.metagraph.S[uid]
        is_serving = axon.is_serving
        
        if is_serving:
            serving_miners += 1
            
            # Get IP and port information
            ip = axon.ip
            port = axon.port
            
            # Convert IP from int to string if needed
            if isinstance(ip, int):
                ip = f"{ip >> 24}.{(ip >> 16) & 255}.{(ip >> 8) & 255}.{ip & 255}"
            
            # Test connectivity with a simple ping
            try:
                # Create a simple test task to check connectivity
                test_task = AudioTask(
                    task_type="transcription",
                    input_data="dGVzdA==",  # base64 for "test"
                    language="en"
                )
                
                # Try to connect with short timeout
                responses = await self.dendrite(
                    axons=[axon],
                    synapse=test_task,
                    deserialize=False,
                    timeout=3
                )
                
                if responses and len(responses) > 0:
                    response = responses[0]
                    status = response.dendrite.status_code if hasattr(response, 'dendrite') else "Unknown"
                    
                    # Consider miner reachable if we get any response (even errors are better than no response)
                    if status in [200, 400, 500]:  # Any HTTP response means it's reachable
                        reachable_miners.append(uid)
                        external_ip = getattr(axon, 'external_ip', 'N/A')
                        external_port = getattr(axon, 'external_port', 'N/A')
                        
                        bt.logging.info(f"✅ UID {uid:3d} | IP: {ip:15s} | Port: {port:5d} | Status: {status}")
                        bt.logging.info(f"   🔑 Hotkey: {hotkey[:20]}...")
                        bt.logging.info(f"   💰 Stake: {stake:,.0f} TAO")
                        bt.logging.info(f"   📡 External: {external_ip}:{external_port}")
                        bt.logging.info("")
                    else:
                        bt.logging.debug(f"⚠️  UID {uid:3d} | {ip}:{port} | Serving but unresponsive (Status: {status})")
                else:
                    bt.logging.debug(f"❌ UID {uid:3d} | {ip}:{port} | No response received")
                    
            except Exception as e:
                bt.logging.debug(f"❌ UID {uid:3d} | {ip}:{port} | Connection failed: {str(e)[:50]}...")
        else:
            bt.logging.debug(f"⭕ UID {uid:3d} | Hotkey: {hotkey[:20]}... | Status: OFFLINE")
    
    bt.logging.info("📈 Connectivity Statistics:")
    bt.logging.info(f"   - Total miners: {total_miners}")
    bt.logging.info(f"   - Serving miners: {serving_miners}")
    bt.logging.info(f"   - Reachable miners: {len(reachable_miners)}")
    bt.logging.info(f"   - Offline miners: {total_miners - serving_miners}")
    bt.logging.info(f"   - Reachability rate: {(len(reachable_miners)/total_miners)*100:.1f}%")
    
    if reachable_miners:
        bt.logging.info(f"\n🎯 Reachable UIDs for task assignment: {reachable_miners}")
        bt.logging.info(f"   - Top 5 by stake: {sorted(reachable_miners, key=lambda x: self.metagraph.S[x], reverse=True)[:5]}")
        
        # Store reachable miners for use in task assignment
        self.reachable_miners = reachable_miners
    else:
        bt.logging.warning("⚠️  No miners are currently reachable!")
        self.reachable_miners = []
    
    bt.logging.info("=" * 80)
    bt.logging.info("")


def generate_test_data(task_type: str) -> tuple:
    """
    Generate test data for different task types.

    Args:
        task_type: Type of task to generate data for
        
    Returns:
        Tuple of (input_data, expected_output)
    """
    if task_type == "transcription":
        # Generate test audio data (simple sine wave)
        import numpy as np
        import soundfile as sf
        import io
        
        # Create a simple test audio (440 Hz sine wave for 2 seconds)
        sample_rate = 16000
        duration = 2.0
        frequency = 440.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.3
        
        # Save to bytes
        audio_bytes = io.BytesIO()
        sf.write(audio_bytes, audio_data, sample_rate, format='WAV')
        audio_bytes.seek(0)
        
        # Create a dummy AudioTask instance for encoding
        dummy_task = AudioTask()
        encoded_audio = dummy_task.encode_audio(audio_bytes.read())
        
        # Expected output (what we expect from Whisper)
        expected_output = "A sine wave tone at 440 hertz."
        
        return encoded_audio, expected_output
    
    elif task_type == "tts":
        # Generate test text for TTS
        test_text = "Hello, this is a test for text to speech conversion."
        dummy_task = AudioTask()
        encoded_text = dummy_task.encode_text(test_text)
        
        # Expected output (placeholder for audio)
        expected_output = "audio_output_placeholder"
        
        return encoded_text, expected_output
    
    elif task_type == "summarization":
        # Generate test text for summarization
        test_text = "This is a long text that needs to be summarized. It contains multiple sentences and should be reduced to a shorter version while preserving the key information. The summarization process should extract the key points and create a concise version of the original text."
        dummy_task = AudioTask()
        encoded_text = dummy_task.encode_text(test_text)
        
        # Expected output (what we expect from BART)
        expected_output = "This text needs summarization to extract key points and create a concise version."
        
        return encoded_text, expected_output
    
    else:
        raise ValueError(f"Unknown task type: {task_type}")
