# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

import time
import typing
import bittensor as bt
from template.base.neuron import BaseMinerNeuron
from template.protocol import AudioTask
import httpx
import asyncio


class Miner(BaseMinerNeuron):
    """
    Your miner neuron. The class name should be "Miner" and should inherit from BaseMinerNeuron.
    """

    def __init__(self, config=None):
        super(Miner, self).__init__(config=config)
        
        # Miner will query proxy server for tasks instead of running its own API server
        self.proxy_server_url = "http://localhost:8000"  # Proxy server URL
        self.last_task_query = 0
        self.task_query_interval = 10  # Query every 10 seconds
        
        bt.logging.info("Initializing audio processing pipelines...")
        
        # Initialize transcription pipeline
        try:
            from template.pipelines.transcription_pipeline import TranscriptionPipeline
            self.transcription_pipeline = TranscriptionPipeline()
            bt.logging.info("✅ Transcription pipeline initialized")
        except Exception as e:
            bt.logging.error(f"❌ Failed to initialize transcription pipeline: {e}")
            self.transcription_pipeline = None
        
        # Initialize TTS pipeline
        try:
            from template.pipelines.tts_pipeline import TTSPipeline
            self.tts_pipeline = TTSPipeline()
            bt.logging.info("✅ TTS pipeline initialized")
        except ImportError as e:
            bt.logging.warning(f"⚠️ TTS pipeline not available (TTS module not installed): {e}")
            self.tts_pipeline = None
        except Exception as e:
            bt.logging.error(f"❌ Failed to initialize TTS pipeline: {e}")
            self.tts_pipeline = None
        
        # Initialize summarization pipeline
        try:
            from template.pipelines.summarization_pipeline import SummarizationPipeline
            self.summarization_pipeline = SummarizationPipeline()
            bt.logging.info("✅ Summarization pipeline initialized")
        except Exception as e:
            bt.logging.error(f"❌ Failed to initialize summarization pipeline: {e}")
            self.summarization_pipeline = None
        
        bt.logging.info("Audio processing pipelines initialization complete!")
        
        # Log configuration
        bt.logging.info(f"Axon IP: {self.config.axon.ip}")
        bt.logging.info(f"Axon Port: {self.config.axon.port}")
        bt.logging.info(f"Axon External IP: {self.config.axon.external_ip}")
        bt.logging.info(f"Axon External Port: {self.config.axon.external_port}")
        
        # Attach forward function to miner axon
        bt.logging.info("Attaching forward function to miner axon.")
        self.axon.attach(
            forward_fn=self.forward,
            blacklist_fn=self.blacklist,
            priority_fn=self.priority,
            verify_fn=self.verify
        )
        
        bt.logging.info(f"Axon created: {self.axon}")

    async def query_proxy_for_tasks(self):
        """Query proxy server for tasks assigned to this miner"""
        try:
            # Get miner UID from Bittensor
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            
            if miner_uid == 0:
                bt.logging.debug("🔄 Miner UID not available yet, skipping task query")
                return
            
            bt.logging.info(f"🔍 Miner {miner_uid} querying proxy server for assigned tasks...")
            
            # Query proxy server for tasks assigned to this miner
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.proxy_server_url}/api/v1/miners/{miner_uid}/tasks",
                    params={"status": "assigned"}
                )
                
                if response.status_code == 200:
                    tasks = response.json()
                    if tasks and len(tasks) > 0:
                        bt.logging.info(f"🎯 Found {len(tasks)} tasks assigned to miner {miner_uid}")
                        
                        # Process each assigned task
                        for task in tasks:
                            await self.process_proxy_task(task)
                    else:
                        bt.logging.debug(f"🔄 No tasks assigned to miner {miner_uid}")
                else:
                    bt.logging.warning(f"⚠️ Failed to query tasks: {response.status_code}")
                    
        except Exception as e:
            bt.logging.warning(f"⚠️ Error querying proxy for tasks: {e}")
    
    async def process_proxy_task(self, task_data: dict):
        """Process a task received from proxy server"""
        try:
            task_id = task_data.get("task_id")
            task_type = task_data.get("task_type")
            
            # Handle both old and new schema formats
            input_file_id = None
            if "input_file_id" in task_data:
                # Old schema format
                input_file_id = task_data.get("input_file_id")
            elif "input_file" in task_data and isinstance(task_data["input_file"], dict):
                # New enhanced schema format
                input_file_id = task_data["input_file"].get("file_id")
            
            # Validate required fields
            if not task_id or not task_type or not input_file_id:
                bt.logging.error(f"❌ Missing required fields in task data: {task_data}")
                bt.logging.error(f"   Task ID: {task_id}")
                bt.logging.error(f"   Task Type: {task_type}")
                bt.logging.error(f"   Input File ID: {input_file_id}")
                bt.logging.error(f"   Available fields: {list(task_data.keys())}")
                return
            
            # Validate task type
            supported_types = ["transcription", "tts", "summarization"]
            if task_type not in supported_types:
                bt.logging.error(f"❌ Unsupported task type: {task_type}. Supported types: {supported_types}")
                return
            
            bt.logging.info(f"🎯 Processing proxy task {task_id} of type {task_type}")
            bt.logging.info(f"   Input file ID: {input_file_id}")
            bt.logging.info(f"   Task data structure: {list(task_data.keys())}")
            
            # Download input file from proxy
            input_data = await self.download_file_from_proxy(f"{self.proxy_server_url}/api/v1/files/{input_file_id}/download")
            
            if input_data is None:
                bt.logging.error(f"❌ Failed to download input file for task {task_id}")
                return
            
            # Process task using existing pipeline
            bt.logging.info(f"🔄 Routing task {task_id} to {task_type} pipeline...")
            
            # Check pipeline availability first
            if task_type == "transcription" and self.transcription_pipeline is None:
                bt.logging.error(f"❌ Transcription pipeline not available for task {task_id}")
                return
            elif task_type == "tts" and self.tts_pipeline is None:
                bt.logging.error(f"❌ TTS pipeline not available for task {task_id}")
                return
            elif task_type == "summarization" and self.summarization_pipeline is None:
                bt.logging.error(f"❌ Summarization pipeline not available for task {task_id}")
                return
            
            # Process task using appropriate pipeline
            if task_type == "transcription":
                result = await self.process_transcription_task(input_data)
            elif task_type == "tts":
                result = await self.process_tts_task(input_data)
            elif task_type == "summarization":
                result = await self.process_summarization_task(input_data)
            else:
                bt.logging.error(f"❌ Unknown task type: {task_type}")
                return
            
            bt.logging.info(f"✅ Task {task_id} processed successfully by {task_type} pipeline")
            
            # Validate result before submission
            if not result or "error" in result:
                bt.logging.error(f"❌ Task {task_id} failed to produce valid result: {result}")
                return
            
            # Submit result back to proxy
            await self.submit_result_to_proxy(f"{self.proxy_server_url}/api/v1/miner/response", task_id, result)
            
            bt.logging.info(f"✅ Task {task_id} completed and result submitted")
            
        except Exception as e:
            bt.logging.error(f"❌ Error processing proxy task: {e}")

    async def download_file_from_proxy(self, file_url: str):
        """Download input file from proxy server"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(file_url)
                response.raise_for_status()
                
                # For audio files
                if "audio" in response.headers.get("content-type", ""):
                    return response.content  # Binary audio data
                
                # For text files
                return response.text
                
        except Exception as e:
            bt.logging.error(f"❌ Failed to download file: {e}")
            return None

    async def process_transcription_task(self, audio_data: bytes):
        """Process transcription task using existing pipeline"""
        try:
            if self.transcription_pipeline is None:
                raise Exception("Transcription pipeline not available")
            
            # Process audio data
            transcribed_text, processing_time = self.transcription_pipeline.transcribe(
                audio_data, language="en"
            )
            
            return {
                "transcript": transcribed_text,
                "confidence": 0.95,  # Mock confidence score
                "processing_time": processing_time,
                "language": "en"
            }
            
        except Exception as e:
            bt.logging.error(f"❌ Error processing transcription task: {e}")
            return {
                "transcript": "",
                "confidence": 0.0,
                "processing_time": 0.0,
                "language": "en",
                "error": str(e)
            }

    async def process_tts_task(self, text_data: str):
        """Process TTS task using existing pipeline"""
        try:
            if self.tts_pipeline is None:
                raise Exception("TTS pipeline not available")
            
            # Process text data
            audio_bytes, processing_time = self.tts_pipeline.synthesize(
                text_data, language="en"
            )
            
            # Encode audio as base64
            import base64
            audio_b64 = base64.b64encode(audio_bytes).decode()
            
            return {
                "output_data": audio_b64,
                "processing_time": processing_time,
                "text_length": len(text_data)
            }
            
        except Exception as e:
            bt.logging.error(f"❌ Error processing TTS task: {e}")
            return {
                "output_data": "",
                "processing_time": 0.0,
                "error": str(e)
            }

    async def process_summarization_task(self, text_data: str):
        """Process summarization task using existing pipeline"""
        try:
            if self.summarization_pipeline is None:
                raise Exception("Summarization pipeline not available")
            
            # Process text data
            summary_text, processing_time = self.summarization_pipeline.summarize(
                text_data, language="en"
            )
            
            return {
                "summary": summary_text,
                "processing_time": processing_time,
                "text_length": len(text_data),
                "language": "en"
            }
            
        except Exception as e:
            bt.logging.error(f"❌ Error processing summarization task: {e}")
            return {
                "summary": "",
                "processing_time": 0.0,
                "text_length": 0,
                "language": "en",
                "error": str(e)
            }

    async def submit_result_to_proxy(self, callback_url: str, task_id: str, result: dict):
        """Submit processing result back to proxy server"""
        try:
            # Prepare response payload
            response_payload = {
                'task_id': task_id,
                'miner_uid': self.uid if hasattr(self, 'uid') else 0,
                'response_data': result,
                'processing_time': result.get('processing_time', 0.0),
                'accuracy_score': result.get('confidence', 0.8),  # Default accuracy
                'speed_score': await self.calculate_speed_score(result.get('processing_time', 0.0))
            }
            
            # Submit to proxy server
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Convert to Form data as expected by proxy
                form_data = {
                    'task_id': response_payload['task_id'],
                    'miner_uid': response_payload['miner_uid'],
                    'response_data': str(response_payload['response_data']),
                    'processing_time': response_payload['processing_time'],
                    'accuracy_score': response_payload['accuracy_score'],
                    'speed_score': response_payload['speed_score']
                }
                response = await client.post(callback_url, data=form_data)
                
                if response.status_code == 200:
                    bt.logging.info(f"✅ Result submitted successfully for task {task_id}")
                else:
                    bt.logging.warning(f"⚠️ Failed to submit result for task {task_id}: {response.status_code}")
                    
        except Exception as e:
            bt.logging.error(f"❌ Error submitting result: {e}")

    async def calculate_speed_score(self, processing_time: float) -> float:
        """Calculate speed score based on processing time"""
        try:
            # Baseline time for scoring (adjust as needed)
            baseline_time = 10.0  # 10 seconds baseline
            
            # Speed score: faster = higher score
            speed_score = max(0.0, min(1.0, baseline_time / processing_time))
            return speed_score
            
        except Exception as e:
            bt.logging.debug(f"⚠️ Error calculating speed score: {e}")
            return 0.5

    async def forward(
        self, synapse: AudioTask
    ) -> AudioTask:
        """
        Handle Bittensor connectivity tests and redirect real tasks to proxy system.
        
        Args:
            synapse (AudioTask): The synapse object containing the task details.

        Returns:
            AudioTask: The synapse object with the response.
        """
        
        # Query proxy server for tasks assigned to this miner
        if hasattr(self, 'uid') and self.uid > 0:
            try:
                await self.query_proxy_for_tasks()
            except Exception as e:
                bt.logging.debug(f"⚠️ Failed to query proxy for tasks: {e}")
        
        # Check if this is a connectivity test (empty input data)
        if not synapse.input_data:
            bt.logging.info("🔄 Connectivity test detected - returning empty response")
            synapse.output_data = ""
            synapse.processing_time = 0.0
            synapse.pipeline_model = "connectivity_test"
            return synapse
        
        # For proxy-based tasks, we don't process here - only handle connectivity tests
        # Real task processing happens in process_proxy_task method
        bt.logging.info("🔄 Proxy task detected - redirecting to proxy system")
        synapse.output_data = "proxy_task_redirected"
        synapse.processing_time = 0.0
        synapse.pipeline_model = "proxy_redirect"
        return synapse

    async def blacklist(
        self, synapse: AudioTask
    ) -> typing.Tuple[bool, str]:
        """
        Determines whether an incoming request should be blacklisted.
        Currently allows all connections for testing purposes.

        Args:
            synapse (AudioTask): A synapse object constructed from the headers of the incoming request.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating whether the synapse's hotkey is blacklisted,
                            and a string providing the reason for the decision.
        """
        # Allow all connections for testing
        bt.logging.debug(f"Allowing request from hotkey {synapse.dendrite.hotkey if synapse.dendrite else 'Unknown'}")
        return False, "Allowed for testing."

    async def priority(
        self, synapse: AudioTask
    ) -> float:
        """
        Determines the priority of the incoming request.
        Currently returns a default priority for testing.

        Args:
            synapse (AudioTask): The synapse object containing the task details.

        Returns:
            float: Priority score (default 1.0 for testing)
        """
        # Return default priority for testing
        return 1.0

    def verify(
        self, synapse: AudioTask
    ) -> None:
        """
        Verifies the synapse data.
        
        Args:
            synapse (AudioTask): A synapse object containing the data to verify.
        """
        # Log the incoming synapse for debugging
        bt.logging.debug(f"🔍 Verifying synapse: task_type={synapse.task_type}, language={synapse.language}, input_data_length={len(synapse.input_data) if synapse.input_data else 0}")
        
        if synapse.task_type not in ["transcription", "tts", "summarization"]:
            bt.logging.warning(f"❌ Invalid task type: {synapse.task_type}")
            raise ValueError(f"Invalid task type: {synapse.task_type}")

        # For testing/connectivity checks, allow empty input data
        if not synapse.input_data:
            bt.logging.warning("⚠️ No input data provided - allowing for connectivity test")
            # Don't raise error for empty input during testing
            return

        if not synapse.language:
            bt.logging.warning("⚠️ No language specified - using default 'en'")
            synapse.language = "en"


# This is the main function, which runs the miner.
if __name__ == "__main__":
    with Miner() as miner:
        while True:
            # Log less frequently to reduce console spam
            if int(time.time()) % 60 == 0:  # Only log every minute
                bt.logging.info(f"Miner running... {time.time()}")
            time.sleep(5)
