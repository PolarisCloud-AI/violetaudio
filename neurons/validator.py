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
from typing import List, Dict
import difflib

# Bittensor
import bittensor as bt
import httpx

# import base validator class which takes care of most of the boilerplate
from template.base.validator import BaseValidatorNeuron

# Bittensor Validator Template:

from template.protocol import AudioTask


class Validator(BaseValidatorNeuron):
    """
    Audio processing validator that evaluates transcription, TTS, and summarization services.
    This validator rewards miners based on speed, accuracy, and stake, prioritizing the top 5 performers.
    """

    def __init__(self, config=None):
        # Initialize critical attributes BEFORE calling parent constructor
        self.proxy_tasks_processed_this_epoch = False
        self.proxy_server_url = "http://localhost:8000"  # Proxy server URL
        self.last_miner_status_report = 0
        self.miner_status_report_interval = 100  # Report every 100 blocks (1 epoch)
        
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
    
    async def check_miner_connectivity(self):
        """Check miner connectivity and populate reachable_miners list"""
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
                        from template.protocol import AudioTask
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
                                bt.logging.info(f"✅ UID {uid:3d} | {ip}:{port} | Stake: {stake:,.0f} TAO | Status: {status}")
                            else:
                                bt.logging.debug(f"⚠️  UID {uid:3d} | {ip}:{port} | Unresponsive (Status: {status})")
                        else:
                            bt.logging.debug(f"❌ UID {uid:3d} | {ip}:{port} | No response")
                        
                    except Exception as e:
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
    
    def should_set_weights(self) -> bool:
        """
        Override to prevent weight setting when proxy tasks are processed or no miners available.
        This ensures we don't set weights based on proxy task evaluations or when there are no miners.
        """
        # Don't set weights if proxy tasks were processed this epoch
        if self.proxy_tasks_processed_this_epoch:
            bt.logging.info("🔄 Skipping weight setting - proxy tasks were processed this epoch")
            return False
        
        # Don't set weights if there are no reachable miners
        if not hasattr(self, 'reachable_miners') or not self.reachable_miners:
            bt.logging.info("🔄 Skipping weight setting - no reachable miners available")
            return False
        
        # Reset the flag when we're about to set weights (new epoch)
        self.proxy_tasks_processed_this_epoch = False
        
        # Use default weight setting logic (every 100 blocks)
        return self.step % 100 == 0

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
        proxy_tasks_processed = False
        if self.enable_proxy_integration:
            proxy_tasks_processed = await self.check_proxy_server_tasks()
        
        # Only run the standard forward pass if no proxy tasks were processed
        # This prevents weight setting when we're evaluating proxy tasks
        if not proxy_tasks_processed:
            return await self._run_standard_forward()
        else:
            bt.logging.info("🔄 Proxy tasks processed, skipping standard forward pass to prevent weight setting")
            
            # Run the new task evaluation and weight setting process
            await self.evaluate_completed_tasks_and_set_weights()
            return None
    
    async def _run_standard_forward(self):
        """Standard forward pass implementation"""
        # Check miner connectivity and register them
        await self.check_miner_connectivity()
        
        # Report miner status to proxy server
        if hasattr(self, 'reachable_miners') and self.reachable_miners:
            await self.report_miner_status_to_proxy()
        
        # Check if we have any reachable miners
        if not hasattr(self, 'reachable_miners') or not self.reachable_miners:
            bt.logging.warning("No reachable miners available. Skipping this round.")
            return
        
        # For now, just log that we're running the standard forward pass
        bt.logging.info("🔄 Running standard forward pass...")
        return None

    async def check_proxy_server_tasks(self):
        """Check proxy server for pending tasks and process them"""
        try:
            current_time = time.time()
            
            # Check if enough time has passed since last check
            if current_time - self.last_proxy_check < self.proxy_check_interval:
                return False # Indicate no new tasks processed
            
            bt.logging.info("🔍 Checking proxy server for pending tasks...")
            
            # Get pending tasks from proxy server
            pending_tasks = await self.get_proxy_pending_tasks()
            if not pending_tasks:
                bt.logging.info("📭 No pending tasks in proxy server")
                # Update timer only after successful check
                self.last_proxy_check = current_time
                return False # Indicate no new tasks processed
            
            bt.logging.info(f"📋 Found {len(pending_tasks)} pending tasks in proxy server")
            
            # Process pending tasks
            await self.process_proxy_tasks(pending_tasks)
            
            # Update timer after successful processing
            self.last_proxy_check = current_time
            
            # Set flag to prevent weight setting this epoch
            self.proxy_tasks_processed_this_epoch = True
            
            return True  # Indicate new tasks processed
            
        except Exception as e:
            bt.logging.error(f"❌ Error checking proxy server tasks: {str(e)}")
            return False # Indicate no new tasks processed
    
    async def get_proxy_pending_tasks(self):
        """Get tasks ready for evaluation from proxy server (only 'done' status)"""
        try:
            # Only get tasks that are ready for evaluation (status = 'done')
            response = requests.get(f"{self.proxy_server_url}/api/v1/validator/tasks", timeout=10)
            if response.status_code == 200:
                data = response.json()
                tasks = data.get('tasks', [])
                # Filter for only 'done' tasks
                done_tasks = [task for task in tasks if task.get('status') == 'done']
                if done_tasks:
                    bt.logging.info(f"📋 Found {len(done_tasks)} tasks ready for evaluation")
                return done_tasks
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
            language = task_data.get('language', 'en')  # Default to English if not specified
            input_data = task_data.get('input_data', '')  # Default to empty string if not specified
            
            # Validate required fields
            if not task_type:
                bt.logging.error(f"❌ Task {task_id} missing task_type")
                return None
            
            if not input_data:
                bt.logging.error(f"❌ Task {task_id} missing input_data")
                return None
            
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
                speed_score = self.calculate_speed_score(response.processing_time if hasattr(response, 'processing_time') else 10.0, task_type)
                
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
    
    def calculate_speed_score(self, processing_time: float, task_type: str) -> float:
        """Calculate speed score based on processing time and task type"""
        try:
            # Define optimal processing times for different task types
            optimal_times = {
                'transcription': 2.0,  # 2 seconds optimal
                'tts': 3.0,            # 3 seconds optimal  
                'summarization': 5.0   # 5 seconds optimal
            }
            
            optimal_time = optimal_times.get(task_type, 5.0)
            
            # Score based on how close to optimal time
            if processing_time <= optimal_time:
                # Faster than optimal = perfect score
                return 1.0
            elif processing_time <= optimal_time * 2:
                # Within 2x optimal = good score
                return 0.8
            elif processing_time <= optimal_time * 5:
                # Within 5x optimal = acceptable score
                return 0.6
            else:
                # Too slow = poor score
                return 0.3
                
        except Exception as e:
            bt.logging.error(f"❌ Error calculating speed score: {str(e)}")
            return 0.5

    def calculate_quality_score(self, miner_response: Dict, task_type: str) -> float:
        """Calculate quality score based on response structure and completeness"""
        try:
            quality_score = 0.0
            
            # Check if response has required fields
            response_data = miner_response.get('response_data', {})
            
            if task_type == 'transcription':
                # Check for transcript field
                if 'output_data' in response_data:
                    output_data = response_data['output_data']
                    if isinstance(output_data, str):
                        # Parse the string output data
                        import ast
                        try:
                            parsed = ast.literal_eval(output_data)
                            if 'transcript' in parsed and parsed['transcript']:
                                quality_score += 0.4
                            if 'confidence' in parsed:
                                quality_score += 0.3
                            if 'language' in parsed:
                                quality_score += 0.3
                        except:
                            quality_score += 0.2  # Partial credit for having output_data
                    else:
                        # Direct dict format
                        if 'transcript' in output_data and output_data['transcript']:
                            quality_score += 0.4
                        if 'confidence' in output_data:
                            quality_score += 0.3
                        if 'language' in output_data:
                            quality_score += 0.3
                            
            elif task_type == 'tts':
                # Check for audio data
                if 'output_data' in response_data:
                    output_data = response_data['output_data']
                    if isinstance(output_data, str):
                        try:
                            parsed = ast.literal_eval(output_data)
                            if 'audio_data' in parsed:
                                quality_score += 0.7
                            if 'duration' in parsed:
                                quality_score += 0.3
                        except:
                            quality_score += 0.3
                    else:
                        if 'audio_data' in output_data:
                            quality_score += 0.7
                        if 'duration' in output_data:
                            quality_score += 0.3
                            
            elif task_type == 'summarization':
                # Check for summary
                if 'output_data' in response_data:
                    output_data = response_data['output_data']
                    if isinstance(output_data, str):
                        try:
                            parsed = ast.literal_eval(output_data)
                            if 'summary' in parsed and parsed['summary']:
                                quality_score += 0.6
                            if 'key_points' in parsed:
                                quality_score += 0.4
                        except:
                            quality_score += 0.3
                    else:
                        if 'summary' in output_data and output_data['summary']:
                            quality_score += 0.6
                        if 'key_points' in output_data:
                            quality_score += 0.4
            
            # Check for processing metrics
            if 'processing_time' in miner_response:
                quality_score += 0.1
            if 'accuracy_score' in miner_response:
                quality_score += 0.1
            if 'speed_score' in miner_response:
                quality_score += 0.1
                
            return min(quality_score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            bt.logging.error(f"❌ Error calculating quality score: {str(e)}")
            return 0.5
    
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

    async def report_miner_status_to_proxy(self):
        """Report current miner status to proxy server"""
        try:
            if not hasattr(self, 'reachable_miners') or not self.reachable_miners:
                bt.logging.debug("🔄 No reachable miners to report")
                return
            
            bt.logging.info("📊 Reporting miner status to proxy server...")
            
            miner_statuses = []
            
            for uid in self.reachable_miners:
                try:
                    # Get miner information from metagraph
                    axon = self.metagraph.axons[uid]
                    hotkey = self.metagraph.hotkeys[uid]
                    stake = self.metagraph.S[uid]
                    
                    # Get IP information
                    ip = axon.ip
                    port = axon.port
                    external_ip = axon.external_ip
                    external_port = axon.external_port
                    
                    # Convert IP from int to string if needed
                    if isinstance(ip, int):
                        ip = f"{ip >> 24}.{(ip >> 16) & 255}.{(ip >> 8) & 255}.{ip & 255}"
                    
                    if isinstance(external_ip, int):
                        external_ip = f"{external_ip >> 24}.{(external_ip >> 16) & 255}.{(external_ip >> 8) & 255}.{external_ip & 255}"
                    
                    # Calculate performance score based on recent interactions
                    performance_score = self.calculate_miner_performance_score(uid)
                    
                    # Get current load (estimate based on recent activity)
                    current_load = self.estimate_miner_current_load(uid)
                    
                    # Task type specialization (based on recent performance)
                    task_type_specialization = self.get_miner_task_specialization(uid)
                    
                    miner_status = {
                        'uid': uid,
                        'hotkey': hotkey,
                        'ip': ip,
                        'port': port,
                        'external_ip': external_ip,
                        'external_port': external_port,
                        'is_serving': axon.is_serving,
                        'stake': float(stake),
                        'performance_score': performance_score,
                        'current_load': current_load,
                        'max_capacity': 5,  # Default capacity
                        'last_seen': datetime.now().isoformat(),
                        'task_type_specialization': task_type_specialization
                    }
                    
                    miner_statuses.append(miner_status)
                    
                except Exception as e:
                    bt.logging.debug(f"⚠️ Error getting status for miner {uid}: {str(e)[:50]}...")
                    continue
            
            if miner_statuses:
                # Send to proxy server
                success = await self.send_miner_status_to_proxy(miner_statuses)
                
                if success:
                    bt.logging.info(f"✅ Reported {len(miner_statuses)} miner statuses to proxy")
                    self.last_miner_status_report = self.step
                else:
                    bt.logging.warning("⚠️ Failed to report miner status to proxy")
            else:
                bt.logging.debug("🔄 No miner statuses to report")
                
        except Exception as e:
            bt.logging.error(f"❌ Error reporting miner status: {str(e)}")
    
    async def send_miner_status_to_proxy(self, miner_statuses: List[Dict]) -> bool:
        """Send miner status to proxy server via HTTP API"""
        try:
            proxy_endpoint = f"{self.proxy_server_url}/api/v1/validators/miner-status"
            
            payload = {
                'validator_uid': self.uid,
                'miner_statuses': miner_statuses,
                'epoch': self.step // 100
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(proxy_endpoint, json=payload)
                
                if response.status_code == 200:
                    return True
                else:
                    bt.logging.warning(f"⚠️ Proxy returned status {response.status_code}: {response.text}")
                    return False
                    
        except httpx.TimeoutException:
            bt.logging.warning("⏰ Timeout connecting to proxy server")
            return False
        except httpx.ConnectError:
            bt.logging.warning("🔌 Connection error to proxy server")
            return False
        except Exception as e:
            bt.logging.error(f"❌ Error sending miner status to proxy: {str(e)}")
            return False
    
    def calculate_miner_performance_score(self, uid: int) -> float:
        """Calculate miner performance score based on recent interactions"""
        try:
            # This is a simplified performance calculation
            # In a real implementation, you'd track actual task completion rates
            
            # Base score from stake (higher stake = higher base score)
            stake = self.metagraph.S[uid]
            max_stake = self.metagraph.S.max()
            base_score = float(stake / max_stake) if max_stake > 0 else 0.5
            
            # Add some randomness for now (replace with actual performance tracking)
            import random
            performance_bonus = random.uniform(-0.1, 0.1)
            
            final_score = max(0.1, min(1.0, base_score + performance_bonus))
            return final_score
            
        except Exception as e:
            bt.logging.debug(f"⚠️ Error calculating performance for miner {uid}: {str(e)[:30]}...")
            return 0.5
    
    def estimate_miner_current_load(self, uid: int) -> int:
        """Estimate miner current load (simplified implementation)"""
        try:
            # This is a simplified load estimation
            # In a real implementation, you'd track actual task assignments
            
            # Random load between 0-3 for now
            import random
            return random.randint(0, 3)
            
        except Exception as e:
            bt.logging.debug(f"⚠️ Error estimating load for miner {uid}: {str(e)[:30]}...")
            return 0
    
    def get_miner_task_specialization(self, uid: int) -> Dict:
        """Get miner task type specialization (simplified implementation)"""
        try:
            # This is a simplified specialization
            # In a real implementation, you'd track actual task performance by type
            
            # Mock specialization data
            return {
                'transcription': {
                    'total': 10,
                    'successful': 9,
                    'avg_time': 2.5,
                    'success_rate': 0.9
                },
                'tts': {
                    'total': 8,
                    'successful': 7,
                    'avg_time': 3.1,
                    'success_rate': 0.875
                }
            }
            
        except Exception as e:
            bt.logging.debug(f"⚠️ Error getting specialization for miner {uid}: {str(e)[:30]}...")
            return {}

    async def evaluate_completed_tasks_and_set_weights(self):
        """
        Main method for evaluating completed tasks and setting miner weights.
        This method:
        1. Tests proxy server connection
        2. Fetches completed tasks from proxy server
        3. Executes each task as a miner would
        4. Compares validator results with miner results
        5. Calculates scores and ranks for each miner
        6. Sets weights based on cumulative performance
        7. Generates comprehensive performance reports
        """
        try:
            bt.logging.info("🚀 Starting task evaluation and weight setting process...")
            
            # First test proxy server connection
            bt.logging.info("🔍 Testing proxy server connection...")
            if not await self.test_proxy_server_connection():
                bt.logging.error("❌ Failed to connect to proxy server, aborting evaluation")
                return
            
            bt.logging.info("✅ Proxy server connection test successful, proceeding with evaluation")
            
            # Fetch completed tasks from proxy server
            completed_tasks = await self.fetch_completed_tasks_from_proxy()
            if not completed_tasks:
                bt.logging.info("📭 No completed tasks found for evaluation")
                return
            
            bt.logging.info(f"📋 Found {len(completed_tasks)} completed tasks for evaluation")
            
            # Filter out tasks that have already been evaluated by this validator
            bt.logging.info("🔍 Filtering out already evaluated tasks...")
            new_tasks = await self.filter_already_evaluated_tasks(completed_tasks)
            
            if not new_tasks:
                bt.logging.info("📭 All tasks have already been evaluated by this validator")
                return
            
            bt.logging.info(f"📋 Proceeding with {len(new_tasks)} new tasks for evaluation")
            
            # Initialize miner performance tracking
            miner_performance = {}
            validator_performance = {}  # Track validator's own performance
            
            # Process each completed task
            for task in new_tasks:
                task_id = task.get('task_id')
                task_type = task.get('task_type')
                miner_responses = task.get('miner_responses', [])
                
                # Enhanced task logging
                bt.logging.info("=" * 80)
                bt.logging.info(f"🔍 EVALUATING TASK: {task_id}")
                bt.logging.info(f"📋 Task Details:")
                bt.logging.info(f"   Type: {task_type}")
                bt.logging.info(f"   Language: {task.get('language', 'en')}")
                bt.logging.info(f"   Status: {task.get('status', 'unknown')}")
                bt.logging.info(f"   Created: {task.get('created_at', 'N/A')}")
                bt.logging.info(f"   Completed: {task.get('completed_at', 'N/A')}")
                bt.logging.info(f"   Miner Responses: {len(miner_responses)}")
                
                # Log input data summary
                input_data = task.get('input_data')
                if input_data:
                    if task_type == 'transcription':
                        bt.logging.info(f"   Input: Audio data ({len(input_data)} chars)")
                    elif task_type == 'tts':
                        bt.logging.info(f"   Input: Text data ({len(input_data)} chars)")
                    elif task_type == 'summarization':
                        bt.logging.info(f"   Input: Text data ({len(input_data)} chars)")
                    else:
                        bt.logging.info(f"   Input: {type(input_data).__name__} data")
                
                # Log miner response summary for this task
                bt.logging.info(f"📊 Miner Response Summary:")
                miner_summary = []
                for i, response in enumerate(miner_responses):
                    miner_uid = response.get('miner_uid')
                    processing_time = response.get('processing_time', 0)
                    accuracy_score = response.get('accuracy_score', 0)
                    speed_score = response.get('speed_score', 0)
                    miner_summary.append(f"UID{miner_uid}({processing_time:.2f}s,{accuracy_score:.3f},{speed_score:.3f})")
                    bt.logging.info(f"      Miner {i+1}: UID {miner_uid}")
                    bt.logging.info(f"         Processing Time: {processing_time:.3f}s")
                    bt.logging.info(f"         Accuracy Score: {accuracy_score:.3f}")
                    bt.logging.info(f"         Speed Score: {speed_score:.3f}")
                    bt.logging.info(f"         Submitted: {response.get('submitted_at', 'N/A')}")
                
                bt.logging.info(f"   Summary: {', '.join(miner_summary)}")
                
                # Validate task has required data
                if not miner_responses:
                    bt.logging.warning(f"⚠️ Task {task_id} has no miner responses, skipping")
                    bt.logging.info("=" * 80)
                    continue
                
                # Execute task as validator (like a miner would) using actual pipelines
                bt.logging.info(f"🔧 EXECUTING TASK AS VALIDATOR:")
                bt.logging.info(f"   Task Type: {task_type}")
                bt.logging.info(f"   Using Pipeline: {self._get_pipeline_name(task_type)}")
                
                validator_result = await self.execute_task_as_validator(task)
                if not validator_result:
                    bt.logging.error(f"❌ Failed to execute task {task_id} as validator")
                    bt.logging.info("=" * 80)
                    continue
                
                # Log validator execution results
                bt.logging.info(f"✅ VALIDATOR EXECUTION COMPLETED:")
                bt.logging.info(f"   Processing Time: {validator_result.get('processing_time', 0):.3f}s")
                bt.logging.info(f"   Accuracy Score: {validator_result.get('accuracy_score', 0):.3f}")
                bt.logging.info(f"   Speed Score: {validator_result.get('speed_score', 0):.3f}")
                
                # Log output data summary
                output_data = validator_result.get('output_data', {})
                if task_type == 'transcription' and 'transcript' in output_data:
                    transcript = output_data['transcript']
                    bt.logging.info(f"   Transcript: {transcript[:100]}{'...' if len(transcript) > 100 else ''}")
                elif task_type == 'summarization' and 'summary' in output_data:
                    summary = output_data['summary']
                    bt.logging.info(f"   Summary: {summary[:100]}{'...' if len(summary) > 100 else ''}")
                elif task_type == 'tts' and 'audio_data' in output_data:
                    bt.logging.info(f"   Audio: Generated ({output_data.get('duration', 0):.1f}s)")
                
                # Store validator's own performance for this task
                validator_uid = self.uid if hasattr(self, 'uid') else 'validator'
                validator_performance[task_id] = {
                    'validator_uid': validator_uid,
                    'task_type': task_type,
                    'processing_time': validator_result.get('processing_time', 0),
                    'accuracy_score': validator_result.get('accuracy_score', 0),
                    'speed_score': validator_result.get('speed_score', 0),
                    'output_data': output_data
                }
                
                bt.logging.info(f"📊 VALIDATOR PERFORMANCE RECORDED:")
                bt.logging.info(f"   Validator UID: {validator_uid}")
                bt.logging.info(f"   Task Score: {validator_result.get('accuracy_score', 0):.3f}")
                
                # Compare validator result with miner results and calculate scores
                bt.logging.info(f"📊 CALCULATING MINER SCORES:")
                task_scores = await self.calculate_task_scores(
                    task_id, task_type, validator_result, miner_responses
                )
                
                if not task_scores:
                    bt.logging.warning(f"⚠️ No valid scores calculated for task {task_id}")
                    bt.logging.info("=" * 80)
                    continue
                
                # Select top 10 miners for this task based on performance
                top_miners = await self.select_top_miners_for_task(task_scores, max_miners=10)
                bt.logging.info(f"🏆 TOP MINERS SELECTED FOR TASK {task_id}:")
                for rank, (miner_uid, score) in enumerate(top_miners, 1):
                    bt.logging.info(f"   #{rank:2d} | UID {miner_uid:3d} | Score: {score:.2f}")
                
                # Update miner performance tracking with only top miners
                bt.logging.info(f"📈 UPDATING MINER PERFORMANCE (TOP {len(top_miners)} ONLY):")
                for miner_uid, score in top_miners:
                    if miner_uid not in miner_performance:
                        miner_performance[miner_uid] = {
                            'total_score': 0.0,
                            'task_count': 0,
                            'task_scores': {},
                            'top_rankings': {}  # Track top rankings per task
                        }
                    
                    miner_performance[miner_uid]['total_score'] += score
                    miner_performance[miner_uid]['task_count'] += 1
                    miner_performance[miner_uid]['task_scores'][task_id] = score
                    
                    # Record ranking position for this task
                    ranking_position = next(i for i, (uid, _) in enumerate(top_miners, 1) if uid == miner_uid)
                    miner_performance[miner_uid]['top_rankings'][task_id] = ranking_position
                    
                    bt.logging.info(f"   Miner {miner_uid}:")
                    bt.logging.info(f"      Task Score: {score:.2f}")
                    bt.logging.info(f"      Ranking: #{ranking_position}")
                    bt.logging.info(f"      Running Total: {miner_performance[miner_uid]['total_score']:.2f}")
                    bt.logging.info(f"      Tasks Completed: {miner_performance[miner_uid]['task_count']}")
                
                bt.logging.info(f"✅ TASK {task_id} EVALUATION COMPLETED SUCCESSFULLY")
                
                # Mark task as evaluated by this validator to prevent re-evaluation
                bt.logging.info(f"🏷️ Marking task {task_id} as evaluated...")
                await self.mark_task_as_validator_evaluated(task_id, validator_performance[task_id])
                
                bt.logging.info("=" * 80)
            
            # Generate performance rankings
            miner_rankings = await self.rank_miners_by_performance(miner_performance)
            
            # Generate comprehensive performance report
            performance_report = await self.generate_performance_report(miner_performance, miner_rankings)
            
            # Calculate final weights for all miners
            final_weights = await self.calculate_final_weights(miner_performance)
            
            # Log final weight summary
            bt.logging.info("🎯 Final Weight Summary:")
            for miner_uid, weight in sorted(final_weights.items(), key=lambda x: x[1], reverse=True):
                performance = miner_performance.get(miner_uid, {})
                task_count = performance.get('task_count', 0)
                bt.logging.info(f"   Miner {miner_uid}: Weight={weight:.2f}, Tasks={task_count}")
            
            # Set weights on chain
            await self.set_miner_weights(final_weights)
            
            # Log completion
            bt.logging.info("🎯 Task evaluation and weight setting completed successfully!")
            bt.logging.info(f"📊 Processed {len(completed_tasks)} tasks for {len(miner_performance)} miners")
            
            # Add comprehensive evaluation summary
            bt.logging.info("=" * 80)
            bt.logging.info("📋 EVALUATION SUMMARY")
            bt.logging.info("=" * 80)
            
            # Task type breakdown
            task_type_counts = {}
            for task in new_tasks:
                task_type = task.get('task_type', 'unknown')
                task_type_counts[task_type] = task_type_counts.get(task_type, 0) + 1
            
            bt.logging.info("📊 Task Type Breakdown:")
            for task_type, count in task_type_counts.items():
                bt.logging.info(f"   {task_type.capitalize()}: {count} tasks")
            
            # Validator performance summary
            bt.logging.info(f"\n👨‍⚖️ Validator Performance Summary:")
            bt.logging.info(f"   Validator UID: {self.uid if hasattr(self, 'uid') else 'unknown'}")
            bt.logging.info(f"   Tasks Evaluated: {len(validator_performance)}")
            
            if validator_performance:
                avg_validator_score = sum(perf['accuracy_score'] for perf in validator_performance.values()) / len(validator_performance)
                avg_processing_time = sum(perf['processing_time'] for perf in validator_performance.values()) / len(validator_performance)
                bt.logging.info(f"   Average Accuracy Score: {avg_validator_score:.3f}")
                bt.logging.info(f"   Average Processing Time: {avg_processing_time:.3f}s")
            
            # Miner participation summary
            bt.logging.info(f"\n👥 Miner Participation Summary:")
            bt.logging.info(f"   Total Miners: {len(miner_performance)}")
            bt.logging.info(f"   Total Tasks Evaluated: {sum(perf['task_count'] for perf in miner_performance.values())}")
            
            # Top performers by ranking
            bt.logging.info(f"\n🏆 Top Performers by Task Ranking:")
            for miner_uid, performance in miner_performance.items():
                top_rankings = performance.get('top_rankings', {})
                if top_rankings:
                    avg_ranking = sum(top_rankings.values()) / len(top_rankings)
                    best_ranking = min(top_rankings.values())
                    bt.logging.info(f"   Miner {miner_uid}: Avg Rank: {avg_ranking:.1f}, Best: #{best_ranking}")
            
            # Performance statistics
            if miner_performance:
                total_scores = [perf['total_score'] for perf in miner_performance.values()]
                avg_score = sum(total_scores) / len(total_scores)
                max_score = max(total_scores)
                min_score = min(total_scores)
                
                bt.logging.info(f"\n📈 Performance Statistics:")
                bt.logging.info(f"   Average Total Score: {avg_score:.2f}")
                bt.logging.info(f"   Highest Total Score: {max_score:.2f}")
                bt.logging.info(f"   Lowest Total Score: {min_score:.2f}")
                bt.logging.info(f"   Score Range: {max_score - min_score:.2f}")
                
                # Score distribution
                excellent = len([s for s in total_scores if s >= 400])
                good = len([s for s in total_scores if 300 <= s < 400])
                average = len([s for s in total_scores if 200 <= s < 300])
                below_avg = len([s for s in total_scores if 100 <= s < 200])
                poor = len([s for s in total_scores if s < 100])
                
                bt.logging.info(f"\n🏆 Score Distribution:")
                bt.logging.info(f"   Excellent (400-500): {excellent} miners")
                bt.logging.info(f"   Good (300-399): {good} miners")
                bt.logging.info(f"   Average (200-299): {average} miners")
                bt.logging.info(f"   Below Average (100-199): {below_avg} miners")
                bt.logging.info(f"   Poor (0-99): {poor} miners")
                
                # Check if any miners hit the 500 cap
                capped_miners = [uid for uid, weight in miner_performance.items() if weight['total_score'] >= 500.0]
                if capped_miners:
                    bt.logging.info(f"   🏆 Miners at Maximum Score (500): {len(capped_miners)}")
            
            # Pipeline execution summary
            bt.logging.info(f"\n🔧 Pipeline Execution Summary:")
            bt.logging.info(f"   Transcription Pipeline: Used {task_type_counts.get('transcription', 0)} times")
            bt.logging.info(f"   TTS Pipeline: Used {task_type_counts.get('tts', 0)} times")
            bt.logging.info(f"   Summarization Pipeline: Used {task_type_counts.get('summarization', 0)} times")
            
            bt.logging.info("=" * 80)
            
            # Save performance report for future reference
            await self.save_performance_report(performance_report)
            
        except Exception as e:
            bt.logging.error(f"❌ Error in task evaluation and weight setting: {str(e)}")
            import traceback
            traceback.print_exc()

    async def fetch_completed_tasks_from_proxy(self) -> List[Dict]:
        """Fetch completed tasks from proxy server with miner responses attached"""
        try:
            bt.logging.info(f"🔍 Fetching completed tasks from proxy server: {self.proxy_server_url}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.proxy_server_url}/api/v1/tasks/completed",
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    tasks = response.json()
                    bt.logging.info(f"📥 Successfully fetched {len(tasks)} completed tasks from proxy")
                    
                    # Log details about each task and its miner responses
                    for task in tasks:
                        task_id = task.get('task_id', 'unknown')
                        task_type = task.get('task_type', 'unknown')
                        miner_responses = task.get('miner_responses', [])
                        
                        bt.logging.info(f"   📋 Task {task_id}: {task_type} - {len(miner_responses)} miner responses")
                        
                        # Log miner response details
                        for response in miner_responses:
                            miner_uid = response.get('miner_uid', 'unknown')
                            processing_time = response.get('processing_time', 0)
                            accuracy_score = response.get('accuracy_score', 0)
                            bt.logging.debug(f"      Miner {miner_uid}: Time={processing_time:.2f}s, Accuracy={accuracy_score:.3f}")
                    
                    # Validate that tasks have the required structure
                    valid_tasks = []
                    for task in tasks:
                        if 'miner_responses' in task and task['miner_responses']:
                            valid_tasks.append(task)
                        else:
                            bt.logging.warning(f"⚠️ Task {task.get('task_id', 'unknown')} has no miner responses, skipping")
                    
                    bt.logging.info(f"✅ Found {len(valid_tasks)} valid tasks with miner responses for evaluation")
                    return valid_tasks
                    
                else:
                    bt.logging.warning(f"⚠️ Proxy server returned status {response.status_code}")
                    bt.logging.debug(f"Response content: {response.text}")
                    return []
                    
        except Exception as e:
            bt.logging.error(f"❌ Error fetching completed tasks from proxy: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    async def execute_task_as_validator(self, task: Dict) -> Dict:
        """
        Execute a task as the validator would (like a miner).
        This simulates the mining process to get ground truth for comparison.
        """
        try:
            task_type = task.get('task_type')
            input_data = task.get('input_data') or task.get('input_file_id')
            
            bt.logging.info(f"🔧 Executing task {task.get('task_id')} as validator ({task_type})")
            
            if task_type == 'transcription':
                return await self.execute_transcription_task(task)
            elif task_type == 'tts':
                return await self.execute_tts_task(task)
            elif task_type == 'summarization':
                return await self.execute_summarization_task(task)
            else:
                bt.logging.warning(f"⚠️ Unknown task type: {task_type}")
                return None
                
        except Exception as e:
            bt.logging.error(f"❌ Error executing task as validator: {str(e)}")
            return None

    async def execute_transcription_task(self, task: Dict) -> Dict:
        """Execute transcription task as validator using actual transcription pipeline"""
        try:
            bt.logging.info(f"🔧 EXECUTING TRANSCRIPTION TASK AS VALIDATOR")
            
            # Import the actual transcription pipeline
            bt.logging.info(f"   📦 Importing TranscriptionPipeline...")
            from template.pipelines.transcription_pipeline import TranscriptionPipeline
            
            # Initialize pipeline
            bt.logging.info(f"   🚀 Initializing TranscriptionPipeline...")
            pipeline = TranscriptionPipeline()
            bt.logging.info(f"   ✅ Pipeline initialized successfully")
            
            # Get input data
            input_data = task.get('input_data')
            if not input_data:
                bt.logging.warning("⚠️ No input data found for transcription task")
                return None
            
            # Decode base64 input if needed
            bt.logging.info(f"   🔍 Processing input data...")
            import base64
            try:
                if isinstance(input_data, str):
                    bt.logging.info(f"   📝 Decoding base64 input data...")
                    audio_bytes = base64.b64decode(input_data)
                    bt.logging.info(f"   ✅ Decoded {len(audio_bytes)} bytes of audio data")
                else:
                    audio_bytes = input_data
                    bt.logging.info(f"   ✅ Using raw audio data ({len(audio_bytes)} bytes)")
            except Exception as e:
                bt.logging.error(f"❌ Failed to decode input data: {str(e)}")
                return None
            
            # Execute transcription
            bt.logging.info(f"   🎵 Starting transcription process...")
            start_time = time.time()
            
            # Log pipeline execution details
            bt.logging.info(f"   🔧 Pipeline execution details:")
            bt.logging.info(f"      Model: {pipeline.model_name}")
            bt.logging.info(f"      Device: {pipeline.device}")
            bt.logging.info(f"      Language: {task.get('language', 'en')}")
            
            transcript, processing_time = pipeline.transcribe(audio_bytes, language=task.get('language', 'en'))
            
            # Calculate confidence based on processing time and quality
            # Lower processing time = higher confidence (up to a point)
            confidence = max(0.7, min(0.98, 1.0 - (processing_time / 10.0)))
            
            bt.logging.info(f"   📝 Transcription completed:")
            bt.logging.info(f"      Raw Processing Time: {processing_time:.3f}s")
            bt.logging.info(f"      Calculated Confidence: {confidence:.3f}")
            bt.logging.info(f"      Transcript Length: {len(transcript)} characters")
            
            result = {
                'output_data': {
                    'transcript': transcript,
                    'confidence': confidence,
                    'language': task.get('language', 'en'),
                    'processing_time': processing_time
                },
                'processing_time': processing_time,
                'accuracy_score': confidence,
                'speed_score': max(0.5, 1.0 - (processing_time / 5.0))
            }
            
            bt.logging.info(f"✅ Transcription task executed successfully")
            bt.logging.debug(f"   Transcript: {transcript[:100]}...")
            return result
            
        except Exception as e:
            bt.logging.error(f"❌ Error executing transcription task: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    async def execute_tts_task(self, task: Dict) -> Dict:
        """Execute TTS task as validator using actual TTS pipeline"""
        try:
            bt.logging.info(f"🔧 EXECUTING TTS TASK AS VALIDATOR")
            
            # Import the actual TTS pipeline
            bt.logging.info(f"   📦 Importing TTSPipeline...")
            from template.pipelines.tts_pipeline import TTSPipeline
            
            # Initialize pipeline
            bt.logging.info(f"   🚀 Initializing TTSPipeline...")
            pipeline = TTSPipeline()
            bt.logging.info(f"   ✅ Pipeline initialized successfully")
            
            # Get input text
            input_text = task.get('input_data')
            if not input_text:
                bt.logging.warning("⚠️ No input text found for TTS task")
                return None
            
            bt.logging.info(f"   🔍 Processing input text...")
            bt.logging.info(f"      Text Length: {len(input_text)} characters")
            bt.logging.info(f"      Language: {task.get('language', 'en')}")
            
            # Execute TTS
            bt.logging.info(f"   🔊 Starting TTS synthesis...")
            start_time = time.time()
            
            # Log pipeline execution details
            bt.logging.info(f"   🔧 Pipeline execution details:")
            bt.logging.info(f"      Model: {pipeline.model_name if hasattr(pipeline, 'model_name') else 'Default'}")
            bt.logging.info(f"      Device: {pipeline.device if hasattr(pipeline, 'device') else 'Default'}")
            
            audio_data, duration = pipeline.synthesize(input_text, language=task.get('language', 'en'))
            
            processing_time = time.time() - start_time
            
            bt.logging.info(f"   🎵 TTS synthesis completed:")
            bt.logging.info(f"      Processing Time: {processing_time:.3f}s")
            bt.logging.info(f"      Audio Duration: {duration:.1f}s")
            bt.logging.info(f"      Audio Data Size: {len(audio_data)} characters")
            
            # Calculate scores
            accuracy_score = 0.9  # TTS quality is harder to measure automatically
            speed_score = max(0.5, 1.0 - (processing_time / 10.0))
            
            result = {
                'output_data': {
                    'audio_data': audio_data,
                    'duration': duration,
                    'language': task.get('language', 'en')
                },
                'processing_time': processing_time,
                'accuracy_score': accuracy_score,
                'speed_score': speed_score
            }
            
            bt.logging.info(f"✅ TTS task executed successfully")
            return result
            
        except Exception as e:
            bt.logging.error(f"❌ Error executing TTS task: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    async def execute_summarization_task(self, task: Dict) -> Dict:
        """Execute summarization task as validator using actual summarization pipeline"""
        try:
            bt.logging.info(f"🔧 EXECUTING SUMMARIZATION TASK AS VALIDATOR")
            
            # Import the actual summarization pipeline
            bt.logging.info(f"   📦 Importing SummarizationPipeline...")
            from template.pipelines.summarization_pipeline import SummarizationPipeline
            
            # Initialize pipeline
            bt.logging.info(f"   🚀 Initializing SummarizationPipeline...")
            pipeline = SummarizationPipeline()
            bt.logging.info(f"   ✅ Pipeline initialized successfully")
            
            # Get input text
            input_text = task.get('input_data')
            if not input_text:
                bt.logging.warning("⚠️ No input text found for summarization task")
                return None
            
            bt.logging.info(f"   🔍 Processing input text...")
            bt.logging.info(f"      Text Length: {len(input_text)} characters")
            bt.logging.info(f"      Language: {task.get('language', 'en')}")
            
            # Execute summarization
            bt.logging.info(f"   📝 Starting text summarization...")
            start_time = time.time()
            
            # Log pipeline execution details
            bt.logging.info(f"   🔧 Pipeline execution details:")
            bt.logging.info(f"      Model: {pipeline.model_name if hasattr(pipeline, 'model_name') else 'Default'}")
            bt.logging.info(f"      Device: {pipeline.device if hasattr(pipeline, 'device') else 'Default'}")
            
            summary, key_points = pipeline.summarize(input_text)
            
            processing_time = time.time() - start_time
            
            bt.logging.info(f"   📋 Summarization completed:")
            bt.logging.info(f"      Processing Time: {processing_time:.3f}s")
            bt.logging.info(f"      Summary Length: {len(summary)} characters")
            bt.logging.info(f"      Key Points: {len(key_points)} points")
            bt.logging.info(f"      Word Count: {len(summary.split())} words")
            
            # Calculate scores
            accuracy_score = 0.88  # Summarization quality is harder to measure automatically
            speed_score = max(0.5, 1.0 - (processing_time / 15.0))
            
            result = {
                'output_data': {
                    'summary': summary,
                    'key_points': key_points,
                    'word_count': len(summary.split()),
                    'language': task.get('language', 'en')
                },
                'processing_time': processing_time,
                'accuracy_score': accuracy_score,
                'speed_score': speed_score
            }
            
            bt.logging.info(f"✅ Summarization task executed successfully")
            bt.logging.debug(f"   Summary: {summary[:100]}...")
            return result
            
        except Exception as e:
            bt.logging.error(f"❌ Error executing summarization task: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    async def calculate_task_scores(self, task_id: str, task_type: str, validator_result: Dict, miner_responses: List[Dict]) -> Dict[int, float]:
        """
        Calculate scores for each miner based on comparison with validator result.
        Returns a dictionary mapping miner UIDs to their scores.
        Scores are capped at 500 as per requirement.
        """
        try:
            bt.logging.info(f"📊 Calculating scores for task {task_id} ({task_type})")
            
            miner_scores = {}
            
            for miner_response in miner_responses:
                miner_uid = miner_response.get('miner_uid')
                if not miner_uid:
                    continue
                
                # Calculate accuracy score by comparing with validator result
                accuracy_score = await self.calculate_accuracy_score_for_comparison(
                    validator_result, miner_response, task_type
                )
                
                # Calculate speed score based on processing time
                speed_score = self.calculate_speed_score(
                    miner_response.get('processing_time', 10.0),
                    task_type
                )
                
                # Calculate quality score based on response structure and completeness
                quality_score = self.calculate_quality_score(miner_response, task_type)
                
                # Combined score (accuracy 60%, speed 25%, quality 15%)
                combined_score = (
                    (accuracy_score * 0.6) + 
                    (speed_score * 0.25) + 
                    (quality_score * 0.15)
                )
                
                # Convert to 0-500 scale
                final_score = combined_score * 500.0
                
                # Ensure score doesn't exceed 500 (as per requirement)
                final_score = min(final_score, 500.0)
                
                miner_scores[miner_uid] = final_score
                
                bt.logging.info(f"   Miner {miner_uid}: Accuracy={accuracy_score:.4f}, Speed={speed_score:.4f}, Quality={quality_score:.4f}, Final={final_score:.2f}")
            
            return miner_scores
            
        except Exception as e:
            bt.logging.error(f"❌ Error calculating task scores: {str(e)}")
            return {}

    async def calculate_accuracy_score_for_comparison(self, validator_result: Dict, miner_response: Dict, task_type: str) -> float:
        """Calculate accuracy score by comparing miner response with validator result"""
        try:
            if task_type == 'transcription':
                return await self.compare_transcription_results(validator_result, miner_response)
            elif task_type == 'tts':
                return await self.compare_tts_results(validator_result, miner_response)
            elif task_type == 'summarization':
                return await self.compare_summarization_results(validator_result, miner_response)
            else:
                return 0.5  # Default score for unknown task types
                
        except Exception as e:
            bt.logging.error(f"❌ Error calculating accuracy score: {str(e)}")
            return 0.0

    async def compare_transcription_results(self, validator_result: Dict, miner_response: Dict) -> float:
        """Compare transcription results between validator and miner"""
        try:
            # Extract transcriptions
            validator_transcript = validator_result.get('output_data', {}).get('transcript', '')
            miner_transcript = miner_response.get('response_data', {}).get('output_data', '')
            
            if not validator_transcript or not miner_transcript:
                return 0.5
            
            # Simple text similarity (you can implement more sophisticated comparison)
            import difflib
            
            similarity = difflib.SequenceMatcher(None, validator_transcript.lower(), miner_transcript.lower()).ratio()
            
            # Convert similarity to score (0-1)
            score = similarity
            
            bt.logging.debug(f"Transcription similarity: {similarity:.4f} -> Score: {score:.4f}")
            return score
            
        except Exception as e:
            bt.logging.error(f"❌ Error comparing transcription results: {str(e)}")
            return 0.5

    async def compare_tts_results(self, validator_result: Dict, miner_response: Dict) -> float:
        """Compare TTS results between validator and miner"""
        try:
            # For TTS, we'll use processing time and response structure as comparison
            validator_time = validator_result.get('processing_time', 10.0)
            miner_time = miner_response.get('processing_time', 10.0)
            
            # Time-based scoring (faster = better, but not too fast)
            if miner_time < 0.1:  # Too fast, suspicious
                return 0.3
            elif miner_time > 30.0:  # Too slow
                return 0.2
            else:
                # Normal range scoring
                time_score = max(0.5, 1.0 - (miner_time / 10.0))
                return time_score
                
        except Exception as e:
            bt.logging.error(f"❌ Error comparing TTS results: {str(e)}")
            return 0.0

    async def compare_summarization_results(self, validator_result: Dict, miner_response: Dict) -> float:
        """Compare summarization results between validator and miner"""
        try:
            # Extract summaries
            validator_summary = validator_result.get('output_data', {}).get('summary', '')
            miner_summary = miner_response.get('response_data', {}).get('output_data', {}).get('summary', '')
            
            if not validator_summary or not miner_summary:
                return 0.5
            
            # Simple text similarity for summaries
            import difflib
            
            similarity = difflib.SequenceMatcher(None, validator_summary.lower(), miner_summary.lower()).ratio()
            
            # Modify the validator's forward method to call the new evaluation method
            score = similarity
            
            bt.logging.debug(f"Summarization similarity: {similarity:.4f} -> Score: {score:.4f}")
            return score
            
        except Exception as e:
            bt.logging.error(f"❌ Error comparing summarization results: {str(e)}")
            return 0.5

    async def calculate_final_weights(self, miner_performance: Dict) -> Dict[int, float]:
        """Calculate final weights for all miners based on cumulative performance across all tasks"""
        try:
            bt.logging.info("⚖️ Calculating final weights for all miners...")
            
            final_weights = {}
            
            for miner_uid, performance in miner_performance.items():
                total_score = performance['total_score']
                task_count = performance['task_count']
                
                # Calculate average score per task
                avg_score = total_score / task_count if task_count > 0 else 0.0
                
                # Ensure total score doesn't exceed 500 (as per requirement)
                # This is the cumulative score across all tasks
                capped_total_score = min(total_score, 500.0)
                
                # Calculate final weight based on capped total score
                # Higher total score = higher weight
                final_weight = capped_total_score
                
                final_weights[miner_uid] = final_weight
                
                bt.logging.info(f"   Miner {miner_uid}: Total={total_score:.2f}, Tasks={task_count}, Avg={avg_score:.2f}, Capped={capped_total_score:.2f}, Weight={final_weight:.2f}")
            
            # Log summary statistics
            if final_weights:
                max_weight = max(final_weights.values())
                min_weight = min(final_weights.values())
                avg_weight = sum(final_weights.values()) / len(final_weights)
                
                bt.logging.info(f"📊 Weight Summary: Max={max_weight:.2f}, Min={min_weight:.2f}, Avg={avg_weight:.2f}")
                
                # Check if any miners hit the 500 cap
                capped_miners = [uid for uid, weight in final_weights.items() if weight >= 500.0]
                if capped_miners:
                    bt.logging.info(f"🏆 Miners at maximum score (500): {capped_miners}")
            
            return final_weights
            
        except Exception as e:
            bt.logging.error(f"❌ Error calculating final weights: {str(e)}")
            return {}

    async def set_miner_weights(self, final_weights: Dict[int, float]):
        """Set miner weights on the blockchain"""
        try:
            bt.logging.info("🔗 Setting miner weights on blockchain...")
            
            # Convert to lists for bittensor
            uids = list(final_weights.keys())
            weights = list(final_weights.values())
            
            # Normalize weights to sum to 1.0
            total_weight = sum(weights)
            if total_weight > 0:
                normalized_weights = [w / total_weight for w in weights]
            else:
                normalized_weights = [1.0 / len(weights)] * len(weights)
            
            # Set weights using the base class method
            self.scores = np.zeros(self.metagraph.n, dtype=np.float32)
            
            for i, uid in enumerate(uids):
                if uid < len(self.scores):
                    self.scores[uid] = normalized_weights[i]
            
            # Call the base class set_weights method
            self.set_weights()
            
            bt.logging.info(f"✅ Successfully set weights for {len(uids)} miners")
            
        except Exception as e:
            bt.logging.error(f"❌ Error setting miner weights: {str(e)}")
            import traceback
            traceback.print_exc()

    async def rank_miners_by_performance(self, miner_performance: Dict) -> List[Dict]:
        """Rank miners by their performance across all tasks"""
        try:
            bt.logging.info("🏆 Ranking miners by performance...")
            
            # Convert to list for sorting
            miner_rankings = []
            
            for miner_uid, performance in miner_performance.items():
                total_score = performance['total_score']
                task_count = performance['task_count']
                avg_score = total_score / task_count if task_count > 0 else 0.0
                
                # Calculate capped score (max 500)
                capped_score = min(total_score, 500.0)
                
                miner_rankings.append({
                    'miner_uid': miner_uid,
                    'total_score': total_score,
                    'capped_score': capped_score,
                    'task_count': task_count,
                    'avg_score_per_task': avg_score,
                    'task_scores': performance['task_scores']
                })
            
            # Sort by capped score (descending)
            miner_rankings.sort(key=lambda x: x['capped_score'], reverse=True)
            
            # Add rank information
            for i, ranking in enumerate(miner_rankings):
                ranking['rank'] = i + 1
                ranking['percentile'] = ((len(miner_rankings) - i) / len(miner_rankings)) * 100
            
            # Log rankings
            bt.logging.info("📊 Miner Rankings:")
            for ranking in miner_rankings[:10]:  # Top 10
                bt.logging.info(f"   #{ranking['rank']:2d} | UID {ranking['miner_uid']:3d} | Score: {ranking['capped_score']:6.2f} | Tasks: {ranking['task_count']:2d} | Avg: {ranking['avg_score_per_task']:6.2f} | Percentile: {ranking['percentile']:5.1f}%")
            
            if len(miner_rankings) > 10:
                bt.logging.info(f"   ... and {len(miner_rankings) - 10} more miners")
            
            return miner_rankings
            
        except Exception as e:
            bt.logging.error(f"❌ Error ranking miners: {str(e)}")
            return []

    async def generate_performance_report(self, miner_performance: Dict, miner_rankings: List[Dict]) -> Dict:
        """Generate a comprehensive performance report"""
        try:
            bt.logging.info("📋 Generating performance report...")
            
            if not miner_performance:
                return {"error": "No miner performance data available"}
            
            # Calculate statistics
            total_miners = len(miner_performance)
            total_tasks = sum(perf['task_count'] for perf in miner_performance.values())
            total_score = sum(perf['total_score'] for perf in miner_performance.values())
            
            # Score distribution
            score_ranges = {
                'excellent': 0,  # 400-500
                'good': 0,        # 300-399
                'average': 0,     # 200-299
                'below_average': 0, # 100-199
                'poor': 0         # 0-99
            }
            
            for ranking in miner_rankings:
                capped_score = ranking['capped_score']
                if capped_score >= 400:
                    score_ranges['excellent'] += 1
                elif capped_score >= 300:
                    score_ranges['good'] += 1
                elif capped_score >= 200:
                    score_ranges['average'] += 1
                elif capped_score >= 100:
                    score_ranges['below_average'] += 1
                else:
                    score_ranges['poor'] += 1
            
            # Top performers
            top_performers = miner_rankings[:5] if len(miner_rankings) >= 5 else miner_rankings
            
            # Miners at max score
            max_score_miners = [r for r in miner_rankings if r['capped_score'] >= 500.0]
            
            report = {
                'summary': {
                    'total_miners': total_miners,
                    'total_tasks_evaluated': total_tasks,
                    'total_score_distributed': total_score,
                    'average_score_per_miner': total_score / total_miners if total_miners > 0 else 0,
                    'average_tasks_per_miner': total_tasks / total_miners if total_miners > 0 else 0
                },
                'score_distribution': score_ranges,
                'top_performers': [
                    {
                        'rank': r['rank'],
                        'miner_uid': r['miner_uid'],
                        'capped_score': r['capped_score'],
                        'task_count': r['task_count'],
                        'avg_score_per_task': r['avg_score_per_task']
                    } for r in top_performers
                ],
                'max_score_miners': [
                    {
                        'miner_uid': r['miner_uid'],
                        'total_score': r['total_score'],
                        'task_count': r['task_count']
                    } for r in max_score_miners
                ],
                'performance_metrics': {
                    'highest_score': max(r['capped_score'] for r in miner_rankings) if miner_rankings else 0,
                    'lowest_score': min(r['capped_score'] for r in miner_rankings) if miner_rankings else 0,
                    'score_standard_deviation': self._calculate_std_dev([r['capped_score'] for r in miner_rankings]),
                    'median_score': self._calculate_median([r['capped_score'] for r in miner_rankings])
                }
            }
            
            # Log report summary
            bt.logging.info("📊 Performance Report Summary:")
            bt.logging.info(f"   Total Miners: {total_miners}")
            bt.logging.info(f"   Total Tasks: {total_tasks}")
            bt.logging.info(f"   Score Distribution: Excellent={score_ranges['excellent']}, Good={score_ranges['good']}, Average={score_ranges['average']}, Below={score_ranges['below_average']}, Poor={score_ranges['poor']}")
            bt.logging.info(f"   Top Score: {report['performance_metrics']['highest_score']:.2f}")
            bt.logging.info(f"   Miners at Max Score (500): {len(max_score_miners)}")
            
            return report
            
        except Exception as e:
            bt.logging.error(f"❌ Error generating performance report: {str(e)}")
            return {"error": str(e)}

    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation of a list of values"""
        try:
            if not values:
                return 0.0
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            return variance ** 0.5
        except:
            return 0.0

    def _calculate_median(self, values: List[float]) -> float:
        """Calculate median of a list of values"""
        try:
            if not values:
                return 0.0
            sorted_values = sorted(values)
            n = len(sorted_values)
            if n % 2 == 0:
                return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
            else:
                return sorted_values[n//2]
        except:
            return 0.0

    async def save_performance_report(self, performance_report: Dict):
        """Save performance report for future reference"""
        try:
            import json
            from datetime import datetime
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"
            
            # Save to logs directory
            import os
            logs_dir = "logs/validator"
            os.makedirs(logs_dir, exist_ok=True)
            
            filepath = os.path.join(logs_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(performance_report, f, indent=2, default=str)
            
            bt.logging.info(f"💾 Performance report saved to: {filepath}")
            
        except Exception as e:
            bt.logging.warning(f"⚠️ Failed to save performance report: {str(e)}")

    async def test_proxy_server_connection(self):
        """Test connection to proxy server and show data structure"""
        try:
            bt.logging.info(f"🔍 Testing proxy server connection: {self.proxy_server_url}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test basic connectivity
                try:
                    response = await client.get(f"{self.proxy_server_url}/health", timeout=5.0)
                    if response.status_code == 200:
                        bt.logging.info("✅ Proxy server health check successful")
                    else:
                        bt.logging.warning(f"⚠️ Proxy server health check returned status {response.status_code}")
                except:
                    bt.logging.warning("⚠️ Proxy server health endpoint not available, continuing with main test")
                
                # Test completed tasks endpoint
                bt.logging.info("🔍 Testing completed tasks endpoint...")
                response = await client.get(
                    f"{self.proxy_server_url}/api/v1/tasks/completed",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    tasks = response.json()
                    bt.logging.info(f"✅ Successfully connected to proxy server")
                    bt.logging.info(f"📊 Found {len(tasks)} completed tasks")
                    
                    if tasks:
                        # Show sample task structure
                        sample_task = tasks[0]
                        bt.logging.info("📋 Sample task structure:")
                        bt.logging.info(f"   Task ID: {sample_task.get('task_id', 'N/A')}")
                        bt.logging.info(f"   Task Type: {sample_task.get('task_type', 'N/A')}")
                        bt.logging.info(f"   Status: {sample_task.get('status', 'N/A')}")
                        bt.logging.info(f"   Miner Responses: {len(sample_task.get('miner_responses', []))}")
                        
                        # Show sample miner response structure
                        miner_responses = sample_task.get('miner_responses', [])
                        if miner_responses:
                            sample_response = miner_responses[0]
                            bt.logging.info("📊 Sample miner response structure:")
                            bt.logging.info(f"   Miner UID: {sample_response.get('miner_uid', 'N/A')}")
                            bt.logging.info(f"   Processing Time: {sample_response.get('processing_time', 'N/A')}")
                            bt.logging.info(f"   Accuracy Score: {sample_response.get('accuracy_score', 'N/A')}")
                            bt.logging.info(f"   Response Data Keys: {list(sample_response.get('response_data', {}).keys())}")
                    else:
                        bt.logging.info("📭 No completed tasks found in proxy server")
                        
                    return True
                    
                else:
                    bt.logging.error(f"❌ Proxy server returned status {response.status_code}")
                    bt.logging.debug(f"Response content: {response.text}")
                    return False
                    
        except Exception as e:
            bt.logging.error(f"❌ Error testing proxy server connection: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _get_pipeline_name(self, task_type: str) -> str:
        """Helper to get the name of the pipeline for logging."""
        if task_type == 'transcription':
            return 'TranscriptionPipeline'
        elif task_type == 'tts':
            return 'TTSPipeline'
        elif task_type == 'summarization':
            return 'SummarizationPipeline'
        else:
            return 'UnknownPipeline'

    async def select_top_miners_for_task(self, task_scores: Dict[int, float], max_miners: int = 10) -> List[tuple]:
        """
        Select top miners for a task based on performance scores.
        Returns list of tuples (miner_uid, score) sorted by score (descending).
        """
        try:
            bt.logging.info(f"🏆 Selecting top {max_miners} miners from {len(task_scores)} total miners")
            
            # Sort miners by score (descending)
            sorted_miners = sorted(task_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Take top max_miners
            top_miners = sorted_miners[:max_miners]
            
            bt.logging.info(f"✅ Selected top {len(top_miners)} miners:")
            for rank, (miner_uid, score) in enumerate(top_miners, 1):
                bt.logging.info(f"   #{rank:2d} | UID {miner_uid:3d} | Score: {score:.2f}")
            
            return top_miners
            
        except Exception as e:
            bt.logging.error(f"❌ Error selecting top miners: {str(e)}")
            return []

    async def mark_task_as_validator_evaluated(self, task_id: str, validator_performance: Dict):
        """
        Mark a task as evaluated by this validator to prevent re-evaluation.
        This updates the proxy server to indicate the task has been processed.
        """
        try:
            bt.logging.info(f"🏷️ Marking task {task_id} as validator evaluated...")
            
            # Prepare evaluation data
            evaluation_data = {
                'task_id': task_id,
                'validator_uid': validator_performance.get('validator_uid', 'unknown'),
                'evaluated_at': datetime.now().isoformat(),
                'validator_score': validator_performance.get('accuracy_score', 0),
                'processing_time': validator_performance.get('processing_time', 0),
                'status': 'validator_evaluated'
            }
            
            # Send to proxy server to mark as evaluated
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.proxy_server_url}/api/v1/tasks/{task_id}/validator-evaluation",
                    json=evaluation_data,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    bt.logging.info(f"✅ Task {task_id} marked as validator evaluated successfully")
                    return True
                else:
                    bt.logging.warning(f"⚠️ Failed to mark task {task_id} as evaluated: {response.status_code}")
                    return False
                    
        except Exception as e:
            bt.logging.error(f"❌ Error marking task as evaluated: {str(e)}")
            return False

    async def get_validator_evaluated_tasks(self) -> List[str]:
        """
        Get list of task IDs that have already been evaluated by this validator.
        This prevents re-evaluation of the same tasks.
        """
        try:
            bt.logging.info("🔍 Fetching already evaluated tasks...")
            
            validator_uid = self.uid if hasattr(self, 'uid') else 'validator'
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.proxy_server_url}/api/v1/validator/{validator_uid}/evaluated-tasks",
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    evaluated_tasks = response.json()
                    task_ids = [task['task_id'] for task in evaluated_tasks]
                    bt.logging.info(f"✅ Found {len(task_ids)} already evaluated tasks")
                    return task_ids
                else:
                    bt.logging.warning(f"⚠️ Failed to fetch evaluated tasks: {response.status_code}")
                    return []
                    
        except Exception as e:
            bt.logging.error(f"❌ Error fetching evaluated tasks: {str(e)}")
            return []

    async def filter_already_evaluated_tasks(self, completed_tasks: List[Dict]) -> List[Dict]:
        """
        Filter out tasks that have already been evaluated by this validator.
        """
        try:
            # Get already evaluated task IDs
            evaluated_task_ids = await self.get_validator_evaluated_tasks()
            
            if not evaluated_task_ids:
                bt.logging.info("📋 No previously evaluated tasks found, processing all tasks")
                return completed_tasks
            
            # Filter out already evaluated tasks
            new_tasks = []
            skipped_tasks = []
            
            for task in completed_tasks:
                task_id = task.get('task_id')
                if task_id in evaluated_task_ids:
                    skipped_tasks.append(task_id)
                else:
                    new_tasks.append(task)
            
            bt.logging.info(f"📋 Task Filtering Results:")
            bt.logging.info(f"   Total Completed Tasks: {len(completed_tasks)}")
            bt.logging.info(f"   Already Evaluated: {len(skipped_tasks)}")
            bt.logging.info(f"   New Tasks to Evaluate: {len(new_tasks)}")
            
            if skipped_tasks:
                bt.logging.info(f"   Skipped Tasks: {', '.join(skipped_tasks[:5])}{'...' if len(skipped_tasks) > 5 else ''}")
            
            return new_tasks
            
        except Exception as e:
            bt.logging.error(f"❌ Error filtering evaluated tasks: {str(e)}")
            return completed_tasks


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
            # Log less frequently to reduce console spam
            if int(time.time()) % 60 == 0:  # Only log every minute
                bt.logging.info(f"Validator running... {time.time()}")
            time.sleep(5)
