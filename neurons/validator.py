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
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.


import time
import asyncio
import requests
import json
import numpy as np
import torch
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import difflib
import os
import pickle

# Bittensor
import bittensor as bt
import httpx

# import base validator class which takes care of most of the boilerplate
from template.base.validator import BaseValidatorNeuron

# Bittensor Validator Template:

from template.protocol import AudioTask


class Validator(BaseValidatorNeuron):
    """
    Enhanced Audio processing validator that evaluates transcription, TTS, and summarization services.
    This validator rewards miners based on speed, accuracy, and stake, prioritizing the top 10 performers.
    Features enhanced block monitoring, task evaluation tracking, and comprehensive logging.
    """

    def __init__(self, config=None):
        # Initialize critical attributes BEFORE calling parent constructor
        self.proxy_tasks_processed_this_epoch = False
        self.proxy_server_url = "http://localhost:8000"  # Proxy server URL
        self.last_miner_status_report = 0
        self.miner_status_report_interval = 100  # Report every 100 blocks (1 epoch)
        
        # Enhanced block monitoring and evaluation tracking
        self.current_epoch = 0
        self.last_evaluation_block = 0
        self.evaluation_interval = 100  # Evaluate every 100 blocks
        self.evaluated_tasks_cache = set()  # In-memory cache of evaluated tasks
        self.evaluation_history = {}  # Track evaluation history per epoch
        self.performance_metrics = {}  # Track performance metrics over time
        
        # Weight setting optimization
        self.last_weight_setting_block = 0
        self.weight_setting_interval = 100  # Set weights every 100 blocks
        self.miner_weight_history = {}  # Track weight changes over time
        
        # Enhanced logging and monitoring
        self.log_file_path = f"logs/validator/validator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.performance_log_path = f"logs/validator/performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        super(Validator, self).__init__(config=config)

        bt.logging.info("load_state()")
        self.load_state()

        # Ensure log directories exist (after parent constructor)
        os.makedirs("logs/validator", exist_ok=True)

        # Proxy server integration settings
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
        
        # Initialize the SAME pipelines that miners use for fair comparison
        self.initialize_miner_pipelines()
        
        # Initialize enhanced monitoring
        self.initialize_enhanced_monitoring()
        
        bt.logging.info("🚀 Enhanced validator initialized with comprehensive monitoring and evaluation tracking")
    
    def initialize_miner_pipelines(self):
        """Initialize the exact same pipelines that miners use for fair comparison"""
        try:
            bt.logging.info("🔧 Initializing miner pipelines for fair comparison...")
            
            # Initialize transcription pipeline (same as miner)
            try:
                from template.pipelines.transcription_pipeline import TranscriptionPipeline
                self.transcription_pipeline = TranscriptionPipeline()
                bt.logging.info("✅ Transcription pipeline initialized (same as miner)")
            except Exception as e:
                bt.logging.error(f"❌ Failed to initialize transcription pipeline: {e}")
                self.transcription_pipeline = None
            
            # Initialize TTS pipeline (same as miner)
            try:
                from template.pipelines.tts_pipeline import TTSPipeline
                self.tts_pipeline = TTSPipeline()
                bt.logging.info("✅ TTS pipeline initialized (same as miner)")
            except ImportError as e:
                bt.logging.warning(f"⚠️ TTS pipeline not available (TTS module not installed): {e}")
                self.tts_pipeline = None
            except Exception as e:
                bt.logging.error(f"❌ Failed to initialize TTS pipeline: {e}")
                self.tts_pipeline = None
            
            # Initialize summarization pipeline (same as miner)
            try:
                from template.pipelines.summarization_pipeline import SummarizationPipeline
                self.summarization_pipeline = SummarizationPipeline()
                bt.logging.info("✅ Summarization pipeline initialized (same as miner)")
            except Exception as e:
                bt.logging.error(f"❌ Failed to initialize summarization pipeline: {e}")
                self.summarization_pipeline = None
            
            bt.logging.info("🎯 Miner pipelines initialization complete - validator now uses EXACTLY the same pipelines!")
            
        except Exception as e:
            bt.logging.error(f"❌ Error initializing miner pipelines: {str(e)}")
    
    def initialize_enhanced_monitoring(self):
        """Initialize enhanced monitoring and tracking systems"""
        try:
            bt.logging.info("🔧 Initializing enhanced monitoring systems...")
            
            # Load existing evaluation history if available
            self.load_evaluation_history()
            
            # Initialize current epoch
            self.current_epoch = self.block // self.evaluation_interval if hasattr(self, 'block') else 0
            
            # Log initialization
            bt.logging.info(f"📊 Enhanced monitoring initialized:")
            bt.logging.info(f"   Current Block: {getattr(self, 'block', 'Unknown')}")
            bt.logging.info(f"   Current Epoch: {self.current_epoch}")
            bt.logging.info(f"   Evaluation Interval: {self.evaluation_interval} blocks")
            bt.logging.info(f"   Weight Setting Interval: {self.weight_setting_interval} blocks")
            bt.logging.info(f"   Log File: {self.log_file_path}")
            bt.logging.info(f"   Performance Log: {self.performance_log_path}")
            
        except Exception as e:
            bt.logging.error(f"❌ Error initializing enhanced monitoring: {str(e)}")
    
    def load_evaluation_history(self):
        """Load evaluation history from disk if available"""
        try:
            history_file = "logs/validator/evaluation_history.pkl"
            if os.path.exists(history_file):
                with open(history_file, 'rb') as f:
                    self.evaluation_history = pickle.load(f)
                bt.logging.info(f"📚 Loaded evaluation history: {len(self.evaluation_history)} epochs")
            else:
                self.evaluation_history = {}
                bt.logging.info("📚 No existing evaluation history found, starting fresh")
        except Exception as e:
            bt.logging.warning(f"⚠️  Could not load evaluation history: {str(e)}")
            self.evaluation_history = {}
    
    def save_evaluation_history(self):
        """Save evaluation history to disk"""
        try:
            history_file = "logs/validator/evaluation_history.pkl"
            with open(history_file, 'wb') as f:
                pickle.dump(self.evaluation_history, f)
            bt.logging.debug("💾 Evaluation history saved to disk")
        except Exception as e:
            bt.logging.warning(f"⚠️  Could not save evaluation history: {str(e)}")
    
    def should_evaluate_tasks(self) -> bool:
        """
        Determine if we should evaluate tasks based on block progression
        """
        if not hasattr(self, 'block'):
            return False
        
        # Check if enough blocks have passed since last evaluation
        blocks_since_evaluation = self.block - self.last_evaluation_block
        
        if blocks_since_evaluation >= self.evaluation_interval:
            bt.logging.info(f"🔍 Evaluation trigger: {blocks_since_evaluation} blocks since last evaluation")
            return True
        
        return False
    
    def should_set_weights(self) -> bool:
        """
        Enhanced weight setting logic with better block monitoring and evaluation tracking
        """
        if not hasattr(self, 'block'):
            return False
        
        # Don't set weights if proxy tasks were processed this epoch
        if self.proxy_tasks_processed_this_epoch:
            bt.logging.info("🔄 Skipping weight setting - proxy tasks were processed this epoch")
            return False
        
        # Don't set weights if there are no reachable miners
        if not hasattr(self, 'reachable_miners') or not self.reachable_miners:
            bt.logging.info("🔄 Skipping weight setting - no reachable miners available")
            return False
        
        # Check if enough blocks have passed since last weight setting
        blocks_since_weight_setting = self.block - self.last_weight_setting_block
        
        if blocks_since_weight_setting >= self.weight_setting_interval:
            bt.logging.info(f"⚖️  Weight setting trigger: {blocks_since_weight_setting} blocks since last weight setting")
            
            # Reset the flag when we're about to set weights (new epoch)
            self.proxy_tasks_processed_this_epoch = False
            
            # Update tracking
            self.last_weight_setting_block = self.block
            self.current_epoch = self.block // self.evaluation_interval
            
            return True
        
        return False
    
    def log_block_status(self):
        """Log current block status and monitoring information"""
        try:
            if hasattr(self, 'block'):
                bt.logging.info("=" * 80)
                bt.logging.info(f"📊 BLOCK STATUS UPDATE - Block {self.block}")
                bt.logging.info(f"   Current Epoch: {self.current_epoch}")
                bt.logging.info(f"   Blocks Since Last Evaluation: {self.block - self.last_evaluation_block}")
                bt.logging.info(f"   Blocks Since Last Weight Setting: {self.block - self.last_weight_setting_block}")
                bt.logging.info(f"   Evaluation Interval: {self.evaluation_interval} blocks")
                bt.logging.info(f"   Weight Setting Interval: {self.weight_setting_interval} blocks")
                
                # Log miner status
                if hasattr(self, 'reachable_miners'):
                    bt.logging.info(f"   Reachable Miners: {len(self.reachable_miners)}")
                    if self.reachable_miners:
                        top_miners = sorted(self.reachable_miners, key=lambda x: self.metagraph.S[x], reverse=True)[:3]
                        bt.logging.info(f"   Top Miners by Stake: {top_miners}")
                
                # Log evaluation status
                if self.evaluated_tasks_cache:
                    bt.logging.info(f"   Tasks Evaluated This Epoch: {len(self.evaluated_tasks_cache)}")
                
                bt.logging.info("=" * 80)
                
        except Exception as e:
            bt.logging.error(f"❌ Error logging block status: {str(e)}")

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
                                # Only log active miners - no more verbose logging for inactive ones
                                bt.logging.info(f"✅ UID {uid:3d} | {ip}:{port} | Stake: {stake:,.0f} TAO | Status: {status}")
                            else:
                                # Silent for inactive miners - only debug level
                                bt.logging.debug(f"⚠️  UID {uid:3d} | {ip}:{port} | Unresponsive (Status: {status})")
                        else:
                            # Silent for inactive miners - only debug level
                            bt.logging.debug(f"❌ UID {uid:3d} | {ip}:{port} | No response")
                        
                    except Exception as e:
                        # Silent for inactive miners - only debug level
                        bt.logging.debug(f"❌ UID {uid:3d} | {ip}:{port} | Connection failed: {str(e)[:30]}...")
                    # No logging for offline miners - completely silent
            
            # Clean connectivity summary - only show active miners
            if reachable_miners:
                # Only show active miners by stake
                top_miners = sorted(reachable_miners, key=lambda x: self.metagraph.S[x], reverse=True)[:3]
                bt.logging.info(f"🎯 Active Miners: {len(reachable_miners)} reachable")
                bt.logging.info(f"   Top by stake: {top_miners}")
                
                # Store reachable miners for use in task assignment
                self.reachable_miners = reachable_miners
            else:
                bt.logging.warning("⚠️  No active miners available!")
                self.reachable_miners = []
            
            # Clean separator
            bt.logging.info("─" * 50)
            
        except Exception as e:
            bt.logging.error(f"❌ Error checking miner connectivity: {str(e)}")
            self.reachable_miners = []
    
    async def forward(self):
        """
        Enhanced validator forward pass with comprehensive monitoring and evaluation tracking.
        Consists of:
        - Block status monitoring and logging
        - Proxy server task checking
        - Task evaluation and weight setting
        - Performance tracking and reporting
        - Periodic maintenance and cleanup
        """
        try:
            # Log block status every 10 blocks for monitoring
            if hasattr(self, 'block') and self.step % 10 == 0:
                self.log_block_status()
            
            # Perform periodic maintenance
            self.periodic_maintenance()
            
            # Check if we should evaluate tasks based on block progression
            if self.should_evaluate_tasks():
                bt.logging.info(f"🔍 Evaluation trigger activated at block {self.block}")
                await self.trigger_task_evaluation()
            
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
                
                # Run the enhanced task evaluation and weight setting process
                await self.evaluate_completed_tasks_and_set_weights()
                return None
                
        except Exception as e:
            bt.logging.error(f"❌ Error in enhanced forward pass: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    async def trigger_task_evaluation(self):
        """Trigger task evaluation when conditions are met"""
        try:
            bt.logging.info("🚀 Triggering task evaluation...")
            
            # Update evaluation tracking
            self.last_evaluation_block = self.block
            
            # Check if we have completed tasks to evaluate
            if self.enable_proxy_integration:
                await self.evaluate_completed_tasks_and_set_weights()
            else:
                bt.logging.info("⚠️  Proxy integration disabled, skipping task evaluation")
                
        except Exception as e:
            bt.logging.error(f"❌ Error triggering task evaluation: {str(e)}")
    
    async def _run_standard_forward(self):
        """Standard forward pass implementation with enhanced monitoring"""
        try:
            # Check miner connectivity and register them
            await self.check_miner_connectivity()
            
            # Report miner status to proxy server
            if hasattr(self, 'reachable_miners') and self.reachable_miners:
                await self.report_miner_status_to_proxy()
            
            # Check if we have any reachable miners
            if not hasattr(self, 'reachable_miners') or not self.reachable_miners:
                bt.logging.warning("No reachable miners available. Skipping this round.")
                return
            
            # Log standard forward pass execution
            bt.logging.info("🔄 Running standard forward pass with enhanced monitoring...")
            
            # Update performance metrics
            self.update_performance_metrics('standard_forward', success=True)
            
            return None
            
        except Exception as e:
            bt.logging.error(f"❌ Error in standard forward pass: {str(e)}")
            self.update_performance_metrics('standard_forward', success=False, error=str(e))
            return None
    
    def update_performance_metrics(self, operation: str, success: bool, error: str = None, **kwargs):
        """Update performance metrics for monitoring and analysis"""
        try:
            if operation not in self.performance_metrics:
                self.performance_metrics[operation] = {
                    'total_calls': 0,
                    'successful_calls': 0,
                    'failed_calls': 0,
                    'errors': [],
                    'last_call': None,
                    'avg_response_time': 0.0,
                    'response_times': []
                }
            
            metrics = self.performance_metrics[operation]
            metrics['total_calls'] += 1
            metrics['last_call'] = datetime.now().isoformat()
            
            if success:
                metrics['successful_calls'] += 1
            else:
                metrics['failed_calls'] += 1
                if error:
                    metrics['errors'].append({
                        'timestamp': datetime.now().isoformat(),
                        'error': error
                    })
            
            # Keep only last 100 errors to prevent memory bloat
            if len(metrics['errors']) > 100:
                metrics['errors'] = metrics['errors'][-100:]
            
            # Log performance update
            success_rate = (metrics['successful_calls'] / metrics['total_calls']) * 100
            bt.logging.debug(f"📊 Performance update for {operation}: {success_rate:.1f}% success rate")
            
        except Exception as e:
            bt.logging.warning(f"⚠️  Error updating performance metrics: {str(e)}")
    
    def get_performance_summary(self) -> Dict:
        """Get a summary of current performance metrics"""
        try:
            summary = {
                'total_operations': 0,
                'overall_success_rate': 0.0,
                'operation_breakdown': {},
                'recent_errors': [],
                'timestamp': datetime.now().isoformat()
            }
            
            total_successful = 0
            total_calls = 0
            
            for operation, metrics in self.performance_metrics.items():
                total_calls += metrics['total_calls']
                total_successful += metrics['successful_calls']
                
                success_rate = (metrics['successful_calls'] / metrics['total_calls']) * 100 if metrics['total_calls'] > 0 else 0
                
                summary['operation_breakdown'][operation] = {
                    'total_calls': metrics['total_calls'],
                    'success_rate': success_rate,
                    'last_call': metrics['last_call']
                }
                
                # Collect recent errors
                if metrics['errors']:
                    summary['recent_errors'].extend(metrics['errors'][-5:])  # Last 5 errors per operation
            
            if total_calls > 0:
                summary['overall_success_rate'] = (total_successful / total_calls) * 100
            
            summary['total_operations'] = total_calls
            
            return summary
            
        except Exception as e:
            bt.logging.error(f"❌ Error generating performance summary: {str(e)}")
            return {'error': str(e)}
    
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
        Enhanced main method for evaluating completed tasks and setting miner weights.
        This method:
        1. Tests proxy server connection
        2. Fetches completed tasks from proxy server
        3. Filters out already evaluated tasks
        4. Executes each task as a miner would
        5. Compares validator results with miner results
        6. Calculates scores and ranks for each miner
        7. Sets weights based on cumulative performance
        8. Generates comprehensive performance reports
        9. Tracks evaluation history and performance metrics
        """
        try:
            start_time = time.time()
            bt.logging.info("🚀 Starting enhanced task evaluation and weight setting process...")
            
            # Update performance metrics
            self.update_performance_metrics('evaluation_start', success=True)
            
            # First test proxy server connection
            bt.logging.info("🔍 Testing proxy server connection...")
            if not await self.test_proxy_server_connection():
                bt.logging.error("❌ Failed to connect to proxy server, aborting evaluation")
                self.update_performance_metrics('evaluation_start', success=False, error="Proxy server connection failed")
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
            
            # Log summary of tasks to be evaluated
            bt.logging.info("=" * 80)
            bt.logging.info("📊 TASKS SELECTED FOR EVALUATION")
            bt.logging.info("=" * 80)
            
            # Count tasks by type and status
            task_type_counts = {}
            status_counts = {}
            miner_response_counts = []
            
            for task in new_tasks:
                task_type = task.get('task_type', 'unknown')
                task_status = task.get('status', 'unknown')
                miner_responses = task.get('miner_responses', [])
                
                task_type_counts[task_type] = task_type_counts.get(task_type, 0) + 1
                status_counts[task_status] = status_counts.get(task_status, 0) + 1
                miner_response_counts.append(len(miner_responses))
            
            bt.logging.info(f"📋 Task Type Breakdown:")
            for task_type, count in task_type_counts.items():
                bt.logging.info(f"   {task_type.capitalize()}: {count} tasks")
            
            bt.logging.info(f"\n📊 Status Breakdown:")
            for status, count in status_counts.items():
                bt.logging.info(f"   {status}: {count} tasks")
            
            if miner_response_counts:
                avg_responses = sum(miner_response_counts) / len(miner_response_counts)
                min_responses = min(miner_response_counts)
                max_responses = max(miner_response_counts)
                bt.logging.info(f"\n👥 Miner Response Statistics:")
                bt.logging.info(f"   Average responses per task: {avg_responses:.1f}")
                bt.logging.info(f"   Minimum responses: {min_responses}")
                bt.logging.info(f"   Maximum responses: {max_responses}")
            
            bt.logging.info("=" * 80)
            
            # Initialize miner performance tracking
            miner_performance = {}
            validator_performance = {}  # Track validator's own performance
            
            # Process each completed task
            for task_index, task in enumerate(new_tasks, 1):
                task_id = task.get('task_id')
                task_type = task.get('task_type')
                task_status = task.get('status', 'unknown')
                miner_responses = task.get('miner_responses', [])
                
                # Double-check task status - only process completed tasks
                if task_status != 'completed':
                    bt.logging.warning(f"⚠️ Task {task_id} has status '{task_status}', not 'completed'. Skipping evaluation.")
                    continue
                
                # Enhanced task logging with progress tracking
                bt.logging.info("=" * 80)
                bt.logging.info(f"🔍 EVALUATING TASK {task_index}/{len(new_tasks)}: {task_id}")
                bt.logging.info(f"📋 Task Details:")
                bt.logging.info(f"   Type: {task_type}")
                bt.logging.info(f"   Status: {task_status} ✅ (Confirmed completed)")
                bt.logging.info(f"   Language: {task.get('language', 'en')}")
                bt.logging.info(f"   Created: {task.get('created_at', 'N/A')}")
                bt.logging.info(f"   Completed: {task.get('completed_at', 'N/A')}")
                bt.logging.info(f"   Miner Responses: {len(miner_responses)}")
                
                # Validate that this is truly a completed task with proper data
                if not miner_responses:
                    bt.logging.warning(f"⚠️ Task {task_id} has no miner responses despite being 'completed'. This may indicate a data inconsistency.")
                    bt.logging.info("=" * 80)
                    continue
                
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
                
                # Additional validation for completed task structure
                bt.logging.info(f"🔍 Validating completed task structure...")
                validation_passed = True
                
                # Check if all miner responses have required fields
                for i, response in enumerate(miner_responses):
                    miner_uid = response.get('miner_uid')
                    if miner_uid is None:
                        bt.logging.warning(f"⚠️ Miner response {i+1} missing miner_uid")
                        validation_passed = False
                    
                    if response.get('processing_time') is None:
                        bt.logging.warning(f"⚠️ Miner response {i+1} missing processing_time")
                        validation_passed = False
                    
                    if response.get('submitted_at') is None:
                        bt.logging.warning(f"⚠️ Miner response {i+1} missing submitted_at")
                        validation_passed = False
                
                if not validation_passed:
                    bt.logging.error(f"❌ Task {task_id} failed validation. Skipping evaluation.")
                    bt.logging.info("=" * 80)
                    continue
                
                bt.logging.info(f"✅ Task structure validation passed")

                # Additional validation: Check if task has the required input data
                bt.logging.info(f"🔍 VALIDATING TASK INPUT DATA:")
                input_data_available = False
                
                # Check multiple possible sources for input data
                if task.get('input_data'):
                    bt.logging.info(f"   ✅ input_data field found")
                    input_data_available = True
                elif task.get('input_file_id'):
                    bt.logging.info(f"   ✅ input_file_id field found")
                    input_data_available = True
                elif task.get('input_file'):
                    input_file = task.get('input_file', {})
                    if isinstance(input_file, dict):
                        if input_file.get('content') or input_file.get('file_id'):
                            bt.logging.info(f"   ✅ input_file object with content/file_id found")
                            input_data_available = True
                        else:
                            bt.logging.warning(f"   ⚠️ input_file object found but no content/file_id")
                    else:
                        bt.logging.info(f"   ✅ input_file as direct data found")
                        input_data_available = True
                
                if not input_data_available:
                    bt.logging.error(f"❌ Task {task_id} missing required input data - cannot execute")
                    bt.logging.error(f"   Available fields: {list(task.keys())}")
                    bt.logging.error(f"   Task data preview: {str(task)[:500]}...")
                    bt.logging.info("=" * 80)
                    continue
                
                bt.logging.info(f"✅ Task input data validation passed")

                # Execute task as validator (like a miner would) using actual pipelines
                bt.logging.info(f"🔧 EXECUTING TASK AS VALIDATOR:")
                bt.logging.info(f"   Task Type: {task_type}")
                bt.logging.info(f"   Pipeline: {self._get_pipeline_name(task_type)}")
                bt.logging.info(f"   Pipeline Description: {self._get_pipeline_description(task_type)}")
                
                # Log pipeline execution details
                pipeline_info = {
                    'transcription': {
                        'input_format': 'Audio data (base64 encoded)',
                        'output_format': 'Transcribed text with confidence',
                        'key_metrics': 'Accuracy, processing time, language detection'
                    },
                    'tts': {
                        'input_format': 'Text data',
                        'output_format': 'Audio data with duration',
                        'key_metrics': 'Audio quality, processing time, text-to-speech accuracy'
                    },
                    'summarization': {
                        'input_format': 'Long text data',
                        'output_format': 'Summarized text with key points',
                        'key_metrics': 'Summary quality, processing time, key point extraction'
                    }
                }
                
                if task_type in pipeline_info:
                    info = pipeline_info[task_type]
                    bt.logging.info(f"   Pipeline Details:")
                    bt.logging.info(f"      Input Format: {info['input_format']}")
                    bt.logging.info(f"      Output Format: {info['output_format']}")
                    bt.logging.info(f"      Key Metrics: {info['key_metrics']}")
                
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
            
            # CRITICAL FIX: Check if we have any weights to set
            if not final_weights:
                bt.logging.warning("⚠️ No final weights calculated - skipping weight setting")
                bt.logging.info("🎯 Task evaluation completed (no weights to set)")
                bt.logging.info(f"📊 Processed {len(new_tasks)} tasks for {len(miner_performance)} miners")
                
                # Log completion without weight setting
                evaluation_time = time.time() - start_time
                bt.logging.info(f"⏱️  Total evaluation time: {evaluation_time:.2f} seconds")
                bt.logging.info(f"📊 Average time per task: {evaluation_time / len(new_tasks):.2f} seconds")
                
                # Log comprehensive evaluation summary
                current_epoch = getattr(self, 'current_epoch', 0)
                self.log_evaluation_summary(current_epoch, len(new_tasks), miner_performance)
                
                # Update performance metrics
                self.update_performance_metrics('evaluation_complete', success=True, 
                                             evaluation_time=evaluation_time, 
                                             tasks_processed=len(new_tasks),
                                             miners_evaluated=len(miner_performance))
                
                # Save evaluation history
                self.save_evaluation_history()
                return
            
            # Log final weight summary
            bt.logging.info("🎯 Final Weight Summary:")
            for miner_uid, weight in sorted(final_weights.items(), key=lambda x: x[1], reverse=True):
                performance = miner_performance.get(miner_uid, {})
                task_count = performance.get('task_count', 0)
                bt.logging.info(f"   Miner {miner_uid}: Weight={weight:.2f}, Tasks={task_count}")
            
            # Set weights on chain
            await self.set_miner_weights(final_weights)
            
            # Calculate and log evaluation performance
            evaluation_time = time.time() - start_time
            bt.logging.info(f"⏱️  Total evaluation time: {evaluation_time:.2f} seconds")
            bt.logging.info(f"📊 Average time per task: {evaluation_time / len(new_tasks):.2f} seconds")
            
            # Log completion
            bt.logging.info("🎯 Task evaluation and weight setting completed successfully!")
            bt.logging.info(f"📊 Processed {len(new_tasks)} tasks for {len(miner_performance)} miners")
            
            # Log comprehensive evaluation summary
            current_epoch = getattr(self, 'current_epoch', 0)
            self.log_evaluation_summary(current_epoch, len(new_tasks), miner_performance)
            
            # Update performance metrics
            self.update_performance_metrics('evaluation_complete', success=True, 
                                         evaluation_time=evaluation_time, 
                                         tasks_processed=len(new_tasks),
                                         miners_evaluated=len(miner_performance))
            
            # Save evaluation history
            self.save_evaluation_history()
            
        except Exception as e:
            bt.logging.error(f"❌ Error in task evaluation and weight setting: {str(e)}")
            self.update_performance_metrics('evaluation_complete', success=False, error=str(e))
            import traceback
            traceback.print_exc()

    async def fetch_completed_tasks_from_proxy(self) -> List[Dict]:
        """
        Fetch completed tasks from proxy server with miner responses attached.
        Only tasks with status 'completed' are considered for evaluation and rewarding.
        """
        try:
            bt.logging.info(f"🔍 Fetching completed tasks from proxy server: {self.proxy_server_url}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.proxy_server_url}/api/v1/tasks/completed",
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    tasks = response.json()
                    bt.logging.info(f"📥 Successfully fetched {len(tasks)} tasks from proxy server")
                    
                    # Filter for ONLY tasks with status 'completed'
                    completed_tasks = []
                    other_status_tasks = []
                    
                    for task in tasks:
                        task_id = task.get('task_id', 'unknown')
                        task_status = task.get('status', 'unknown')
                        task_type = task.get('task_type', 'unknown')
                        miner_responses = task.get('miner_responses', [])
                        
                        if task_status == 'completed':
                            completed_tasks.append(task)
                            bt.logging.info(f"   ✅ Task {task_id}: {task_type} - Status: {task_status} - {len(miner_responses)} miner responses")
                        else:
                            other_status_tasks.append(task)
                            bt.logging.debug(f"   ⚠️ Task {task_id}: {task_type} - Status: {task_status} - Skipping (not completed)")
                    
                    bt.logging.info(f"📊 Task Status Breakdown:")
                    bt.logging.info(f"   ✅ Completed tasks: {len(completed_tasks)}")
                    bt.logging.info(f"   ⚠️ Other status tasks: {len(other_status_tasks)}")
                    
                    if other_status_tasks:
                        status_counts = {}
                        for task in other_status_tasks:
                            status = task.get('status', 'unknown')
                            status_counts[status] = status_counts.get(status, 0) + 1
                        
                        bt.logging.info(f"   📋 Other status breakdown:")
                        for status, count in status_counts.items():
                            bt.logging.info(f"      {status}: {count} tasks")
                    
                    if not completed_tasks:
                        bt.logging.info("📭 No completed tasks found for evaluation")
                        return []
                    
                    # Additional validation for completed tasks
                    valid_completed_tasks = []
                    invalid_tasks = []
                    
                    for task in completed_tasks:
                        task_id = task.get('task_id', 'unknown')
                        task_type = task.get('task_type', 'unknown')
                        miner_responses = task.get('miner_responses', [])
                        created_at = task.get('created_at')
                        completed_at = task.get('completed_at')
                        
                        # Validate required fields
                        validation_errors = []
                        
                        if not miner_responses:
                            validation_errors.append("No miner responses")
                        
                        if not task_type:
                            validation_errors.append("No task type")
                        
                        if not created_at:
                            validation_errors.append("No creation timestamp")
                        
                        # Check if task has been processed by miners
                        if miner_responses:
                            valid_responses = 0
                            for response in miner_responses:
                                if (response.get('miner_uid') is not None and 
                                    response.get('processing_time') is not None and
                                    response.get('submitted_at') is not None):
                                    valid_responses += 1
                            
                            if valid_responses == 0:
                                validation_errors.append("No valid miner responses")
                        
                        if validation_errors:
                            invalid_tasks.append({
                                'task_id': task_id,
                                'task_type': task_type,
                                'errors': validation_errors
                            })
                            bt.logging.warning(f"⚠️ Task {task_id} validation failed: {', '.join(validation_errors)}")
                        else:
                            valid_completed_tasks.append(task)
                            bt.logging.debug(f"   ✅ Task {task_id} validation passed")
                    
                    bt.logging.info(f"📊 Validation Results:")
                    bt.logging.info(f"   ✅ Valid completed tasks: {len(valid_completed_tasks)}")
                    bt.logging.info(f"   ❌ Invalid tasks: {len(invalid_tasks)}")
                    
                    if invalid_tasks:
                        bt.logging.info(f"   📋 Invalid task details:")
                        for invalid_task in invalid_tasks[:5]:  # Show first 5 invalid tasks
                            bt.logging.info(f"      Task {invalid_task['task_id']} ({invalid_task['task_type']}): {', '.join(invalid_task['errors'])}")
                        
                        if len(invalid_tasks) > 5:
                            bt.logging.info(f"      ... and {len(invalid_tasks) - 5} more invalid tasks")
                    
                    # Log final summary
                    bt.logging.info(f"🎯 Final Result: {len(valid_completed_tasks)} valid completed tasks ready for evaluation")
                    
                    # Log details about each valid completed task
                    for task in valid_completed_tasks:
                        task_id = task.get('task_id', 'unknown')
                        task_type = task.get('task_type', 'unknown')
                        miner_responses = task.get('miner_responses', [])
                        created_at = task.get('created_at', 'N/A')
                        completed_at = task.get('completed_at', 'N/A')
                        
                        bt.logging.info(f"   📋 Valid Task {task_id}:")
                        bt.logging.info(f"      Type: {task_type}")
                        bt.logging.info(f"      Created: {created_at}")
                        bt.logging.info(f"      Completed: {completed_at}")
                        bt.logging.info(f"      Miner Responses: {len(miner_responses)}")
                        
                        # Log miner response summary
                        for i, response in enumerate(miner_responses[:3], 1):  # Show first 3 responses
                            miner_uid = response.get('miner_uid', 'unknown')
                            processing_time = response.get('processing_time', 0)
                            accuracy_score = response.get('accuracy_score', 0)
                            submitted_at = response.get('submitted_at', 'N/A')
                            bt.logging.info(f"         Miner {i}: UID {miner_uid} | Time: {processing_time:.2f}s | Accuracy: {accuracy_score:.3f} | Submitted: {submitted_at}")
                        
                        if len(miner_responses) > 3:
                            bt.logging.info(f"         ... and {len(miner_responses) - 3} more miner responses")
                    
                    return valid_completed_tasks
                    
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
        The validator runs the appropriate pipeline based on task type.
        ENHANCED: Uses the same robust patterns as the miner for consistent processing.
        """
        try:
            task_id = task.get('task_id', 'unknown')
            task_type = task.get('task_type')
            
            bt.logging.info(f"🔧 EXECUTING TASK {task_id} AS VALIDATOR (ENHANCED)")
            bt.logging.info(f"   Task Type: {task_type}")
            bt.logging.info(f"   Available Fields: {list(task.keys())}")
            
            # ENHANCED: Use the same robust input data extraction as miner
            input_data = await self._extract_input_data_robust(task, task_id)
            if not input_data:
                bt.logging.error(f"❌ Task {task_id} - Failed to extract input data")
                return None
            
            # ENHANCED: Validate input data using same checks as miner
            validation_result = await self._validate_input_data_robust(input_data, task_type, task_id)
            if not validation_result['valid']:
                bt.logging.error(f"❌ Task {task_id} - Input validation failed: {validation_result['reason']}")
                return None
            
            # ENHANCED: Process task using the same pipeline execution pattern as miner
            start_time = time.time()
            result = await self._execute_pipeline_robust(task_type, input_data, task_id)
            total_time = time.time() - start_time
            
            if result:
                # ENHANCED: Log results using the same format as miner
                await self._log_task_execution_result(task_id, task_type, result, total_time)
                return result
            else:
                bt.logging.error(f"❌ Task {task_id} execution failed - no result returned")
                return None
                
        except Exception as e:
            bt.logging.error(f"❌ Error executing task as validator: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    async def _extract_input_data_robust(self, task: Dict, task_id: str) -> Optional[Any]:
        """
        ENHANCED: Extract input data using the same robust pattern as miner.
        Handles multiple possible field names and formats consistently.
        """
        try:
            bt.logging.info(f"   🔍 EXTRACTING INPUT DATA (ROBUST METHOD):")
            
            # CRITICAL FIX: The proxy server already provides processed input_data
            # We should use this directly instead of trying to extract file IDs
            if "input_data" in task and task["input_data"]:
                input_data = task["input_data"]
                bt.logging.info(f"      ✅ Found input_data directly: {len(str(input_data))} chars")
                return input_data
            
            # Fallback: Try multiple possible field names (same as miner)
            possible_fields = [
                "input_file_id",        # File ID field
                "input_file",           # Object field
                "file_id",              # Alternative field name
                "audio_file_id",        # Audio-specific field
                "input_data_id"         # Another alternative
            ]
            
            input_data = None
            for field in possible_fields:
                if field in task:
                    field_value = task[field]
                    if isinstance(field_value, str) and field_value:
                        input_data = field_value
                        bt.logging.info(f"      ✅ Found input_file_id in field '{field}': {input_data}")
                        break
                    elif isinstance(field_value, dict) and field_value.get('file_id'):
                        input_data = field_value['file_id']
                        bt.logging.info(f"      ✅ Found input_file_id in field '{field}.file_id': {input_data}")
                        break
            
            # If still no input_data, try to extract from nested structures (same as miner)
            if not input_data:
                for key, value in task.items():
                    if isinstance(value, dict) and 'file_id' in value:
                        input_data = value['file_id']
                        bt.logging.info(f"      ✅ Found input_file_id in nested field '{key}.file_id': {input_data}")
                        break
                    elif isinstance(value, dict) and 'input_file_id' in value:
                        input_data = value['input_file_id']
                        bt.logging.info(f"      ✅ Found input_file_id in nested field '{key}.input_file_id': {input_data}")
                        break
            
            if input_data:
                bt.logging.info(f"      ✅ Successfully extracted input data: {len(str(input_data))} chars")
                return input_data
            else:
                bt.logging.warning(f"      ⚠️ Could not find input data in task:")
                bt.logging.warning(f"         Available fields: {list(task.keys())}")
                for key, value in task.items():
                    bt.logging.warning(f"         {key}: {type(value).__name__} = {str(value)[:100]}...")
                return None
                
        except Exception as e:
            bt.logging.error(f"❌ Error extracting input data: {str(e)}")
            return None

    async def _validate_input_data_robust(self, input_data: Any, task_type: str, task_id: str) -> Dict:
        """
        ENHANCED: Validate input data using the same checks as miner.
        Ensures data quality and format consistency.
        """
        try:
            bt.logging.info(f"   🔍 VALIDATING INPUT DATA (ROBUST METHOD):")
            
            validation_result = {
                'valid': False,
                'reason': '',
                'data_size': 0,
                'data_type': type(input_data).__name__
            }
            
            # Check if input_data exists
            if not input_data:
                validation_result['reason'] = 'Input data is empty or None'
                return validation_result
            
            # Get data size
            if isinstance(input_data, str):
                validation_result['data_size'] = len(input_data)
            elif isinstance(input_data, bytes):
                validation_result['data_size'] = len(input_data)
            else:
                validation_result['data_size'] = len(str(input_data))
            
            bt.logging.info(f"      📊 Data Type: {validation_result['data_type']}")
            bt.logging.info(f"      📊 Data Size: {validation_result['data_size']}")
            
            # ENHANCED: Same validation logic as miner
            if validation_result['data_size'] == 0:
                validation_result['reason'] = 'Input data is empty (0 bytes/chars)'
                bt.logging.warning(f"      ⚠️ Empty input data detected")
                return validation_result
            
            # Check for suspiciously small files (same as miner)
            if validation_result['data_size'] < 100:  # Less than 100 chars/bytes is suspicious
                validation_result['reason'] = f'Input data is suspiciously small ({validation_result["data_size"]} chars/bytes)'
                bt.logging.warning(f"      ⚠️ Suspiciously small input data detected")
                return validation_result
            
            # Type-specific validation (same as miner)
            if task_type == "transcription":
                if not isinstance(input_data, str):
                    validation_result['reason'] = f'Transcription expects base64 string, got {type(input_data)}'
                    return validation_result
                # Validate base64 format
                try:
                    import base64
                    decoded = base64.b64decode(input_data)
                    bt.logging.info(f"      ✅ Base64 validation passed: {len(decoded)} bytes decoded")
                except Exception as e:
                    validation_result['reason'] = f'Invalid base64 format: {str(e)}'
                    return validation_result
            
            elif task_type in ["tts", "summarization"]:
                if not isinstance(input_data, str):
                    validation_result['reason'] = f'{task_type.capitalize()} expects text string, got {type(input_data)}'
                    return validation_result
                if len(input_data.strip()) < 10:
                    validation_result['reason'] = f'{task_type.capitalize()} text too short (min 10 chars)'
                    return validation_result
            
            validation_result['valid'] = True
            bt.logging.info(f"      ✅ Input data validation passed")
            return validation_result
            
        except Exception as e:
            bt.logging.error(f"❌ Error validating input data: {str(e)}")
            return {'valid': False, 'reason': f'Validation error: {str(e)}'}

    async def _execute_pipeline_robust(self, task_type: str, input_data: Any, task_id: str) -> Optional[Dict]:
        """
        ENHANCED: Execute pipeline using the same robust pattern as miner.
        Handles errors gracefully and provides consistent output format.
        """
        try:
            bt.logging.info(f"   🔄 EXECUTING PIPELINE (ROBUST METHOD):")
            bt.logging.info(f"      Pipeline: {self._get_pipeline_name(task_type)}")
            
            # Check pipeline availability (same as miner)
            pipeline_available = await self._check_pipeline_availability(task_type)
            if not pipeline_available['available']:
                bt.logging.error(f"      ❌ {pipeline_available['reason']}")
                return None
            
            # Execute task based on type using appropriate pipeline
            start_time = time.time()
            
            if task_type == 'transcription':
                bt.logging.info(f"      🎵 Executing TRANSCRIPTION pipeline...")
                result = await self.execute_transcription_task({'input_data': input_data, 'task_id': task_id})
            elif task_type == 'tts':
                bt.logging.info(f"      🔊 Executing TTS pipeline...")
                result = await self.execute_tts_task({'input_data': input_data, 'task_id': task_id})
            elif task_type == 'summarization':
                bt.logging.info(f"      📝 Executing SUMMARIZATION pipeline...")
                result = await self.execute_summarization_task({'input_data': input_data, 'task_id': task_id})
            else:
                bt.logging.error(f"      ❌ Unknown task type: {task_type}")
                return None
            
            total_time = time.time() - start_time
            
            if result:
                bt.logging.info(f"      ✅ Pipeline execution completed in {total_time:.3f}s")
                return result
            else:
                bt.logging.error(f"      ❌ Pipeline execution failed")
                return None
                
        except Exception as e:
            bt.logging.error(f"❌ Error executing pipeline: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    async def _check_pipeline_availability(self, task_type: str) -> Dict:
        """
        ENHANCED: Check pipeline availability using the same logic as miner.
        """
        try:
            if task_type == "transcription":
                if self.transcription_pipeline is None:
                    return {'available': False, 'reason': 'Transcription pipeline not available'}
            elif task_type == "tts":
                if self.tts_pipeline is None:
                    return {'available': False, 'reason': 'TTS pipeline not available'}
            elif task_type == "summarization":
                if self.summarization_pipeline is None:
                    return {'available': False, 'reason': 'Summarization pipeline not available'}
            
            return {'available': True, 'reason': 'Pipeline available'}
            
        except Exception as e:
            return {'available': False, 'reason': f'Pipeline check error: {str(e)}'}

    async def _log_task_execution_result(self, task_id: str, task_type: str, result: Dict, total_time: float):
        """
        ENHANCED: Log task execution results using the same format as miner.
        """
        try:
            bt.logging.info(f"   ✅ TASK {task_id} EXECUTED SUCCESSFULLY:")
            bt.logging.info(f"      Pipeline: {task_type.capitalize()}")
            bt.logging.info(f"      Total Execution Time: {total_time:.3f}s")
            bt.logging.info(f"      Pipeline Processing Time: {result.get('processing_time', 0):.3f}s")
            bt.logging.info(f"      Accuracy Score: {result.get('accuracy_score', 0):.3f}")
            bt.logging.info(f"      Speed Score: {result.get('speed_score', 0):.3f}")
            
            # Log output data summary (same as miner)
            output_data = result.get('output_data', {})
            if task_type == 'transcription' and 'transcript' in output_data:
                transcript = output_data['transcript']
                bt.logging.info(f"      Output: Transcript ({len(transcript)} chars)")
                bt.logging.debug(f"      Transcript Preview: {transcript[:100]}...")
            elif task_type == 'tts' and 'audio_data' in output_data:
                duration = output_data.get('duration', 0)
                bt.logging.info(f"      Output: Audio ({duration:.1f}s duration)")
            elif task_type == 'summarization' and 'summary' in output_data:
                summary = output_data['summary']
                bt.logging.info(f"      Output: Summary ({len(summary)} chars)")
                bt.logging.debug(f"      Summary Preview: {summary[:100]}...")
            
        except Exception as e:
            bt.logging.error(f"❌ Error logging task execution result: {str(e)}")

    async def execute_transcription_task(self, task: Dict) -> Dict:
        """Execute transcription task as validator using the SAME pipeline as miners"""
        try:
            bt.logging.info(f"🔧 EXECUTING TRANSCRIPTION TASK AS VALIDATOR (ENHANCED)")
            bt.logging.info(f"   Using: {self._get_pipeline_name('transcription')}")
            
            # ENHANCED: Check if pipeline is available (same check as miner)
            if self.transcription_pipeline is None:
                bt.logging.error("❌ Transcription pipeline not available (same as miner)")
                return None
            
            # ENHANCED: Get input data with robust extraction
            input_data = task.get('input_data')
            if not input_data:
                bt.logging.warning("⚠️ No input data found for transcription task")
                return None
            
            # ENHANCED: Decode base64 input if needed (same as miner)
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
            
            # ENHANCED: Validate input data (same validation as miner)
            if not isinstance(audio_bytes, bytes):
                bt.logging.error(f"❌ Invalid audio data type: expected bytes, got {type(audio_bytes)}")
                return None
            
            if len(audio_bytes) == 0:
                bt.logging.error("❌ Audio data is empty")
                return None
            
            # ENHANCED: Check for suspiciously small files (same as miner)
            if len(audio_bytes) < 1000:  # Less than 1KB is suspicious for audio files
                bt.logging.warning(f"⚠️ Audio file is suspiciously small ({len(audio_bytes)} bytes) - may be corrupted")
            
            bt.logging.info(f"🎵 Processing {len(audio_bytes)} bytes of audio data (same as miner)...")
            
            # ENHANCED: Execute transcription using EXACTLY the same method as miner
            start_time = time.time()
            transcribed_text, processing_time = self.transcription_pipeline.transcribe(
                audio_bytes, language="en"  # Same parameters as miner
            )
            total_time = time.time() - start_time
            
            bt.logging.info(f"✅ Transcription completed (same as miner):")
            bt.logging.info(f"   Raw Processing Time: {processing_time:.3f}s")
            bt.logging.info(f"   Total Execution Time: {total_time:.3f}s")
            bt.logging.info(f"   Transcript Length: {len(transcribed_text)} characters")
            
            # ENHANCED: Return result in the same format as miner
            result = {
                'output_data': {
                    'transcript': transcribed_text,
                    'confidence': 0.95,  # Same mock confidence as miner
                    'processing_time': processing_time,
                    'language': 'en'
                },
                'processing_time': processing_time,
                'accuracy_score': 0.95,  # Use same confidence as accuracy
                'speed_score': max(0.5, 1.0 - (processing_time / 5.0))
            }
            
            bt.logging.info(f"✅ Transcription task executed successfully using miner pipeline")
            bt.logging.debug(f"   Transcript: {transcribed_text[:100]}...")
            return result
            
        except Exception as e:
            bt.logging.error(f"❌ Error executing transcription task: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    async def execute_tts_task(self, task: Dict) -> Dict:
        """Execute TTS task as validator using the SAME pipeline as miners"""
        try:
            bt.logging.info(f"🔧 EXECUTING TTS TASK AS VALIDATOR (ENHANCED)")
            bt.logging.info(f"   Using: {self._get_pipeline_name('tts')}")
            
            # ENHANCED: Check if pipeline is available (same check as miner)
            if self.tts_pipeline is None:
                bt.logging.error("❌ TTS pipeline not available (same as miner)")
                return None
            
            # ENHANCED: Get input text with robust extraction
            input_text = task.get('input_data')
            if not input_text:
                bt.logging.warning("⚠️ No input text found for TTS task")
                return None
            
            bt.logging.info(f"   🔍 Processing input text...")
            bt.logging.info(f"      Text Length: {len(input_text)} characters")
            bt.logging.info(f"      Language: {task.get('language', 'en')}")
            
            # ENHANCED: Validate input text (same validation as miner)
            if not isinstance(input_text, str):
                bt.logging.error(f"❌ Invalid input text type: expected string, got {type(input_text)}")
                return None
            
            if len(input_text.strip()) < 5:
                bt.logging.error("❌ Input text too short for TTS (min 5 characters)")
                return None
            
            # ENHANCED: Check for suspiciously small text (same as miner)
            if len(input_text.strip()) < 20:
                bt.logging.warning(f"⚠️ Text is suspiciously short ({len(input_text)} chars) - may not provide good TTS output")
            
            # ENHANCED: Execute TTS using EXACTLY the same method as miner
            bt.logging.info(f"   🔊 Starting TTS synthesis (same as miner)...")
            start_time = time.time()
            
            # Use the same pipeline call as miner
            audio_bytes, processing_time = self.tts_pipeline.synthesize(
                input_text, language="en"  # Same parameters as miner
            )
            
            total_time = time.time() - start_time
            
            bt.logging.info(f"✅ TTS synthesis completed (same as miner):")
            bt.logging.info(f"   Pipeline Processing Time: {processing_time:.3f}s")
            bt.logging.info(f"   Total Execution Time: {total_time:.3f}s")
            bt.logging.info(f"   Audio Data Size: {len(audio_bytes)} bytes")
            
            # ENHANCED: Validate audio output (same as miner)
            if not isinstance(audio_bytes, bytes):
                bt.logging.error(f"❌ Invalid audio output type: expected bytes, got {type(audio_bytes)}")
                return None
            
            if len(audio_bytes) == 0:
                bt.logging.error("❌ Audio output is empty")
                return None
            
            # ENHANCED: Check for suspiciously small audio (same as miner)
            if len(audio_bytes) < 1000:  # Less than 1KB is suspicious for audio
                bt.logging.warning(f"⚠️ Audio output is suspiciously small ({len(audio_bytes)} bytes) - may be corrupted")
            
            # Encode audio as base64 (same as miner)
            import base64
            audio_b64 = base64.b64encode(audio_bytes).decode()
            
            # ENHANCED: Return result in the same format as miner
            result = {
                'output_data': {
                    'audio_data': audio_b64,
                    'duration': len(audio_bytes) / 16000,  # Estimate duration (16kHz sample rate)
                    'language': 'en'
                },
                'processing_time': processing_time,
                'accuracy_score': 0.9,  # Same as miner
                'speed_score': max(0.5, 1.0 - (processing_time / 10.0))
            }
            
            bt.logging.info(f"✅ TTS task executed successfully using miner pipeline")
            return result
            
        except Exception as e:
            bt.logging.error(f"❌ Error executing TTS task: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    async def execute_summarization_task(self, task: Dict) -> Dict:
        """Execute summarization task as validator using the SAME pipeline as miners"""
        try:
            bt.logging.info(f"🔧 EXECUTING SUMMARIZATION TASK AS VALIDATOR (ENHANCED)")
            bt.logging.info(f"   Using: {self._get_pipeline_name('summarization')}")
            
            # ENHANCED: Check if pipeline is available (same check as miner)
            if self.summarization_pipeline is None:
                bt.logging.error("❌ Summarization pipeline not available (same as miner)")
                return None
            
            # ENHANCED: Get input text with robust extraction
            input_text = task.get('input_data')
            if not input_text:
                bt.logging.warning("⚠️ No input text found for summarization task")
                return None
            
            bt.logging.info(f"   🔍 Processing input text...")
            bt.logging.info(f"      Text Length: {len(input_text)} characters")
            bt.logging.info(f"      Language: {task.get('language', 'en')}")
            
            # ENHANCED: Validate input text (same validation as miner)
            if not isinstance(input_text, str):
                bt.logging.error(f"❌ Invalid input text type: expected string, got {type(input_text)}")
                return None
            
            if len(input_text.strip()) < 10:
                bt.logging.error("❌ Input text too short for summarization (min 10 characters)")
                return None
            
            # ENHANCED: Check for suspiciously small text (same as miner)
            if len(input_text.strip()) < 50:
                bt.logging.warning(f"⚠️ Text is suspiciously short ({len(input_text)} chars) - may not provide good summarization")
            
            # ENHANCED: Execute summarization using EXACTLY the same method as miner
            bt.logging.info(f"   📝 Starting text summarization (same as miner)...")
            start_time = time.time()
            
            # Use the same pipeline call as miner
            summary_text, processing_time = self.summarization_pipeline.summarize(
                input_text, language="en"  # Same parameters as miner
            )
            
            total_time = time.time() - start_time
            
            bt.logging.info(f"✅ Summarization completed (same as miner):")
            bt.logging.info(f"   Pipeline Processing Time: {processing_time:.3f}s")
            bt.logging.info(f"   Total Execution Time: {total_time:.3f}s")
            bt.logging.info(f"   Summary Length: {len(summary_text)} characters")
            bt.logging.info(f"   Word Count: {len(summary_text.split())} words")
            
            # ENHANCED: Return result in the same format as miner
            result = {
                'output_data': {
                    'summary': summary_text,
                    'processing_time': processing_time,
                    'text_length': len(input_text),
                    'language': 'en'
                },
                'processing_time': processing_time,
                'accuracy_score': 0.88,  # Same as miner
                'speed_score': max(0.5, 1.0 - (processing_time / 15.0))
            }
            
            bt.logging.info(f"✅ Summarization task executed successfully using miner pipeline")
            bt.logging.debug(f"   Summary: {summary_text[:100]}...")
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
        Scores are calculated based on task type and capped at 500 as per requirement.
        """
        try:
            bt.logging.info(f"📊 CALCULATING SCORES FOR TASK {task_id}")
            bt.logging.info(f"   Task Type: {task_type}")
            bt.logging.info(f"   Validator Result: {len(validator_result.get('output_data', {}))} output fields")
            bt.logging.info(f"   Miner Responses: {len(miner_responses)}")
            
            miner_scores = {}
            score_breakdown = {}
            
            for i, miner_response in enumerate(miner_responses, 1):
                miner_uid = miner_response.get('miner_uid')
                if not miner_uid:
                    bt.logging.warning(f"⚠️ Miner response {i} missing miner_uid, skipping")
                    continue
                
                bt.logging.info(f"   🔍 Evaluating Miner {miner_uid} (Response {i}/{len(miner_responses)}):")
                
                # Calculate accuracy score by comparing with validator result
                accuracy_score = await self.calculate_accuracy_score_for_comparison(
                    validator_result, miner_response, task_type
                )
                
                # Calculate speed score based on processing time
                miner_processing_time = miner_response.get('processing_time', 10.0)
                speed_score = self.calculate_speed_score(miner_processing_time, task_type)
                
                # Calculate quality score based on response structure and completeness
                quality_score = self.calculate_quality_score(miner_response, task_type)
                
                # Task type-specific scoring weights
                if task_type == 'transcription':
                    # Transcription: accuracy is most important
                    weights = {'accuracy': 0.65, 'speed': 0.25, 'quality': 0.10}
                elif task_type == 'tts':
                    # TTS: quality and accuracy are important
                    weights = {'accuracy': 0.50, 'speed': 0.20, 'quality': 0.30}
                elif task_type == 'summarization':
                    # Summarization: accuracy and quality are important
                    weights = {'accuracy': 0.60, 'speed': 0.20, 'quality': 0.20}
                else:
                    # Default weights
                    weights = {'accuracy': 0.60, 'speed': 0.25, 'quality': 0.15}
                
                # Combined score with task type-specific weights
                combined_score = (
                    (accuracy_score * weights['accuracy']) + 
                    (speed_score * weights['speed']) + 
                    (quality_score * weights['quality'])
                )
                
                # Convert to 0-500 scale
                final_score = combined_score * 500.0
                
                # Ensure score doesn't exceed 500 (as per requirement)
                final_score = min(final_score, 500.0)
                
                miner_scores[miner_uid] = final_score
                
                # Store detailed score breakdown for logging
                score_breakdown[miner_uid] = {
                    'accuracy_score': accuracy_score,
                    'speed_score': speed_score,
                    'quality_score': quality_score,
                    'combined_score': combined_score,
                    'final_score': final_score,
                    'weights_used': weights,
                    'processing_time': miner_processing_time
                }
                
                bt.logging.info(f"      Accuracy Score: {accuracy_score:.4f} (Weight: {weights['accuracy']:.2f})")
                bt.logging.info(f"      Speed Score: {speed_score:.4f} (Weight: {weights['speed']:.2f})")
                bt.logging.info(f"      Quality Score: {quality_score:.4f} (Weight: {weights['quality']:.2f})")
                bt.logging.info(f"      Combined Score: {combined_score:.4f}")
                bt.logging.info(f"      Final Score: {final_score:.2f}/500")
                bt.logging.info(f"      Processing Time: {miner_processing_time:.3f}s")
            
            # Log score summary
            if miner_scores:
                scores_list = list(miner_scores.values())
                avg_score = sum(scores_list) / len(scores_list)
                max_score = max(scores_list)
                min_score = min(scores_list)
                
                bt.logging.info(f"   📊 Score Summary for Task {task_id}:")
                bt.logging.info(f"      Miners Evaluated: {len(miner_scores)}")
                bt.logging.info(f"      Average Score: {avg_score:.2f}")
                bt.logging.info(f"      Highest Score: {max_score:.2f}")
                bt.logging.info(f"      Lowest Score: {min_score:.2f}")
                bt.logging.info(f"      Score Range: {max_score - min_score:.2f}")
                
                # Show top 3 miners for this task
                top_miners = sorted(miner_scores.items(), key=lambda x: x[1], reverse=True)[:3]
                bt.logging.info(f"      🏆 Top Miners for Task {task_id}:")
                for rank, (uid, score) in enumerate(top_miners, 1):
                    breakdown = score_breakdown.get(uid, {})
                    bt.logging.info(f"         #{rank} | UID {uid:3d} | Score: {score:6.2f} | Accuracy: {breakdown.get('accuracy_score', 0):.3f} | Speed: {breakdown.get('speed_score', 0):.3f}")
            
            return miner_scores
            
        except Exception as e:
            bt.logging.error(f"❌ Error calculating task scores for task {task_id}: {str(e)}")
            import traceback
            traceback.print_exc()
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
        """
        Calculate final weights for all miners based on cumulative performance across all tasks.
        Each miner's total score is the sum of all their scores from all tasks they participated in.
        Weights are capped at 500 as per requirement.
        """
        try:
            bt.logging.info("⚖️ CALCULATING FINAL WEIGHTS FOR ALL MINERS")
            bt.logging.info("=" * 60)
            
            # CRITICAL FIX: Check if we have any miner performance data
            if not miner_performance:
                bt.logging.warning("⚠️ No miner performance data available - cannot calculate weights")
                return {}
            
            final_weights = {}
            weight_summary = {}
            
            # Calculate weights for each miner
            for miner_uid, performance in miner_performance.items():
                total_score = performance['total_score']
                task_count = performance['task_count']
                task_scores = performance.get('task_scores', {})
                
                bt.logging.info(f"🔍 Miner {miner_uid}:")
                bt.logging.info(f"   Tasks Participated: {task_count}")
                bt.logging.info(f"   Raw Total Score: {total_score:.2f}")
                
                # Show individual task scores
                if task_scores:
                    bt.logging.info(f"   Individual Task Scores:")
                    for task_id, score in sorted(task_scores.items(), key=lambda x: x[1], reverse=True):
                        bt.logging.info(f"      Task {task_id[:8]}...: {score:.2f}")
                
                # Calculate average score per task
                avg_score = total_score / task_count if task_count > 0 else 0.0
                bt.logging.info(f"   Average Score per Task: {avg_score:.2f}")
                
                # Ensure total score doesn't exceed 500 (as per requirement)
                # This is the cumulative score across all tasks
                capped_total_score = min(total_score, 500.0)
                
                # Calculate final weight based on capped total score
                # Higher total score = higher weight
                final_weight = capped_total_score
                
                final_weights[miner_uid] = final_weight
                
                # Store summary information
                weight_summary[miner_uid] = {
                    'total_score': total_score,
                    'task_count': task_count,
                    'avg_score_per_task': avg_score,
                    'capped_total_score': capped_total_score,
                    'final_weight': final_weight,
                    'was_capped': total_score > 500.0
                }
                
                bt.logging.info(f"   Capped Total Score: {capped_total_score:.2f}")
                bt.logging.info(f"   Final Weight: {final_weight:.2f}")
                if total_score > 500.0:
                    bt.logging.info(f"   ⚠️  Score was capped from {total_score:.2f} to 500.0")
                bt.logging.info("")
            
            # CRITICAL FIX: Check if we calculated any weights
            if not final_weights:
                bt.logging.warning("⚠️ No final weights calculated - returning empty dict")
                return {}
            
            # Log comprehensive weight summary
            bt.logging.info("📊 COMPREHENSIVE WEIGHT SUMMARY")
            bt.logging.info("=" * 60)
            
            # Sort miners by final weight (descending)
            sorted_miners = sorted(final_weights.items(), key=lambda x: x[1], reverse=True)
            
            max_weight = max(final_weights.values())
            min_weight = min(final_weights.values())
            avg_weight = sum(final_weights.values()) / len(final_weights)
            total_weight_sum = sum(final_weights.values())
            
            bt.logging.info(f"🏆 Top Performers:")
            for rank, (uid, weight) in enumerate(sorted_miners[:5], 1):
                summary = weight_summary.get(uid, {})
                bt.logging.info(f"   #{rank:2d} | UID {uid:3d} | Weight: {weight:6.2f} | Tasks: {summary.get('task_count', 0):2d} | Avg: {summary.get('avg_score_per_task', 0):6.2f}")
            
            if len(sorted_miners) > 5:
                bt.logging.info(f"   ... and {len(sorted_miners) - 5} more miners")
            
            bt.logging.info(f"\n📈 Weight Statistics:")
            bt.logging.info(f"   Total Miners: {len(final_weights)}")
            bt.logging.info(f"   Total Weight Sum: {total_weight_sum:.2f}")
            bt.logging.info(f"   Maximum Weight: {max_weight:.2f}")
            bt.logging.info(f"   Minimum Weight: {min_weight:.2f}")
            bt.logging.info(f"   Average Weight: {avg_weight:.2f}")
            bt.logging.info(f"   Weight Range: {max_weight - min_weight:.2f}")
            
            # Check if any miners hit the 500 cap
            capped_miners = [uid for uid, weight in final_weights.items() if weight >= 500.0]
            if capped_miners:
                bt.logging.info(f"\n🏆 Miners at Maximum Score (500): {len(capped_miners)}")
                for uid in capped_miners:
                    summary = weight_summary.get(uid, {})
                    bt.logging.info(f"   UID {uid:3d}: Raw Score {summary.get('total_score', 0):.2f} → Capped to 500.0")
            
            return final_weights
            
        except Exception as e:
            bt.logging.error(f"❌ Error calculating final weights: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}

    async def set_miner_weights(self, final_weights: Dict[int, float]):
        """Set miner weights on the blockchain"""
        try:
            bt.logging.info("🔗 Setting miner weights on blockchain...")
            
            # Check if we have any weights to set
            if not final_weights:
                bt.logging.warning("⚠️ No miner weights to set - skipping weight setting")
                return
            
            # Convert to lists for bittensor
            uids = list(final_weights.keys())
            weights = list(final_weights.values())
            
            # CRITICAL FIX: Handle division by zero and empty weights
            total_weight = sum(weights)
            if total_weight <= 0:
                bt.logging.warning(f"⚠️ Total weight is {total_weight} - cannot normalize weights")
                bt.logging.info("   Setting equal weights for all miners to prevent division by zero")
                normalized_weights = [1.0 / len(weights)] * len(weights)
            else:
                # Normalize weights to sum to 1.0
                normalized_weights = [w / total_weight for w in weights]
            
            bt.logging.info(f"📊 Weight normalization:")
            bt.logging.info(f"   Total weight: {total_weight}")
            bt.logging.info(f"   Miners with tasks: {len(uids)}")
            bt.logging.info(f"   Normalized weights: {[f'{w:.4f}' for w in normalized_weights]}")
            
            # FIXED: Only set weights for miners that actually completed tasks
            # Don't initialize scores for all miners in metagraph - only for working miners
            bt.logging.info(f"🎯 SMART WEIGHT SETTING - Only active miners get weights:")
            bt.logging.info(f"   Active miners (did tasks): {len(uids)}")
            bt.logging.info(f"   Total miners in network: {self.metagraph.n}")
            bt.logging.info(f"   Efficiency gain: Setting weights for {len(uids)} miners instead of {self.metagraph.n}")
            
            # Create weight tensor only for miners that did work
            weights_tensor = torch.zeros(self.metagraph.n, dtype=torch.float32)
            
            for i, uid in enumerate(uids):
                if uid < len(weights_tensor):
                    weights_tensor[uid] = normalized_weights[i]
                    bt.logging.info(f"   Miner {uid}: weight = {normalized_weights[i]:.4f}")
                else:
                    bt.logging.warning(f"   ⚠️ Miner UID {uid} is out of range for metagraph size {len(weights_tensor)}")
            
            # Only set weights for miners that have done work
            # All other miners will have 0 weight (default)
            bt.logging.info(f"📊 Weight Distribution Summary:")
            active_miners = sum(1 for w in weights_tensor if w > 0)
            bt.logging.info(f"   Active miners (weight > 0): {active_miners}")
            bt.logging.info(f"   Inactive miners (weight = 0): {self.metagraph.n - active_miners}")
            bt.logging.info(f"   Total miners in metagraph: {self.metagraph.n}")
            
            # Set the scores and call our custom set_weights method
            self.scores = weights_tensor.numpy()
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
        """Get the pipeline name for a given task type"""
        pipeline_map = {
            'transcription': 'TranscriptionPipeline (Whisper)',
            'tts': 'TTSPipeline (Coqui TTS)',
            'summarization': 'SummarizationPipeline (BART)'
        }
        return pipeline_map.get(task_type, f'Unknown Pipeline ({task_type})')
    
    def _get_pipeline_description(self, task_type: str) -> str:
        """Get a detailed description of the pipeline for a given task type"""
        descriptions = {
            'transcription': {
                'name': 'TranscriptionPipeline',
                'model': 'Whisper (OpenAI)',
                'capability': 'Audio to Text conversion',
                'languages': 'Multi-language support',
                'input': 'Audio data (base64 encoded)',
                'output': 'Transcribed text with confidence'
            },
            'tts': {
                'name': 'TTSPipeline',
                'model': 'Coqui TTS (Tacotron2-DDC)',
                'capability': 'Text to Speech synthesis',
                'languages': 'Multi-language support',
                'input': 'Text data',
                'output': 'Audio data with duration'
            },
            'summarization': {
                'name': 'SummarizationPipeline',
                'model': 'BART Large CNN (Facebook)',
                'capability': 'Text summarization',
                'languages': 'Multi-language support',
                'input': 'Long text data',
                'output': 'Summarized text with key points'
            }
        }
        
        desc = descriptions.get(task_type, {})
        if desc:
            return f"{desc['name']} using {desc['model']} for {desc['capability']}"
        else:
            return f"Unknown pipeline for task type: {task_type}"

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
        """Mark a task as evaluated by this validator to prevent re-evaluation"""
        try:
            bt.logging.info(f"🏷️ Marking task {task_id} as evaluated by validator...")
            
            # Add to in-memory cache
            self.evaluated_tasks_cache.add(task_id)
            
            # Update evaluation history
            current_epoch = getattr(self, 'current_epoch', 0)
            if current_epoch not in self.evaluation_history:
                self.evaluation_history[current_epoch] = {
                    'tasks_evaluated': [],
                    'evaluation_timestamp': datetime.now().isoformat(),
                    'validator_uid': getattr(self, 'uid', 'unknown'),
                    'total_tasks': 0,
                    'successful_evaluations': 0,
                    'failed_evaluations': 0
                }
            
            # Record task evaluation
            evaluation_record = {
                'task_id': task_id,
                'evaluated_at': datetime.now().isoformat(),
                'validator_uid': getattr(self, 'uid', 'unknown'),
                'task_type': validator_performance.get('task_type', 'unknown'),
                'processing_time': validator_performance.get('processing_time', 0),
                'accuracy_score': validator_performance.get('accuracy_score', 0),
                'speed_score': validator_performance.get('speed_score', 0)
            }
            
            self.evaluation_history[current_epoch]['tasks_evaluated'].append(evaluation_record)
            self.evaluation_history[current_epoch]['total_tasks'] += 1
            self.evaluation_history[current_epoch]['successful_evaluations'] += 1
            
            # Save evaluation history to disk
            self.save_evaluation_history()
            
            # Post evaluation data to proxy server
            await self.post_evaluation_data_to_proxy(task_id, validator_performance)
            
            bt.logging.info(f"✅ Task {task_id} successfully marked as evaluated")
            
        except Exception as e:
            bt.logging.error(f"❌ Error marking task {task_id} as evaluated: {str(e)}")
            # Still add to cache to prevent re-evaluation
            self.evaluated_tasks_cache.add(task_id)
    
    async def post_evaluation_data_to_proxy(self, task_id: str, validator_performance: Dict):
        """Post evaluation data to proxy server for tracking"""
        try:
            evaluation_data = {
                'task_id': task_id,
                'validator_uid': getattr(self, 'uid', 'unknown'),
                'evaluated_at': datetime.now().isoformat(),
                'evaluation_data': validator_performance
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.proxy_server_url}/api/v1/validator/evaluation",
                    json=evaluation_data,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    bt.logging.debug(f"✅ Evaluation data posted to proxy server for task {task_id}")
                else:
                    bt.logging.warning(f"⚠️  Failed to post evaluation data to proxy server: {response.status_code}")
                    
        except Exception as e:
            bt.logging.warning(f"⚠️  Could not post evaluation data to proxy server: {str(e)}")
    
    async def get_validator_evaluated_tasks(self) -> List[str]:
        """Get list of task IDs already evaluated by this validator"""
        try:
            # First check in-memory cache
            if self.evaluated_tasks_cache:
                bt.logging.debug(f"📚 Found {len(self.evaluated_tasks_cache)} tasks in memory cache")
                return list(self.evaluated_tasks_cache)
            
            # Try to get from proxy server
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.proxy_server_url}/api/v1/validator/{getattr(self, 'uid', 'unknown')}/evaluated_tasks",
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    evaluated_tasks = data.get('evaluated_tasks', [])
                    
                    # Update in-memory cache
                    self.evaluated_tasks_cache.update(evaluated_tasks)
                    
                    bt.logging.info(f"📚 Retrieved {len(evaluated_tasks)} evaluated tasks from proxy server")
                    return evaluated_tasks
                else:
                    bt.logging.warning(f"⚠️  Proxy server returned status {response.status_code} for evaluated tasks")
                    return []
                    
        except Exception as e:
            bt.logging.warning(f"⚠️  Could not retrieve evaluated tasks from proxy server: {str(e)}")
            return []
    
    async def filter_already_evaluated_tasks(self, completed_tasks: List[Dict]) -> List[Dict]:
        """Filter out tasks that have already been evaluated by this validator"""
        try:
            bt.logging.info(f"🔍 Filtering {len(completed_tasks)} completed tasks for already evaluated ones...")
            
            # Get list of already evaluated tasks
            evaluated_task_ids = await self.get_validator_evaluated_tasks()
            
            if not evaluated_task_ids:
                bt.logging.info("📋 No previously evaluated tasks found, proceeding with all tasks")
                return completed_tasks
            
            # Filter out already evaluated tasks
            new_tasks = []
            skipped_tasks = []
            
            for task in completed_tasks:
                task_id = task.get('task_id')
                if task_id and task_id not in evaluated_task_ids:
                    new_tasks.append(task)
                else:
                    skipped_tasks.append(task_id)
            
            bt.logging.info(f"📋 Filtering complete:")
            bt.logging.info(f"   Total tasks: {len(completed_tasks)}")
            bt.logging.info(f"   Already evaluated: {len(skipped_tasks)}")
            bt.logging.info(f"   New tasks for evaluation: {len(new_tasks)}")
            
            if skipped_tasks:
                bt.logging.debug(f"   Skipped task IDs: {skipped_tasks[:10]}{'...' if len(skipped_tasks) > 10 else ''}")
            
            return new_tasks
            
        except Exception as e:
            bt.logging.error(f"❌ Error filtering already evaluated tasks: {str(e)}")
            # Return all tasks if filtering fails to prevent data loss
            return completed_tasks
    
    def log_evaluation_summary(self, epoch: int, tasks_evaluated: int, miner_performance: Dict):
        """Log comprehensive evaluation summary for the current epoch"""
        try:
            bt.logging.info("=" * 80)
            bt.logging.info(f"📊 EVALUATION SUMMARY - EPOCH {epoch}")
            bt.logging.info("=" * 80)
            
            # Epoch statistics
            bt.logging.info(f"📈 Epoch Statistics:")
            bt.logging.info(f"   Epoch Number: {epoch}")
            bt.logging.info(f"   Tasks Evaluated: {tasks_evaluated}")
            bt.logging.info(f"   Miners Participating: {len(miner_performance)}")
            bt.logging.info(f"   Evaluation Timestamp: {datetime.now().isoformat()}")
            
            # Miner performance summary
            if miner_performance:
                total_scores = [perf['total_score'] for perf in miner_performance.values()]
                avg_score = sum(total_scores) / len(total_scores)
                max_score = max(total_scores)
                min_score = min(total_scores)
                
                bt.logging.info(f"\n🏆 Miner Performance Summary:")
                bt.logging.info(f"   Average Total Score: {avg_score:.2f}")
                bt.logging.info(f"   Highest Score: {max_score:.2f}")
                bt.logging.info(f"   Lowest Score: {min_score:.2f}")
                bt.logging.info(f"   Score Range: {max_score - min_score:.2f}")
                
                # Top performers
                top_miners = sorted(miner_performance.items(), key=lambda x: x[1]['total_score'], reverse=True)[:5]
                bt.logging.info(f"\n🥇 Top 5 Performers:")
                for i, (miner_uid, performance) in enumerate(top_miners, 1):
                    bt.logging.info(f"   #{i} | UID {miner_uid:3d} | Score: {performance['total_score']:6.2f} | Tasks: {performance['task_count']:2d}")
            
            # Performance metrics summary
            performance_summary = self.get_performance_summary()
            bt.logging.info(f"\n📊 Overall Performance Metrics:")
            bt.logging.info(f"   Total Operations: {performance_summary.get('total_operations', 0)}")
            bt.logging.info(f"   Success Rate: {performance_summary.get('overall_success_rate', 0):.1f}%")
            
            # Recent errors
            recent_errors = performance_summary.get('recent_errors', [])
            if recent_errors:
                bt.logging.info(f"\n⚠️  Recent Errors ({len(recent_errors)}):")
                for error in recent_errors[-3:]:  # Last 3 errors
                    bt.logging.info(f"   {error.get('timestamp', 'Unknown')}: {error.get('error', 'Unknown error')}")
            
            bt.logging.info("=" * 80)
            
        except Exception as e:
            bt.logging.error(f"❌ Error logging evaluation summary: {str(e)}")

    def save_performance_metrics(self):
        """Save current performance metrics to disk"""
        try:
            if not self.performance_metrics:
                return
            
            # Create performance summary
            performance_summary = self.get_performance_summary()
            
            # Add current timestamp and block information
            performance_summary['block'] = getattr(self, 'block', 'unknown')
            performance_summary['epoch'] = getattr(self, 'current_epoch', 0)
            performance_summary['validator_uid'] = getattr(self, 'uid', 'unknown')
            
            # Save to JSON file
            with open(self.performance_log_path, 'w') as f:
                json.dump(performance_summary, f, indent=2, default=str)
            
            bt.logging.debug("💾 Performance metrics saved to disk")
            
        except Exception as e:
            bt.logging.warning(f"⚠️  Could not save performance metrics: {str(e)}")
    
    def cleanup_old_data(self):
        """Clean up old data to prevent memory bloat"""
        try:
            # Clean up old evaluation history (keep last 10 epochs)
            if len(self.evaluation_history) > 10:
                old_epochs = sorted(self.evaluation_history.keys())[:-10]
                for old_epoch in old_epochs:
                    del self.evaluation_history[old_epoch]
                bt.logging.debug(f"🧹 Cleaned up {len(old_epochs)} old epochs from evaluation history")
            
            # Clean up old performance metrics (keep last 1000 operations per type)
            for operation, metrics in self.performance_metrics.items():
                if 'response_times' in metrics and len(metrics['response_times']) > 1000:
                    metrics['response_times'] = metrics['response_times'][-1000:]
                if 'errors' in metrics and len(metrics['errors']) > 100:
                    metrics['errors'] = metrics['errors'][-100:]
            
            # Clean up evaluated tasks cache if it gets too large
            if len(self.evaluated_tasks_cache) > 10000:
                # Keep only recent tasks (this is a simple approach)
                # In production, you might want to implement a more sophisticated LRU cache
                bt.logging.warning(f"⚠️  Evaluated tasks cache is large ({len(self.evaluated_tasks_cache)}), consider implementing LRU cache")
            
        except Exception as e:
            bt.logging.warning(f"⚠️  Error during cleanup: {str(e)}")
    
    def get_validator_status(self) -> Dict:
        """Get comprehensive validator status for monitoring"""
        try:
            status = {
                'validator_uid': getattr(self, 'uid', 'unknown'),
                'current_block': getattr(self, 'block', 'unknown'),
                'current_epoch': getattr(self, 'current_epoch', 0),
                'step': getattr(self, 'step', 0),
                'proxy_integration_enabled': self.enable_proxy_integration,
                'proxy_server_url': self.proxy_server_url,
                'evaluation_status': {
                    'last_evaluation_block': self.last_evaluation_block,
                    'blocks_since_evaluation': getattr(self, 'block', 0) - self.last_evaluation_block if hasattr(self, 'block') else 0,
                    'evaluation_interval': self.evaluation_interval,
                    'tasks_evaluated_this_epoch': len(self.evaluated_tasks_cache)
                },
                'weight_setting_status': {
                    'last_weight_setting_block': self.last_weight_setting_block,
                    'blocks_since_weight_setting': getattr(self, 'block', 0) - self.last_weight_setting_block if hasattr(self, 'block') else 0,
                    'weight_setting_interval': self.weight_setting_interval,
                    'proxy_tasks_processed_this_epoch': self.proxy_tasks_processed_this_epoch
                },
                'miner_status': {
                    'total_miners': len(self.metagraph.hotkeys) if hasattr(self, 'metagraph') else 0,
                    'reachable_miners': len(self.reachable_miners) if hasattr(self, 'reachable_miners') else 0,
                    'top_miners_by_stake': []
                },
                'performance_metrics': self.get_performance_summary(),
                'evaluation_history': {
                    'total_epochs': len(self.evaluation_history),
                    'recent_epochs': list(self.evaluation_history.keys())[-5:] if self.evaluation_history else []
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # Add top miners by stake if available
            if hasattr(self, 'reachable_miners') and self.reachable_miners:
                top_miners = sorted(self.reachable_miners, key=lambda x: self.metagraph.S[x], reverse=True)[:5]
                status['miner_status']['top_miners_by_stake'] = [
                    {'uid': uid, 'stake': float(self.metagraph.S[uid])} for uid in top_miners
                ]
            
            return status
            
        except Exception as e:
            bt.logging.error(f"❌ Error getting validator status: {str(e)}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def log_validator_status(self):
        """Log comprehensive validator status for monitoring"""
        try:
            status = self.get_validator_status()
            
            bt.logging.info("=" * 80)
            bt.logging.info("📊 VALIDATOR STATUS REPORT")
            bt.logging.info("=" * 80)
            
            # Basic info
            bt.logging.info(f"🔧 Validator Information:")
            bt.logging.info(f"   UID: {status['validator_uid']}")
            bt.logging.info(f"   Current Block: {status['current_block']}")
            bt.logging.info(f"   Current Epoch: {status['current_epoch']}")
            bt.logging.info(f"   Step: {status['step']}")
            
            # Proxy integration
            bt.logging.info(f"\n🔗 Proxy Integration:")
            bt.logging.info(f"   Enabled: {status['proxy_integration_enabled']}")
            bt.logging.info(f"   Server URL: {status['proxy_server_url']}")
            
            # Evaluation status
            eval_status = status['evaluation_status']
            bt.logging.info(f"\n🔍 Evaluation Status:")
            bt.logging.info(f"   Last Evaluation Block: {eval_status['last_evaluation_block']}")
            bt.logging.info(f"   Blocks Since Evaluation: {eval_status['blocks_since_evaluation']}")
            bt.logging.info(f"   Evaluation Interval: {eval_status['evaluation_interval']}")
            bt.logging.info(f"   Tasks Evaluated This Epoch: {eval_status['tasks_evaluated_this_epoch']}")
            
            # Weight setting status
            weight_status = status['weight_setting_status']
            bt.logging.info(f"\n⚖️  Weight Setting Status:")
            bt.logging.info(f"   Last Weight Setting Block: {weight_status['last_weight_setting_block']}")
            bt.logging.info(f"   Blocks Since Weight Setting: {weight_status['blocks_since_weight_setting']}")
            bt.logging.info(f"   Weight Setting Interval: {weight_status['weight_setting_interval']}")
            bt.logging.info(f"   Proxy Tasks Processed This Epoch: {weight_status['proxy_tasks_processed_this_epoch']}")
            
            # Miner status
            miner_status = status['miner_status']
            bt.logging.info(f"\n👥 Miner Status:")
            bt.logging.info(f"   Total Miners: {miner_status['total_miners']}")
            bt.logging.info(f"   Reachable Miners: {miner_status['reachable_miners']}")
            
            if miner_status['top_miners_by_stake']:
                bt.logging.info(f"   Top Miners by Stake:")
                for i, miner in enumerate(miner_status['top_miners_by_stake'][:3], 1):
                    bt.logging.info(f"      #{i} | UID {miner['uid']:3d} | Stake: {miner['stake']:,.0f} TAO")
            
            # Performance summary
            perf_summary = status['performance_metrics']
            bt.logging.info(f"\n📈 Performance Summary:")
            bt.logging.info(f"   Total Operations: {perf_summary.get('total_operations', 0)}")
            bt.logging.info(f"   Overall Success Rate: {perf_summary.get('overall_success_rate', 0):.1f}%")
            
            # Evaluation history
            eval_history = status['evaluation_history']
            bt.logging.info(f"\n📚 Evaluation History:")
            bt.logging.info(f"   Total Epochs: {eval_history['total_epochs']}")
            bt.logging.info(f"   Recent Epochs: {eval_history['recent_epochs']}")
            
            bt.logging.info("=" * 80)
            
        except Exception as e:
            bt.logging.error(f"❌ Error logging validator status: {str(e)}")
    
    def periodic_maintenance(self):
        """Perform periodic maintenance tasks"""
        try:
            # Save performance metrics
            self.save_performance_metrics()
            
            # Clean up old data
            self.cleanup_old_data()
            
            # Log status every 50 blocks
            if hasattr(self, 'step') and self.step % 50 == 0:
                self.log_validator_status()
            
            bt.logging.debug("🔧 Periodic maintenance completed")
            
        except Exception as e:
            bt.logging.warning(f"⚠️  Error during periodic maintenance: {str(e)}")

    def set_weights(self):
        """
        Override the base validator's set_weights method to only set weights for active miners.
        This prevents the default behavior of setting equal weights for all miners.
        """
        try:
            bt.logging.info("🎯 Setting weights ONLY for active miners...")
            
            # Check if we have scores set
            if not hasattr(self, 'scores') or self.scores is None:
                bt.logging.warning("⚠️ No scores available - skipping weight setting")
                return
            
            # Find only the UIDs with non-zero scores (active miners)
            active_uids = np.where(self.scores > 0)[0]
            active_weights = self.scores[active_uids]
            
            if len(active_uids) == 0:
                bt.logging.warning("⚠️ No active miners with scores > 0 - skipping weight setting")
                return
            
            bt.logging.info(f"📊 Setting weights for {len(active_uids)} active miners:")
            for i, uid in enumerate(active_uids):
                bt.logging.info(f"   UID {uid}: weight = {active_weights[i]:.6f}")
            
            # Normalize weights to sum to 1.0
            total_weight = np.sum(active_weights)
            if total_weight > 0:
                normalized_weights = active_weights / total_weight
            else:
                bt.logging.warning("⚠️ Total weight is 0 - cannot normalize")
                return
            
            bt.logging.info(f"📊 Normalized weights sum: {np.sum(normalized_weights):.6f}")
            
            # Convert to uint16 weights and uids for blockchain submission
            from template.base.utils.weight_utils import convert_weights_and_uids_for_emit
            
            uint_uids, uint_weights = convert_weights_and_uids_for_emit(
                uids=active_uids, 
                weights=normalized_weights
            )
            
            bt.logging.info(f"🔗 Submitting weights to blockchain for {len(uint_uids)} miners...")
            
            # Set the weights on chain via our subtensor connection
            result, msg = self.subtensor.set_weights(
                wallet=self.wallet,
                netuid=self.config.netuid,
                uids=uint_uids,
                weights=uint_weights,
                wait_for_finalization=False,
                wait_for_inclusion=False,
                version_key=self.spec_version,
            )
            
            if result is True:
                bt.logging.info("✅ Weights set on blockchain successfully!")
                bt.logging.info(f"   Active miners: {len(active_uids)}")
                bt.logging.info(f"   Total miners in network: {self.metagraph.n}")
                bt.logging.info(f"   Efficiency: {len(active_uids)}/{self.metagraph.n} miners rewarded")
            else:
                bt.logging.error(f"❌ set_weights failed: {msg}")
                
        except Exception as e:
            bt.logging.error(f"❌ Error in custom set_weights: {str(e)}")
            import traceback
            traceback.print_exc()


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
