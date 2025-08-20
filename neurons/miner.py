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

import time
import typing
import bittensor as bt

# Bittensor Miner Template:
import template
from template.protocol import AudioTask

# import base miner class which takes care of most of the boilerplate
from template.base.miner import BaseMinerNeuron

# Import pipelines with availability checks
from template.pipelines import TranscriptionPipeline, TTS_AVAILABLE, SUMMARIZATION_AVAILABLE

# Conditional imports for optional pipelines
if TTS_AVAILABLE:
    from template.pipelines import TTSPipeline
if SUMMARIZATION_AVAILABLE:
    from template.pipelines import SummarizationPipeline


class Miner(BaseMinerNeuron):
    """
    Audio processing miner that handles transcription, TTS, and summarization tasks.
    This miner provides high-speed, accurate audio processing services using state-of-the-art models.
    """

    def __init__(self, config=None):
        super(Miner, self).__init__(config=config)

        # Initialize pipelines
        bt.logging.info("Initializing audio processing pipelines...")
        
        # Transcription pipeline (always available)
        self.transcription_pipeline = TranscriptionPipeline("openai/whisper-tiny")
        bt.logging.info("✅ Transcription pipeline initialized")
        
        # TTS pipeline (conditional)
        if TTS_AVAILABLE:
            self.tts_pipeline = TTSPipeline("tts_models/en/ljspeech/tacotron2-DDC")
            bt.logging.info("✅ TTS pipeline initialized")
        else:
            self.tts_pipeline = None
            bt.logging.warning("⚠️  TTS pipeline not available (TTS package not installed)")
        
        # Summarization pipeline (conditional)
        if SUMMARIZATION_AVAILABLE:
            self.summarization_pipeline = SummarizationPipeline("facebook/bart-large-cnn")
            bt.logging.info("✅ Summarization pipeline initialized")
        else:
            self.summarization_pipeline = None
            bt.logging.warning("⚠️  Summarization pipeline not available (transformers package not installed)")
        
        bt.logging.info("Audio processing pipelines initialization complete!")

    async def forward(
        self, synapse: template.protocol.AudioTask
    ) -> template.protocol.AudioTask:
        """
        Process audio tasks including transcription, TTS, and summarization.

        Args:
            synapse (template.protocol.AudioTask): The synapse object containing the task details.

        Returns:
            template.protocol.AudioTask: The synapse object with the processed results.
        """
        bt.logging.info("🚨 FORWARD FUNCTION CALLED! 🚨")
        bt.logging.info(f"🎯 Processing {synapse.task_type} task...")
        start_time = time.time()
        
        try:
            # Route to appropriate pipeline based on task type
            if synapse.task_type == "transcription":
                if self.transcription_pipeline is None:
                    raise Exception("Transcription pipeline not available")
                
                bt.logging.info("📝 Starting transcription...")
                
                # Decode audio data
                audio_bytes = synapse.decode_audio(synapse.input_data)
                bt.logging.info(f"🎵 Decoded audio data: {len(audio_bytes)} bytes")
                
                # Process transcription
                transcribed_text, processing_time = self.transcription_pipeline.transcribe(
                    audio_bytes, synapse.language
                )
                
                # Encode output
                synapse.output_data = synapse.encode_text(transcribed_text)
                synapse.processing_time = processing_time
                synapse.pipeline_model = self.transcription_pipeline.model_name
                
                bt.logging.info(f"✅ Transcription completed in {processing_time:.2f}s")
                bt.logging.info(f"📝 Output: {transcribed_text[:100]}...")
                
            elif synapse.task_type == "tts":
                if self.tts_pipeline is None:
                    raise Exception("TTS pipeline not available")
                
                bt.logging.info("🎤 Starting text-to-speech...")
                
                # Decode text data
                text = synapse.decode_text(synapse.input_data)
                bt.logging.info(f"📝 Input text: {text[:100]}...")
                
                # Process TTS
                audio_bytes, processing_time = self.tts_pipeline.synthesize(
                    text, synapse.language
                )
                
                # Encode output
                synapse.output_data = synapse.encode_audio(audio_bytes)
                synapse.processing_time = processing_time
                synapse.pipeline_model = self.tts_pipeline.model_name
                
                bt.logging.info(f"✅ TTS completed in {processing_time:.2f}s")
                bt.logging.info(f"🎵 Output audio: {len(audio_bytes)} bytes")
                
            elif synapse.task_type == "summarization":
                if self.summarization_pipeline is None:
                    raise Exception("Summarization pipeline not available")
                
                bt.logging.info("📋 Starting summarization...")
                
                # Decode text data
                text = synapse.decode_text(synapse.input_data)
                bt.logging.info(f"📝 Input text: {text[:100]}...")
                
                # Process summarization
                summary_text, processing_time = self.summarization_pipeline.summarize(
                    text, language=synapse.language
                )
                
                # Encode output
                synapse.output_data = synapse.encode_text(summary_text)
                synapse.processing_time = processing_time
                synapse.pipeline_model = self.summarization_pipeline.model_name
                
                bt.logging.info(f"✅ Summarization completed in {processing_time:.2f}s")
                bt.logging.info(f"📝 Summary: {summary_text[:100]}...")
                
            else:
                raise Exception(f"Unknown task type: {synapse.task_type}")
            
            total_time = time.time() - start_time
            bt.logging.info(f"🎉 Task completed successfully! Total time: {total_time:.2f}s")
            
        except Exception as e:
            total_time = time.time() - start_time
            synapse.error_message = str(e)
            synapse.processing_time = total_time
            synapse.output_data = None
            synapse.pipeline_model = "error"
            
            bt.logging.error(f"❌ Error processing {synapse.task_type} task: {str(e)}")
            bt.logging.error(f"⏱️  Failed after {total_time:.2f}s")
        
        return synapse

    async     def blacklist(
        self, synapse: template.protocol.AudioTask
    ) -> typing.Tuple[bool, str]:
        """
        Determines whether an incoming request should be blacklisted.
        Currently allows all connections for testing purposes.

        Args:
            synapse (template.protocol.AudioTask): A synapse object constructed from the headers of the incoming request.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating whether the synapse's hotkey is blacklisted,
                            and a string providing the reason for the decision.
        """
        # Allow all connections for testing
        bt.logging.info(f"Allowing request from hotkey {synapse.dendrite.hotkey if synapse.dendrite else 'Unknown'}")
        return False, "Allowed for testing."

    async def priority(
        self, synapse: template.protocol.AudioTask
    ) -> float:
        """
        Determines the priority of the incoming request.
        Currently returns a default priority for testing.

        Args:
            synapse (template.protocol.AudioTask): A synapse object constructed from the headers of the incoming request.

        Returns:
            float: Priority score (default 1.0 for testing)
        """
        # Return default priority for testing
        return 1.0

    async def verify(
        self, synapse: template.protocol.AudioTask
    ) -> typing.Tuple[bool, str]:
        """
        Verifies the synapse data.
        
        Args:
            synapse (template.protocol.AudioTask): A synapse object containing the data to verify.
            
        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating whether the synapse data is valid,
                            and a string providing the reason for the decision.
        """
        if synapse.task_type not in ["transcription", "tts", "summarization"]:
            return False, f"Invalid task type: {synapse.task_type}"

        if not synapse.input_data:
            return False, "No input data provided"

        if not synapse.language:
            return False, "No language specified"

        return True, "Synapse data is valid"


# This is the main function, which runs the miner.
if __name__ == "__main__":
    with Miner() as miner:
        while True:
            bt.logging.info(f"Miner running... {time.time()}")
            time.sleep(5)
