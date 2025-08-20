#!/usr/bin/env python3
"""
Test script for the transcription pipeline using Whisper tiny model.
This script creates a simple audio file and tests the transcription functionality.
"""

import numpy as np
import soundfile as sf
import io
import time
from template.pipelines.transcription_pipeline import TranscriptionPipeline


def create_test_audio(duration=3.0, sample_rate=16000, frequency=440.0):
    """
    Create a simple test audio file with a sine wave.
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency of the sine wave in Hz
        
    Returns:
        Audio bytes
    """
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = np.sin(2 * np.pi * frequency * t) * 0.3
    
    # Convert to 16-bit PCM
    audio = (audio * 32767).astype(np.int16)
    
    # Save to bytes
    audio_bytes = io.BytesIO()
    sf.write(audio_bytes, audio, sample_rate, format='WAV')
    audio_bytes.seek(0)
    
    return audio_bytes.read()


def test_transcription_pipeline():
    """Test the transcription pipeline with a simple audio file."""
    print("Initializing transcription pipeline...")
    
    # Initialize pipeline
    pipeline = TranscriptionPipeline("openai/whisper-tiny")
    
    print("Creating test audio...")
    # Create test audio
    audio_bytes = create_test_audio(duration=2.0)
    
    print("Testing transcription...")
    start_time = time.time()
    
    try:
        # Transcribe audio
        transcribed_text, processing_time = pipeline.transcribe(audio_bytes, language="en")
        
        total_time = time.time() - start_time
        
        print(f"✅ Transcription successful!")
        print(f"📝 Transcribed text: '{transcribed_text}'")
        print(f"⏱️  Processing time: {processing_time:.2f}s")
        print(f"⏱️  Total time (including model loading): {total_time:.2f}s")
        print(f"🔧 Model used: {pipeline.model_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Transcription failed: {str(e)}")
        return False


if __name__ == "__main__":
    print("🎵 Testing Audio Transcription Pipeline")
    print("=" * 50)
    
    success = test_transcription_pipeline()
    
    if success:
        print("\n🎉 All tests passed! The transcription pipeline is working correctly.")
    else:
        print("\n💥 Tests failed. Please check the error messages above.")
