# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import typing
import bittensor as bt
from enum import Enum
import base64


class TaskType(Enum):
    TRANSCRIPTION = "transcription"
    TTS = "tts"
    SUMMARIZATION = "summarization"


class AudioTask(bt.Synapse):
    """
    Protocol for audio transcription, TTS, and text summarization tasks.

    Attributes:
    - task_type: Type of task (transcription, tts, summarization)
    - input_data: Input data (audio bytes for transcription, text for TTS/summarization)
    - language: Language code (e.g., 'en', 'es', 'fr')
    - output_data: Output data (transcribed text, audio bytes, summary)
    - processing_time: Time taken to process the task
    - model_name: Name of the model used for processing
    """

    # Required request inputs
    task_type: str = "transcription"  # Changed from TaskType enum to str
    input_data: str  # Base64 encoded data
    language: str = "en"
    
    # Optional request outputs
    output_data: typing.Optional[str] = None  # Base64 encoded output
    processing_time: typing.Optional[float] = None
    pipeline_model: typing.Optional[str] = None  # Changed from model_name to avoid Pydantic conflict
    error_message: typing.Optional[str] = None

    def deserialize(self) -> dict:
        """
        Deserialize the response data.

        Returns:
        - dict: Dictionary containing output_data, processing_time, pipeline_model, and error_message
        """
        return {
            "output_data": self.output_data,
            "processing_time": self.processing_time,
            "pipeline_model": self.pipeline_model,
            "error_message": self.error_message
        }

    def encode_audio(self, audio_bytes: bytes) -> str:
        """Encode audio bytes to base64 string."""
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    def decode_audio(self, audio_b64: str) -> bytes:
        """Decode base64 string to audio bytes."""
        return base64.b64decode(audio_b64.encode('utf-8'))
    
    def encode_text(self, text: str) -> str:
        """Encode text to base64 string."""
        return base64.b64encode(text.encode('utf-8')).decode('utf-8')
    
    def decode_text(self, text_b64: str) -> str:
        """Decode base64 string to text."""
        return base64.b64decode(text_b64.encode('utf-8')).decode('utf-8')
