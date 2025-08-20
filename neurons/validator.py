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
import asyncio
import requests
import json
import numpy as np
from datetime import datetime

# Bittensor
import bittensor as bt

# import base validator class which takes care of most of the boilerplate
from template.base.validator import BaseValidatorNeuron

# Bittensor Validator Template:
from template.validator import forward


class Validator(BaseValidatorNeuron):
    """
    Audio processing validator that evaluates transcription, TTS, and summarization services.
    This validator rewards miners based on speed, accuracy, and stake, prioritizing the top 5 performers.
    """

    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)

        bt.logging.info("load_state()")
        self.load_state()

        # Proxy server integration settings
        import os
        self.proxy_server_url = os.getenv('PROXY_SERVER_URL', 'http://localhost:8000')
        self.enable_proxy_integration = os.getenv('ENABLE_PROXY_INTEGRATION', 'True').lower() == 'true'
        self.proxy_check_interval = int(os.getenv('PROXY_CHECK_INTERVAL', '30'))  # seconds
        
        # Initialize proxy integration if enabled
        if self.enable_proxy_integration:
            bt.logging.info(f"🔗 Proxy server integration enabled: {self.proxy_server_url}")
            self.last_proxy_check = 0
        else:
            bt.logging.info("⚠️  Proxy server integration disabled")
        
        # Initialize miner tracker for performance monitoring and load balancing
        try:
            from template.validator.miner_tracker import MinerTracker
            self.miner_tracker = MinerTracker(self.config)
            bt.logging.info("✅ Miner tracker initialized for load balancing and performance tracking")
        except Exception as e:
            bt.logging.warning(f"⚠️  Failed to initialize miner tracker: {e}")
            self.miner_tracker = None

    async def forward(self):
        """
        Validator forward pass. Consists of:
        - Generating the query
        - Querying the miners
        - Getting the responses
        - Rewarding the miners
        - Updating the scores
        """
        # Check proxy server for tasks if integration is enabled
        if self.enable_proxy_integration:
            await self.check_proxy_server_tasks()
        
        return await forward(self)
    
    async def check_proxy_server_tasks(self):
        """Check proxy server for pending tasks and process them"""
        try:
            current_time = time.time()
            
            # Check if enough time has passed since last check
            if current_time - self.last_proxy_check < self.proxy_check_interval:
                return
            
            bt.logging.info("🔍 Checking proxy server for pending tasks...")
            
            # Get pending tasks from proxy server
            pending_tasks = await self.get_proxy_pending_tasks()
            if not pending_tasks:
                bt.logging.info("📭 No pending tasks in proxy server")
                # Update timer only after successful check
                self.last_proxy_check = current_time
                return
            
            bt.logging.info(f"📋 Found {len(pending_tasks)} pending tasks in proxy server")
            
            # Process pending tasks
            await self.process_proxy_tasks(pending_tasks)
            
            # Update timer after successful processing
            self.last_proxy_check = current_time
            
        except Exception as e:
            bt.logging.error(f"❌ Error checking proxy server tasks: {str(e)}")
    
    async def get_proxy_pending_tasks(self):
        """Get pending tasks from proxy server"""
        try:
            response = requests.get(f"{self.proxy_server_url}/api/v1/validator/distribute", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('tasks', [])
            else:
                bt.logging.warning(f"⚠️  Proxy server returned status {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            bt.logging.warning(f"⚠️  Could not connect to proxy server: {str(e)}")
            return []
    
    async def process_proxy_tasks(self, pending_tasks):
        """Process pending tasks from proxy server"""
        try:
            bt.logging.info(f"🔄 Processing {len(pending_tasks)} tasks from proxy server...")
            
            for task_data in pending_tasks:
                task_id = task_data.get('task_id')
                task_type = task_data.get('task_type')
                language = task_data.get('language')
                input_data = task_data.get('input_data')
                
                bt.logging.info(f"📝 Processing task {task_id}: {task_type} ({language})")
                
                # Process the task using the existing forward logic
                result = await self.process_single_proxy_task(task_data)
                
                if result:
                    # Send result back to proxy server
                    await self.submit_result_to_proxy(task_id, result)
                
        except Exception as e:
            bt.logging.error(f"❌ Error processing proxy tasks: {str(e)}")
    
    async def process_single_proxy_task(self, task_data):
        """Process a single task from proxy server"""
        try:
            task_id = task_data.get('task_id')
            task_type = task_data.get('task_type')
            language = task_data.get('language')
            input_data = task_data.get('input_data')
            
            bt.logging.info(f"🎯 Processing proxy task: {task_type} in {language}")
            
            # Create AudioTask synapse for this task
            from template.protocol import AudioTask
            
            synapse = AudioTask(
                task_type=task_type,
                input_data=input_data,
                language=language
            )
            
            # Use miner tracker for intelligent miner selection with load balancing
            if self.miner_tracker:
                # Register miners if not already done
                for uid in self.get_available_miners():
                    if uid < len(self.metagraph.hotkeys):
                        hotkey = self.metagraph.hotkeys[uid]
                        stake = self.metagraph.S[uid]
                        self.miner_tracker.register_miner(uid, hotkey, stake)
                
                # Select 3 miners using intelligent load balancing
                miner_uids = self.miner_tracker.select_miners_for_task(task_type, required_count=3)
                bt.logging.info(f"🎯 Intelligent miner selection: {miner_uids}")
            else:
                # Fallback to stake-based selection
                available_uids = self.get_available_miners()
                if not available_uids:
                    bt.logging.warning("⚠️  No available miners found")
                    return None
                
                miner_uids = sorted(available_uids, key=lambda x: self.metagraph.S[x], reverse=True)[:3]
                bt.logging.info(f"🎯 Fallback miner selection: {miner_uids}")
            
            # Query miners
            responses = await self.dendrite(
                axons=[self.metagraph.axons[uid] for uid in miner_uids],
                synapse=synapse,
                deserialize=True,
            )
            
            # Evaluate responses and find best one
            best_response = await self.evaluate_miner_responses(
                responses, miner_uids, task_type, input_data, language
            )
            
            if best_response:
                bt.logging.info(f"✅ Best response found from miner {best_response['miner_uid']}")
                return best_response
            else:
                bt.logging.warning("⚠️  No valid responses from miners")
                return None
                
        except Exception as e:
            bt.logging.error(f"❌ Error processing single proxy task: {str(e)}")
            return None
    
    async def evaluate_miner_responses(self, responses, miner_uids, task_type, input_data, language):
        """Evaluate miner responses and find the best one"""
        try:
            best_response = None
            best_score = 0
            
            bt.logging.info(f"🔍 Evaluating {len(responses)} miner responses...")
            
            for i, response in enumerate(responses):
                if i >= len(miner_uids):
                    continue
                    
                uid = miner_uids[i]
                if not response:
                    bt.logging.warning(f"⚠️  No response from miner {uid}")
                    continue
                
                if not hasattr(response, 'output_data') or not response.output_data:
                    bt.logging.warning(f"⚠️  No output data from miner {uid}")
                    continue
                
                # Calculate scores
                accuracy_score = await self.calculate_accuracy_score(response, task_type, input_data, language)
                speed_score = self.calculate_speed_score(response.processing_time if hasattr(response, 'processing_time') else 10.0)
                
                # Combined score (accuracy 70%, speed 30%)
                combined_score = (accuracy_score * 0.7) + (speed_score * 0.3)
                
                bt.logging.info(f"📊 Miner {uid} scores - Accuracy: {accuracy_score:.4f}, Speed: {speed_score:.4f}, Combined: {combined_score:.4f}")
                
                # Update miner tracker with performance data
                if self.miner_tracker:
                    processing_time = getattr(response, 'processing_time', 10.0)
                    success = combined_score > 0.5  # Consider response successful if score > 0.5
                    self.miner_tracker.update_task_result(uid, task_type, success, processing_time)
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_response = {
                        'output_data': response.output_data,
                        'processing_time': getattr(response, 'processing_time', 10.0),
                        'miner_uid': uid,
                        'accuracy_score': accuracy_score,
                        'speed_score': speed_score,
                        'combined_score': combined_score
                    }
                    
                    bt.logging.info(f"🏆 New best response from miner {uid} with score {combined_score:.4f}")
            
            return best_response
            
        except Exception as e:
            bt.logging.error(f"❌ Error evaluating responses: {str(e)}")
            return None
    
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
    
    def get_available_miners(self):
        """Get list of available miners"""
        try:
            available_miners = []
            for uid in range(len(self.metagraph.hotkeys)):
                if self.metagraph.axons[uid].is_serving:
                    available_miners.append(uid)
            return available_miners
        except Exception as e:
            bt.logging.error(f"❌ Error getting available miners: {str(e)}")
            return []
    
    async def submit_result_to_proxy(self, task_id, result):
        """Submit task result back to proxy server"""
        try:
            data = {
                'task_id': task_id,
                'result': result['output_data'],
                'processing_time': result['processing_time'],
                'miner_uid': result['miner_uid'],
                'accuracy_score': result['accuracy_score'],
                'speed_score': result['speed_score']
            }
            
            # Save miner metrics periodically
            if self.miner_tracker:
                self.miner_tracker.save_metrics()
            
            response = requests.post(
                f"{self.proxy_server_url}/api/v1/validator/submit_result",
                data=data,
                timeout=10
            )
            
            if response.status_code == 200:
                bt.logging.info(f"✅ Result submitted to proxy server for task {task_id}")
            else:
                bt.logging.warning(f"⚠️  Failed to submit result to proxy server: {response.status_code}")
                
        except Exception as e:
            bt.logging.error(f"❌ Error submitting result to proxy server: {str(e)}")


# The main function parses the configuration and runs the validator.
if __name__ == "__main__":
    import argparse
    
    # Create argument parser
    parser = argparse.ArgumentParser(description="Bittensor Audio Processing Validator")
    parser.add_argument("--proxy_server_url", type=str, default="http://localhost:8000",
                       help="URL of the proxy server for task integration")
    parser.add_argument("--enable_proxy_integration", action="store_true", default=True,
                       help="Enable integration with proxy server")
    parser.add_argument("--proxy_check_interval", type=int, default=30,
                       help="Interval in seconds to check proxy server for tasks")
    
    # Parse arguments
    args, unknown = parser.parse_known_args()
    
    # Store proxy config in environment variables for the validator to access
    import os
    os.environ['PROXY_SERVER_URL'] = args.proxy_server_url
    os.environ['ENABLE_PROXY_INTEGRATION'] = str(args.enable_proxy_integration)
    os.environ['PROXY_CHECK_INTERVAL'] = str(args.proxy_check_interval)
    
    with Validator() as validator:
        bt.logging.info("🚀 Validator started with proxy server integration")
        bt.logging.info(f"🔗 Proxy server URL: {args.proxy_server_url}")
        bt.logging.info(f"⏱️  Check interval: {args.proxy_check_interval}s")
        
        while True:
            bt.logging.info(f"Validator running... {time.time()}")
            time.sleep(5)
