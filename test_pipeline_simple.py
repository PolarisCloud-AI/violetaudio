#!/usr/bin/env python3
"""
Simple pipeline test with real audio file - no Bittensor initialization
"""

import os
import sys
import time
import torch
from transformers import pipeline

def test_transcription_pipeline_direct():
    """Test the transcription pipeline directly without miner initialization"""
    
    # Path to the real audio file
    audio_file_path = "proxy_server/local_storage/user_audio/7290cb3e-3c5c-4b53-8e49-c182e3357f5d_LJ037-0171.wav"
    
    if not os.path.exists(audio_file_path):
        print(f"❌ Audio file not found: {audio_file_path}")
        return
    
    print(f"🎵 Testing transcription pipeline with: {audio_file_path}")
    print(f"📁 File size: {os.path.getsize(audio_file_path)} bytes")
    
    try:
        # Initialize the transcription pipeline directly
        print("🔧 Initializing Whisper transcription pipeline...")
        transcription_pipeline = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-base",
            device="cpu"  # Use CPU to avoid GPU issues
        )
        
        print("✅ Pipeline initialized successfully")
        
        # Test the transcription pipeline directly
        print("🎯 Testing transcription pipeline...")
        start_time = time.time()
        
        # Process the audio file
        result = transcription_pipeline(audio_file_path)
        
        processing_time = time.time() - start_time
        
        print("✅ Transcription Pipeline Test Results:")
        print(f"   📝 Transcript: {result.get('text', 'N/A')}")
        print(f"   ⏱️  Processing Time: {processing_time:.2f}s")
        
        # Test with raw audio data
        print("\n🔍 Testing with raw audio data...")
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        
        print(f"📊 Audio data loaded: {len(audio_data)} bytes")
        
        # Test TTS pipeline
        print("\n🔊 Testing TTS pipeline...")
        try:
            tts_pipeline = pipeline(
                "text-to-speech",
                model="microsoft/speecht5_tts",
                device="cpu"
            )
            
            # Use a simple test text
            test_text = "Hello, this is a test of the text to speech pipeline."
            print(f"📝 Test text: {test_text}")
            
            tts_result = tts_pipeline(test_text)
            print(f"✅ TTS pipeline working - Output type: {type(tts_result)}")
            
        except Exception as e:
            print(f"⚠️ TTS pipeline test failed: {e}")
        
        # Test summarization pipeline
        print("\n📝 Testing summarization pipeline...")
        try:
            summarization_pipeline = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device="cpu"
            )
            
            # Use the transcript as input for summarization
            if 'text' in result:
                test_text = result['text']
                if len(test_text) > 50:  # Only summarize if we have enough text
                    summary_result = summarization_pipeline(test_text, max_length=50, min_length=10)
                    print(f"✅ Summarization pipeline working - Summary: {summary_result[0]['summary_text']}")
                else:
                    print(f"⚠️ Text too short for summarization: '{test_text}'")
            else:
                print("⚠️ No transcript available for summarization test")
                
        except Exception as e:
            print(f"⚠️ Summarization pipeline test failed: {e}")
        
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Simple Pipeline Test")
    print("=" * 50)
    
    test_transcription_pipeline_direct()
    
    print("\n" + "=" * 50)
    print("🏁 Pipeline test completed")

