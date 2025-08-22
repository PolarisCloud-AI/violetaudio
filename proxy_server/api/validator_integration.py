"""
Validator Integration API for Enhanced Proxy Server
Handles communication between proxy server and validators
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from firebase_admin import firestore
from ..database.enhanced_schema import TaskStatus

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
            # Get tasks with 'completed' status
            query = self.tasks_collection.where('status', '==', TaskStatus.COMPLETED.value)
            
            # If validator_uid is provided, filter by not yet evaluated by this validator
            if validator_uid is not None:
                query = query.where('evaluated_by', '==', None)  # Not yet evaluated
            
            tasks = query.limit(10).stream()
            
            task_list = []
            for doc in tasks:
                task_data = doc.to_dict()
                task_data['id'] = doc.id
                task_list.append(task_data)
            
            return task_list
            
        except Exception as e:
            print(f"❌ Error getting tasks for evaluation: {e}")
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
