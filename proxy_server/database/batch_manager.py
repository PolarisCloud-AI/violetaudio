"""
Batch Database Manager for Enhanced Proxy Server
Buffers database operations and executes them in batches to reduce Firestore quota usage
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict
from firebase_admin import firestore
import uuid

class BatchDatabaseManager:
    def __init__(self, db):
        self.db = db
        self.operation_buffer = defaultdict(list)
        self.buffer_size = 100  # Firestore batch limit is 500, use 100 to be safe
        self.flush_interval = 30  # Flush every 30 seconds
        self.last_flush = time.time()
        self.flush_lock = asyncio.Lock()
        
        # Start background flush timer
        asyncio.create_task(self._background_flush_timer())
    
    async def buffered_write(self, operation: Dict):
        """Buffer a database operation for batch execution"""
        try:
            operation_type = operation.get('type', 'unknown')
            
            # Add operation to buffer
            self.operation_buffer[operation_type].append(operation)
            
            print(f"📝 Buffered {operation_type} operation")
            print(f"   Buffer size for {operation_type}: {len(self.operation_buffer[operation_type])}")
            
            # Check if buffer is full
            if len(self.operation_buffer[operation_type]) >= self.buffer_size:
                await self._flush_operation_type(operation_type)
                
        except Exception as e:
            print(f"❌ Error buffering operation: {e}")
            raise
    
    async def _flush_operation_type(self, operation_type: str):
        """Flush operations of a specific type"""
        async with self.flush_lock:
            operations = self.operation_buffer[operation_type]
            
            if not operations:
                return
            
            try:
                print(f"🔄 Flushing {len(operations)} {operation_type} operations...")
                
                # Create batch
                batch = self.db.batch()
                operation_count = 0
                
                for operation in operations:
                    try:
                        if operation['type'] == 'set':
                            batch.set(operation['ref'], operation['data'])
                        elif operation['type'] == 'update':
                            batch.update(operation['ref'], operation['data'])
                        elif operation['type'] == 'delete':
                            batch.delete(operation['ref'])
                        
                        operation_count += 1
                        
                    except Exception as e:
                        print(f"⚠️ Error preparing operation: {e}")
                        continue
                
                if operation_count > 0:
                    # Commit batch
                    batch.commit()
                    print(f"✅ Successfully committed {operation_count} {operation_type} operations")
                    
                    # Clear buffer for this operation type
                    self.operation_buffer[operation_type].clear()
                    
                    # Update last flush time
                    self.last_flush = time.time()
                    
                else:
                    print(f"⚠️ No valid operations to commit for {operation_type}")
                    
            except Exception as e:
                print(f"❌ Batch flush failed for {operation_type}: {e}")
                # Keep operations in buffer for retry
                print(f"   Operations kept in buffer for retry")
    
    async def _background_flush_timer(self):
        """Background task to flush operations based on time intervals"""
        while True:
            try:
                current_time = time.time()
                
                # Check if it's time to flush
                if current_time - self.last_flush >= self.flush_interval:
                    await self._flush_all_operation_types()
                
                # Sleep for a short interval
                await asyncio.sleep(10)
                
            except Exception as e:
                print(f"❌ Background flush timer error: {e}")
                await asyncio.sleep(30)  # Longer sleep on error
    
    async def _flush_all_operation_types(self):
        """Flush all operation types that have pending operations"""
        try:
            print(f"🔄 Time-based flush check...")
            
            for operation_type, operations in self.operation_buffer.items():
                if operations:
                    print(f"   Flushing {len(operations)} {operation_type} operations")
                    await self._flush_operation_type(operation_type)
                    
        except Exception as e:
            print(f"❌ Flush all operation types failed: {e}")
    
    async def force_flush_all(self):
        """Force flush all buffered operations (useful for shutdown)"""
        try:
            print(f"🔄 Force flushing all buffered operations...")
            
            for operation_type in list(self.operation_buffer.keys()):
                await self._flush_operation_type(operation_type)
            
            print(f"✅ All operations flushed")
            
        except Exception as e:
            print(f"❌ Force flush failed: {e}")
    
    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get statistics about current buffer state"""
        try:
            stats = {}
            total_operations = 0
            
            for operation_type, operations in self.operation_buffer.items():
                count = len(operations)
                stats[operation_type] = count
                total_operations += count
            
            stats.update({
                'total_buffered_operations': total_operations,
                'buffer_size_limit': self.buffer_size,
                'flush_interval': self.flush_interval,
                'last_flush': self.last_flush,
                'time_since_last_flush': time.time() - self.last_flush
            })
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}
    
    def clear_buffer(self):
        """Clear all buffered operations (use with caution)"""
        try:
            for operation_type in self.operation_buffer:
                self.operation_buffer[operation_type].clear()
            print("🧹 Operation buffer cleared")
        except Exception as e:
            print(f"❌ Buffer clear failed: {e}")
    
    # Convenience methods for common operations
    async def create_document(self, collection: str, data: Dict, doc_id: str = None) -> str:
        """Create a document with buffered write"""
        if not doc_id:
            doc_id = str(uuid.uuid4())
        
        doc_ref = self.db.collection(collection).document(doc_id)
        
        operation = {
            'type': 'set',
            'ref': doc_ref,
            'data': data
        }
        
        await self.buffered_write(operation)
        return doc_id
    
    async def update_document(self, collection: str, doc_id: str, data: Dict):
        """Update a document with buffered write"""
        doc_ref = self.db.collection(collection).document(doc_id)
        
        operation = {
            'type': 'update',
            'ref': doc_ref,
            'data': data
        }
        
        await self.buffered_write(operation)
    
    async def delete_document(self, collection: str, doc_id: str):
        """Delete a document with buffered write"""
        doc_ref = self.db.collection(collection).document(doc_id)
        
        operation = {
            'type': 'delete',
            'ref': doc_ref,
            'data': {}
        }
        
        await self.buffered_write(operation)
    
    async def create_task(self, task_data: Dict) -> str:
        """Create a task using batch operations"""
        try:
            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Add metadata
            task_data.update({
                'task_id': task_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            # Use batch operation
            await self.create_document('tasks', task_data, task_id)
            
            print(f"✅ Task queued for creation: {task_id}")
            return task_id
            
        except Exception as e:
            print(f"❌ Error creating task: {e}")
            raise
    
    async def update_task_status(self, task_id: str, status: str, additional_data: Dict = None):
        """Update task status using batch operations"""
        try:
            update_data = {
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            if additional_data:
                update_data.update(additional_data)
            
            await self.update_document('tasks', task_id, update_data)
            
            print(f"✅ Task status update queued: {task_id} -> {status}")
            
        except Exception as e:
            print(f"❌ Error updating task status: {e}")
            raise
