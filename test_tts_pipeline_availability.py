#!/usr/bin/env python3
"""
Test script to check TTS pipeline availability
"""

def test_tts_pipeline_import():
    """Test if TTS pipeline can be imported"""
    print("🧪 Testing TTS Pipeline Availability")
    print("=" * 50)
    
    try:
        print("1️⃣ Attempting to import TTS pipeline...")
        from template.pipelines.tts_pipeline import TTSPipeline
        print("✅ TTS pipeline import successful")
        
        print("2️⃣ Attempting to initialize TTS pipeline...")
        tts_pipeline = TTSPipeline()
        print("✅ TTS pipeline initialization successful")
        
        print("3️⃣ Testing TTS pipeline methods...")
        if hasattr(tts_pipeline, 'synthesize'):
            print("✅ TTS pipeline has 'synthesize' method")
        else:
            print("❌ TTS pipeline missing 'synthesize' method")
            
        return True
        
    except ImportError as e:
        print(f"❌ TTS pipeline import failed: {e}")
        print("   This means the TTS module is not installed")
        return False
    except Exception as e:
        print(f"❌ TTS pipeline initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = test_tts_pipeline_import()
    if success:
        print("\n🎯 TTS Pipeline is available and working!")
    else:
        print("\n❌ TTS Pipeline is not available - this explains why tasks aren't being processed")


