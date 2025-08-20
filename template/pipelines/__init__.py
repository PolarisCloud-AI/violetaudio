# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

# Import transcription pipeline (always available)
from .transcription_pipeline import TranscriptionPipeline

# Import TTS pipeline if available
try:
    from .tts_pipeline import TTSPipeline
    TTS_AVAILABLE = True
except ImportError:
    TTSPipeline = None
    TTS_AVAILABLE = False

# Import summarization pipeline if available
try:
    from .summarization_pipeline import SummarizationPipeline
    SUMMARIZATION_AVAILABLE = True
except ImportError:
    SummarizationPipeline = None
    SUMMARIZATION_AVAILABLE = False

__all__ = [
    "TranscriptionPipeline",
    "TTSPipeline", 
    "SummarizationPipeline",
    "TTS_AVAILABLE",
    "SUMMARIZATION_AVAILABLE"
]
