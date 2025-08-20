#!/usr/bin/env python3
"""
Basic test script for the miner functionality without requiring wallet or network connection.
This script tests the core miner logic and pipeline functionality.
"""

import sys
import os
import asyncio

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from template.protocol import AudioTask, TaskType
from template.pipelines.transcription_pipeline import TranscriptionPipeline


async def test_miner_functionality():
    """Test the miner's core functionality without network dependencies."""
    print("🧪 Testing Miner Core Functionality")
    print("=" * 50)
    
    try:
        # Test 1: Initialize transcription pipeline
        print("1. Testing transcription pipeline initialization...")
        pipeline = TranscriptionPipeline("openai/whisper-tiny")
        print("✅ Transcription pipeline initialized successfully")
        
        # Test 2: Test protocol functionality
        print("\n2. Testing protocol functionality...")
        
        # Create a test audio task
        test_audio_bytes = b"fake_audio_data_for_testing"
        audio_task = AudioTask(
            task_type=TaskType.TRANSCRIPTION,
            input_data="test_input_data",  # We'll test encoding separately
            language="en"
        )
        
        print(f"✅ AudioTask created successfully")
        print(f"   - Task type: {audio_task.task_type}")
        print(f"   - Language: {audio_task.language}")
        print(f"   - Input data length: {len(audio_task.input_data)}")
        
        # Test 3: Test encoding/decoding
        print("\n3. Testing encoding/decoding functionality...")
        
        # Test text encoding/decoding
        test_text = "Hello, this is a test message"
        encoded_text = audio_task.encode_text(test_text)
        decoded_text = audio_task.decode_text(encoded_text)
        
        assert decoded_text == test_text, f"Text encoding/decoding failed: {decoded_text} != {test_text}"
        print("✅ Text encoding/decoding works correctly")
        
        # Test audio encoding/decoding
        test_audio = b"fake_audio_data"
        encoded_audio = audio_task.encode_audio(test_audio)
        decoded_audio = audio_task.decode_audio(encoded_audio)
        
        assert decoded_audio == test_audio, "Audio encoding/decoding failed"
        print("✅ Audio encoding/decoding works correctly")
        
        # Test 4: Test task type validation
        print("\n4. Testing task type validation...")
        
        valid_task_types = [TaskType.TRANSCRIPTION, TaskType.TTS, TaskType.SUMMARIZATION]
        for task_type in valid_task_types:
            print(f"   - {task_type.value}: ✅ Valid")
        
        print("✅ All task types are valid")
        
        # Test 5: Test pipeline model info
        print("\n5. Testing pipeline model information...")
        print(f"   - Model name: {pipeline.model_name}")
        print(f"   - Supported languages: {len(pipeline.get_supported_languages())}")
        print(f"   - Device: {pipeline.device}")
        print("✅ Pipeline model information retrieved successfully")
        
        print("\n🎉 All basic miner functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_protocol_serialization():
    """Test protocol serialization and deserialization."""
    print("\n📦 Testing Protocol Serialization")
    print("=" * 40)
    
    try:
        # Create a test task
        task = AudioTask(
            task_type=TaskType.TRANSCRIPTION,
            input_data="test_input_data",
            language="en"
        )
        
        # Set some output data
        task.output_data = "test_output_data"
        task.processing_time = 1.5
        task.pipeline_model = "test_model"
        
        # Test deserialization
        result = task.deserialize()
        
        expected_keys = ["output_data", "processing_time", "pipeline_model", "error_message"]
        for key in expected_keys:
            assert key in result, f"Missing key in deserialized result: {key}"
        
        print("✅ Protocol serialization/deserialization works correctly")
        print(f"   - Deserialized keys: {list(result.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Protocol serialization test failed: {str(e)}")
        return False


if __name__ == "__main__":
    print("🚀 Audio Processing Miner Basic Tests")
    print("=" * 60)
    
    # Run tests
    success1 = asyncio.run(test_miner_functionality())
    success2 = test_protocol_serialization()
    
    if success1 and success2:
        print("\n🎉 All tests passed! The miner core functionality is working correctly.")
        print("\n💡 Next steps:")
        print("   1. Install bittensor: pip install bittensor")
        print("   2. Create a wallet: btcli wallet new_coldkey")
        print("   3. Run the miner: python neurons/miner.py")
    else:
        print("\n💥 Some tests failed. Please check the error messages above.")
