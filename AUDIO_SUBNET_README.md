# Audio Processing Bittensor Subnet

A high-performance Bittensor subnet for audio transcription, text-to-speech (TTS), and text summarization services. This subnet rewards miners based on speed, accuracy, and stake, prioritizing the top 5 performers.

## 🎯 Features

### Multi-Service Support
- **Audio Transcription**: Convert speech to text using Whisper models
- **Text-to-Speech (TTS)**: Convert text to speech using Coqui TTS
- **Text Summarization**: Summarize long text using BART models

### Performance Optimization
- **Speed-First Design**: Uses lightweight models (Whisper tiny) for fast processing
- **Multi-Language Support**: Supports 10+ languages including English, Spanish, French, German, etc.
- **Stake-Based Rewards**: Miners with higher stake receive priority and better rewards

### Evaluation Criteria
- **Speed (40%)**: Exponential decay based on processing time
- **Accuracy (40%)**: Task-specific evaluation metrics
- **Stake (20%)**: Normalized stake-based scoring

## 🏗️ Architecture

### Protocol (`template/protocol.py`)
```python
class AudioTask(bt.Synapse):
    task_type: TaskType  # TRANSCRIPTION, TTS, or SUMMARIZATION
    input_data: str      # Base64 encoded input
    language: str        # Language code (e.g., 'en', 'es', 'fr')
    output_data: str     # Base64 encoded output
    processing_time: float
    model_name: str
    error_message: str
```

### Pipelines

#### 1. Transcription Pipeline (`template/pipelines/transcription_pipeline.py`)
- **Model**: Whisper Tiny (fast, efficient)
- **Input**: Audio bytes
- **Output**: Transcribed text
- **Languages**: 10+ supported languages

#### 2. TTS Pipeline (`template/pipelines/tts_pipeline.py`)
- **Model**: Coqui TTS (Tacotron2-DDC)
- **Input**: Text
- **Output**: Audio bytess
- **Features**: Multi-speaker support

#### 3. Summarization Pipeline (`template/pipelines/summarization_pipeline.py`)
- **Model**: BART Large CNN
- **Input**: Long text
- **Output**: Summarized text
- **Quality**: High-quality summaries with key concept preservation

## 🚀 Quick Start

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Test transcription pipeline
python test_transcription.py
```

### Running a Miner
```bash
# Run miner with default configuration
python neurons/miner.py

# Run miner with custom config
python neurons/miner.py --config path/to/config.yaml
```

### Running a Validator
```bash
# Run validator
python neurons/validator.py

# Run validator with custom config
python neurons/validator.py --config path/to/config.yaml
```

## 📊 Evaluation Metrics

### Speed Scoring
```python
speed_score = exp(-processing_time / max_acceptable_time)
```
- Exponential decay: faster = higher score
- Default max acceptable time: 10 seconds

### Accuracy Scoring

#### Transcription
- **Metric**: Sequence similarity using difflib
- **Range**: 0.0 to 1.0
- **Formula**: `SequenceMatcher(actual, expected).ratio()`

#### Summarization
- **Metric**: Word overlap + length appropriateness
- **Range**: 0.0 to 1.0
- **Formula**: `(overlap_score * 0.7) + (length_score * 0.3)`

#### TTS
- **Metric**: Audio quality analysis (placeholder)
- **Range**: 0.0 to 1.0
- **Note**: Requires audio processing libraries for full evaluation

### Stake Scoring
```python
stake_score = min(1.0, stake / max_stake)
```
- Normalized by maximum stake in network
- Higher stake = higher priority and rewards

## 🔧 Configuration

### Miner Configuration
```yaml
neuron:
  sample_size: 5  # Number of miners to query
  min_stake: 1000  # Minimum stake required
  
# Model configurations
transcription_model: "openai/whisper-tiny"
tts_model: "tts_models/en/ljspeech/tacotron2-DDC"
summarization_model: "facebook/bart-large-cnn"
```

### Validator Configuration
```yaml
neuron:
  sample_size: 5  # Top 5 miners
  max_acceptable_time: 10.0  # Maximum processing time
  
# Reward weights
speed_weight: 0.4
accuracy_weight: 0.4
stake_weight: 0.2
```

## 🧪 Testing

### Test Transcription Pipeline
```bash
python test_transcription.py
```

### Expected Output
```
🎵 Testing Audio Transcription Pipeline
==================================================
Initializing transcription pipeline...
Creating test audio...
Testing transcription...
✅ Transcription successful!
📝 Transcribed text: '[transcribed text]'
⏱️  Processing time: 1.23s
⏱️  Total time (including model loading): 5.67s
🔧 Model used: openai/whisper-tiny

🎉 All tests passed! The transcription pipeline is working correctly.
```

## 📈 Performance Benchmarks

### Whisper Tiny Model
- **Model Size**: ~39MB
- **Processing Speed**: ~1-3 seconds for 30-second audio
- **Accuracy**: ~90%+ on clear speech
- **Memory Usage**: ~2GB RAM

### TTS Model (Tacotron2-DDC)
- **Model Size**: ~50MB
- **Processing Speed**: ~2-5 seconds for 100 words
- **Quality**: High-quality speech synthesis
- **Memory Usage**: ~3GB RAM

### BART Large CNN
- **Model Size**: ~400MB
- **Processing Speed**: ~1-2 seconds for 500 words
- **Quality**: High-quality summaries
- **Memory Usage**: ~4GB RAM

## 🌍 Supported Languages

| Language | Code | Transcription | TTS | Summarization |
|----------|------|---------------|-----|---------------|
| English  | en   | ✅            | ✅  | ✅            |
| Spanish  | es   | ✅            | ✅  | ✅            |
| French   | fr   | ✅            | ✅  | ✅            |
| German   | de   | ✅            | ✅  | ✅            |
| Italian  | it   | ✅            | ✅  | ✅            |
| Portuguese| pt  | ✅            | ✅  | ✅            |
| Russian  | ru   | ✅            | ✅  | ✅            |
| Japanese | ja   | ✅            | ✅  | ✅            |
| Korean   | ko   | ✅            | ✅  | ✅            |
| Chinese  | zh   | ✅            | ✅  | ✅            |

## 🔒 Security Features

### Miner Security
- **Blacklisting**: Rejects unregistered or non-validator hotkeys
- **Stake Verification**: Requires minimum stake for processing
- **Input Validation**: Validates task type and input data

### Validator Security
- **Response Validation**: Validates miner responses
- **Error Handling**: Graceful handling of failed responses
- **Stake-Based Prioritization**: Higher stake miners get priority

## 🚀 Deployment

### Local Development
```bash
# Clone repository
git clone <repository-url>
cd bittensor-subnet-template

# Install dependencies
pip install -r requirements.txt

# Test pipelines
python test_transcription.py

# Run miner/validator
python neurons/miner.py
python neurons/validator.py
```

### Production Deployment
```bash
# Install with GPU support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Run with production config
python neurons/miner.py --config production_config.yaml
```

## 📝 API Usage

### Client Example
```python
import bittensor as bt
from template.protocol import AudioTask, TaskType

# Create wallet and dendrite
wallet = bt.wallet()
dendrite = bt.dendrite(wallet=wallet)

# Create audio task
task = AudioTask(
    task_type=TaskType.TRANSCRIPTION,
    input_data=audio_base64,
    language="en"
)

# Query miner
response = await dendrite.query(axons=[miner_axon], synapse=task)
result = response.deserialize()
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Discord**: Join the Bittensor Discord for community support
- **Issues**: Report bugs and feature requests on GitHub
- **Documentation**: Check the main README.md for detailed setup instructions
