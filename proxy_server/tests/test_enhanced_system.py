"""
Comprehensive Test Suite for Enhanced Proxy Server
Tests all crucial functionality to ensure system reliability
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the components to test
from database.schema import DatabaseManager, TaskStatus, TaskPriority, TaskType
from managers.task_manager import TaskManager
from managers.file_manager import FileManager
from managers.miner_response_handler import MinerResponseHandler
from orchestrators.workflow_orchestrator import WorkflowOrchestrator
from api.validator_integration import ValidatorIntegrationAPI

class TestDatabaseManager:
    """Test database initialization and management"""
    
    def test_database_manager_initialization(self):
        """Test database manager creation"""
        db_manager = DatabaseManager("db/violet.json")
        assert db_manager.credentials_path == "db/violet.json"
        assert db_manager.initialized == False
        assert db_manager.db is None
        assert db_manager.storage_client is None
    
    @patch('firebase_admin.initialize_app')
    @patch('firebase_admin.credentials.Certificate')
    @patch('firebase_admin.firestore.client')
    @patch('google.cloud.storage.Client.from_service_account_json')
    def test_database_initialization_success(self, mock_storage, mock_firestore, mock_cred, mock_init):
        """Test successful database initialization"""
        # Mock the Firebase initialization
        mock_init.return_value = None
        mock_cred.return_value = Mock()
        mock_firestore.return_value = Mock()
        mock_storage.return_value = Mock()
        
        db_manager = DatabaseManager("db/violet.json")
        result = db_manager.initialize()
        
        assert result == True
        assert db_manager.initialized == True
        assert db_manager.db is not None
        assert db_manager.storage_client is not None
    
    def test_database_manager_get_db_before_initialization(self):
        """Test that get_db raises error before initialization"""
        db_manager = DatabaseManager("db/violet.json")
        
        with pytest.raises(RuntimeError, match="Database not initialized"):
            db_manager.get_db()
    
    def test_database_manager_get_storage_before_initialization(self):
        """Test that get_storage_client raises error before initialization"""
        db_manager = DatabaseManager("db/violet.json")
        
        with pytest.raises(RuntimeError, match="Database not initialized"):
            db_manager.get_storage_client()

class TestTaskManager:
    """Test task management functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database for testing"""
        mock_db = Mock()
        mock_collection = Mock()
        mock_doc = Mock()
        
        # Mock the collection and document methods
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        
        return mock_db
    
    @pytest.fixture
    def task_manager(self, mock_db):
        """Create a task manager instance for testing"""
        return TaskManager(mock_db)
    
    def test_task_manager_creation(self, task_manager, mock_db):
        """Test task manager creation"""
        assert task_manager.db == mock_db
        assert task_manager.tasks_collection is not None
        assert task_manager.miner_responses_collection is not None
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, task_manager, mock_db):
        """Test successful task creation"""
        # Mock the document operations
        mock_doc = Mock()
        mock_doc.set = Mock()
        mock_db.collection.return_value.document.return_value = mock_doc
        
        task_data = {
            "task_type": "transcription",
            "input_data": "test_data",
            "language": "en",
            "priority": "normal"
        }
        
        task_id = await task_manager.create_task(task_data)
        
        assert task_id is not None
        assert isinstance(task_id, str)
        mock_doc.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_tasks_by_status(self, task_manager, mock_db):
        """Test getting tasks by status"""
        # Mock the query operations
        mock_query = Mock()
        mock_docs = [Mock(), Mock()]
        
        for doc in mock_docs:
            doc.to_dict.return_value = {"task_id": "test_id", "status": "pending"}
            doc.id = "test_id"
        
        mock_query.stream.return_value = mock_docs
        mock_db.collection.return_value.where.return_value.limit.return_value = mock_query
        
        tasks = await task_manager.get_tasks_by_status("pending", limit=10)
        
        assert len(tasks) == 2
        assert all(task["status"] == "pending" for task in tasks)

class TestFileManager:
    """Test file management functionality"""
    
    @pytest.fixture
    def mock_storage_client(self):
        """Create a mock storage client"""
        mock_client = Mock()
        mock_bucket = Mock()
        mock_blob = Mock()
        
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        
        return mock_client
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database"""
        mock_db = Mock()
        mock_collection = Mock()
        mock_doc = Mock()
        
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        
        return mock_db
    
    @pytest.fixture
    def file_manager(self, mock_storage_client, mock_db):
        """Create a file manager instance"""
        return FileManager(mock_storage_client, mock_db)
    
    def test_file_manager_creation(self, file_manager, mock_storage_client, mock_db):
        """Test file manager creation"""
        assert file_manager.storage_client == mock_storage_client
        assert file_manager.db == mock_db
        assert file_manager.bucket is not None
    
    @pytest.mark.asyncio
    async def test_upload_file_success(self, file_manager, mock_storage_client, mock_db):
        """Test successful file upload"""
        # Mock the blob operations
        mock_blob = Mock()
        mock_blob.public_url = "https://example.com/test.wav"
        mock_storage_client.bucket.return_value.blob.return_value = mock_blob
        
        # Mock the database operations
        mock_doc = Mock()
        mock_doc.set = Mock()
        mock_db.collection.return_value.document.return_value = mock_doc
        
        file_data = b"test audio data"
        file_name = "test.wav"
        content_type = "audio/wav"
        
        file_id = await file_manager.upload_file(file_data, file_name, content_type)
        
        assert file_id is not None
        assert isinstance(file_id, str)
        mock_blob.upload_from_string.assert_called_once()
        mock_blob.make_public.assert_called_once()
        mock_doc.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_file_upload_success(self, file_manager):
        """Test successful file validation"""
        file_data = b"test audio data"
        file_name = "test.wav"
        content_type = "audio/wav"
        
        is_valid, message = await file_manager.validate_file_upload(file_data, file_name, content_type)
        
        assert is_valid == True
        assert "File validation passed" in message
    
    @pytest.mark.asyncio
    async def test_validate_file_upload_too_large(self, file_manager):
        """Test file validation with oversized file"""
        # Create a large file (over 50MB)
        file_data = b"x" * (51 * 1024 * 1024)
        file_name = "large.wav"
        content_type = "audio/wav"
        
        is_valid, message = await file_manager.validate_file_upload(file_data, file_name, content_type)
        
        assert is_valid == False
        assert "File too large" in message
    
    @pytest.mark.asyncio
    async def test_validate_file_upload_invalid_type(self, file_manager):
        """Test file validation with invalid file type"""
        file_data = b"test data"
        file_name = "test.exe"
        content_type = "application/x-executable"
        
        is_valid, message = await file_manager.validate_file_upload(file_data, file_name, content_type)
        
        assert is_valid == False
        assert "File type not supported" in message

class TestMinerResponseHandler:
    """Test miner response handling functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database"""
        mock_db = Mock()
        mock_collection = Mock()
        mock_doc = Mock()
        
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        
        return mock_db
    
    @pytest.fixture
    def response_handler(self, mock_db):
        """Create a miner response handler instance"""
        return MinerResponseHandler(mock_db)
    
    def test_response_handler_creation(self, response_handler, mock_db):
        """Test response handler creation"""
        assert response_handler.db == mock_db
        assert response_handler.miner_responses_collection is not None
        assert response_handler.tasks_collection is not None
    
    @pytest.mark.asyncio
    async def test_handle_miner_response_success(self, response_handler, mock_db):
        """Test successful miner response handling"""
        # Mock the document operations
        mock_doc = Mock()
        mock_doc.update = Mock()
        mock_db.collection.return_value.document.return_value = mock_doc
        
        # Mock the task completion check
        mock_task_doc = Mock()
        mock_task_doc.exists = True
        mock_task_doc.to_dict.return_value = {"required_miner_count": 3}
        mock_db.collection.return_value.document.return_value = mock_task_doc
        
        # Mock the query operations
        mock_query = Mock()
        mock_responses = [Mock(), Mock(), Mock()]
        for resp in mock_responses:
            resp.to_dict.return_value = {"status": "completed"}
        
        mock_query.stream.return_value = mock_responses
        mock_db.collection.return_value.where.return_value.where.return_value = mock_query
        
        response_data = {
            "output_data": "test output",
            "metrics": {"accuracy": 0.95},
            "processing_time": 2.5,
            "accuracy_score": 0.95,
            "speed_score": 0.88
        }
        
        await response_handler.handle_miner_response("test_task_id", 1, response_data)
        
        # Verify the response was processed
        mock_doc.update.assert_called()

class TestWorkflowOrchestrator:
    """Test workflow orchestration functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database"""
        return Mock()
    
    @pytest.fixture
    def orchestrator(self, mock_db):
        """Create a workflow orchestrator instance"""
        return WorkflowOrchestrator(mock_db)
    
    def test_orchestrator_creation(self, orchestrator, mock_db):
        """Test orchestrator creation"""
        assert orchestrator.db == mock_db
        assert orchestrator.running == False
        assert orchestrator.task_manager is not None
        assert orchestrator.miner_response_handler is not None
    
    @pytest.mark.asyncio
    async def test_start_orchestration(self, orchestrator):
        """Test starting workflow orchestration"""
        await orchestrator.start_orchestration()
        
        assert orchestrator.running == True
    
    @pytest.mark.asyncio
    async def test_stop_orchestration(self, orchestrator):
        """Test stopping workflow orchestration"""
        orchestrator.running = True
        await orchestrator.stop_orchestration()
        
        assert orchestrator.running == False
    
    @pytest.mark.asyncio
    async def test_select_optimal_miners(self, orchestrator):
        """Test miner selection logic"""
        task = {"required_miner_count": 3}
        
        miners = await orchestrator.select_optimal_miners(task)
        
        assert len(miners) == 3
        assert all("uid" in miner for miner in miners)
        assert all("score" in miner for miner in miners)

class TestValidatorIntegrationAPI:
    """Test validator integration functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database"""
        mock_db = Mock()
        mock_collection = Mock()
        mock_doc = Mock()
        
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        
        return mock_db
    
    @pytest.fixture
    def validator_api(self, mock_db):
        """Create a validator integration API instance"""
        return ValidatorIntegrationAPI(mock_db)
    
    def test_validator_api_creation(self, validator_api, mock_db):
        """Test validator API creation"""
        assert validator_api.db == mock_db
        assert validator_api.tasks_collection is not None
        assert validator_api.miner_responses_collection is not None
        assert validator_api.validators_collection is not None
    
    @pytest.mark.asyncio
    async def test_get_tasks_for_evaluation(self, validator_api, mock_db):
        """Test getting tasks for validator evaluation"""
        # Mock the query operations
        mock_query = Mock()
        mock_tasks = [Mock(), Mock()]
        
        for task in mock_tasks:
            task.to_dict.return_value = {"task_id": "test_id", "status": "done"}
            task.id = "test_id"
        
        mock_query.stream.return_value = mock_tasks
        mock_query.where.return_value.where.return_value.limit.return_value = mock_query
        mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query
        
        # Mock the miner responses
        mock_responses = []
        validator_api.get_miner_responses_for_task = Mock(return_value=mock_responses)
        
        tasks = await validator_api.get_tasks_for_evaluation(1)
        
        assert len(tasks) == 2
        assert all(task["status"] == "done" for task in tasks)

class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test a complete workflow from task creation to completion"""
        # This is a high-level integration test
        # In a real scenario, you'd test the actual database and storage
        
        # Mock the database manager
        with patch('database.schema.DatabaseManager') as mock_db_manager:
            mock_db_manager.return_value.initialize.return_value = True
            mock_db_manager.return_value.get_db.return_value = Mock()
            mock_db_manager.return_value.get_storage_client.return_value = Mock()
            
            # Test that the system can be initialized
            db_manager = DatabaseManager("db/violet.json")
            assert db_manager.initialize() == True

# Test utilities
def create_test_audio_file():
    """Create a test audio file for testing"""
    # Create a simple WAV file header (44 bytes)
    wav_header = (
        b'RIFF' +           # Chunk ID
        b'\x24\x00\x00\x00' +  # Chunk size (36 bytes)
        b'WAVE' +           # Format
        b'fmt ' +           # Subchunk1 ID
        b'\x10\x00\x00\x00' +  # Subchunk1 size (16 bytes)
        b'\x01\x00' +       # Audio format (PCM)
        b'\x01\x00' +       # Number of channels (1)
        b'\x44\xAC\x00\x00' +  # Sample rate (44100 Hz)
        b'\x88\x58\x01\x00' +  # Byte rate
        b'\x02\x00' +       # Block align
        b'\x10\x00' +       # Bits per sample (16)
        b'data' +           # Subchunk2 ID
        b'\x00\x00\x00\x00'    # Subchunk2 size (0 bytes)
    )
    
    return wav_header

def test_create_test_audio_file():
    """Test that test audio file creation works"""
    audio_data = create_test_audio_file()
    assert len(audio_data) == 44
    assert audio_data.startswith(b'RIFF')
    assert b'WAVE' in audio_data

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
