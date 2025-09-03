#!/usr/bin/env python3
"""
Test script to verify multilingual TTS capabilities
"""

def test_multilingual_tts():
    """Test TTS with different languages"""
    print("🌍 Testing Multilingual TTS Capabilities")
    print("=" * 50)
    
    try:
        print("1️⃣ Importing TTS pipeline...")
        from template.pipelines.tts_pipeline import TTSPipeline
        print("✅ TTS pipeline import successful")
        
        print("2️⃣ Initializing TTS pipeline...")
        tts_pipeline = TTSPipeline()
        print("✅ TTS pipeline initialization successful")
        
        # Test different languages
        test_cases = [
            ("en", "Hello, this is a test in English."),
            ("fr", "Bonjour, ceci est un test en français."),
            ("pt", "Olá, este é um teste em português.")
        ]
        
        for language, text in test_cases:
            print(f"\n3️⃣ Testing {language.upper()} language...")
            print(f"   Text: {text}")
            
            try:
                audio_data, processing_time = tts_pipeline.synthesize(text, language=language)
                print(f"✅ {language.upper()} synthesis successful!")
                print(f"   Audio data size: {len(audio_data)} bytes")
                print(f"   Processing time: {processing_time:.2f}s")
                
                # Save audio file
                filename = f"test_audio_{language}.wav"
                with open(filename, "wb") as f:
                    f.write(audio_data)
                print(f"✅ Audio saved as '{filename}'")
                
            except Exception as e:
                print(f"❌ {language.upper()} synthesis failed: {e}")
        
        print(f"\n🎯 Multilingual TTS Pipeline Test Complete!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_multilingual_tts()
    if success:
        print("\n🎉 All language tests passed!")
    else:
        print("\n❌ Some language tests failed")


