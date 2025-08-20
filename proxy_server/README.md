# Bittensor Audio Processing Proxy Server

A FastAPI-based proxy server that provides REST API endpoints for audio processing services and integrates with the Bittensor network for distributed task processing.

## 🚀 Features

- **Service-Specific REST API Endpoints** for audio transcription, TTS, and summarization
- **Priority-based Task Queue** with Redis backend
- **Bittensor Network Integration** for distributed processing
- **Automatic Miner Evaluation** with accuracy and speed scoring
- **Task Status Tracking** with real-time updates
- **Webhook Support** for task completion notifications
- **Retry Mechanism** for failed tasks
- **Health Monitoring** and statistics
- **Input Validation** and formatting for each service type

## 🏗️ Architecture

```
User Request → FastAPI Server → Task Queue → Bittensor Network → Miners
                ↓                    ↓              ↓
            Response ← Result ← Validator ← Miner Responses
```

## 📋 Prerequisites

- Python 3.8+
- Redis server
- Bittensor wallet configured
- Access to Bittensor network (finney/testnet)

## 🛠️ Installation

1. **Clone the repository and navigate to the proxy server directory:**
   ```bash
   cd proxy_server
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install and start Redis:**
   ```bash
   # macOS
   brew install redis
   brew services start redis
   
   # Ubuntu/Debian
   sudo apt-get install redis-server
   sudo systemctl start redis-server
   
   # Or use Docker
   docker run -d -p 6379:6379 redis:alpine
   ```

4. **Set environment variables (optional):**
   ```bash
   export ENVIRONMENT=development
   export BT_NETUID=49
   export BT_NETWORK=finney
   export BT_WALLET_NAME=luno
   export BT_WALLET_HOTKEY=arusha
   ```

## 🚀 Running the Server

### Development Mode
```bash
python start_server.py
```

### Production Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The server will start on `http://localhost:8000`

## 📚 API Endpoints

### 1. Audio Transcription
```http
POST /api/v1/transcription
Content-Type: multipart/form-data

Form Data:
- audio_file: Audio file (WAV, MP3, etc.)
- source_language: Language code (e.g., 'en', 'es', 'fr')
- priority: Task priority (low, normal, high, urgent)
- callback_url: Optional webhook URL
```

**Example with curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/transcription" \
  -F "audio_file=@audio.wav" \
  -F "source_language=en" \
  -F "priority=normal"
```

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "message": "Transcription task submitted successfully",
  "estimated_completion_time": 60,
  "task_type": "transcription",
  "source_language": "en"
}
```

### 2. Text-to-Speech (TTS)
```http
POST /api/v1/tts
Content-Type: application/json

{
  "text": "Text to convert to speech",
  "source_language": "en",
  "priority": "normal",
  "callback_url": "https://your-webhook.com/callback"
}
```

**Example with curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/tts" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test for TTS conversion.",
    "source_language": "en",
    "priority": "normal"
  }'
```

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "message": "TTS task submitted successfully",
  "estimated_completion_time": 45,
  "task_type": "tts",
  "source_language": "en"
}
```

### 3. Text Summarization
```http
POST /api/v1/summarization
Content-Type: application/json

{
  "text": "Long text to summarize",
  "source_language": "en",
  "priority": "normal",
  "callback_url": "https://your-webhook.com/callback"
}
```

**Example with curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/summarization" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Long article text here...",
    "source_language": "en",
    "priority": "normal"
  }'
```

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "message": "Summarization task submitted successfully",
  "estimated_completion_time": 30,
  "task_type": "summarization",
  "source_language": "en"
}
```

### 4. Task Status Check
```http
GET /api/v1/tasks/{task_id}
```

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "completed",
  "task_type": "transcription",
  "source_language": "en",
  "result": {
    "output_data": "base64_encoded_result",
    "model_used": "openai/whisper-tiny",
    "processing_time": 1.23,
    "accuracy_score": 0.95,
    "speed_score": 0.89,
    "miner_uid": 48
  },
  "processing_time": 1.23,
  "accuracy_score": 0.95,
  "speed_score": 0.89,
  "completed_at": "2024-01-01T12:00:00"
}
```

### 5. List All Tasks
```http
GET /api/v1/tasks?status=pending&limit=10
```

### 6. Health Check
```http
GET /api/v1/health
```

## 🔧 Configuration

The server configuration can be customized through environment variables or by modifying `config.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `BT_NETUID` | `49` | Bittensor subnet UID |
| `BT_NETWORK` | `finney` | Bittensor network |
| `MAX_CONCURRENT_TASKS` | `10` | Maximum concurrent tasks |
| `TASK_TIMEOUT` | `60` | Task timeout in seconds |

## 📊 Task Processing Flow

1. **Task Submission**: User submits task via service-specific endpoint
2. **Input Validation**: Server validates input format and requirements
3. **Queue Management**: Task is added to priority queue in Redis
4. **Bittensor Processing**: Validator queries available miners
5. **Response Evaluation**: Responses are scored for accuracy and speed
6. **Result Selection**: Best response is selected based on combined score
7. **Task Completion**: Result is returned to user and task is dequeued

## 🎯 Scoring System

Tasks are evaluated using a weighted scoring system:

- **Accuracy Score (70%)**: Based on comparison with validator pipeline
- **Speed Score (30%)**: Based on processing time
- **Combined Score**: Weighted average of accuracy and speed

## 🔄 Retry Mechanism

Failed tasks are automatically retried up to 3 times before being marked as permanently failed.

## 📈 Monitoring

### Queue Statistics
- Pending tasks count
- Processing tasks count
- Completed tasks count
- Failed tasks count
- Queue size

### Network Statistics
- Total miners
- Available miners
- Total stake
- Network connectivity status

## 🧪 Testing

### Test with curl
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Submit transcription task
curl -X POST "http://localhost:8000/api/v1/transcription" \
  -F "audio_file=@audio.wav" \
  -F "source_language=en" \
  -F "priority=normal"

# Submit TTS task
curl -X POST "http://localhost:8000/api/v1/tts" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "source_language": "en",
    "priority": "normal"
  }'

# Submit summarization task
curl -X POST "http://localhost:8000/api/v1/summarization" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Long article text...",
    "source_language": "en",
    "priority": "normal"
  }'

# Check task status (replace {task_id} with actual ID)
curl "http://localhost:8000/api/v1/tasks/{task_id}"
```

### Test with Python
```python
import requests

# Test transcription
with open('audio.wav', 'rb') as f:
    files = {'audio_file': ('audio.wav', f, 'audio/wav')}
    data = {'source_language': 'en', 'priority': 'normal'}
    response = requests.post("http://localhost:8000/api/v1/transcription", 
                           files=files, data=data)
    task_id = response.json()["task_id"]

# Test TTS
tts_data = {
    "text": "Hello, this is a test.",
    "source_language": "en",
    "priority": "normal"
}
response = requests.post("http://localhost:8000/api/v1/tts", json=tts_data)
task_id = response.json()["task_id"]

# Test summarization
summarization_data = {
    "text": "Long article text here...",
    "source_language": "en",
    "priority": "normal"
}
response = requests.post("http://localhost:8000/api/v1/summarization", 
                       json=summarization_data)
task_id = response.json()["task_id"]

# Check status
status_response = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}")
print(f"Task status: {status_response.json()}")
```

### Run Test Suite
```bash
python test_proxy.py
```

## 🚨 Troubleshooting

### Common Issues

1. **Redis Connection Error**
   ```bash
   # Check if Redis is running
   redis-cli ping
   
   # Start Redis if needed
   brew services start redis  # macOS
   sudo systemctl start redis-server  # Linux
   ```

2. **Bittensor Connection Error**
   - Verify wallet configuration
   - Check network connectivity
   - Ensure metagraph sync

3. **Task Processing Errors**
   - Check miner availability
   - Verify input data format
   - Review server logs

### Logs
The server provides detailed logging for:
- Task submission and processing
- Bittensor network communication
- Miner response evaluation
- Error details and stack traces

## 🔒 Security Considerations

- **Input Validation**: All inputs are validated using Pydantic models
- **File Upload Limits**: Audio files limited to 50MB
- **Text Length Limits**: TTS (10K chars), Summarization (50K chars)
- **Language Validation**: Only supported languages accepted
- **Rate Limiting**: Configurable rate limiting per endpoint
- **CORS**: Configurable CORS policies
- **Authentication**: Ready for JWT token integration

## 🚀 Production Deployment

1. **Use a production WSGI server** (Gunicorn, uWSGI)
2. **Set up Redis persistence** and clustering
3. **Configure monitoring** and alerting
4. **Set up load balancing** for high availability
5. **Use environment-specific configurations**

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the logs for error details
