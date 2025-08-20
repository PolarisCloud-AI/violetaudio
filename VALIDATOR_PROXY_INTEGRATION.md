# Validator-Proxy Server Integration

This document explains how the Bittensor validator integrates with the proxy server to orchestrate and distribute tasks to miners.

## Overview

The integration allows the validator to:
1. **Check for pending tasks** from the proxy server at regular intervals
2. **Get network information** about available miners and their status
3. **Process tasks** using the existing Bittensor forward logic
4. **Distribute tasks** to active miners based on their stake and availability

## Architecture

```
User Request → Proxy Server → Task Queue → Validator → Miners → Response → User
```

### Components

1. **Proxy Server** (`proxy_server/main.py`)
   - Accepts user requests for transcription, TTS, and summarization
   - Stores tasks in in-memory queue
   - Provides endpoints for validator integration

2. **Validator** (`neurons/validator.py`)
   - Checks proxy server for pending tasks
   - Processes tasks using Bittensor network
   - Evaluates miner responses and calculates rewards

3. **Task Storage**
   - In-memory storage with thread safety
   - Priority-based task queuing
   - Task status tracking (pending, processing, completed, failed)

## Integration Endpoints

### 1. Validator Integration Info
```
GET /api/v1/validator/integration
```
Returns:
- Network information (netuid, network, total miners)
- Available miners with their details
- Pending tasks in the queue
- Queue statistics

### 2. Task Distribution
```
POST /api/v1/validator/distribute
```
Distributes pending tasks to the validator for processing.

## Validator Configuration

The validator can be configured with proxy server integration:

```bash
python neurons/validator.py \
  --netuid 49 \
  --subtensor.network finney \
  --wallet.name luno \
  --wallet.hotkey arusha \
  --logging.debug \
  --axon.ip 0.0.0.0 \
  --axon.port 8092 \
  --axon.external_ip 102.134.149.117 \
  --axon.external_port 8092 \
  --proxy_server_url http://localhost:8000 \
  --enable_proxy_integration \
  --proxy_check_interval 30
```

### Configuration Options

- `--proxy_server_url`: URL of the proxy server (default: http://localhost:8000)
- `--enable_proxy_integration`: Enable/disable integration (default: True)
- `--proxy_check_interval`: Seconds between checks (default: 30)

## How It Works

### 1. Task Submission
1. User submits task via proxy server endpoint
2. Task is stored in in-memory queue with priority
3. Task status is set to "pending"

### 2. Validator Task Checking
1. Validator runs `check_proxy_server_tasks()` every forward cycle
2. Checks if enough time has passed since last check
3. Queries proxy server for integration info
4. Processes any pending tasks found

### 3. Task Processing
1. Validator creates AudioTask synapse for each task
2. Queries available miners using existing forward logic
3. Evaluates responses and calculates scores
4. Updates task status in proxy server

### 4. Response Handling
1. Best miner response is selected based on accuracy and speed
2. Task is marked as completed with results
3. User can retrieve results via proxy server endpoints

## Testing the Integration

### 1. Start the Proxy Server
```bash
cd proxy_server
python main.py
```

### 2. Start the Validator
```bash
python neurons/validator.py --enable_proxy_integration
```

### 3. Submit a Test Task
```bash
# Test transcription
curl -X POST "http://localhost:8000/api/v1/transcription" \
  -F "audio_file=@test_audio.wav" \
  -F "source_language=en" \
  -F "priority=normal"

# Test TTS
curl -X POST "http://localhost:8000/api/v1/tts" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "source_language": "en"}'

# Test summarization
curl -X POST "http://localhost:8000/api/v1/summarization" \
  -H "Content-Type: application/json" \
  -d '{"text": "Long text to summarize...", "source_language": "en"}'
```

### 4. Check Integration
```bash
# Get integration info
curl "http://localhost:8000/api/v1/validator/integration"

# Distribute tasks
curl -X POST "http://localhost:8000/api/v1/validator/distribute"
```

## Benefits

1. **Decoupled Architecture**: Proxy server handles user requests, validator handles Bittensor network
2. **Real-time Task Processing**: Validator actively checks for new tasks
3. **Scalable**: Multiple validators can potentially share the same proxy server
4. **Monitoring**: Full visibility into task queue and processing status
5. **Priority Handling**: Tasks can be prioritized based on user requirements

## Future Enhancements

1. **Webhook Notifications**: Notify users when tasks complete
2. **Task Batching**: Process multiple similar tasks together
3. **Load Balancing**: Distribute tasks across multiple validators
4. **Persistent Storage**: Add database backend for task persistence
5. **Authentication**: Secure endpoints with API keys

## Troubleshooting

### Common Issues

1. **Validator can't connect to proxy server**
   - Check if proxy server is running
   - Verify URL and port configuration
   - Check firewall settings

2. **Tasks not being processed**
   - Verify validator is running with integration enabled
   - Check proxy server logs for errors
   - Verify Bittensor network connectivity

3. **Performance issues**
   - Adjust `proxy_check_interval` based on task volume
   - Monitor memory usage of in-memory storage
   - Consider implementing task batching

### Logs

The validator will log integration activities:
```
🔍 Checking proxy server for pending tasks...
📋 Found 3 pending tasks in proxy server
🔄 Processing 3 tasks from proxy server...
🎯 Processing proxy task: transcription in en
```

## Conclusion

The validator-proxy server integration provides a robust foundation for orchestrating audio processing tasks in the Bittensor network. It enables real-time task processing while maintaining the decentralized nature of the network.
