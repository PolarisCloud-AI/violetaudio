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
from database.enhanced_schema import (
    TaskStatus, TaskPriority, TaskType, TaskModel, 
    MinerInfo, FileReference, TextContent, COLLECTIONS, DatabaseOperations,
    generate_text_content_id
)
from managers.task_manager import TaskManager
from managers.file_manager import FileManager
from managers.miner_response_handler import MinerResponseHandler
from orchestrators.workflow_orchestrator import WorkflowOrchestrator
from api.validator_integration import ValidatorIntegrationAPI

def create_safe_filename(original_filename: str) -> str:
    """Create a safe filename for storage by removing problematic characters"""
    import re
    # Remove or replace problematic characters
    safe_filename = re.sub(r'[^\w\s\-_.]', '_', original_filename)
    # Replace spaces with underscores
    safe_filename = safe_filename.replace(' ', '_')
    # Ensure it's not empty
    if not safe_filename:
        safe_filename = "unnamed_file"
    return safe_filename

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
from wandb_config import setup_wandb, get_wandb_config

class WandbMonitor:
    def __init__(self, project_name: str = "bittensor-subnet", entity: str = None):
        self.project_name = project_name
        self.entity = entity
        self.run = None
        self.initialized = False
        
        # Setup wandb automatically
        if setup_wandb():
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
        else:
            print("ℹ️  Wandb monitoring disabled - no API key available")
    
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
wandb_monitor = WandbMonitor(project_name="audio-processing-proxy")

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced Audio Processing Proxy Server",
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
        from database.schema import DatabaseManager
        import os
        
        # Try multiple possible paths for the credentials file
        possible_paths = [
            "db/violet.json",  # From project root
            os.path.join(os.path.dirname(__file__), "db", "violet.json")
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
        
        # 🔒 DUPLICATE PROTECTION: Assign components to app.state for endpoint access
        app.state.miner_response_handler = miner_response_handler
        app.state.file_manager = file_manager
        app.state.task_manager = task_manager
        
        # Create and assign task distributor for duplicate protection
        from orchestrators.task_distributor import TaskDistributor
        
        # Create a network-aware miner status manager for the task distributor
        class NetworkMinerStatusManager:
            def __init__(self, db):
                self.db = db
                self.miner_status_collection = db.collection('miner_status')
                self.consensus_collection = db.collection('miner_consensus')
            
            async def get_available_miners(self):
                """Get real miners from Bittensor network via multi-validator consensus"""
                try:
                    # First try to get consensus-based miner status
                    consensus_miners = await self._get_consensus_miners()
                    if consensus_miners:
                        print(f"🔍 Multi-validator consensus: Found {len(consensus_miners)} available miners")
                        return consensus_miners
                    
                    # Fallback to individual validator reports
                    print(f"⚠️ No consensus available, falling back to individual validator reports")
                    return await self._get_fallback_miners()
                    
                except Exception as e:
                    print(f"❌ Error getting network miners: {e}")
                    # Final fallback to basic miner info
                    return [{'uid': 48, 'availability_score': 0.8, 'task_type_specialization': None, 'current_load': 0, 'max_capacity': 5}]
            
            async def _get_consensus_miners(self):
                """Get miners based on multi-validator consensus"""
                try:
                    # Query consensus collection
                    docs = self.consensus_collection.stream()
                    
                    consensus_miners = []
                    for doc in docs:
                        consensus_data = doc.to_dict()
                        consensus_status = consensus_data.get('consensus_status', {})
                        
                        # Only include miners with high consensus confidence
                        consensus_confidence = consensus_data.get('consensus_confidence', 0.0)
                        if consensus_confidence < 0.7:  # Minimum confidence threshold
                            continue
                        
                        if consensus_status.get('is_serving') and consensus_status.get('stake', 0) > 0:
                            # Calculate availability score based on consensus data
                            performance_score = consensus_status.get('performance_score', 0.5)
                            stake = float(consensus_status.get('stake', 0))
                            current_load = consensus_status.get('current_load', 0)
                            max_capacity = consensus_status.get('max_capacity', 5)
                            
                            # Boost score for high consensus confidence
                            consensus_boost = consensus_confidence * 0.2
                            
                            # Calculate availability score (0.0 to 1.0)
                            availability_score = min(1.0, max(0.1, 
                                performance_score * (1 - current_load/max_capacity) + consensus_boost))
                            
                            consensus_miners.append({
                                'uid': consensus_status['uid'],
                                'hotkey': consensus_status.get('hotkey', 'unknown'),
                                'stake': stake,
                                'availability_score': availability_score,
                                'task_type_specialization': consensus_status.get('task_type_specialization'),
                                'current_load': current_load,
                                'max_capacity': max_capacity,
                                'performance_score': performance_score,
                                'ip': consensus_status.get('ip'),
                                'port': consensus_status.get('port'),
                                'consensus_confidence': consensus_confidence,
                                'consensus_validators': consensus_status.get('consensus_validators', [])
                            })
                    
                    # Sort by availability score (higher is better)
                    consensus_miners.sort(key=lambda x: x['availability_score'], reverse=True)
                    
                    # Log top miners with consensus info
                    for miner in consensus_miners[:5]:
                        print(f"   Miner {miner['uid']}: consensus={miner['consensus_confidence']:.3f}, score={miner['availability_score']:.3f}, load={miner['current_load']}/{miner['max_capacity']}, stake={miner['stake']:.2f}")
                    
                    return consensus_miners
                    
                except Exception as e:
                    print(f"❌ Error getting consensus miners: {e}")
                    return []
            
            async def _get_fallback_miners(self):
                """Fallback to individual validator reports"""
                try:
                    # Query miner status collection (populated by validators)
                    query = self.miner_status_collection.where('is_serving', '==', True)
                    docs = query.stream()
                    
                    available_miners = []
                    for doc in docs:
                        miner_data = doc.to_dict()
                        if miner_data.get('is_serving') and miner_data.get('stake', 0) > 0:
                            # Calculate availability score based on performance and stake
                            performance_score = miner_data.get('performance_score', 0.5)
                            stake = float(miner_data.get('stake', 0))
                            current_load = miner_data.get('current_load', 0)
                            max_capacity = miner_data.get('max_capacity', 5)
                            
                            # Calculate availability score (0.0 to 1.0)
                            availability_score = min(1.0, max(0.1, performance_score * (1 - current_load/max_capacity)))
                            
                            available_miners.append({
                                'uid': miner_data['uid'],
                                'hotkey': miner_data.get('hotkey', 'unknown'),
                                'stake': stake,
                                'availability_score': availability_score,
                                'task_type_specialization': miner_data.get('task_type_specialization'),
                                'current_load': current_load,
                                'max_capacity': max_capacity,
                                'performance_score': performance_score,
                                'ip': miner_data.get('ip'),
                                'port': miner_data.get('port'),
                                'consensus_confidence': 0.0,  # No consensus
                                'consensus_validators': [miner_data.get('reported_by_validator', 'unknown')]
                            })
                    
                    # Sort by availability score (higher is better)
                    available_miners.sort(key=lambda x: x['availability_score'], reverse=True)
                    
                    print(f"🔍 Fallback miner discovery: Found {len(available_miners)} available miners")
                    for miner in available_miners[:5]:  # Log top 5
                        print(f"   Miner {miner['uid']}: score={miner['availability_score']:.3f}, load={miner['current_load']}/{miner['max_capacity']}, stake={miner['stake']:.2f}")
                    
                    return available_miners
                    
                except Exception as e:
                    print(f"❌ Error getting fallback miners: {e}")
                    return []
        
        # Initialize multi-validator manager for consensus-based miner status
        from managers.multi_validator_manager import MultiValidatorManager
        app.state.multi_validator_manager = MultiValidatorManager(db_manager.get_db())
        
        app.state.miner_status_manager = NetworkMinerStatusManager(db_manager.get_db())
        app.state.task_distributor = TaskDistributor(
            db_manager.get_db(), 
            task_manager, 
            app.state.miner_status_manager
        )
        
        print("🔒 Duplicate protection components assigned to app.state")
        print("🌐 Network-aware miner status manager initialized")
        
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
        
        # Create a safe filename for storage
        safe_filename = create_safe_filename(audio_file.filename)
        
        # Upload file to local storage with transcription type
        file_id = await file_manager.upload_file(
            file_data, 
            safe_filename,  # Use safe filename for storage
            audio_file.content_type,
            file_type="transcription"
        )
        
        # Get the actual file metadata to get the correct path
        file_metadata = await file_manager.get_file_metadata(file_id)
        
        # Determine the correct path based on storage type
        if file_metadata and file_metadata.get('stored_in_cloud', False):
            # File is stored in Firebase Cloud Storage
            file_path = file_metadata.get('cloud_path', f"user_audio/{file_id}")
            storage_location = "cloud_storage"
        else:
            # File is stored in Firestore (small files)
            file_path = f"firestore/{file_id}"
            storage_location = "firestore"
        
        # Create task using enhanced schema
        task_data = {
            'task_type': 'transcription',
            'input_file': {
                'file_id': file_id,
                'file_name': audio_file.filename,  # Keep original filename for display
                'file_type': audio_file.content_type,
                'file_size': len(file_data),
                'local_path': file_path,
                'file_url': f"/api/v1/files/{file_id}",
                'checksum': str(hash(file_data)),  # Simple hash for now
                'uploaded_at': datetime.now(),
                'storage_location': storage_location
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
    source_language: str = Form("en"),
    priority: str = Form("normal")
):
    """Submit text-to-speech task with text stored directly in database"""
    try:
        # Validate text length
        if len(text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Text too short for TTS (min 10 characters)")
        
        # Use the source language provided by the user
        detected_language = source_language
        language_confidence = 1.0
        
        # Create text content object
        text_content = {
            'content_id': generate_text_content_id(),
            'text': text.strip(),
            'source_language': detected_language,
            'detected_language': detected_language,
            'language_confidence': language_confidence,
            'text_length': len(text),
            'word_count': len(text.split()),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'metadata': {
                'original_source_language': source_language,
                'detection_method': 'manual'
            }
        }
        
        # Create task data
        task_data = {
            'task_type': 'tts',
            'input_text': text_content,
            'priority': priority,
            'source_language': detected_language,
            'required_miner_count': 3
        }
        
        # Create task in database
        task_id = DatabaseOperations.create_task(db_manager.get_db(), task_data)
        
        # Auto-assign task to available miners
        assignment_success = DatabaseOperations.auto_assign_task(
            db_manager.get_db(),
            task_id,
            'tts',
            task_data.get('required_miner_count', 3)
        )
        
        if assignment_success:
            print(f"✅ Task {task_id} automatically assigned to miners")
        else:
            print(f"⚠️ Task {task_id} created but could not be assigned to miners")
        
        # Track metrics
        system_metrics.increment_tasks()
        
        # Log task creation to wandb
        if wandb_monitor.initialized:
            wandb_monitor.log_task_metrics({
                'task_type': 'tts',
                'task_id': task_id,
                'priority': priority,
                'source_language': detected_language,
                'detected_language': detected_language,
                'language_confidence': language_confidence,
                'text_length': len(text),
                'word_count': len(text.split()),
                'created_at': datetime.now().isoformat(),
                'auto_assigned': assignment_success
            })
        
        return {
            "success": True,
            "task_id": task_id,
            "text_content_id": text_content['content_id'],
            "detected_language": detected_language,
            "language_confidence": language_confidence,
            "text_length": len(text),
            "word_count": len(text.split()),
            "auto_assigned": assignment_success,
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
    """Submit summarization task with text stored directly in database"""
    try:
        # Validate text length
        if len(text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Text too short for summarization (min 50 characters)")
        
        # Use the source language provided by the user
        detected_language = source_language
        language_confidence = 1.0
        
        # Create text content object
        text_content = {
            'content_id': generate_text_content_id(),
            'text': text.strip(),
            'source_language': detected_language,
            'detected_language': detected_language,
            'language_confidence': language_confidence,
            'text_length': len(text),
            'word_count': len(text.split()),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'metadata': {
                'original_source_language': source_language,
                'detection_method': 'auto' if source_language == "auto" else 'manual'
            }
        }
        
        # Create task using enhanced schema with text content
        task_data = {
            'task_type': 'summarization',
            'input_text': text_content,
            'priority': priority,
            'source_language': detected_language,
            'required_miner_count': 3
        }
        
        # Use enhanced database operations
        task_id = DatabaseOperations.create_task(db_manager.get_db(), task_data)
        
        # Automatically assign task to available miners
        assignment_success = DatabaseOperations.auto_assign_task(
            db_manager.get_db(), 
            task_id, 
            'summarization', 
            task_data.get('required_miner_count', 3)
        )
        
        if assignment_success:
            print(f"✅ Task {task_id} automatically assigned to miners")
        else:
            print(f"⚠️ Task {task_id} created but could not be assigned to miners")
        
        # Track metrics
        system_metrics.increment_tasks()
        
        # Log task creation to wandb
        if wandb_monitor.initialized:
            wandb_monitor.log_task_metrics({
                'task_type': 'summarization',
                'task_id': task_id,
                'priority': priority,
                'source_language': detected_language,
                'detected_language': detected_language,
                'language_confidence': language_confidence,
                'text_length': len(text),
                'word_count': len(text.split()),
                'created_at': datetime.now().isoformat(),
                'auto_assigned': assignment_success
            })
        
        return {
            "success": True,
            "task_id": task_id,
            "text_content_id": text_content['content_id'],
            "detected_language": detected_language,
            "language_confidence": language_confidence,
            "text_length": len(text),
            "word_count": len(text.split()),
            "auto_assigned": assignment_success,
            "message": "Summarization task submitted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")

@app.post("/api/v1/video-transcription")
async def submit_video_transcription_task(
    video_file: UploadFile = File(...),
    source_language: str = Form("en"),
    priority: str = Form("normal")
):
    """Submit video transcription task - miner will extract audio and transcribe"""
    try:
        # Validate file type
        if not video_file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="File must be a video file")
        
        # Validate file size (max 100MB for video files)
        file_data = await video_file.read()
        if len(file_data) > 100 * 1024 * 1024:  # 100MB
            raise HTTPException(status_code=400, detail="Video file too large (max 100MB)")
        
        # Create a safe filename for storage
        safe_filename = create_safe_filename(video_file.filename)
        
        # Upload video file to local storage with safe filename
        file_id = await file_manager.upload_file(
            file_data, 
            safe_filename,  # Use safe filename for storage
            video_file.content_type,
            file_type="video_transcription"
        )
        
        # Get the actual file metadata to get the correct path
        file_metadata = await file_manager.get_file_metadata(file_id)
        
        # Determine the correct path based on storage type
        if file_metadata and file_metadata.get('stored_in_cloud', False):
            # File is stored in Firebase Cloud Storage
            file_path = file_metadata.get('cloud_path', f"user_videos/{file_id}")
            storage_location = "cloud_storage"
        else:
            # File is stored in Firestore (small files)
            file_path = f"firestore/{file_id}"
            storage_location = "firestore"
        
        # Create task using enhanced schema
        task_data = {
            'task_type': 'video_transcription',
            'input_file': {
                'file_id': file_id,
                'file_name': video_file.filename,  # Keep original filename for display
                'file_type': video_file.content_type,
                'file_size': len(file_data),
                'local_path': file_path,
                'file_url': f"/api/v1/files/{file_id}",
                'checksum': str(hash(file_data)),  # Simple hash for now
                'uploaded_at': datetime.now(),
                'storage_location': storage_location
            },
            'priority': priority,
            'source_language': source_language,
            'required_miner_count': 3
        }
        
        # Use enhanced database operations
        task_id = DatabaseOperations.create_task(db_manager.get_db(), task_data)
        
        # Automatically assign task to available miners
        assignment_success = DatabaseOperations.auto_assign_task(
            db_manager.get_db(), 
            task_id, 
            'video_transcription', 
            task_data.get('required_miner_count', 3)
        )
        
        if assignment_success:
            print(f"✅ Video transcription task {task_id} automatically assigned to miners")
        else:
            print(f"⚠️ Video transcription task {task_id} created but could not be assigned to miners")
        
        # Track metrics
        system_metrics.increment_tasks()
        
        # Log task creation to wandb
        if wandb_monitor.initialized:
            wandb_monitor.log_task_metrics({
                'task_type': 'video_transcription',
                'task_id': task_id,
                'priority': priority,
                'source_language': source_language,
                'file_id': file_id,
                'file_size': len(file_data),
                'created_at': datetime.now().isoformat(),
                'auto_assigned': assignment_success
            })
        
        return {
            "success": True,
            "task_id": task_id,
            "file_id": file_id,
            "file_name": video_file.filename,
            "file_size": len(file_data),
            "source_language": source_language,
            "auto_assigned": assignment_success,
            "message": "Video transcription task submitted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit video transcription task: {str(e)}")

@app.post("/api/v1/text-translation")
async def submit_text_translation_task(
    text: str = Form(...),
    source_language: str = Form(...),
    target_language: str = Form(...),
    priority: str = Form("normal")
):
    """Submit text translation task with text stored directly in database"""
    try:
        # Validate text length
        if len(text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Text too short for translation (min 10 characters)")
        
        # Validate language codes
        if source_language == target_language:
            raise HTTPException(status_code=400, detail="Source and target languages must be different")
        
        # Create text content object
        text_content = {
            'content_id': generate_text_content_id(),
            'text': text.strip(),
            'source_language': source_language,
            'target_language': target_language,
            'text_length': len(text),
            'word_count': len(text.split()),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'metadata': {
                'translation_type': 'text',
                'source_language': source_language,
                'target_language': target_language
            }
        }
        
        # Create task data
        task_data = {
            'task_type': 'text_translation',
            'input_text': text_content,
            'priority': priority,
            'source_language': source_language,
            'target_language': target_language,
            'required_miner_count': 3
        }
        
        # Create task in database
        task_id = DatabaseOperations.create_task(db_manager.get_db(), task_data)
        
        # Auto-assign task to available miners
        assignment_success = DatabaseOperations.auto_assign_task(
            db_manager.get_db(), 
            task_id, 
            'text_translation', 
            task_data.get('required_miner_count', 3)
        )
        
        if assignment_success:
            print(f"✅ Text translation task {task_id} automatically assigned to miners")
        else:
            print(f"⚠️ Text translation task {task_id} created but could not be assigned to miners")
        
        # Track metrics
        system_metrics.increment_tasks()
        
        # Log task creation to wandb
        if wandb_monitor.initialized:
            wandb_monitor.log_task_metrics({
                'task_type': 'text_translation',
                'task_id': task_id,
                'priority': priority,
                'source_language': source_language,
                'target_language': target_language,
                'text_length': len(text),
                'word_count': len(text.split()),
                'created_at': datetime.now().isoformat(),
                'auto_assigned': assignment_success
            })
        
        return {
            "success": True,
            "task_id": task_id,
            "text_content_id": text_content['content_id'],
            "source_language": source_language,
            "target_language": target_language,
            "text_length": len(text),
            "word_count": len(text.split()),
            "auto_assigned": assignment_success,
            "message": "Text translation task submitted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit text translation task: {str(e)}")

@app.post("/api/v1/document-translation")
async def submit_document_translation_task(
    document_file: UploadFile = File(...),
    source_language: str = Form(...),
    target_language: str = Form(...),
    priority: str = Form("normal")
):
    """Submit document translation task - miner will extract text and translate"""
    try:
        # Validate file type
        file_extension = document_file.filename.lower().split('.')[-1]
        supported_formats = ['pdf', 'docx', 'txt', 'text']
        
        if file_extension not in supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Supported formats: {', '.join(supported_formats)}"
            )
        
        # Validate language codes
        if source_language == target_language:
            raise HTTPException(status_code=400, detail="Source and target languages must be different")
        
        # Validate file size (max 50MB for documents)
        file_data = await document_file.read()
        if len(file_data) > 50 * 1024 * 1024:  # 50MB
            raise HTTPException(status_code=400, detail="Document file too large (max 50MB)")
        
        # Create a safe filename for storage
        safe_filename = create_safe_filename(document_file.filename)
        
        # Upload document file to local storage
        file_id = await file_manager.upload_file(
            file_data, 
            safe_filename,  # Use safe filename for storage
            document_file.content_type,
            file_type="document_translation"
        )
        
        # Get the actual file metadata to get the correct path
        file_metadata = await file_manager.get_file_metadata(file_id)
        
        # Determine the correct path based on storage type
        if file_metadata and file_metadata.get('stored_in_cloud', False):
            # File is stored in Firebase Cloud Storage
            file_path = file_metadata.get('cloud_path', f"user_documents/{file_id}")
            storage_location = "cloud_storage"
        else:
            # File is stored in Firestore (small files)
            file_path = f"firestore/{file_id}"
            storage_location = "firestore"
        
        # Create task using enhanced schema
        task_data = {
            'task_type': 'document_translation',
            'input_file': {
                'file_id': file_id,
                'file_name': document_file.filename,  # Keep original filename for display
                'file_type': document_file.content_type,
                'file_size': len(file_data),
                'local_path': file_path,
                'file_url': f"/api/v1/files/{file_id}",
                'checksum': str(hash(file_data)),  # Simple hash for now
                'uploaded_at': datetime.now(),
                'storage_location': storage_location
            },
            'priority': priority,
            'source_language': source_language,
            'target_language': target_language,
            'required_miner_count': 3
        }
        
        # Use enhanced database operations
        task_id = DatabaseOperations.create_task(db_manager.get_db(), task_data)
        
        # Automatically assign task to available miners
        assignment_success = DatabaseOperations.auto_assign_task(
            db_manager.get_db(), 
            task_id, 
            'document_translation', 
            task_data.get('required_miner_count', 3)
        )
        
        if assignment_success:
            print(f"✅ Document translation task {task_id} automatically assigned to miners")
        else:
            print(f"⚠️ Document translation task {task_id} created but could not be assigned to miners")
        
        # Track metrics
        system_metrics.increment_tasks()
        
        # Log task creation to wandb
        if wandb_monitor.initialized:
            wandb_monitor.log_task_metrics({
                'task_type': 'document_translation',
                'task_id': task_id,
                'priority': priority,
                'source_language': source_language,
                'target_language': target_language,
                'file_id': file_id,
                'file_size': len(file_data),
                'file_format': file_extension,
                'created_at': datetime.now().isoformat(),
                'auto_assigned': assignment_success
            })
        
        return {
            "success": True,
            "task_id": task_id,
            "file_id": file_id,
            "file_name": document_file.filename,
            "file_size": len(file_data),
            "file_format": file_extension,
            "source_language": source_language,
            "target_language": target_language,
            "auto_assigned": assignment_success,
            "message": "Document translation task submitted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit document translation task: {str(e)}")

@app.get("/api/v1/miner/summarization/{task_id}")
async def get_summarization_task_content(task_id: str):
    """Get summarization task text content for miners"""
    try:
        # Get task from database
        task = DatabaseOperations.get_task(db_manager.get_db(), task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.get('task_type') != 'summarization':
            raise HTTPException(status_code=400, detail="Task is not a summarization task")
        
        # Get text content
        if 'input_text' in task and task['input_text']:
            text_content = task['input_text']
        elif 'input_file' in task and task['input_file']:
            # Fallback to file-based approach
            file_id = task['input_file']['file_id']
            file_content = await file_manager.get_file_content(file_id)
            if file_content:
                text_content = {
                    'text': file_content.decode('utf-8'),
                    'source_language': task.get('source_language', 'en'),
                    'detected_language': task.get('source_language', 'en'),
                    'language_confidence': 1.0
                }
            else:
                raise HTTPException(status_code=404, detail="Text content not found")
        else:
            raise HTTPException(status_code=404, detail="No input content found for task")
        
        return {
            "success": True,
            "task_id": task_id,
            "text_content": text_content,
            "task_metadata": {
                "priority": task.get('priority'),
                "source_language": task.get('source_language', 'en'),
                "required_miner_count": task.get('required_miner_count', 1)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task content: {str(e)}")

@app.get("/api/v1/miner/tts/{task_id}")
async def get_tts_task_content(task_id: str):
    """Get TTS task text content for miners"""
    try:
        # Get task from database
        task = DatabaseOperations.get_task(db_manager.get_db(), task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.get('task_type') != 'tts':
            raise HTTPException(status_code=400, detail="Task is not a TTS task")
        
        # Get text content
        if 'input_text' in task and task['input_text']:
            text_content = task['input_text']
        elif 'input_file' in task and task['input_file']:
            # Fallback to file-based approach
            file_id = task['input_file']['file_id']
            file_content = await file_manager.get_file_content(file_id)
            if file_content:
                text_content = {
                    'text': file_content.decode('utf-8'),
                    'source_language': task.get('source_language', 'en'),
                    'detected_language': task.get('source_language', 'en'),
                    'language_confidence': 1.0
                }
            else:
                raise HTTPException(status_code=404, detail="Text content not found")
        else:
            raise HTTPException(status_code=404, detail="No input content found for task")
        
        return {
            "success": True,
            "task_id": task_id,
            "text_content": text_content,
            "task_metadata": {
                "priority": task.get("priority"),
                "source_language": task.get("source_language", "en"),
                "required_miner_count": task.get("required_miner_count", 1)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task content: {str(e)}")

@app.get("/api/v1/miner/video-transcription/{task_id}")
async def get_video_transcription_task_content(task_id: str):
    """Get video transcription task file content for miners"""
    try:
        # Get task from database
        task = DatabaseOperations.get_task(db_manager.get_db(), task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.get('task_type') != 'video_transcription':
            raise HTTPException(status_code=400, detail="Task is not a video transcription task")
        
        # Get file content
        if 'input_file' in task and task['input_file']:
            file_id = task['input_file']['file_id']
            file_content = await file_manager.get_file_content(file_id)
            if file_content:
                return {
                    "success": True,
                    "task_id": task_id,
                    "file_content": file_content,
                    "file_metadata": task['input_file'],
                    "task_metadata": {
                        "priority": task.get("priority"),
                        "source_language": task.get("source_language", "en"),
                        "required_miner_count": task.get("required_miner_count", 1)
                    }
                }
            else:
                raise HTTPException(status_code=404, detail="Video file content not found")
        else:
            raise HTTPException(status_code=404, detail="No input file found for video transcription task")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get video transcription task content: {str(e)}")

@app.get("/api/v1/miner/text-translation/{task_id}")
async def get_text_translation_task_content(task_id: str):
    """Get text translation task text content for miners"""
    try:
        # Get task from database
        task = DatabaseOperations.get_task(db_manager.get_db(), task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.get('task_type') != 'text_translation':
            raise HTTPException(status_code=400, detail="Task is not a text translation task")
        
        # Get text content
        if 'input_text' in task and task['input_text']:
            text_content = task['input_text']
        else:
            raise HTTPException(status_code=404, detail="No input text found for text translation task")
        
        return {
            "success": True,
            "task_id": task_id,
            "text_content": text_content,
            "task_metadata": {
                "priority": task.get("priority"),
                "source_language": task.get("source_language", "en"),
                "target_language": task.get("target_language", "es"),
                "required_miner_count": task.get("required_miner_count", 1)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get text translation task content: {str(e)}")

@app.get("/api/v1/miner/document-translation/{task_id}")
async def get_document_translation_task_content(task_id: str):
    """Get document translation task file content for miners"""
    try:
        # Get task from database
        task = DatabaseOperations.get_task(db_manager.get_db(), task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.get('task_type') != 'document_translation':
            raise HTTPException(status_code=400, detail="Task is not a document translation task")
        
        # Get file content
        if 'input_file' in task and task['input_file']:
            file_id = task['input_file']['file_id']
            file_content = await file_manager.get_file_content(file_id)
            if file_content:
                return {
                    "success": True,
                    "task_id": task_id,
                    "file_content": file_content,
                    "file_metadata": task['input_file'],
                    "task_metadata": {
                        "priority": task.get("priority"),
                        "source_language": task.get("source_language", "en"),
                        "target_language": task.get("target_language", "es"),
                        "required_miner_count": task.get("required_miner_count", 1)
                    }
                }
            else:
                raise HTTPException(status_code=404, detail="Document file content not found")
        else:
            raise HTTPException(status_code=404, detail="No input file found for document translation task")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document translation task content: {str(e)}")

@app.post("/api/v1/miner/tts/upload-audio")
async def upload_tts_audio(
    task_id: str = Form(...),
    miner_uid: int = Form(...),
    audio_file: UploadFile = File(...),
    processing_time: float = Form(...),
    accuracy_score: float = Form(0.0),
    speed_score: float = Form(0.0)
):
    """Upload TTS audio file generated by miner"""
    try:
        # Validate required parameters
        if not task_id or task_id == "None" or task_id == "null":
            raise HTTPException(status_code=400, detail="Invalid task_id provided")
        
        if not miner_uid or miner_uid <= 0:
            raise HTTPException(status_code=400, detail="Invalid miner_uid provided")
        
        # Validate audio file
        if not audio_file.filename or not audio_file.filename.endswith('.wav'):
            raise HTTPException(status_code=400, detail="Audio file must be a .wav file")
        
        # Read audio file content
        audio_content = await audio_file.read()
        if len(audio_content) == 0:
            raise HTTPException(status_code=400, detail="Audio file is empty")
        
        # Generate unique filename
        import uuid
        audio_filename = f"{task_id}_{miner_uid}_{uuid.uuid4().hex[:8]}.wav"
        
        # Store audio file in Firebase Cloud Storage
        file_id = await file_manager.upload_file(
            audio_content,
            audio_filename,
            "audio/wav",
            file_type="tts"
        )
        
        # Get file metadata
        file_metadata = await file_manager.get_file_metadata(file_id)
        
        # Create file reference
        file_reference = {
            'file_id': file_id,
            'file_name': audio_filename,
            'file_type': 'audio/wav',
            'file_size': len(audio_content),
            'local_path': file_metadata.get('cloud_path', f"tts_audio/{file_id}") if file_metadata else f"tts_audio/{file_id}",
            'file_url': f"/api/v1/tts/audio/{file_id}",
            'checksum': str(hash(audio_content)),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'storage_location': 'cloud_storage'
        }
        
        # Create response data with audio file info
        response_data = {
            'output_data': {
                'audio_file': file_reference,
                'audio_duration': 0.0,  # Will be calculated by validator
                'sample_rate': 22050,   # Default, will be verified by validator
                'bit_depth': 16,        # Default, will be verified by validator
                'channels': 1           # Default, will be verified by validator
            },
            'processing_time': processing_time,
            'accuracy_score': accuracy_score,
            'speed_score': speed_score
        }
        
        # Submit the response
        success = await miner_response_handler.handle_miner_response(task_id, miner_uid, response_data)
        
        if success:
            print(f"✅ TTS audio uploaded successfully for task {task_id} by miner {miner_uid}")
            print(f"   Audio file: {audio_filename}")
            print(f"   File size: {len(audio_content)} bytes")
            print(f"   File ID: {file_id}")
            
            return {
                "success": True,
                "message": "TTS audio uploaded successfully",
                "task_id": task_id,
                "miner_uid": miner_uid,
                "audio_file": file_reference,
                "file_url": f"/api/v1/tts/audio/{file_id}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process TTS response")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error uploading TTS audio: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload audio: {str(e)}")

@app.get("/api/v1/tts/audio/{file_id}")
async def get_tts_audio(file_id: str):
    """Serve TTS audio files from Firebase Cloud Storage"""
    try:
        # Get file from Firebase Cloud Storage
        file_content = await file_manager.download_file(file_id)
        
        if not file_content:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Get file metadata
        file_metadata = await file_manager.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="Audio file metadata not found")
        
        filename = file_metadata.get('file_name', f"{file_id}.wav")
        
        # Handle Unicode filenames properly
        safe_filename = urllib.parse.quote(filename)
        
        # Return audio file as streaming response
        return StreamingResponse(
            iter([file_content]),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}",
                "Cache-Control": "no-cache"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error serving TTS audio: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to serve audio: {str(e)}")

@app.post("/api/v1/miner/video-transcription/upload-result")
async def upload_video_transcription_result(
    task_id: str = Form(...),
    miner_uid: int = Form(...),
    transcript: str = Form(...),
    processing_time: float = Form(...),
    accuracy_score: float = Form(0.0),
    speed_score: float = Form(0.0),
    confidence: float = Form(0.0),
    language: str = Form("en")
):
    """Upload video transcription result from miner"""
    try:
        # Validate required parameters
        if not task_id or task_id == "None" or task_id == "null":
            raise HTTPException(status_code=400, detail="Invalid task_id provided")
        
        if not miner_uid or miner_uid <= 0:
            raise HTTPException(status_code=400, detail="Invalid miner_uid provided")
        
        if not transcript or transcript.strip() == "":
            raise HTTPException(status_code=400, detail="Transcript cannot be empty")
        
        # Create response data
        response_data = {
            'output_data': {
                'transcript': transcript.strip(),
                'confidence': confidence,
                'processing_time': processing_time,
                'language': language
            },
            'processing_time': processing_time,
            'accuracy_score': accuracy_score,
            'speed_score': speed_score
        }
        
        # Log the response submission for debugging
        print(f"📥 Miner {miner_uid} submitting video transcription result for task {task_id}")
        print(f"   Transcript length: {len(transcript)} characters")
        print(f"   Processing time: {processing_time}s")
        print(f"   Confidence: {confidence}")
        print(f"   Language: {language}")
        
        # Handle the response with miner_response_handler
        success = await miner_response_handler.handle_miner_response(task_id, miner_uid, response_data)
        
        if success:
            print(f"✅ Video transcription result uploaded successfully for task {task_id} by miner {miner_uid}")
            return {
                "success": True,
                "message": "Video transcription result uploaded successfully",
                "task_id": task_id,
                "miner_uid": miner_uid,
                "transcript_length": len(transcript),
                "confidence": confidence,
                "language": language
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process video transcription response")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error uploading video transcription result: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload result: {str(e)}")

@app.post("/api/v1/miner/text-translation/upload-result")
async def upload_text_translation_result(
    task_id: str = Form(...),
    miner_uid: int = Form(...),
    translated_text: str = Form(...),
    processing_time: float = Form(...),
    accuracy_score: float = Form(0.0),
    speed_score: float = Form(0.0),
    source_language: str = Form(...),
    target_language: str = Form(...)
):
    """Upload text translation result from miner"""
    try:
        # Validate required parameters
        if not task_id or task_id == "None" or task_id == "null":
            raise HTTPException(status_code=400, detail="Invalid task_id provided")
        
        if not miner_uid or miner_uid <= 0:
            raise HTTPException(status_code=400, detail="Invalid miner_uid provided")
        
        if not translated_text or translated_text.strip() == "":
            raise HTTPException(status_code=400, detail="Translated text cannot be empty")
        
        # Create response data
        response_data = {
            'output_data': {
                'translated_text': translated_text.strip(),
                'source_language': source_language,
                'target_language': target_language,
                'processing_time': processing_time
            },
            'processing_time': processing_time,
            'accuracy_score': accuracy_score,
            'speed_score': speed_score
        }
        
        # Log the response submission for debugging
        print(f"📥 Miner {miner_uid} submitting text translation result for task {task_id}")
        print(f"   Translated text length: {len(translated_text)} characters")
        print(f"   Processing time: {processing_time}s")
        print(f"   From {source_language} to {target_language}")
        
        # Handle the response with miner_response_handler
        success = await miner_response_handler.handle_miner_response(task_id, miner_uid, response_data)
        
        if success:
            print(f"✅ Text translation result uploaded successfully for task {task_id} by miner {miner_uid}")
            return {
                "success": True,
                "message": "Text translation result uploaded successfully",
                "task_id": task_id,
                "miner_uid": miner_uid,
                "translated_text_length": len(translated_text),
                "source_language": source_language,
                "target_language": target_language
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process text translation response")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error uploading text translation result: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload result: {str(e)}")

@app.post("/api/v1/miner/document-translation/upload-result")
async def upload_document_translation_result(
    task_id: str = Form(...),
    miner_uid: int = Form(...),
    translated_text: str = Form(...),
    processing_time: float = Form(...),
    accuracy_score: float = Form(0.0),
    speed_score: float = Form(0.0),
    source_language: str = Form(...),
    target_language: str = Form(...),
    metadata: str = Form("{}")
):
    """Upload document translation result from miner"""
    try:
        # Validate required parameters
        if not task_id or task_id == "None" or task_id == "null":
            raise HTTPException(status_code=400, detail="Invalid task_id provided")
        
        if not miner_uid or miner_uid <= 0:
            raise HTTPException(status_code=400, detail="Invalid miner_uid provided")
        
        if not translated_text or translated_text.strip() == "":
            raise HTTPException(status_code=400, detail="Translated text cannot be empty")
        
        # Parse metadata if provided
        import json
        try:
            metadata_dict = json.loads(metadata) if metadata else {}
        except json.JSONDecodeError:
            metadata_dict = {}
        
        # Create response data
        response_data = {
            'output_data': {
                'translated_text': translated_text.strip(),
                'source_language': source_language,
                'target_language': target_language,
                'processing_time': processing_time,
                'metadata': metadata_dict
            },
            'processing_time': processing_time,
            'accuracy_score': accuracy_score,
            'speed_score': speed_score
        }
        
        # Log the response submission for debugging
        print(f"📥 Miner {miner_uid} submitting document translation result for task {task_id}")
        print(f"   Translated text length: {len(translated_text)} characters")
        print(f"   Processing time: {processing_time}s")
        print(f"   From {source_language} to {target_language}")
        
        # Handle the response with miner_response_handler
        success = await miner_response_handler.handle_miner_response(task_id, miner_uid, response_data)
        
        if success:
            print(f"✅ Document translation result uploaded successfully for task {task_id} by miner {miner_uid}")
            return {
                "success": True,
                "message": "Document translation result uploaded successfully",
                "task_id": task_id,
                "miner_uid": miner_uid,
                "translated_text_length": len(translated_text),
                "source_language": source_language,
                "target_language": target_language,
                "metadata": metadata_dict
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process document translation response")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error uploading document translation result: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload result: {str(e)}")

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

@app.post("/api/v1/miner/tts/upload")
async def upload_tts_audio(
    task_id: str = Form(...),
    miner_uid: int = Form(...),
    audio_file: UploadFile = File(...),
    processing_time: float = Form(...),
    accuracy_score: float = Form(0.0),
    speed_score: float = Form(0.0)
):
    """Upload TTS audio file from miner"""
    try:
        # Validate required parameters
        if not task_id or task_id == "None" or task_id == "null":
            raise HTTPException(status_code=400, detail="Invalid task_id provided")
        
        if not miner_uid or miner_uid <= 0:
            raise HTTPException(status_code=400, detail="Invalid miner_uid provided")
        
        # Validate audio file
        if not audio_file or audio_file.filename == "":
            raise HTTPException(status_code=400, detail="No audio file provided")
        
        # Check file type (should be .wav)
        if not audio_file.filename.lower().endswith('.wav'):
            raise HTTPException(status_code=400, detail="Audio file must be .wav format")
        
        # Read audio file content
        audio_content = await audio_file.read()
        if len(audio_content) == 0:
            raise HTTPException(status_code=400, detail="Audio file is empty")
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{task_id}_{miner_uid}_{timestamp}.wav"
        
        # Store audio file in Firebase Cloud Storage
        file_id = await file_manager.upload_file(
            audio_content,
            filename,
            "audio/wav",
            file_type="tts"
        )
        
        # Get file metadata
        file_metadata = await file_manager.get_file_metadata(file_id)
        
        # Create file reference
        file_reference = {
            'file_id': file_id,
            'file_name': filename,
            'file_type': "audio/wav",
            'file_size': len(audio_content),
            'local_path': file_metadata.get('cloud_path', f"tts_audio/{file_id}") if file_metadata else f"tts_audio/{file_id}",
            'file_url': f"/api/v1/tts/audio/{file_id}",
            'checksum': str(hash(audio_content)),
            'created_at': datetime.now(),
            'storage_location': 'cloud_storage'
        }
        
        # Create response payload
        response_payload = {
            'output_data': {
                'audio_file': file_reference,
                'duration': 0.0,  # Will be calculated by validator
                'sample_rate': 22050,  # Default sample rate
                'format': 'wav'
            },
            'processing_time': processing_time,
            'accuracy_score': accuracy_score,
            'speed_score': speed_score
        }
        
        # Handle the response with miner_response_handler
        success = await miner_response_handler.handle_miner_response(task_id, miner_uid, response_payload)
        
        if success:
            print(f"✅ TTS audio uploaded successfully for task {task_id} by miner {miner_uid}")
            print(f"   File: {filename}")
            print(f"   Size: {len(audio_content)} bytes")
            print(f"   File ID: {file_id}")
            
            return {
                "success": True,
                "message": "TTS audio uploaded successfully",
                "task_id": task_id,
                "miner_uid": miner_uid,
                "audio_file": file_reference,
                "file_url": f"/api/v1/tts/audio/{file_id}"
            }
        else:
            print(f"❌ Failed to process TTS audio upload for task {task_id}")
            raise HTTPException(status_code=500, detail="Failed to process TTS audio upload")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in upload_tts_audio: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload TTS audio: {str(e)}")

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
        
        # Check Firebase Cloud Storage health
        file_system_healthy = True
        file_system_errors = []
        
        try:
            # Check if Firebase Cloud Storage is accessible
            storage_stats = await file_manager.get_storage_statistics()
            if 'error' in storage_stats:
                file_system_healthy = False
                file_system_errors.append(f"Firebase Cloud Storage error: {storage_stats['error']}")
                    
        except Exception as e:
            file_system_healthy = False
            file_system_errors.append(f"Firebase Cloud Storage check error: {str(e)}")
        
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
    """Serve files from Firebase Cloud Storage"""
    try:
        # Validate file_id parameter
        if not file_id or file_id == "None" or file_id == "null":
            raise HTTPException(status_code=400, detail="Invalid file ID provided")
        
        # Get file from Firebase Cloud Storage
        file_content = await file_manager.download_file(file_id)
        if not file_content:
            raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
        
        # Get file metadata
        file_metadata = await file_manager.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail=f"File metadata not found: {file_id}")
        
        # Handle Unicode filenames properly
        filename = file_metadata['file_name']
        
        # Create a safe filename for Content-Disposition header
        import urllib.parse
        safe_filename = urllib.parse.quote(filename)
        
        # Return file with appropriate headers
        return StreamingResponse(
            iter([file_content]),
            media_type=file_metadata['content_type'],
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}",
                "Cache-Control": "no-cache"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving file: {str(e)}")

@app.get("/api/v1/files/{file_id}/download")
async def download_file(file_id: str):
    """Download files from Firebase Cloud Storage with enhanced error handling"""
    try:
        # Validate file_id parameter
        if not file_id or file_id == "None" or file_id == "null":
            raise HTTPException(
                status_code=400, 
                detail="Invalid file ID provided. File ID cannot be None or null."
            )
        
        # Get file from Firebase Cloud Storage
        file_content = await file_manager.download_file(file_id)
        if not file_content:
            raise HTTPException(
                status_code=404, 
                detail=f"File not found in Firebase Cloud Storage for ID: {file_id}"
            )
        
        # Get file metadata
        file_metadata = await file_manager.get_file_metadata(file_id)
        if not file_metadata:
            raise HTTPException(
                status_code=404, 
                detail=f"File metadata not found for ID: {file_id}"
            )
        
        # Determine content type for proper headers
        content_type = file_metadata.get('content_type', 'application/octet-stream')
        
        # Handle Unicode filenames properly
        filename = file_metadata['file_name']
        
        # Create a safe filename for Content-Disposition header
        import urllib.parse
        safe_filename = urllib.parse.quote(filename)
        
        # Return file with appropriate headers
        return StreamingResponse(
            iter([file_content]),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}",
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

@app.post("/api/v1/miners/register")
async def register_miner(
    uid: int = Form(...),
    hotkey: str = Form(...),
    stake: float = Form(1000.0),
    is_serving: bool = Form(True),
    task_type_specialization: str = Form(""),
    max_capacity: int = Form(100)
):
    """Register a new miner or update existing one"""
    try:
        # Create miner data
        miner_data = {
            'uid': uid,
            'hotkey': hotkey,
            'stake': stake,
            'is_serving': is_serving,
            'task_type_specialization': task_type_specialization,
            'max_capacity': max_capacity,
            'current_load': 0,
            'registered_at': datetime.now(),
            'last_seen': datetime.now()
        }
        
        # Register miner in database
        success = DatabaseOperations.register_miner(db_manager.get_db(), miner_data)
        
        if success:
            print(f"✅ Miner {uid} registered successfully")
            return {
                "success": True,
                "message": f"Miner {uid} registered successfully",
                "miner_data": miner_data
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to register miner")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register miner: {str(e)}")

@app.get("/api/v1/miners")
async def get_miners():
    """Get all registered miners"""
    try:
        miners = DatabaseOperations.get_all_miners(db_manager.get_db())
        return {"miners": miners}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get miners: {str(e)}")

@app.get("/api/v1/tasks")
async def get_all_tasks():
    """Get all tasks"""
    try:
        # Get tasks by status - get all statuses
        all_tasks = []
        for status in ['pending', 'assigned', 'in_progress', 'completed', 'failed']:
            try:
                tasks = DatabaseOperations.get_tasks_by_status(db_manager.get_db(), status, limit=100)
                all_tasks.extend(tasks)
            except:
                continue
        return all_tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")

@app.get("/api/v1/tasks/{task_id}")
async def get_task_by_id(task_id: str):
    """Get specific task by ID"""
    try:
        task = DatabaseOperations.get_task(db_manager.get_db(), task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")

@app.get("/api/v1/metrics")
async def get_metrics():
    """Get system metrics and statistics"""
    try:
        # Get basic system metrics
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system_status": "healthy",
            "duplicate_protection": {},
            "network_miners": {}
        }
        
        # Get duplicate protection statistics from all levels
        try:
            # Level 1: Miner-level protection stats
            miner_stats = {
                "level": "miner",
                "description": "In-memory task tracking and processing state management",
                "status": "active"
            }
            metrics["duplicate_protection"]["miner_level"] = miner_stats
            
            # Level 2: Proxy server-level protection stats
            if hasattr(app.state, 'miner_response_handler'):
                proxy_stats = app.state.miner_response_handler.get_duplicate_protection_stats()
                metrics["duplicate_protection"]["proxy_level"] = proxy_stats
            else:
                metrics["duplicate_protection"]["proxy_level"] = {"status": "not_initialized"}
            
            # Level 3: Task distributor-level protection stats
            if hasattr(app.state, 'task_distributor'):
                distributor_stats = app.state.task_distributor.get_duplicate_protection_stats()
                metrics["duplicate_protection"]["distributor_level"] = distributor_stats
            else:
                metrics["duplicate_protection"]["distributor_level"] = {"status": "not_initialized"}
            
            # Overall duplicate protection summary
            total_protected = 0
            total_effectiveness = 0
            active_levels = 0
            
            for level, stats in metrics["duplicate_protection"].items():
                if isinstance(stats, dict) and stats.get("status") == "active":
                    active_levels += 1
                    if "duplicate_protection_effectiveness" in stats:
                        effectiveness_str = stats["duplicate_protection_effectiveness"]
                        try:
                            effectiveness = float(effectiveness_str.rstrip('%'))
                            total_effectiveness += effectiveness
                        except:
                            pass
            
            metrics["duplicate_protection"]["summary"] = {
                "active_protection_levels": active_levels,
                "total_protection_levels": 3,
                "overall_effectiveness": f"{(total_effectiveness / max(active_levels, 1)):.2f}%" if active_levels > 0 else "0%",
                "protection_status": "fully_active" if active_levels == 3 else "partially_active"
            }
            
        except Exception as e:
            metrics["duplicate_protection"]["error"] = f"Error getting protection stats: {str(e)}"
        
        # Get network miner status
        try:
            if hasattr(app.state, 'miner_status_manager'):
                available_miners = await app.state.miner_status_manager.get_available_miners()
                
                # Calculate network statistics
                total_miners = len(available_miners)
                active_miners = len([m for m in available_miners if m.get('is_serving', True)])
                total_stake = sum(float(m.get('stake', 0)) for m in available_miners)
                avg_performance = sum(m.get('performance_score', 0) for m in available_miners) / max(total_miners, 1)
                
                metrics["network_miners"] = {
                    "total_miners": total_miners,
                    "active_miners": active_miners,
                    "total_stake": total_stake,
                    "average_performance_score": round(avg_performance, 3),
                    "miner_details": [
                        {
                            "uid": m.get('uid'),
                            "hotkey": m.get('hotkey', 'unknown')[:10] + '...' if m.get('hotkey') else 'unknown',
                            "stake": m.get('stake', 0),
                            "availability_score": m.get('availability_score', 0),
                            "current_load": m.get('current_load', 0),
                            "max_capacity": m.get('max_capacity', 5)
                        }
                        for m in available_miners[:10]  # Show top 10 miners
                    ]
                }
            else:
                metrics["network_miners"] = {"status": "not_initialized"}
                
        except Exception as e:
            metrics["network_miners"]["error"] = f"Error getting network miner status: {str(e)}"
        
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting metrics: {str(e)}")

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

@app.get("/api/v1/duplicate-protection/stats")
async def get_duplicate_protection_stats():
    """Get detailed duplicate protection statistics from all levels"""
    try:
        stats = {
            "timestamp": datetime.now().isoformat(),
            "duplicate_protection_system": {
                "description": "Multi-level duplicate protection system to prevent miners from processing the same task multiple times",
                "total_levels": 3,
                "levels": {}
            }
        }
        
        # Level 1: Miner-level protection
        stats["duplicate_protection_system"]["levels"]["miner_level"] = {
            "name": "Miner-Level Protection",
            "description": "In-memory task tracking and processing state management",
            "mechanisms": [
                "processed_tasks set - tracks completed tasks",
                "processing_tasks set - tracks currently processing tasks",
                "Task status validation before processing",
                "Automatic cleanup of old processed tasks"
            ],
            "status": "active",
            "effectiveness": "Prevents miner from processing same task multiple times"
        }
        
        # Level 2: Proxy server-level protection
        if hasattr(app.state, 'miner_response_handler'):
            proxy_stats = app.state.miner_response_handler.get_duplicate_protection_stats()
            stats["duplicate_protection_system"]["levels"]["proxy_level"] = {
                "name": "Proxy Server-Level Protection",
                "description": "Duplicate response detection and prevention",
                "mechanisms": [
                    "Check for existing miner responses before storing",
                    "Race condition protection with double-checking",
                    "Automatic duplicate response rejection"
                ],
                "status": "active",
                "statistics": proxy_stats
            }
        else:
            stats["duplicate_protection_system"]["levels"]["proxy_level"] = {
                "name": "Proxy Server-Level Protection",
                "description": "Duplicate response detection and prevention",
                "status": "not_initialized",
                "error": "Miner response handler not available"
            }
        
        # Level 3: Task distributor-level protection
        if hasattr(app.state, 'task_distributor'):
            distributor_stats = app.state.task_distributor.get_duplicate_protection_stats()
            stats["duplicate_protection_system"]["levels"]["distributor_level"] = {
                "name": "Task Distributor-Level Protection",
                "description": "Prevent distribution of already assigned/completed tasks",
                "mechanisms": [
                    "Task status validation before distribution",
                    "Skip tasks with invalid statuses",
                    "Prevent duplicate task assignments"
                ],
                "status": "active",
                "statistics": distributor_stats
            }
        else:
            stats["duplicate_protection_system"]["levels"]["distributor_level"] = {
                "name": "Task Distributor-Level Protection",
                "description": "Prevent distribution of already assigned/completed tasks",
                "status": "not_initialized",
                "error": "Task distributor not available"
            }
        
        # Overall system health
        active_levels = sum(1 for level in stats["duplicate_protection_system"]["levels"].values() 
                          if level.get("status") == "active")
        
        stats["duplicate_protection_system"]["overall_health"] = {
            "active_levels": active_levels,
            "total_levels": 3,
            "health_percentage": f"{(active_levels / 3) * 100:.1f}%",
            "status": "fully_healthy" if active_levels == 3 else "partially_healthy" if active_levels > 0 else "unhealthy"
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting duplicate protection stats: {str(e)}")

# Enhanced multi-validator miner status endpoint
@app.post("/api/v1/validators/miner-status")
async def receive_miner_status_from_validator(
    validator_uid: int = Form(...),
    miner_statuses: str = Form(...),  # JSON string
    epoch: int = Form(...)
):
    """Receive miner status reports from validators with multi-validator consensus"""
    try:
        import json
        miner_data = json.loads(miner_statuses)
        
        print(f"📥 Received miner status from validator {validator_uid} for epoch {epoch}")
        print(f"   Miners reported: {len(miner_data)}")
        
        # Use multi-validator manager for consensus-based processing
        if hasattr(app.state, 'multi_validator_manager'):
            result = await app.state.multi_validator_manager.receive_validator_report(
                validator_uid, miner_data, epoch
            )
            
            if result.get('success'):
                print(f"   ✅ Multi-validator consensus processing completed")
                print(f"      Miners processed: {result.get('miners_processed', 0)}")
                print(f"      Consensus updated: {result.get('consensus_updated', 0)}")
            else:
                print(f"   ❌ Multi-validator processing failed: {result.get('error', 'Unknown error')}")
        else:
            # Fallback to legacy single-validator processing
            print(f"   ⚠️ Multi-validator manager not available, using legacy processing")
            result = await _legacy_miner_status_processing(validator_uid, miner_data, epoch)
        
        # Track metrics
        system_metrics.increment_database_operations()
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON from validator {validator_uid}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON data: {str(e)}")
    except Exception as e:
        print(f"❌ Error processing miner status from validator {validator_uid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process miner status: {str(e)}")

async def _legacy_miner_status_processing(validator_uid: int, miner_data: List[Dict], epoch: int) -> Dict[str, Any]:
    """Legacy single-validator miner status processing"""
    try:
        updated_count = 0
        for miner_status in miner_data:
            try:
                miner_uid = miner_status.get('uid')
                if miner_uid is not None:
                    # Use the existing miner status collection
                    miner_ref = db_manager.get_db().collection('miner_status').document(str(miner_uid))
                    
                    # Add timestamp and validator info
                    miner_status['last_updated'] = datetime.now()
                    miner_status['reported_by_validator'] = validator_uid
                    miner_status['epoch'] = epoch
                    
                    # Store in database
                    miner_ref.set(miner_status, merge=True)
                    updated_count += 1
                    
                    print(f"      ✅ Updated miner {miner_uid}: {miner_status.get('hotkey', 'unknown')}")
                else:
                    print(f"      ⚠️ Skipping miner without UID: {miner_status}")
                    
            except Exception as e:
                print(f"      ❌ Error updating miner {miner_status.get('uid', 'unknown')}: {e}")
                continue
        
        print(f"   Successfully updated {updated_count}/{len(miner_data)} miners (legacy mode)")
        
        return {
            "success": True, 
            "miners_updated": updated_count,
            "total_received": len(miner_data),
            "validator_uid": validator_uid,
            "epoch": epoch,
            "processing_mode": "legacy"
        }
        
    except Exception as e:
        print(f"❌ Error in legacy miner status processing: {e}")
        return {
            "success": False,
            "error": str(e),
            "validator_uid": validator_uid,
            "processing_mode": "legacy"
        }

# Add endpoint to get current miner status
@app.get("/api/v1/miners/network-status")
async def get_network_miner_status():
    """Get current miner status from Bittensor network (via validator reports)"""
    try:
        # Query miner status collection
        miner_status_collection = db_manager.get_db().collection('miner_status')
        docs = miner_status_collection.stream()
        
        miners = []
        for doc in docs:
            miner_data = doc.to_dict()
            miner_data['miner_id'] = doc.id
            miners.append(miner_data)
        
        # Calculate network statistics
        total_miners = len(miners)
        active_miners = len([m for m in miners if m.get('is_serving', False)])
        total_stake = sum(float(m.get('stake', 0)) for m in miners)
        
        return {
            "success": True,
            "network_status": {
                "total_miners": total_miners,
                "active_miners": active_miners,
                "total_stake": total_stake,
                "last_updated": datetime.now().isoformat()
            },
            "miners": miners
        }
        
    except Exception as e:
        print(f"❌ Error getting network miner status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get miner status: {str(e)}")

# New endpoint to get multi-validator consensus statistics
@app.get("/api/v1/validators/consensus-stats")
async def get_validator_consensus_stats():
    """Get statistics about multi-validator consensus and reports"""
    try:
        if not hasattr(app.state, 'multi_validator_manager'):
            raise HTTPException(status_code=503, detail="Multi-validator manager not available")
        
        stats = await app.state.multi_validator_manager.get_validator_report_stats()
        
        return {
            "success": True,
            "consensus_statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting consensus stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get consensus stats: {str(e)}")

# New endpoint to get consensus status for a specific miner
@app.get("/api/v1/miners/{miner_uid}/consensus")
async def get_miner_consensus_status(miner_uid: int):
    """Get consensus status for a specific miner"""
    try:
        if not hasattr(app.state, 'multi_validator_manager'):
            raise HTTPException(status_code=503, detail="Multi-validator manager not available")
        
        consensus_status = await app.state.multi_validator_manager.get_consensus_miner_status(miner_uid)
        
        if consensus_status:
            return {
                "success": True,
                "miner_uid": miner_uid,
                "consensus_status": consensus_status,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"No consensus status found for miner {miner_uid}")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting miner consensus status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get miner consensus status: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
