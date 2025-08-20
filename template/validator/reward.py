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

import numpy as np
from typing import List, Dict, Any
import bittensor as bt
from difflib import SequenceMatcher
import time

from template.protocol import AudioTask


def calculate_speed_score(processing_time: float, max_acceptable_time: float = 10.0) -> float:
    """
    Calculate speed score based on processing time.
    
    Args:
        processing_time: Time taken to process the task
        max_acceptable_time: Maximum acceptable time (default 10 seconds)
        
    Returns:
        Speed score between 0 and 1
    """
    if processing_time <= 0:
        return 0.0
    
    # Exponential decay: faster = higher score
    speed_score = np.exp(-processing_time / max_acceptable_time)
    return min(1.0, max(0.0, speed_score))


def calculate_accuracy_score(response_text: str, expected_output: str, task_type: str) -> float:
    """
    Calculate accuracy score based on task type.
    
    Args:
        response_text: Miner's response text
        expected_output: Expected output text
        task_type: Type of task performed
        
    Returns:
        Accuracy score between 0 and 1
    """
    if not response_text or not expected_output:
        return 0.0
    
    if task_type == "transcription":
        # Use sequence similarity for transcription
        from difflib import SequenceMatcher
        return SequenceMatcher(None, response_text.lower(), expected_output.lower()).ratio()
    
    elif task_type == "summarization":
        # Use word overlap and length appropriateness for summarization
        response_words = set(response_text.lower().split())
        expected_words = set(expected_output.lower().split())
        
        # Word overlap score
        if expected_words:
            overlap_score = len(response_words.intersection(expected_words)) / len(expected_words)
        else:
            overlap_score = 0.0
        
        # Length appropriateness score (summary should be shorter than original)
        length_ratio = len(response_text) / len(expected_output) if len(expected_output) > 0 else 1.0
        length_score = max(0, 1 - abs(length_ratio - 0.3))  # Ideal ratio around 0.3
        
        # Combined score
        return (overlap_score * 0.7) + (length_score * 0.3)
    
    elif task_type == "tts":
        # For TTS, we'd need audio quality analysis
        # For now, return a placeholder score
        return 0.8  # Placeholder score
    
    else:
        return 0.0


def calculate_stake_score(stake: float, max_stake: float) -> float:
    """
    Calculate stake-based score.
    
    Args:
        stake: Miner's stake
        max_stake: Maximum stake in the network
        
    Returns:
        Stake score between 0 and 1
    """
    if max_stake <= 0:
        return 0.0
    
    # Normalize stake score
    stake_score = min(1.0, stake / max_stake)
    return stake_score


def reward(
    response: Dict[str, Any],
    expected_output: str,
    task_type: str,
    processing_time: float,
    stake: float,
    max_stake: float,
    max_acceptable_time: float = 10.0
) -> float:
    """
    Calculate comprehensive reward for a miner response.
    
    Args:
        response: Miner's response dictionary
        expected_output: Expected output for the task
        task_type: Type of task performed
        processing_time: Time taken to process
        stake: Miner's stake
        max_stake: Maximum stake in network
        max_acceptable_time: Maximum acceptable processing time
        
    Returns:
        Reward score between 0 and 1
    """
    # Check for errors
    if response.get("error_message"):
        bt.logging.warning(f"Miner returned error: {response['error_message']}")
        return 0.0
    
    # Extract response data
    output_data = response.get("output_data")
    if not output_data:
        bt.logging.warning("Miner returned no output data")
        return 0.0
    
    # Decode response based on task type
    if task_type in ["transcription", "summarization"]:
        try:
            response_text = AudioTask.decode_text(output_data)
        except Exception as e:
            bt.logging.warning(f"Failed to decode text response: {e}")
            return 0.0
    else:  # TTS
        response_text = output_data  # Keep as base64 for audio
    
    # Calculate individual scores
    speed_score = calculate_speed_score(processing_time, max_acceptable_time)
    accuracy_score = calculate_accuracy_score(response_text, expected_output, task_type)
    stake_score = calculate_stake_score(stake, max_stake)
    
    # Weighted combination of scores
    # Speed: 40%, Accuracy: 40%, Stake: 20%
    final_score = (
        speed_score * 0.4 +
        accuracy_score * 0.4 +
        stake_score * 0.2
    )
    
    bt.logging.info(
        f"Reward breakdown - Speed: {speed_score:.3f}, "
        f"Accuracy: {accuracy_score:.3f}, "
        f"Stake: {stake_score:.3f}, "
        f"Final: {final_score:.3f}"
    )
    
    return final_score


def get_rewards(
    self,
    task_type: str,
    query: str,
    responses: List[Dict[str, Any]],
    expected_output: str,
    miner_uids: List[int],
    max_acceptable_time: float = 10.0
) -> np.ndarray:
    """
    Calculate rewards for all miner responses.
    
    Args:
        self: Validator instance
        task_type: Type of task performed
        query: Original query sent to miners
        responses: List of responses from miners
        expected_output: Expected output for the task
        miner_uids: List of miner UIDs
        max_acceptable_time: Maximum acceptable processing time
        
    Returns:
        Array of reward scores
    """
    rewards = []
    max_stake = float(self.metagraph.S.max()) if len(self.metagraph.S) > 0 else 1.0
    
    for i, response in enumerate(responses):
        if i >= len(miner_uids):
            break
            
        uid = miner_uids[i]
        stake = float(self.metagraph.S[uid])
        processing_time = response.get("processing_time", 0.0)
        
        # Calculate reward for this miner
        miner_reward = reward(
            response=response,
            expected_output=expected_output,
            task_type=task_type,
            processing_time=processing_time,
            stake=stake,
            max_stake=max_stake,
            max_acceptable_time=max_acceptable_time
        )
        
        rewards.append(miner_reward)
    
    # Ensure we have rewards for all miners
    while len(rewards) < len(miner_uids):
        rewards.append(0.0)
    
    return np.array(rewards)


def run_validator_pipeline(task_type: str, input_data: str, language: str = "en") -> tuple:
    """
    Run the same pipeline locally to get expected output for comparison.
    
    Args:
        task_type: Type of task to run
        input_data: Input data (base64 encoded)
        language: Language code
        
    Returns:
        Tuple of (output_data, processing_time, model_name)
    """
    try:
        # Create a dummy AudioTask for decoding
        dummy_task = AudioTask(input_data="dummy", task_type=task_type, language=language)
        
        if task_type == "transcription":
            from template.pipelines.transcription_pipeline import TranscriptionPipeline
            
            # Decode audio data
            audio_bytes = dummy_task.decode_audio(input_data)
            
            # Run transcription pipeline
            pipeline = TranscriptionPipeline("openai/whisper-tiny")
            output_text, processing_time = pipeline.transcribe(audio_bytes, language)
            
            # Encode output
            output_data = dummy_task.encode_text(output_text)
            return output_data, processing_time, pipeline.model_name
            
        elif task_type == "summarization":
            from template.pipelines.summarization_pipeline import SummarizationPipeline
            
            # Decode text data
            text = dummy_task.decode_text(input_data)
            
            # Run summarization pipeline
            pipeline = SummarizationPipeline("facebook/bart-large-cnn")
            output_text, processing_time = pipeline.summarize(text, language=language)
            
            # Encode output
            output_data = dummy_task.encode_text(output_text)
            return output_data, processing_time, pipeline.model_name
            
        elif task_type == "tts":
            # For TTS, we'll use a placeholder since it requires audio comparison
            return "audio_output_placeholder", 1.0, "tts_placeholder_model"
            
        else:
            return None, 0.0, "unknown_model"
            
    except Exception as e:
        bt.logging.error(f"Error running validator pipeline for {task_type}: {str(e)}")
        return None, 0.0, "error_model"
