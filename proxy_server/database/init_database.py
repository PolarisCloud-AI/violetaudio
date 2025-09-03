"""
Database Initialization Script for Production Task Management
Sets up collections, indexes, and initial data structure
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .enhanced_schema import (
        COLLECTIONS, REQUIRED_INDEXES, DatabaseOperations,
        TaskType, TaskPriority, TaskStatus, MinerStatus, ResponseStatus
    )
except ImportError:
    # Fallback for direct execution
    from enhanced_schema import (
        COLLECTIONS, REQUIRED_INDEXES, DatabaseOperations,
        TaskType, TaskPriority, TaskStatus, MinerStatus, ResponseStatus
    )

class DatabaseInitializer:
    """Initialize the production database with proper structure"""
    
    def __init__(self, db: firestore.Client):
        self.db = db
        self.collections_created = set()
        self.indexes_created = set()
    
    def initialize_database(self):
        """Initialize the complete database structure"""
        print("🚀 Initializing production database...")
        
        try:
            # Create collections
            self.create_collections()
            
            # Create indexes (Firestore handles these automatically, but we document them)
            self.document_indexes()
            
            # Create sample data for testing
            self.create_sample_data()
            
            # Verify database structure
            self.verify_database_structure()
            
            print("✅ Database initialization completed successfully!")
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            raise
    
    def create_collections(self):
        """Create all required collections"""
        print("📁 Creating database collections...")
        
        for collection_name in COLLECTIONS.values():
            try:
                # Create a dummy document to ensure collection exists
                dummy_doc = self.db.collection(collection_name).document('_init')
                dummy_doc.set({
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'initialized': True,
                    'version': '1.0.0'
                })
                
                self.collections_created.add(collection_name)
                print(f"✅ Collection '{collection_name}' created")
                
            except Exception as e:
                print(f"⚠️ Collection '{collection_name}' already exists or error: {e}")
    
    def document_indexes(self):
        """Document required indexes for Firestore"""
        print("📋 Documenting required indexes...")
        
        print("📊 Required indexes for Firestore:")
        for index in REQUIRED_INDEXES:
            print(f"   - {index}")
            self.indexes_created.add(index)
        
        print("ℹ️ Note: Firestore creates composite indexes automatically when queries are made")
    
    def create_sample_data(self):
        """Create sample data for testing and development"""
        print("🧪 Creating sample data...")
        
        # Create sample miner
        sample_miner = {
            'uid': 48,
            'hotkey': "5Gxwzb9gKBCE2a4Qb6VDfUSabKMRZt9nUWAsw",
            'ip': "102.134.149.117",
            'port': 8091,
            'external_ip': "102.134.149.117",
            'external_port': 8091,
            'is_serving': True,
            'stake': 1000.0,
            'performance_score': 0.85,
            'current_load': 0,
            'max_capacity': 5,
            'last_seen': datetime.now(),
            'task_type_specialization': 'transcription,tts,summarization',
            'reported_by_validators': ['validator_48'],
            'updated_at': datetime.now()
        }
        
        # Save sample miner
        miner_ref = self.db.collection(COLLECTIONS['miner_status']).document(str(sample_miner['uid']))
        miner_ref.set(sample_miner)
        print(f"✅ Sample miner {sample_miner['uid']} created")
        
        # Create sample file reference using existing real file
        sample_file = {
            'file_id': "7290cb3e-3c5c-4b53-8e49-c182e3357f5d",
            'file_name': "LJ037-0171.wav",
            'file_type': "audio/wav",
            'file_size': 334496,  # Actual file size
            'local_path': "firestore/7290cb3e-3c5c-4b53-8e49-c182e3357f5d_LJ037-0171.wav",
            'file_url': "/api/v1/files/7290cb3e-3c5c-4b53-8e49-c182e3357f5d",
            'content_type': "audio/wav",
            'checksum': "abc123def456",
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        # Save sample file
        file_ref = self.db.collection(COLLECTIONS['files']).document(sample_file['file_id'])
        file_ref.set(sample_file)
        print(f"✅ Sample file {sample_file['file_id']} created")
        
        # Create sample task
        sample_task = {
            'task_id': "sample_task_001",
            'task_type': TaskType.TRANSCRIPTION.value,
            'status': TaskStatus.PENDING.value,
            'priority': TaskPriority.NORMAL.value,
            'input_file': sample_file,
            'source_language': "en",
            'target_language': "en",
            'required_miner_count': 1,
            'estimated_completion_time': 60,
            'user_metadata': {
                'user_id': 'test_user',
                'project': 'sample_project',
                'description': 'Sample transcription task for testing'
            },
            'tags': ['sample', 'transcription', 'test'],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        # Save sample task
        task_ref = self.db.collection(COLLECTIONS['tasks']).document(sample_task['task_id'])
        task_ref.set(sample_task)
        print(f"✅ Sample task {sample_task['task_id']} created")
        
        # Create sample task assignment
        sample_assignment = {
            'assignment_id': f"{sample_task['task_id']}_{sample_miner['uid']}",
            'miner_uid': sample_miner['uid'],
            'assigned_at': datetime.now(),
            'status': ResponseStatus.PENDING.value,
            'processing_time': None,
            'accuracy_score': None,
            'speed_score': None
        }
        
        # Save sample assignment
        assignment_ref = self.db.collection(COLLECTIONS['assignments']).document(sample_assignment['assignment_id'])
        assignment_ref.set(sample_assignment)
        print(f"✅ Sample assignment {sample_assignment['assignment_id']} created")
    
    def verify_database_structure(self):
        """Verify that all collections and data were created correctly"""
        print("🔍 Verifying database structure...")
        
        # Check collections
        for collection_name in COLLECTIONS.values():
            try:
                docs = self.db.collection(collection_name).limit(1).stream()
                doc_count = len(list(docs))
                print(f"✅ Collection '{collection_name}': {doc_count} documents")
            except Exception as e:
                print(f"❌ Collection '{collection_name}' verification failed: {e}")
        
        # Check sample data
        try:
            # Check miner
            miner_doc = self.db.collection(COLLECTIONS['miner_status']).document('48').get()
            if miner_doc.exists:
                print(f"✅ Sample miner 48 verified")
            else:
                print(f"❌ Sample miner 48 not found")
            
            # Check task
            task_doc = self.db.collection(COLLECTIONS['tasks']).document('sample_task_001').get()
            if task_doc.exists:
                print(f"✅ Sample task verified")
            else:
                print(f"❌ Sample task not found")
                
        except Exception as e:
            print(f"⚠️ Sample data verification error: {e}")
    
    def cleanup_sample_data(self):
        """Clean up sample data (use with caution)"""
        print("🧹 Cleaning up sample data...")
        
        try:
            # Remove sample documents
            collections_to_clean = [
                (COLLECTIONS['miner_status'], '48'),
                (COLLECTIONS['tasks'], 'sample_task_001'),
                (COLLECTIONS['assignments'], 'sample_task_001_48'),
                (COLLECTIONS['files'], '7290cb3e-3c5c-4b53-8e49-c182e3357f5d')
            ]
            
            for collection_name, doc_id in collections_to_clean:
                try:
                    self.db.collection(collection_name).document(doc_id).delete()
                    print(f"✅ Cleaned {collection_name}/{doc_id}")
                except Exception as e:
                    print(f"⚠️ Could not clean {collection_name}/{doc_id}: {e}")
            
            print("✅ Sample data cleanup completed")
            
        except Exception as e:
            print(f"❌ Sample data cleanup failed: {e}")

def main():
    """Main initialization function"""
    try:
        # Initialize Firebase (assuming credentials are already set up)
        if not firebase_admin._apps:
            cred = credentials.Certificate("../db/violet.json")
            firebase_admin.initialize_app(cred)
        
        # Get database instance
        db = firestore.client()
        
        # Initialize database
        initializer = DatabaseInitializer(db)
        initializer.initialize_database()
        
        print("\n🎉 Database is ready for production use!")
        print("\n📋 Available collections:")
        for collection in COLLECTIONS.values():
            print(f"   - {collection}")
        
        print("\n🔧 Next steps:")
        print("   1. Start your proxy server")
        print("   2. Create real tasks using the API endpoints")
        print("   3. Monitor task distribution and completion")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
