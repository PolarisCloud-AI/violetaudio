"""
Validator Integration API for Enhanced Proxy Server
Handles communication between proxy server and validators
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from firebase_admin import firestore
from database.enhanced_schema import TaskStatus

class ValidatorIntegrationAPI:
    def __init__(self, db):
        self.db = db
        self.tasks_collection = db.collection('tasks')
        self.miner_responses_collection = db.collection('miner_responses')
        self.validators_collection = db.collection('validators')
        self.evaluations_collection = db.collection('evaluations') # Added this line
    
    async def get_tasks_for_evaluation(self, validator_uid: int = None) -> List[Dict]:
        """Get tasks that are ready for validator evaluation (status: 'completed')"""
        try:
            print(f"🔍 Getting tasks for evaluation (validator_uid: {validator_uid})")
            
            # Get tasks with 'completed' status
            query = self.tasks_collection.where('status', '==', TaskStatus.COMPLETED.value)
            
            # If validator_uid is provided, we need to check if it's already been evaluated
            # But first, let's get all completed tasks and filter in Python to avoid Firestore query issues
            print(f"   📋 Querying for completed tasks...")
            tasks = query.limit(20).stream()  # Increased limit to get more tasks
            
            task_list = []
            for doc in tasks:
                task_data = doc.to_dict()
                task_data['task_id'] = doc.id  # Use task_id for consistency
                
                # If validator_uid is provided, check if this task has already been evaluated by this validator
                if validator_uid is not None:
                    # Check if task has been evaluated by this specific validator
                    evaluated_by = task_data.get('evaluated_by')
                    if evaluated_by == validator_uid:
                        print(f"   ⏭️ Task {doc.id} already evaluated by validator {validator_uid}, skipping...")
                        continue
                
                print(f"   ✅ Processing task {doc.id} ({task_data.get('task_type', 'unknown')})")
                
                # Get the complete input file data for the validator
                input_file = task_data.get('input_file', {})
                if input_file and isinstance(input_file, dict):
                    # If input_file is a FileReference, get the actual file content
                    file_id = input_file.get('file_id')
                    if file_id:
                        try:
                            print(f"      📁 Retrieving file content for {file_id}...")
                            
                            # Get file metadata from database
                            file_doc = self.db.collection('files').document(file_id).get()
                            if file_doc.exists:
                                file_data = file_doc.to_dict()
                                
                                # Try to get content directly from file_data first
                                if file_data.get('content'):
                                    content = file_data.get('content')
                                    
                                    # Convert binary content to base64 if needed
                                    if isinstance(content, bytes):
                                        import base64
                                        base64_content = base64.b64encode(content).decode('utf-8')
                                        task_data['input_data'] = base64_content
                                        print(f"         ✅ File content found in database and converted to base64 ({len(content)} bytes -> {len(base64_content)} chars)")
                                    else:
                                        task_data['input_data'] = content
                                        print(f"         ✅ File content found in database ({len(str(content))} chars)")
                                else:
                                    # Try to construct the correct file path and read from disk
                                    local_path = file_data.get('local_path', '')
                                    if local_path:
                                        # The database path is relative, convert to absolute path
                                        import os
                                        import glob
                                        
                                        # Get file content from Firebase Cloud Storage instead of local storage
                                        try:
                                            from proxy_server.managers.file_manager import FileManager
                                            from firebase_admin import firestore
                                            
                                            # Use existing Firebase app and get Firestore client
                                            db = firestore.client()
                                            file_manager = FileManager(db)
                                            
                                            # Get file content from Firebase Cloud Storage
                                            file_content = await file_manager.download_file(file_id)
                                            
                                            if file_content:
                                                # Convert binary data to base64 string for JSON serialization
                                                import base64
                                                if isinstance(file_content, bytes):
                                                    # For binary files (audio, etc.), convert to base64
                                                    base64_content = base64.b64encode(file_content).decode('utf-8')
                                                    task_data['input_data'] = base64_content
                                                    print(f"         ✅ File content retrieved from Firebase Cloud Storage and converted to base64 ({len(file_content)} bytes -> {len(base64_content)} chars)")
                                                else:
                                                    # For text files, use as-is
                                                    task_data['input_data'] = file_content
                                                    print(f"         ✅ File content retrieved from Firebase Cloud Storage ({len(str(file_content))} chars)")
                                            else:
                                                print(f"         ❌ File content not found in Firebase Cloud Storage")
                                                task_data['input_data'] = None
                                                
                                        except Exception as read_error:
                                            print(f"         ❌ Failed to retrieve file from Firebase Cloud Storage: {read_error}")
                                            task_data['input_data'] = None
                                    else:
                                        print(f"         ❌ No local_path in file metadata")
                                        task_data['input_data'] = None
                            else:
                                print(f"         ❌ File metadata not found in database")
                                task_data['input_data'] = None
                                    
                        except Exception as e:
                            print(f"      ❌ Error retrieving file {file_id} for task {doc.id}: {e}")
                            task_data['input_data'] = None
                    else:
                        # If input_file doesn't have file_id, try to get content directly
                        task_data['input_data'] = input_file.get('content', '')
                        print(f"      ✅ Using direct file content ({len(str(task_data['input_data']))} chars)")
                else:
                    # Fallback: try to get input_data directly from task
                    task_data['input_data'] = task_data.get('input_data', '')
                    if task_data['input_data']:
                        print(f"      ✅ Using direct input_data ({len(str(task_data['input_data']))} chars)")
                    else:
                        print(f"      ⚠️ No input_data found in task")
                
                # Ensure we have the required fields for validator execution
                if not task_data.get('input_data'):
                    print(f"      ❌ Task {doc.id} missing input_data, skipping...")
                    continue
                
                print(f"      ✅ Task {doc.id} ready for validator execution")
                task_list.append(task_data)
            
            print(f"✅ Retrieved {len(task_list)} tasks with complete data for validator evaluation")
            return task_list
            
        except Exception as e:
            print(f"❌ Error getting tasks for evaluation: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def get_miner_responses_for_task(self, task_id: str) -> List[Dict]:
        """Get all miner responses for a specific task"""
        try:
            query = self.miner_responses_collection.where('task_id', '==', task_id)
            query = query.where('status', '==', 'completed')
            responses = query.stream()
            
            miner_responses = []
            for doc in responses:
                response_data = doc.to_dict()
                response_data['id'] = doc.id
                miner_responses.append(response_data)
            
            return miner_responses
            
        except Exception as e:
            print(f"❌ Error getting miner responses for task {task_id}: {e}")
            return []
    
    async def submit_validator_evaluation(self, task_id: str, validator_uid: int, evaluation_data: Dict):
        """Submit validator evaluation and rewards"""
        try:
            # Get task info
            task_doc = self.tasks_collection.document(task_id).get()  # Remove await
            if not task_doc.exists:
                raise Exception(f"Task {task_id} not found")
            
            task_data = task_doc.to_dict()
            
            # Store evaluation results
            evaluation_doc = {
                'task_id': task_id,
                'validator_uid': validator_uid,
                'evaluation_data': evaluation_data,
                'evaluated_at': firestore.SERVER_TIMESTAMP,
                'task_type': task_data.get('task_type'),
                'miner_rewards': evaluation_data.get('miner_rewards', {}),
                'overall_score': evaluation_data.get('overall_score', 0)
            }
            
            # Store in evaluations collection
            self.evaluations_collection.document(f"{task_id}_{validator_uid}").set(evaluation_doc)  # Remove await
            
            # Update task status to 'approved'
            self.tasks_collection.document(task_id).update({  # Remove await
                'status': 'approved',
                'evaluated_by': validator_uid,
                'evaluated_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            print(f"✅ Validator {validator_uid} evaluation submitted for task {task_id}")
            
        except Exception as e:
            print(f"❌ Error submitting validator evaluation: {e}")
            raise
    
    async def notify_user_final_results(self, task_id: str, evaluation_data: Dict):
        """Notify user of final validated results"""
        try:
            # Get task info
            task_doc = await self.tasks_collection.document(task_id).get()
            if not task_doc.exists:
                return
            
            task_data = task_doc.to_dict()
            
            # Prepare final result notification
            final_result = {
                'task_id': task_id,
                'status': 'approved',
                'final_response': evaluation_data.get('best_response'),
                'validator_accuracy_score': evaluation_data.get('validator_accuracy_score'),
                'miner_rewards': evaluation_data.get('rewards', {}),
                'completed_at': firestore.SERVER_TIMESTAMP
            }
            
            # Send to user callback URL if provided
            if task_data.get('callback_url'):
                await self.send_callback_notification(task_data['callback_url'], final_result)
            
            # Store final result for user retrieval
            await self.store_final_result(task_id, final_result)
            
            print(f"📢 Final results notified for task {task_id}")
            
        except Exception as e:
            print(f"❌ Error notifying user of final results: {e}")
    
    async def send_callback_notification(self, callback_url: str, final_result: Dict):
        """Send callback notification to user"""
        try:
            # This would typically make an HTTP POST request to the callback URL
            # For now, we'll just log it
            
            print(f"📤 Callback notification sent to {callback_url}")
            print(f"   Task ID: {final_result['task_id']}")
            print(f"   Status: {final_result['status']}")
            
        except Exception as e:
            print(f"❌ Error sending callback notification: {e}")
    
    async def store_final_result(self, task_id: str, final_result: Dict):
        """Store final result for user retrieval"""
        try:
            # Store in final_results collection
            final_results_collection = self.db.collection('final_results')
            await final_results_collection.document(task_id).set(final_result)
            
            print(f"💾 Final result stored for task {task_id}")
            
        except Exception as e:
            print(f"❌ Error storing final result: {e}")
    
    async def get_validator_info(self, validator_uid: int) -> Optional[Dict]:
        """Get or create validator information"""
        try:
            doc = self.validators_collection.document(str(validator_uid)).get()  # Remove await
            if doc.exists:
                return doc.to_dict()
            
            # Create new validator info
            validator_info = {
                'validator_uid': validator_uid,
                'created_at': firestore.SERVER_TIMESTAMP,
                'last_active': firestore.SERVER_TIMESTAMP,
                'total_evaluations': 0,
                'average_evaluation_time': 0
            }
            
            self.validators_collection.document(str(validator_uid)).set(validator_info)  # Remove await
            return validator_info
            
        except Exception as e:
            print(f"❌ Error getting validator info: {e}")
            return None
    
    async def register_validator(self, validator_info: Dict) -> bool:
        """Register a new validator"""
        try:
            validator_uid = validator_info.get('uid')
            if not validator_uid:
                return False
            
            # Add registration timestamp
            validator_info['registered_at'] = firestore.SERVER_TIMESTAMP
            validator_info['last_seen'] = firestore.SERVER_TIMESTAMP
            validator_info['status'] = 'active'
            
            # Store validator info
            await self.validators_collection.document(str(validator_uid)).set(validator_info)
            
            print(f"✅ Validator {validator_uid} registered successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error registering validator: {e}")
            return False
    
    async def update_validator_status(self, validator_uid: int, status: str, **kwargs):
        """Update validator status and metadata"""
        try:
            update_data = {
                'status': status,
                'last_seen': firestore.SERVER_TIMESTAMP
            }
            update_data.update(kwargs)
            
            await self.validators_collection.document(str(validator_uid)).update(update_data)
            
            print(f"✅ Validator {validator_uid} status updated to {status}")
            
        except Exception as e:
            print(f"❌ Error updating validator status: {e}")
    
    async def get_active_validators(self) -> List[Dict]:
        """Get list of active validators"""
        try:
            query = self.validators_collection.where('status', '==', 'active')
            validators = query.stream()
            
            active_validators = []
            for doc in validators:
                validator_data = doc.to_dict()
                validator_data['id'] = doc.id
                active_validators.append(validator_data)
            
            return active_validators
            
        except Exception as e:
            print(f"❌ Error getting active validators: {e}")
            return []
    
    async def get_task_evaluation_history(self, task_id: str) -> Dict[str, Any]:
        """Get evaluation history for a specific task"""
        try:
            # Get task info
            task_doc = await self.tasks_collection.document(task_id).get()
            if not task_doc.exists:
                return {'error': 'Task not found'}
            
            task_data = task_doc.to_dict()
            
            # Get miner responses
            miner_responses = await self.get_miner_responses_for_task(task_id)
            
            # Get validator evaluation if available
            validator_evaluation = task_data.get('validator_evaluation', {})
            
            return {
                'task_id': task_id,
                'task_type': task_data.get('task_type'),
                'status': task_data.get('status'),
                'miner_responses': miner_responses,
                'validator_evaluation': validator_evaluation,
                'final_rewards': task_data.get('final_rewards', {}),
                'evaluation_timeline': {
                    'created_at': task_data.get('created_at'),
                    'distributed_at': task_data.get('distributed_at'),
                    'all_miners_completed_at': task_data.get('all_miners_completed_at'),
                    'evaluated_at': task_data.get('evaluated_at')
                }
            }
            
        except Exception as e:
            print(f"❌ Error getting task evaluation history: {e}")
            return {'error': str(e)}

    async def get_task_evaluation_status(self, task_id: str) -> Dict:
        """Get task evaluation status"""
        try:
            task_doc = self.tasks_collection.document(task_id).get()  # Remove await
            if not task_doc.exists:
                return {'error': 'Task not found'}
            
            task_data = task_doc.to_dict()
            
            # Get evaluations for this task
            query = self.evaluations_collection.where('task_id', '==', task_id)
            evaluations = query.stream()
            
            evaluation_list = []
            for doc in evaluations:
                eval_data = doc.to_dict()
                eval_data['id'] = doc.id
                evaluation_list.append(eval_data)
            
            return {
                'task_id': task_id,
                'status': task_data.get('status'),
                'evaluations': evaluation_list,
                'evaluation_count': len(evaluation_list)
            }
            
        except Exception as e:
            return {'error': f'Failed to get evaluation status: {str(e)}'}
