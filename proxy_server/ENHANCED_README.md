# Enhanced Bittensor Proxy Server

A sophisticated, production-ready proxy server for the Bittensor Audio Processing Subnet that handles task distribution, miner coordination, validator integration, and real-time workflow orchestration.

## 🚀 Features

### Core Functionality
- **Advanced Task Management**: Complete task lifecycle from creation to completion
- **Intelligent Load Balancing**: Smart distribution of tasks across miners
- **Real-time Monitoring**: Live tracking of task progress and miner performance
- **File Management**: Secure upload/download with Google Cloud Storage
- **Database Integration**: Firestore-based data persistence and state management

### Workflow Orchestration
- **Task Distribution**: Automatic assignment of tasks to optimal miners
- **Response Handling**: Real-time processing of miner responses
- **Immediate Feedback**: First-response delivery for better user experience
- **Validator Integration**: Seamless coordination with Bittensor validators
- **Performance Analytics**: Comprehensive metrics and optimization insights

### Architecture Benefits
- **Scalability**: Horizontal scaling support for high-throughput workloads
- **Reliability**: Fault-tolerant design with automatic failover
- **Performance**: Optimized for fastest inference with minimal latency
- **Maintainability**: Clean separation of concerns and modular design

## 🏗️ Architecture Overview

```
Client Request → Proxy Server → Database → Miners → Validators → Final Results
     ↓              ↓           ↓         ↓         ↓           ↓
File Upload → Task Queue → Firestore → Processing → Evaluation → User Response
```

### Component Structure
```
proxy_server/
├── database/           # Database schema and management
├── managers/           # Core business logic managers
├── orchestrators/      # Workflow orchestration
├── api/               # API endpoints and integration
├── tests/             # Comprehensive test suite
└── enhanced_main.py   # Main application entry point
```

## 📋 Prerequisites

- Python 3.8+
- Firebase project with Firestore enabled
- Google Cloud Storage bucket
- Valid Firebase service account credentials

## 🛠️ Installation

### 1. Clone and Setup
```bash
cd proxy_server
chmod +x start_enhanced_server.sh
chmod +x run_tests.sh
```

### 2. Install Dependencies
```bash
./start_enhanced_server.sh
```

### 3. Configure Database
Ensure your Firebase credentials are in `db/violet.json`:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "your-private-key",
  "client_email": "your-client-email",
  "client_id": "your-client-id"
}
```

## 🚀 Quick Start

### Start the Enhanced Server
```bash
./start_enhanced_server.sh
```

The server will be available at:
- **Main Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

### Run Tests
```bash
./run_tests.sh
```

## 📚 API Endpoints

### Task Submission
- `POST /api/v1/transcription` - Submit audio transcription task
- `POST /api/v1/tts` - Submit text-to-speech task
- `POST /api/v1/summarization` - Submit text summarization task

### Task Management
- `GET /api/v1/task/{task_id}/status` - Get comprehensive task status
- `GET /api/v1/health` - System health and statistics

### Miner Integration
- `POST /api/v1/miner/response` - Submit miner response and metrics

### Validator Integration
- `GET /api/v1/validator/tasks` - Get tasks ready for evaluation
- `POST /api/v1/validator/evaluation` - Submit validator evaluation and rewards

## 🔄 Workflow Lifecycle

### 1. Task Creation
```
Client submits task → File uploaded to storage → Task created in database → Status: PENDING
```

### 2. Task Distribution
```
Proxy selects optimal miners → Task assigned to miners → Status: DISTRIBUTED
```

### 3. Miner Processing
```
Miners process tasks → Submit responses and metrics → First response triggers immediate feedback
```

### 4. Task Completion
```
All miners complete → Status: DONE → Validators notified for evaluation
```

### 5. Validation & Rewards
```
Validators evaluate responses → Calculate rewards → Update task status → Status: APPROVED
```

## 📊 Performance Features

### Real-time Monitoring
- Live task progress tracking
- Miner performance metrics
- System health monitoring
- Performance analytics dashboard

### Load Balancing
- Intelligent miner selection
- Performance-based routing
- Load distribution optimization
- Failover handling

### Data Persistence
- Firestore for metadata
- Google Cloud Storage for files
- Automatic cleanup and archiving
- Data retention policies

## 🧪 Testing

### Test Coverage
The system includes comprehensive tests for:
- Database operations
- File management
- Task lifecycle
- Miner response handling
- Workflow orchestration
- Validator integration
- API endpoints

### Running Tests
```bash
# Run all tests
./run_tests.sh

# Run specific test file
python -m pytest tests/test_enhanced_system.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

## 🔧 Configuration

### Environment Variables
```bash
export ENVIRONMENT="production"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export GOOGLE_APPLICATION_CREDENTIALS="db/violet.json"
```

### Database Configuration
- **Firestore**: Main database for task and response metadata
- **Google Cloud Storage**: File storage for audio and text data
- **Collections**: tasks, miner_responses, files, validators, final_results

## 📈 Monitoring and Analytics

### Health Checks
- Database connectivity
- Storage availability
- Workflow status
- System performance metrics

### Performance Metrics
- Task completion rates
- Miner response times
- System throughput
- Error rates and handling

### Logging
- Structured logging for all operations
- Performance tracking
- Error reporting
- Audit trails

## 🚀 Deployment

### Production Setup
1. **Environment**: Use production Firebase project
2. **Scaling**: Deploy multiple proxy instances behind load balancer
3. **Monitoring**: Set up comprehensive monitoring and alerting
4. **Backup**: Configure automated backups for Firestore and Storage

### Docker Support
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements_enhanced.txt .
RUN pip install -r requirements_enhanced.txt
COPY . .
CMD ["python", "enhanced_main.py"]
```

## 🔒 Security Features

- **Authentication**: Firebase Auth integration
- **Authorization**: Role-based access control
- **Data Validation**: Comprehensive input validation
- **File Security**: Secure file upload/download
- **API Security**: Rate limiting and request validation

## 🆘 Troubleshooting

### Common Issues
1. **Database Connection**: Check Firebase credentials and network access
2. **File Upload**: Verify Google Cloud Storage permissions
3. **Task Distribution**: Check miner availability and network connectivity
4. **Performance**: Monitor system resources and database performance

### Debug Mode
Enable debug logging by setting environment variable:
```bash
export LOG_LEVEL="DEBUG"
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch
3. Run tests: `./run_tests.sh`
4. Submit pull request

### Code Standards
- Follow PEP 8 style guidelines
- Include comprehensive tests
- Document all public APIs
- Use type hints throughout

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the API documentation at `/docs`
- Review the test suite for usage examples

## 🎯 Roadmap

### Future Enhancements
- **Real-time WebSocket support**
- **Advanced ML model integration**
- **Multi-region deployment**
- **Enhanced analytics dashboard**
- **Automated scaling policies**

---

**Built with ❤️ for the Bittensor community**
