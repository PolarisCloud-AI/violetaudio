# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

import time
import torch
import numpy as np
from TTS.api import TTS
import io
import soundfile as sf
from typing import Optional, Tuple


class TTSPipeline:
    """
    Text-to-Speech pipeline using Coqui TTS models.
    Supports multiple languages and voices.
    """
    
    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"):
        """
        Initialize the TTS pipeline.
        
        Args:
            model_name: TTS model name from Coqui TTS
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load TTS model
        self.tts = TTS(model_name=model_name)
        self.tts.to(self.device)
        
        # Language code mapping
        self.language_codes = {
            "en": "en",
            "es": "es", 
            "fr": "fr",
            "de": "de",
            "it": "it",
            "pt": "pt",
            "ru": "ru",
            "ja": "ja",
            "ko": "ko",
            "zh": "zh"
        }
    
    def synthesize(self, text: str, language: str = "en", speaker: Optional[str] = None) -> Tuple[bytes, float]:
        """
        Synthesize text to speech.
        
        Args:
            text: Input text to synthesize
            language: Language code (e.g., 'en', 'es', 'fr')
            speaker: Speaker name (if model supports multiple speakers)
            
        Returns:
            Tuple of (audio_bytes, processing_time)
        """
        start_time = time.time()
        
        try:
            # Prepare synthesis parameters
            synthesis_params = {
                "text": text,
                "language": self.language_codes.get(language, "en")
            }
            
            # Add speaker if specified and supported
            if speaker and hasattr(self.tts, 'speakers') and speaker in self.tts.speakers:
                synthesis_params["speaker"] = speaker
            
            # Synthesize audio
            audio_array = self.tts.tts(**synthesis_params)
            
            # Convert to bytes
            audio_bytes = io.BytesIO()
            sf.write(audio_bytes, audio_array, self.tts.synthesizer.output_sample_rate, format='WAV')
            audio_bytes.seek(0)
            
            processing_time = time.time() - start_time
            
            return audio_bytes.read(), processing_time
            
        except Exception as e:
            processing_time = time.time() - start_time
            raise Exception(f"TTS synthesis failed: {str(e)}")
    
    def get_available_models(self) -> list:
        """Get list of available TTS models."""
        return TTS.list_models()
    
    def get_supported_languages(self) -> list:
        """Get list of supported language codes."""
        return list(self.language_codes.keys())
    
    def validate_language(self, language: str) -> bool:
        """Validate if language is supported."""
        return language in self.language_codes
    
    def get_available_speakers(self) -> list:
        """Get list of available speakers (if model supports multiple speakers)."""
        if hasattr(self.tts, 'speakers'):
            return self.tts.speakers
        return []
