# Enhanced Pipelines Documentation

## Overview

This document describes the comprehensive enhancements made to all pipelines in the Bittensor subnet template, focusing on **production readiness**, **timestamped transcription**, and **large file handling**.

## 🎵 Enhanced Transcription Pipeline

### New Features

#### 1. **Timestamped Chunks (YouTube-Style)**
- **Audio Segmentation**: Automatically splits long audio into configurable time chunks
- **Timing Information**: Each chunk includes start/end timestamps
- **Multiple Output Formats**:
  - **YouTube Style**: `02:05 Hello, this is the first chunk`
  - **SRT Subtitles**: Standard subtitle format with timing
  - **WebVTT**: Web video text tracks format
  - **Plain Timestamps**: `[125.50s - 140.00s] Text content`

#### 2. **Memory Management**
- **Smart Chunking**: Automatically chunks audio based on:
  - Duration threshold (configurable)
  - Memory usage (configurable)
  - File size limits
- **Resource Cleanup**: Automatic CUDA cache clearing and garbage collection
- **Memory Monitoring**: Real-time memory usage tracking

#### 3. **Parallel Processing**
- **Concurrent Chunks**: Processes multiple audio chunks simultaneously
- **ThreadPoolExecutor**: Configurable worker threads for optimal performance
- **Progress Tracking**: Real-time chunk processing status

#### 4. **Production Optimization**
```python
# Optimize for production use
pipeline.optimize_for_production(
    target_memory_gb=2.0,        # Memory limit
    target_chunk_duration=15.0    # Chunk duration
)
```

### Usage Example

```python
from template.pipelines.transcription_pipeline import TranscriptionPipeline

# Initialize with production settings
pipeline = TranscriptionPipeline(
    model_name="openai/whisper-tiny",
    chunk_duration=30.0,      # 30-second chunks
    max_memory_gb=4.0         # 4GB memory limit
)

# Transcribe audio with automatic chunking
result = pipeline.transcribe(audio_bytes, language="en")

# Get timestamped transcript in various formats
youtube_format = pipeline.get_timestamped_transcript(result, "youtube")
srt_format = pipeline.get_timestamped_transcript(result, "srt")
vtt_format = pipeline.get_timestamped_transcript(result, "vtt")

# Access individual chunks
for chunk in result.chunks:
    print(f"{chunk.start_time:.2f}s - {chunk.end_time:.2f}s: {chunk.text}")
```

### Performance Monitoring

```python
# Get comprehensive performance statistics
stats = pipeline.get_performance_stats()
print(f"Total files processed: {stats['total_files_processed']}")
print(f"Average processing speed: {stats['average_processing_speed']:.2f}s/audio")
print(f"Memory usage samples: {stats['memory_usage_samples']}")
```

## 🎤 Enhanced TTS Pipeline

### New Features

#### 1. **Long Text Handling**
- **Automatic Chunking**: Splits long texts into manageable chunks
- **Configurable Limits**: Adjustable maximum text length per synthesis
- **Overlap Management**: Configurable character overlap between chunks

#### 2. **Memory Management**
- **Resource Cleanup**: Automatic memory cleanup after each chunk
- **CUDA Optimization**: GPU memory management for large models
- **Performance Monitoring**: Memory usage tracking and optimization

#### 3. **Production Settings**
```python
# Production optimization
pipeline.optimize_for_production(
    target_max_text_length=3000,  # Characters per chunk
    target_chunk_overlap=50        # Overlap between chunks
)
```

### Usage Example

```python
from template.pipelines.tts_pipeline import TTSPipeline

# Initialize pipeline
pipeline = TTSPipeline()

# Synthesize long text (automatically chunked)
long_text = "Very long text..." * 1000
result = pipeline.synthesize(long_text, language="en")

# Access synthesis metadata
print(f"Audio duration: {result.audio_duration:.2f}s")
print(f"Processing time: {result.processing_time:.2f}s")
print(f"Chunked: {result.metadata['chunked']}")
```

## 🌐 Enhanced Translation Pipeline

### New Features

#### 1. **Large Document Handling**
- **Text Chunking**: Automatic splitting of long texts
- **Configurable Chunk Sizes**: Adjustable character limits per chunk
- **Overlap Management**: Character overlap for context preservation

#### 2. **Production Optimization**
- **Memory Management**: Automatic cleanup and garbage collection
- **Performance Monitoring**: Translation speed and memory usage tracking
- **Configurable Settings**: Adjustable chunk sizes and overlap

#### 3. **Robust Error Handling**
- **Fallback Models**: Multiple model options with automatic fallback
- **Chunk Recovery**: Continues processing even if individual chunks fail
- **Error Reporting**: Detailed error information for debugging

### Usage Example

```python
from template.pipelines.translation_pipeline import TranslationPipeline

# Initialize pipeline
pipeline = TranslationPipeline()

# Translate long text (automatically chunked)
long_text = "Very long text..." * 500
translated_text, processing_time = pipeline.translate_text(
    long_text, "en", "es"
)

# Optimize for production
pipeline.optimize_for_production(
    target_max_chunk_size=600,
    target_chunk_overlap=20
)
```

## 🏭 Production Readiness Features

### 1. **Memory Management**
- **Automatic Cleanup**: CUDA cache clearing and garbage collection
- **Memory Monitoring**: Real-time usage tracking with psutil
- **Configurable Limits**: Adjustable memory thresholds

### 2. **Performance Monitoring**
- **Processing Statistics**: Comprehensive performance metrics
- **Resource Usage**: CPU and memory monitoring
- **Optimization Tools**: Built-in optimization methods

### 3. **Scalability**
- **Chunking Strategies**: Automatic handling of large inputs
- **Parallel Processing**: Concurrent processing where applicable
- **Resource Optimization**: Configurable settings for different environments

### 4. **Error Handling**
- **Graceful Degradation**: Continues processing despite individual failures
- **Error Recovery**: Automatic retry and fallback mechanisms
- **Detailed Logging**: Comprehensive error reporting and debugging

## 📊 Performance Monitoring

### Available Metrics

#### Transcription Pipeline
- Total files processed
- Total audio duration
- Average processing speed (seconds/audio)
- Memory usage samples
- Chunking statistics

#### TTS Pipeline
- Total syntheses
- Total text length processed
- Average processing speed (characters/second)
- Memory usage tracking
- Chunking performance

#### Translation Pipeline
- Total translations
- Total text length
- Average processing speed
- Memory usage monitoring
- Chunk processing statistics

### Example Monitoring

```python
# Get performance stats from any pipeline
stats = pipeline.get_performance_stats()

# Monitor memory usage
memory_samples = stats['memory_usage_samples']
current_memory = memory_samples[-1] if memory_samples else 0
print(f"Current memory usage: {current_memory:.2f}GB")

# Monitor processing speed
speed = stats['average_processing_speed']
print(f"Average processing speed: {speed:.2f}")
```

## ⚙️ Configuration Options

### Transcription Pipeline
```python
TranscriptionPipeline(
    model_name="openai/whisper-tiny",  # Whisper model
    chunk_duration=30.0,               # Seconds per chunk
    max_memory_gb=4.0                  # Memory limit
)
```

### TTS Pipeline
```python
TTSPipeline(
    model_name="tts_models/multilingual/multi-dataset/your_tts",
    # Automatic production settings
)
```

### Translation Pipeline
```python
TranslationPipeline(
    model_name="t5-small",  # Translation model
    # Automatic fallback models
)
```

## 🚀 Getting Started

### 1. **Install Dependencies**
```bash
pip install psutil transformers torch librosa soundfile
```

### 2. **Basic Usage**
```python
# Import enhanced pipelines
from template.pipelines.transcription_pipeline import TranscriptionPipeline
from template.pipelines.tts_pipeline import TTSPipeline
from template.pipelines.translation_pipeline import TranslationPipeline

# Initialize with production settings
transcription = TranscriptionPipeline(chunk_duration=15.0, max_memory_gb=2.0)
tts = TTSPipeline()
translation = TranslationPipeline()
```

### 3. **Production Optimization**
```python
# Optimize all pipelines for production
transcription.optimize_for_production(target_memory_gb=1.0, target_chunk_duration=10.0)
tts.optimize_for_production(target_max_text_length=2000, target_chunk_overlap=30)
translation.optimize_for_production(target_max_chunk_size=600, target_chunk_overlap=20)
```

### 4. **Monitor Performance**
```python
# Get performance statistics
transcription_stats = transcription.get_performance_stats()
tts_stats = tts.get_performance_stats()
translation_stats = translation.get_performance_stats()
```

## 🔧 Advanced Configuration

### Custom Chunking Strategies
```python
# Custom transcription chunking
pipeline = TranscriptionPipeline(
    chunk_duration=20.0,      # 20-second chunks
    max_memory_gb=1.5         # 1.5GB memory limit
)

# Custom TTS chunking
tts_pipeline = TTSPipeline()
tts_pipeline.max_text_length = 4000      # 4K characters per chunk
tts_pipeline.chunk_overlap = 200         # 200 character overlap
```

### Memory Management
```python
# Force memory cleanup
pipeline._cleanup_memory()

# Monitor memory usage
memory_gb = pipeline._get_memory_usage()
print(f"Current memory: {memory_gb:.2f}GB")
```

## 📈 Performance Benchmarks

### Transcription Pipeline
- **Small Audio (< 30s)**: Single chunk, ~2-5 seconds processing
- **Medium Audio (1-5 min)**: Chunked, ~10-30 seconds processing
- **Large Audio (5+ min)**: Parallel chunked, ~1-5 minutes processing

### TTS Pipeline
- **Short Text (< 5K chars)**: Single synthesis, ~5-15 seconds
- **Long Text (5K+ chars)**: Chunked synthesis, ~20-60 seconds

### Translation Pipeline
- **Short Text (< 1K chars)**: Single translation, ~2-8 seconds
- **Long Text (1K+ chars)**: Chunked translation, ~10-30 seconds

## 🐛 Troubleshooting

### Common Issues

#### 1. **Memory Errors**
```python
# Reduce memory usage
pipeline.optimize_for_production(target_memory_gb=1.0)
pipeline._cleanup_memory()
```

#### 2. **Chunking Issues**
```python
# Adjust chunk sizes
pipeline.chunk_duration = 20.0  # Smaller chunks
pipeline.max_text_length = 2000  # Smaller text chunks
```

#### 3. **Performance Issues**
```python
# Monitor performance
stats = pipeline.get_performance_stats()
print(f"Processing speed: {stats['average_processing_speed']}")
```

### Debug Mode
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Get detailed performance info
stats = pipeline.get_performance_stats()
print(f"Memory samples: {stats['memory_usage_samples']}")
```

## 🔮 Future Enhancements

### Planned Features
- **GPU Memory Pooling**: Shared GPU memory across pipelines
- **Distributed Processing**: Multi-node pipeline execution
- **Adaptive Chunking**: Dynamic chunk size based on content
- **Real-time Streaming**: Live audio/video processing
- **Advanced Caching**: Intelligent result caching and reuse

### Contributing
- **Performance Improvements**: Optimize chunking algorithms
- **New Output Formats**: Additional transcript formats
- **Memory Management**: Enhanced resource optimization
- **Error Handling**: Improved error recovery mechanisms

## 📚 Additional Resources

### Documentation
- [Whisper Model Documentation](https://huggingface.co/docs/transformers/model_doc/whisper)
- [Coqui TTS Documentation](https://tts.readthedocs.io/)
- [HuggingFace Transformers](https://huggingface.co/docs/transformers/)

### Examples
- `test_enhanced_pipelines.py` - Comprehensive test suite
- `template/pipelines/` - Pipeline source code
- Integration examples in miner and validator

### Support
- Check logs for detailed error information
- Use performance monitoring for optimization
- Adjust configuration parameters as needed
- Monitor memory usage in production environments

---

**Note**: These enhanced pipelines are designed for production use with large files and high-throughput scenarios. Always test with your specific use case and adjust configuration parameters accordingly.
