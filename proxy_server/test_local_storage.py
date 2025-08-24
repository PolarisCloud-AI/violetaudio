#!/usr/bin/env python3
"""
Test script for local storage system
"""

import asyncio
import os
from pathlib import Path

async def test_local_storage():
    """Test the local storage system"""
    print("🧪 Testing Local Storage System...")
    
    # Check if directories exist
    base_path = Path("proxy_server/local_storage")
    directories = [
        base_path / "user_audio",
        base_path / "tts_audio", 
        base_path / "transcription_files",
        base_path / "summarization_files"
    ]
    
    print("\n📁 Checking directories:")
    for directory in directories:
        if directory.exists():
            print(f"✅ {directory} exists")
        else:
            print(f"❌ {directory} missing")
    
    # Create test files
    print("\n📝 Creating test files:")
    
    # Test user audio
    test_audio_path = base_path / "user_audio" / "test_audio.wav"
    test_audio_path.write_bytes(b"fake_audio_data")
    print(f"✅ Created test audio: {test_audio_path}")
    
    # Test TTS audio
    test_tts_path = base_path / "tts_audio" / "test_tts.wav"
    test_tts_path.write_bytes(b"fake_tts_data")
    print(f"✅ Created test TTS: {test_tts_path}")
    
    # Test transcription file
    test_trans_path = base_path / "transcription_files" / "test_trans.txt"
    test_trans_path.write_text("This is a test transcription file")
    print(f"✅ Created test transcription: {test_trans_path}")
    
    # Test summarization file
    test_sum_path = base_path / "summarization_files" / "test_sum.txt"
    test_sum_path.write_text("This is a test summarization file")
    print(f"✅ Created test summarization: {test_sum_path}")
    
    # List files in each directory
    print("\n📋 Directory contents:")
    for directory in directories:
        if directory.exists():
            files = list(directory.glob("*"))
            print(f"\n{directory.name}:")
            for file in files:
                size = file.stat().st_size
                print(f"  - {file.name} ({size} bytes)")
    
    print("\n🎉 Local storage test completed!")

if __name__ == "__main__":
    asyncio.run(test_local_storage())
