"""
Miner Response Handler for Enhanced Proxy Server
Manages miner responses, task completion tracking, and immediate user feedback
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from firebase_admin import firestore
from ..database.enhanced_schema import TaskStatus, COLLECTIONS

class MinerResponseHandler:
    def __init__(self, db, task_manager=None):
        self.db = db
        self.task_manager = task_manager
        self.tasks_collection = db.collection('tasks')
    
    async def handle_miner_response(self, task_id: str, miner_uid: int, response_data: Dict) -> bool:
        """Handle miner response and update task status"""
        try:
            # Get task details
            task = self.task_manager.get_task(task_id)
            if not task:
                print(f"❌ Task {task_id} not found")
                return False
            
            # Prepare response data - use datetime.now() for embedded documents
            # firestore.SERVER_TIMESTAMP cannot be stored in document fields that get retrieved later
            response_doc = {
                'miner_uid': miner_uid,
                'response_data': response_data,
                'status': 'completed',
                'submitted_at': datetime.now(),
                'processing_time': response_data.get('processing_time', 0),
                'accuracy_score': response_data.get('accuracy_score', 0),
                'speed_score': response_data.get('speed_score', 0)
            }
            
            # If this is a TTS task and has audio output, store the audio file
            if task.get('task_type') == 'tts' and response_data.get('output_data'):
                try:
                    import base64
                    audio_data = base64.b64decode(response_data['output_data'])
                    
                    from ..managers.file_manager import FileManager
                    file_manager = FileManager(self.db)
                    
                    filename = f"tts_output_{task_id}_{miner_uid}.wav"
                    
                    file_id = await file_manager.upload_file(
                        audio_data,
                        filename,
                        "audio/wav",
                        file_type="tts"
                    )
                    
                    response_doc['output_file_id'] = file_id
                    response_doc['output_file_url'] = f"http://localhost:8000/api/v1/files/{file_id}"
                    
                    print(f"✅ TTS audio file stored: {file_id}")
                    
                except Exception as e:
                    print(f"⚠️  Failed to store TTS audio file: {e}")
            
            # Store response directly in task document (embedded approach)
            task_ref = self.tasks_collection.document(task_id)
            
            # Get current task data
            task_doc = task_ref.get()
            if not task_doc.exists:
                print(f"❌ Task {task_id} not found in database")
                return False
            
            current_task = task_doc.to_dict()
            miner_responses = current_task.get('miner_responses', [])
            
            # Add new response to the list
            if isinstance(miner_responses, list):
                miner_responses.append(response_doc)
            else:
                # Fallback for old dictionary format
                miner_responses = [response_doc]
            
            # Update task with embedded response - use firestore.SERVER_TIMESTAMP for top-level fields
            update_data = {
                'miner_responses': miner_responses,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            # Check if all miners completed
            assigned_miners = current_task.get('assigned_miners', [])
            if len(miner_responses) >= len(assigned_miners):
                update_data['status'] = TaskStatus.COMPLETED.value
                update_data['all_miners_completed_at'] = firestore.SERVER_TIMESTAMP
                
                # Calculate best response
                best_response = self._calculate_best_response(miner_responses)
                if best_response:
                    update_data['best_response'] = best_response
            
            # Update task document
            task_ref.update(update_data)
            
            print(f"✅ Miner {miner_uid} response stored in task {task_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error handling miner response: {e}")
            return False
    
    def _calculate_best_response(self, miner_responses: List[Dict]) -> Optional[Dict]:
        """Calculate the best response based on accuracy and speed scores"""
        try:
            if not miner_responses:
                return None
            
            # Score each response
            scored_responses = []
            for response in miner_responses:
                accuracy = response.get('accuracy_score', 0.0)
                speed = response.get('speed_score', 0.0)
                processing_time = response.get('processing_time', 0.0)
                
                # Combined score (accuracy weighted more than speed)
                combined_score = (accuracy * 0.7) + (speed * 0.3)
                
                scored_responses.append({
                    'response': response,
                    'score': combined_score,
                    'processing_time': processing_time
                })
            
            # Sort by score (highest first), then by processing time (lowest first)
            scored_responses.sort(key=lambda x: (x['score'], -x['processing_time']), reverse=True)
            
            # Return the best response
            return scored_responses[0]['response']
            
        except Exception as e:
            print(f"⚠️ Error calculating best response: {e}")
            return None
    
    async def get_task_completion_status(self, task_id: str) -> Dict[str, Any]:
        """Get task completion status and miner response summary"""
        try:
            task_doc = self.tasks_collection.document(task_id).get()
            if not task_doc.exists:
                return {'error': 'Task not found'}
            
            task_data = task_doc.to_dict()
            miner_responses = task_data.get('miner_responses', [])
            
            response_statuses = {}
            completed_count = 0
            
            # Handle miner_responses as a list (enhanced schema)
            if isinstance(miner_responses, list):
                for response in miner_responses:
                    miner_uid = response.get('miner_uid')
                    status = response.get('status', 'pending')
                    
                    if miner_uid:
                        response_statuses[miner_uid] = {
                            'status': status,
                            'processing_time': response.get('processing_time'),
                            'accuracy_score': response.get('accuracy_score'),
                            'speed_score': response.get('speed_score')
                        }
                        
                        if status == 'completed':
                            completed_count += 1
            else:
                # Fallback for old dictionary format
                for miner_uid, response in miner_responses.items():
                    status = response.get('status', 'pending')
                    
                    response_statuses[miner_uid] = {
                        'status': status,
                        'processing_time': response.get('processing_time'),
                        'accuracy_score': response.get('accuracy_score'),
                        'speed_score': response.get('speed_score')
                    }
                    
                    if status == 'completed':
                        completed_count += 1
            
            return {
                'task_id': task_id,
                'status': task_data['status'],
                'required_miners': task_data.get('required_miner_count', 3),
                'assigned_miners': len(task_data.get('assigned_miners', [])),
                'completed_miners': completed_count,
                'miner_statuses': response_statuses,
                'first_response': task_data.get('first_response'),
                'all_completed_at': task_data.get('all_miners_completed_at'),
                'best_response': task_data.get('best_response')
            }
            
        except Exception as e:
            print(f"❌ Error getting task completion status: {e}")
            return {'error': str(e)}
    
    async def get_best_response(self, task_id: str) -> Optional[Dict]:
        """Get the best response for a completed task"""
        try:
            task_doc = self.tasks_collection.document(task_id).get()
            if not task_doc.exists:
                return None
            
            task_data = task_doc.to_dict()
            return task_data.get('best_response')
            
        except Exception as e:
            print(f"❌ Error getting best response: {e}")
            return None
    
    async def check_all_miners_completed(self, task_id: str) -> bool:
        """Check if all assigned miners have completed the task"""
        try:
            completion_status = await self.get_task_completion_status(task_id)
            
            if 'error' in completion_status:
                return False
            
            assigned_count = completion_status.get('assigned_miners', 0)
            completed_count = completion_status.get('completed_miners', 0)
            
            return assigned_count > 0 and assigned_count == completed_count
            
        except Exception as e:
            print(f"❌ Error checking miner completion: {e}")
            return False
    
    async def _update_task_status(self, task_id: str, status: str, **kwargs):
        """Update task status with additional fields"""
        try:
            update_data = {
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            update_data.update(kwargs)
            
            self.tasks_collection.document(task_id).update(update_data)
            
        except Exception as e:
            print(f"❌ Error updating task status: {e}")
    
    async def notify_validators_task_ready(self, task_id: str):
        """Notify validators that a task is ready for evaluation"""
        try:
            # Update task status to indicate it's ready for validator evaluation
            await self._update_task_status(task_id, 'ready_for_evaluation')
            
            print(f"📢 Task {task_id} marked as ready for validator evaluation")
            
        except Exception as e:
            print(f"❌ Error notifying validators: {e}")
    
    async def cleanup_failed_responses(self, task_id: str):
        """Clean up failed or invalid miner responses"""
        try:
            task_doc = self.tasks_collection.document(task_id).get()
            if not task_doc.exists:
                return
            
            task_data = task_doc.to_dict()
            miner_responses = task_data.get('miner_responses', [])
            
            # Filter out failed responses
            valid_responses = []
            for response in miner_responses:
                if response.get('status') != 'failed':
                    valid_responses.append(response)
            
            # Update task with cleaned responses
            if len(valid_responses) != len(miner_responses):
                self.tasks_collection.document(task_id).update({
                    'miner_responses': valid_responses,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                
                print(f"🧹 Cleaned up failed responses for task {task_id}")
            
        except Exception as e:
            print(f"❌ Error cleaning up failed responses: {e}")
