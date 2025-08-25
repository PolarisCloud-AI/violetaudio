#!/usr/bin/env python3
"""
Script to create test miners in the database for testing the summarization pipeline
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from proxy_server.database.enhanced_schema import DatabaseOperations, COLLECTIONS
from proxy_server.database.schema import DatabaseManager
from datetime import datetime

def create_test_miners():
    """Create test miners in the database"""
    try:
        # Initialize database manager with credentials
        import os
        
        # Try multiple possible paths for the credentials file
        possible_paths = [
            "proxy_server/db/violet.json",  # From project root
            "db/violet.json",               # From proxy_server directory
            os.path.join(os.path.dirname(__file__), "proxy_server", "db", "violet.json"),  # Absolute path
            os.path.join(os.getcwd(), "proxy_server", "db", "violet.json")  # Current working directory
        ]
        
        credentials_path = None
        for path in possible_paths:
            if os.path.exists(path):
                credentials_path = path
                print(f"✅ Found credentials at: {path}")
                break
        
        if not credentials_path:
            raise FileNotFoundError(f"Firebase credentials not found. Tried paths: {possible_paths}")
        
        db_manager = DatabaseManager(credentials_path)
        db_manager.initialize()
        db = db_manager.get_db()
        
        print("🔧 Creating test miners in database...")
        
        # Test miner data
        test_miners = [
            {
                'uid': 1001,
                'hotkey': 'test_miner_1001',
                'ip': '127.0.0.1',
                'port': 8001,
                'external_ip': '127.0.0.1',
                'external_port': 8001,
                'is_serving': True,
                'stake': 1000.0,
                'performance_score': 0.95,
                'current_load': 20.0,
                'max_capacity': 100.0,
                'task_type_specialization': 'summarization',
                'last_seen': datetime.utcnow()
            },
            {
                'uid': 1002,
                'hotkey': 'test_miner_1002',
                'ip': '127.0.0.1',
                'port': 8002,
                'external_ip': '127.0.0.1',
                'external_port': 8002,
                'is_serving': True,
                'stake': 1000.0,
                'performance_score': 0.92,
                'current_load': 15.0,
                'max_capacity': 100.0,
                'task_type_specialization': 'summarization',
                'last_seen': datetime.utcnow()
            },
            {
                'uid': 1003,
                'hotkey': 'test_miner_1003',
                'ip': '127.0.0.1',
                'port': 8003,
                'external_ip': '127.0.0.1',
                'external_port': 8003,
                'is_serving': True,
                'stake': 1000.0,
                'performance_score': 0.88,
                'current_load': 30.0,
                'max_capacity': 100.0,
                'task_type_specialization': 'summarization',
                'last_seen': datetime.utcnow()
            }
        ]
        
        # Add each test miner
        for miner_data in test_miners:
            miner_id = str(miner_data['uid'])
            
            # Check if miner already exists
            existing_miner = db.collection(COLLECTIONS['miners']).document(miner_id).get()
            if existing_miner.exists:
                print(f"⚠️ Miner {miner_id} already exists, updating...")
                db.collection(COLLECTIONS['miners']).document(miner_id).update(miner_data)
            else:
                print(f"➕ Creating new miner {miner_id}...")
                db.collection(COLLECTIONS['miners']).document(miner_id).set(miner_data)
            
            print(f"   ✅ Miner {miner_id} ({miner_data['hotkey']}) ready")
        
        print(f"🎯 Created {len(test_miners)} test miners successfully!")
        
        # Verify miners are accessible
        available_miners = DatabaseOperations.get_available_miners(db, 'summarization')
        print(f"🔍 Found {len(available_miners)} available miners for summarization tasks:")
        for miner in available_miners:
            print(f"   - Miner {miner['uid']}: {miner['hotkey']} (load: {miner['current_load']}/{miner['max_capacity']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating test miners: {e}")
        return False

if __name__ == "__main__":
    success = create_test_miners()
    if success:
        print("✅ Test miners setup complete!")
    else:
        print("❌ Failed to setup test miners")
        sys.exit(1)
