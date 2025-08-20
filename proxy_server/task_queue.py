#!/usr/bin/env python3
"""
Task Queue Manager for Bittensor Audio Processing Proxy Server
Handles task queuing, processing, and result management
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import redis
from dataclasses import dataclass, asdict

from config import get_config

config = get_config()

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class Task:
    """Task data structure"""
    task_id: str
    task_type: str
    input_data: str
    language: str
    priority: TaskPriority
    callback_url: Optional[str] = None
    submitted_at: Optional[str] = None
    queued_at: Optional[str] = None
    processing_started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

class TaskQueueManager:
    """Manages the task queue and processing"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            password=config.REDIS_PASSWORD,
            decode_responses=True
        )
        self.processing_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self.failed_tasks: Dict[str, Task] = {}
        
    def add_task(self, task: Task) -> bool:
        """Add a new task to the queue"""
        try:
            # Set timestamps
            if not task.submitted_at:
                task.submitted_at = datetime.now().isoformat()
            if not task.queued_at:
                task.queued_at = datetime.now().isoformat()
            
            # Store task data in Redis
            task_data = asdict(task)
            self.redis_client.hset(f"task:{task.task_id}", mapping=task_data)
            
            # Add to priority queue
            priority_score = self._get_priority_score(task.priority)
            self.redis_client.zadd("task_queue", {task.task_id: priority_score})
            
            # Add to pending tasks
            self.redis_client.sadd("pending_tasks", task.task_id)
            
            print(f"📝 Task {task.task_id} added to queue with priority {task.priority}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding task to queue: {str(e)}")
            return False
    
    def get_next_task(self) -> Optional[Task]:
        """Get the next task from the queue based on priority"""
        try:
            # Get highest priority task
            task_ids = self.redis_client.zrevrange("task_queue", 0, 0)
            if not task_ids:
                return None
            
            task_id = task_ids[0]
            task_data = self.redis_client.hgetall(f"task:{task_id}")
            
            if task_data:
                # Create Task object
                task = Task(
                    task_id=task_data['task_id'],
                    task_type=task_data['task_type'],
                    input_data=task_data['input_data'],
                    language=task_data['language'],
                    priority=TaskPriority(task_data['priority']),
                    callback_url=task_data.get('callback_url'),
                    submitted_at=task_data.get('submitted_at'),
                    queued_at=task_data.get('queued_at'),
                    status=TaskStatus(task_data.get('status', 'pending')),
                    retry_count=int(task_data.get('retry_count', 0)),
                    max_retries=int(task_data.get('max_retries', 3))
                )
                return task
            return None
            
        except Exception as e:
            print(f"❌ Error getting next task: {str(e)}")
            return None
    
    def mark_task_processing(self, task_id: str) -> bool:
        """Mark task as processing"""
        try:
            task_data = self.redis_client.hgetall(f"task:{task_id}")
            if task_data:
                # Update status
                self.redis_client.hset(f"task:{task_id}", "status", TaskStatus.PROCESSING)
                self.redis_client.hset(f"task:{task_id}", "processing_started_at", datetime.now().isoformat())
                
                # Move from pending to processing
                self.redis_client.srem("pending_tasks", task_id)
                self.redis_client.sadd("processing_tasks", task_id)
                
                print(f"🔄 Task {task_id} marked as processing")
                return True
            return False
            
        except Exception as e:
            print(f"❌ Error marking task as processing: {str(e)}")
            return False
    
    def mark_task_completed(self, task_id: str, result: Dict) -> bool:
        """Mark task as completed with result"""
        try:
            task_data = self.redis_client.hgetall(f"task:{task_id}")
            if task_data:
                # Update task with result
                update_data = {
                    "status": TaskStatus.COMPLETED,
                    "completed_at": datetime.now().isoformat(),
                    "result": json.dumps(result)
                }
                
                # Add result fields
                for key, value in result.items():
                    if key in ['output_data', 'processing_time', 'pipeline_model', 'accuracy_score', 'speed_score', 'combined_score', 'miner_uid']:
                        update_data[key] = str(value)
                
                self.redis_client.hset(f"task:{task_id}", mapping=update_data)
                
                # Remove from processing and add to completed
                self.redis_client.srem("processing_tasks", task_id)
                self.redis_client.sadd("completed_tasks", task_id)
                
                # Remove from priority queue
                self.redis_client.zrem("task_queue", task_id)
                
                print(f"✅ Task {task_id} marked as completed")
                return True
            return False
            
        except Exception as e:
            print(f"❌ Error marking task as completed: {str(e)}")
            return False
    
    def mark_task_failed(self, task_id: str, error_message: str) -> bool:
        """Mark task as failed"""
        try:
            task_data = self.redis_client.hgetall(f"task:{task_id}")
            if task_data:
                # Check if we should retry
                retry_count = int(task_data.get('retry_count', 0))
                max_retries = int(task_data.get('max_retries', 3))
                
                if retry_count < max_retries:
                    # Retry the task
                    retry_count += 1
                    self.redis_client.hset(f"task:{task_id}", "retry_count", retry_count)
                    self.redis_client.hset(f"task:{task_id}", "status", TaskStatus.PENDING)
                    
                    # Move back to pending
                    self.redis_client.srem("processing_tasks", task_id)
                    self.redis_client.sadd("pending_tasks", task_id)
                    
                    print(f"🔄 Task {task_id} retry {retry_count}/{max_retries}")
                    return True
                else:
                    # Mark as permanently failed
                    update_data = {
                        "status": TaskStatus.FAILED,
                        "failed_at": datetime.now().isoformat(),
                        "error_message": error_message
                    }
                    self.redis_client.hset(f"task:{task_id}", mapping=update_data)
                    
                    # Remove from processing and add to failed
                    self.redis_client.srem("processing_tasks", task_id)
                    self.redis_client.sadd("failed_tasks", task_id)
                    
                    # Remove from priority queue
                    self.redis_client.zrem("task_queue", task_id)
                    
                    print(f"❌ Task {task_id} marked as permanently failed after {max_retries} retries")
                    return True
            return False
            
        except Exception as e:
            print(f"❌ Error marking task as failed: {str(e)}")
            return False
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        try:
            task_data = self.redis_client.hgetall(f"task:{task_id}")
            if task_data and task_data.get('status') == TaskStatus.PENDING:
                # Mark as cancelled
                self.redis_client.hset(f"task:{task_id}", "status", TaskStatus.CANCELLED)
                
                # Remove from pending and priority queue
                self.redis_client.srem("pending_tasks", task_id)
                self.redis_client.zrem("task_queue", task_id)
                
                print(f"🚫 Task {task_id} cancelled")
                return True
            return False
            
        except Exception as e:
            print(f"❌ Error cancelling task: {str(e)}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get the current status of a task"""
        try:
            task_data = self.redis_client.hgetall(f"task:{task_id}")
            if task_data:
                return task_data
            return None
            
        except Exception as e:
            print(f"❌ Error getting task status: {str(e)}")
            return None
    
    def list_tasks(self, status: Optional[TaskStatus] = None, limit: int = 100) -> List[Dict]:
        """List tasks with optional status filter"""
        try:
            tasks = []
            
            if status:
                # Get tasks by specific status
                status_key = f"{status.value}_tasks"
                task_ids = self.redis_client.smembers(status_key)
            else:
                # Get all task IDs
                all_keys = self.redis_client.keys("task:*")
                task_ids = [key.replace("task:", "") for key in all_keys]
            
            for task_id in list(task_ids)[:limit]:
                task_data = self.get_task_status(task_id)
                if task_data:
                    tasks.append(task_data)
            
            return tasks
            
        except Exception as e:
            print(f"❌ Error listing tasks: {str(e)}")
            return []
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            stats = {
                "pending_count": self.redis_client.scard("pending_tasks"),
                "processing_count": self.redis_client.scard("processing_tasks"),
                "completed_count": self.redis_client.scard("completed_tasks"),
                "failed_count": self.redis_client.scard("failed_tasks"),
                "queue_size": self.redis_client.zcard("task_queue"),
                "total_tasks": len(self.redis_client.keys("task:*")),
                "timestamp": datetime.now().isoformat()
            }
            return stats
            
        except Exception as e:
            print(f"❌ Error getting queue stats: {str(e)}")
            return {}
    
    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Clean up old completed/failed tasks"""
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
            cleaned_count = 0
            
            # Clean completed tasks
            completed_ids = self.redis_client.smembers("completed_tasks")
            for task_id in completed_ids:
                task_data = self.get_task_status(task_id)
                if task_data and task_data.get('completed_at'):
                    try:
                        completed_time = datetime.fromisoformat(task_data['completed_at']).timestamp()
                        if completed_time < cutoff_time:
                            self.redis_client.delete(f"task:{task_id}")
                            self.redis_client.srem("completed_tasks", task_id)
                            cleaned_count += 1
                    except:
                        continue
            
            # Clean failed tasks
            failed_ids = self.redis_client.smembers("failed_tasks")
            for task_id in failed_ids:
                task_data = self.get_task_status(task_id)
                if task_data and task_data.get('failed_at'):
                    try:
                        failed_time = datetime.fromisoformat(task_data['failed_at']).timestamp()
                        if failed_time < cutoff_time:
                            self.redis_client.delete(f"task:{task_id}")
                            self.redis_client.srem("failed_tasks", task_id)
                            cleaned_count += 1
                    except:
                        continue
            
            print(f"🧹 Cleaned up {cleaned_count} old tasks")
            return cleaned_count
            
        except Exception as e:
            print(f"❌ Error cleaning up old tasks: {str(e)}")
            return 0
    
    def _get_priority_score(self, priority: TaskPriority) -> int:
        """Convert priority to numeric score for queue ordering"""
        priority_map = {
            TaskPriority.LOW: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.HIGH: 3,
            TaskPriority.URGENT: 4
        }
        return priority_map.get(priority, 2)
    
    def health_check(self) -> bool:
        """Check if the queue manager is healthy"""
        try:
            # Test Redis connection
            self.redis_client.ping()
            return True
        except Exception as e:
            print(f"❌ Queue manager health check failed: {str(e)}")
            return False
