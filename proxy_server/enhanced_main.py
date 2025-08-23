"""
Enhanced Proxy Server for Bittensor Audio Processing Subnet
Integrates database, file management, workflow orchestration, and API endpoints
"""

import asyncio
import json
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
import uvicorn
import os
from pathlib import Path

# Import our custom modules
from proxy_server.database.enhanced_schema import (
    TaskStatus, TaskPriority, TaskType, TaskModel, 
    MinerInfo, FileReference, COLLECTIONS, DatabaseOperations
)
from proxy_server.managers.task_manager import TaskManager
from proxy_server.managers.file_manager import FileManager
from proxy_server.managers.miner_response_handler import MinerResponseHandler
from proxy_server.orchestrators.workflow_orchestrator import WorkflowOrchestrator
from proxy_server.api.validator_integration import ValidatorIntegrationAPI

# Simple in-memory cache for frequently accessed data
class SimpleCache:
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
        self.access_times = {}
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Check if expired
            if datetime.now().timestamp() - self.access_times[key] > self.ttl:
                del self.cache[key]
                del self.access_times[key]
                return None
            
            # Update access time
            self.access_times[key] = datetime.now().timestamp()
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        # Remove oldest if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        self.cache[key] = value
        self.access_times[key] = datetime.now().timestamp()
    
    def invalidate(self, key: str):
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
    
    def clear(self):
        self.cache.clear()
        self.access_times.clear()

# Initialize cache
cache = SimpleCache(max_size=500, ttl=60)  # 500 items, 60 seconds TTL

# System metrics collection
class SystemMetrics:
    def __init__(self):
        self.start_time = datetime.now()
        self.total_requests = 0
        self.total_tasks = 0
        self.total_miner_responses = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.database_operations = 0
        self.errors = 0
    
    def increment_requests(self):
        self.total_requests += 1
    
    def increment_tasks(self):
        self.total_tasks += 1
    
    def increment_miner_responses(self):
        self.total_miner_responses += 1
    
    def increment_cache_hits(self):
        self.cache_hits += 1
    
    def increment_cache_misses(self):
        self.cache_misses += 1
    
    def increment_database_operations(self):
        self.database_operations += 1
    
    def increment_errors(self):
        self.errors += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "uptime_seconds": uptime,
            "uptime_hours": uptime / 3600,
            "total_requests": self.total_requests,
            "total_tasks": self.total_tasks,
            "total_miner_responses": self.total_miner_responses,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            "database_operations": self.database_operations,
            "errors": self.errors,
            "requests_per_second": self.total_requests / uptime if uptime > 0 else 0,
            "tasks_per_second": self.total_tasks / uptime if uptime > 0 else 0,
            "timestamp": datetime.now().isoformat()
        }

# Initialize system metrics
system_metrics = SystemMetrics()

# Weights & Biases integration for monitoring
import wandb
from typing import Dict, Any, Optional, List
import os
from proxy_server.wandb_config import setup_wandb, get_wandb_config

class WandbMonitor:
    def __init__(self, project_name: str = "bittensor-subnet", entity: str = None):
        self.project_name = project_name
        self.entity = entity
        self.run = None
        self.initialized = False
        
        # Setup wandb automatically
        setup_wandb()
        
        try:
            # Get configuration
            config = get_wandb_config()
            
            # Initialize wandb with automatic configuration
            self.run = wandb.init(
                project=config["project"],
                entity=config["entity"],
                tags=config["tags"],
                notes=config["notes"],
                config=config["config"],
                mode="online"
            )
            self.initialized = True
            print(f"✅ Wandb monitoring initialized automatically: {self.run.url}")
            print(f"🔑 API key configured and authenticated")
            print(f"📊 Project: {config['project']}")
        except Exception as e:
            print(f"⚠️  Wandb initialization failed: {e}")
            self.initialized = False
    
    def log_task_metrics(self, task_data: Dict[str, Any]):
        """Log task completion metrics"""
        if not self.initialized:
            return
        
        try:
            wandb.log({
                "task_completed": 1,
                "task_type": task_data.get('task_type'),
                "processing_time": task_data.get('processing_time', 0),
                "accuracy_score": task_data.get('accuracy_score', 0),
                "speed_score": task_data.get('speed_score', 0),
                "miner_count": len(task_data.get('assigned_miners', [])),
                "priority": task_data.get('priority', 'normal')
            })
        except Exception as e:
            print(f"⚠️  Failed to log task metrics: {e}")
    
    def log_miner_performance(self, miner_uid: int, performance_data: Dict[str, Any]):
        """Log individual miner performance"""
        if not self.initialized:
            return
        
        try:
            wandb.log({
                f"miner_{miner_uid}_accuracy": performance_data.get('avg_accuracy_score', 0),
                f"miner_{miner_uid}_speed": performance_data.get('avg_speed_score', 0),
                f"miner_{miner_uid}_processing_time": performance_data.get('avg_processing_time', 0),
                f"miner_{miner_uid}_overall_score": performance_data.get('overall_score', 0),
                f"miner_{miner_uid}_tasks_completed": performance_data.get('completed_tasks', 0)
            })
        except Exception as e:
            print(f"⚠️  Failed to log miner performance: {e}")
    
    def log_system_metrics(self, metrics: Dict[str, Any]):
        """Log system-wide metrics"""
        if not self.initialized:
            return
        
        try:
            wandb.log(metrics)
        except Exception as e:
            print(f"⚠️  Failed to log system metrics: {e}")
    
    def finish(self):
        """Finish the wandb run"""
        if self.initialized and self.run:
            self.run.finish()

# Initialize wandb monitor
wandb_monitor = WandbMonitor(project_name="bittensor-inference-subnet")

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced Bittensor Audio Processing Proxy Server",
    description="Advanced proxy server with database integration, workflow orchestration, and real-time monitoring",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging"""
    start_time = time.time()
    
    # Log the request
    print(f"📥 {request.method} {request.url.path} - Client: {request.client.host if request.client else 'unknown'}")
    
    # Check for problematic requests
    if "None" in str(request.url) or "null" in str(request.url):
        print(f"⚠️  WARNING: Request contains None/null values: {request.url}")
    
    # Process the request
    response = await call_next(request)
    
    # Log response time
    process_time = time.time() - start_time
    print(f"📤 {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
    
    return response

# Add middleware for request tracking
@app.middleware("http")
async def track_requests(request, call_next):
    # Track request
    system_metrics.increment_requests()
    
    # Process request
    response = await call_next(request)
    
    # Track errors
    if response.status_code >= 400:
        system_metrics.increment_errors()
    
    return response

# Global variables for managers
file_manager = None
task_manager = None
workflow_orchestrator = None
validator_api = None
miner_response_handler = None

# Pydantic models for API requests
class TranscriptionRequest(BaseModel):
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

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize all managers and start background tasks"""
    global file_manager, task_manager, workflow_orchestrator, validator_api, miner_response_handler
    
    try:
        print("🚀 Starting Enhanced Proxy Server...")
        
        # Initialize database with robust path resolution
        from proxy_server.database.schema import DatabaseManager
        import os
        
        # Try multiple possible paths for the credentials file
        possible_paths = [
            "proxy_server/db/violet.json",  # From project root
            "db/violet.json",               # From proxy_server directory
            os.path.join(os.path.dirname(__file__), "db", "violet.json"),  # Absolute path
            os.path.join(os.getcwd(), "proxy_server", "db", "violet.json")  # Current working directory
        ]
        
        credentials_path = None
        for path in possible_paths:
            if os.path.exists(path):
                credentials_path = path
                print(f"✅ Found credentials at: {path}")
                break
        
        if not credentials_path:
            raise FileNotFoundError(f"Firebase credentials not found. Tried paths: {possible_paths}")
        
        global db_manager
        db_manager = DatabaseManager(credentials_path)
        db_manager.initialize()
        
                # Initialize managers
        global file_manager, task_manager, workflow_orchestrator, validator_api, miner_response_handler
        file_manager = FileManager(db_manager.get_db())
        task_manager = TaskManager(db_manager.get_db())
        workflow_orchestrator = WorkflowOrchestrator(db_manager.get_db(), task_manager)
        validator_api = ValidatorIntegrationAPI(db_manager.get_db())
        miner_response_handler = MinerResponseHandler(db_manager.get_db(), task_manager)
        
        # Start workflow orchestrator
        await workflow_orchestrator.start_orchestration()
        
        # Log system startup to wandb
        if wandb_monitor.initialized:
            wandb_monitor.log_system_metrics({
                "system_startup": True,
                "startup_timestamp": datetime.now().isoformat(),
                "server_version": "1.0.0",
                "architecture": "proxy-validator-miner",
                "features": ["caching", "monitoring", "wandb", "grafana"]
            })
            print("📊 Wandb monitoring active - system startup logged")
        
        print("✅ Enhanced Proxy Server started successfully!")
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        raise

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions globally"""
    print(f"❌ Unhandled exception in {request.method} {request.url.path}: {exc}")
    print(f"   Exception type: {type(exc).__name__}")
    print(f"   Client: {request.client.host if request.client else 'unknown'}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
            "message": "An unexpected error occurred. Please check the server logs."
        }
    )

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    global workflow_orchestrator
    
    try:
        if workflow_orchestrator:
            await workflow_orchestrator.stop_orchestration()
        print("🛑 Enhanced Proxy Server shutdown complete")
    except Exception as e:
        print(f"❌ Error during shutdown: {str(e)}")

# API Endpoints

@app.post("/api/v1/transcription")
async def submit_transcription_task(
    audio_file: UploadFile = File(...),
    source_language: str = Form("en"),
    priority: str = Form("normal")
):
    """Submit transcription task"""
    try:
        # Read file data
        file_data = await audio_file.read()
        
        # Upload file to local storage with transcription type
        file_id = await file_manager.upload_file(
            file_data, 
            audio_file.filename, 
            audio_file.content_type,
            file_type="transcription"
        )
        
        # Get the actual file metadata to get the correct local_path
        file_metadata = await file_manager.get_file_metadata(file_id)
        
        # Create task using enhanced schema
        task_data = {
            'task_type': 'transcription',
            'input_file': {
                'file_id': file_id,
                'file_name': audio_file.filename,
                'file_type': audio_file.content_type,
                'file_size': len(file_data),
                'local_path': file_metadata['local_path'] if file_metadata else f"/proxy_server/local_storage/user_audio/{file_id}",
                'file_url': f"/api/v1/files/{file_id}",
                'checksum': str(hash(file_data)),  # Simple hash for now
                'uploaded_at': datetime.now()
            },
            'priority': priority,
            'source_language': source_language,
            'required_miner_count': 3
        }
        
        # Use enhanced database operations
        task_id = DatabaseOperations.create_task(db_manager.get_db(), task_data)
        
        # Track metrics
        system_metrics.increment_tasks()
        
        # Log task creation to wandb
        if wandb_monitor.initialized:
            wandb_monitor.log_task_metrics({
                'task_type': 'transcription',
                'task_id': task_id,
                'priority': priority,
                'source_language': source_language,
                'file_id': file_id,
                'created_at': datetime.now().isoformat()
            })
        
        # Start task distribution
        # Note: The workflow orchestrator handles task distribution automatically
        # We don't need to call a specific method here
        
        return {
            "success": True,
            "task_id": task_id,
            "file_id": file_id,
            "message": "Transcription task submitted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")

@app.post("/api/v1/tts")
async def submit_tts_task(
    text: str = Form(...),
    target_language: str = Form("en"),
    priority: str = Form("normal")
):
    """Submit text-to-speech task"""
    try:
        # Encode text as bytes
        text_bytes = text.encode('utf-8')
        
        # Create a text file for TTS input
        file_id = await file_manager.upload_file(
            text_bytes, 
            "tts_input.txt", 
            "text/plain",
            file_type="tts"
        )
        
        # Get the actual file metadata to get the correct local_path
        file_metadata = await file_manager.get_file_metadata(file_id)
        
        # Create task using enhanced schema
        task_data = {
            'task_type': 'tts',
            'input_file': {
                'file_id': file_id,
                'file_name': "tts_input.txt",
                'file_type': "text/plain",
                'file_size': len(text_bytes),
                'local_path': file_metadata['local_path'] if file_metadata else f"/proxy_server/local_storage/tts_audio/{file_id}",
                'file_url': f"/api/v1/files/{file_id}",
                'checksum': str(hash(text_bytes)),  # Simple hash for now
                'uploaded_at': datetime.now()
            },
            'priority': priority,
            'target_language': target_language,
            'required_miner_count': 3
        }
        
        # Use enhanced database operations
        task_id = DatabaseOperations.create_task(db_manager.get_db(), task_data)
        
        # Track metrics
        system_metrics.increment_tasks()
        
        # Log task creation to wandb
        if wandb_monitor.initialized:
            wandb_monitor.log_task_metrics({
                'task_type': 'tts',
                'task_id': task_id,
                'priority': priority,
                'target_language': target_language,
                'file_id': file_id,
                'created_at': datetime.now().isoformat()
            })
        
        # Start task distribution
        # Note: The workflow orchestrator handles task distribution automatically
        # We don't need to call a specific method here
        
        return {
            "success": True,
            "task_id": task_id,
            "file_id": file_id,
            "message": "TTS task submitted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")

@app.post("/api/v1/summarization")
async def submit_summarization_task(
    text: str = Form(...),
    source_language: str = Form("en"),
    priority: str = Form("normal")
):
    """Submit summarization task"""
    try:
        # Encode text as bytes
        text_bytes = text.encode('utf-8')
        
        # Create a text file for summarization input
        file_id = await file_manager.upload_file(
            text_bytes, 
            "summarization_input.txt", 
            "text/plain",
            file_type="summarization"
        )
        
        # Get the actual file metadata to get the correct local_path
        file_metadata = await file_manager.get_file_metadata(file_id)
        
        # Create task using enhanced schema
        task_data = {
            'task_type': 'summarization',
            'input_file': {
                'file_id': file_id,
                'file_name': "summarization_input.txt",
                'file_type': "text/plain",
                'file_size': len(text_bytes),
                'local_path': file_metadata['local_path'] if file_metadata else f"/proxy_server/local_storage/summarization_files/{file_id}",
                'file_url': f"/api/v1/files/{file_id}",
                'checksum': str(hash(text_bytes)),  # Simple hash for now
                'uploaded_at': datetime.now()
            },
            'priority': priority,
            'source_language': source_language,
            'required_miner_count': 3
        }
        
        # Use enhanced database operations
        task_id = DatabaseOperations.create_task(db_manager.get_db(), task_data)
        
        # Track metrics
        system_metrics.increment_tasks()
        
        # Log task creation to wandb
        if wandb_monitor.initialized:
            wandb_monitor.log_task_metrics({
                'task_type': 'summarization',
                'task_id': task_id,
                'priority': priority,
                'source_language': source_language,
                'file_id': file_id,
                'created_at': datetime.now().isoformat()
            })
        
        # Start task distribution
        # Note: The workflow orchestrator handles task distribution automatically
        # We don't need to call a specific method here
        
        return {
            "success": True,
            "task_id": task_id,
            "file_id": file_id,
            "message": "Summarization task submitted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")

@app.post("/api/v1/miner/response")
async def submit_miner_response(
    task_id: str = Form(...),
    miner_uid: int = Form(...),
    response_data: str = Form(...),
    processing_time: float = Form(...),
    accuracy_score: float = Form(0.0),
    speed_score: float = Form(0.0)
):
    """Submit miner response for a task"""
    try:
        # Validate required parameters
        if not task_id or task_id == "None" or task_id == "null":
            raise HTTPException(status_code=400, detail="Invalid task_id provided")
        
        if not miner_uid or miner_uid <= 0:
            raise HTTPException(status_code=400, detail="Invalid miner_uid provided")
        
        # Parse response data (assuming it's JSON string)
        import json
        try:
            response_data_dict = json.loads(response_data)
        except json.JSONDecodeError:
            response_data_dict = {"output_data": response_data}
        
        # Validate response data structure
        if not response_data_dict:
            raise HTTPException(status_code=400, detail="Empty response data provided")
        
        # Create response payload
        response_payload = {
            'output_data': response_data_dict,
            'processing_time': processing_time,
            'accuracy_score': accuracy_score,
            'speed_score': speed_score
        }
        
        # Log the response submission for debugging
        print(f"📥 Miner {miner_uid} submitting response for task {task_id}")
        print(f"   Processing time: {processing_time}s")
        print(f"   Accuracy score: {accuracy_score}")
        print(f"   Speed score: {speed_score}")
        
        # Handle the response directly with miner_response_handler
        success = await miner_response_handler.handle_miner_response(task_id, miner_uid, response_payload)
        
        if success:
            # Track metrics
            system_metrics.increment_miner_responses()
            
            # Log metrics to wandb
            wandb_monitor.log_task_metrics({
                'task_type': 'miner_response',
                'processing_time': processing_time,
                'accuracy_score': accuracy_score,
                'speed_score': speed_score,
                'miner_uid': miner_uid
            })
            
            # Invalidate cache for this task
            cache.invalidate(f"task_status_{task_id}")
            
            print(f"✅ Miner response for task {task_id} processed successfully")
            
            return {
                "success": True,
                "message": "Miner response submitted successfully",
                "task_id": task_id,
                "miner_uid": miner_uid
            }
        else:
            print(f"❌ Failed to process miner response for task {task_id}")
            raise HTTPException(status_code=500, detail="Failed to process miner response")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in submit_miner_response: {e}")
        print(f"   Task ID: {task_id}")
        print(f"   Miner UID: {miner_uid}")
        raise HTTPException(status_code=500, detail=f"Failed to submit response: {str(e)}")

@app.get("/api/v1/validator/tasks")
async def get_tasks_for_validator(validator_uid: int = None):
    """Get tasks ready for validator evaluation"""
    try:
        print(f"🔍 Validator requesting tasks (validator_uid: {validator_uid})")
        
        # If no validator_uid provided, get all tasks ready for evaluation
        if validator_uid is None:
            tasks = await validator_api.get_tasks_for_evaluation()
        else:
            tasks = await validator_api.get_tasks_for_evaluation(validator_uid)
        
        print(f"✅ Retrieved {len(tasks)} tasks for validator")
        
        # Debug: Log task structure for first few tasks
        for i, task in enumerate(tasks[:3]):  # Log first 3 tasks
            print(f"   Task {i+1}: {task.get('task_id', 'no_id')}")
            print(f"      Type: {task.get('task_type', 'no_type')}")
            print(f"      Status: {task.get('status', 'no_status')}")
            print(f"      Has input_data: {'input_data' in task}")
            print(f"      Has input_file: {'input_file' in task}")
            print(f"      Has input_file_id: {'input_file_id' in task}")
            if 'input_data' in task and task['input_data']:
                print(f"      Input data type: {type(task['input_data']).__name__}")
                if isinstance(task['input_data'], str):
                    print(f"      Input data length: {len(task['input_data'])} chars")
                elif isinstance(task['input_data'], bytes):
                    print(f"      Input data length: {len(task['input_data'])} bytes")
            print()
        
        return {
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        }
        
    except Exception as e:
        print(f"❌ Error in get_tasks_for_validator: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")

@app.post("/api/v1/validator/evaluation")
async def submit_validator_evaluation(
    task_id: str = Form(...),
    validator_uid: int = Form(...),
    evaluation_data: str = Form(...)
):
    """Submit validator evaluation and rewards"""
    try:
        # Parse evaluation JSON
        evaluation_dict = json.loads(evaluation_data)
        
        # Submit evaluation
        await validator_api.submit_validator_evaluation(task_id, validator_uid, evaluation_dict)
        
        return {"success": True, "message": "Evaluation submitted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit evaluation: {str(e)}")

@app.get("/api/v1/task/{task_id}/status")
async def get_task_status(task_id: str):
    """Get comprehensive task status"""
    try:
        # Check cache first
        cache_key = f"task_status_{task_id}"
        cached_result = cache.get(cache_key)
        if cached_result:
            system_metrics.increment_cache_hits()
            return cached_result
        
        # Cache miss - get from database
        system_metrics.increment_cache_misses()
        system_metrics.increment_database_operations()
        
        # Get task from database using enhanced operations
        task_ref = db_manager.get_db().collection(COLLECTIONS['tasks']).document(task_id)
        task_doc = task_ref.get()
        
        if not task_doc.exists:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task_data = task_doc.to_dict()
        
        # Format response
        task_status = {
            'task_id': task_id,
            'status': task_data.get('status'),
            'task_type': task_data.get('task_type'),
            'created_at': task_data.get('created_at'),
            'assigned_miners': task_data.get('assigned_miners', []),
            'miner_responses': len(task_data.get('miner_responses', [])),
            'required_miner_count': task_data.get('required_miner_count', 0)
        }
        
        # Cache the result
        cache.set(cache_key, task_status)
        
        return task_status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Get system metrics
        metrics = system_metrics.get_metrics()
        
        # Check file system health
        file_system_healthy = True
        file_system_errors = []
        
        try:
            # Check if local storage directories exist
            storage_dirs = [
                "proxy_server/local_storage/user_audio",
                "proxy_server/local_storage/tts_audio", 
                "proxy_server/local_storage/transcription_files",
                "proxy_server/local_storage/summarization_files"
            ]
            
            for dir_path in storage_dirs:
                if not os.path.exists(dir_path):
                    file_system_healthy = False
                    file_system_errors.append(f"Directory missing: {dir_path}")
                elif not os.access(dir_path, os.W_OK):
                    file_system_healthy = False
                    file_system_errors.append(f"Directory not writable: {dir_path}")
                    
        except Exception as e:
            file_system_healthy = False
            file_system_errors.append(f"File system check error: {str(e)}")
        
        # Log health check to wandb
        if wandb_monitor.initialized:
            wandb_monitor.log_system_metrics({
                "health_check": True,
                "file_system_healthy": file_system_healthy,
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": metrics["uptime_seconds"],
                "total_requests": metrics["total_requests"],
                "cache_hit_rate": metrics["cache_hit_rate"],
                "error_rate": metrics["errors"] / max(metrics["total_requests"], 1)
            })
        
        health_status = "healthy" if file_system_healthy else "degraded"
        
        return {
            "status": health_status,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": metrics["uptime_seconds"],
            "cache_hit_rate": f"{metrics['cache_hit_rate']:.2%}",
            "requests_per_second": f"{metrics['requests_per_second']:.2f}",
            "wandb_active": wandb_monitor.initialized,
            "file_system": {
                "healthy": file_system_healthy,
                "errors": file_system_errors
            }
        }
        
    except Exception as e:
        # Log error to wandb
        if wandb_monitor.initialized:
            wandb_monitor.log_system_metrics({
                "health_check_error": True,
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/api/v1/files/{file_id}")
async def serve_file(file_id: str):
    """Serve files from local storage"""
    try:
        # Validate file_id parameter
        if not file_id or file_id == "None" or file_id == "null":
            raise HTTPException(status_code=400, detail="Invalid file ID provided")
        
        # Get file metadata
        file_metadata = await file_manager.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
        
        file_path = file_metadata['local_path']
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found on disk: {file_id}")
        
        # Return file with appropriate headers
        return FileResponse(
            path=file_path,
            filename=file_metadata['file_name'],
            media_type=file_metadata['content_type']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving file: {str(e)}")

@app.get("/api/v1/files/{file_id}/download")
async def download_file(file_id: str):
    """Download files from local storage with enhanced error handling"""
    try:
        # Validate file_id parameter
        if not file_id or file_id == "None" or file_id == "null":
            raise HTTPException(
                status_code=400, 
                detail="Invalid file ID provided. File ID cannot be None or null."
            )
        
        # Get file metadata
        file_metadata = await file_manager.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(
                status_code=404, 
                detail=f"File metadata not found for ID: {file_id}"
            )
        
        file_path = file_metadata['local_path']
        
        # Check if file exists on disk
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404, 
                detail=f"File not found on disk for ID: {file_id}. Path: {file_path}"
            )
        
        # Determine content type for proper headers
        content_type = file_metadata.get('content_type', 'application/octet-stream')
        
        # Return file with appropriate headers
        return FileResponse(
            path=file_path,
            filename=file_metadata['file_name'],
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_metadata['file_name']}",
                "Cache-Control": "no-cache"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Log the error for debugging
        print(f"❌ Error in download_file endpoint: {e}")
        print(f"   File ID: {file_id}")
        print(f"   Error type: {type(e).__name__}")
        
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error while downloading file: {str(e)}"
        )

@app.get("/api/v1/files/stats")
async def get_file_stats():
    """Get file storage statistics"""
    try:
        stats = await file_manager.get_storage_statistics()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/api/v1/files/list/{file_type}")
async def list_files_by_type(file_type: str):
    """List files by type"""
    try:
        files = await file_manager.list_files_by_type(file_type)
        return {
            "success": True,
            "file_type": file_type,
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@app.get("/api/v1/transcription/{task_id}/result")
async def get_transcription_result(task_id: str):
    """Get transcription result for a completed task"""
    try:
        # Get task status
        task_status = await workflow_orchestrator.get_task_status(task_id)
        
        if 'error' in task_status:
            raise HTTPException(status_code=404, detail=task_status['error'])
        
        # Check if task is completed
        task_info = task_status.get('task', {})
        if task_info.get('status') not in ['done', 'approved']:
            return {
                "success": False,
                "message": f"Task is still {task_info.get('status')}",
                "status": task_info.get('status')
            }
        
        # Get the best response from completion status
        completion_status = task_status.get('completion_status', {})
        miner_statuses = completion_status.get('miner_statuses', {})
        
        # Find the best response (highest accuracy score)
        best_miner_uid = None
        best_accuracy = 0
        
        for miner_uid, status in miner_statuses.items():
            if status.get('status') == 'completed':
                accuracy = status.get('accuracy_score', 0)
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_miner_uid = miner_uid
        
        if not best_miner_uid:
            return {
                "success": False,
                "message": "No completed responses found"
            }
        
        # Get the best miner's response data
        best_status = miner_statuses[best_miner_uid]
        
        return {
            "success": True,
            "task_id": task_id,
            "status": task_info.get('status'),
            "transcript": f"Transcription from miner {best_miner_uid}: This is a test transcription of the audio file from miner {best_miner_uid}.",
            "processing_time": best_status.get('processing_time', 0),
            "miner_uid": int(best_miner_uid),
            "accuracy_score": best_status.get('accuracy_score', 0),
            "speed_score": best_status.get('speed_score', 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get result: {str(e)}")

@app.get("/api/v1/tts/{task_id}/result")
async def get_tts_result(task_id: str):
    """Get TTS result for a completed task"""
    try:
        # Get task status
        task_status = await workflow_orchestrator.get_task_status(task_id)
        
        if 'error' in task_status:
            raise HTTPException(status_code=404, detail=task_status['error'])
        
        # Check if task is completed
        task_info = task_status.get('task', {})
        if task_info.get('status') not in ['done', 'approved']:
            return {
                "success": False,
                "message": f"Task is still {task_info.get('status')}",
                "status": task_info.get('status')
            }
        
        # Get the best response from completion status
        completion_status = task_status.get('completion_status', {})
        miner_statuses = completion_status.get('miner_statuses', {})
        
        # Find the best response (highest accuracy score)
        best_miner_uid = None
        best_accuracy = 0
        
        for miner_uid, status in miner_statuses.items():
            if status.get('status') == 'completed':
                accuracy = status.get('accuracy_score', 0)
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_miner_uid = miner_uid
        
        if not best_miner_uid:
            return {
                "success": False,
                "message": "No completed responses found"
            }
        
        # Get the best miner's response data
        best_status = miner_statuses[best_miner_uid]
        
        # Get audio file URL if available
        audio_url = f"http://localhost:8000/api/v1/files/tts_audio/{task_id}_{best_miner_uid}.wav"
        
        return {
            "success": True,
            "task_id": task_id,
            "status": task_info.get('status'),
            "audio_url": audio_url,
            "processing_time": best_status.get('processing_time', 0),
            "miner_uid": int(best_miner_uid),
            "accuracy_score": best_status.get('accuracy_score', 0),
            "speed_score": best_status.get('speed_score', 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get result: {str(e)}")

@app.get("/api/v1/miners/performance")
async def get_miner_performance():
    """Get comprehensive miner performance metrics"""
    try:
        # Get all completed tasks
        tasks_collection = workflow_orchestrator.db.collection('tasks')
        completed_tasks = tasks_collection.where('status', 'in', ['done', 'approved']).stream()
        
        miner_stats = {}
        
        for task_doc in completed_tasks:
            task = task_doc.to_dict()
            task_id = task['task_id']
            
            # Get miner responses for this task
            responses_collection = workflow_orchestrator.db.collection('miner_responses')
            responses = responses_collection.where('task_id', '==', task_id).stream()
            
            for response_doc in responses:
                response = response_doc.to_dict()
                miner_uid = response['miner_uid']
                
                if miner_uid not in miner_stats:
                    miner_stats[miner_uid] = {
                        'total_tasks': 0,
                        'completed_tasks': 0,
                        'total_processing_time': 0,
                        'total_accuracy_score': 0,
                        'total_speed_score': 0,
                        'task_types': {},
                        'recent_performance': []
                    }
                
                miner_stats[miner_uid]['total_tasks'] += 1
                miner_stats[miner_uid]['completed_tasks'] += 1
                miner_stats[miner_uid]['total_processing_time'] += response.get('processing_time', 0)
                miner_stats[miner_uid]['total_accuracy_score'] += response.get('accuracy_score', 0)
                miner_stats[miner_uid]['total_speed_score'] += response.get('speed_score', 0)
                
                # Track task types
                task_type = task.get('task_type', 'unknown')
                if task_type not in miner_stats[miner_uid]['task_types']:
                    miner_stats[miner_uid]['task_types'][task_type] = 0
                miner_stats[miner_uid]['task_types'][task_type] += 1
                
                # Track recent performance
                recent_perf = {
                    'task_id': task_id,
                    'task_type': task_type,
                    'processing_time': response.get('processing_time', 0),
                    'accuracy_score': response.get('accuracy_score', 0),
                    'speed_score': response.get('speed_score', 0),
                    'completed_at': response.get('submitted_at')
                }
                miner_stats[miner_uid]['recent_performance'].append(recent_perf)
        
        # Calculate averages and rankings
        for miner_uid, stats in miner_stats.items():
            if stats['completed_tasks'] > 0:
                stats['avg_processing_time'] = stats['total_processing_time'] / stats['completed_tasks']
                stats['avg_accuracy_score'] = stats['total_accuracy_score'] / stats['completed_tasks']
                stats['avg_speed_score'] = stats['total_speed_score'] / stats['completed_tasks']
                
                # Calculate overall performance score
                stats['overall_score'] = (
                    stats['avg_accuracy_score'] * 0.5 + 
                    stats['avg_speed_score'] * 0.3 + 
                    (1.0 / stats['avg_processing_time']) * 0.2
                )
                
                # Keep only last 10 performance records
                stats['recent_performance'] = sorted(
                    stats['recent_performance'], 
                    key=lambda x: x.get('completed_at', ''), 
                    reverse=True
                )[:10]
        
        # Sort miners by overall performance
        sorted_miners = sorted(
            miner_stats.items(), 
            key=lambda x: x[1].get('overall_score', 0), 
            reverse=True
        )
        
        # Log miner performance to wandb
        if wandb_monitor.initialized:
            for miner_uid, stats in miner_stats.items():
                wandb_monitor.log_miner_performance(int(miner_uid), stats)
            
            # Log overall performance summary
            wandb_monitor.log_system_metrics({
                "miner_performance_summary": {
                    "total_miners": len(miner_stats),
                    "top_performer": sorted_miners[0][0] if sorted_miners else None,
                    "avg_completion_rate": sum(s['completed_tasks'] for s in miner_stats.values()) / len(miner_stats) if miner_stats else 0,
                    "total_tasks_processed": sum(s['completed_tasks'] for s in miner_stats.values())
                }
            })
        
        return {
            "success": True,
            "total_miners": len(miner_stats),
            "miners": dict(sorted_miners),
            "performance_summary": {
                "top_performer": sorted_miners[0][0] if sorted_miners else None,
                "avg_completion_rate": sum(s['completed_tasks'] for s in miner_stats.values()) / len(miner_stats) if miner_stats else 0,
                "total_tasks_processed": sum(s['completed_tasks'] for s in miner_stats.values())
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get miner performance: {str(e)}")

@app.get("/api/v1/miners/{miner_uid}/tasks")
async def get_miner_tasks(miner_uid: int, status: str = "assigned"):
    """Get tasks assigned to a specific miner with proper status filtering"""
    try:
        print(f"🔍 Miner {miner_uid} requesting tasks with status: {status}")
        
        # Validate status parameter - miners should only get assigned tasks
        valid_statuses = ["assigned", "pending", "processing"]
        if status not in valid_statuses:
            print(f"⚠️ Invalid status '{status}' requested by miner {miner_uid}. Allowing but logging warning.")
            # Still allow the request but log the warning
        
        # Use enhanced database operations with proper filtering
        tasks = DatabaseOperations.get_miner_tasks(db_manager.get_db(), miner_uid, status)
        
        # Log what we found
        print(f"📋 Found {len(tasks)} tasks for miner {miner_uid} with status '{status}'")
        
        # Additional validation: ensure we're not returning completed tasks to miners
        filtered_tasks = []
        for task in tasks:
            task_status = task.get('status', 'unknown')
            if task_status in ['completed', 'failed', 'cancelled']:
                print(f"⚠️ Filtering out {task_status} task {task.get('task_id')} for miner {miner_uid}")
                continue
            filtered_tasks.append(task)
        
        if len(filtered_tasks) != len(tasks):
            print(f"🔍 Filtered {len(tasks) - len(filtered_tasks)} completed/failed tasks from miner {miner_uid} results")
        
        return filtered_tasks
        
    except Exception as e:
        print(f"❌ Error getting tasks for miner {miner_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting miner tasks: {str(e)}")

@app.get("/api/v1/task/{task_id}/responses")
async def get_task_responses(task_id: str):
    """Get task information including best response and input details (filtered for client use)"""
    try:
        print(f"🔍 Getting filtered task responses for task: {task_id}")
        
        # Get task from database
        task_ref = db_manager.get_db().collection('tasks').document(task_id)
        task_doc = task_ref.get()
        
        if not task_doc.exists:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task_data = task_doc.to_dict()
        
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
                "created_at": task_data.get('created_at'),
                "best_response": {
                    "output_data": best_response.get('response_data', {}).get('output_data', {}) if best_response else {},
                    "processing_time": best_response.get('processing_time', 0) if best_response else 0,
                    "accuracy_score": best_response.get('accuracy_score', 0) if best_response else 0,
                    "speed_score": best_response.get('speed_score', 0) if best_response else 0
                } if best_response else None,
                "task_summary": {
                    "total_responses_received": len(task_data.get('miner_responses', [])),
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
                "created_at": task_data.get('created_at'),
                "best_response": {
                    "response_data": best_response.get('response_data'),
                    "processing_time": best_response.get('processing_time'),
                    "accuracy_score": best_response.get('accuracy_score'),
                    "speed_score": best_response.get('speed_score'),
                    "submitted_at": best_response.get('submitted_at')
                } if best_response else None,
                "task_summary": {
                    "total_responses_received": len(task_data.get('miner_responses', [])),
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
            if 'miner_responses' not in task_data:
                task_data['miner_responses'] = []
            
            tasks.append(task_data)
        
        print(f"✅ Retrieved {len(tasks)} completed tasks for validator evaluation")
        return tasks
        
    except Exception as e:
        print(f"❌ Error getting completed tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get completed tasks: {str(e)}")

@app.get("/api/v1/metrics")
async def get_system_metrics():
    """Get system metrics in Prometheus format for Grafana"""
    try:
        # Get current metrics
        metrics = system_metrics.get_metrics()
        
        # Format for Prometheus/Grafana
        prometheus_metrics = f"""# HELP bittensor_subnet_uptime_seconds Total uptime in seconds
# TYPE bittensor_subnet_uptime_seconds counter
bittensor_subnet_uptime_seconds {metrics['uptime_seconds']}

# HELP bittensor_subnet_total_requests Total number of requests
# TYPE bittensor_subnet_total_requests counter
bittensor_subnet_total_requests {metrics['total_requests']}

# HELP bittensor_subnet_total_tasks Total number of tasks created
# TYPE bittensor_subnet_total_tasks counter
bittensor_subnet_total_tasks {metrics['total_tasks']}

# HELP bittensor_subnet_total_miner_responses Total number of miner responses
# TYPE bittensor_subnet_total_miner_responses counter
bittensor_subnet_total_miner_responses {metrics['total_miner_responses']}

# HELP bittensor_subnet_cache_hits Total cache hits
# TYPE bittensor_subnet_cache_hits counter
bittensor_subnet_cache_hits {metrics['cache_hits']}

# HELP bittensor_subnet_cache_misses Total cache misses
# TYPE bittensor_subnet_cache_misses counter
bittensor_subnet_cache_misses {metrics['cache_misses']}

# HELP bittensor_subnet_cache_hit_rate Cache hit rate percentage
# TYPE bittensor_subnet_cache_hit_rate gauge
bittensor_subnet_cache_hit_rate {metrics['cache_hit_rate']}

# HELP bittensor_subnet_database_operations Total database operations
# TYPE bittensor_subnet_database_operations counter
bittensor_subnet_database_operations {metrics['database_operations']}

# HELP bittensor_subnet_errors Total errors
# TYPE bittensor_subnet_errors counter
bittensor_subnet_errors {metrics['errors']}

# HELP bittensor_subnet_requests_per_second Requests per second
# TYPE bittensor_subnet_requests_per_second gauge
bittensor_subnet_requests_per_second {metrics['requests_per_second']}

# HELP bittensor_subnet_tasks_per_second Tasks per second
# TYPE bittensor_subnet_tasks_per_second gauge
bittensor_subnet_tasks_per_second {metrics['tasks_per_second']}
"""
        
        return Response(content=prometheus_metrics, media_type="text/plain")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@app.get("/api/v1/metrics/json")
async def get_system_metrics_json():
    """Get system metrics in JSON format"""
    try:
        metrics = system_metrics.get_metrics()
        
        # Log to wandb
        wandb_monitor.log_system_metrics(metrics)
        
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "enhanced_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
