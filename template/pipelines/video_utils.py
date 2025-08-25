#!/usr/bin/env python3
"""
Video processing utilities for extracting audio from video files
"""

import os
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Tuple, Optional
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoProcessor:
    """
    Utility class for processing video files and extracting audio
    """
    
    def __init__(self):
        """Initialize video processor and check dependencies"""
        self.ffmpeg_available = self._check_ffmpeg()
        if not self.ffmpeg_available:
            logger.warning("⚠️ FFmpeg not available - video processing will be limited")
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available in the system"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            if result.returncode == 0:
                logger.info("✅ FFmpeg is available")
                return True
            else:
                logger.warning("⚠️ FFmpeg check failed")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            logger.warning("⚠️ FFmpeg not found in system PATH")
            return False
    
    def extract_audio_from_video(
        self, 
        video_data: bytes, 
        video_filename: str,
        output_format: str = "wav",
        sample_rate: int = 16000
    ) -> Tuple[bytes, str]:
        """
        Extract audio from video file data
        
        Args:
            video_data: Raw video file bytes
            video_filename: Original video filename
            output_format: Audio output format (wav, mp3, etc.)
            sample_rate: Target audio sample rate
            
        Returns:
            Tuple of (audio_bytes, temp_audio_path)
        """
        if not self.ffmpeg_available:
            raise Exception("FFmpeg not available for video processing")
        
        # Create temporary files
        temp_video = None
        temp_audio = None
        
        try:
            # Create temporary video file
            temp_video = tempfile.NamedTemporaryFile(
                suffix=f".{video_filename.split('.')[-1]}", 
                delete=False
            )
            temp_video.write(video_data)
            temp_video.close()
            
            # Create temporary audio file
            temp_audio = tempfile.NamedTemporaryFile(
                suffix=f".{output_format}", 
                delete=False
            )
            temp_audio.close()
            
            logger.info(f"🎬 Processing video: {video_filename}")
            logger.info(f"   Video size: {len(video_data)} bytes")
            logger.info(f"   Temp video: {temp_video.name}")
            logger.info(f"   Temp audio: {temp_audio.name}")
            
            # Extract audio using FFmpeg
            cmd = [
                'ffmpeg',
                '-i', temp_video.name,  # Input video
                '-vn',                   # No video
                '-acodec', 'pcm_s16le', # PCM 16-bit audio codec
                '-ar', str(sample_rate), # Sample rate
                '-ac', '1',              # Mono audio
                '-y',                    # Overwrite output
                temp_audio.name          # Output audio file
            ]
            
            logger.info(f"🔧 Running FFmpeg command: {' '.join(cmd)}")
            
            # Execute FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"❌ FFmpeg failed: {result.stderr}")
                raise Exception(f"FFmpeg extraction failed: {result.stderr}")
            
            # Read extracted audio
            with open(temp_audio.name, 'rb') as f:
                audio_bytes = f.read()
            
            logger.info(f"✅ Audio extraction successful: {len(audio_bytes)} bytes")
            
            return audio_bytes, temp_audio.name
            
        except Exception as e:
            logger.error(f"❌ Error extracting audio: {e}")
            raise
        finally:
            # Clean up temporary files
            try:
                if temp_video and os.path.exists(temp_video.name):
                    os.unlink(temp_video.name)
                    logger.debug(f"🧹 Cleaned up temp video: {temp_video.name}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to clean up temp video: {e}")
            
            try:
                if temp_audio and os.path.exists(temp_audio.name):
                    os.unlink(temp_audio.name)
                    logger.debug(f"🧹 Cleaned up temp audio: {temp_audio.name}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to clean up temp audio: {e}")
    
    def get_video_info(self, video_data: bytes, video_filename: str) -> dict:
        """
        Get basic information about the video file
        
        Args:
            video_data: Raw video file bytes
            video_filename: Original video filename
            
        Returns:
            Dictionary with video information
        """
        if not self.ffmpeg_available:
            return {
                "filename": video_filename,
                "size_bytes": len(video_data),
                "size_mb": len(video_data) / (1024 * 1024),
                "ffmpeg_available": False
            }
        
        # Create temporary video file for analysis
        temp_video = None
        try:
            temp_video = tempfile.NamedTemporaryFile(
                suffix=f".{video_filename.split('.')[-1]}", 
                delete=False
            )
            temp_video.write(video_data)
            temp_video.close()
            
            # Get video information using FFmpeg
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                temp_video.name
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                
                # Extract relevant information
                format_info = info.get('format', {})
                video_stream = next(
                    (s for s in info.get('streams', []) if s.get('codec_type') == 'video'), 
                    {}
                )
                audio_stream = next(
                    (s for s in info.get('streams', []) if s.get('codec_type') == 'audio'), 
                    {}
                )
                
                return {
                    "filename": video_filename,
                    "size_bytes": len(video_data),
                    "size_mb": len(video_data) / (1024 * 1024),
                    "duration": float(format_info.get('duration', 0)),
                    "format": format_info.get('format_name', 'unknown'),
                    "video_codec": video_stream.get('codec_name', 'unknown'),
                    "video_resolution": f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}",
                    "audio_codec": audio_stream.get('codec_name', 'unknown'),
                    "audio_channels": audio_stream.get('channels', 0),
                    "audio_sample_rate": audio_stream.get('sample_rate', 0),
                    "ffmpeg_available": True
                }
            else:
                logger.warning(f"⚠️ FFprobe failed: {result.stderr}")
                return {
                    "filename": video_filename,
                    "size_bytes": len(video_data),
                    "size_mb": len(video_data) / (1024 * 1024),
                    "ffmpeg_available": True,
                    "error": "Failed to extract video info"
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting video info: {e}")
            return {
                "filename": video_filename,
                "size_bytes": len(video_data),
                "size_mb": len(video_data) / (1024 * 1024),
                "ffmpeg_available": True,
                "error": str(e)
            }
        finally:
            # Clean up temporary file
            try:
                if temp_video and os.path.exists(temp_video.name):
                    os.unlink(temp_video.name)
            except Exception as e:
                logger.warning(f"⚠️ Failed to clean up temp video: {e}")
    
    def is_video_file(self, filename: str) -> bool:
        """Check if file is a video file based on extension"""
        video_extensions = {
            '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', 
            '.webm', '.m4v', '.3gp', '.ogv', '.ts', '.mts'
        }
        return Path(filename).suffix.lower() in video_extensions
    
    def get_supported_formats(self) -> list:
        """Get list of supported video formats"""
        if not self.ffmpeg_available:
            return []
        
        return [
            'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 
            'webm', 'm4v', '3gp', 'ogv', 'ts', 'mts'
        ]

# Global instance
video_processor = VideoProcessor()
