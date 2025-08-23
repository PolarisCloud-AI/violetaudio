"""
Enhanced Database Schema for Production Task Management
This schema provides comprehensive models for tasks, files, miners, and responses.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import uuid
import hashlib
import time

# Enums
class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    APPROVED = "approved"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class TaskType(str, Enum):
    TRANSCRIPTION = "transcription"
    TTS = "tts"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"

class MinerStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"

class ResponseStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

# Core Data Models
@dataclass
class TextContent:
    """Text content for summarization and other text-based tasks"""
    content_id: str
    text: str
    created_at: datetime
    updated_at: datetime
    source_language: str = "en"
    detected_language: Optional[str] = None
    language_confidence: Optional[float] = None
    text_length: int = 0
    word_count: int = 0
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class FileReference:
    """Reference to a file stored in the system"""
    file_id: str
    file_name: str
    file_type: str
    file_size: int
    local_path: str
    file_url: str
    content_type: str
    checksum: str
    created_at: datetime
    updated_at: datetime

@dataclass
class MinerInfo:
    """Information about a miner"""
    uid: int
    hotkey: str
    ip: str
    port: int
    external_ip: Optional[str] = None
    external_port: Optional[int] = None
    is_serving: bool = True
    stake: float = 0.0
    performance_score: float = 0.0
    current_load: float = 0.0
    max_capacity: float = 100.0
    task_type_specialization: Optional[str] = None
    last_seen: Optional[datetime] = None

@dataclass
class TaskAssignment:
    """Assignment of a task to a miner"""
    assignment_id: str
    miner_uid: int
    assigned_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: ResponseStatus = ResponseStatus.PENDING
    processing_time: Optional[float] = None
    accuracy_score: Optional[float] = None
    speed_score: Optional[float] = None
    error_message: Optional[str] = None

@dataclass
class MinerResponse:
    """Response from a miner for a task"""
    response_id: str
    miner_uid: int
    submitted_at: datetime
    processing_time: float
    accuracy_score: float
    speed_score: float
    output_data: Union[str, Dict[str, Any]]
    output_file: Optional[FileReference] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class TaskModel:
    """Complete task model with all related data"""
    task_id: str
    task_type: TaskType
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    updated_at: datetime
    
    # Input/Output - can be either file-based or text-based
    input_file: Optional[FileReference] = None
    input_text: Optional[TextContent] = None
    output_file: Optional[FileReference] = None
    
    # Task details
    source_language: str = "en"
    target_language: Optional[str] = None
    estimated_completion_time: Optional[float] = None
    actual_completion_time: Optional[float] = None
    deadline: Optional[datetime] = None
    
    # Assignment and execution
    required_miner_count: int = 1
    assigned_miners: List[int] = field(default_factory=list)
    task_assignments: List[TaskAssignment] = field(default_factory=list)
    miner_responses: List[MinerResponse] = field(default_factory=list)
    
    # Results and evaluation
    best_response: Optional[MinerResponse] = None
    evaluation_data: Optional[Dict[str, Any]] = None
    
    # Metadata
    user_metadata: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)
    callback_url: Optional[str] = None
    distributed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

# Collection names
COLLECTIONS = {
    'tasks': 'tasks',
    'files': 'files',
    'text_content': 'text_content',
    'miners': 'miners',
    'miner_status': 'miner_status',
    'assignments': 'task_assignments',
    'responses': 'miner_responses',
    'evaluations': 'task_evaluations',
    'system_metrics': 'system_metrics'
}

# Required indexes for Firestore
REQUIRED_INDEXES = [
    'tasks_status_created_at',
    'tasks_type_status',
    'tasks_assigned_miners',
    'miner_status_uid_updated_at',
    'assignments_task_id_miner_uid',
    'responses_task_id_miner_uid'
]

# Utility functions
def generate_task_id() -> str:
    """Generate a unique task ID"""
    return str(uuid.uuid4())

def generate_assignment_id() -> str:
    """Generate a unique assignment ID"""
    return str(uuid.uuid4())

def generate_response_id() -> str:
    """Generate a unique response ID"""
    return str(uuid.uuid4())

def generate_file_id() -> str:
    """Generate a unique file ID"""
    return str(uuid.uuid4())

def generate_text_content_id() -> str:
    """Generate a unique text content ID"""
    return str(uuid.uuid4())

def validate_task_data(task_data: Dict[str, Any]) -> bool:
    """Validate task data structure"""
    required_fields = ['task_type', 'priority']
    
    # Must have either input_file or input_text
    has_input = 'input_file' in task_data or 'input_text' in task_data
    
    return all(field in task_data for field in required_fields) and has_input

def calculate_task_score(accuracy: float, speed: float, processing_time: float) -> float:
    """Calculate overall task score"""
    # Weighted combination of accuracy and speed
    accuracy_weight = 0.7
    speed_weight = 0.3
    
    # Normalize processing time (lower is better)
    time_score = max(0.0, min(1.0, 10.0 / max(processing_time, 0.1)))
    
    return (accuracy * accuracy_weight) + (speed * speed_weight) + (time_score * 0.1)

# Database Operations
class DatabaseOperations:
    """Static class for common database operations"""
    
    @staticmethod
    def create_task(db, task_data: Dict[str, Any]) -> str:
        """Create a new task in the database"""
        task_id = generate_task_id()
        task_data['task_id'] = task_id
        task_data['created_at'] = datetime.utcnow()
        task_data['updated_at'] = datetime.utcnow()
        
        # Set default values
        if 'status' not in task_data:
            task_data['status'] = TaskStatus.PENDING
        if 'priority' not in task_data:
            task_data['priority'] = TaskPriority.NORMAL
        if 'required_miner_count' not in task_data:
            task_data['required_miner_count'] = 1
        
        # Create task document
        db.collection(COLLECTIONS['tasks']).document(task_id).set(task_data)
        return task_id
    
    @staticmethod
    def assign_task_to_miners(db, task_id: str, miner_uids: List[int]) -> bool:
        """Assign a task to multiple miners"""
        try:
            task_ref = db.collection(COLLECTIONS['tasks']).document(task_id)
            
            # Create assignments
            assignments = []
            for miner_uid in miner_uids:
                assignment = {
                    'assignment_id': generate_assignment_id(),
                    'miner_uid': miner_uid,
                    'assigned_at': datetime.utcnow(),
                    'status': ResponseStatus.PENDING
                }
                assignments.append(assignment)
            
            # Update task
            task_ref.update({
                'assigned_miners': miner_uids,
                'task_assignments': assignments,
                'status': TaskStatus.ASSIGNED,
                'distributed_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            
            return True
        except Exception as e:
            print(f"❌ Error assigning task to miners: {e}")
            return False
    
    @staticmethod
    def get_tasks_by_status(db, status: TaskStatus, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tasks by status"""
        try:
            query = db.collection(COLLECTIONS['tasks']).where('status', '==', status).limit(limit)
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            print(f"❌ Error getting tasks by status: {e}")
            return []
    
    @staticmethod
    def get_task(db, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID"""
        try:
            doc = db.collection(COLLECTIONS['tasks']).document(task_id).get()
            if doc.exists:
                return doc.to_dict()
            else:
                return None
        except Exception as e:
            print(f"❌ Error getting task {task_id}: {e}")
            return None
    
    @staticmethod
    def get_miner_tasks(db, miner_uid: int, status: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
        """Get tasks assigned to a specific miner with proper status filtering"""
        try:
            # Start with base query
            query = db.collection(COLLECTIONS['tasks'])
            
            # Always filter by status first - miners should only get assigned tasks
            if status:
                # If status is provided, use it (for flexibility)
                query = query.where('status', '==', status)
            else:
                # Default: only return assigned tasks (not completed, failed, etc.)
                query = query.where('status', '==', 'assigned')
            
            # Execute the status-filtered query
            docs = query.stream()
            tasks = []
            
            # Then filter by miner assignment
            for doc in docs:
                task_data = doc.to_dict()
                # Only include tasks assigned to this specific miner
                if miner_uid in task_data.get('assigned_miners', []):
                    tasks.append(task_data)
            
            print(f"🔍 Found {len(tasks)} tasks for miner {miner_uid} with status '{status or 'assigned'}'")
            return tasks
            
        except Exception as e:
            print(f"❌ Error getting miner tasks for miner {miner_uid}: {e}")
            return []
    
    @staticmethod
    def update_task_status(db, task_id: str, status: TaskStatus, **kwargs) -> bool:
        """Update task status and other fields"""
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow()
            }
            update_data.update(kwargs)
            
            db.collection(COLLECTIONS['tasks']).document(task_id).update(update_data)
            return True
        except Exception as e:
            print(f"❌ Error updating task status: {e}")
            return False
    
    @staticmethod
    def get_available_miners(db, task_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get available miners that can process tasks"""
        try:
            query = db.collection(COLLECTIONS['miners'])
            
            # Filter by availability
            query = query.where('is_serving', '==', True)
            
            # If task type is specified, filter by specialization
            if task_type:
                query = query.where('task_type_specialization', 'in', [task_type, None, ''])
            
            # Limit results
            query = query.limit(limit)
            
            docs = query.stream()
            miners = []
            
            for doc in docs:
                miner_data = doc.to_dict()
                # Only include miners with reasonable load
                if miner_data.get('current_load', 0) < miner_data.get('max_capacity', 100):
                    miners.append(miner_data)
            
            print(f"🔍 Found {len(miners)} available miners for task type '{task_type or 'any'}'")
            return miners
            
        except Exception as e:
            print(f"❌ Error getting available miners: {e}")
            return []
    
    @staticmethod
    def auto_assign_task(db, task_id: str, task_type: str, required_count: int = 3) -> bool:
        """Automatically assign a task to available miners"""
        try:
            # Get available miners for this task type
            available_miners = DatabaseOperations.get_available_miners(db, task_type, limit=required_count * 2)
            
            if not available_miners:
                print(f"⚠️ No available miners found for task {task_id}")
                return False
            
            # Select miners (take first required_count or all available if fewer)
            selected_miners = available_miners[:required_count]
            miner_uids = [miner['uid'] for miner in selected_miners]
            
            print(f"🎯 Auto-assigning task {task_id} to {len(miner_uids)} miners: {miner_uids}")
            
            # Assign the task
            success = DatabaseOperations.assign_task_to_miners(db, task_id, miner_uids)
            
            if success:
                print(f"✅ Successfully auto-assigned task {task_id} to miners {miner_uids}")
            else:
                print(f"❌ Failed to auto-assign task {task_id}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error auto-assigning task {task_id}: {e}")
            return False
    
    @staticmethod
    def add_miner_response(db, task_id: str, miner_uid: int, response_data: Dict[str, Any]) -> bool:
        """Add a miner response to a task"""
        try:
            response_id = generate_response_id()
            response = {
                'response_id': response_id,
                'miner_uid': miner_uid,
                'submitted_at': datetime.utcnow(),
                **response_data
            }
            
            # Get current task
            task_ref = db.collection(COLLECTIONS['tasks']).document(task_id)
            task_doc = task_ref.get()
            
            if not task_doc.exists:
                print(f"❌ Task {task_id} not found")
                return False
            
            task_data = task_doc.to_dict()
            miner_responses = task_data.get('miner_responses', [])
            miner_responses.append(response)
            
            # Update task
            task_ref.update({
                'miner_responses': miner_responses,
                'updated_at': datetime.utcnow()
            })
            
            return True
        except Exception as e:
            print(f"❌ Error adding miner response: {e}")
            return False
