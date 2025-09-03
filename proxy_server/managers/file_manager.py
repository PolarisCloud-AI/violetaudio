"""
File Manager for Enhanced Proxy Server
Handles file uploads, downloads, and storage operations using Firebase Cloud Storage ONLY
"""

import uuid
import hashlib
import os
import shutil
from typing import Dict, List, Optional, Any, Tuple
from firebase_admin import firestore
from pathlib import Path
import mimetypes
from datetime import datetime

class FileManager:
    def __init__(self, db):
        self.db = db
        self.files_collection = db.collection('files')
        
        # Import and initialize Firebase Cloud Storage manager
        try:
            from .firebase_storage_manager import FirebaseStorageManager
            self.firebase_storage_manager = FirebaseStorageManager(db)
            print("✅ Firebase Cloud Storage manager initialized")
        except ImportError as e:
            print(f"❌ Could not import Firebase Cloud Storage manager: {e}")
            raise Exception("Firebase Cloud Storage manager is required")
        
        print(f"✅ Firebase Cloud Storage initialized")
    
    async def upload_file(self, file_data: bytes, file_name: str, content_type: str, file_type: str = "audio") -> str:
        """Upload file using Firebase Cloud Storage"""
        try:
            # Use Firebase Cloud Storage
            file_metadata = await self.firebase_storage_manager.store_file(file_data, file_name, content_type, file_type)
            file_id = file_metadata['file_id']
            print(f"✅ File uploaded using Firebase Cloud Storage: {file_id}")
            return file_id
            
        except Exception as e:
            print(f"❌ Failed to upload file {file_name}: {e}")
            raise
    
    async def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file from Firebase Cloud Storage"""
        try:
            # Use Firebase Cloud Storage
            result = await self.firebase_storage_manager.retrieve_file(file_id)
            if result:
                file_content, content_type, file_name = result
                print(f"✅ File downloaded from Firebase Cloud Storage: {file_name}")
                return file_content
            else:
                print(f"❌ File {file_id} not found in Firebase Cloud Storage")
                return None
            
        except Exception as e:
            print(f"❌ Failed to download file {file_id}: {e}")
            return None
    
    async def get_file_metadata(self, file_id: str) -> Optional[Dict]:
        """Get file metadata from Firebase Cloud Storage"""
        try:
            # Use Firebase Cloud Storage
            file_info = await self.firebase_storage_manager.get_file_info(file_id)
            if file_info:
                print(f"✅ File metadata retrieved from Firebase: {file_id}")
                return file_info
            else:
                print(f"❌ File {file_id} not found in Firebase")
                return None
                
        except Exception as e:
            print(f"❌ Failed to get file metadata {file_id}: {e}")
            return None
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file from Firebase Cloud Storage"""
        try:
            # Use Firebase Cloud Storage
            result = await self.firebase_storage_manager.delete_file(file_id)
            if result:
                print(f"✅ File {file_id} deleted from Firebase Cloud Storage")
            else:
                print(f"❌ Failed to delete file {file_id} from Firebase Cloud Storage")
            return result
            
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
        """Get storage statistics from Firebase Cloud Storage"""
        try:
            if self.firebase_storage_manager:
                return self.firebase_storage_manager.get_storage_stats()
            else:
                return {'error': 'Firebase Cloud Storage manager not available'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def get_file_url(self, file_id: str) -> Optional[str]:
        """Get public URL for a file"""
        try:
            # This would need to be implemented to get the public URL from Firebase
            # For now, return a placeholder
            return f"https://storage.googleapis.com/violet-7063e.appspot.com/{file_id}"
        except Exception as e:
            print(f"❌ Error getting file URL: {e}")
            return None
    
    async def file_exists(self, file_id: str) -> bool:
        """Check if file exists in Firebase Cloud Storage"""
        try:
            file_info = await self.get_file_metadata(file_id)
            return file_info is not None
        except Exception as e:
            print(f"❌ Error checking file existence: {e}")
            return False
