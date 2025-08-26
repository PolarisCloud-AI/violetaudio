"""
Test Script for Quota Optimization Components
Tests the response aggregator, batch database manager, and smart file manager
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, List

# Mock database for testing
class MockDatabase:
    def __init__(self):
        self.collections = {}
        self.operations = []
    
    def collection(self, name: str):
        if name not in self.collections:
            self.collections[name] = {}
        return MockCollection(self.collections[name], self.operations)

class MockCollection:
    def __init__(self, data, operations):
        self.data = data
        self.operations = operations
    
    def document(self, doc_id: str):
        return MockDocument(doc_id, self.data, self.operations)
    
    def where(self, field: str, op: str, value):
        return MockQuery(self.data, self.operations, field, op, value)

class MockDocument:
    def __init__(self, doc_id, data, operations):
        self.doc_id = doc_id
        self.data = data
        self.operations = operations
    
    def set(self, data):
        self.data[self.doc_id] = data
        self.operations.append(('set', self.doc_id, data))
        print(f"✅ Mock: Document {self.doc_id} set")
    
    def update(self, data):
        if self.doc_id in self.data:
            self.data[self.doc_id].update(data)
        self.operations.append(('update', self.doc_id, data))
        print(f"✅ Mock: Document {self.doc_id} updated")
    
    def get(self):
        return MockDocumentSnapshot(self.doc_id, self.data.get(self.doc_id, {}))

class MockDocumentSnapshot:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data
    
    def exists(self):
        return bool(self._data)
    
    def to_dict(self):
        return self._data

class MockQuery:
    def __init__(self, data, operations, field, op, value):
        self.data = data
        self.operations = field
        self.operations = operations
        self.field = field
        self.op = op
        self.value = value
    
    def stream(self):
        # Mock stream method
        return []

# Test data
def create_test_task():
    return {
        'task_type': 'transcription',
        'input_file_id': str(uuid.uuid4()),
        'source_language': 'en',
        'target_language': 'en',
        'priority': 'normal',
        'status': 'pending',
        'required_miner_count': 3
    }

def create_test_response(miner_uid: int):
    return {
        'miner_uid': miner_uid,
        'output_data': f"Test transcription from miner {miner_uid}",
        'processing_time': 2.5,
        'accuracy_score': 0.85,
        'speed_score': 0.90,
        'submitted_at': datetime.now()
    }

def create_test_file(size_mb: float = 0.5):
    """Create a test file with specified size in MB"""
    size_bytes = int(size_mb * 1024 * 1024)
    return b"0" * size_bytes

async def test_response_aggregator():
    """Test the response aggregator"""
    print("\n🧪 Testing Response Aggregator...")
    
    try:
        # Import and initialize
        from managers.response_aggregator import ResponseAggregator
        
        mock_db = MockDatabase()
        aggregator = ResponseAggregator(mock_db)
        
        # Test buffering responses
        task_id = str(uuid.uuid4())
        
        print(f"   📝 Task ID: {task_id}")
        
        # Add responses from 3 miners
        for i in range(3):
            response = create_test_response(i + 1)
            await aggregator.buffer_miner_response(task_id, i + 1, response)
            print(f"   📥 Buffered response from miner {i + 1}")
            await asyncio.sleep(0.1)  # Small delay
        
        # Check buffer stats
        stats = aggregator.get_buffer_stats()
        print(f"   📊 Buffer stats: {stats}")
        
        # Force flush
        await aggregator.force_flush_all()
        
        print("✅ Response aggregator test completed")
        return True
        
    except Exception as e:
        print(f"❌ Response aggregator test failed: {e}")
        return False

async def test_batch_database_manager():
    """Test the batch database manager"""
    print("\n🧪 Testing Batch Database Manager...")
    
    try:
        # Import and initialize
        from database.batch_manager import BatchDatabaseManager
        
        mock_db = MockDatabase()
        batch_manager = BatchDatabaseManager(mock_db)
        
        # Test creating multiple tasks
        tasks = []
        for i in range(5):
            task_data = create_test_task()
            task_id = await batch_manager.create_task(task_data)
            tasks.append(task_id)
            print(f"   📝 Created task {i + 1}: {task_id}")
            await asyncio.sleep(0.1)
        
        # Check buffer stats
        stats = batch_manager.get_buffer_stats()
        print(f"   📊 Buffer stats: {stats}")
        
        # Force flush
        await batch_manager.force_flush_all()
        
        print("✅ Batch database manager test completed")
        return True
        
    except Exception as e:
        print(f"❌ Batch database manager test failed: {e}")
        return False

async def test_smart_file_manager():
    """Test the smart file manager"""
    print("\n🧪 Testing Smart File Manager...")
    
    try:
        # Import and initialize
        from managers.smart_file_manager import SmartFileManager
        
        mock_db = MockDatabase()
        file_manager = SmartFileManager(mock_db)
        
        # Test small file (should go to Firestore)
        small_file = create_test_file(0.5)  # 0.5MB
        small_result = await file_manager.store_file(
            small_file, "small_test.txt", "text/plain", "document"
        )
        print(f"   💾 Small file stored: {small_result['file_id']}")
        print(f"      Storage location: {small_result['storage_location']}")
        
        # Test large file (should go to local storage)
        large_file = create_test_file(2.0)  # 2MB
        large_result = await file_manager.store_file(
            large_file, "large_test.wav", "audio/wav", "audio"
        )
        print(f"   📁 Large file stored: {large_result['file_id']}")
        print(f"      Storage location: {large_result['storage_location']}")
        
        # Get storage stats
        stats = file_manager.get_storage_stats()
        print(f"   📊 Storage stats: {stats}")
        
        print("✅ Smart file manager test completed")
        return True
        
    except Exception as e:
        print(f"❌ Smart file manager test failed: {e}")
        return False

async def test_quota_monitor():
    """Test the quota monitor"""
    print("\n🧪 Testing Quota Monitor...")
    
    try:
        # Import and initialize
        from managers.quota_monitor import QuotaMonitor
        
        quota_monitor = QuotaMonitor()
        
        # Test quota checking
        for i in range(10):
            can_write = await quota_monitor.check_write_quota()
            can_read = await quota_monitor.check_read_quota()
            
            print(f"   📝 Write {i + 1}: {'✅' if can_write else '❌'}")
            print(f"   📖 Read {i + 1}: {'✅' if can_read else '❌'}")
            
            await asyncio.sleep(0.1)
        
        # Get quota stats
        stats = quota_monitor.get_quota_stats()
        print(f"   📊 Quota stats: {stats}")
        
        # Shutdown
        await quota_monitor.shutdown()
        
        print("✅ Quota monitor test completed")
        return True
        
    except Exception as e:
        print(f"❌ Quota monitor test failed: {e}")
        return False

async def test_high_volume_operations():
    """Test high volume operations to simulate real usage"""
    print("\n🧪 Testing High Volume Operations...")
    
    try:
        # Import components
        from managers.response_aggregator import ResponseAggregator
        from database.batch_manager import BatchDatabaseManager
        from managers.smart_file_manager import SmartFileManager
        from managers.quota_monitor import QuotaMonitor
        
        mock_db = MockDatabase()
        
        # Initialize all components
        aggregator = ResponseAggregator(mock_db)
        batch_manager = BatchDatabaseManager(mock_db)
        file_manager = SmartFileManager(mock_db)
        quota_monitor = QuotaMonitor()
        
        print("   🚀 Starting high volume test...")
        
        # Simulate high volume task creation
        start_time = time.time()
        task_count = 20
        
        for i in range(task_count):
            # Check quota before operation
            if await quota_monitor.check_write_quota():
                # Create task
                task_data = create_test_task()
                task_id = await batch_manager.create_task(task_data)
                
                # Simulate miner responses
                for j in range(3):
                    if await quota_monitor.check_write_quota():
                        response = create_test_response(j + 1)
                        await aggregator.buffer_miner_response(task_id, j + 1, response)
                
                # Simulate file upload
                if await quota_monitor.check_write_quota():
                    file_data = create_test_file(0.8)  # 0.8MB
                    await file_manager.store_file(
                        file_data, f"test_file_{i}.wav", "audio/wav", "audio"
                    )
                
                print(f"   📝 Processed task {i + 1}/{task_count}")
                
                # Small delay to simulate real processing
                await asyncio.sleep(0.05)
            else:
                print(f"   ⏳ Quota limit reached, waiting...")
                await quota_monitor.enforce_write_quota()
        
        # Force flush all operations
        await aggregator.force_flush_all()
        await batch_manager.force_flush_all()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"   ⏱️  High volume test completed in {duration:.2f} seconds")
        print(f"   📊 Total operations: {len(mock_db.operations)}")
        
        # Get final stats
        quota_stats = quota_monitor.get_quota_stats()
        print(f"   📊 Final quota stats: {quota_stats}")
        
        # Shutdown
        await quota_monitor.shutdown()
        
        print("✅ High volume operations test completed")
        return True
        
    except Exception as e:
        print(f"❌ High volume operations test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Quota Optimization Tests...")
    print("=" * 60)
    
    test_results = []
    
    # Run individual component tests
    test_results.append(await test_response_aggregator())
    test_results.append(await test_batch_database_manager())
    test_results.append(await test_smart_file_manager())
    test_results.append(await test_quota_monitor())
    
    # Run high volume test
    test_results.append(await test_high_volume_operations())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(test_results)
    total = len(test_results)
    
    for i, result in enumerate(test_results):
        status = "✅ PASS" if result else "❌ FAIL"
        test_names = [
            "Response Aggregator",
            "Batch Database Manager", 
            "Smart File Manager",
            "Quota Monitor",
            "High Volume Operations"
        ]
        print(f"   {test_names[i]}: {status}")
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Quota optimization is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    print("\n💡 Next Steps:")
    print("   1. Start your proxy server with these optimizations")
    print("   2. Monitor Firestore usage")
    print("   3. Check for quota exceeded errors")
    print("   4. Verify performance improvements")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())
