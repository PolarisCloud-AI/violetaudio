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
from typing import Optional, Tuple, List, Dict, Union
import gc
import psutil
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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
    Enhanced audio transcription pipeline using Whisper models.
    Supports timestamped chunks, memory management, and production-ready features.
    """
    
    def __init__(self, model_name: str = "openai/whisper-tiny", chunk_duration: float = 30.0, max_memory_gb: float = 4.0):
        """
        Initialize the enhanced transcription pipeline.
        
        Args:
            model_name: HuggingFace model name for Whisper
            chunk_duration: Duration of each audio chunk in seconds
            max_memory_gb: Maximum memory usage in GB before chunking
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.chunk_duration = chunk_duration
        self.max_memory_gb = max_memory_gb
        self.max_memory_bytes = max_memory_gb * 1024 * 1024 * 1024
        
        # Load model and processor
        logger.info(f"🔄 Loading Whisper model: {model_name}")
        self.processor = WhisperProcessor.from_pretrained(model_name)
        self.model = WhisperForConditionalGeneration.from_pretrained(model_name)
        self.model.to(self.device)
        logger.info(f"✅ Whisper model loaded successfully on {self.device}")
        
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
            "zh": "chinese",
            "ar": "arabic",
            "hi": "hindi",
            "nl": "dutch",
            "pl": "polish",
            "sv": "swedish",
            "tr": "turkish",
            "bg": "bulgarian",
            "ca": "catalan",
            "cs": "czech",
            "da": "danish",
            "el": "greek",
            "et": "estonian",
            "fi": "finnish",
            "hr": "croatian",
            "hu": "hungarian",
            "id": "indonesian",
            "lt": "lithuanian",
            "lv": "latvian",
            "ms": "malay",
            "mt": "maltese",
            "no": "norwegian",
            "ro": "romanian",
            "sk": "slovak",
            "sl": "slovenian",
            "th": "thai",
            "uk": "ukrainian",
            "vi": "vietnamese"
        }
        
        # Performance monitoring
        self.processing_stats = {
            'total_files_processed': 0,
            'total_audio_duration': 0.0,
            'total_processing_time': 0.0,
            'memory_usage_samples': []
        }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in GB"""
        process = psutil.Process()
        memory_gb = process.memory_info().rss / (1024 * 1024 * 1024)
        self.processing_stats['memory_usage_samples'].append(memory_gb)
        return memory_gb
    
    def _should_chunk_audio(self, audio_duration: float, audio_size_bytes: int) -> bool:
        """Determine if audio should be chunked based on duration and memory constraints"""
        # Chunk if audio is longer than chunk duration
        if audio_duration > self.chunk_duration:
            return True
        
        # Chunk if audio file is larger than memory threshold
        if audio_size_bytes > self.max_memory_bytes * 0.5:  # 50% of max memory
            return True
        
        # Chunk if current memory usage is high
        current_memory = self._get_memory_usage()
        if current_memory > self.max_memory_gb * 0.8:  # 80% of max memory
            return True
        
        return False
    
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
    
    def _transcribe_chunk(self, chunk_data: Tuple[np.ndarray, float, float], language: str, chunk_index: int) -> TranscriptionChunk:
        """Transcribe a single audio chunk"""
        chunk, start_time, end_time = chunk_data
        
        try:
            # Prepare input for Whisper
            inputs = self.processor(
                chunk, 
                sampling_rate=16000, 
                return_tensors="pt"
            ).input_features.to(self.device)
            
            # Generate transcription
            predicted_ids = self.model.generate(inputs)
            transcription = self.processor.batch_decode(
                predicted_ids, 
                skip_special_tokens=True
            )[0]
            
            # Calculate confidence (simple heuristic based on text length)
            confidence = min(0.95, max(0.5, len(transcription.strip()) / 50))
            
            return TranscriptionChunk(
                start_time=start_time,
                end_time=end_time,
                text=transcription.strip(),
                confidence=confidence,
                language=language,
                chunk_index=chunk_index
            )
            
        except Exception as e:
            logger.error(f"❌ Chunk {chunk_index} transcription failed: {e}")
            # Return empty chunk with error info
            return TranscriptionChunk(
                start_time=start_time,
                end_time=end_time,
                text=f"[Transcription Error: {str(e)}]",
                confidence=0.0,
                language=language,
                chunk_index=chunk_index
            )
    
    def preprocess_audio(self, audio_bytes: bytes) -> Tuple[np.ndarray, int]:
        """
        Preprocess audio bytes to the format expected by Whisper.
        
        Args:
            audio_bytes: Raw audio bytes
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        try:
            # Load audio from bytes
            audio_array, sample_rate = sf.read(io.BytesIO(audio_bytes))
            
            # Convert to mono if stereo
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            # Resample to 16kHz if needed (Whisper requirement)
            if sample_rate != 16000:
                audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=16000)
                sample_rate = 16000
            
            # Normalize audio
            if np.max(np.abs(audio_array)) > 0:
                audio_array = audio_array / np.max(np.abs(audio_array))
            
            return audio_array, sample_rate
            
        except Exception as e:
            logger.error(f"❌ Audio preprocessing failed: {e}")
            raise Exception(f"Audio preprocessing failed: {str(e)}")
    
    def transcribe(self, audio_bytes: bytes, language: str = "en") -> TranscriptionResult:
        """
        Transcribe audio to text with timestamped chunks.
        
        Args:
            audio_bytes: Raw audio bytes
            language: Language code (e.g., 'en', 'es', 'fr')
            
        Returns:
            TranscriptionResult with chunks and metadata
        """
        start_time = time.time()
        
        try:
            logger.info(f"🎵 Starting transcription of {len(audio_bytes)} bytes")
            
            # Preprocess audio
            audio_array, sample_rate = self.preprocess_audio(audio_bytes)
            audio_duration = len(audio_array) / sample_rate
            
            logger.info(f"📊 Audio info: {audio_duration:.2f}s duration, {sample_rate}Hz sample rate")
            
            # Check if chunking is needed
            should_chunk = self._should_chunk_audio(audio_duration, len(audio_bytes))
            
            if should_chunk:
                logger.info(f"✂️ Chunking audio for better processing")
                return self._transcribe_chunked(audio_array, sample_rate, language, start_time)
            else:
                logger.info(f"🔄 Processing audio as single chunk")
                return self._transcribe_single(audio_array, sample_rate, language, start_time)
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Transcription failed: {e}")
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
            
            # Update stats
            self._update_stats(len(audio_array) / sample_rate, processing_time)
            
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
        """Transcribe audio in chunks with parallel processing"""
        try:
            # Segment audio
            chunks = self._segment_audio(audio_array, sample_rate)
            
            # Process chunks (can be parallelized for better performance)
            transcribed_chunks = []
            
            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=min(4, len(chunks))) as executor:
                # Submit all chunk transcription tasks
                future_to_chunk = {
                    executor.submit(self._transcribe_chunk, chunk, language, i): i 
                    for i, chunk in enumerate(chunks)
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_chunk):
                    chunk_index = future_to_chunk[future]
                    try:
                        chunk_result = future.result()
                        transcribed_chunks.append(chunk_result)
                        logger.info(f"✅ Chunk {chunk_index + 1}/{len(chunks)} completed")
                    except Exception as e:
                        logger.error(f"❌ Chunk {chunk_index + 1} failed: {e}")
                        # Add error chunk
                        chunk_data = chunks[chunk_index]
                        error_chunk = TranscriptionChunk(
                            start_time=chunk_data[1],
                            end_time=chunk_data[2],
                            text=f"[Error: {str(e)}]",
                            confidence=0.0,
                            language=language,
                            chunk_index=chunk_index
                        )
                        transcribed_chunks.append(error_chunk)
            
            # Sort chunks by index to maintain order
            transcribed_chunks.sort(key=lambda x: x.chunk_index)
            
            # Combine all text
            full_text = " ".join([chunk.text for chunk in transcribed_chunks])
            
            processing_time = time.time() - start_time
            
            # Update stats
            self._update_stats(len(audio_array) / sample_rate, processing_time)
            
            # Clean up memory
            self._cleanup_memory()
            
            return TranscriptionResult(
                full_text=full_text,
                chunks=transcribed_chunks,
                total_duration=len(audio_array) / sample_rate,
                processing_time=processing_time,
                language=language,
                metadata={
                    'chunked': True,
                    'chunk_count': len(chunks),
                    'chunk_duration': self.chunk_duration,
                    'model_used': self.model_name,
                    'device': self.device,
                    'parallel_processing': True
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Chunked transcription failed: {e}")
            raise
    
    def _update_stats(self, audio_duration: float, processing_time: float):
        """Update processing statistics"""
        self.processing_stats['total_files_processed'] += 1
        self.processing_stats['total_audio_duration'] += audio_duration
        self.processing_stats['total_processing_time'] += processing_time
    
    def _cleanup_memory(self):
        """Clean up memory and perform garbage collection"""
        try:
            # Clear CUDA cache if using GPU
            if self.device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Force garbage collection
            gc.collect()
            
            # Log memory usage
            current_memory = self._get_memory_usage()
            logger.info(f"🧹 Memory cleanup completed. Current usage: {current_memory:.2f}GB")
            
        except Exception as e:
            logger.warning(f"⚠️ Memory cleanup failed: {e}")
    
    def get_timestamped_transcript(self, result: TranscriptionResult, format: str = "youtube") -> str:
        """
        Get transcript in various timestamped formats.
        
        Args:
            result: TranscriptionResult object
            format: Output format ("youtube", "srt", "vtt", "plain")
            
        Returns:
            Formatted transcript string
        """
        if format == "youtube":
            return self._format_youtube_style(result)
        elif format == "srt":
            return self._format_srt(result)
        elif format == "vtt":
            return self._format_vtt(result)
        elif format == "plain":
            return self._format_plain_timestamps(result)
        else:
            logger.warning(f"⚠️ Unknown format '{format}', using YouTube style")
            return self._format_youtube_style(result)
    
    def _format_youtube_style(self, result: TranscriptionResult) -> str:
        """Format transcript in YouTube-style with timestamps"""
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
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        return {
            'total_files_processed': self.processing_stats['total_files_processed'],
            'total_audio_duration': self.processing_stats['total_audio_duration'],
            'total_processing_time': self.processing_stats['total_processing_time'],
            'average_processing_speed': (
                self.processing_stats['total_audio_duration'] / 
                max(self.processing_stats['total_processing_time'], 0.001)
            ),
            'memory_usage_samples': self.processing_stats['memory_usage_samples'][-10:],  # Last 10 samples
            'model_info': {
                'name': self.model_name,
                'device': self.device,
                'chunk_duration': self.chunk_duration,
                'max_memory_gb': self.max_memory_gb
            }
        }
    
    def optimize_for_production(self, target_memory_gb: float = 2.0, target_chunk_duration: float = 15.0):
        """Optimize pipeline settings for production use"""
        self.max_memory_gb = target_memory_gb
        self.max_memory_bytes = target_memory_gb * 1024 * 1024 * 1024
        self.chunk_duration = target_chunk_duration
        
        logger.info(f"⚙️ Pipeline optimized for production:")
        logger.info(f"   Max memory: {target_memory_gb}GB")
        logger.info(f"   Chunk duration: {target_chunk_duration}s")
        
        # Force memory cleanup
        self._cleanup_memory()

# Global instance
transcription_pipeline = TranscriptionPipeline()
