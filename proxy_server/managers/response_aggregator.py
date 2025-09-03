"""
Response Aggregator for Enhanced Proxy Server
Buffers miner responses and flushes them in batches to reduce Firestore quota usage
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict
from firebase_admin import firestore
import time

class ResponseAggregator:
    def __init__(self, db):
        self.db = db
        self.response_buffer = defaultdict(list)
        self.buffer_timeout = 60  # 60 seconds
        self.min_responses_to_flush = 3  # Flush after 3 miners respond
        self.last_flush_check = time.time()
        self.flush_check_interval = 30  # Check for timeouts every 30 seconds
        
        # Start background flush checker
        asyncio.create_task(self._background_flush_checker())
    
    async def buffer_miner_response(self, task_id: str, miner_uid: int, response: Dict):
        """Buffer miner response instead of immediate database update"""
        try:
            # Add response to buffer
            self.response_buffer[task_id].append({
                'miner_uid': miner_uid,
                'response': response,
                'timestamp': datetime.now()
            })
            
            print(f"📥 Buffered response from miner {miner_uid} for task {task_id}")
            print(f"   Buffer size: {len(self.response_buffer[task_id])}")
            
            # Check if we should flush this task's responses
            await self._check_flush_task(task_id)
            
        except Exception as e:
            print(f"❌ Error buffering response: {e}")
    
    async def _check_flush_task(self, task_id: str):
        """Check if task responses should be flushed to database"""
        responses = self.response_buffer[task_id]
        
        if not responses:
            return
        
        # Flush if:
        # 1. We have enough responses (3+ miners)
        # 2. Timeout reached
        # 3. Task is completed
        
        should_flush = (
            len(responses) >= self.min_responses_to_flush or
            (datetime.now() - responses[0]['timestamp']).seconds >= self.buffer_timeout
        )
        
        if should_flush:
            await self._flush_task_responses(task_id)
    
    async def _flush_task_responses(self, task_id: str):
        """Flush all buffered responses for a task in ONE database operation"""
        responses = self.response_buffer[task_id]
        
        if not responses:
            return
        
        try:
            print(f"🔄 Flushing {len(responses)} responses for task {task_id}")
            
            # Prepare response data for database
            response_data = []
            for r in responses:
                response_info = {
                    'miner_uid': r['miner_uid'],
                    'response': r['response'],
                    'submitted_at': r['timestamp']
                }
                response_data.append(response_info)
            
            # Single batch update instead of multiple individual updates
            batch = self.db.batch()
            
            # Update task with all responses at once
            task_ref = self.db.collection('tasks').document(task_id)
            batch.update(task_ref, {
                'miner_responses': firestore.ArrayUnion(response_data),
                'response_count': firestore.Increment(len(responses)),
                'last_response_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'status': 'processing' if len(responses) < 5 else 'completed'
            })
            
            # Commit batch
            batch.commit()
            
            # Clear buffer for this task
            del self.response_buffer[task_id]
            
            print(f"✅ Successfully flushed {len(responses)} responses for task {task_id}")
            
        except Exception as e:
            print(f"❌ Response flush failed for task {task_id}: {e}")
            # Keep responses in buffer for retry
            print(f"   Responses kept in buffer for retry")
    
    async def _background_flush_checker(self):
        """Background task to check for timeouts and flush old responses"""
        while True:
            try:
                current_time = time.time()
                
                # Check if it's time to look for timeouts
                if current_time - self.last_flush_check >= self.flush_check_interval:
                    await self._check_timeouts()
                    self.last_flush_check = current_time
                
                # Sleep for a short interval
                await asyncio.sleep(10)
                
            except Exception as e:
                print(f"❌ Background flush checker error: {e}")
                await asyncio.sleep(30)  # Longer sleep on error
    
    async def _check_timeouts(self):
        """Check for tasks with timed-out responses and flush them"""
        try:
            current_time = datetime.now()
            tasks_to_flush = []
            
            for task_id, responses in self.response_buffer.items():
                if not responses:
                    continue
                
                # Check if oldest response has timed out
                oldest_response = min(responses, key=lambda x: x['timestamp'])
                time_since_oldest = (current_time - oldest_response['timestamp']).seconds
                
                if time_since_oldest >= self.buffer_timeout:
                    tasks_to_flush.append(task_id)
            
            # Flush timed-out tasks
            for task_id in tasks_to_flush:
                print(f"⏰ Flushing timed-out responses for task {task_id}")
                await self._flush_task_responses(task_id)
                
        except Exception as e:
            print(f"❌ Timeout check failed: {e}")
    
    async def force_flush_all(self):
        """Force flush all buffered responses (useful for shutdown)"""
        try:
            print(f"🔄 Force flushing all buffered responses...")
            
            task_ids = list(self.response_buffer.keys())
            for task_id in task_ids:
                await self._flush_task_responses(task_id)
            
            print(f"✅ All responses flushed")
            
        except Exception as e:
            print(f"❌ Force flush failed: {e}")
    
    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get statistics about current buffer state"""
        try:
            total_responses = sum(len(responses) for responses in self.response_buffer.values())
            total_tasks = len(self.response_buffer)
            
            return {
                'buffered_tasks': total_tasks,
                'buffered_responses': total_responses,
                'buffer_timeout': self.buffer_timeout,
                'min_responses_to_flush': self.min_responses_to_flush,
                'tasks_in_buffer': list(self.response_buffer.keys())
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def clear_buffer(self):
        """Clear all buffered responses (use with caution)"""
        try:
            self.response_buffer.clear()
            print("🧹 Response buffer cleared")
        except Exception as e:
            print(f"❌ Buffer clear failed: {e}")
