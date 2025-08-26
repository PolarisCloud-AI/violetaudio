#!/usr/bin/env python3
"""
Setup Local Storage Directories for Proxy Server
Creates all required directories for smart file storage
"""

import os
from pathlib import Path
import shutil

def setup_local_storage():
    """Create all required local storage directories"""
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    storage_base = project_root / "proxy_server" / "local_storage"
    
    print(f"🚀 Setting up local storage directories...")
    print(f"   Project root: {project_root}")
    print(f"   Storage base: {storage_base}")
    
    # Define all required directories
    directories = [
        "user_audio",
        "tts_audio", 
        "transcription_files",
        "summarization_files",
        "user_videos",
        "user_documents",
        "temp",
        "audio_chunks",
        "transcript_segments"
    ]
    
    # Create directories
    created_dirs = []
    existing_dirs = []
    
    for dir_name in directories:
        dir_path = storage_base / dir_name
        
        if dir_path.exists():
            existing_dirs.append(dir_name)
            print(f"   📁 {dir_name}: already exists")
        else:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(dir_name)
                print(f"   ✅ {dir_name}: created")
            except Exception as e:
                print(f"   ❌ {dir_name}: failed to create - {e}")
    
    # Create .gitkeep files to preserve empty directories
    for dir_name in directories:
        dir_path = storage_base / dir_name
        gitkeep_file = dir_path / ".gitkeep"
        
        if not gitkeep_file.exists():
            try:
                gitkeep_file.touch()
                print(f"   📄 {dir_name}/.gitkeep: created")
            except Exception as e:
                print(f"   ❌ {dir_name}/.gitkeep: failed to create - {e}")
    
    # Summary
    print(f"\n📊 Setup Summary:")
    print(f"   Created: {len(created_dirs)} directories")
    print(f"   Existing: {len(existing_dirs)} directories")
    print(f"   Total: {len(directories)} directories")
    
    if created_dirs:
        print(f"   New directories: {', '.join(created_dirs)}")
    
    print(f"\n✅ Local storage setup complete!")
    print(f"   All files will be stored in: {storage_base}")
    
    return storage_base

def verify_storage_setup():
    """Verify that all storage directories are accessible"""
    project_root = Path(__file__).parent.parent
    storage_base = project_root / "proxy_server" / "local_storage"
    
    print(f"\n🔍 Verifying storage setup...")
    
    # Check if base directory exists
    if not storage_base.exists():
        print(f"   ❌ Storage base directory doesn't exist: {storage_base}")
        return False
    
    # Check each subdirectory
    directories = [
        "user_audio",
        "tts_audio", 
        "transcription_files",
        "summarization_files",
        "user_videos",
        "user_documents",
        "temp",
        "audio_chunks",
        "transcript_segments"
    ]
    
    all_good = True
    
    for dir_name in directories:
        dir_path = storage_base / dir_name
        
        if not dir_path.exists():
            print(f"   ❌ Directory missing: {dir_name}")
            all_good = False
        elif not os.access(dir_path, os.W_OK):
            print(f"   ❌ Directory not writable: {dir_name}")
            all_good = False
        else:
            print(f"   ✅ {dir_name}: accessible and writable")
    
    if all_good:
        print(f"\n🎉 All storage directories are properly configured!")
    else:
        print(f"\n⚠️  Some storage directories have issues. Please check permissions.")
    
    return all_good

def create_sample_files():
    """Create sample files to test storage"""
    project_root = Path(__file__).parent.parent
    storage_base = project_root / "proxy_server" / "local_storage"
    
    print(f"\n🧪 Creating sample files for testing...")
    
    # Sample audio file
    audio_dir = storage_base / "user_audio"
    sample_audio = audio_dir / "sample_audio.wav"
    
    try:
        # Create a small sample audio file (just for testing)
        sample_audio.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xAC\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        print(f"   ✅ Sample audio file created: {sample_audio}")
    except Exception as e:
        print(f"   ❌ Failed to create sample audio: {e}")
    
    # Sample document
    doc_dir = storage_base / "user_documents"
    sample_doc = doc_dir / "sample_document.txt"
    
    try:
        sample_doc.write_text("This is a sample document for testing the proxy server file storage system.")
        print(f"   ✅ Sample document created: {sample_doc}")
    except Exception as e:
        print(f"   ❌ Failed to create sample document: {e}")
    
    # Sample transcript segments
    transcript_dir = storage_base / "transcript_segments"
    sample_segments = transcript_dir / "sample_segments.json"
    
    try:
        import json
        sample_data = {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello, this is the first segment."},
                {"start": 2.5, "end": 5.0, "text": "This is the second segment of the transcript."},
                {"start": 5.0, "end": 7.5, "text": "And here is the final segment."}
            ],
            "total_duration": 7.5,
            "language": "en"
        }
        sample_segments.write_text(json.dumps(sample_data, indent=2))
        print(f"   ✅ Sample transcript segments created: {sample_segments}")
    except Exception as e:
        print(f"   ❌ Failed to create sample transcript segments: {e}")

if __name__ == "__main__":
    print("🚀 Local Storage Setup for Bittensor Proxy Server")
    print("=" * 60)
    
    # Setup directories
    storage_base = setup_local_storage()
    
    # Verify setup
    verify_storage_setup()
    
    # Create sample files
    create_sample_files()
    
    print(f"\n🎯 Next Steps:")
    print(f"   1. Start your proxy server")
    print(f"   2. Test file uploads")
    print(f"   3. Check that files are stored in: {storage_base}")
    print(f"   4. Verify no more 'directory doesn't exist' errors")
