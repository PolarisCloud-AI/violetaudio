"""
File Manager for Enhanced Proxy Server
Handles file uploads, downloads, and local storage operations
"""

import uuid
import hashlib
import os
import shutil
from typing import Dict, List, Optional, Any, Tuple
from firebase_admin import firestore
from pathlib import Path
import mimetypes

class FileManager:
    def __init__(self, db):
        self.db = db
        self.files_collection = db.collection('files')
        
        # Local storage paths
        self.base_storage_path = Path("proxy_server/local_storage")
        self.user_audio_path = self.base_storage_path / "user_audio"
        self.tts_audio_path = self.base_storage_path / "tts_audio"
        self.transcription_path = self.base_storage_path / "transcription_files"
        self.summarization_path = self.base_storage_path / "summarization_files"
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Base URL for remote access
        self.base_url = "http://localhost:8000/api/v1/files"
        
        print(f"✅ Local File Storage initialized at: {self.base_storage_path.absolute()}")
    
    def _ensure_directories(self):
        """Ensure all storage directories exist"""
        for path in [self.user_audio_path, self.tts_audio_path, self.transcription_path, self.summarization_path]:
            path.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created directory: {path}")
    
    def _get_storage_path_for_type(self, file_type: str) -> Path:
        """Get the appropriate storage path based on file type"""
        if file_type in ["transcription", "audio"]:
            return self.user_audio_path
        elif file_type == "tts":
            return self.tts_audio_path
        elif file_type == "summarization":
            return self.summarization_path
        else:
            return self.user_audio_path  # Default
    
    async def upload_file(self, file_data: bytes, file_name: str, content_type: str, file_type: str = "audio") -> str:
        """Upload file to local storage"""
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Get appropriate storage path
            storage_path = self._get_storage_path_for_type(file_type)
            file_path = storage_path / f"{file_id}_{file_name}"
            
            # Save file to local storage
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Generate file URL for remote access
            file_url = f"{self.base_url}/{file_id}"
            
            # Store file metadata in database
            file_metadata = {
                'file_id': file_id,
                'file_name': file_name,
                'file_path': str(file_path),
                'content_type': content_type,
                'size': len(file_data),
                'uploaded_at': firestore.SERVER_TIMESTAMP,  # This is not awaitable
                'file_url': file_url,
                'status': 'active',
                'checksum': hashlib.md5(file_data).hexdigest(),
                'file_type': file_type,
                'local_path': str(file_path)
            }
            
            self.files_collection.document(file_id).set(file_metadata)  # Remove await
            
            print(f"✅ File {file_name} uploaded successfully: {file_id}")
            print(f"📁 Stored at: {file_path}")
            print(f"🌐 Accessible at: {file_url}")
            return file_id
            
        except Exception as e:
            print(f"❌ Failed to upload file {file_name}: {e}")
            raise
    
    async def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file from local storage"""
        try:
            # Get file metadata
            doc = self.files_collection.document(file_id).get()  # Remove await
            if not doc.exists:
                return None
            
            file_data = doc.to_dict()
            file_path = file_data['local_path']
            
            # Read file from local storage
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            return file_content
            
        except Exception as e:
            print(f"❌ Failed to download file {file_id}: {e}")
            return None
    
    async def get_file_metadata(self, file_id: str) -> Optional[Dict]:
        """Get file metadata"""
        try:
            doc = self.files_collection.document(file_id).get()  # Remove await
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            print(f"❌ Failed to get file metadata {file_id}: {e}")
            return None
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file from storage and database"""
        try:
            # Get file metadata
            file_metadata = await self.get_file_metadata(file_id)
            if not file_metadata:
                return False
            
            # Delete from local storage
            file_path = file_metadata['local_path']
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️  Deleted file: {file_path}")
            
            # Delete metadata from database
            self.files_collection.document(file_id).delete()  # Remove await
            
            print(f"✅ File {file_id} deleted successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to delete file {file_id}: {e}")
            return False
    
    async def cleanup_expired_files(self, max_age_hours: int = 24):
        """Clean up expired files to save storage space"""
        try:
            from datetime import datetime, timedelta
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            # Query expired files
            query = self.files_collection.where('uploaded_at', '<', cutoff_time)
            expired_files = query.stream()
            
            deleted_count = 0
            for doc in expired_files:
                file_data = doc.to_dict()
                if await self.delete_file(file_data['file_id']):
                    deleted_count += 1
            
            if deleted_count > 0:
                print(f"🧹 Cleaned up {deleted_count} expired files")
                
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
    
    def get_file_path(self, file_id: str) -> Optional[str]:
        """Get local file path for a file ID (synchronous)"""
        try:
            # This is a synchronous method for quick path access
            # Note: This doesn't check if file exists in database
            return str(self.base_storage_path / f"{file_id}_*")
        except Exception as e:
            print(f"❌ Error getting file path: {e}")
            return None
    
    async def list_files_by_type(self, file_type: str) -> List[Dict]:
        """List all files of a specific type"""
        try:
            query = self.files_collection.where('file_type', '==', file_type)
            files = query.stream()
            
            file_list = []
            for doc in files:
                file_data = doc.to_dict()
                file_data['id'] = doc.id
                file_list.append(file_data)
            
            return file_list
            
        except Exception as e:
            print(f"❌ Error listing files by type: {e}")
            return []
    
    async def get_storage_statistics(self) -> Dict:
        """Get storage statistics"""
        try:
            stats = {
                'total_files': 0,
                'total_size': 0,
                'files_by_type': {},
                'storage_paths': {
                    'user_audio': str(self.user_audio_path),
                    'tts_audio': str(self.tts_audio_path),
                    'transcription': str(self.transcription_path),
                    'summarization': str(self.summarization_path)
                }
            }
            
            # Count files and calculate sizes
            files = self.files_collection.stream()
            for doc in files:
                file_data = doc.to_dict()
                file_type = file_data.get('file_type', 'unknown')
                
                stats['total_files'] += 1
                stats['total_size'] += file_data.get('size', 0)
                
                if file_type not in stats['files_by_type']:
                    stats['files_by_type'][file_type] = {'count': 0, 'size': 0}
                
                stats['files_by_type'][file_type]['count'] += 1
                stats['files_by_type'][file_type]['size'] += file_data.get('size', 0)
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting storage statistics: {e}")
            return {}
