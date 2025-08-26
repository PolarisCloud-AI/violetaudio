"""
Smart File Manager for Enhanced Proxy Server
Stores large files locally and only metadata in Firestore to reduce quota usage
"""

import uuid
import hashlib
import os
import shutil
import re
import base64
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
from datetime import datetime
from firebase_admin import firestore
import mimetypes

class SmartFileManager:
    def __init__(self, db):
        self.db = db
        self.files_collection = db.collection('files')
        
        # Local storage paths
        self.base_storage_path = Path("proxy_server/local_storage")
        self.user_audio_path = self.base_storage_path / "user_audio"
        self.tts_audio_path = self.base_storage_path / "tts_audio"
        self.transcription_path = self.base_storage_path / "transcription_files"
        self.summarization_path = self.base_storage_path / "summarization_files"
        self.video_path = self.base_storage_path / "user_videos"
        self.document_path = self.base_storage_path / "user_documents"
        self.temp_path = self.base_storage_path / "temp"
        
        # File size limits
        self.max_file_size_firestore = 1 * 1024 * 1024  # 1MB limit for Firestore
        self.max_file_size_local = 100 * 1024 * 1024     # 100MB limit for local storage
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Base URL for remote access
        self.base_url = "http://localhost:8000/api/v1/files"
        
        print(f"✅ Smart File Storage initialized at: {self.base_storage_path.absolute()}")
        print(f"   Firestore size limit: {self.max_file_size_firestore / (1024*1024):.1f}MB")
        print(f"   Local storage limit: {self.max_file_size_local / (1024*1024):.1f}MB")
    
    def _ensure_directories(self):
        """Ensure all storage directories exist"""
        directories = [
            self.user_audio_path, 
            self.tts_audio_path, 
            self.transcription_path, 
            self.summarization_path, 
            self.video_path, 
            self.document_path,
            self.temp_path
        ]
        
        for path in directories:
            path.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created directory: {path}")
    
    def _get_storage_path_for_type(self, file_type: str) -> Path:
        """Get the appropriate storage path based on file type"""
        if file_type in ["transcription", "audio", "audio/wav", "audio/mp3", "audio/m4a"]:
            return self.user_audio_path
        elif file_type == "tts":
            return self.tts_audio_path
        elif file_type == "summarization":
            return self.summarization_path
        elif file_type in ["video_transcription", "video", "video/mp4", "video/avi", "video/mov"]:
            return self.video_path
        elif file_type in ["document_translation", "text", "application/pdf", "text/plain"]:
            return self.document_path
        else:
            return self.temp_path  # Default to temp for unknown types
    
    def _create_safe_filename(self, original_filename: str) -> str:
        """Create a safe filename for storage by removing problematic characters"""
        # Remove or replace problematic characters
        safe_filename = re.sub(r'[^\w\s\-_.]', '_', original_filename)
        # Replace spaces with underscores
        safe_filename = safe_filename.replace(' ', '_')
        # Ensure it's not empty
        if not safe_filename:
            safe_filename = "unnamed_file"
        return safe_filename
    
    def _calculate_file_hash(self, file_data: bytes) -> str:
        """Calculate SHA-256 hash of file data for deduplication"""
        return hashlib.sha256(file_data).hexdigest()
    
    async def store_file(self, file_data: bytes, file_name: str, content_type: str, file_type: str = "audio") -> Dict:
        """Smart file storage based on size and type"""
        try:
            file_size = len(file_data)
            file_id = str(uuid.uuid4())
            
            print(f"📁 Storing file: {file_name}")
            print(f"   Size: {file_size / (1024*1024):.2f}MB")
            print(f"   Type: {content_type}")
            
            # Check file size limits
            if file_size > self.max_file_size_local:
                raise ValueError(f"File too large: {file_size / (1024*1024):.2f}MB exceeds {self.max_file_size_local / (1024*1024):.2f}MB limit")
            
            # Determine storage strategy
            if file_size > self.max_file_size_firestore:
                # Large file: Store locally, only metadata in Firestore
                print(f"   📦 Large file detected, storing locally...")
                storage_info = await self._store_large_file(file_data, file_name, file_type, file_id)
                firestore_data = storage_info
                
            else:
                # Small file: Store in Firestore
                print(f"   💾 Small file, storing in Firestore...")
                firestore_data = await self._store_small_file(file_data, file_name, content_type, file_id)
            
            # Add common metadata
            firestore_data.update({
                'file_id': file_id,
                'file_name': file_name,
                'content_type': content_type,
                'size': file_size,
                'file_type': file_type,
                'checksum': self._calculate_file_hash(file_data),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })
            
            # Store metadata in Firestore
            self.files_collection.document(file_id).set(firestore_data)
            
            print(f"✅ File stored successfully: {file_id}")
            return firestore_data
            
        except Exception as e:
            print(f"❌ File storage failed: {e}")
            raise
    
    async def _store_large_file(self, file_data: bytes, file_name: str, file_type: str, file_id: str) -> Dict:
        """Store large file in local storage"""
        try:
            # Get appropriate storage path
            storage_path = self._get_storage_path_for_type(file_type)
            safe_filename = self._create_safe_filename(file_name)
            file_path = storage_path / f"{file_id}_{safe_filename}"
            
            # Save file to local storage
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Generate file URL for remote access
            file_url = f"{self.base_url}/{file_id}"
            
            storage_info = {
                'file_path': str(file_path),
                'local_path': str(file_path),
                'file_url': file_url,
                'stored_locally': True,
                'storage_location': 'local'
            }
            
            print(f"   📁 File stored locally: {file_path}")
            return storage_info
            
        except Exception as e:
            print(f"❌ Local file storage failed: {e}")
            raise
    
    async def _store_small_file(self, file_data: bytes, file_name: str, content_type: str, file_id: str) -> Dict:
        """Store small file in Firestore"""
        try:
            # Encode file data as base64
            encoded_data = base64.b64encode(file_data).decode('utf-8')
            
            # Generate file URL
            file_url = f"{self.base_url}/{file_id}"
            
            storage_info = {
                'content': encoded_data,
                'file_url': file_url,
                'stored_locally': False,
                'storage_location': 'firestore'
            }
            
            print(f"   💾 File stored in Firestore")
            return storage_info
            
        except Exception as e:
            print(f"❌ Firestore file storage failed: {e}")
            raise
    
    async def retrieve_file(self, file_id: str) -> Optional[Tuple[bytes, str, str]]:
        """Retrieve file data, content type, and filename"""
        try:
            # Get file metadata from Firestore
            file_doc = self.files_collection.document(file_id).get()
            
            if not file_doc.exists:
                print(f"❌ File {file_id} not found")
                return None
            
            file_data = file_doc.to_dict()
            file_name = file_data.get('file_name', 'unknown')
            content_type = file_data.get('content_type', 'application/octet-stream')
            
            if file_data.get('stored_locally', False):
                # File stored locally
                local_path = file_data.get('local_path')
                if not local_path or not os.path.exists(local_path):
                    print(f"❌ Local file not found: {local_path}")
                    return None
                
                with open(local_path, 'rb') as f:
                    file_content = f.read()
                
                print(f"✅ Retrieved local file: {file_name}")
                
            else:
                # File stored in Firestore
                encoded_content = file_data.get('content')
                if not encoded_content:
                    print(f"❌ No content found for file {file_id}")
                    return None
                
                file_content = base64.b64decode(encoded_content)
                print(f"✅ Retrieved Firestore file: {file_name}")
            
            return file_content, content_type, file_name
            
        except Exception as e:
            print(f"❌ File retrieval failed: {e}")
            return None
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file from both storage and database"""
        try:
            # Get file metadata
            file_doc = self.files_collection.document(file_id).get()
            
            if not file_doc.exists:
                print(f"⚠️ File {file_id} not found for deletion")
                return False
            
            file_data = file_doc.to_dict()
            
            # Delete local file if it exists
            if file_data.get('stored_locally', False):
                local_path = file_data.get('local_path')
                if local_path and os.path.exists(local_path):
                    os.remove(local_path)
                    print(f"🗑️ Deleted local file: {local_path}")
            
            # Delete from Firestore
            self.files_collection.document(file_id).delete()
            print(f"🗑️ Deleted file metadata: {file_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ File deletion failed: {e}")
            return False
    
    async def get_file_info(self, file_id: str) -> Optional[Dict]:
        """Get file information without retrieving the actual file"""
        try:
            file_doc = self.files_collection.document(file_id).get()
            
            if not file_doc.exists:
                return None
            
            file_data = file_doc.to_dict()
            
            # Add storage location info
            if file_data.get('stored_locally', False):
                file_data['storage_info'] = 'Local Storage'
                file_data['file_exists'] = os.path.exists(file_data.get('local_path', ''))
            else:
                file_data['storage_info'] = 'Firestore'
                file_data['file_exists'] = True
            
            return file_data
            
        except Exception as e:
            print(f"❌ Error getting file info: {e}")
            return None
    
    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than specified age"""
        try:
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            deleted_count = 0
            
            # Clean up temp directory
            for file_path in self.temp_path.glob('*'):
                if file_path.is_file():
                    file_age = file_path.stat().st_mtime
                    if file_age < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        print(f"🧹 Cleaned up temp file: {file_path.name}")
            
            print(f"✅ Cleaned up {deleted_count} temporary files")
            return deleted_count
            
        except Exception as e:
            print(f"❌ Temp file cleanup failed: {e}")
            return 0
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            stats = {
                'local_storage': {},
                'firestore_files': 0,
                'total_files': 0
            }
            
            # Count local files by type
            for storage_path, path_name in [
                (self.user_audio_path, 'audio'),
                (self.tts_audio_path, 'tts'),
                (self.transcription_path, 'transcription'),
                (self.summarization_path, 'summarization'),
                (self.video_path, 'video'),
                (self.document_path, 'documents'),
                (self.temp_path, 'temp')
            ]:
                if storage_path.exists():
                    file_count = len(list(storage_path.glob('*')))
                    stats['local_storage'][path_name] = file_count
                    stats['total_files'] += file_count
            
            # Count Firestore files
            firestore_files = list(self.files_collection.where('stored_locally', '==', False).stream())
            stats['firestore_files'] = len(firestore_files)
            stats['total_files'] += stats['firestore_files']
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}
    
    async def migrate_file_to_local(self, file_id: str) -> bool:
        """Migrate a file from Firestore to local storage to save quota"""
        try:
            file_data = await self.retrieve_file(file_id)
            if not file_data:
                return False
            
            file_content, content_type, file_name = file_data
            
            # Delete from Firestore
            self.files_collection.document(file_id).delete()
            
            # Store locally
            await self._store_large_file(file_content, file_name, content_type, file_id)
            
            # Update metadata
            self.files_collection.document(file_id).set({
                'stored_locally': True,
                'storage_location': 'local',
                'migrated_at': datetime.now()
            })
            
            print(f"✅ Migrated file {file_id} to local storage")
            return True
            
        except Exception as e:
            print(f"❌ File migration failed: {e}")
            return False
