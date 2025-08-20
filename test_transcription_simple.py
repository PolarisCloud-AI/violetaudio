#!/usr/bin/env python3
"""
Simple test script for the transcription pipeline using Whisper tiny model.
This script tests only the transcription functionality without importing the full validator chain.
"""

import numpy as np
import soundfile as sf
import io
import time
import sys
import os

# Add the current directory to the path so we can import the pipeline directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import only the transcription pipeline
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
    
    try:
        # Initialize pipeline
        pipeline = TranscriptionPipeline("openai/whisper-tiny")
        
        print("Creating test audio...")
        # Create test audio
        audio_bytes = create_test_audio(duration=2.0)
        
        print("Testing transcription...")
        start_time = time.time()
        
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
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🎵 Testing Audio Transcription Pipeline (Simple Version)")
    print("=" * 60)
    
    success = test_transcription_pipeline()
    
    if success:
        print("\n🎉 All tests passed! The transcription pipeline is working correctly.")
    else:
        print("\n💥 Tests failed. Please check the error messages above.")
        print("\n💡 Try installing missing dependencies:")
        print("pip install transformers librosa soundfile torch")

