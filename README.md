# Enhanced Proxy Server

A high-performance proxy server for Bittensor audio processing subnet with Firebase Cloud Storage integration.

## 🚀 Features

- **Firebase Cloud Storage Integration** - All files stored in cloud (no local storage)
- **Comprehensive API Endpoints** - Transcription, video processing, document translation, TTS
- **Docker Containerization** - Easy deployment and scaling
- **Health Monitoring** - Built-in health checks and monitoring
- **Automatic Task Distribution** - Smart task assignment to miners
- **Real-time Processing** - Async processing with response buffering
- **Weights & Biases Integration** - Performance monitoring and logging

## 📋 Prerequisites

- Python 3.12+
- Docker (for containerized deployment)
- Firebase project with Cloud Storage enabled
- Firebase service account credentials

## 🛠️ Installation

### Local Development

```bash
# Clone the repository
git clone <repository-url>
cd proxy_server

# Install dependencies
pip install -r requirements.txt

# Set up Firebase credentials
# Place your Firebase service account JSON file at db/violet.json

# Run the server
python main.py
```

### Docker Deployment

```bash
# Using Docker Compose (Recommended)
docker-compose up --build

# Or using Docker directly
docker build -t proxy-server .
docker run -p 8000:8000 -v $(pwd)/db:/app/db:ro proxy-server
```

## 🔧 Configuration

### Firebase Setup

1. Create a Firebase project
2. Enable Cloud Storage
3. Create a service account and download the JSON key
4. Place the JSON file at `db/violet.json`

### Environment Variables

- `PYTHONPATH=/app` - Python path (set automatically in Docker)
- `PYTHONUNBUFFERED=1` - Unbuffered Python output

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
