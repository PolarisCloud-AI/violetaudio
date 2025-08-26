# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2024 Bittensor Subnet Template

import time
import torch
import numpy as np
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import librosa
import io
import soundfile as sf
from typing import Optional, Tuple, List, Dict, Union
import gc
import logging
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TranscriptionChunk:
    """Represents a transcribed audio chunk with timing information"""
    start_time: float
    end_time: float
    text: str
    confidence: float
    language: str
    chunk_index: int

@dataclass
class TranscriptionResult:
    """Complete transcription result with chunks and metadata"""
    full_text: str
    chunks: List[TranscriptionChunk]
    total_duration: float
    processing_time: float
    language: str
    metadata: Dict

class TranscriptionPipeline:
    """
    Clean and efficient audio transcription pipeline using Whisper models.
    Supports timestamped chunks and is compatible with existing miner code.
    """
    
    def __init__(self, model_name: str = "openai/whisper-tiny", chunk_duration: float = 30.0):
        """
        Initialize the transcription pipeline.
        
        Args:
            model_name: HuggingFace model name for Whisper
            chunk_duration: Duration of each audio chunk in seconds
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.chunk_duration = chunk_duration
        
        # Load model and processor
        logger.info(f"🔄 Loading Whisper model: {model_name}")
        self.processor = WhisperProcessor.from_pretrained(model_name)
        self.model = WhisperForConditionalGeneration.from_pretrained(model_name)
        self.model.to(self.device)
        logger.info(f"✅ Whisper model loaded successfully on {self.device}")
        
        # Language code mapping
        self.language_codes = {
            "en": "english", "es": "spanish", "fr": "french", "de": "german",
            "it": "italian", "pt": "portuguese", "ru": "russian", "ja": "japanese",
            "ko": "korean", "zh": "chinese", "ar": "arabic", "hi": "hindi"
        }
    
    def transcribe(self, audio_bytes: bytes, language: str = "en") -> Tuple[str, float]:
        """
        Transcribe audio and return (transcript, processing_time) tuple.
        This maintains compatibility with existing miner code.
        
        Args:
            audio_bytes: Raw audio data
            language: Language code (e.g., 'en', 'es')
            
        Returns:
            Tuple of (transcript_text, processing_time)
        """
        start_time = time.time()
        
        try:
            logger.info(f"🎵 Starting transcription of {len(audio_bytes)} bytes")
            
            # Preprocess audio
            audio_array, sample_rate = self.preprocess_audio(audio_bytes)
            audio_duration = len(audio_array) / sample_rate
            
            logger.info(f"📊 Audio info: {audio_duration:.2f}s duration, {sample_rate}Hz sample rate")
            
            # Check if chunking is needed
            should_chunk = audio_duration > self.chunk_duration
            
            if should_chunk:
                logger.info(f"✂️ Chunking audio for better processing")
                result = self._transcribe_chunked(audio_array, sample_rate, language, start_time)
            else:
                logger.info(f"🔄 Processing audio as single chunk")
                result = self._transcribe_single(audio_array, sample_rate, language, start_time)
            
            # Return tuple format for compatibility
            return result.full_text, result.processing_time
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Transcription failed: {e}")
            return "", processing_time
    
    def transcribe_with_timestamps(self, audio_bytes: bytes, language: str = "en") -> TranscriptionResult:
        """
        Transcribe audio with full timestamp information.
        Use this when you need detailed timing data.
        
        Args:
            audio_bytes: Raw audio data
            language: Language code
            
        Returns:
            TranscriptionResult with full metadata
        """
        start_time = time.time()
        
        try:
            logger.info(f"🎵 Starting timestamped transcription of {len(audio_bytes)} bytes")
            
            # Preprocess audio
            audio_array, sample_rate = self.preprocess_audio(audio_bytes)
            audio_duration = len(audio_array) / sample_rate
            
            # Check if chunking is needed
            should_chunk = audio_duration > self.chunk_duration
            
            if should_chunk:
                return self._transcribe_chunked(audio_array, sample_rate, language, start_time)
            else:
                return self._transcribe_single(audio_array, sample_rate, language, start_time)
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Timestamped transcription failed: {e}")
            raise Exception(f"Transcription failed: {str(e)}")
    
    def _transcribe_single(self, audio_array: np.ndarray, sample_rate: int, language: str, start_time: float) -> TranscriptionResult:
        """Transcribe audio as a single chunk"""
        try:
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
            
            # Create single chunk
            chunk = TranscriptionChunk(
                start_time=0.0,
                end_time=len(audio_array) / sample_rate,
                text=transcription.strip(),
                confidence=0.9,
                language=language,
                chunk_index=0
            )
            
            return TranscriptionResult(
                full_text=transcription.strip(),
                chunks=[chunk],
                total_duration=len(audio_array) / sample_rate,
                processing_time=processing_time,
                language=language,
                metadata={
                    'chunked': False,
                    'chunk_count': 1,
                    'model_used': self.model_name,
                    'device': self.device
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Single chunk transcription failed: {e}")
            raise
    
    def _transcribe_chunked(self, audio_array: np.ndarray, sample_rate: int, language: str, start_time: float) -> TranscriptionResult:
        """Transcribe audio in chunks with timing information"""
        try:
            # Segment audio
            chunks = self._segment_audio(audio_array, sample_rate)
            
            # Process chunks sequentially for reliability
            transcribed_chunks = []
            full_text_parts = []
            
            for i, (chunk, start_time_chunk, end_time_chunk) in enumerate(chunks):
                try:
                    # Prepare input for Whisper
                    inputs = self.processor(
                        chunk, 
                        sampling_rate=sample_rate, 
                        return_tensors="pt"
                    ).input_features.to(self.device)
                    
                    # Generate transcription
                    predicted_ids = self.model.generate(inputs)
                    transcription = self.processor.batch_decode(
                        predicted_ids, 
                        skip_special_tokens=True
                    )[0]
                    
                    # Calculate confidence (simple heuristic)
                    confidence = min(0.95, max(0.5, len(transcription.strip()) / 50))
                    
                    # Create chunk result
                    chunk_result = TranscriptionChunk(
                        start_time=start_time_chunk,
                        end_time=end_time_chunk,
                        text=transcription.strip(),
                        confidence=confidence,
                        language=language,
                        chunk_index=i
                    )
                    
                    transcribed_chunks.append(chunk_result)
                    full_text_parts.append(transcription.strip())
                    
                    logger.info(f"✅ Chunk {i+1}/{len(chunks)} transcribed: {start_time_chunk:.1f}s - {end_time_chunk:.1f}s")
                    
                except Exception as e:
                    logger.error(f"❌ Chunk {i} transcription failed: {e}")
                    # Create empty chunk for failed segment
                    chunk_result = TranscriptionChunk(
                        start_time=start_time_chunk,
                        end_time=end_time_chunk,
                        text="[Transcription failed]",
                        confidence=0.0,
                        language=language,
                        chunk_index=i
                    )
                    transcribed_chunks.append(chunk_result)
                    full_text_parts.append("[Transcription failed]")
            
            processing_time = time.time() - start_time
            
            return TranscriptionResult(
                full_text=" ".join(full_text_parts),
                chunks=transcribed_chunks,
                total_duration=len(audio_array) / sample_rate,
                processing_time=processing_time,
                language=language,
                metadata={
                    'chunked': True,
                    'chunk_count': len(chunks),
                    'model_used': self.model_name,
                    'device': self.device
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Chunked transcription failed: {e}")
            raise
    
    def _segment_audio(self, audio_array: np.ndarray, sample_rate: int) -> List[Tuple[np.ndarray, float, float]]:
        """Segment audio into chunks with timing information"""
        chunk_samples = int(self.chunk_duration * sample_rate)
        chunks = []
        
        for i in range(0, len(audio_array), chunk_samples):
            start_sample = i
            end_sample = min(i + chunk_samples, len(audio_array))
            
            # Extract chunk
            chunk = audio_array[start_sample:end_sample]
            
            # Calculate timing
            start_time = start_sample / sample_rate
            end_time = end_sample / sample_rate
            
            chunks.append((chunk, start_time, end_time))
        
        logger.info(f"📊 Audio segmented into {len(chunks)} chunks of ~{self.chunk_duration}s each")
        return chunks
    
    def preprocess_audio(self, audio_bytes: bytes) -> Tuple[np.ndarray, int]:
        """Preprocess audio data for transcription"""
        try:
            # Load audio using librosa
            audio_array, sample_rate = librosa.load(io.BytesIO(audio_bytes), sr=16000)
            
            # Convert to mono if stereo
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            # Normalize audio
            if np.max(np.abs(audio_array)) > 0:
                audio_array = audio_array / np.max(np.abs(audio_array))
            
            logger.info(f"✅ Audio preprocessed: {len(audio_array)} samples, {sample_rate}Hz")
            return audio_array, sample_rate
            
        except Exception as e:
            logger.error(f"❌ Audio preprocessing failed: {e}")
            raise
    
    def format_timed_transcript(self, result: TranscriptionResult, format_type: str = "plain") -> str:
        """
        Format transcript with timing information.
        
        Args:
            result: TranscriptionResult object
            format_type: 'plain', 'srt', 'vtt', or 'timestamps'
            
        Returns:
            Formatted transcript string
        """
        if format_type == "srt":
            return self._format_srt(result)
        elif format_type == "vtt":
            return self._format_vtt(result)
        elif format_type == "timestamps":
            return self._format_plain_timestamps(result)
        else:
            return self._format_plain(result)
    
    def _format_plain(self, result: TranscriptionResult) -> str:
        """Format transcript as plain text with timestamps"""
        lines = []
        for chunk in result.chunks:
            timestamp = self._format_timestamp(chunk.start_time)
            lines.append(f"{timestamp} {chunk.text}")
        return "\n".join(lines)
    
    def _format_srt(self, result: TranscriptionResult) -> str:
        """Format transcript in SRT subtitle format"""
        lines = []
        for i, chunk in enumerate(result.chunks):
            lines.append(str(i + 1))
            start_time = self._format_timestamp_srt(chunk.start_time)
            end_time = self._format_timestamp_srt(chunk.end_time)
            lines.append(f"{start_time} --> {end_time}")
            lines.append(chunk.text)
            lines.append("")
        return "\n".join(lines)
    
    def _format_vtt(self, result: TranscriptionResult) -> str:
        """Format transcript in WebVTT format"""
        lines = ["WEBVTT", ""]
        for chunk in result.chunks:
            start_time = self._format_timestamp_vtt(chunk.start_time)
            end_time = self._format_timestamp_vtt(chunk.end_time)
            lines.append(f"{start_time} --> {end_time}")
            lines.append(chunk.text)
            lines.append("")
        return "\n".join(lines)
    
    def _format_plain_timestamps(self, result: TranscriptionResult) -> str:
        """Format transcript with plain timestamps"""
        lines = []
        for chunk in result.chunks:
            timestamp = f"[{chunk.start_time:.2f}s - {chunk.end_time:.2f}s]"
            lines.append(f"{timestamp} {chunk.text}")
        return "\n".join(lines)
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to MM:SS format"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _format_timestamp_srt(self, seconds: float) -> str:
        """Format seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_timestamp_vtt(self, seconds: float) -> str:
        """Format seconds to WebVTT timestamp format (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    def get_supported_languages(self) -> list:
        """Get list of supported language codes."""
        return list(self.language_codes.keys())
    
    def validate_language(self, language: str) -> bool:
        """Validate if language is supported."""
        return language in self.language_codes
    
    def cleanup_memory(self):
        """Clean up memory and GPU cache"""
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            logger.info("🧹 Memory cleanup completed")
        except Exception as e:
            logger.warning(f"⚠️ Memory cleanup failed: {e}")

# Global instance for backward compatibility
transcription_pipeline = TranscriptionPipeline()
