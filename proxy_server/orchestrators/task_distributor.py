"""
Task Distributor for Enhanced Proxy Server
Intelligently distributes tasks to available miners based on their status and capabilities.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import firebase_admin
from firebase_admin import firestore

class TaskDistributor:
    """Distributes tasks to available miners intelligently"""
    
    def __init__(self, db, task_manager, miner_status_manager):
        self.db = db
        self.task_manager = task_manager
        self.miner_status_manager = miner_status_manager
        self.tasks_collection = db.collection('tasks')
        self.distribution_interval = 30  # 30 seconds
        self.max_retries = 3
        self.retry_delay = 60  # 1 minute
        
    async def start_distribution(self):
        """Start the task distribution loop"""
        print("🚀 Starting task distribution service...")
        
        try:
            while True:
                await self.distribution_loop()
                await asyncio.sleep(self.distribution_interval)
                
        except Exception as e:
            print(f"❌ Task distribution service failed: {e}")
            # Restart after delay
            await asyncio.sleep(self.retry_delay)
            await self.start_distribution()
    
    async def distribution_loop(self):
        """Main distribution loop"""
        try:
            print("🔄 Running task distribution loop...")
            
            # Get pending tasks
            pending_tasks = await self._get_pending_tasks()
            
            if not pending_tasks:
                print("   No pending tasks to distribute")
                return
            
            print(f"   Found {len(pending_tasks)} pending tasks")
            
            # Get available miners
            available_miners = await self.miner_status_manager.get_available_miners()
            
            if not available_miners:
                print("   No available miners for task distribution")
                return
            
            print(f"   Found {len(available_miners)} available miners")
            
            # Distribute tasks
            distributed_count = 0
            for task in pending_tasks:
                if await self._distribute_single_task(task, available_miners):
                    distributed_count += 1
            
            print(f"   Successfully distributed {distributed_count}/{len(pending_tasks)} tasks")
            
        except Exception as e:
            print(f"❌ Error in distribution loop: {e}")
    
    async def _get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks that are pending distribution"""
        try:
            # Query for pending tasks
            query = self.tasks_collection.where('status', '==', 'pending').limit(50)
            docs = query.stream()
            
            pending_tasks = []
            for doc in docs:
                task_data = doc.to_dict()
                pending_tasks.append(task_data)
            
            return pending_tasks
            
        except Exception as e:
            print(f"❌ Error getting pending tasks: {e}")
            return []
    
    async def _distribute_single_task(self, task: Dict[str, Any], available_miners: List[Dict[str, Any]]) -> bool:
        """Distribute a single task to appropriate miners"""
        try:
            task_id = task.get('task_id')
            task_type = task.get('task_type')
            required_count = task.get('required_miner_count', 1)
            current_status = task.get('status')
            
            print(f"   📋 Distributing task {task_id} ({task_type}) to {required_count} miners")
            
            # 🔒 DUPLICATE PROTECTION: Check task status before distribution
            if current_status in ['completed', 'failed', 'cancelled']:
                print(f"      ⚠️ Task {task_id} has status '{current_status}', skipping distribution")
                return False
            
            if current_status == 'assigned':
                print(f"      ⚠️ Task {task_id} is already assigned to miners, skipping duplicate distribution")
                return False
            
            if current_status == 'in_progress':
                print(f"      ⚠️ Task {task_id} is already in progress, skipping duplicate distribution")
                return False
            
            print(f"      ✅ Task {task_id} status '{current_status}' is valid for distribution")
            
            # Ensure we have enough available miners
            if len(available_miners) < required_count:
                print(f"      ⚠️ Only {len(available_miners)} miners available, but task requires {required_count}")
                # Adjust required count to available miners, but ensure minimum of 1
                required_count = max(1, len(available_miners))
                print(f"      🔄 Adjusted required count to {required_count}")
            
            # Select optimal miners for this task
            selected_miners = self._select_optimal_miners(task, available_miners, required_count)
            
            if not selected_miners:
                print(f"      ❌ No suitable miners found for task {task_id}")
                return False
            
            print(f"      ✅ Selected {len(selected_miners)} miners: {[m['uid'] for m in selected_miners]}")
            
            # Assign task to selected miners
            success = await self._assign_task_to_miners(task_id, selected_miners)
            
            if success:
                print(f"      ✅ Task {task_id} successfully assigned to miners")
                return True
            else:
                print(f"      ❌ Failed to assign task {task_id} to miners")
                return False
                
        except Exception as e:
            print(f"❌ Error distributing single task: {e}")
            return False
    
    def _select_optimal_miners(self, task: Dict[str, Any], available_miners: List[Dict[str, Any]], 
                              required_count: int) -> List[Dict[str, Any]]:
        """Select optimal miners for a specific task"""
        try:
            task_type = task.get('task_type')
            
            # Filter miners by task type specialization if available
            suitable_miners = []
            for miner in available_miners:
                # Check if miner can handle this task type
                if self._can_miner_handle_task(miner, task_type):
                    suitable_miners.append(miner)
            
            if not suitable_miners:
                print(f"      ⚠️ No miners specialized for task type: {task_type}")
                # Fall back to all available miners
                suitable_miners = available_miners
            
            # Sort by availability score (higher is better)
            suitable_miners.sort(key=lambda x: x.get('availability_score', 0), reverse=True)
            
            # Select the best miners up to required count
            selected_miners = suitable_miners[:required_count]
            
            return selected_miners
            
        except Exception as e:
            print(f"❌ Error selecting optimal miners: {e}")
            return []
    
    def _can_miner_handle_task(self, miner: Dict[str, Any], task_type: str) -> bool:
        """Check if a miner can handle a specific task type"""
        try:
            # If miner has no specialization, assume it can handle all tasks
            specialization = miner.get('task_type_specialization')
            if not specialization:
                return True
            
            # Check if task type is in miner's specialization
            return task_type in specialization
            
        except Exception as e:
            print(f"⚠️ Error checking miner task compatibility: {e}")
            return True  # Default to allowing the task
    
    async def _assign_task_to_miners(self, task_id: str, selected_miners: List[Dict[str, Any]]) -> bool:
        """Assign a task to the selected miners"""
        try:
            # Create assignments for each miner
            assignments = []
            miner_uids = []
            
            for miner in selected_miners:
                assignment = {
                    'assignment_id': self._generate_assignment_id(),
                    'miner_uid': miner['uid'],
                    'assigned_at': datetime.utcnow(),
                    'status': 'pending'
                }
                assignments.append(assignment)
                miner_uids.append(miner['uid'])
            
            # Update task with assignments
            task_ref = self.tasks_collection.document(task_id)
            task_ref.update({
                'assigned_miners': miner_uids,
                'task_assignments': assignments,
                'status': 'assigned',
                'distributed_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            
            # Update miner load
            for miner in selected_miners:
                await self._update_miner_load(miner['uid'], increment=True)
            
            return True
            
        except Exception as e:
            print(f"❌ Error assigning task to miners: {e}")
            return False
    
    def get_duplicate_protection_stats(self) -> Dict[str, Any]:
        """Get statistics about duplicate distribution protection"""
        try:
            # Count tasks by status to analyze distribution patterns
            status_counts = {}
            total_tasks = 0
            skipped_distributions = 0
            
            # Query all tasks to analyze status patterns
            docs = self.tasks_collection.stream()
            for doc in docs:
                task_data = doc.to_dict()
                status = task_data.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                total_tasks += 1
                
                # Count tasks that would be skipped due to duplicate protection
                if status in ['completed', 'failed', 'cancelled', 'assigned', 'in_progress']:
                    skipped_distributions += 1
            
            return {
                'duplicate_protection_active': True,
                'total_tasks': total_tasks,
                'status_distribution': status_counts,
                'tasks_protected_from_duplicate_distribution': skipped_distributions,
                'duplicate_protection_effectiveness': f"{(skipped_distributions / total_tasks * 100):.2f}%" if total_tasks > 0 else "100%"
            }
        except Exception as e:
            print(f"⚠️ Error getting duplicate protection stats: {e}")
            return {'error': str(e)}
    
    async def _update_miner_load(self, miner_uid: int, increment: bool = True):
        """Update miner's current load"""
        try:
            # Get current miner status
            miner_doc_ref = self.miner_status_manager.miner_status_collection.document(str(miner_uid))
            miner_doc = miner_doc_ref.get()
            
            if miner_doc.exists:
                miner_data = miner_doc.to_dict()
                current_load = miner_data.get('current_load', 0.0)
                max_capacity = miner_data.get('max_capacity', 100.0)
                
                # Update load
                if increment:
                    new_load = min(max_capacity, current_load + 1.0)
                else:
                    new_load = max(0.0, current_load - 1.0)
                
                # Update the document
                miner_doc_ref.update({
                    'current_load': new_load,
                    'updated_at': datetime.utcnow()
                })
                
        except Exception as e:
            print(f"⚠️ Error updating miner load: {e}")
    
    def _generate_assignment_id(self) -> str:
        """Generate a unique assignment ID"""
        import uuid
        return str(uuid.uuid4())
    
    async def get_distribution_stats(self) -> Dict[str, Any]:
        """Get task distribution statistics"""
        try:
            # Get task counts by status
            status_counts = {}
            statuses = ['pending', 'assigned', 'in_progress', 'completed', 'failed']
            
            for status in statuses:
                query = self.tasks_collection.where('status', '==', status)
                docs = query.stream()
                count = len(list(docs))
                status_counts[status] = count
            
            # Get miner assignment counts
            total_assignments = sum(status_counts.get('assigned', 0), 
                                  status_counts.get('in_progress', 0))
            
            # Get available miners count
            available_miners = await self.miner_status_manager.get_available_miners()
            
            return {
                'task_status_counts': status_counts,
                'total_assignments': total_assignments,
                'available_miners': len(available_miners),
                'distribution_health': 'healthy' if available_miners else 'no_miners'
            }
            
        except Exception as e:
            print(f"❌ Error getting distribution stats: {e}")
            return {
                'task_status_counts': {},
                'total_assignments': 0,
                'available_miners': 0,
                'distribution_health': 'error'
            }
    
    async def cleanup_failed_assignments(self):
        """Clean up failed or stale task assignments"""
        try:
            current_time = datetime.utcnow()
            timeout_threshold = current_time - timedelta(minutes=30)  # 30 minutes
            
            # Find tasks with failed assignments
            query = self.tasks_collection.where('status', '==', 'assigned')
            docs = query.stream()
            
            cleaned_count = 0
            for doc in docs:
                task_data = doc.to_dict()
                distributed_at = task_data.get('distributed_at')
                
                if distributed_at and distributed_at < timeout_threshold:
                    # Check if any miners have responded
                    miner_responses = task_data.get('miner_responses', [])
                    
                    if not miner_responses:
                        # No responses, mark as failed
                        doc.reference.update({
                            'status': 'failed',
                            'updated_at': datetime.utcnow()
                        })
                        cleaned_count += 1
            
            if cleaned_count > 0:
                print(f"🧹 Cleaned up {cleaned_count} failed task assignments")
                
        except Exception as e:
            print(f"⚠️ Error cleaning up failed assignments: {e}")
    
    async def redistribute_failed_tasks(self):
        """Redistribute tasks that have failed"""
        try:
            # Get failed tasks
            query = self.tasks_collection.where('status', '==', 'failed')
            docs = query.stream()
            
            redistributed_count = 0
            for doc in docs:
                task_data = doc.to_dict()
                task_id = task_data.get('task_id')
                
                # Reset task to pending for redistribution
                doc.reference.update({
                    'status': 'pending',
                    'assigned_miners': [],
                    'task_assignments': [],
                    'miner_responses': [],
                    'updated_at': datetime.utcnow()
                })
                
                redistributed_count += 1
                print(f"🔄 Redistributed failed task {task_id}")
            
            if redistributed_count > 0:
                print(f"✅ Redistributed {redistributed_count} failed tasks")
                
        except Exception as e:
            print(f"⚠️ Error redistributing failed tasks: {e}")
    
    async def emergency_distribution(self, task_id: str, miner_uids: List[int]) -> bool:
        """Emergency task distribution to specific miners"""
        try:
            print(f"🚨 Emergency distribution of task {task_id} to miners {miner_uids}")
            
            # Force assign task to specified miners
            success = await self._assign_task_to_miners(task_id, 
                                                      [{'uid': uid} for uid in miner_uids])
            
            if success:
                print(f"✅ Emergency distribution successful for task {task_id}")
            else:
                print(f"❌ Emergency distribution failed for task {task_id}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error in emergency distribution: {e}")
            return False
