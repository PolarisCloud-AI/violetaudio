#!/usr/bin/env python3
"""
Bittensor Client for Audio Processing Proxy Server
Handles communication with the Bittensor network and miner evaluation
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
import bittensor as bt

from template.protocol import AudioTask
from template.validator.reward import run_validator_pipeline, calculate_accuracy_score, calculate_speed_score
from config import get_config

config = get_config()

class BittensorClient:
    """Client for interacting with the Bittensor network"""
    
    def __init__(self):
        self.wallet = None
        self.subtensor = None
        self.metagraph = None
        self.dendrite = None
        self.netuid = config.BT_NETUID
        self.network = config.BT_NETWORK
        self.wallet_name = config.BT_WALLET_NAME
        self.wallet_hotkey = config.BT_WALLET_HOTKEY
        self.initialized = False
        
    async def initialize(self) -> bool:
        """Initialize Bittensor components"""
        try:
            print(f"🚀 Initializing Bittensor client for network {self.network}, netuid {self.netuid}")
            
            # Initialize wallet
            self.wallet = bt.wallet(name=self.wallet_name, hotkey=self.wallet_hotkey)
            print(f"✅ Wallet initialized: {self.wallet_name}/{self.wallet_hotkey}")
            
            # Initialize subtensor connection
            self.subtensor = bt.subtensor(network=self.network)
            print(f"✅ Subtensor connection established to {self.network}")
            
            # Get metagraph
            self.metagraph = self.subtensor.metagraph(netuid=self.netuid)
            
            # Sync metagraph
            self.metagraph.sync(subtensor=self.subtensor)
            print(f"✅ Metagraph synced - {len(self.metagraph.hotkeys)} total miners")
            
            # Initialize dendrite
            self.dendrite = bt.dendrite(wallet=self.wallet)
            print(f"✅ Dendrite initialized")
            
            self.initialized = True
            print("🎉 Bittensor client initialization complete!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Bittensor client: {str(e)}")
            self.initialized = False
            return False
    
    def get_available_miners(self) -> List[int]:
        """Get list of available miners"""
        if not self.initialized:
            return []
        
        try:
            available_miners = []
            for uid in range(len(self.metagraph.hotkeys)):
                if self.metagraph.axons[uid].is_serving:
                    available_miners.append(uid)
            
            return available_miners
            
        except Exception as e:
            print(f"❌ Error getting available miners: {str(e)}")
            return []
    
    def get_miner_info(self, uid: int) -> Optional[Dict]:
        """Get information about a specific miner"""
        if not self.initialized or uid >= len(self.metagraph.hotkeys):
            return None
        
        try:
            axon = self.metagraph.axons[uid]
            stake = float(self.metagraph.S[uid]) if len(self.metagraph.S) > uid else 0.0
            
            return {
                "uid": uid,
                "hotkey": self.metagraph.hotkeys[uid],
                "stake": stake,
                "is_serving": axon.is_serving,
                "ip": axon.ip,
                "port": axon.port,
                "external_ip": axon.external_ip,
                "external_port": axon.external_port
            }
            
        except Exception as e:
            print(f"❌ Error getting miner info for UID {uid}: {str(e)}")
            return None
    
    async def process_task(self, task_data: Dict) -> Dict:
        """Process a task through the Bittensor network"""
        if not self.initialized:
            return {
                'success': False,
                'error_message': 'Bittensor client not initialized'
            }
        
        try:
            print(f"🎯 Processing {task_data['task_type']} task through Bittensor network")
            
            # Create AudioTask synapse
            synapse = AudioTask(
                task_type=task_data['task_type'],
                input_data=task_data['input_data'],
                language=task_data['language']
            )
            
            # Get available miners
            available_miners = self.get_available_miners()
            if not available_miners:
                return {
                    'success': False,
                    'error_message': 'No available miners found'
                }
            
            print(f"🎯 Found {len(available_miners)} available miners")
            
            # Select top miners (limit for efficiency)
            top_miners = available_miners[:config.MAX_MINERS_PER_REQUEST]
            axons = [self.metagraph.axons[uid] for uid in top_miners]
            
            print(f"🎯 Querying {len(top_miners)} miners: {top_miners}")
            
            # Send request to miners
            start_time = time.time()
            responses = await self.dendrite(
                axons=axons,
                synapse=synapse,
                deserialize=False,
                timeout=config.TASK_TIMEOUT
            )
            
            total_time = time.time() - start_time
            print(f"⏱️  Total communication time: {total_time:.2f}s")
            
            # Process responses and find best result
            best_response = await self._evaluate_responses(
                responses, top_miners, task_data, total_time
            )
            
            if best_response:
                return {
                    'success': True,
                    **best_response
                }
            else:
                return {
                    'success': False,
                    'error_message': 'No valid responses from miners'
                }
                
        except Exception as e:
            error_msg = f'Bittensor processing error: {str(e)}'
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error_message': error_msg
            }
    
    async def _evaluate_responses(
        self, 
        responses: List, 
        miner_uids: List[int], 
        task_data: Dict, 
        total_time: float
    ) -> Optional[Dict]:
        """Evaluate miner responses and find the best one"""
        try:
            best_response = None
            best_score = 0
            
            print(f"🔍 Evaluating {len(responses)} miner responses...")
            
            for i, response in enumerate(responses):
                if not response:
                    print(f"⚠️  No response from miner {miner_uids[i]}")
                    continue
                
                if not hasattr(response, 'output_data') or not response.output_data:
                    print(f"⚠️  No output data from miner {miner_uids[i]}")
                    continue
                
                print(f"🔍 Processing response from miner {miner_uids[i]}")
                
                # Extract response data
                processing_time = getattr(response, 'processing_time', total_time)
                model_used = getattr(response, 'pipeline_model', 'unknown')
                error_msg = getattr(response, 'error_message', None)
                
                if error_msg:
                    print(f"⚠️  Miner {miner_uids[i]} reported error: {error_msg}")
                    continue
                
                # Run validator pipeline for comparison
                print(f"🔬 Running validator pipeline for comparison...")
                validator_output, validator_time, validator_model = run_validator_pipeline(
                    task_data['task_type'],
                    task_data['input_data'],
                    task_data['language']
                )
                
                if not validator_output:
                    print(f"⚠️  Validator pipeline failed for miner {miner_uids[i]}")
                    continue
                
                # Calculate scores
                scores = await self._calculate_response_scores(
                    response, validator_output, task_data, processing_time, synapse
                )
                
                if scores:
                    accuracy, speed_score, combined_score = scores
                    
                    print(f"📊 Miner {miner_uids[i]} scores - Accuracy: {accuracy:.4f}, Speed: {speed_score:.4f}, Combined: {combined_score:.4f}")
                    
                    if combined_score > best_score:
                        best_score = combined_score
                        best_response = {
                            'output_data': response.output_data,
                            'processing_time': processing_time,
                            'pipeline_model': model_used,
                            'accuracy_score': accuracy,
                            'speed_score': speed_score,
                            'combined_score': combined_score,
                            'miner_uid': miner_uids[i],
                            'validator_time': validator_time,
                            'validator_model': validator_model
                        }
                        
                        print(f"🏆 New best response from miner {miner_uids[i]} with score {combined_score:.4f}")
                else:
                    print(f"⚠️  Could not calculate scores for miner {miner_uids[i]}")
            
            if best_response:
                print(f"🎉 Best response selected from miner {best_response['miner_uid']} with score {best_response['combined_score']:.4f}")
            else:
                print("❌ No valid responses found")
            
            return best_response
            
        except Exception as e:
            print(f"❌ Error evaluating responses: {str(e)}")
            return None
    
    async def _calculate_response_scores(
        self, 
        response: AudioTask, 
        validator_output: str, 
        task_data: Dict, 
        processing_time: float,
        synapse: AudioTask
    ) -> Optional[Tuple[float, float, float]]:
        """Calculate accuracy and speed scores for a response"""
        try:
            # Decode response for comparison
            if task_data['task_type'] == 'transcription':
                response_text = synapse.decode_text(response.output_data)
                expected_text = synapse.decode_text(validator_output)
                accuracy = calculate_accuracy_score(response_text, expected_text, 'transcription')
                
                print(f"📝 Response: '{response_text[:100]}...'")
                print(f"📝 Expected: '{expected_text[:100]}...'")
                
            elif task_data['task_type'] == 'summarization':
                response_text = synapse.decode_text(response.output_data)
                expected_text = synapse.decode_text(validator_output)
                accuracy = calculate_accuracy_score(response_text, expected_text, 'summarization')
                
            elif task_data['task_type'] == 'tts':
                # For TTS, we'll use a placeholder accuracy since audio comparison is complex
                accuracy = 0.8  # Placeholder score
                
            else:
                accuracy = 0.0
            
            # Calculate speed score
            speed_score = calculate_speed_score(processing_time)
            
            # Calculate combined score using configured weights
            combined_score = (accuracy * config.ACCURACY_WEIGHT) + (speed_score * config.SPEED_WEIGHT)
            
            return accuracy, speed_score, combined_score
            
        except Exception as e:
            print(f"❌ Error calculating scores: {str(e)}")
            return None
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics"""
        if not self.initialized:
            return {}
        
        try:
            stats = {
                "network": self.network,
                "netuid": self.netuid,
                "total_miners": len(self.metagraph.hotkeys),
                "available_miners": len(self.get_available_miners()),
                "total_stake": float(self.metagraph.S.sum()) if len(self.metagraph.S) > 0 else 0.0,
                "metagraph_synced": True,
                "wallet_connected": self.wallet is not None,
                "timestamp": time.time()
            }
            return stats
            
        except Exception as e:
            print(f"❌ Error getting network stats: {str(e)}")
            return {}
    
    def health_check(self) -> bool:
        """Check if the Bittensor client is healthy"""
        try:
            if not self.initialized:
                return False
            
            # Test basic connectivity
            if not self.subtensor or not self.metagraph or not self.dendrite:
                return False
            
            # Test metagraph sync
            self.metagraph.sync(subtensor=self.subtensor)
            
            return True
            
        except Exception as e:
            print(f"❌ Bittensor client health check failed: {str(e)}")
            return False
    
    async def close(self):
        """Clean up resources"""
        try:
            if self.subtensor:
                self.subtensor.close()
            self.initialized = False
            print("🔌 Bittensor client closed")
        except Exception as e:
            print(f"❌ Error closing Bittensor client: {str(e)}")

# Global Bittensor client instance
bittensor_client = BittensorClient()
