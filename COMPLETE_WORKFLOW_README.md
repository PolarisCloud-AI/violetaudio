# Complete Workflow Test: Proxy Server → Validator → Miner → Response

This document explains how to test the entire audio processing pipeline from user input to final response.

## 🎯 What We're Testing

The complete workflow demonstrates:
1. **User submits task** → Proxy server receives and queues
2. **Validator checks** → Automatically discovers pending tasks
3. **Task processing** → Validator queries miners via Bittensor network
4. **Response evaluation** → Validator scores and selects best response
5. **Result delivery** → User receives processed results via proxy server

## 🏗️ System Architecture

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────┐    ┌─────────────┐
│    User    │───▶│  Proxy Server   │───▶│  Validator  │───▶│    Miner    │
│             │    │   (Port 8000)   │    │ (Port 8092) │    │ (Port 8091) │
└─────────────┘    └─────────────────┘    └─────────────┘    └─────────────┘
       ▲                    │                    │                    │
       │                    │                    │                    │
       └────────────────────┴────────────────────┴────────────────────┘
                              Response Flow
```

## 🚀 Quick Start

### 1. Start All Components
```bash
./start_complete_system.sh
```

This script will:
- Start the proxy server on port 8000
- Start the miner on port 8091
- Start the validator on port 8092 (with proxy integration)
- Wait for all services to be ready
- Display status and next steps

### 2. Run the Complete Workflow Test
```bash
python test_complete_workflow.py
```

This test will:
- Submit 3 different task types (transcription, TTS, summarization)
- Monitor task processing through the entire pipeline
- Verify responses from miners
- Provide detailed analysis of the workflow

### 3. Stop All Components
```bash
./stop_complete_system.sh
```

## 📋 Prerequisites

### Required Software
- Python 3.8+
- Bittensor 6.0.0+
- Required Python packages (see `requirements.txt`)

### Network Configuration
- Validator wallet: `luno` with hotkey `arusha`
- Miner wallet: `mokoai` with hotkey `default`
- External IP: `102.134.149.117`
- NetUID: `49`
- Network: `finney` (mainnet)

### Bittensor Setup
- Valid wallets with sufficient TAO balance
- Network connectivity to Bittensor mainnet
- Proper axon configuration for external access

## 🔧 Manual Component Startup

If you prefer to start components manually:

### 1. Start Proxy Server
```bash
cd proxy_server
python main.py
```

### 2. Start Miner
```bash
python neurons/miner.py \
  --netuid 49 \
  --subtensor.network finney \
  --wallet.name mokoai \
  --wallet.hotkey default \
  --logging.debug \
  --axon.ip 0.0.0.0 \
  --axon.port 8091 \
  --axon.external_ip 102.134.149.117 \
  --axon.external_port 8091
```

### 3. Start Validator (with proxy integration)
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

## 🧪 Testing the Workflow

### Test 1: Health Check
- Verifies proxy server is running
- Checks Bittensor connectivity
- Shows current queue status

### Test 2: Validator Integration
- Tests validator integration endpoint
- Shows available miners
- Displays network information

### Test 3: Task Submission
- Submits transcription task (with test audio)
- Submits TTS task (with test text)
- Submits summarization task (with long text)

### Test 4: Task Distribution
- Distributes tasks to validator
- Marks tasks as processing
- Prepares for Bittensor processing

### Test 5: Task Monitoring
- Monitors task status changes
- Tracks processing progress
- Waits for completion

### Test 6: Result Analysis
- Analyzes final results
- Shows processing times and scores
- Verifies output data quality

## 📊 Expected Results

### Successful Workflow
```
✅ PROXY_HEALTH: Server healthy - healthy
✅ VALIDATOR_INTEGRATION: Integration successful
✅ TASK_SUBMISSION: 3/3 tasks submitted
✅ TASK_DISTRIBUTION: Tasks distributed successfully
✅ TASK_MONITORING: All tasks completed!
✅ FINAL_RESULTS: Success Rate: 100%
```

### Task Processing Flow
1. **Pending** → Task submitted and queued
2. **Processing** → Validator picks up task
3. **Completed** → Miner response processed and scored
4. **Result Available** → User can retrieve results

## 🔍 Monitoring and Debugging

### Log Files
- `logs/proxy_server.log` - Proxy server activity
- `logs/miner.log` - Miner operations and responses
- `logs/validator.log` - Validator processing and integration

### Real-time Monitoring
```bash
# Watch proxy server logs
tail -f logs/proxy_server.log

# Watch validator logs
tail -f logs/validator.log

# Watch miner logs
tail -f logs/miner.log
```

### Health Checks
```bash
# Check proxy server health
curl http://localhost:8000/api/v1/health

# Check validator integration
curl http://localhost:8000/api/v1/validator/integration

# Check task queue
curl http://localhost:8000/api/v1/tasks
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Check what's using the port
lsof -i :8000
lsof -i :8091
lsof -i :8092

# Kill processes if needed
kill -9 <PID>
```

#### 2. Validator Can't Connect to Proxy
- Check proxy server is running on port 8000
- Verify firewall settings
- Check proxy server logs for errors

#### 3. Tasks Not Processing
- Verify validator is running with integration enabled
- Check validator logs for integration errors
- Ensure Bittensor network connectivity

#### 4. Miner Not Responding
- Check miner is running and connected
- Verify miner logs for errors
- Check Bittensor network status

### Debug Mode
Enable debug logging for detailed information:
```bash
# Proxy server (already enabled)
# Miner (already enabled)
# Validator (already enabled)
```

## 📈 Performance Metrics

### Expected Processing Times
- **Transcription**: ~60 seconds
- **TTS**: ~45 seconds  
- **Summarization**: ~30 seconds

### Quality Metrics
- **Accuracy Score**: 0.0 - 1.0 (higher is better)
- **Speed Score**: 0.0 - 1.0 (higher is better)
- **Combined Score**: Weighted average (70% accuracy + 30% speed)

## 🔮 Next Steps

After successful testing:

1. **Real Data Testing**: Submit actual audio files and text
2. **Load Testing**: Submit multiple concurrent tasks
3. **Performance Optimization**: Adjust intervals and timeouts
4. **Production Deployment**: Configure for production environment
5. **Monitoring Setup**: Implement comprehensive monitoring

## 📚 Additional Resources

- [Validator-Proxy Integration Guide](VALIDATOR_PROXY_INTEGRATION.md)
- [Proxy Server Documentation](proxy_server/README.md)
- [Bittensor Documentation](https://docs.bittensor.com/)
- [API Endpoints Reference](proxy_server/README.md#api-endpoints)

## 🆘 Support

If you encounter issues:

1. Check the logs in the `logs/` directory
2. Verify all prerequisites are met
3. Check network connectivity and firewall settings
4. Ensure proper wallet configuration
5. Review Bittensor network status

---

**Happy Testing! 🎉**

The complete workflow test demonstrates the full power of your Bittensor audio processing subnet with integrated proxy server orchestration.
