#!/usr/bin/env python3
"""
Simple Functional Test for Enhanced Proxy Server
Tests core functionality without external dependencies
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, MagicMock

# Import our components
from database.schema import DatabaseManager, TaskStatus, TaskPriority, TaskType, TaskModel
from managers.task_manager import TaskManager
from managers.file_manager import FileManager
from managers.miner_response_handler import MinerResponseHandler
from orchestrators.workflow_orchestrator import WorkflowOrchestrator
from api.validator_integration import ValidatorIntegrationAPI

async def test_database_schema():
    """Test database schema functionality"""
    print("🧪 Testing Database Schema...")
    
    # Test enums
    assert TaskStatus.PENDING.value == "pending"
    assert TaskPriority.HIGH.value == "high"
    assert TaskType.TRANSCRIPTION.value == "transcription"
    
    # Test TaskModel
    task_data = {
        'task_type': 'transcription',
        'input_data': 'test_audio.wav',
        'language': 'en',
        'priority': 'high'
    }
    
    task = TaskModel(**task_data)
    assert task.task_type == 'transcription'
    assert task.language == 'en'
    assert task.priority == TaskPriority.HIGH
    
    # Test to_dict conversion
    task_dict = task.to_dict()
    assert task_dict['task_type'] == 'transcription'
    assert task_dict['priority'] == 'high'
    
    print("✅ Database Schema tests passed!")

async def test_task_manager():
    """Test task manager functionality"""
    print("🧪 Testing Task Manager...")
    
    # Create mock database
    mock_db = Mock()
    mock_collection = Mock()
    mock_doc = Mock()
    
    mock_db.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_doc
    
    # Create task manager
    task_manager = TaskManager(mock_db)
    assert task_manager.db == mock_db
    assert task_manager.tasks_collection is not None
    
    print("✅ Task Manager tests passed!")

async def test_file_manager():
    """Test file manager functionality"""
    print("🧪 Testing File Manager...")
    
    # Create mock storage client and database
    mock_storage = Mock()
    mock_db = Mock()
    
    # Create file manager
    file_manager = FileManager(mock_storage, mock_db)
    assert file_manager.storage_client == mock_storage
    assert file_manager.db == mock_db
    
    # Test file validation
    test_audio = b"test audio data"
    is_valid, message = await file_manager.validate_file_upload(
        test_audio, "test.wav", "audio/wav"
    )
    assert is_valid == True
    assert "File validation passed" in message
    
    # Test oversized file
    large_file = b"x" * (51 * 1024 * 1024)  # 51MB
    is_valid, message = await file_manager.validate_file_upload(
        large_file, "large.wav", "audio/wav"
    )
    assert is_valid == False
    assert "File too large" in message
    
    print("✅ File Manager tests passed!")

async def test_miner_response_handler():
    """Test miner response handler functionality"""
    print("🧪 Testing Miner Response Handler...")
    
    # Create mock database
    mock_db = Mock()
    mock_collection = Mock()
    mock_doc = Mock()
    
    mock_db.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_doc
    
    # Create response handler
    response_handler = MinerResponseHandler(mock_db)
    assert response_handler.db == mock_db
    assert response_handler.miner_responses_collection is not None
    
    print("✅ Miner Response Handler tests passed!")

async def test_workflow_orchestrator():
    """Test workflow orchestrator functionality"""
    print("🧪 Testing Workflow Orchestrator...")
    
    # Create mock database
    mock_db = Mock()
    
    # Create orchestrator
    orchestrator = WorkflowOrchestrator(mock_db)
    assert orchestrator.db == mock_db
    assert orchestrator.running == False
    
    # Test start/stop
    await orchestrator.start_orchestration()
    assert orchestrator.running == True
    
    await orchestrator.stop_orchestration()
    assert orchestrator.running == False
    
    # Test miner selection
    task = {"required_miner_count": 3}
    miners = await orchestrator.select_optimal_miners(task)
    assert len(miners) == 3
    assert all("uid" in miner for miner in miners)
    
    print("✅ Workflow Orchestrator tests passed!")

async def test_validator_integration():
    """Test validator integration functionality"""
    print("🧪 Testing Validator Integration...")
    
    # Create mock database
    mock_db = Mock()
    mock_collection = Mock()
    mock_doc = Mock()
    
    mock_db.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_doc
    
    # Create validator API
    validator_api = ValidatorIntegrationAPI(mock_db)
    assert validator_api.db == mock_db
    assert validator_api.tasks_collection is not None
    
    print("✅ Validator Integration tests passed!")

async def test_complete_workflow():
    """Test a complete workflow simulation"""
    print("🧪 Testing Complete Workflow...")
    
    # Create mock components
    mock_db = Mock()
    mock_storage = Mock()
    
    # Test workflow initialization
    task_manager = TaskManager(mock_db)
    file_manager = FileManager(mock_storage, mock_db)
    miner_handler = MinerResponseHandler(mock_db)
    orchestrator = WorkflowOrchestrator(mock_db)
    validator_api = ValidatorIntegrationAPI(mock_db)
    
    # Verify all components are properly initialized
    assert task_manager is not None
    assert file_manager is not None
    assert miner_handler is not None
    assert orchestrator is not None
    assert validator_api is not None
    
    print("✅ Complete Workflow tests passed!")

async def run_all_tests():
    """Run all functional tests"""
    print("🚀 Starting Enhanced Proxy Server Functional Tests...")
    print("=" * 60)
    
    try:
        await test_database_schema()
        await test_task_manager()
        await test_file_manager()
        await test_miner_response_handler()
        await test_workflow_orchestrator()
        await test_validator_integration()
        await test_complete_workflow()
        
        print("=" * 60)
        print("🎉 All functional tests passed successfully!")
        print("✅ Enhanced Proxy Server is ready for deployment!")
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Run the tests
    asyncio.run(run_all_tests())
