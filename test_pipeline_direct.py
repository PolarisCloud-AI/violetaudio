#!/usr/bin/env python3
"""
Direct pipeline test with real audio file
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# Add the neurons directory to the path
sys.path.append('neurons')

def test_transcription_pipeline():
    """Test the transcription pipeline directly with a real audio file"""
    
    # Path to the real audio file
    audio_file_path = "proxy_server/local_storage/user_audio/7290cb3e-3c5c-4b53-8e49-c182e3357f5d_LJ037-0171.wav"
    
    if not os.path.exists(audio_file_path):
        print(f"❌ Audio file not found: {audio_file_path}")
        return
    
    print(f"🎵 Testing transcription pipeline with: {audio_file_path}")
    print(f"📁 File size: {os.path.getsize(audio_file_path)} bytes")
    
    try:
        # Import the miner class to access the pipeline
        from neurons.miner import Miner
        
        # Create miner instance (this will initialize the pipelines)
        print("🔧 Initializing miner and pipelines...")
        miner = Miner()
        
        # Test the transcription pipeline directly
        print("🎯 Testing transcription pipeline...")
        start_time = time.time()
        
        # Read the audio file
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        
        print(f"📊 Audio data loaded: {len(audio_data)} bytes")
        
        # Process with transcription pipeline
        result = miner.transcription_pipeline(audio_data)
        
        processing_time = time.time() - start_time
        
        print("✅ Transcription Pipeline Test Results:")
        print(f"   📝 Transcript: {result.get('transcript', 'N/A')}")
        print(f"   🎯 Confidence: {result.get('confidence', 'N/A')}")
        print(f"   ⏱️  Processing Time: {processing_time:.2f}s")
        print(f"   🌍 Language: {result.get('language', 'N/A')}")
        
        if 'error' in result:
            print(f"   ❌ Error: {result['error']}")
        
        # Test file download capability
        print("\n🔍 Testing file download capability...")
        try:
            # Create a simple test to verify the download method works
            test_result = asyncio.run(miner.test_file_download())
            print(f"✅ File download test: {test_result}")
        except Exception as e:
            print(f"❌ File download test failed: {e}")
        
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Direct Pipeline Test")
    print("=" * 50)
    
    test_transcription_pipeline()
    
    print("\n" + "=" * 50)
    print("🏁 Pipeline test completed")


