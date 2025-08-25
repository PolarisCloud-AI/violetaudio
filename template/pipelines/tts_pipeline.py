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
from typing import Optional, Tuple, List, Dict
import gc
import psutil
import logging
from dataclasses import dataclass
import threading
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TTSSynthesisResult:
    """Result of TTS synthesis with metadata"""
    audio_bytes: bytes
    processing_time: float
    text_length: int
    audio_duration: float
    sample_rate: int
    language: str
    speaker: Optional[str]
    metadata: Dict


class TTSPipeline:
    """
    Text-to-Speech pipeline using Coqui TTS models.
    Supports multiple languages and voices.
    """
    
    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/your_tts"):
        """
        Initialize the TTS pipeline with a multilingual model.
        
        Args:
            model_name: TTS model name from Coqui TTS (default: multilingual model)
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load TTS model
        try:
            self.tts = TTS(model_name=model_name)
            self.tts.to(self.device)
            print(f"✅ Loaded TTS model: {model_name}")
        except Exception as e:
            print(f"⚠️ Failed to load {model_name}, trying fallback multilingual model...")
            # Fallback to a known multilingual model
            try:
                self.tts = TTS(model_name="tts_models/multilingual/multi-dataset/your_tts")
                self.tts.to(self.device)
                print(f"✅ Loaded fallback TTS model: tts_models/multilingual/multi-dataset/your_tts")
            except Exception as e2:
                print(f"❌ Failed to load fallback model: {e2}")
                raise Exception(f"Could not load any TTS model: {e}, {e2}")
        
        # Language code mapping for multilingual model
        self.language_codes = {
            "en": "en",
            "es": "es", 
            "fr": "fr-fr",
            "de": "de",
            "it": "it",
            "pt": "pt-br",
            "ru": "ru",
            "ja": "ja",
            "ko": "ko",
            "zh": "zh",
            "ar": "ar",
            "hi": "hi",
            "nl": "nl",
            "pl": "pl",
            "sv": "sv",
            "tr": "tr"
        }
        
        # Check if model is multilingual
        self.is_multilingual = hasattr(self.tts, 'languages') and self.tts.languages is not None
        if self.is_multilingual:
            logger.info(f"✅ Using multilingual TTS model with languages: {self.tts.languages}")
        else:
            logger.warning(f"⚠️ Model may not be multilingual, language parameter may be ignored")
        
        # Production settings
        self.max_text_length = 5000  # Maximum characters per synthesis
        self.chunk_overlap = 100     # Characters overlap between chunks
        
        # Performance monitoring
        self.processing_stats = {
            'total_syntheses': 0,
            'total_text_length': 0,
            'total_processing_time': 0.0,
            'memory_usage_samples': []
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
            synthesis_params = {"text": text}
            
            # Add language if model is multilingual
            if self.is_multilingual and language in self.language_codes:
                synthesis_params["language"] = self.language_codes.get(language, "en")
                print(f"🎵 Using language: {language} for TTS synthesis")
            elif not self.is_multilingual:
                print(f"⚠️ Model is not multilingual, ignoring language parameter: {language}")
            
            # Add speaker if specified and supported
            if speaker and hasattr(self.tts, 'speakers') and speaker in self.tts.speakers:
                synthesis_params["speaker"] = speaker
                print(f"🎤 Using speaker: {speaker}")
            elif hasattr(self.tts, 'speakers') and self.tts.speakers:
                # Auto-select first available speaker if none specified
                default_speaker = self.tts.speakers[0]
                synthesis_params["speaker"] = default_speaker
                print(f"🎤 Auto-selected speaker: {default_speaker}")
            
            print(f"🔧 TTS synthesis parameters: {synthesis_params}")
            
            # Synthesize audio
            audio_array = self.tts.tts(**synthesis_params)
            
            # Convert to bytes
            audio_bytes = io.BytesIO()
            sf.write(audio_bytes, audio_array, self.tts.synthesizer.output_sample_rate, format='WAV')
            audio_bytes.seek(0)
            
            processing_time = time.time() - start_time
            print(f"✅ TTS synthesis completed in {processing_time:.2f}s")
            
            return audio_bytes.read(), processing_time
            
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"❌ TTS synthesis error: {str(e)}")
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
    
    def _update_stats(self, text_length: int, processing_time: float):
        """Update processing statistics"""
        self.processing_stats['total_syntheses'] += 1
        self.processing_stats['total_text_length'] += text_length
        self.processing_stats['total_processing_time'] += processing_time
    
    def _cleanup_memory(self):
        """Clean up memory and perform garbage collection"""
        try:
            # Clear CUDA cache if using GPU
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Force garbage collection
            gc.collect()
            
            # Log memory usage
            process = psutil.Process()
            current_memory = process.memory_info().rss / (1024 * 1024 * 1024)
            self.processing_stats['memory_usage_samples'].append(current_memory)
            logger.info(f"🧹 Memory cleanup completed. Current usage: {current_memory:.2f}GB")
            
        except Exception as e:
            logger.warning(f"⚠️ Memory cleanup failed: {e}")
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        return {
            'total_syntheses': self.processing_stats['total_syntheses'],
            'total_text_length': self.processing_stats['total_text_length'],
            'total_processing_time': self.processing_stats['total_processing_time'],
            'average_processing_speed': (
                self.processing_stats['total_text_length'] / 
                max(self.processing_stats['total_processing_time'], 0.001)
            ),
            'memory_usage_samples': self.processing_stats['memory_usage_samples'][-10:],  # Last 10 samples
            'model_info': {
                'name': self.model_name,
                'max_text_length': self.max_text_length,
                'chunk_overlap': self.chunk_overlap
            }
        }
    
    def optimize_for_production(self, target_max_text_length: int = 3000, target_chunk_overlap: int = 50):
        """Optimize pipeline settings for production use"""
        self.max_text_length = target_max_text_length
        self.chunk_overlap = target_chunk_overlap
        
        logger.info(f"⚙️ TTS pipeline optimized for production:")
        logger.info(f"   Max text length: {target_max_text_length} characters")
        logger.info(f"   Chunk overlap: {target_chunk_overlap} characters")
        
        # Force memory cleanup
        self._cleanup_memory()
