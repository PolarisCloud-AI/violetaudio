"""
Task Manager for Enhanced Proxy Server
Handles task lifecycle, status updates, and miner assignments
"""

import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from firebase_admin import firestore
from proxy_server.database.enhanced_schema import TaskStatus, TaskPriority

class TaskManager:
    def __init__(self, db):
        self.db = db
        self.tasks_collection = db.collection('tasks')
        self.miner_responses_collection = db.collection('miner_responses')
        self.task_metrics_collection = db.collection('task_metrics')
        
        # Miner assignment configuration
        self.min_miners_per_task = 1
        self.max_miners_per_task = 10
        self.default_miners_per_task = 3
    
    async def create_task(self, task_data: Dict) -> str:
        """Create a new task"""
        try:
            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Create task document
            task_doc = {
                'task_id': task_id,
                'task_type': task_data['task_type'],
                'input_file_id': task_data['input_file_id'],
                'source_language': task_data.get('source_language', 'en'),
                'target_language': task_data.get('target_language', 'en'),
                'priority': task_data.get('priority', 'normal'),
                'status': task_data.get('status', 'pending'),
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'assigned_miners': [],
                'required_miner_count': self._calculate_required_miner_count(task_data),
                'estimated_completion_time': task_data.get('estimated_completion_time', 60),
                'callback_url': task_data.get('callback_url'),
                'user_metadata': task_data.get('user_metadata', {})
            }
            
            # Save to database
            self.tasks_collection.document(task_id).set(task_doc)
            
            print(f"✅ Task created: {task_id} ({task_data['task_type']}) - Required miners: {task_doc['required_miner_count']}")
            return task_id
            
        except Exception as e:
            print(f"❌ Error creating task: {e}")
            raise

    def _calculate_required_miner_count(self, task_data: Dict) -> int:
        """Calculate the required number of miners for a task"""
        try:
            # Get requested miner count from task data
            requested_count = task_data.get('required_miner_count', self.default_miners_per_task)
            
            # Ensure minimum and maximum constraints
            if requested_count < self.min_miners_per_task:
                requested_count = self.min_miners_per_task
            elif requested_count > self.max_miners_per_task:
                requested_count = self.max_miners_per_task
            
            return requested_count
            
        except Exception as e:
            print(f"⚠️ Error calculating required miner count: {e}")
            return self.default_miners_per_task

    async def assign_miners_to_task(self, task_id: str, miner_uids: List[int]):
        """Assign miners to a specific task"""
        try:
            # Validate miner count constraints
            if len(miner_uids) < self.min_miners_per_task:
                raise ValueError(f"Task requires at least {self.min_miners_per_task} miners, got {len(miner_uids)}")
            
            if len(miner_uids) > self.max_miners_per_task:
                raise ValueError(f"Task cannot have more than {self.max_miners_per_task} miners, got {len(miner_uids)}")
            
            # Update task with assigned miners
            self.tasks_collection.document(task_id).update({
                'assigned_miners': miner_uids,
                'status': TaskStatus.ASSIGNED.value,
                'distributed_at': firestore.SERVER_TIMESTAMP,
                'actual_miner_count': len(miner_uids)
            })
            
            # Create miner response tracking documents
            for miner_uid in miner_uids:
                self.miner_responses_collection.document(f"{task_id}_{miner_uid}").set({
                    'task_id': task_id,
                    'miner_uid': miner_uid,
                    'status': 'assigned',
                    'assigned_at': firestore.SERVER_TIMESTAMP,
                    'response_data': None,
                    'metrics': {},
                    'processing_time': None,
                    'accuracy_score': None,
                    'speed_score': None
                })
            
            print(f"✅ Task {task_id} assigned to {len(miner_uids)} miners (UIDs: {miner_uids})")
            
        except Exception as e:
            print(f"❌ Failed to assign miners to task {task_id}: {e}")
            raise

    async def get_optimal_miner_count(self, task_type: str, priority: str = 'normal') -> int:
        """Get optimal number of miners for a task based on type and priority"""
        try:
            # Base miner count by task type
            base_counts = {
                'transcription': 2,  # Audio transcription benefits from multiple miners
                'tts': 2,            # TTS can have quality variations
                'summarization': 3,  # Summarization benefits from multiple perspectives
                'translation': 3     # Translation needs validation
            }
            
            base_count = base_counts.get(task_type, self.default_miners_per_task)
            
            # Adjust by priority
            priority_multipliers = {
                'low': 0.8,
                'normal': 1.0,
                'high': 1.3,
                'urgent': 1.5
            }
            
            multiplier = priority_multipliers.get(priority, 1.0)
            optimal_count = int(base_count * multiplier)
            
            # Ensure within constraints
            optimal_count = max(self.min_miners_per_task, min(optimal_count, self.max_miners_per_task))
            
            return optimal_count
            
        except Exception as e:
            print(f"⚠️ Error calculating optimal miner count: {e}")
            return self.default_miners_per_task

    async def update_task_status(self, task_id: str, status: str, **kwargs):
        """Update task status and additional fields"""
        try:
            update_data = {
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            update_data.update(kwargs)
            
            self.tasks_collection.document(task_id).update(update_data)
            print(f"✅ Task {task_id} status updated to {status}")
            
        except Exception as e:
            print(f"❌ Failed to update task {task_id}: {e}")
            raise
    
    async def get_tasks_by_status(self, status: str, limit: int = 100) -> List[Dict]:
        """Get tasks by status"""
        try:
            query = self.tasks_collection.where('status', '==', status).limit(limit)
            docs = query.stream()
            
            tasks = []
            for doc in docs:
                task_data = doc.to_dict()
                task_data['id'] = doc.id
                tasks.append(task_data)
            
            return tasks
            
        except Exception as e:
            print(f"❌ Failed to get tasks by status {status}: {e}")
            return []
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a specific task by ID"""
        try:
            doc = self.tasks_collection.document(task_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            print(f"❌ Error getting task {task_id}: {e}")
            return None
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task and all associated data"""
        try:
            # Delete task
            self.tasks_collection.document(task_id).delete()  # Remove await
            
            # Delete associated miner responses
            query = self.miner_responses_collection.where('task_id', '==', task_id)
            responses = query.stream()
            for doc in responses:
                doc.reference.delete()  # Remove await
            
            print(f"✅ Task {task_id} deleted successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to delete task {task_id}: {e}")
            return False
