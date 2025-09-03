"""
Firestore Database Schema for Enhanced Proxy Server
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from firebase_admin import firestore
from datetime import datetime
from dataclasses import dataclass

class TaskStatus(str, Enum):
    PENDING = "pending"
    DISTRIBUTED = "distributed"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    APPROVED = "approved"
    FAILED = "failed"

class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class TaskType(str, Enum):
    TRANSCRIPTION = "transcription"
    TTS = "tts"
    SUMMARIZATION = "summarization"

class TaskModel:
    def __init__(
        self,
        task_id: str,
        task_type: str,
        input_file_id: str,
        source_language: str = "en",
        target_language: str = "en",
        priority: str = "normal",
        status: str = "pending",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        assigned_miners: Optional[List[int]] = None,
        required_miner_count: int = 3,
        estimated_completion_time: int = 60,
        callback_url: Optional[str] = None,
        user_metadata: Optional[Dict] = None,
        miner_responses: Optional[Dict] = None,
        best_response: Optional[Dict] = None,
        evaluation_data: Optional[Dict] = None
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.input_file_id = input_file_id
        self.source_language = source_language
        self.target_language = target_language
        self.priority = priority
        self.status = status
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.assigned_miners = assigned_miners or []
        self.required_miner_count = required_miner_count
        self.estimated_completion_time = estimated_completion_time
        self.callback_url = callback_url
        self.user_metadata = user_metadata or {}
        self.miner_responses = miner_responses or {}
        self.best_response = best_response or {}
        self.evaluation_data = evaluation_data or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'input_file_id': self.input_file_id,
            'source_language': self.source_language,
            'target_language': self.target_language,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'assigned_miners': self.assigned_miners,
            'required_miner_count': self.required_miner_count,
            'estimated_completion_time': self.estimated_completion_time,
            'callback_url': self.callback_url,
            'user_metadata': self.user_metadata,
            'miner_responses': self.miner_responses,
            'best_response': self.best_response,
            'evaluation_data': self.evaluation_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskModel':
        return cls(
            task_id=data['task_id'],
            task_type=data['task_type'],
            input_file_id=data['input_file_id'],
            source_language=data.get('source_language', 'en'),
            target_language=data.get('target_language', 'en'),
            priority=data.get('priority', 'normal'),
            status=data.get('status', 'pending'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            assigned_miners=data.get('assigned_miners', []),
            required_miner_count=data.get('required_miner_count', 3),
            estimated_completion_time=data.get('estimated_completion_time', 60),
            callback_url=data.get('callback_url'),
            user_metadata=data.get('user_metadata', {}),
            miner_responses=data.get('miner_responses', {}),
            best_response=data.get('best_response', {}),
            evaluation_data=data.get('evaluation_data', {})
        )

class MinerResponseModel:
    def __init__(
        self,
        response_id: str,
        task_id: str,
        miner_uid: int,
        response_data: Dict[str, Any],
        status: str = "completed",
        submitted_at: Optional[datetime] = None,
        processing_time: float = 0.0,
        accuracy_score: float = 0.0,
        speed_score: float = 0.0,
        output_file_id: Optional[str] = None,
        output_file_url: Optional[str] = None
    ):
        self.response_id = response_id
        self.task_id = task_id
        self.miner_uid = miner_uid
        self.response_data = response_data
        self.status = status
        self.submitted_at = submitted_at or datetime.now()
        self.processing_time = processing_time
        self.accuracy_score = accuracy_score
        self.speed_score = speed_score
        self.output_file_id = output_file_id
        self.output_file_url = output_file_url
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'response_id': self.response_id,
            'task_id': self.task_id,
            'miner_uid': self.miner_uid,
            'response_data': self.response_data,
            'status': self.status,
            'submitted_at': self.submitted_at,
            'processing_time': self.processing_time,
            'accuracy_score': self.accuracy_score,
            'speed_score': self.speed_score,
            'output_file_id': self.output_file_id,
            'output_file_url': self.output_file_url
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MinerResponseModel':
        return cls(
            response_id=data['response_id'],
            task_id=data['task_id'],
            miner_uid=data['miner_uid'],
            response_data=data['response_data'],
            status=data.get('status', 'completed'),
            submitted_at=data.get('submitted_at'),
            processing_time=data.get('processing_time', 0.0),
            accuracy_score=data.get('accuracy_score', 0.0),
            speed_score=data.get('speed_score', 0.0),
            output_file_id=data.get('output_file_id'),
            output_file_url=data.get('output_file_url')
        )

class FileModel:
    def __init__(
        self,
        file_id: str,
        file_name: str,
        file_path: str,
        content_type: str,
        size: int,
        file_type: str,
        local_path: str,
        file_url: str,
        uploaded_at: Optional[datetime] = None,
        status: str = "active",
        checksum: Optional[str] = None
    ):
        self.file_id = file_id
        self.file_name = file_name
        self.file_path = file_path
        self.content_type = content_type
        self.size = size
        self.file_type = file_type
        self.local_path = local_path
        self.file_url = file_url
        self.uploaded_at = uploaded_at or datetime.now()
        self.status = status
        self.checksum = checksum
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_id': self.file_id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'content_type': self.content_type,
            'size': self.size,
            'file_type': self.file_type,
            'local_path': self.local_path,
            'file_url': self.file_url,
            'uploaded_at': self.uploaded_at,
            'status': self.status,
            'checksum': self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileModel':
        return cls(
            file_id=data['file_id'],
            file_name=data['file_name'],
            file_path=data['file_path'],
            content_type=data['content_type'],
            size=data['size'],
            file_type=data['file_type'],
            local_path=data['local_path'],
            file_url=data['file_url'],
            uploaded_at=data.get('uploaded_at'),
            status=data.get('status', 'active'),
            checksum=data.get('checksum')
        )

class DatabaseManager:
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        self.db = None
        self.initialized = False
    
    def initialize(self):
        """Initialize Firebase connection"""
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
            
            # Initialize Firebase
            cred = credentials.Certificate(self.credentials_path)
            firebase_admin.initialize_app(cred)
            
            # Get Firestore client
            self.db = firestore.client()
            
            self.initialized = True
            
            print("✅ Database initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize database: {e}")
            raise
    
    def get_db(self):
        """Get Firestore database client"""
        if not self.initialized:
            raise Exception("Database not initialized")
        return self.db
@dataclass
class MinerStatusModel:
    """Track miner status and performance from validator reports"""
    uid: int
    hotkey: str
    ip: str
    port: int
    external_ip: Optional[str] = None
    external_port: Optional[int] = None
    is_serving: bool = False
    stake: float = 0.0
    performance_score: float = 0.0
    current_load: int = 0
    max_capacity: int = 5
    last_seen: Optional[datetime] = None
    reported_by_validators: List[int] = None
    task_type_specialization: Dict = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.reported_by_validators is None:
            self.reported_by_validators = []
        if self.task_type_specialization is None:
            self.task_type_specialization = {}
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'uid': self.uid,
            'hotkey': self.hotkey,
            'ip': self.ip,
            'port': self.port,
            'external_ip': self.external_ip,
            'external_port': self.external_port,
            'is_serving': self.is_serving,
            'stake': self.stake,
            'performance_score': self.performance_score,
            'current_load': self.current_load,
            'max_capacity': self.max_capacity,
            'last_seen': self.last_seen,
            'reported_by_validators': self.reported_by_validators,
            'task_type_specialization': self.task_type_specialization,
            'updated_at': self.updated_at
        }

