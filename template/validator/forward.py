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
from template.validator.miner_tracker import MinerTracker


async def forward(self):
    """
    Main forward function that:
    1. Scans for available miners
    2. Selects a random task type
    3. Generates test data
    4. Sends tasks to selected miners
    5. Evaluates responses using the same pipelines
    6. Rewards miners based on speed, accuracy, and stake
    """
    
    # Check miner connectivity and register them
    await self.check_miner_connectivity()
    
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
        dummy_task = AudioTask(input_data="dummy", task_type=selected_task, language="en")
        if selected_task in ["transcription", "summarization"]:
            expected_output = dummy_task.decode_text(validator_output)
        else:
            expected_output = "audio_output_placeholder"  # For TTS
        
        bt.logging.info(f"✅ Validator pipeline: {validator_time:.2f}s | {validator_model}")
    else:
        bt.logging.warning(f"⚠️  Validator pipeline failed, using placeholder output")
        expected_output = placeholder_expected
    
    # Initialize miner tracker if not exists
    if not hasattr(self, 'miner_tracker'):
        self.miner_tracker = MinerTracker(self.config)
        bt.logging.info("🆕 Initialized miner tracker for load balancing")
    
    # Register miners in the tracker
    for uid in self.reachable_miners:
        if uid < len(self.metagraph.hotkeys):
            hotkey = self.metagraph.hotkeys[uid]
            stake = self.metagraph.S[uid]
            self.miner_tracker.register_miner(uid, hotkey, stake)
    
    # Use intelligent miner selection with load balancing (3 miners per task)
    miner_uids = self.miner_tracker.select_miners_for_task(selected_task, required_count=3)
    
    bt.logging.info(f"🎯 Task: {selected_task} | Miners: {miner_uids}")
    
    # Log details of selected miners with performance metrics (more concise)
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
            
            # Get performance metrics
            performance_score = "N/A"
            current_load = "N/A"
            if uid in self.miner_tracker.miners:
                miner = self.miner_tracker.miners[uid]
                performance_score = f"{miner.get_performance_score():.3f}"
                current_load = f"{miner.current_load}/{miner.max_concurrent_tasks}"
            
            bt.logging.info(f"   📡 UID {uid}: {ip}:{port} | Performance: {performance_score} | Load: {current_load}")
    
    bt.logging.info(f"🚀 Sending {selected_task} task to {len(miner_uids)} miners...")
    
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

    # Log responses for monitoring (more concise)
    bt.logging.info(f"📥 Received {len(responses)} responses from miners")
    
    bt.logging.info(f"✅ Task completed: {selected_task}")
    
    # Evaluate responses and calculate rewards
    bt.logging.info(f"📊 Evaluating miner responses...")
    
    # Calculate rewards for each miner
    rewards = []
    for i, response in enumerate(responses):
        if i >= len(miner_uids):
            continue
            
        uid = miner_uids[i]
        if not response:
            rewards.append(0.0)
            continue
        
        if not hasattr(response, 'output_data') or not response.output_data:
            rewards.append(0.0)
            continue
        
        # Calculate accuracy score
        accuracy_score = await self.calculate_accuracy_score(response, selected_task, test_data, "en")
        
        # Calculate speed score
        processing_time = getattr(response, 'processing_time', 10.0)
        speed_score = self.calculate_speed_score(processing_time)
        
        # Combined score (accuracy 70%, speed 30%)
        combined_score = (accuracy_score * 0.7) + (speed_score * 0.3)
        
        # Store response data for evaluation
        response_data = {
            'output_data': response.output_data,
            'processing_time': processing_time,
            'pipeline_model': getattr(response, 'pipeline_model', 'Unknown'),
            'error_message': getattr(response, 'error_message', None)
        }
        
        rewards.append(combined_score)
        
        # Update miner tracker with performance data
        if self.miner_tracker:
            success = combined_score > 0.5  # Consider response successful if score > 0.5
            self.miner_tracker.update_task_result(uid, selected_task, success, processing_time)
    
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
    
    # Log rankings (more concise)
    bt.logging.info(f"🏆 Miner rankings for {selected_task}:")
    
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
        
        # More concise logging
        bt.logging.info(f"{rank:2d}. {status_icon} UID {uid:3d} | Reward: {reward:.4f} | Time: {processing_time:.2f}s")
        
        if error_msg:
            bt.logging.info(f"    ❌ Error: {error_msg[:50]}...")
    
    # Reward top 5 miners (more concise)
    top_miners = miner_rankings[:5]
    bt.logging.info(f"🎁 Rewarding top {len(top_miners)} miners...")
    
    for rank, miner in enumerate(top_miners, 1):
        uid = miner['uid']
        reward = miner['reward']
        
        # Calculate final reward (normalized)
        final_reward = reward / sum(m['reward'] for m in top_miners) if sum(m['reward'] for m in top_miners) > 0 else 0
        
        bt.logging.info(f"{rank}. UID {uid:3d} | Final Reward: {final_reward:.4f}")
        
        # Update scores
        self.scores[uid] = final_reward
    
    # Update miner tracker with task results for performance history
    bt.logging.info(f"📊 Updating miner performance history...")
    for i, miner in enumerate(miner_rankings):
        uid = miner['uid']
        reward = miner['reward']
        response = miner['response']
        
        if response:
            processing_time = response.get('processing_time', 0.0)
            error_msg = response.get('error_message', None)
            success = reward > 0 and not error_msg
            
            # Update miner tracker
            self.miner_tracker.update_task_result(uid, selected_task, success, processing_time)
            
            bt.logging.debug(f"   📈 UID {uid}: success={success}, time={processing_time:.2f}s, reward={reward:.4f}")
    
    # Save updated metrics
    self.miner_tracker.save_metrics()
    
    # Log summary
    total_reward = sum(m['reward'] for m in miner_rankings)
    avg_reward = total_reward / len(miner_rankings) if miner_rankings else 0
    
    bt.logging.info(f"\n📈 EVALUATION SUMMARY:")
    bt.logging.info(f"   - Total miners evaluated: {len(miner_rankings)}")
    bt.logging.info(f"   - Average reward: {avg_reward:.4f}")
    bt.logging.info(f"   - Top reward: {miner_rankings[0]['reward']:.4f} (UID {miner_rankings[0]['uid']})")
    bt.logging.info(f"   - Bottom reward: {miner_rankings[-1]['reward']:.4f} (UID {miner_rankings[-1]['uid']})")
    
    # Print miner performance summary every 10 rounds
    if hasattr(self, 'round_count'):
        self.round_count += 1
    else:
        self.round_count = 1
    
    if self.round_count % 10 == 0:
        self.miner_tracker.print_miner_summary()
        self.miner_tracker.cleanup_old_miners(max_age_hours=24)
    
    bt.logging.debug("─" * 40)
    
    # Sleep between iterations
    time.sleep(5)


async def check_miner_connectivity(self):
    """
    Check miner connectivity and populate reachable_miners list.
    Only logs reachable miners, not offline ones.
    """
    try:
        total_miners = len(self.metagraph.hotkeys)
        serving_miners = 0
        reachable_miners = []
        
        bt.logging.info(f"🔍 Checking miner connectivity...")
        
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
                            
                            # More concise logging for reachable miners
                            bt.logging.info(f"✅ UID {uid:3d} | {ip}:{port} | Stake: {stake:,.0f} TAO | Status: {status}")
                        else:
                            # Only log unresponsive miners at debug level
                            bt.logging.debug(f"⚠️  UID {uid:3d} | {ip}:{port} | Unresponsive (Status: {status})")
                    else:
                        # Only log no response at debug level
                        bt.logging.debug(f"❌ UID {uid:3d} | {ip}:{port} | No response")
                    
                except Exception as e:
                    # Only log connection failures at debug level
                    bt.logging.debug(f"❌ UID {uid:3d} | {ip}:{port} | Connection failed: {str(e)[:30]}...")
                # No logging for offline miners - completely silent
        
        # More concise connectivity summary
        bt.logging.info(f"📊 Network Status: {len(reachable_miners)}/{serving_miners} miners reachable ({(len(reachable_miners)/total_miners)*100:.1f}% success rate)")
        
        if reachable_miners:
            # Only show top miners by stake, not all reachable UIDs
            top_miners = sorted(reachable_miners, key=lambda x: self.metagraph.S[x], reverse=True)[:3]
            bt.logging.info(f"🎯 Top miners by stake: {top_miners}")
            
            # Store reachable miners for use in task assignment
            self.reachable_miners = reachable_miners
        else:
            bt.logging.warning("⚠️  No miners are currently reachable!")
            self.reachable_miners = []
        
        bt.logging.info("─" * 60)
        
    except Exception as e:
        bt.logging.error(f"❌ Error checking miner connectivity: {str(e)}")
        self.reachable_miners = []


async def calculate_accuracy_score(self, response, task_type, input_data, language):
    """Calculate accuracy score for a response"""
    try:
        if task_type == "transcription":
            # For transcription, we'll use a placeholder score for now
            # In a real implementation, you'd compare with ground truth
            return 0.85  # Placeholder score
        elif task_type == "summarization":
            return 0.80  # Placeholder score
        elif task_type == "tts":
            return 0.75  # Placeholder score
        else:
            return 0.5
    except Exception as e:
        bt.logging.error(f"❌ Error calculating accuracy score: {str(e)}")
        return 0.0


def calculate_speed_score(self, processing_time):
    """Calculate speed score based on processing time"""
    try:
        if processing_time <= 0:
            return 0.0
        
        # Exponential decay: faster = higher score
        max_acceptable_time = 10.0
        speed_score = np.exp(-processing_time / max_acceptable_time)
        return min(1.0, max(0.0, speed_score))
    except Exception as e:
        bt.logging.error(f"❌ Error calculating speed score: {str(e)}")
        return 0.0


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
        dummy_task = AudioTask(input_data="dummy_audio_data")
        encoded_audio = dummy_task.encode_audio(audio_bytes.read())
        
        # Expected output (what we expect from Whisper)
        expected_output = "A sine wave tone at 440 hertz."
        
        return encoded_audio, expected_output
    
    elif task_type == "tts":
        # Generate test text for TTS
        test_text = "Hello, this is a test for text to speech conversion."
        dummy_task = AudioTask(input_data="dummy_text_data")
        encoded_text = dummy_task.encode_text(test_text)
        
        # Expected output (placeholder for audio)
        expected_output = "audio_output_placeholder"
        
        return encoded_text, expected_output
    
    elif task_type == "summarization":
        # Generate test text for summarization
        test_text = "This is a long text that needs to be summarized. It contains multiple sentences and should be reduced to a shorter version while preserving the key information. The summarization process should extract the key points and create a concise version of the original text."
        dummy_task = AudioTask(input_data="dummy_summary_data")
        encoded_text = dummy_task.encode_text(test_text)
        
        # Expected output (what we expect from BART)
        expected_output = "This text needs summarization to extract key points and create a concise version."
        
        return encoded_text, expected_output
    
    else:
        raise ValueError(f"Unknown task type: {task_type}")
