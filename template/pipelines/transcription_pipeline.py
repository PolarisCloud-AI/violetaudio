# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

import time
import torch
import numpy as np
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import librosa
import io
import soundfile as sf
from typing import Optional, Tuple


class TranscriptionPipeline:
    """
    Audio transcription pipeline using Whisper models.
    Supports multiple languages and model sizes.
    """
    
    def __init__(self, model_name: str = "openai/whisper-tiny"):
        """
        Initialize the transcription pipeline.
        
        Args:
            model_name: HuggingFace model name for Whisper
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load model and processor
        self.processor = WhisperProcessor.from_pretrained(model_name)
        self.model = WhisperForConditionalGeneration.from_pretrained(model_name)
        self.model.to(self.device)
        
        # Language code mapping
        self.language_codes = {
            "en": "english",
            "es": "spanish", 
            "fr": "french",
            "de": "german",
            "it": "italian",
            "pt": "portuguese",
            "ru": "russian",
            "ja": "japanese",
            "ko": "korean",
            "zh": "chinese"
        }
    
    def preprocess_audio(self, audio_bytes: bytes) -> Tuple[np.ndarray, int]:
        """
        Preprocess audio bytes to the format expected by Whisper.
        
        Args:
            audio_bytes: Raw audio bytes
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        # Load audio from bytes
        audio_array, sample_rate = sf.read(io.BytesIO(audio_bytes))
        
        # Convert to mono if stereo
        if len(audio_array.shape) > 1:
            audio_array = np.mean(audio_array, axis=1)
        
        # Resample to 16kHz if needed (Whisper requirement)
        if sample_rate != 16000:
            audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=16000)
            sample_rate = 16000
        
        return audio_array, sample_rate
    
    def transcribe(self, audio_bytes: bytes, language: str = "en") -> Tuple[str, float]:
        """
        Transcribe audio to text.
        
        Args:
            audio_bytes: Raw audio bytes
            language: Language code (e.g., 'en', 'es', 'fr')
            
        Returns:
            Tuple of (transcribed_text, processing_time)
        """
        start_time = time.time()
        
        try:
            # Preprocess audio
            audio_array, sample_rate = self.preprocess_audio(audio_bytes)
            
            # Prepare input for Whisper
            inputs = self.processor(
                audio_array, 
                sampling_rate=sample_rate, 
                return_tensors="pt"
            ).input_features.to(self.device)
            
            # Generate transcription
            predicted_ids = self.model.generate(inputs)
            transcription = self.processor.batch_decode(
                predicted_ids, 
                skip_special_tokens=True
            )[0]
            
            processing_time = time.time() - start_time
            
            return transcription.strip(), processing_time
            
        except Exception as e:
            processing_time = time.time() - start_time
            raise Exception(f"Transcription failed: {str(e)}")
    
    def get_supported_languages(self) -> list:
        """Get list of supported language codes."""
        return list(self.language_codes.keys())
    
    def validate_language(self, language: str) -> bool:
        """Validate if language is supported."""
        return language in self.language_codes
