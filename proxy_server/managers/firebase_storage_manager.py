"""
Firebase Cloud Storage Manager for Enhanced Proxy Server
Handles file uploads, downloads, and storage operations using Google Cloud Storage
"""

import uuid
import hashlib
import os
import base64
import re
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
from datetime import datetime
from firebase_admin import firestore
from google.cloud import storage
import mimetypes

class FirebaseStorageManager:
    def __init__(self, db, bucket_name: str = "violet-7063e.firebasestorage.app", credentials_path: str = "db/violet.json"):
        self.db = db
        self.files_collection = db.collection('files')
        self.credentials_path = credentials_path
        
        # Initialize Google Cloud Storage client with Firebase credentials
        from google.cloud import storage
        from google.oauth2 import service_account
        
        # Load service account credentials
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        
        # Initialize storage client with credentials
        self.storage_client = storage.Client(credentials=credentials)
        self.bucket_name = bucket_name
        self.bucket = self.storage_client.bucket(bucket_name)
        
        # File size limits
        self.max_file_size_firestore = 1 * 1024 * 1024  # 1MB limit for Firestore
        self.max_file_size_cloud = 5 * 1024 * 1024 * 1024  # 5GB limit for Cloud Storage
        
        # Base URL for remote access
        self.base_url = "https://violet-proxy.onrender.com/api/v1/files"
        
        print(f"✅ Firebase Cloud Storage initialized")
        print(f"   Bucket: {self.bucket_name}")
        print(f"   ALL files will be stored in Cloud Storage")
        print(f"   Cloud Storage limit: {self.max_file_size_cloud / (1024*1024*1024):.1f}GB")
    
    def _get_storage_path_for_type(self, file_type: str) -> str:
        """Get the appropriate storage path based on file type"""
        if file_type in ["transcription", "audio", "audio/wav", "audio/mp3", "audio/m4a"]:
            return "user_audio"
        elif file_type == "tts":
            return "tts_audio"
        elif file_type == "summarization":
            return "summarization_files"
        elif file_type in ["video_transcription", "video", "video/mp4", "video/avi", "video/mov"]:
            return "user_videos"
        elif file_type in ["document_translation", "text", "application/pdf", "text/plain"]:
            return "user_documents"
        else:
            return "temp"  # Default to temp for unknown types
    
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
        """Store file using Firebase Cloud Storage - ALL files go to Cloud Storage"""
        try:
            file_size = len(file_data)
            file_id = str(uuid.uuid4())
            
            print(f"📁 Storing file in Firebase Cloud Storage: {file_name}")
            print(f"   Size: {file_size / (1024*1024):.2f}MB")
            print(f"   Type: {content_type}")
            
            # Check file size limits
            if file_size > self.max_file_size_cloud:
                raise ValueError(f"File too large: {file_size / (1024*1024*1024):.2f}GB exceeds {self.max_file_size_cloud / (1024*1024*1024):.2f}GB limit")
            
            # ALWAYS store in Cloud Storage (no more smart storage strategy)
            print(f"   📦 Storing ALL files in Cloud Storage...")
            storage_info = await self._store_in_cloud_storage(file_data, file_name, file_type, file_id, content_type)
            firestore_data = storage_info
            
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
            
            print(f"✅ File stored successfully in Firebase Cloud Storage: {file_id}")
            return firestore_data
            
        except Exception as e:
            print(f"❌ File storage failed: {e}")
            raise
    
    async def _store_in_cloud_storage(self, file_data: bytes, file_name: str, file_type: str, file_id: str, content_type: str) -> Dict:
        """Store large file in Google Cloud Storage"""
        try:
            # Get appropriate storage path
            storage_path = self._get_storage_path_for_type(file_type)
            safe_filename = self._create_safe_filename(file_name)
            cloud_path = f"{storage_path}/{file_id}_{safe_filename}"
            
            # Create blob and upload to Cloud Storage
            blob = self.bucket.blob(cloud_path)
            blob.upload_from_string(file_data, content_type=content_type)
            
            # Make the blob publicly readable (optional, for direct access)
            blob.make_public()
            
            # Generate file URL
            file_url = f"gs://{self.bucket_name}/{cloud_path}"
            public_url = blob.public_url
            
            storage_info = {
                'file_path': cloud_path,
                'cloud_path': cloud_path,
                'file_url': file_url,
                'public_url': public_url,
                'stored_in_cloud': True,
                'storage_location': 'cloud_storage',
                'bucket_name': self.bucket_name
            }
            
            print(f"   📁 File stored in Cloud Storage: {cloud_path}")
            print(f"   🔗 Public URL: {public_url}")
            return storage_info
            
        except Exception as e:
            print(f"❌ Cloud Storage upload failed: {e}")
            raise
    
    async def _store_in_firestore(self, file_data: bytes, file_name: str, content_type: str, file_id: str) -> Dict:
        """Store small file in Firestore"""
        try:
            # Encode file data as base64
            encoded_data = base64.b64encode(file_data).decode('utf-8')
            
            # Generate file URL
            file_url = f"{self.base_url}/{file_id}"
            
            storage_info = {
                'content': encoded_data,
                'file_url': file_url,
                'stored_in_cloud': False,
                'storage_location': 'firestore'
            }
            
            print(f"   💾 File stored in Firestore")
            return storage_info
            
        except Exception as e:
            print(f"❌ Firestore file storage failed: {e}")
            raise
    
    async def retrieve_file(self, file_id: str) -> Optional[Tuple[bytes, str, str]]:
        """Retrieve file data, content type, and filename from Firebase"""
        try:
            # Get file metadata from Firestore
            file_doc = self.files_collection.document(file_id).get()
            
            if not file_doc.exists:
                print(f"❌ File {file_id} not found")
                return None
            
            file_data = file_doc.to_dict()
            file_name = file_data.get('file_name', 'unknown')
            content_type = file_data.get('content_type', 'application/octet-stream')
            
            if file_data.get('stored_in_cloud', False):
                # File stored in Cloud Storage
                cloud_path = file_data.get('cloud_path')
                if not cloud_path:
                    print(f"❌ Cloud Storage path not found for file {file_id}")
                    return None
                
                # Download from Cloud Storage
                blob = self.bucket.blob(cloud_path)
                file_content = blob.download_as_bytes()
                
                print(f"✅ Retrieved Cloud Storage file: {file_name}")
                
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
            
            # Delete from Cloud Storage if it exists
            if file_data.get('stored_in_cloud', False):
                cloud_path = file_data.get('cloud_path')
                if cloud_path:
                    blob = self.bucket.blob(cloud_path)
                    if blob.exists():
                        blob.delete()
                        print(f"🗑️ Deleted Cloud Storage file: {cloud_path}")
            
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
            if file_data.get('stored_in_cloud', False):
                file_data['storage_info'] = 'Cloud Storage'
                cloud_path = file_data.get('cloud_path')
                if cloud_path:
                    blob = self.bucket.blob(cloud_path)
                    file_data['file_exists'] = blob.exists()
                    file_data['public_url'] = file_data.get('public_url', '')
            else:
                file_data['storage_info'] = 'Firestore'
                file_data['file_exists'] = True
            
            return file_data
            
        except Exception as e:
            print(f"❌ Error getting file info: {e}")
            return None
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            stats = {
                'cloud_storage': {},
                'firestore_files': 0,
                'total_files': 0
            }
            
            # Count Cloud Storage files by type
            storage_paths = ['user_audio', 'tts_audio', 'summarization_files', 'user_videos', 'user_documents', 'temp']
            
            for path in storage_paths:
                blobs = list(self.bucket.list_blobs(prefix=path))
                stats['cloud_storage'][path] = len(blobs)
                stats['total_files'] += len(blobs)
            
            # Count Firestore files
            firestore_files = list(self.files_collection.where('stored_in_cloud', '==', False).stream())
            stats['firestore_files'] = len(firestore_files)
            stats['total_files'] += stats['firestore_files']
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}
    
    async def migrate_file_to_cloud(self, file_id: str) -> bool:
        """Migrate a file from Firestore to Cloud Storage"""
        try:
            file_data = await self.retrieve_file(file_id)
            if not file_data:
                return False
            
            file_content, content_type, file_name = file_data
            
            # Delete from Firestore
            self.files_collection.document(file_id).delete()
            
            # Store in Cloud Storage
            await self._store_in_cloud_storage(file_content, file_name, content_type, file_id, content_type)
            
            # Update metadata
            self.files_collection.document(file_id).set({
                'stored_in_cloud': True,
                'storage_location': 'cloud_storage',
                'migrated_at': datetime.now()
            })
            
            print(f"✅ Migrated file {file_id} to Cloud Storage")
            return True
            
        except Exception as e:
            print(f"❌ File migration failed: {e}")
            return False
