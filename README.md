# Violet Subnet - Audio Processing Network

Welcome to **Violet**, a cutting-edge Bittensor subnet dedicated to decentralized audio processing and AI-powered speech technologies. Our network leverages the power of distributed computing to provide high-quality transcription, text-to-speech synthesis, and audio analysis services.

## 🌟 Overview

Violet subnet enables a decentralized ecosystem where miners provide computational power for audio processing tasks while validators ensure quality and distribute rewards. The network integrates with a hosted proxy server for seamless task management and real-time processing.

### Key Features
- **Decentralized Audio Processing** - Distributed transcription, TTS, and audio analysis
- **Quality Assurance** - Multi-validator consensus for reliable results
- **Real-time Processing** - Low-latency audio processing with response buffering
- **Scalable Architecture** - Cloud-based storage and task distribution
- **Performance Monitoring** - Comprehensive metrics and analytics

## 💻 System Requirements

### Operating System
- **Linux** (Ubuntu 20.04+ recommended)
- **macOS** (10.15+)

### Hardware Requirements

#### For Miners
- **RAM**: 12 GB minimum
- **Storage**: 500 GB SSD
- **GPU**: NVIDIA GPU with 12 GB VRAM minimum
- **Network**: Stable internet connection (100+ Mbps)

#### For Validators
- **RAM**: 12 GB minimum
- **Storage**: 500 GB SSD
- **GPU**: NVIDIA GPU with 12 GB VRAM minimum
- **Network**: Stable internet connection (100+ Mbps)

### Software Dependencies
- Python 3.12+
- CUDA 11.8+ (for GPU acceleration)
- Docker (for containerized deployment)
- Firebase project with Cloud Storage enabled
- Firebase service account credentials
- Bittensor CLI (`pip install bittensor-cli`)

## 🚀 Network Features

- **Decentralized Audio Processing** - Distributed transcription, TTS, and audio analysis across the network
- **Multi-Validator Consensus** - Quality assurance through multiple validator evaluation
- **Real-time Task Distribution** - Smart task assignment to available miners
- **Performance Monitoring** - Comprehensive metrics and analytics tracking
- **Cloud Storage Integration** - Firebase Cloud Storage for scalable file management
- **Weights & Biases Integration** - Performance monitoring and logging
- **Automatic Load Balancing** - Intelligent distribution of computational load
- **Quality Scoring** - Fair evaluation and reward distribution system

## 📋 Prerequisites

- Python 3.12+
- Docker (for containerized deployment)
- Firebase project with Cloud Storage enabled
- Firebase service account credentials
- Bittensor CLI (`pip install bittensor-cli`)

## 🏗️ Bittensor Network Setup

### Step 1: Create Wallets

Create a coldkey and hotkey for your subnet wallet:

```bash
# Install bittensor CLI
pip install bittensor-cli

# Create a coldkey for the validator/miner
btcli wallet new_coldkey --wallet.name <your_wallet_name>

# Create a hotkey for the validator/miner
btcli wallet new_hotkey --wallet.name <your_wallet_name> --wallet.hotkey default
```

### Step 2: Register on the Subnet

Register as a miner or validator on the subnet:

**Mainnet (NetUID 49):**
```bash
btcli subnet register --netuid 49 --subtensor.network finney --wallet.name <your_wallet_name> --wallet.hotkey default
```

**Testnet (NetUID 424):**
```bash
btcli subnet register --netuid 424 --subtensor.network test --wallet.name <your_wallet_name> --wallet.hotkey default
```

**Note:** Registration requires 0.005 TAO for mainnet or test tokens for testnet.

### Step 3: Clone and Install Violet Repository

Clone the official Violet repository and install the dependencies:

```bash
# Clone the Violet repository
git clone https://github.com/hivetrainai/violet.git
cd violet

# Install the Violet package in development mode
pip install -e .

# Install additional requirements
pip install -r requirements.txt

# Return to the main directory
cd ..
```

### Step 4: Run the Miner

Start your miner node:

**Mainnet:**
```bash
python neurons/miner.py \
  --netuid 49 \
  --subtensor.network finney \
  --wallet.name <your_wallet_name> \
  --wallet.hotkey <your_hotkey> \
  --logging.debug \
  --axon.ip 0.0.0.0 \
  --axon.port <PORT> \
  --axon.external_ip <YOUR_PUBLIC_IP> \
  --axon.external_port <PORT>
```

**Testnet:**
```bash
python neurons/miner.py \
  --netuid 424 \
  --subtensor.network test \
  --wallet.name <your_wallet_name> \
  --wallet.hotkey <your_hotkey> \
  --logging.debug \
  --axon.ip 0.0.0.0 \
  --axon.port <PORT> \
  --axon.external_ip <YOUR_PUBLIC_IP> \
  --axon.external_port <PORT>
```

### Step 5: Run the Validator

Start your validator node:

**Mainnet:**
```bash
python neurons/validator.py \
  --netuid 49 \
  --subtensor.network finney \
  --wallet.name <your_wallet_name> \
  --wallet.hotkey <your_hotkey> \
  --logging.debug \
  --axon.ip 0.0.0.0 \
  --axon.port <PORT> \
  --axon.external_ip <YOUR_PUBLIC_IP> \
  --axon.external_port <PORT>
```

**Testnet:**
```bash
python neurons/validator.py \
  --netuid 424 \
  --subtensor.network test \
  --wallet.name <your_wallet_name> \
  --wallet.hotkey <your_hotkey> \
  --logging.debug \
  --axon.ip 0.0.0.0 \
  --axon.port <PORT> \
  --axon.external_ip <YOUR_PUBLIC_IP> \
  --axon.external_port <PORT>
```

### Network Configuration Summary

| Network | NetUID | Network Name | Registration Cost |
|---------|--------|--------------|-------------------|
| Mainnet | 49     | finney       | 0.005 TAO         |
| Testnet | 424    | test         | 0.005 test tokens |

### Proxy Server Integration

Both miner and validator are configured to use the hosted proxy server at `https://violet-proxy.onrender.com`. You can override this using environment variables:

```bash
# Override proxy server URL
export PROXY_SERVER_URL=https://your-custom-proxy.com

# Or use command line argument
python neurons/validator.py --proxy_server_url https://your-custom-proxy.com
```

## 🏗️ System Architecture

### Network Overview

Violet subnet operates as a decentralized network of miners and validators, coordinated through a centralized proxy server for task distribution and result aggregation.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    VIOLET SUBNET ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   USER CLIENT   │    │  PROXY SERVER    │    │  BITTENSOR      │    │  CLOUD STORAGE   │
│                 │    │                 │    │  NETWORK        │    │                 │
│ • Web App       │───▶│ • Task Queue    │───▶│ • Miners        │───▶│ • Firebase       │
│ • API Client    │    │ • Distribution   │    │ • Validators    │    │ • Cloud Storage  │
│ • Mobile App    │    │ • Aggregation    │    │ • Consensus     │    │ • Firestore DB   │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │                        │
                                ▼                        ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
                       │  TASK MANAGER   │    │  AI PROCESSING  │    │  FILE MANAGER   │
                       │                 │    │                 │    │                 │
                       │ • Task Creation │    │ • Transcription │    │ • Upload/Download│
                       │ • Assignment    │    │ • TTS Synthesis │    │ • Metadata Mgmt  │
                       │ • Status Track  │    │ • Audio Analysis│    │ • Cache Control  │
                       └─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │                        │
                                ▼                        ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
                       │  VALIDATOR      │    │  MINER NODES    │    │  MONITORING     │
                       │  CONSENSUS      │    │                 │    │                 │
                       │                 │    │ • GPU Processing│    │ • Weights & Biases│
                       │ • Quality Check │    │ • Model Loading │    │ • Performance    │
                       │ • Reward Calc   │    │ • Response Gen  │    │ • Analytics      │
                       │ • Network Health│    │ • Result Submit │    │ • Logging        │
                       └─────────────────┘    └─────────────────┘    └─────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATA FLOW DIAGRAM                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   1. UPLOAD │  │  2. QUEUE   │  │  3. ASSIGN  │  │  4. PROCESS │  │  5. EVALUATE│
│             │  │             │  │             │  │             │  │             │
│ User uploads│──▶│ Task created │──▶│ Distributed │──▶│ Miners     │──▶│ Validators  │
│ audio/text  │  │ in Firestore│  │ to miners  │  │ process    │  │ evaluate    │
│ to proxy    │  │ & queued    │  │ based on   │  │ with AI    │  │ quality &   │
│ server      │  │ for dist.   │  │ availability│  │ models     │  │ distribute  │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
       │                │                │                │                │
       ▼                ▼                ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ File stored │  │ Task status │  │ Load       │  │ Results     │  │ Rewards     │
│ in Firebase │  │ tracked in  │  │ balanced   │  │ uploaded to │  │ calculated  │
│ Cloud       │  │ real-time   │  │ across     │  │ Cloud       │  │ & distributed│
│ Storage     │  │             │  │ network    │  │ Storage     │  │ to miners   │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    COMPONENT DETAILS                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  PROXY SERVER (https://violet-proxy.onrender.com)                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ • Task Distribution Engine    │ • Response Aggregation    │ • Quality Control      │
│ • Load Balancing Algorithm     │ • Buffer Management       │ • Duplicate Protection │
│ • Real-time Status Tracking    │ • Performance Monitoring  │ • Error Handling       │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  MINER NODES (Computational Power)                                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ • GPU-Accelerated Processing   │ • AI Model Management     │ • Response Generation  │
│ • Task Execution Engine        │ • Memory Optimization    │ • Result Submission   │
│ • Performance Tracking         │ • Error Recovery          │ • Health Monitoring   │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  VALIDATOR NODES (Quality Assurance)                                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ • Multi-Validator Consensus     │ • Quality Scoring         │ • Reward Calculation   │
│ • Response Evaluation           │ • Performance Metrics     │ • Network Health Check │
│ • Fairness Assurance            │ • Load Distribution       │ • Consensus Building   │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  CLOUD INFRASTRUCTURE (Scalable Storage & Analytics)                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ • Firebase Cloud Storage       │ • Firestore Database      │ • Weights & Biases     │
│ • File Metadata Management     │ • Task Status Tracking    │ • Performance Analytics│
│ • Scalable File Operations     │ • Real-time Updates       │ • Network Monitoring   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Architecture

#### 1. **Proxy Server** (`https://violet-proxy.onrender.com`)
- **Task Distribution**: Routes tasks to available miners
- **Response Aggregation**: Collects and buffers miner responses
- **Quality Control**: Validates responses before final delivery
- **Load Balancing**: Distributes computational load across miners

#### 2. **Miners** (Computational Nodes)
- **Audio Processing**: Transcription, TTS, and audio analysis
- **Task Execution**: Processes assigned tasks with AI models
- **Response Submission**: Sends results back to proxy server
- **Performance Monitoring**: Tracks processing times and accuracy

#### 3. **Validators** (Quality Assurance)
- **Response Evaluation**: Assesses miner response quality
- **Consensus Building**: Multi-validator agreement on results
- **Reward Distribution**: Calculates and distributes TAO rewards
- **Network Health**: Monitors miner performance and availability

#### 4. **Cloud Infrastructure**
- **Firebase Cloud Storage**: Scalable file storage and retrieval
- **Firestore Database**: Task metadata and result tracking
- **Weights & Biases**: Performance monitoring and analytics

### Data Flow

```
1. User Upload → Proxy Server
   ├── File stored in Firebase Cloud Storage
   ├── Task created in Firestore
   └── Task queued for distribution

2. Task Distribution → Miners
   ├── Proxy server assigns tasks to available miners
   ├── Miners download files from Cloud Storage
   └── Miners process tasks using AI models

3. Response Collection → Proxy Server
   ├── Miners upload results to Cloud Storage
   ├── Results aggregated by proxy server
   └── Quality validation performed

4. Validator Evaluation → Consensus
   ├── Validators evaluate miner responses
   ├── Multi-validator consensus reached
   ├── Rewards calculated and distributed
   └── Results delivered to user

5. Performance Tracking → Analytics
   ├── Metrics logged to Weights & Biases
   ├── Network health monitored
   └── Performance optimizations applied
```

### Security & Reliability

- **Multi-Validator Consensus**: Ensures result accuracy through multiple validators
- **Duplicate Protection**: Prevents double-processing of tasks
- **Response Buffering**: Handles network latency and miner failures
- **Quality Scoring**: Fair evaluation system for miner rewards
- **Load Balancing**: Prevents network overload and ensures fair distribution

## 🛠️ Installation & Setup

### Prerequisites Installation

```bash
# Install Python dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers librosa soundfile numpy fastapi uvicorn

# Install Bittensor
pip install bittensor

# Install Bittensor CLI
pip install bittensor-cli

# Install additional dependencies
pip install firebase-admin google-cloud-storage wandb
```

### Clone Repository

```bash
# Clone the repository
git clone <repository-url>
cd bittensor-subnet-template

# Install project dependencies
pip install -r requirements.txt
```

### Environment Setup

```bash
# Set up environment variables
export PYTHONPATH=$PYTHONPATH:$(pwd)
export CUDA_VISIBLE_DEVICES=0  # Use first GPU
export WANDB_MODE=online       # Enable Weights & Biases logging
```

## 🔧 Configuration

### GPU Configuration

Ensure your GPU is properly configured for CUDA:

```bash
# Check CUDA installation
nvidia-smi

# Verify PyTorch CUDA support
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'CUDA version: {torch.version.cuda}')"
```

### Network Configuration

Configure your network settings for optimal performance:

```bash
# Set network parameters
export BT_NETUID=49          # Mainnet subnet ID
export BT_NETWORK=finney     # Mainnet network
export BT_WALLET_NAME=your_wallet_name
export BT_WALLET_HOTKEY=default

# For testnet
export BT_NETUID=424         # Testnet subnet ID
export BT_NETWORK=test       # Testnet network
```

### Proxy Server Integration

The subnet automatically connects to the hosted proxy server. Configuration is handled automatically, but you can override if needed:

```bash
# Override proxy server URL (optional)
export PROXY_SERVER_URL=https://violet-proxy.onrender.com
```

## 📡 API Endpoints

### Health & Monitoring
- `GET /health` - Health check endpoint
- `GET /api/v1/status` - System status

### File Upload & Processing
- `POST /api/v1/transcription` - Audio transcription
- `POST /api/v1/video-transcription` - Video transcription
- `POST /api/v1/document-translation` - Document translation
- `POST /api/v1/tts` - Text-to-speech generation

### File Management
- `GET /api/v1/files/{file_id}` - Download file
- `GET /api/v1/files/{file_id}/download` - Download file (with headers)
- `GET /api/v1/tts/audio/{file_id}` - Download TTS audio

### Task Management
- `GET /api/v1/tasks` - List all tasks
- `GET /api/v1/tasks/{task_id}` - Get specific task
- `GET /api/v1/tasks/completed` - List completed tasks

### Miner Integration
- `GET /api/v1/miners/{miner_id}/tasks` - Get miner's assigned tasks
- `POST /api/v1/miner/response` - Submit miner response
- `POST /api/v1/miner/tts/upload-audio` - Upload TTS audio from miner

### Validator Integration
- `GET /api/v1/validator/tasks` - Get tasks for validator evaluation
- `POST /api/v1/validator/evaluate` - Submit validator evaluation

## 🏗️ Architecture

### Core Components

1. **FirebaseStorageManager** - Handles all file operations with Firebase Cloud Storage
2. **DatabaseManager** - Manages Firestore database operations
3. **TaskOrchestrator** - Coordinates task distribution and processing
4. **ResponseAggregator** - Buffers and manages miner responses
5. **WorkflowOrchestrator** - Orchestrates the entire workflow

### Storage Strategy

- **All files** → Firebase Cloud Storage (`gs://violet-7063e.firebasestorage.app`)
- **File metadata** → Firestore database
- **No local storage** → Everything in the cloud

### Task Flow

1. **Upload** → File uploaded to Cloud Storage
2. **Task Creation** → Task created in Firestore
3. **Distribution** → Task assigned to available miners
4. **Processing** → Miners process and submit responses
5. **Aggregation** → Responses buffered and aggregated
6. **Evaluation** → Validator evaluates responses
7. **Completion** → Task marked as completed


## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### System Status
```bash
curl http://localhost:8000/api/v1/status
```

### Weights & Biases
The server automatically logs metrics to Weights & Biases for monitoring:
- Task creation and completion rates
- Processing times
- Error rates
- System performance metrics

## 🔍 Testing

### Run Tests
```bash
# Run all tests
python -m pytest

# Run specific test
python -m pytest test_functionality.py

# Run with coverage
python -m pytest --cov=.
```

### Test Endpoints
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test file upload
curl -X POST http://localhost:8000/api/v1/transcription \
  -F "audio_file=@test.wav" \
  -F "source_language=en"
```

## 🚨 Troubleshooting

### Common Issues

1. **Firebase Connection Error**
   - Verify `db/violet.json` exists and is valid
   - Check Firebase project permissions

2. **Port Already in Use**
   - Change port in docker-compose.yml
   - Or kill existing process: `pkill -f main.py`

3. **File Upload Fails**
   - Check file size limits
   - Verify Firebase Cloud Storage bucket exists
   - Check network connectivity

### Logs
```bash
# View application logs
tail -f logs/proxy_server.log

# View Docker logs
docker-compose logs -f
```

## 📈 Performance

### Optimizations
- Async processing for all I/O operations
- Response buffering to reduce database writes
- Smart task distribution based on miner availability
- Cloud Storage for scalable file handling

### Benchmarks
- **File Upload**: ~5-10 seconds for 1MB files
- **Task Processing**: ~2-5 seconds for simple tasks
- **Concurrent Users**: Supports 100+ concurrent connections

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation

---

**Built with ❤️ for the Bittensor community**
