#!/usr/bin/env python3
"""
Simple TTS test to verify the pipeline is working
"""

def test_simple_tts():
    """Test simple TTS operation"""
    print("🧪 Testing Simple TTS Operation")
    print("=" * 50)
    
    try:
        print("1️⃣ Importing TTS pipeline...")
        from template.pipelines.tts_pipeline import TTSPipeline
        print("✅ TTS pipeline import successful")
        
        print("2️⃣ Initializing TTS pipeline...")
        tts_pipeline = TTSPipeline()
        print("✅ TTS pipeline initialization successful")
        
        print("3️⃣ Testing simple text synthesis...")
        test_text = "Hello, this is a test."
        
        # Test the synthesize method
        if hasattr(tts_pipeline, 'synthesize'):
            print("✅ TTS pipeline has 'synthesize' method")
            
            # Try to synthesize audio without language parameter
            print("4️⃣ Attempting to synthesize audio...")
            try:
                audio_data, processing_time = tts_pipeline.synthesize(test_text)
                print(f"✅ Audio synthesis successful!")
                print(f"   Audio data size: {len(audio_data)} bytes")
                print(f"   Processing time: {processing_time:.2f}s")
                
                # Save a small test file
                with open("test_audio.wav", "wb") as f:
                    f.write(audio_data)
                print("✅ Test audio file saved as 'test_audio.wav'")
                
                return True
                
            except Exception as e:
                print(f"❌ Audio synthesis failed: {e}")
                return False
        else:
            print("❌ TTS pipeline missing 'synthesize' method")
            return False
            
    except ImportError as e:
        print(f"❌ TTS pipeline import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ TTS pipeline error: {e}")
        return False

if __name__ == "__main__":
    success = test_simple_tts()
    if success:
        print("\n🎯 TTS Pipeline is working correctly!")
    else:
        print("\n❌ TTS Pipeline has issues")
