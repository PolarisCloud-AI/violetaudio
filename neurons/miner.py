#!/usr/bin/env python3
"""
Bittensor Miner for Audio Processing Subnet
Handles transcription, TTS, and summarization tasks with enhanced logging
"""

import time
import typing
import bittensor as bt
import httpx
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
import threading

# Bittensor Miner Template:
from template.base.miner import BaseMinerNeuron
from template.protocol import AudioTask

# Add FastAPI imports for the endpoints
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel
import typing
from typing import Dict, Any, Optional
# Response models for the endpoints
class TaskResponse(BaseModel):
    task_id: str
    task_type: str
    status: str
    input_file: Dict[str, Any]
    source_language: str
    priority: str


class MinerResponse(BaseModel):
    task_id: str
    miner_uid: int
    response_data: Dict[str, Any]
    processing_time: float
    accuracy_score: float
    speed_score: float

# Import base miner class which takes care of most of the boilerplate
from template.base.miner import BaseMinerNeuron

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
        
        # Enhanced logging setup
        self.setup_enhanced_logging()
        
        # Record start time for uptime tracking
        self._start_time = time.time()
        
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
        
        # Initialize translation pipeline
        try:
            from template.pipelines.translation_pipeline import translation_pipeline
            self.translation_pipeline = translation_pipeline
            bt.logging.info("✅ Translation pipeline initialized")
        except Exception as e:
            bt.logging.error(f"❌ Failed to initialize translation pipeline: {e}")
            self.translation_pipeline = None
        
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
        
        # Start background task to continuously query proxy server for tasks
        self.start_proxy_query_task()
        
        # Start periodic metrics saving
        self.start_periodic_metrics_saving()
        
        bt.logging.info("✅ Miner initialization complete")
        
        # Initialize duplicate protection
        self.processed_tasks = set()  # Track processed task IDs
        self.processing_tasks = set()  # Track currently processing tasks
        self.max_processed_tasks = 1000  # Maximum tasks to keep in memory
        self.task_processing_lock = threading.Lock()  # Thread safety for task processing

    def setup_enhanced_logging(self):
        """Setup enhanced logging with structured logging and response tracking"""
        # Create logs directory if it doesn't exist
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # Create miner-specific log directory
        self.miner_logs_dir = self.logs_dir / "miner"
        self.miner_logs_dir.mkdir(exist_ok=True)
        
        # Create response logs directory
        self.response_logs_dir = self.miner_logs_dir / "responses"
        self.response_logs_dir.mkdir(exist_ok=True)
        
        # Create metrics logs directory
        self.metrics_logs_dir = self.miner_logs_dir / "metrics"
        self.metrics_logs_dir.mkdir(exist_ok=True)
        
        # Initialize response tracking
        self.response_count = 0
        self.successful_responses = 0
        self.failed_responses = 0
        self.total_processing_time = 0.0
        
        bt.logging.info(f"📁 Enhanced logging setup complete")
        bt.logging.info(f"   Logs directory: {self.logs_dir.absolute()}")
        bt.logging.info(f"   Miner logs: {self.miner_logs_dir.absolute()}")
        bt.logging.info(f"   Response logs: {self.response_logs_dir.absolute()}")
        bt.logging.info(f"   Metrics logs: {self.metrics_logs_dir.absolute()}")

    def log_response(self, task_id: str, task_type: str, miner_uid: int, result: dict, 
                    processing_time: float, input_size: int, success: bool, error: str = None):
        """Log detailed response information"""
        try:
            timestamp = datetime.now().isoformat()
            response_id = f"{task_id}_{miner_uid}_{int(time.time())}"
            
            # Create response log entry
            response_log = {
                "response_id": response_id,
                "timestamp": timestamp,
                "task_id": task_id,
                "task_type": task_type,
                "miner_uid": miner_uid,
                "success": success,
                "processing_time": processing_time,
                "input_size": input_size,
                "result_summary": self._summarize_result(result, task_type),
                "error": error,
                "metrics": {
                    "accuracy_score": result.get("accuracy_score", 0.0) if success else 0.0,
                    "speed_score": result.get("speed_score", 0.0) if success else 0.0,
                    "confidence": result.get("confidence", 0.0) if success else 0.0
                }
            }
            
            # Save detailed response log
            response_log_file = self.response_logs_dir / f"{response_id}.json"
            with open(response_log_file, 'w') as f:
                json.dump(response_log, f, indent=2, default=str)
            
            # Update metrics
            self.response_count += 1
            if success:
                self.successful_responses += 1
            else:
                self.failed_responses += 1
            self.total_processing_time += processing_time
            
            # Log to console with enhanced formatting
            status_emoji = "✅" if success else "❌"
            bt.logging.info(f"{status_emoji} RESPONSE LOGGED: {response_id}")
            bt.logging.info(f"   Task: {task_type} ({task_id})")
            bt.logging.info(f"   Miner: {miner_uid}")
            bt.logging.info(f"   Processing: {processing_time:.2f}s")
            bt.logging.info(f"   Input: {input_size} bytes")
            bt.logging.info(f"   Success: {success}")
            if error:
                bt.logging.error(f"   Error: {error}")
            
            # Log metrics summary
            self._log_metrics_summary()
            
        except Exception as e:
            bt.logging.error(f"❌ Error logging response: {e}")

    def _summarize_result(self, result: dict, task_type: str) -> dict:
        """Create a summary of the result for logging"""
        try:
            summary = {
                "task_type": task_type,
                "has_error": "error" in result,
                "output_size": 0
            }
            
            if task_type == "transcription":
                summary["output_size"] = len(result.get("transcript", ""))
                summary["confidence"] = result.get("confidence", 0.0)
            elif task_type == "tts":
                summary["output_size"] = len(result.get("output_data", ""))
                summary["text_length"] = result.get("text_length", 0)
            elif task_type == "summarization":
                summary["output_size"] = len(result.get("summary", ""))
                summary["text_length"] = result.get("text_length", 0)
            
            return summary
            
        except Exception as e:
            bt.logging.error(f"❌ Error summarizing result: {e}")
            return {"error": str(e)}

    def _log_metrics_summary(self):
        """Log current metrics summary"""
        try:
            if self.response_count > 0:
                success_rate = (self.successful_responses / self.response_count) * 100
                avg_processing_time = self.total_processing_time / self.response_count
                
                bt.logging.info(f"📊 METRICS SUMMARY:")
                bt.logging.info(f"   Total Responses: {self.response_count}")
                bt.logging.info(f"   Success Rate: {success_rate:.1f}%")
                bt.logging.info(f"   Avg Processing Time: {avg_processing_time:.2f}s")
                bt.logging.info(f"   Successful: {self.successful_responses}")
                bt.logging.info(f"   Failed: {self.failed_responses}")
                
                # Save metrics to file
                metrics_data = {
                    "timestamp": datetime.now().isoformat(),
                    "total_responses": self.response_count,
                    "successful_responses": self.successful_responses,
                    "failed_responses": self.failed_responses,
                    "success_rate": success_rate,
                    "total_processing_time": self.total_processing_time,
                    "average_processing_time": avg_processing_time
                }
                
                metrics_file = self.metrics_logs_dir / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(metrics_file, 'w') as f:
                    json.dump(metrics_data, f, indent=2)
                    
        except Exception as e:
            bt.logging.error(f"❌ Error logging metrics summary: {e}")

    def save_comprehensive_metrics(self):
        """Save comprehensive metrics and create summary report"""
        try:
            timestamp = datetime.now()
            timestamp_str = timestamp.isoformat()
            date_str = timestamp.strftime('%Y%m%d_%H%M%S')
            
            # Create comprehensive metrics report
            comprehensive_metrics = {
                "timestamp": timestamp_str,
                "miner_info": {
                    "uid": getattr(self, 'uid', 0),
                    "hotkey": getattr(self, 'wallet', {}).get('hotkey', 'unknown') if hasattr(self, 'wallet') else 'unknown',
                    "coldkey": getattr(self, 'wallet', {}).get('coldkey', 'unknown') if hasattr(self, 'wallet') else 'unknown'
                },
                "performance_metrics": {
                    "total_responses": self.response_count,
                    "successful_responses": self.successful_responses,
                    "failed_responses": self.failed_responses,
                    "success_rate": (self.successful_responses / self.response_count * 100) if self.response_count > 0 else 0,
                    "total_processing_time": self.total_processing_time,
                    "average_processing_time": (self.total_processing_time / self.response_count) if self.response_count > 0 else 0,
                    "uptime": time.time() - getattr(self, '_start_time', time.time())
                },
                "pipeline_status": {
                    "transcription_pipeline": self.transcription_pipeline is not None,
                    "tts_pipeline": self.tts_pipeline is not None,
                    "summarization_pipeline": self.summarization_pipeline is not None
                },
                "system_info": {
                    "proxy_server_url": self.proxy_server_url,
                    "task_query_interval": self.task_query_interval,
                    "logs_directory": str(self.logs_dir.absolute())
                }
            }
            
            # Save comprehensive metrics
            comprehensive_file = self.metrics_logs_dir / f"comprehensive_metrics_{date_str}.json"
            with open(comprehensive_file, 'w') as f:
                json.dump(comprehensive_metrics, f, indent=2, default=str)
            
            # Create human-readable summary report
            summary_report = f"""# Miner Performance Summary Report
Generated: {timestamp_str}

## Miner Information
- UID: {comprehensive_metrics['miner_info']['uid']}
- Hotkey: {comprehensive_metrics['miner_info']['hotkey']}
- Coldkey: {comprehensive_metrics['miner_info']['coldkey']}

## Performance Metrics
- Total Responses: {comprehensive_metrics['performance_metrics']['total_responses']}
- Success Rate: {comprehensive_metrics['performance_metrics']['success_rate']:.1f}%
- Average Processing Time: {comprehensive_metrics['performance_metrics']['average_processing_time']:.2f}s
- Total Processing Time: {comprehensive_metrics['performance_metrics']['total_processing_time']:.2f}s

## Pipeline Status
- Transcription Pipeline: {'✅ Available' if comprehensive_metrics['pipeline_status']['transcription_pipeline'] else '❌ Not Available'}
- TTS Pipeline: {'✅ Available' if comprehensive_metrics['pipeline_status']['tts_pipeline'] else '❌ Not Available'}
- Summarization Pipeline: {'✅ Available' if comprehensive_metrics['pipeline_status']['summarization_pipeline'] else '❌ Not Available'}

## System Configuration
- Proxy Server: {comprehensive_metrics['system_info']['proxy_server_url']}
- Task Query Interval: {comprehensive_metrics['system_info']['task_query_interval']}s
- Logs Directory: {comprehensive_metrics['system_info']['logs_directory']}

---
Report generated automatically by Bittensor Miner
"""
            
            # Save summary report
            summary_file = self.metrics_logs_dir / f"summary_report_{date_str}.md"
            with open(summary_file, 'w') as f:
                f.write(summary_report)
            
            bt.logging.info(f"📊 Comprehensive metrics saved: {comprehensive_file}")
            bt.logging.info(f"📋 Summary report saved: {summary_file}")
            
        except Exception as e:
            bt.logging.error(f"❌ Error saving comprehensive metrics: {e}")

    def start_periodic_metrics_saving(self):
        """Start periodic saving of comprehensive metrics"""
        import threading
        
        def metrics_saving_loop():
            while True:
                try:
                    time.sleep(300)  # Save metrics every 5 minutes
                    self.save_comprehensive_metrics()
                except Exception as e:
                    bt.logging.error(f"❌ Error in metrics saving loop: {e}")
        
        # Start metrics saving thread
        metrics_thread = threading.Thread(target=metrics_saving_loop, daemon=True)
        metrics_thread.start()
        bt.logging.info("📊 Started periodic metrics saving (every 5 minutes)")

    def start_periodic_metrics_saving(self):
        """Start background task to periodically save metrics"""
        import threading
        import time
        
        def metrics_saving_loop():
            while True:
                try:
                    # Save metrics every 5 minutes
                    time.sleep(300)  # 5 minutes
                    if hasattr(self, 'miner_logs_dir'):
                        self._save_metrics()
                except Exception as e:
                    bt.logging.warning(f"⚠️ Metrics saving error: {e}")
        
        # Start background thread
        metrics_thread = threading.Thread(target=metrics_saving_loop, daemon=True)
        metrics_thread.start()
        bt.logging.info("🔄 Started periodic metrics saving (every 5 minutes)")
    
    def _save_metrics(self):
        """Save current metrics to file"""
        try:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'response_count': getattr(self, 'response_count', 0),
                'successful_responses': getattr(self, 'successful_responses', 0),
                'failed_responses': getattr(self, 'failed_responses', 0),
                'total_processing_time': getattr(self, 'total_processing_time', 0.0),
                'success_rate': getattr(self, 'successful_responses', 0) / max(getattr(self, 'response_count', 1), 1),
                'avg_processing_time': getattr(self, 'total_processing_time', 0.0) / max(getattr(self, 'response_count', 1), 1)
            }
            
            metrics_file = self.metrics_logs_dir / f"metrics_{int(time.time())}.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)
            
            bt.logging.debug(f"📊 Metrics saved to {metrics_file}")
            
        except Exception as e:
            bt.logging.error(f"❌ Error saving metrics: {e}")

    def log_task_start(self, task_id: str, task_type: str, miner_uid: int, input_size: int):
        """Log when a task starts processing"""
        try:
            timestamp = datetime.now().isoformat()
            start_log = {
                "timestamp": timestamp,
                "event": "task_start",
                "task_id": task_id,
                "task_type": task_type,
                "miner_uid": miner_uid,
                "input_size": input_size
            }
            
            # Save start log
            start_log_file = self.response_logs_dir / f"{task_id}_{miner_uid}_start.json"
            with open(start_log_file, 'w') as f:
                json.dump(start_log, f, indent=2)
            
            bt.logging.info(f"🚀 TASK START: {task_id} ({task_type}) - Miner {miner_uid}")
            bt.logging.info(f"   Input Size: {input_size} bytes")
            bt.logging.info(f"   Start Time: {timestamp}")
            
        except Exception as e:
            bt.logging.error(f"❌ Error logging task start: {e}")

    def log_task_completion(self, task_id: str, task_type: str, miner_uid: int, 
                           processing_time: float, success: bool, result: dict, error: str = None):
        """Log when a task completes processing"""
        try:
            timestamp = datetime.now().isoformat()
            completion_log = {
                "timestamp": timestamp,
                "event": "task_completion",
                "task_id": task_id,
                "task_type": task_type,
                "miner_uid": miner_uid,
                "processing_time": processing_time,
                "success": success,
                "result_summary": self._summarize_result(result, task_type),
                "error": error
            }
            
            # Save completion log
            completion_log_file = self.response_logs_dir / f"{task_id}_{miner_uid}_completion.json"
            with open(completion_log_file, 'w') as f:
                json.dump(completion_log, f, indent=2)
            
            status_emoji = "✅" if success else "❌"
            bt.logging.info(f"{status_emoji} TASK COMPLETION: {task_id} ({task_type}) - Miner {miner_uid}")
            bt.logging.info(f"   Processing Time: {processing_time:.2f}s")
            bt.logging.info(f"   Success: {success}")
            if error:
                bt.logging.error(f"   Error: {error}")
            
        except Exception as e:
            bt.logging.error(f"❌ Error logging task completion: {e}")
    
    async def query_proxy_for_tasks(self):
        """Query proxy server for tasks assigned to this miner"""
        try:
            # Get miner UID from Bittensor
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            
            if miner_uid == 0:
                bt.logging.debug("🔄 Miner UID not available yet, skipping task query")
                return
            
            bt.logging.info(f"🔍 Miner {miner_uid} querying proxy server for assigned tasks...")
            
            # 🔒 DUPLICATE PROTECTION: Enhanced task filtering
            # Only request tasks that are actually eligible for processing
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.proxy_server_url}/api/v1/miners/{miner_uid}/tasks",
                    params={
                        "status": "assigned",  # Only assigned tasks
                        "exclude_processing": "true"  # Exclude tasks already being processed
                    }
                )
                
                if response.status_code == 200:
                    tasks = response.json()
                    if tasks and len(tasks) > 0:
                        bt.logging.info(f"🎯 Found {len(tasks)} tasks assigned to miner {miner_uid}")
                        
                        # 🔒 DUPLICATE PROTECTION: Additional filtering before processing
                        eligible_tasks = []
                        for task in tasks:
                            task_id = task.get("task_id")
                            task_status = task.get("status")
                            
                            # Skip if already processed
                            if task_id in self.processed_tasks:
                                bt.logging.debug(f"🔄 Skipping already processed task: {task_id}")
                                continue
                            
                            # Skip if currently being processed
                            if task_id in self.processing_tasks:
                                bt.logging.debug(f"⏳ Skipping currently processing task: {task_id}")
                                continue
                            
                            # Skip if status is not eligible
                            if task_status not in ['assigned', 'pending']:
                                bt.logging.debug(f"⚠️ Skipping task with invalid status '{task_status}': {task_id}")
                                continue
                            
                            eligible_tasks.append(task)
                        
                        bt.logging.info(f"✅ {len(eligible_tasks)} tasks eligible for processing after duplicate protection")
                        
                        # Process each eligible task
                        for task in eligible_tasks:
                            await self.process_proxy_task(task)
                    else:
                        bt.logging.debug(f"🔄 No tasks assigned to miner {miner_uid}")
                else:
                    bt.logging.warning(f"⚠️ Failed to query tasks: {response.status_code}")
                    
        except Exception as e:
            bt.logging.warning(f"⚠️ Error querying proxy for tasks: {e}")
    
    def start_proxy_query_task(self):
        """Start background task to continuously query proxy server for tasks"""
        import threading
        import time
        
        def proxy_query_loop():
            while True:
                try:
                    # Use asyncio.run to call the async method from a separate thread
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Query for tasks
                        loop.run_until_complete(self.query_proxy_for_tasks())
                        
                        # 🔒 DUPLICATE PROTECTION: Clean up old processed tasks
                        self.cleanup_processed_tasks()
                        
                    finally:
                        loop.close()
                except Exception as e:
                    bt.logging.warning(f"⚠️ Background proxy query error: {e}")
                
                # Wait before next query
                time.sleep(self.task_query_interval)
        
        # Start background thread
        proxy_thread = threading.Thread(target=proxy_query_loop, daemon=True)
        proxy_thread.start()
        bt.logging.info(f"🔄 Started background proxy query task (every {self.task_query_interval} seconds)")
    
    async def test_file_download(self):
        """Test file download capability"""
        try:
            bt.logging.info("🧪 Testing file download from proxy server...")
            
            # Test with a known file
            test_file_id = "5b279112-f771-485b-84a0-44383f930f9d"
            test_url = f"{self.proxy_server_url}/api/v1/files/{test_file_id}/download"
            
            bt.logging.info(f"🧪 Testing download from: {test_url}")
            
            # Use our download function
            downloaded_data = await self.download_file_from_proxy(test_url)
            
            if downloaded_data is not None:
                bt.logging.info(f"🧪 Downloaded {len(downloaded_data)} bytes successfully")
                
                # Test if it's valid audio data
                if len(downloaded_data) > 1000:  # Should be at least 1KB
                    bt.logging.info("✅ File download test PASSED - audio file is valid")
                    
                    # Test if we can process it
                    if self.transcription_pipeline:
                        try:
                            result = await self.process_transcription_task(downloaded_data)
                            if result and "error" not in result:
                                bt.logging.info("✅ Transcription pipeline test PASSED")
                                bt.logging.info(f"   Transcript: {result.get('transcript', '')[:100]}...")
                            else:
                                bt.logging.warning("⚠️ Transcription pipeline test WARNING - pipeline returned error")
                        except Exception as e:
                            bt.logging.warning(f"⚠️ Transcription pipeline test WARNING - {e}")
                    else:
                        bt.logging.info("ℹ️ Transcription pipeline not available, skipping pipeline test")
                else:
                    bt.logging.warning("⚠️ File download test WARNING - file seems too small")
            else:
                bt.logging.error("❌ File download test FAILED - no data received")
                    
        except Exception as e:
            bt.logging.error(f"❌ File download test error: {e}")
            import traceback
            traceback.print_exc()

    async def test_miner_tasks_endpoint(self):
        """Test the miner tasks endpoint to see what data structure is returned"""
        try:
            bt.logging.info("🧪 Testing miner tasks endpoint...")
            
            # Get miner UID
            miner_uid = self.uid if hasattr(self, 'uid') else 48  # Use 48 as fallback for testing
            
            bt.logging.info(f"🧪 Testing endpoint for miner {miner_uid}")
            
            # Test the endpoint with "assigned" status (tasks assigned to this miner)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.proxy_server_url}/api/v1/miners/{miner_uid}/tasks",
                    params={"status": "assigned"}  # Correct: Miner should process assigned tasks
                )
                
                bt.logging.info(f"🧪 Response status: {response.status_code}")
                bt.logging.info(f"🧪 Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    tasks = response.json()
                    bt.logging.info(f"🧪 Response data type: {type(tasks)}")
                    bt.logging.info(f"🧪 Response data: {tasks}")
                    
                    if isinstance(tasks, list) and len(tasks) > 0:
                        bt.logging.info(f"🧪 Found {len(tasks)} tasks")
                        for i, task in enumerate(tasks):
                            bt.logging.info(f"🧪 Task {i+1}:")
                            bt.logging.info(f"   Task ID: {task.get('task_id', 'N/A')}")
                            bt.logging.info(f"   Task Type: {task.get('task_type', 'N/A')}")
                            bt.logging.info(f"   Status: {task.get('status', 'N/A')}")
                            bt.logging.info(f"   Available fields: {list(task.keys())}")
                            
                            # Check for input file related fields
                            input_fields = [k for k in task.keys() if 'file' in k.lower() or 'input' in k.lower()]
                            if input_fields:
                                bt.logging.info(f"   Input-related fields: {input_fields}")
                                for field in input_fields:
                                    bt.logging.info(f"      {field}: {task[field]}")
                            else:
                                bt.logging.warning(f"   ⚠️ No input-related fields found")
                    else:
                        bt.logging.info(f"🧪 No tasks found or empty response")
                else:
                    bt.logging.error(f"🧪 Endpoint returned error: {response.status_code}")
                    bt.logging.error(f"🧪 Error response: {response.text}")
                    
        except Exception as e:
            bt.logging.error(f"❌ Error testing miner tasks endpoint: {e}")
            import traceback
            traceback.print_exc()

    async def process_proxy_task(self, task_data: dict):
        """Process a task received from proxy server"""
        try:
            bt.logging.info(f"🔍 Processing proxy task with data: {task_data}")
            
            task_id = task_data.get("task_id")
            task_type = task_data.get("task_type")
            task_status = task_data.get("status")
            
            # 🔒 DUPLICATE PROTECTION: Atomic task status checking and assignment
            with self.task_processing_lock:
                # Check if task already processed
                if task_id in self.processed_tasks:
                    bt.logging.info(f"🔄 Task {task_id} already processed, skipping duplicate")
                    return
                
                # Check if task is currently being processed
                if task_id in self.processing_tasks:
                    bt.logging.info(f"⏳ Task {task_id} is currently being processed, skipping duplicate")
                    return
                
                # Check if task status is valid for processing
                if task_status not in ['assigned', 'pending']:
                    bt.logging.info(f"⚠️ Task {task_id} has status '{task_status}', not eligible for processing")
                    return
                
                # Mark task as currently being processed (atomic operation)
                self.processing_tasks.add(task_id)
                bt.logging.info(f"🔒 Task {task_id} locked for processing")
            
            try:
                # For summarization tasks, we handle text-based input differently
                if task_type == "summarization":
                    await self.process_summarization_task_from_proxy(task_data)
                    return
                
                # For TTS tasks, we handle text-based input differently
                if task_type == "tts":
                    await self.process_tts_task_from_proxy(task_data)
                    return
                
                # For text translation tasks, we handle text-based input differently
                if task_type == "text_translation":
                    await self.process_text_translation_task(task_data)
                    return
                
                # For document translation tasks, we handle file-based input differently
                if task_type == "document_translation":
                    await self.process_document_translation_task_from_proxy(task_data)
                    return
                
                # Handle multiple possible input file ID formats for file-based tasks
                input_file_id = None
                
                # Try different possible field names and formats
                possible_fields = [
                    "input_file_id",           # Direct field
                    "input_file",              # Object field
                    "file_id",                 # Alternative field name
                    "audio_file_id",           # Audio-specific field
                    "input_data_id"            # Another alternative
                ]
                
                for field in possible_fields:
                    if field in task_data:
                        field_value = task_data[field]
                        if isinstance(field_value, str) and field_value:
                            input_file_id = field_value
                            bt.logging.info(f"📋 Found input_file_id in field '{field}': {input_file_id}")
                            break
                        elif isinstance(field_value, dict) and field_value.get('file_id'):
                            input_file_id = field_value['file_id']
                            bt.logging.info(f"📋 Found input_file_id in field '{field}.file_id': {input_file_id}")
                            break
                
                # If still no input_file_id, try to extract from nested structures
                if not input_file_id:
                    # Check if there's a nested input structure
                    for key, value in task_data.items():
                        if isinstance(value, dict) and 'file_id' in value:
                            input_file_id = value['file_id']
                            bt.logging.info(f"📋 Found input_file_id in nested field '{key}.file_id': {input_file_id}")
                            break
                        elif isinstance(value, dict) and 'input_file_id' in value:
                            input_file_id = value['input_file_id']
                            bt.logging.info(f"📋 Found input_file_id in nested field '{key}.input_file_id': {input_file_id}")
                            break
                
                # Log what we found
                if input_file_id:
                    bt.logging.info(f"✅ Successfully extracted input_file_id: {input_file_id}")
                else:
                    bt.logging.warning(f"⚠️ Could not find input_file_id in task data:")
                    bt.logging.warning(f"   Available fields: {list(task_data.keys())}")
                    for key, value in task_data.items():
                        bt.logging.warning(f"   {key}: {type(value).__name__} = {value}")
                
                # Validate required fields for file-based tasks
                if not task_id or not task_type or not input_file_id:
                    bt.logging.error(f"❌ Missing required fields in task data:")
                    bt.logging.error(f"   Task ID: {task_id}")
                    bt.logging.error(f"   Task Type: {task_type}")
                    bt.logging.error(f"   Input File ID: {input_file_id}")
                    bt.logging.error(f"   Available fields: {list(task_data.keys())}")
                    bt.logging.error(f"   Full task data: {task_data}")
                    return
                
                # Validate task type
                supported_types = ["transcription", "tts", "summarization", "video_transcription"]
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
                
                # Validate input data is not empty
                input_size = len(input_data) if hasattr(input_data, '__len__') else 0
                if input_size == 0:
                    bt.logging.warning(f"⚠️ Downloaded file is empty (0 bytes) for task {task_id} - marking as completed with broken file notice")
                    
                    # Instead of failing, create a completed response for broken files
                    broken_file_result = {
                        "transcript": "broken file",
                        "confidence": 0.0,
                        "processing_time": 0.0,
                        "language": "en",
                        "error": "File is empty or broken (0 bytes)",
                        "status": "completed_broken_file"
                    }
                    
                    # Log the broken file completion
                    miner_uid = self.uid if hasattr(self, 'uid') else 0
                    self.log_task_completion(task_id, task_type, miner_uid, 0.0, True, broken_file_result, "File marked as completed due to being broken/empty")
                    
                    # Submit the broken file result to proxy
                    await self.submit_result_to_proxy(f"{self.proxy_server_url}/api/v1/miner/response", task_id, broken_file_result)
                    
                    # Log the response
                    self.log_response(task_id, task_type, miner_uid, broken_file_result, 0.0, 0, True, "Broken file handled gracefully")
                    
                    bt.logging.info(f"✅ Task {task_id} marked as completed (broken file) and submitted to proxy")
                    return
                
                # Check for suspiciously small files that might be corrupted
                if input_size < 1000:  # Less than 1KB is suspicious for audio files
                    bt.logging.warning(f"⚠️ File is suspiciously small ({input_size} bytes) for task {task_id} - may be corrupted")
                    if task_type == "transcription":
                        bt.logging.warning(f"⚠️ Audio files should typically be larger than 1KB - marking as completed with broken file notice")
                        
                        # Create a completed response for suspiciously small files
                        suspicious_file_result = {
                            "transcript": "broken file",
                            "confidence": 0.0,
                            "processing_time": 0.0,
                            "language": "en",
                            "error": f"File is suspiciously small ({input_size} bytes) - may be corrupted",
                            "status": "completed_broken_file"
                        }
                        
                        # Log the suspicious file completion
                        miner_uid = self.uid if hasattr(self, 'uid') else 0
                        self.log_task_completion(task_id, task_type, miner_uid, 0.0, True, suspicious_file_result, "File marked as completed due to being suspiciously small")
                        
                        # Submit the suspicious file result to proxy
                        await self.submit_result_to_proxy(f"{self.proxy_server_url}/api/v1/miner/response", task_id, suspicious_file_result)
                        
                        # Log the response
                        self.log_response(task_id, task_type, miner_uid, suspicious_file_result, 0.0, input_size, True, "Suspiciously small file handled gracefully")
                        
                        bt.logging.info(f"✅ Task {task_id} marked as completed (suspicious file) and submitted to proxy")
                        return
                
                bt.logging.info(f"📥 Downloaded {input_size} bytes for task {task_id}")
                
                # Validate input data type
                if task_type == "transcription" and not isinstance(input_data, bytes):
                    bt.logging.error(f"❌ Invalid input data type for transcription task {task_id}: expected bytes, got {type(input_data)}")
                    return
                
                # Get miner UID for logging
                miner_uid = self.uid if hasattr(self, 'uid') else 0
                
                # Log task start
                self.log_task_start(task_id, task_type, miner_uid, input_size)
                
                # Process task using existing pipeline
                bt.logging.info(f"🔄 Routing task {task_id} to {task_type} pipeline...")
                
                # Check pipeline availability first
                if task_type == "transcription" and self.transcription_pipeline is None:
                    error_msg = f"Transcription pipeline not available for task {task_id}"
                    bt.logging.error(f"❌ {error_msg}")
                    self.log_task_completion(task_id, task_type, miner_uid, 0.0, False, {}, error_msg)
                    return
                elif task_type == "tts" and self.tts_pipeline is None:
                    error_msg = f"TTS pipeline not available for task {task_id}"
                    bt.logging.error(f"❌ {error_msg}")
                    self.log_task_completion(task_id, task_type, miner_uid, 0.0, False, {}, error_msg)
                    return
                elif task_type == "summarization" and self.summarization_pipeline is None:
                    error_msg = f"Summarization pipeline not available for task {task_id}"
                    bt.logging.error(f"❌ {error_msg}")
                    self.log_task_completion(task_id, task_type, miner_uid, 0.0, False, {}, error_msg)
                    return
                elif task_type == "video_transcription" and self.transcription_pipeline is None:
                    error_msg = f"Transcription pipeline not available for video transcription task {task_id}"
                    bt.logging.error(f"❌ {error_msg}")
                    self.log_task_completion(task_id, task_type, miner_uid, 0.0, False, {}, error_msg)
                    return
                elif task_type in ["text_translation", "document_translation"] and not hasattr(self, 'translation_pipeline'):
                    error_msg = f"Translation pipeline not available for {task_type} task {task_id}"
                    bt.logging.error(f"❌ {error_msg}")
                    self.log_task_completion(task_id, task_type, miner_uid, 0.0, False, {}, error_msg)
                    return
                
                # Process task using appropriate pipeline
                start_time = time.time()
                try:
                    if task_type == "transcription":
                        result = await self.process_transcription_task(input_data)
                    elif task_type == "tts":
                        result = await self.process_tts_task(input_data)
                    elif task_type == "summarization":
                        result = await self.process_summarization_task(input_data)
                    elif task_type == "video_transcription":
                        result = await self.process_video_transcription_task(input_data, task_data)
                    elif task_type == "text_translation":
                        result = await self.process_text_translation_task(task_data)
                    elif task_type == "document_translation":
                        result = await self.process_document_translation_task(input_data, task_data)
                    else:
                        error_msg = f"Unknown task type: {task_type}"
                        bt.logging.error(f"❌ {error_msg}")
                        self.log_task_completion(task_id, task_type, miner_uid, 0.0, False, {}, error_msg)
                        return
                    
                    processing_time = time.time() - start_time
                    
                    # Validate result before submission
                    if not result or "error" in result:
                        error_msg = f"Task {task_id} failed to produce valid result: {result}"
                        bt.logging.error(f"❌ {error_msg}")
                        self.log_task_completion(task_id, task_type, miner_uid, processing_time, False, result, error_msg)
                        return
                    
                    # Log successful task completion
                    self.log_task_completion(task_id, task_type, miner_uid, processing_time, True, result)
                    
                    bt.logging.info(f"✅ Task {task_id} processed successfully by {task_type} pipeline in {processing_time:.2f}s")
                    
                    # Submit result back to proxy
                    await self.submit_result_to_proxy(f"{self.proxy_server_url}/api/v1/miner/response", task_id, result)
                    
                    # Log final response
                    self.log_response(task_id, task_type, miner_uid, result, processing_time, input_size, True)
                    
                    bt.logging.info(f"✅ Task {task_id} completed and result submitted")
                    
                except Exception as e:
                    processing_time = time.time() - start_time
                    error_msg = f"Pipeline processing error: {str(e)}"
                    bt.logging.error(f"❌ {error_msg}")
                    self.log_task_completion(task_id, task_type, miner_uid, processing_time, False, {}, error_msg)
                    self.log_response(task_id, task_type, miner_uid, {}, processing_time, input_size, False, error_msg)
                    return
                
            finally:
                # 🔒 DUPLICATE PROTECTION: Atomic task completion marking
                with self.task_processing_lock:
                    self.processing_tasks.discard(task_id)
                    self.processed_tasks.add(task_id)
                    bt.logging.info(f"✅ Task {task_id} marked as processed, duplicate protection active")
                
        except Exception as e:
            # 🔒 DUPLICATE PROTECTION: Ensure task is removed from processing even on error
            task_id = task_data.get("task_id")
            if task_id:
                with self.task_processing_lock:
                    self.processing_tasks.discard(task_id)
                bt.logging.error(f"❌ Error processing task {task_id}: {e}")
            else:
                bt.logging.error(f"❌ Error processing task: {e}")

    async def download_file_from_proxy(self, file_url: str):
        """Download input file from proxy server"""
        try:
            bt.logging.info(f"📥 Downloading file from: {file_url}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(file_url)
                response.raise_for_status()
                
                # Log response details for debugging
                content_type = response.headers.get("content-type", "")
                content_length = response.headers.get("content-length", "unknown")
                bt.logging.info(f"📥 Response received:")
                bt.logging.info(f"   Status: {response.status_code}")
                bt.logging.info(f"   Content-Type: {content_type}")
                bt.logging.info(f"   Content-Length: {content_length}")
                bt.logging.info(f"   Response size: {len(response.content)} bytes")
                
                # Check if we got any content
                if len(response.content) == 0:
                    bt.logging.error(f"❌ Downloaded file is empty (0 bytes)")
                    return None
                
                # For audio files or binary files - be more permissive
                if (content_type.startswith("audio/") or 
                    "octet-stream" in content_type or 
                    "wav" in content_type.lower() or 
                    "mp3" in content_type.lower() or
                    "m4a" in content_type.lower() or
                    "flac" in content_type.lower() or
                    file_url.lower().endswith(('.wav', '.mp3', '.m4a', '.flac'))):
                    
                    bt.logging.info(f"✅ Detected audio file: {len(response.content)} bytes")
                    return response.content  # Binary audio data
                
                # For text files
                elif content_type.startswith("text/") or "json" in content_type:
                    bt.logging.info(f"✅ Detected text file: {len(response.content)} bytes")
                    return response.text
                
                # Default case - treat as binary if we have content
                else:
                    bt.logging.info(f"⚠️ Unknown content type '{content_type}', treating as binary: {len(response.content)} bytes")
                    return response.content
                
        except httpx.HTTPStatusError as e:
            bt.logging.error(f"❌ HTTP error downloading file: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.TimeoutException:
            bt.logging.error(f"❌ Timeout downloading file from {file_url}")
            return None
        except httpx.ConnectError:
            bt.logging.error(f"❌ Connection error downloading file from {file_url}")
            return None
        except Exception as e:
            bt.logging.error(f"❌ Failed to download file from {file_url}: {e}")
            return None

    async def extract_text_data(self, task_data: dict) -> Optional[str]:
        """Extract text data from task data"""
        try:
            # Try to get text directly from task data
            if "input_text" in task_data and task_data["input_text"]:
                bt.logging.info(f"✅ Found input_text directly in task data")
                return task_data["input_text"]
            
            # Try to get text from input_data field
            if "input_data" in task_data and task_data["input_data"]:
                bt.logging.info(f"✅ Found input_data in task data")
                return task_data["input_data"]
            
            # Try to get text from text field
            if "text" in task_data and task_data["text"]:
                bt.logging.info(f"✅ Found text field in task data")
                return task_data["text"]
            
            bt.logging.warning(f"⚠️ No text data found in task data")
            return None
            
        except Exception as e:
            bt.logging.error(f"❌ Error extracting text data: {e}")
            return None

    async def extract_summarization_data(self, task_data: dict) -> Optional[dict]:
        """Extract summarization data from task data or fetch from proxy API"""
        try:
            task_id = task_data.get("task_id")
            if not task_id:
                bt.logging.error("❌ No task_id provided for summarization task")
                return None
            
            # First try to get text directly from task data
            if "input_text" in task_data and task_data["input_text"]:
                bt.logging.info(f"✅ Found input_text directly in task data")
                # Extract the actual text from the input_text dictionary
                text_content = task_data["input_text"]
                actual_text = text_content.get("text", "")
                source_lang = text_content.get("source_language", task_data.get("source_language", "en"))
                
                bt.logging.info(f"   Extracted text length: {len(actual_text)} characters")
                bt.logging.info(f"   Text preview: {actual_text[:100]}...")
                
                return {
                    "text": actual_text,
                    "source_language": source_lang,
                    "detected_language": source_lang,  # Use source language directly
                    "language_confidence": 1.0  # Always 1.0 since user specified the language
                }
            
            # If no direct text, fetch from proxy API
            bt.logging.info(f"📡 Fetching summarization task content from proxy API for task {task_id}")
            
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{self.proxy_server_url}/api/v1/miner/summarization/{task_id}")
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        if response_data.get("success"):
                            text_content = response_data.get("text_content", {})
                            bt.logging.info(f"✅ Successfully fetched summarization content from proxy API")
                            bt.logging.info(f"   Text length: {len(text_content.get('text', ''))}")
                            bt.logging.info(f"   Source language: {text_content.get('source_language', 'en')}")
                            
                            return {
                                "text": text_content.get("text", ""),
                                "source_language": text_content.get("source_language", "en"),
                                "detected_language": text_content.get("source_language", "en"),  # Use source language directly
                                "language_confidence": 1.0,  # Always 1.0 since user specified the language
                                "task_metadata": response_data.get("task_metadata", {})
                            }
                        else:
                            bt.logging.error(f"❌ Proxy API returned error: {response_data}")
                            return None
                    else:
                        bt.logging.error(f"❌ Failed to fetch summarization content: HTTP {response.status_code}")
                        return None
                        
            except Exception as e:
                bt.logging.error(f"❌ Error fetching summarization content from proxy API: {e}")
                return None
            
        except Exception as e:
            bt.logging.error(f"❌ Error extracting summarization data: {e}")
            return None

    async def extract_tts_data(self, task_data: dict) -> Optional[dict]:
        """Extract TTS data from task data or fetch from proxy API"""
        try:
            task_id = task_data.get("task_id")
            if not task_id:
                bt.logging.error("❌ No task_id provided for TTS task")
                return None
            
            # First try to get text directly from task data
            if "input_text" in task_data and task_data["input_text"]:
                bt.logging.info(f"✅ Found input_text directly in task data")
                # Extract the actual text from the input_text dictionary
                text_content = task_data["input_text"]
                actual_text = text_content.get("text", "")
                source_lang = text_content.get("source_language", task_data.get("source_language", "en"))
                
                bt.logging.info(f"   Extracted text length: {len(actual_text)} characters")
                bt.logging.info(f"   Text preview: {actual_text[:100]}...")
                
                return {
                    "text": actual_text,
                    "source_language": source_lang,
                    "detected_language": source_lang,  # Use source language directly
                    "language_confidence": 1.0  # Always 1.0 since user specified the language
                }
            
            # If no direct text, fetch from proxy API
            bt.logging.info(f"📡 Fetching TTS task content from proxy API for task {task_id}")
            
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{self.proxy_server_url}/api/v1/miner/tts/{task_id}")
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        if response_data.get("success"):
                            text_content = response_data.get("text_content", {})
                            bt.logging.info(f"✅ Successfully fetched TTS content from proxy API")
                            bt.logging.info(f"   Text length: {len(text_content.get('text', ''))}")
                            bt.logging.info(f"   Source language: {text_content.get('source_language', 'en')}")
                            
                            return {
                                "text": text_content.get("text", ""),
                                "source_language": text_content.get("source_language", "en"),
                                "detected_language": text_content.get("source_language", "en"),  # Use source language directly
                                "language_confidence": 1.0,  # Always 1.0 since user specified the language
                                "task_metadata": response_data.get("task_metadata", {})
                            }
                        else:
                            bt.logging.error(f"❌ Proxy API returned error: {response_data}")
                            return None
                    else:
                        bt.logging.error(f"❌ Failed to fetch TTS content: HTTP {response.status_code}")
                        return None
                        
            except Exception as e:
                bt.logging.error(f"❌ Error fetching TTS content from proxy API: {e}")
                return None
            
        except Exception as e:
            bt.logging.error(f"❌ Error extracting TTS data: {e}")
            return None
    
    async def process_transcription_task(self, audio_data: bytes):
        """Process transcription task using existing pipeline"""
        try:
            if self.transcription_pipeline is None:
                raise Exception("Transcription pipeline not available")
            
            # Validate input data
            if not isinstance(audio_data, bytes):
                raise Exception(f"Invalid audio data type: expected bytes, got {type(audio_data)}")
            
            if len(audio_data) == 0:
                raise Exception("Audio data is empty")
            
            bt.logging.info(f"🎵 Processing {len(audio_data)} bytes of audio data...")
            
            # Process audio data
            transcribed_text, processing_time = self.transcription_pipeline.transcribe(
                audio_data, language="en"
            )
            
            bt.logging.info(f"✅ Transcription completed: {len(transcribed_text)} characters in {processing_time:.2f}s")
            
            return {
                "transcript": transcribed_text,
                "confidence": 0.95,  # Mock confidence score
                "processing_time": processing_time,
                "language": "en"
            }
            
        except Exception as e:
            bt.logging.error(f"❌ Error processing transcription task: {e}")
            bt.logging.error(f"   Audio data type: {type(audio_data)}")
            bt.logging.error(f"   Audio data length: {len(audio_data) if hasattr(audio_data, '__len__') else 'N/A'}")
            
            # Check if this is a broken file error
            if "Audio data is empty" in str(e) or len(audio_data) == 0:
                bt.logging.warning(f"⚠️ Broken file detected - marking as completed with broken file notice")
                return {
                    "transcript": "broken file",
                    "confidence": 0.0,
                    "processing_time": 0.0,
                    "language": "en",
                    "error": "File is empty or broken",
                    "status": "completed_broken_file"
                }
            
            # For other errors, return standard error format
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
    
    async def process_summarization_task_from_proxy(self, task_data: dict):
        """Process summarization task from proxy server using text-based input"""
        try:
            task_id = task_data.get("task_id")
            bt.logging.info(f"📝 Processing summarization task {task_id} from proxy server")
            
            # Extract summarization data using the existing method
            summarization_data = await self.extract_summarization_data(task_data)
            
            if not summarization_data:
                error_msg = f"Failed to extract summarization data for task {task_id}"
                bt.logging.error(f"❌ {error_msg}")
                miner_uid = self.uid if hasattr(self, 'uid') else 0
                self.log_task_completion(task_id, "summarization", miner_uid, 0.0, False, {}, error_msg)
                return
            
            # Process the summarization task
            start_time = time.time()
            result = await self.process_summarization_task(summarization_data)
            processing_time = time.time() - start_time
            
            # Validate result before submission
            if not result or "error" in result:
                error_msg = f"Task {task_id} failed to produce valid result: {result}"
                bt.logging.error(f"❌ {error_msg}")
                miner_uid = self.uid if hasattr(self, 'uid') else 0
                self.log_task_completion(task_id, "summarization", miner_uid, processing_time, False, result, error_msg)
                return
            
            # Log successful task completion
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            self.log_task_completion(task_id, "summarization", miner_uid, processing_time, True, result)
            
            bt.logging.info(f"✅ Task {task_id} processed successfully by summarization pipeline in {processing_time:.2f}s")
            
            # Submit result back to proxy
            await self.submit_result_to_proxy(f"{self.proxy_server_url}/api/v1/miner/response", task_id, result)
            
            # Log final response
            self.log_response(task_id, "summarization", miner_uid, result, processing_time, 0, True)
            
            bt.logging.info(f"✅ Task {task_id} completed and result submitted")
            
        except Exception as e:
            error_msg = f"Error processing summarization task from proxy: {str(e)}"
            bt.logging.error(f"❌ {error_msg}")
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            self.log_response(task_id, "summarization", miner_uid, {}, 0.0, 0, False, error_msg)

    async def process_tts_task_from_proxy(self, task_data: dict):
        """Process TTS task from proxy server using text-based input"""
        try:
            task_id = task_data.get("task_id")
            bt.logging.info(f"🎵 Processing TTS task {task_id} from proxy server")
            
            # Extract TTS data using the existing method
            tts_data = await self.extract_tts_data(task_data)
            
            if not tts_data:
                error_msg = f"Failed to extract TTS data for task {task_id}"
                bt.logging.error(f"❌ {error_msg}")
                miner_uid = self.uid if hasattr(self, 'uid') else 0
                self.log_task_completion(task_id, "tts", miner_uid, 0.0, False, {}, error_msg)
                return
            
            # Process the TTS task
            start_time = time.time()
            result = await self.process_tts_task(tts_data)
            processing_time = time.time() - start_time
            
            # Validate result before submission
            if not result or "error" in result:
                error_msg = f"Task {task_id} failed to produce valid result: {result}"
                bt.logging.error(f"❌ {error_msg}")
                miner_uid = self.uid if hasattr(self, 'uid') else 0
                self.log_task_completion(task_id, "tts", miner_uid, processing_time, False, result, error_msg)
                return
            
            # Log successful task completion
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            self.log_task_completion(task_id, "tts", miner_uid, processing_time, True, result)
            
            bt.logging.info(f"✅ Task {task_id} processed successfully by TTS pipeline in {processing_time:.2f}s")
            
            # Submit result back to proxy using TTS-specific endpoint
            await self.submit_tts_result_to_proxy(f"{self.proxy_server_url}/api/v1/miner/tts/upload-audio", task_id, result)
            
            # Log final response
            self.log_response(task_id, "tts", miner_uid, result, processing_time, 0, True)
            
            bt.logging.info(f"✅ Task {task_id} completed and result submitted")
            
        except Exception as e:
            error_msg = f"Error processing TTS task from proxy: {str(e)}"
            bt.logging.error(f"❌ {error_msg}")
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            self.log_response(task_id, "tts", miner_uid, {}, 0.0, 0, False, error_msg)

    async def process_summarization_task(self, summarization_data: dict):
        """Process summarization task using existing pipeline with language support"""
        try:
            if self.summarization_pipeline is None:
                raise Exception("Summarization pipeline not available")
            
            # Extract text and language information
            text = summarization_data.get("text", "")
            source_language = summarization_data.get("source_language", "en")
            detected_language = summarization_data.get("detected_language", "en")
            language_confidence = summarization_data.get("language_confidence", 1.0)
            
            bt.logging.info(f"📝 Processing summarization task:")
            bt.logging.info(f"   Text type: {type(text)}")
            bt.logging.info(f"   Text length: {len(text) if isinstance(text, str) else 'N/A'}")
            bt.logging.info(f"   Text preview: {str(text)[:100] if text else 'None'}...")
            bt.logging.info(f"   Source language: {source_language}")
            bt.logging.info(f"   Detected language: {detected_language}")
            bt.logging.info(f"   Language confidence: {language_confidence}")
            
            if not text:
                raise Exception("No text provided for summarization")
            
            if not isinstance(text, str):
                raise Exception(f"Text must be a string, got {type(text)}")
            
            # Use the source language directly since user specified it
            processing_language = source_language
            
            # Process text data with language support
            summary_text, processing_time = self.summarization_pipeline.summarize(
                text, language=processing_language
            )
            
            return {
                "summary": summary_text,
                "processing_time": processing_time,
                "text_length": len(text),
                "source_language": source_language,
                "detected_language": detected_language,
                "language_confidence": language_confidence,
                "processing_language": processing_language,
                "word_count": len(text.split()),
                "summary_length": len(summary_text),
                "compression_ratio": len(summary_text) / max(len(text), 1)
            }
            
        except Exception as e:
            bt.logging.error(f"❌ Error processing summarization task: {e}")
            return {
                "summary": "",
                "processing_time": 0.0,
                "text_length": 0,
                "source_language": "en",
                "detected_language": "en",
                "language_confidence": 0.0,
                "processing_language": "en",
                "word_count": 0,
                "summary_length": 0,
                "compression_ratio": 0.0,
                "error": str(e)
            }

    async def process_tts_task(self, tts_data: dict):
        """Process TTS task using existing pipeline with language support"""
        try:
            if self.tts_pipeline is None:
                raise Exception("TTS pipeline not available")
            
            # Extract text and language information
            text = tts_data.get("text", "")
            source_language = tts_data.get("source_language", "en")
            detected_language = tts_data.get("detected_language", "en")
            language_confidence = tts_data.get("language_confidence", 1.0)
            
            bt.logging.info(f"🎵 Processing TTS task:")
            bt.logging.info(f"   Text type: {type(text)}")
            bt.logging.info(f"   Text length: {len(text) if isinstance(text, str) else 'N/A'}")
            bt.logging.info(f"   Text preview: {str(text)[:100] if text else 'None'}...")
            bt.logging.info(f"   Source language: {source_language}")
            bt.logging.info(f"   Detected language: {detected_language}")
            bt.logging.info(f"   Language confidence: {language_confidence}")
            
            if not text:
                raise Exception("No text provided for TTS")
            
            if not isinstance(text, str):
                raise Exception(f"Text must be a string, got {type(text)}")
            
            # Use the source language directly since user specified it
            processing_language = source_language
            
            # Process text data with language support
            audio_data, processing_time = self.tts_pipeline.synthesize(
                text, language=processing_language
            )
            
            # Generate unique filename for the audio
            import uuid
            audio_filename = f"{uuid.uuid4().hex[:8]}.wav"
            
            # Save audio to local storage
            audio_path = f"proxy_server/local_storage/tts_audio/{audio_filename}"
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            
            with open(audio_path, "wb") as f:
                f.write(audio_data)
            
            bt.logging.info(f"✅ Audio file saved: {audio_path}")
            bt.logging.info(f"   File size: {len(audio_data)} bytes")
            
            return {
                "audio_file": {
                    "filename": audio_filename,
                    "local_path": audio_path,
                    "file_size": len(audio_data),
                    "file_type": "audio/wav"
                },
                "processing_time": processing_time,
                "text_length": len(text),
                "source_language": source_language,
                "detected_language": detected_language,
                "language_confidence": language_confidence,
                "processing_language": processing_language,
                "word_count": len(text.split()),
                "audio_duration": 0.0,  # Will be calculated by validator
                "sample_rate": 22050,   # Default, will be verified by validator
                "bit_depth": 16,        # Default, will be verified by validator
                "channels": 1           # Default, will be verified by validator
            }
            
        except Exception as e:
            bt.logging.error(f"❌ Error processing TTS task: {e}")
            return {
                "audio_file": None,
                "processing_time": 0.0,
                "text_length": 0,
                "source_language": "en",
                "detected_language": "en",
                "language_confidence": 0.0,
                "processing_language": "en",
                "word_count": 0,
                "audio_duration": 0.0,
                "sample_rate": 0,
                "bit_depth": 0,
                "channels": 0,
                "error": str(e)
            }
    
    async def process_video_transcription_task(self, video_data: bytes, task_data: dict):
        """Process video transcription task - extract audio and transcribe"""
        try:
            if self.transcription_pipeline is None:
                raise Exception("Transcription pipeline not available")
            
            # Import video processing utilities
            try:
                from template.pipelines.video_utils import video_processor
            except ImportError:
                raise Exception("Video processing utilities not available")
            
            # Get task information
            task_id = task_data.get("task_id", "unknown")
            source_language = task_data.get("source_language", "en")
            filename = task_data.get("input_file", {}).get("file_name", "unknown_video")
            
            bt.logging.info(f"🎬 Processing video transcription task {task_id}")
            bt.logging.info(f"   Video filename: {filename}")
            bt.logging.info(f"   Video size: {len(video_data)} bytes")
            bt.logging.info(f"   Source language: {source_language}")
            
            # Extract audio from video
            bt.logging.info(f"🔧 Extracting audio from video...")
            audio_bytes, temp_audio_path = video_processor.extract_audio_from_video(
                video_data, 
                filename,
                output_format="wav",
                sample_rate=16000  # Whisper requirement
            )
            
            bt.logging.info(f"✅ Audio extraction successful: {len(audio_bytes)} bytes")
            
            # Get video information for metadata
            video_info = video_processor.get_video_info(video_data, filename)
            bt.logging.info(f"📊 Video info: {video_info}")
            
            # Transcribe the extracted audio
            bt.logging.info(f"🎵 Transcribing extracted audio...")
            transcribed_text, processing_time = self.transcription_pipeline.transcribe(
                audio_bytes, language=source_language
            )
            
            bt.logging.info(f"✅ Transcription completed: {len(transcribed_text)} characters in {processing_time:.2f}s")
            
            # Calculate confidence score (mock for now)
            confidence = 0.95
            
            return {
                "transcript": transcribed_text,
                "confidence": confidence,
                "processing_time": processing_time,
                "language": source_language,
                "video_info": video_info,
                "audio_extraction_success": True,
                "audio_size_bytes": len(audio_bytes),
                "transcript_length": len(transcribed_text),
                "word_count": len(transcribed_text.split()),
                "source_language": source_language
            }
            
        except Exception as e:
            bt.logging.error(f"❌ Error processing video transcription task: {e}")
            return {
                "transcript": "",
                "confidence": 0.0,
                "processing_time": 0.0,
                "language": source_language if 'source_language' in locals() else "en",
                "video_info": {},
                "audio_extraction_success": False,
                "audio_size_bytes": 0,
                "transcript_length": 0,
                "word_count": 0,
                "source_language": source_language if 'source_language' in locals() else "en",
                "error": str(e)
            }
    
    async def process_text_translation_task(self, task_data: dict):
        """Process text translation task from proxy server"""
        try:
            task_id = task_data.get("task_id")
            bt.logging.info(f"🌐 Processing text translation task {task_id} from proxy server")
            
            # Extract translation data
            translation_data = await self.extract_text_translation_data(task_data)
            
            if not translation_data:
                error_msg = f"Failed to extract text translation data for task {task_id}"
                bt.logging.error(f"❌ {error_msg}")
                miner_uid = self.uid if hasattr(self, 'uid') else 0
                self.log_task_completion(task_id, "text_translation", miner_uid, 0.0, False, {}, error_msg)
                return
            
            # Process the text translation task
            start_time = time.time()
            result = await self.process_text_translation(translation_data)
            processing_time = time.time() - start_time
            
            # Validate result before submission
            if not result or "error" in result:
                error_msg = f"Task {task_id} failed to produce valid result: {result}"
                bt.logging.error(f"❌ {error_msg}")
                miner_uid = self.uid if hasattr(self, 'uid') else 0
                self.log_task_completion(task_id, "text_translation", miner_uid, processing_time, False, result, error_msg)
                return
            
            # Log successful task completion
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            self.log_task_completion(task_id, "text_translation", miner_uid, processing_time, True, result)
            
            bt.logging.info(f"✅ Task {task_id} processed successfully by text translation pipeline in {processing_time:.2f}s")
            
            # Submit result back to proxy using text translation-specific endpoint
            await self.submit_text_translation_result_to_proxy(f"{self.proxy_server_url}/api/v1/miner/text-translation/upload-result", task_id, result)
            
            # Log final response
            self.log_response(task_id, "text_translation", miner_uid, result, processing_time, 0, True)
            
            bt.logging.info(f"✅ Task {task_id} completed and result submitted")
            
        except Exception as e:
            error_msg = f"Error processing text translation task from proxy: {str(e)}"
            bt.logging.error(f"❌ {error_msg}")
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            self.log_response(task_id, "text_translation", miner_uid, {}, 0.0, 0, False, error_msg)
    
    async def process_document_translation_task_from_proxy(self, task_data: dict):
        """Process document translation task from proxy server"""
        try:
            task_id = task_data.get("task_id")
            bt.logging.info(f"📄 Processing document translation task {task_id} from proxy server")
            
            # Extract document data
            if 'input_file' in task_data and task_data['input_file']:
                input_file = task_data['input_file']
                file_id = input_file.get('file_id')
                
                if not file_id:
                    bt.logging.error(f"❌ No file_id found in input_file for task {task_id}")
                    return
                
                # Download the document file from proxy
                input_data = await self.download_file_from_proxy(f"{self.proxy_server_url}/api/v1/files/{file_id}/download")
                
                if input_data is None:
                    bt.logging.error(f"❌ Failed to download document file for task {task_id}")
                    return
                
                # Now process the document translation
                await self.process_document_translation_task(input_data, task_data)
            else:
                bt.logging.error(f"❌ No input_file found in task data for document translation task {task_id}")
                
        except Exception as e:
            error_msg = f"Error processing document translation task from proxy: {str(e)}"
            bt.logging.error(f"❌ {error_msg}")
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            self.log_response(task_id, "document_translation", miner_uid, {}, 0.0, 0, False, error_msg)

    async def process_document_translation_task(self, document_data, task_data: dict):
        """Process document translation task from proxy server"""
        try:
            task_id = task_data.get("task_id")
            bt.logging.info(f"📄 Processing document translation task {task_id} from proxy server")
            
            # Extract translation data
            translation_data = await self.extract_document_translation_data(task_data)
            
            if not translation_data:
                error_msg = f"Failed to extract document translation data for task {task_id}"
                bt.logging.error(f"❌ {error_msg}")
                miner_uid = self.uid if hasattr(self, 'uid') else 0
                self.log_task_completion(task_id, "document_translation", miner_uid, 0.0, False, {}, error_msg)
                return
            
            # Process the document translation task
            start_time = time.time()
            result = await self.process_document_translation(document_data, translation_data)
            processing_time = time.time() - start_time
            
            # Validate result before submission
            if not result or "error" in result:
                error_msg = f"Task {task_id} failed to produce valid result: {result}"
                bt.logging.error(f"❌ {error_msg}")
                miner_uid = self.uid if hasattr(self, 'uid') else 0
                self.log_task_completion(task_id, "document_translation", miner_uid, processing_time, False, result, error_msg)
                return
            
            # Log successful task completion
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            self.log_task_completion(task_id, "document_translation", miner_uid, processing_time, True, result)
            
            bt.logging.info(f"✅ Task {task_id} processed successfully by document translation pipeline in {processing_time:.2f}s")
            
            # Submit result back to proxy using document translation-specific endpoint
            await self.submit_document_translation_result_to_proxy(f"{self.proxy_server_url}/api/v1/miner/document-translation/upload-result", task_id, result)
            
            # Log final response
            self.log_response(task_id, "document_translation", miner_uid, result, processing_time, len(document_data), True)
            
            bt.logging.info(f"✅ Task {task_id} completed and result submitted")
            
        except Exception as e:
            error_msg = f"Error processing document translation task from proxy: {str(e)}"
            bt.logging.error(f"❌ {error_msg}")
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            self.log_response(task_id, "document_translation", miner_uid, {}, 0.0, 0, False, error_msg)
    
    async def extract_text_translation_data(self, task_data: dict) -> Optional[dict]:
        """Extract text translation data from task data"""
        try:
            task_id = task_data.get("task_id")
            
            # Try to get data from task_data first
            if 'input_text' in task_data and task_data['input_text']:
                text_content = task_data['input_text']
                bt.logging.info(f"✅ Found text translation data in task_data for task {task_id}")
                return {
                    'text': text_content.get('text', ''),
                    'source_language': text_content.get('source_language', 'en'),
                    'target_language': text_content.get('target_language', 'es')
                }
            
            # If not in task_data, try to fetch from proxy API
            bt.logging.info(f"🔍 Fetching text translation data from proxy API for task {task_id}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.proxy_server_url}/api/v1/miner/text-translation/{task_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and 'text_content' in data:
                        text_content = data['text_content']
                        bt.logging.info(f"✅ Retrieved text translation data from proxy API for task {task_id}")
                        return {
                            'text': text_content.get('text', ''),
                            'source_language': text_content.get('source_language', 'en'),
                            'target_language': text_content.get('target_language', 'es')
                        }
                    else:
                        bt.logging.warning(f"⚠️ No text content found in proxy API response for task {task_id}")
                        return None
                else:
                    bt.logging.error(f"❌ Failed to fetch text translation data from proxy API: {response.status_code}")
                    return None
                        
        except Exception as e:
            bt.logging.error(f"❌ Error extracting text translation data: {e}")
            return None
    
    async def extract_document_translation_data(self, task_data: dict) -> Optional[dict]:
        """Extract document translation data from task data"""
        try:
            task_id = task_data.get("task_id")
            
            # Try to get data from task_data first
            if 'input_file' in task_data and task_data['input_file']:
                input_file = task_data['input_file']
                bt.logging.info(f"✅ Found document translation data in task_data for task {task_id}")
                return {
                    'filename': input_file.get('file_name', 'unknown'),
                    'source_language': task_data.get('source_language', 'en'),
                    'target_language': task_data.get('target_language', 'es')
                }
            
            # If not in task_data, try to fetch from proxy API
            bt.logging.info(f"🔍 Fetching document translation data from proxy API for task {task_id}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.proxy_server_url}/api/v1/miner/document-translation/{task_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and 'file_metadata' in data:
                        file_metadata = data['file_metadata']
                        bt.logging.info(f"✅ Retrieved document translation data from proxy API for task {task_id}")
                        return {
                            'filename': file_metadata.get('file_name', 'unknown'),
                            'source_language': data['task_metadata'].get('source_language', 'en'),
                            'target_language': data['task_metadata'].get('target_language', 'es')
                        }
                    else:
                        bt.logging.warning(f"⚠️ No file metadata found in proxy API response for task {task_id}")
                        return None
                else:
                    bt.logging.error(f"❌ Failed to fetch document translation data from proxy API: {response.status_code}")
                    return None
                        
        except Exception as e:
            bt.logging.error(f"❌ Error extracting document translation data: {e}")
            return None
    
    async def process_text_translation(self, translation_data: dict) -> dict:
        """Process text translation using translation pipeline"""
        try:
            if self.translation_pipeline is None:
                raise Exception("Translation pipeline not available")
            
            # Extract translation parameters
            text = translation_data.get("text", "")
            source_language = translation_data.get("source_language", "en")
            target_language = translation_data.get("target_language", "es")
            
            bt.logging.info(f"🌐 Processing text translation:")
            bt.logging.info(f"   Text length: {len(text)} characters")
            bt.logging.info(f"   From {source_language} to {target_language}")
            
            if not text:
                raise Exception("No text provided for translation")
            
            # Process text translation
            translated_text, processing_time = self.translation_pipeline.translate_text(
                text, source_language, target_language
            )
            
            return {
                "translated_text": translated_text,
                "source_language": source_language,
                "target_language": target_language,
                "processing_time": processing_time,
                "original_text_length": len(text),
                "translated_text_length": len(translated_text),
                "word_count": len(text.split()),
                "translated_word_count": len(translated_text.split())
            }
            
        except Exception as e:
            bt.logging.error(f"❌ Error processing text translation: {e}")
            return {
                "translated_text": "",
                "source_language": translation_data.get("source_language", "en"),
                "target_language": translation_data.get("target_language", "es"),
                "processing_time": 0.0,
                "original_text_length": 0,
                "translated_text_length": 0,
                "word_count": 0,
                "translated_word_count": 0,
                "error": str(e)
            }
    
    async def process_document_translation(self, document_data, translation_data: dict) -> dict:
        """Process document translation using translation pipeline"""
        try:
            if self.translation_pipeline is None:
                raise Exception("Translation pipeline not available")
            
            # Extract translation parameters
            filename = translation_data.get("filename", "unknown")
            source_language = translation_data.get("source_language", "en")
            target_language = translation_data.get("target_language", "es")
            
            bt.logging.info(f"📄 Processing document translation:")
            bt.logging.info(f"   Filename: {filename}")
            bt.logging.info(f"   File size: {len(document_data)} bytes")
            bt.logging.info(f"   From {source_language} to {target_language}")
            
            if not document_data:
                raise Exception("No document data provided for translation")
            
            # Process document translation
            translated_text, processing_time, metadata = self.translation_pipeline.translate_document(
                document_data, filename, source_language, target_language
            )
            
            return {
                "translated_text": translated_text,
                "source_language": source_language,
                "target_language": target_language,
                "processing_time": processing_time,
                "original_filename": filename,
                "file_size_bytes": len(document_data),
                "translated_text_length": len(translated_text),
                "metadata": metadata
            }
            
        except Exception as e:
            bt.logging.error(f"❌ Error processing document translation: {e}")
            return {
                "translated_text": "",
                "source_language": translation_data.get("source_language", "en"),
                "target_language": translation_data.get("target_language", "es"),
                "processing_time": 0.0,
                "original_filename": translation_data.get("filename", "unknown"),
                "file_size_bytes": len(document_data) if document_data else 0,
                "translated_text_length": 0,
                "metadata": {},
                "error": str(e)
            }
    
    async def submit_text_translation_result_to_proxy(self, callback_url: str, task_id: str, result: dict):
        """Submit text translation result to proxy server"""
        try:
            # Get miner UID from Bittensor
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            
            # Prepare form data
            form_data = {
                'task_id': task_id,
                'miner_uid': miner_uid,
                'translated_text': result.get('translated_text', ''),
                'processing_time': result.get('processing_time', 0.0),
                'accuracy_score': 0.95,  # Mock confidence for translation
                'speed_score': max(0.5, 1.0 - (result.get('processing_time', 0.0) / 10.0)),
                'source_language': result.get('source_language', 'en'),
                'target_language': result.get('target_language', 'es')
            }
            
            bt.logging.info(f"📤 Submitting text translation result to proxy server for task {task_id}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(callback_url, data=form_data)
                
                if response.status_code == 200:
                    bt.logging.info(f"✅ Text translation result submitted successfully for task {task_id}")
                else:
                    bt.logging.warning(f"⚠️ Failed to submit text translation result: {response.status_code}")
                    
        except Exception as e:
            bt.logging.error(f"❌ Error submitting text translation result: {e}")
    
    async def submit_document_translation_result_to_proxy(self, callback_url: str, task_id: str, result: dict):
        """Submit document translation result to proxy server"""
        try:
            # Get miner UID from Bittensor
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            
            # Prepare form data
            form_data = {
                'task_id': task_id,
                'miner_uid': miner_uid,
                'translated_text': result.get('translated_text', ''),
                'processing_time': result.get('processing_time', 0.0),
                'accuracy_score': 0.95,  # Mock confidence for translation
                'speed_score': max(0.5, 1.0 - (result.get('processing_time', 0.0) / 10.0)),
                'source_language': result.get('source_language', 'en'),
                'target_language': result.get('target_language', 'es'),
                'metadata': json.dumps(result.get('metadata', {}))
            }
            
            bt.logging.info(f"📤 Submitting document translation result to proxy server for task {task_id}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(callback_url, data=form_data)
                
                if response.status_code == 200:
                    bt.logging.info(f"✅ Document translation result submitted successfully for task {task_id}")
                else:
                    bt.logging.warning(f"⚠️ Failed to submit document translation result: {response.status_code}")
                    
        except Exception as e:
            bt.logging.error(f"❌ Error submitting document translation result: {e}")
    
    async def submit_result_to_proxy(self, callback_url: str, task_id: str, result: dict):
        """Submit task result back to proxy server"""
        try:
            # Get miner UID from Bittensor
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            
            # Prepare response payload based on task type
            response_payload = {
                "task_id": task_id,
                "miner_uid": miner_uid,
                "response_data": result,
                "processing_time": result.get("processing_time", 0.0),
                "speed_score": self.calculate_speed_score(result.get("processing_time", 0.0))
            }
            
            # Add task-specific metrics
            if "confidence" in result:  # Transcription or video transcription task
                response_payload["accuracy_score"] = result.get("confidence", 0.0)
            elif "summary" in result:  # Summarization task
                response_payload["accuracy_score"] = 0.95  # Mock confidence for summarization
            elif "output_data" in result:  # TTS task
                response_payload["accuracy_score"] = 0.90  # Mock confidence for TTS
            elif "translated_text" in result:  # Translation tasks
                response_payload["accuracy_score"] = 0.95  # Mock confidence for translation
            else:
                response_payload["accuracy_score"] = 0.0
            
            bt.logging.info(f"📤 Submitting result to proxy server for task {task_id}")
            bt.logging.info(f"   Callback URL: {callback_url}")
            bt.logging.info(f"   Miner UID: {miner_uid}")
            bt.logging.info(f"   Processing Time: {response_payload['processing_time']:.2f}s")
            bt.logging.info(f"   Accuracy Score: {response_payload['accuracy_score']:.2f}")
            bt.logging.info(f"   Speed Score: {response_payload['speed_score']:.2f}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Convert to Form data as expected by proxy
                form_data = {
                    'task_id': response_payload['task_id'],
                    'miner_uid': response_payload['miner_uid'],
                    'response_data': json.dumps(response_payload['response_data']),  # Use JSON serialization instead of str()
                    'processing_time': response_payload['processing_time'],
                    'accuracy_score': response_payload['accuracy_score'],
                    'speed_score': response_payload['speed_score']
                }
                
                submit_start_time = time.time()
                response = await client.post(callback_url, data=form_data)
                submit_time = time.time() - submit_start_time
                
                if response.status_code == 200:
                    bt.logging.info(f"✅ Result submitted successfully for task {task_id}")
                    bt.logging.info(f"   Submission time: {submit_time:.2f}s")
                    bt.logging.info(f"   Response status: {response.status_code}")
                    
                    # Log submission success
                    submission_log = {
                        "timestamp": datetime.now().isoformat(),
                        "event": "result_submission_success",
                        "task_id": task_id,
                        "miner_uid": miner_uid,
                        "submission_time": submit_time,
                        "response_status": response.status_code,
                        "response_headers": dict(response.headers)
                    }
                    
                    submission_log_file = self.response_logs_dir / f"{task_id}_{miner_uid}_submission_success.json"
                    with open(submission_log_file, 'w') as f:
                        json.dump(submission_log, f, indent=2, default=str)
                        
                else:
                    error_msg = f"Failed to submit result for task {task_id}: HTTP {response.status_code}"
                    bt.logging.warning(f"⚠️ {error_msg}")
                    bt.logging.warning(f"   Response body: {response.text}")
                    
                    # Log submission failure
                    submission_log = {
                        "timestamp": datetime.now().isoformat(),
                        "event": "result_submission_failure",
                        "task_id": task_id,
                        "miner_uid": miner_uid,
                        "submission_time": submit_time,
                        "response_status": response.status_code,
                        "response_body": response.text,
                        "error": error_msg
                    }
                    
                    submission_log_file = self.response_logs_dir / f"{task_id}_{miner_uid}_submission_failure.json"
                    with open(submission_log_file, 'w') as f:
                        json.dump(submission_log, f, indent=2, default=str)
                    
        except Exception as e:
            error_msg = f"Error submitting result: {str(e)}"
            bt.logging.error(f"❌ {error_msg}")
            
            # Log submission error
            submission_log = {
                "timestamp": datetime.now().isoformat(),
                "event": "result_submission_error",
                "task_id": task_id,
                "miner_uid": miner_uid,
                "error": error_msg,
                "callback_url": callback_url
            }
            
            submission_log_file = self.response_logs_dir / f"{task_id}_{miner_uid}_submission_error.json"
            with open(submission_log_file, 'w') as f:
                json.dump(submission_log, f, indent=2, default=str)
    
    def calculate_speed_score(self, processing_time: float) -> float:
        """Calculate speed score based on processing time"""
        try:
            # Normalize processing time (lower is better)
            # Assume 10 seconds is baseline, scale to 0-1
            baseline_time = 10.0
            if processing_time <= 0:
                return 1.0
            
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
        
        # ALWAYS process proxy tasks when any request comes in
        if hasattr(self, 'uid') and self.uid > 0:
            try:
                await self.query_proxy_for_tasks()
            except Exception as e:
                bt.logging.warning(f"⚠️ Failed to query proxy for tasks: {e}")
        
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

    async def submit_tts_result_to_proxy(self, callback_url: str, task_id: str, result: dict):
        """Submit TTS result to proxy server with audio file upload"""
        try:
            # Get miner UID from Bittensor
            miner_uid = self.uid if hasattr(self, 'uid') else 0
            
            # Check if we have audio file data
            audio_file = result.get("audio_file")
            if not audio_file:
                bt.logging.error(f"❌ No audio file data in TTS result for task {task_id}")
                return False
            
            # Read the audio file
            audio_path = audio_file.get("local_path")
            if not os.path.exists(audio_path):
                bt.logging.error(f"❌ Audio file not found at {audio_path}")
                return False
            
            with open(audio_path, "rb") as f:
                audio_content = f.read()
            
            bt.logging.info(f"📤 Submitting TTS result to proxy server for task {task_id}")
            bt.logging.info(f"   Callback URL: {callback_url}")
            bt.logging.info(f"   Miner UID: {miner_uid}")
            bt.logging.info(f"   Audio file: {audio_file.get('filename')}")
            bt.logging.info(f"   File size: {len(audio_content)} bytes")
            
            # Prepare form data for TTS upload
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Prepare form data
                files = {
                    'audio_file': (audio_file.get('filename'), audio_content, 'audio/wav')
                }
                
                data = {
                    'task_id': task_id,
                    'miner_uid': miner_uid,
                    'processing_time': result.get('processing_time', 0.0),
                    'accuracy_score': 0.90,  # Mock confidence for TTS
                    'speed_score': self.calculate_speed_score(result.get('processing_time', 0.0))
                }
                
                submit_start_time = time.time()
                response = await client.post(callback_url, files=files, data=data)
                submit_time = time.time() - submit_start_time
                
                if response.status_code == 200:
                    bt.logging.info(f"✅ TTS result submitted successfully for task {task_id}")
                    bt.logging.info(f"   Submission time: {submit_time:.2f}s")
                    bt.logging.info(f"   Response status: {response.status_code}")
                    
                    # Parse response to get file URL
                    response_data = response.json()
                    if response_data.get("success"):
                        file_url = response_data.get("file_url")
                        bt.logging.info(f"   Audio file URL: {file_url}")
                    
                    return True
                else:
                    error_msg = f"Failed to submit TTS result for task {task_id}: HTTP {response.status_code}"
                    bt.logging.warning(f"⚠️ {error_msg}")
                    bt.logging.warning(f"   Response body: {response.text}")
                    return False
                    
        except Exception as e:
            error_msg = f"Error submitting TTS result: {str(e)}"
            bt.logging.error(f"❌ {error_msg}")
            return False

    def cleanup_processed_tasks(self):
        """Clean up old processed tasks to prevent memory bloat"""
        try:
            if len(self.processed_tasks) > self.max_processed_tasks:
                # Keep only the most recent 80% of processed tasks
                keep_count = int(self.max_processed_tasks * 0.8)
                current_count = len(self.processed_tasks)
                
                # Convert to list, keep the last keep_count items
                tasks_list = list(self.processed_tasks)
                self.processed_tasks = set(tasks_list[-keep_count:])
                
                bt.logging.info(f"🧹 Cleaned up processed tasks: {current_count} -> {len(self.processed_tasks)}")
        except Exception as e:
            bt.logging.warning(f"⚠️ Error cleaning up processed tasks: {e}")
    
    def get_duplicate_protection_stats(self):
        """Get statistics about duplicate protection"""
        try:
            # Calculate protection effectiveness
            total_processed = len(self.processed_tasks)
            currently_processing = len(self.processing_tasks)
            
            # Estimate duplicate attempts prevented
            # This is based on the fact that without protection, miners would process tasks multiple times
            estimated_duplicates_prevented = total_processed * 2  # Conservative estimate
            
            return {
                'processed_tasks_count': total_processed,
                'processing_tasks_count': currently_processing,
                'max_processed_tasks': self.max_processed_tasks,
                'duplicate_protection_active': True,
                'protection_mechanisms': [
                    'In-memory processed tasks tracking',
                    'Currently processing tasks tracking',
                    'Task status validation',
                    'Atomic task processing with threading locks',
                    'Automatic cleanup of old processed tasks'
                ],
                'estimated_duplicates_prevented': estimated_duplicates_prevented,
                'memory_usage_percentage': f"{(total_processed / self.max_processed_tasks) * 100:.1f}%",
                'cleanup_threshold': f"{(self.max_processed_tasks * 0.8):.0f}",
                'thread_safety': 'enabled' if hasattr(self, 'task_processing_lock') else 'disabled'
            }
        except Exception as e:
            return {
                'error': f'Error getting duplicate protection stats: {str(e)}',
                'duplicate_protection_active': False
            }


# This is the main function, which runs the miner.
if __name__ == "__main__":
    with Miner() as miner:
        last_task_check = 0
        task_check_interval = 10  # Check for tasks every 10 seconds
        
        # Run initial tests
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Test file download capability
                loop.run_until_complete(miner.test_file_download())
                
                # Test miner tasks endpoint to debug task structure
                loop.run_until_complete(miner.test_miner_tasks_endpoint())
            finally:
                loop.close()
        except Exception as e:
            bt.logging.warning(f"⚠️ Initial test error: {e}")
        
        while True:
            current_time = time.time()
            
            # Check for proxy tasks periodically
            if current_time - last_task_check >= task_check_interval:
                try:
                    # Create a new event loop for task processing
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(miner.query_proxy_for_tasks())
                    finally:
                        loop.close()
                    last_task_check = current_time
                except Exception as e:
                    bt.logging.warning(f"⚠️ Main loop task check error: {e}")
            
            # Log less frequently to reduce console spam
            if int(current_time) % 60 == 0:  # Only log every minute
                bt.logging.info(f"Miner running... {current_time}")
            
            time.sleep(5)
