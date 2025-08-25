<div align="center">

# **🎵 Bittensor Audio Processing Subnet** <!-- omit in toc -->
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.gg/bittensor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 

---
## The Incentivized Internet <!-- omit in toc -->

[Discord](https://discord.gg/bittensor) • [Network](https://taostats.io/) • [Research](https://bittensor.com/whitepaper)
</div>

---

## 📋 Table of Contents
- [🎯 What This Subnet Does](#-what-this-subnet-does)
- [🏗️ System Architecture](#️-system-architecture)
- [🚀 Quick Start](#-quick-start)
- [🔧 How to Run Each Component](#-how-to-run-each-component)
- [📊 Performance & Requirements](#-performance--requirements)
- [🌐 Network Configuration](#-network-configuration)
- [🧪 Testing & Validation](#-testing--validation)
- [📚 Available Documentation](#-available-documentation)
- [🔑 Key Features](#-key-features)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## 🎯 What This Subnet Does

This is a **production-ready Audio Processing Subnet** that provides:

- **🎵 Audio Transcription**: Convert speech to text using Whisper models
- **🔊 Text-to-Speech (TTS)**: Convert text to speech using Coqui TTS  
- **📝 Text Summarization**: Summarize long text using BART models
- **🌍 Multi-language Support**: 10+ languages (English, Spanish, French, German, etc.)
- **🎬 Video Transcription**: Extract audio and transcribe video content
- **🔤 Machine Translation**: Translate text between multiple languages
- **📹 Video Processing**: Handle video files with audio extraction
- **🎙️ Audio Enhancement**: Improve audio quality and processing

### **Key Features:**
- **Speed-Optimized Evaluation**: 40% speed, 40% accuracy, 20% stake
- **Top 5 Miner Prioritization**: Rewards best-performing miners
- **Real-time Task Management**: Proxy server orchestration
- **Broken File Handling**: Graceful error handling for corrupted files
- **Comprehensive Logging**: Detailed performance tracking and debugging

---

## 🏗️ System Architecture

```
User Request → Proxy Server → Task Queue → Validator → Miners → Response → User
     ↓              ↓           ↓         ↓         ↓         ↓
File Upload → Database → Firestore → Processing → Evaluation → Final Results
```

### **Component Structure:**
- **Proxy Server** (Port 8000): Task management, file storage, miner coordination
- **Miner** (Port 8091): Process audio/text tasks using AI pipelines
- **Validator** (Port 8092): Evaluate responses, set weights, coordinate tasks

---

## 🚀 Quick Start

```bash
# Start all components at once
./start_complete_system.sh

# Run complete workflow test
python test_complete_workflow.py

# Stop all components
./stop_complete_system.sh
```

---

## 🔧 How to Run Each Component

### **1. 🖥️ Proxy Server**
```bash
cd proxy_server
python enhanced_main.py
# OR
./start_enhanced_server.sh
```

**Purpose**: Task management, file storage, miner coordination
**Port**: 8000
**Features**: 
- Real-time monitoring and load balancing
- Database integration with Firestore
- File management with Google Cloud Storage
- Comprehensive API endpoints

### **2. ⛏️ Miner**
```bash
python neurons/miner.py \
  --netuid 49 \
  --subtensor.network finney \
  --wallet.name wallet_name \
  --wallet.hotkey hotkey \
  --logging.debug \
  --axon.ip 0.0.0.0 \
  --axon.port 8091 \
  --axon.external_ip YOUR_IP \
  --axon.external_port 8091
```

**Purpose**: Process audio/text tasks using AI pipelines
**Port**: 8091 (default)
**Features**:
- Automatic proxy server integration
- Broken file handling and validation
- Comprehensive logging and metrics
- Support for transcription, TTS, and summarization

### **3. ✅ Validator**
```bash


# With proxy integration
python neurons/validator.py \
  --netuid 49 \
  --subtensor.network finney \
  --wallet.name wallet_name \
  --wallet.hotkey hotkey \
  --logging.debug \
  --axon.ip 0.0.0.0 \
  --axon.port 8092 \
  --axon.external_ip YOUR_IP \
  --axon.external_port 8092 \
 
```

**Purpose**: Evaluate miner responses, set weights, coordinate tasks
**Port**: 8092 (default)
**Features**:
- Proxy server integration
- Performance scoring and reward calculation
- Top 10 miner selection per task
- Comprehensive evaluation metrics

---

## 📊 Performance & Requirements

### **System Requirements**
- **Python**: 3.8+
- **Network**: Stable internet connection

### **Validator Requirements**
- **GPU**: Required (for model evaluation and processing)
- **RAM**: 12GB+ (for AI models and validation)
- **Storage**: 100GB+ (for models, files, and database)

### **Miner Requirements**
- **GPU**: Required (for AI model inference)
- **RAM**: 12GB+ (for AI models and processing)
- **VRAM**: 12GB+ (for GPU model loading)
- **Storage**: 100GB+ (for models and temporary files)

### **Model Performance**
- **Whisper Tiny**: ~1-3 seconds for 30-second audio
- **TTS (Tacotron2-DDC)**: ~2-5 seconds for 100 words
- **BART Large CNN**: ~1-2 seconds for 500 words
- **Video Processing**: ~5-15 seconds for 1-minute video
- **Machine Translation**: ~2-4 seconds for 100 words
- **Audio Enhancement**: ~3-6 seconds for 30-second audio

### **Supported Languages & Services**
| Language | Code | Transcription | TTS | Summarization | Translation | Video Processing |
|----------|------|---------------|-----|---------------|-------------|------------------|
| English  | en   | ✅            | ✅  | ✅            | ✅          | ✅               |
| Spanish  | es   | ✅            | ✅  | ✅            | ✅          | ✅               |
| French   | fr   | ✅            | ✅  | ✅            | ✅          | ✅               |
| German   | de   | ✅            | ✅  | ✅            | ✅          | ✅               |
| Italian  | it   | ✅            | ✅  | ✅            | ✅          | ✅               |
| Portuguese| pt  | ✅            | ✅  | ✅            | ✅          | ✅               |
| Russian  | ru   | ✅            | ✅  | ✅            | ✅          | ✅               |
| Japanese | ja   | ✅            | ✅  | ✅            | ✅          | ✅               |
| Korean   | ko   | ✅            | ✅  | ✅            | ✅          | ✅               |
| Chinese  | zh   | ✅            | ✅  | ✅            | ✅          | ✅               |

---

## 🌐 Network Configuration

### **Local Development (Staging)**
```bash
# Network: local (staging)
# NetUID: Any available number
# Ports: 8000 (proxy), 8091 (miner), 8092 (validator)

# Follow detailed setup in:
./docs/running_on_staging.md
```

### **Testnet/Mainnet**
```bash
# Network: test or finney
# NetUID: 49 (or your subnet number)
# External IP: Your public IP address

# Follow detailed setup in:
./docs/running_on_testnet.md
./docs/running_on_mainnet.md
```

---

## 🧪 Testing & Validation

### **Test Individual Components**
```bash
# Test transcription pipeline
python test_transcription.py

# Test proxy server
cd proxy_server
python -m pytest tests/ -v

# Test complete workflow
python test_complete_workflow.py
```

### **Monitor System Health**
```bash
# Check proxy server
curl http://localhost:8000/api/v1/health

# Check validator integration
curl http://localhost:8000/api/v1/validator/integration

# View logs
tail -f logs/proxy_server.log
tail -f logs/miner.log
tail -f logs/validator.log
```

### **Expected Test Results**
```
✅ PROXY_HEALTH: Server healthy - healthy
✅ VALIDATOR_INTEGRATION: Integration successful
✅ TASK_SUBMISSION: 3/3 tasks submitted
✅ TASK_DISTRIBUTION: Tasks distributed successfully
✅ TASK_MONITORING: All tasks completed!
✅ FINAL_RESULTS: Success Rate: 100%
```

---

## 📚 Available Documentation

1. **`README.md`** - This file (main project overview and setup)
2. **`AUDIO_SUBNET_README.md`** - Detailed subnet features and configuration
3. **`proxy_server/ENHANCED_README.md`** - Proxy server setup and API reference
4. **`COMPLETE_WORKFLOW_README.md`** - End-to-end testing guide
5. **`docs/running_on_staging.md`** - Local development setup
6. **`docs/running_on_testnet.md`** - Testnet deployment
7. **`docs/running_on_mainnet.md`** - Production deployment

---

## 🔑 Key Features

### **✅ Task Management**
- **Smart Distribution**: Assigns tasks to optimal miners (1-10 miners per task)
- **Status Tracking**: Complete lifecycle from creation to completion
- **Load Balancing**: Intelligent miner selection based on performance
- **Multi-format Support**: Audio, video, text, and translation tasks

### **✅ Response Handling**
- **Real-time Processing**: Immediate feedback on first response
- **Quality Validation**: Comprehensive scoring and evaluation
- **Error Handling**: Graceful handling of failed responses and broken files
- **Multi-pipeline Support**: Transcription, TTS, summarization, translation, and video processing

### **✅ Proxy Server Integration**
- **Task Filtering**: Miners only get assigned tasks (not completed ones)
- **Response Submission**: Results sent to proxy server database
- **API Endpoints**: Comprehensive REST API for all operations

### **✅ Performance & Monitoring**
- **Real-time Metrics**: Live task progress and miner performance
- **Comprehensive Logging**: Detailed tracking for debugging
- **Health Checks**: System monitoring and alerting

---

## 🚀 Installation

### **Prerequisites**
```bash
# Install Bittensor
pip install bittensor

# Install dependencies
pip install -r requirements.txt
```

### **Environment Setup**
```bash
# Set environment variables
export ENVIRONMENT="production"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export GOOGLE_APPLICATION_CREDENTIALS="db/violet.json"
```

### **Database Configuration**
- **Firestore**: Main database for task and response metadata
- **Google Cloud Storage**: File storage for audio and text data
- **Collections**: tasks, miner_responses, files, validators, final_results

---

## 🤝 Contributing

### **Development Setup**
1. Fork the repository
2. Create feature branch
3. Run tests: `./run_tests.sh`
4. Submit pull request

### **Code Standards**
- Follow PEP 8 style guidelines
- Include comprehensive tests
- Document all public APIs
- Use type hints throughout

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

```text
# The MIT License (MIT)
# Copyright © 2024 Opentensor Foundation

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
```

---

## 🆘 Support

For support and questions:
- **Discord**: Join the [Bittensor Discord](https://discord.gg/bittensor) for community support
- **Issues**: Report bugs and feature requests on GitHub
- **Documentation**: Check the detailed documentation files listed above
- **API Docs**: Visit `http://localhost:8000/docs` when proxy server is running

---
**🎉 Happy Mining and Validating! This subnet is production-ready with a sophisticated proxy server architecture that handles the complete workflow from task submission to final result delivery! Supports audio transcription, TTS, summarization, machine translation, video processing, and audio enhancement across 10+ languages!**
=======