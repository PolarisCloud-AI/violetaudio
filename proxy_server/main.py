#!/usr/bin/env python3
"""
FastAPI Proxy Server for Bittensor Audio Processing Subnet
This server provides REST API endpoints for audio processing services and manages
the task queue workflow with the Bittensor network.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import base64
import threading
import time

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import uvicorn

# Bittensor imports
import bittensor as bt
from template.protocol import AudioTask
from template.validator.reward import run_validator_pipeline, calculate_accuracy_score, calculate_speed_score

# Initialize FastAPI app
app = FastAPI(
    title="Bittensor Audio Processing Proxy Server",
    description="REST API for audio transcription, TTS, and summarization services",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Task status enum
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# Task priority enum
class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

# Service-specific request models
class TranscriptionRequest(BaseModel):
    """Request model for audio transcription"""
    source_language: str = Field(..., description="Source language code (e.g., 'en', 'es', 'fr')")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority level")
    callback_url: Optional[str] = Field(None, description="Optional webhook URL for task completion notification")
    
    @validator('source_language')
    def validate_language(cls, v):
        valid_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh', 'ar', 'hi']
        if v.lower() not in valid_languages:
            raise ValueError(f'Language must be one of: {", ".join(valid_languages)}')
        return v.lower()

class TTSRequest(BaseModel):
    """Request model for text-to-speech"""
    text: str = Field(..., description="Text to convert to speech")
    source_language: str = Field(..., description="Source language code (e.g., 'en', 'es', 'fr')")
    priority: TaskPriority = Field(..., description="Task priority level")
    callback_url: Optional[str] = Field(None, description="Optional webhook URL for task completion notification")
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty')
        if len(v) > 10000:  # Limit text length
            raise ValueError('Text too long (max 10,000 characters)')
        return v.strip()
    
    @validator('source_language')
    def validate_language(cls, v):
        valid_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh', 'ar', 'hi']
        if v.lower() not in valid_languages:
            raise ValueError(f'Language must be one of: {", ".join(valid_languages)}')
        return v.lower()

class SummarizationRequest(BaseModel):
    """Request model for text summarization"""
    text: str = Field(..., description="Text to summarize")
    source_language: str = Field(..., description="Source language code (e.g., 'en', 'es', 'fr')")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority level")
    callback_url: Optional[str] = Field(None, description="Optional webhook URL for task completion notification")
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty')
        if len(v) < 50:  # Minimum text length for summarization
            raise ValueError('Text too short for summarization (min 50 characters)')
        if len(v) > 50000:  # Maximum text length
            raise ValueError('Text too long (max 50,000 characters)')
        return v.strip()
    
    @validator('source_language')
    def validate_language(cls, v):
        valid_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh', 'ar', 'hi']
        if v.lower() not in valid_languages:
            raise ValueError(f'Language must be one of: {", ".join(valid_languages)}')
        return v.lower()

# Response models
class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str
    estimated_completion_time: Optional[int] = None
    task_type: str
    source_language: str

class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    task_type: str
    source_language: str
    result: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None
    accuracy_score: Optional[float] = None
    speed_score: Optional[float] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None

# In-memory task storage
class TaskStorage:
    """In-memory task storage with thread safety"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
        self.pending_tasks: List[str] = []
        self.processing_tasks: List[str] = []
        self.completed_tasks: List[str] = []
        self.failed_tasks: List[str] = []
        self.lock = threading.Lock()
    
    def add_task(self, task_id: str, task_data: Dict) -> None:
        """Add a new task"""
        with self.lock:
            task_data['queued_at'] = datetime.now().isoformat()
            task_data['status'] = TaskStatus.PENDING
            
            self.tasks[task_id] = task_data
            self.pending_tasks.append(task_id)
            
            # Sort by priority
            self._sort_pending_tasks()
    
    def get_next_task(self) -> Optional[Dict]:
        """Get next task from queue based on priority"""
        with self.lock:
            if not self.pending_tasks:
                return None
            
            task_id = self.pending_tasks[0]
            task_data = self.tasks.get(task_id)
            
            if task_data:
                return {"task_id": task_id, **task_data}
            return None
    
    def mark_task_processing(self, task_id: str) -> bool:
        """Mark task as processing"""
        with self.lock:
            if task_id in self.pending_tasks:
                self.pending_tasks.remove(task_id)
                self.processing_tasks.append(task_id)
                
                if task_id in self.tasks:
                    self.tasks[task_id]['status'] = TaskStatus.PROCESSING
                    self.tasks[task_id]['processing_started_at'] = datetime.now().isoformat()
                return True
            return False
    
    def mark_task_completed(self, task_id: str, result: Dict) -> bool:
        """Mark task as completed"""
        with self.lock:
            if task_id in self.processing_tasks:
                self.processing_tasks.remove(task_id)
                self.completed_tasks.append(task_id)
                
                if task_id in self.tasks:
                    self.tasks[task_id]['status'] = TaskStatus.COMPLETED
                    self.tasks[task_id]['completed_at'] = datetime.now().isoformat()
                    self.tasks[task_id].update(result)
                return True
            return False
    
    def mark_task_failed(self, task_id: str, error_message: str) -> bool:
        """Mark task as failed"""
        with self.lock:
            if task_id in self.processing_tasks:
                self.processing_tasks.remove(task_id)
                self.failed_tasks.append(task_id)
                
                if task_id in self.tasks:
                    self.tasks[task_id]['status'] = TaskStatus.FAILED
                    self.tasks[task_id]['failed_at'] = datetime.now().isoformat()
                    self.tasks[task_id]['error_message'] = error_message
                return True
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get task status"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get complete task data"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def list_tasks(self, status: Optional[TaskStatus] = None, limit: int = 100) -> List[Dict]:
        """List tasks with optional status filter"""
        with self.lock:
            if status:
                if status == TaskStatus.PENDING:
                    task_ids = self.pending_tasks
                elif status == TaskStatus.PROCESSING:
                    task_ids = self.processing_tasks
                elif status == TaskStatus.COMPLETED:
                    task_ids = self.completed_tasks
                elif status == TaskStatus.FAILED:
                    task_ids = self.failed_tasks
                else:
                    task_ids = []
            else:
                task_ids = list(self.tasks.keys())
            
            tasks = []
            for task_id in task_ids[:limit]:
                task_data = self.get_task_status(task_id)
                if task_data:
                    tasks.append(task_data)
            
            return tasks
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        with self.lock:
            return {
                "pending_count": len(self.pending_tasks),
                "processing_count": len(self.processing_tasks),
                "completed_count": len(self.completed_tasks),
                "failed_count": len(self.failed_tasks),
                "total_tasks": len(self.tasks),
                "timestamp": datetime.now().isoformat()
            }
    
    def _sort_pending_tasks(self):
        """Sort pending tasks by priority"""
        def get_priority_score(task_id):
            task_data = self.tasks.get(task_id, {})
            priority = task_data.get('priority', 'normal')
            priority_map = {'low': 1, 'normal': 2, 'high': 3, 'urgent': 4}
            return priority_map.get(priority, 2)
        
        self.pending_tasks.sort(key=get_priority_score, reverse=True)

# Initialize task storage
task_storage = TaskStorage()

# Bittensor configuration
class BittensorConfig:
    def __init__(self):
        self.wallet = None
        self.subtensor = None
        self.metagraph = None
        self.dendrite = None
        self.netuid = 49
        self.network = "finney"
        
    async def initialize(self):
        """Initialize Bittensor components"""
        try:
            self.wallet = bt.wallet(name="luno", hotkey="arusha")
            self.subtensor = bt.subtensor(network=self.network)
            self.metagraph = self.subtensor.metagraph(netuid=self.netuid)
            self.dendrite = bt.dendrite(wallet=self.wallet)
            
            # Sync metagraph
            self.metagraph.sync(subtensor=self.subtensor)
            print(f"✅ Bittensor initialized - {len(self.metagraph.hotkeys)} total miners")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize Bittensor: {str(e)}")
            return False

# Initialize Bittensor config
bt_config = BittensorConfig()

# Remove the background task processor that directly calls miners
# The proxy server should only queue tasks and wait for validator results

# Add endpoint for validator to submit results
@app.post("/api/v1/validator/submit_result", response_model=Dict)
async def submit_validator_result(
    task_id: str = Form(...),
    result: str = Form(...),
    processing_time: float = Form(...),
    miner_uid: int = Form(...),
    accuracy_score: float = Form(...),
    speed_score: float = Form(...)
):
    """Receive task results from validator"""
    try:
        # Update task with validator result
        if task_storage.mark_task_completed(task_id, {
            'output_data': result,
            'processing_time': processing_time,
            'miner_uid': miner_uid,
            'accuracy_score': accuracy_score,
            'speed_score': speed_score,
            'completed_by_validator': True
        }):
            return {
                'success': True,
                'message': f'Result received for task {task_id}',
                'task_id': task_id
            }
        else:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit result: {str(e)}")

# Add endpoint to get task result
@app.get("/api/v1/task/{task_id}/result", response_model=TaskResult)
async def get_task_result(task_id: str):
    """Get the result of a completed task"""
    try:
        task = task_storage.get_task_status(task_id) # Changed from get_task to get_task_status
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task['status'] != TaskStatus.COMPLETED:
            return TaskResult(
                task_id=task_id,
                status=task['status'],
                task_type=task.get('task_type', 'unknown'),
                source_language=task.get('language', 'en'),
                result=None,
                processing_time=None,
                accuracy_score=None,
                speed_score=None,
                error_message=None,
                completed_at=None
            )
        
        # Return completed task result
        return TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            task_type=task.get('task_type', 'unknown'),
            source_language=task.get('language', 'en'),
            result={
                'output_data': task.get('output_data'),
                'processing_time': task.get('processing_time'),
                'miner_uid': task.get('miner_uid'),
                'accuracy_score': task.get('accuracy_score'),
                'speed_score': task.get('speed_score')
            },
            processing_time=task.get('processing_time'),
            accuracy_score=task.get('accuracy_score'),
            speed_score=task.get('speed_score'),
            error_message=task.get('error_message'),
            completed_at=task.get('completed_at')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task result: {str(e)}")

# Modify the startup to remove background task processor
@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    try:
        # Initialize Bittensor client
        if await bt_config.initialize():
            print("✅ Bittensor initialized - {} total miners".format(len(bt_config.metagraph.hotkeys)))
        else:
            print("❌ Failed to initialize Bittensor client")
        
        # Remove background task processor - tasks will be processed by validator
        # asyncio.create_task(process_task_queue())
        
        print("🚀 Proxy server ready - tasks will be processed by validator")
        print("🔗 Validator integration endpoints available:")
        print("   GET  /api/v1/validator/integration - Get network and task info")
        print("   POST /api/v1/validator/distribute - Distribute tasks to validator")
        print("   POST /api/v1/validator/submit_result - Submit task results from validator")
        print("   GET  /api/v1/task/{task_id}/result - Get task result for user")
        print("   GET  /api/v1/task/{task_id}/responses - Get all task responses and best response")
        
    except Exception as e:
        print(f"❌ Error during startup: {str(e)}")
        raise

# API Endpoints

@app.post("/api/v1/transcription", response_model=TaskResponse)
async def submit_transcription_task(
    audio_file: UploadFile = File(..., description="Audio file to transcribe"),
    request: TranscriptionRequest = Depends()
):
    """Submit a new audio transcription task"""
    try:
        # Validate audio file
        if not audio_file.filename:
            raise HTTPException(status_code=400, detail="Audio file is required")
        
        # Check file size (max 50MB)
        if audio_file.size and audio_file.size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Audio file too large (max 50MB)")
        
        # Read and encode audio file
        audio_content = await audio_file.read()
        if not audio_content:
            raise HTTPException(status_code=400, detail="Audio file is empty")
        
        # Encode audio to base64
        audio_b64 = base64.b64encode(audio_content).decode('utf-8')
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Create task data
        task_data = {
            "task_id": task_id,
            "task_type": "transcription",
            "input_data": audio_b64,
            "language": request.source_language,
            "priority": request.priority.value,
            "callback_url": request.callback_url,
            "submitted_at": datetime.now().isoformat(),
            "status": TaskStatus.PENDING,
            "file_name": audio_file.filename,
            "file_size": len(audio_content)
        }
        
        # Add task to storage
        task_storage.add_task(task_id, task_data)
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Transcription task submitted successfully",
            estimated_completion_time=60,  # 60 seconds for transcription
            task_type="transcription",
            source_language=request.source_language
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit transcription task: {str(e)}")

@app.post("/api/v1/tts", response_model=TaskResponse)
async def submit_tts_task(request: TTSRequest):
    """Submit a new text-to-speech task"""
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Encode text to base64
        text_b64 = base64.b64encode(request.text.encode('utf-8')).decode('utf-8')
        
        # Create task data
        task_data = {
            "task_id": task_id,
            "task_type": "tts",
            "input_data": text_b64,
            "language": request.source_language,
            "priority": request.priority.value,
            "callback_url": request.callback_url,
            "submitted_at": datetime.now().isoformat(),
            "status": TaskStatus.PENDING,
            "text_length": len(request.text)
        }
        
        # Add task to storage
        task_storage.add_task(task_id, task_data)
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="TTS task submitted successfully",
            estimated_completion_time=45,  # 45 seconds for TTS
            task_type="tts",
            source_language=request.source_language
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit TTS task: {str(e)}")

@app.post("/api/v1/summarization", response_model=TaskResponse)
async def submit_summarization_task(request: SummarizationRequest):
    """Submit a new text summarization task"""
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Encode text to base64
        text_b64 = base64.b64encode(request.text.encode('utf-8')).decode('utf-8')
        
        # Create task data
        task_data = {
            "task_id": task_id,
            "task_type": "summarization",
            "input_data": text_b64,
            "language": request.source_language,
            "priority": request.priority.value,
            "callback_url": request.callback_url,
            "submitted_at": datetime.now().isoformat(),
            "status": TaskStatus.PENDING,
            "text_length": len(request.text)
        }
        
        # Add task to storage
        task_storage.add_task(task_id, task_data)
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Summarization task submitted successfully",
            estimated_completion_time=30,  # 30 seconds for summarization
            task_type="summarization",
            source_language=request.source_language
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit summarization task: {str(e)}")

@app.get("/api/v1/tasks/{task_id}", response_model=TaskResult)
async def get_task_status(task_id: str):
    """Get the status and result of a specific task"""
    try:
        task_data = task_storage.get_task_status(task_id)
        if not task_data:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Convert to response model
        result = TaskResult(
            task_id=task_id,
            status=TaskStatus(task_data.get('status', 'pending')),
            task_type=task_data.get('task_type', 'unknown'),
            source_language=task_data.get('language', 'unknown'),
            completed_at=datetime.fromisoformat(task_data['completed_at']) if task_data.get('completed_at') else None
        )
        
        # Add result data if completed
        if task_data.get('status') == TaskStatus.COMPLETED:
            result.result = {
                "output_data": task_data.get('output_data'),
                "model_used": task_data.get('pipeline_model'),
                "processing_time": float(task_data.get('processing_time', 0)),
                "accuracy_score": float(task_data.get('accuracy_score', 0)),
                "speed_score": float(task_data.get('speed_score', 0)),
                "miner_uid": task_data.get('miner_uid')
            }
            result.processing_time = float(task_data.get('processing_time', 0))
            result.accuracy_score = float(task_data.get('accuracy_score', 0))
            result.speed_score = float(task_data.get('speed_score', 0))
        
        # Add error message if failed
        if task_data.get('status') == TaskStatus.FAILED:
            result.error_message = task_data.get('error_message')
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

@app.get("/api/v1/task/{task_id}/responses")
async def get_task_responses(task_id: str):
    """Get task information including best response and input details (filtered for client use)"""
    try:
        print(f"🔍 Getting filtered task responses for task: {task_id}")
        
        # Get task from storage
        task_data = task_storage.get_task_status(task_id)
        if not task_data:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Extract best response
        best_response = task_data.get('best_response', {})
        
        # Format standardized response data based on task type
        task_type = task_data.get('task_type')
        
        if task_type == 'transcription':
            # Standardized transcription response format
            response_data = {
                "task_id": task_id,
                "task_type": task_type,
                "status": task_data.get('status'),
                "created_at": task_data.get('submitted_at'),
                "best_response": {
                    "output_data": best_response.get('response_data', {}).get('output_data', {}) if best_response else {},
                    "processing_time": best_response.get('processing_time', 0) if best_response else 0,
                    "accuracy_score": best_response.get('accuracy_score', 0) if best_response else 0,
                    "speed_score": best_response.get('speed_score', 0) if best_response else 0
                } if best_response else None,
                "task_summary": {
                    "total_responses_received": len(task_data.get('miner_responses', [])) if isinstance(task_data.get('miner_responses', []), list) else 0,
                    "required_miner_count": task_data.get('required_miner_count', 1),
                    "task_priority": task_data.get('priority', 'normal')
                }
            }
        else:
            # Fallback format for other task types
            response_data = {
                "task_id": task_id,
                "task_type": task_type,
                "status": task_data.get('status'),
                "created_at": task_data.get('submitted_at'),
                "best_response": {
                    "response_data": best_response.get('response_data'),
                    "processing_time": best_response.get('processing_time'),
                    "accuracy_score": best_response.get('accuracy_score'),
                    "speed_score": best_response.get('speed_score'),
                    "submitted_at": best_response.get('submitted_at')
                } if best_response else None,
                "task_summary": {
                    "total_responses_received": len(task_data.get('miner_responses', [])) if isinstance(task_data.get('miner_responses', []), list) else 0,
                    "required_miner_count": task_data.get('required_miner_count', 1),
                    "task_priority": task_data.get('priority', 'normal')
                }
            }
        
        print(f"✅ Retrieved filtered task information for task {task_id}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting task responses: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task responses: {str(e)}")

@app.get("/api/v1/tasks/completed")
async def get_completed_tasks():
    """Get all completed tasks for validator evaluation"""
    try:
        print(f"🔍 Getting completed tasks for validator evaluation")
        
        # Get all completed tasks from database
        tasks_ref = db_manager.get_db().collection('tasks')
        completed_tasks = tasks_ref.where('status', '==', 'completed').stream()
        
        tasks = []
        for task_doc in completed_tasks:
            task_data = task_doc.to_dict()
            task_data['task_id'] = task_doc.id
            
            # Ensure miner_responses is included for evaluation
            if 'miner_responses' not in task_doc:
                task_data['miner_responses'] = []
            
            tasks.append(task_data)
        
        print(f"✅ Retrieved {len(tasks)} completed tasks for validator evaluation")
        return tasks
        
    except Exception as e:
        print(f"❌ Error getting completed tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get completed tasks: {str(e)}")

@app.get("/api/v1/tasks", response_model=List[Dict])
async def list_tasks(status: Optional[TaskStatus] = None, limit: int = 100):
    """List all tasks with optional status filter"""
    try:
        return task_storage.list_tasks(status, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    stats = task_storage.get_stats()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bittensor_connected": bt_config.wallet is not None,
        "queue_size": stats["pending_count"],
        "pending_tasks": stats["pending_count"],
        "processing_tasks": stats["processing_count"],
        "completed_tasks": stats["completed_count"],
        "failed_tasks": stats["failed_count"],
        "total_tasks": stats["total_tasks"]
    }

@app.get("/api/v1/validator/integration")
async def get_validator_integration_info():
    """Get information for validator integration"""
    try:
        # Get available miners
        available_miners = []
        miner_info = []
        
        for uid in range(len(bt_config.metagraph.hotkeys)):
            if bt_config.metagraph.axons[uid].is_serving:
                available_miners.append(uid)
                axon = bt_config.metagraph.axons[uid]
                miner_info.append({
                    "uid": uid,
                    "hotkey": bt_config.metagraph.hotkeys[uid],
                    "ip": axon.ip,
                    "port": axon.port,
                    "external_ip": getattr(axon, 'external_ip', axon.ip),
                    "external_port": getattr(axon, 'external_port', axon.port),
                    "stake": float(bt_config.metagraph.S[uid]) if len(bt_config.metagraph.S) > uid else 0.0
                })
        
        # Get pending tasks for validator
        pending_tasks = []
        for task_id in task_storage.pending_tasks[:10]:  # Limit to 10 tasks
            task_data = task_storage.get_task_status(task_id)
            if task_data:
                pending_tasks.append({
                    "task_id": task_id,
                    "task_type": task_data.get('task_type'),
                    "language": task_data.get('language'),
                    "priority": task_data.get('priority'),
                    "submitted_at": task_data.get('submitted_at')
                })
        
        return {
            "network_info": {
                "netuid": bt_config.netuid,
                "network": bt_config.network,
                "total_miners": len(bt_config.metagraph.hotkeys),
                "available_miners": len(available_miners)
            },
            "miners": miner_info,
            "pending_tasks": pending_tasks,
            "queue_stats": task_storage.get_stats()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get validator integration info: {str(e)}")

@app.post("/api/v1/validator/distribute")
async def distribute_tasks_to_validator():
    """Distribute pending tasks to the validator for processing"""
    try:
        # Get all pending tasks
        pending_tasks = []
        for task_id in task_storage.pending_tasks:
            task_data = task_storage.get_task_status(task_id)
            if task_data:
                pending_tasks.append({
                    "task_id": task_id,
                    "task_type": task_data.get('task_type'),
                    "input_data": task_data.get('input_data'),
                    "language": task_data.get('language'),
                    "priority": task_data.get('priority'),
                    "submitted_at": task_data.get('submitted_at')
                })
        
        if not pending_tasks:
            return {"message": "No pending tasks to distribute", "task_count": 0}
        
        print(f"🔄 Distributing {len(pending_tasks)} tasks to validator...")
        
        # Mark tasks as processing (they will be handled by validator)
        for task_data in pending_tasks:
            task_storage.mark_task_processing(task_data['task_id'])
        
        return {
            "message": f"Distributed {len(pending_tasks)} tasks to validator",
            "task_count": len(pending_tasks),
            "tasks": pending_tasks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to distribute tasks: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
