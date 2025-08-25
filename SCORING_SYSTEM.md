# 🏆 Bittensor AI Inferencing Subnet Scoring System

## 🎯 **Reward Mechanism Overview**

### **Core Principles**
- **Merit-Based Rewards**: Miners are rewarded based on actual performance, not just stake
- **Multi-Dimensional Evaluation**: Considers accuracy, speed, and quality simultaneously
- **Task-Specific Optimization**: Different weights for different AI task types
- **Performance Capping**: Maximum 500 points per miner (Bittensor requirement)
- **Cumulative Tracking**: Builds performance over multiple tasks for fair assessment

### **Reward Flow**
```
Task Completion → Validator Execution → Performance Comparison → Score Calculation → Weight Setting → Blockchain Update
```

## 📊 **Task-Specific Scoring Weights**

### **1. Transcription Tasks (Audio & Video)**
```
Accuracy Score:    65%  ← Most important for speech recognition
Speed Score:       25%  ← Processing time efficiency
Quality Score:     10%  ← Response structure completeness
```

**Why These Weights?**
- **Accuracy is critical** for transcription - users need correct text
- **Speed matters** for real-time applications
- **Quality ensures** proper metadata (confidence, language, timestamps)

### **2. Text-to-Speech (TTS)**
```
Accuracy Score:    50%  ← Audio quality and text faithfulness
Speed Score:       20%  ← Generation time
Quality Score:     30%  ← Audio format, duration, metadata
```

**Why These Weights?**
- **Quality is important** for audio output and user experience
- **Accuracy ensures** proper pronunciation and intonation
- **Speed matters** for interactive applications

### **3. Summarization Tasks**
```
Accuracy Score:    60%  ← Content preservation and key point extraction
Speed Score:       20%  ← Processing time for long texts
Quality Score:     20%  ← Summary structure and readability
```

**Why These Weights?**
- **Accuracy ensures** important information isn't lost
- **Quality provides** well-structured, readable summaries
- **Speed handles** long document processing efficiently

### **4. Translation Tasks (Text & Document)**
```
Accuracy Score:    70%  ← Translation quality and faithfulness
Speed Score:       20%  ← Processing time for language conversion
Quality Score:     10%  ← Output format and metadata
```

**Why These Weights?**
- **Accuracy is paramount** for translation - wrong translations are useless
- **Speed handles** document processing efficiently
- **Quality ensures** proper formatting and language codes

## 🎯 **Detailed Scoring Breakdown**

### **Accuracy Score Calculation (0.0 - 1.0)**

#### **Transcription Accuracy**
```python
# Uses difflib.SequenceMatcher for text similarity
similarity = SequenceMatcher(None, validator_transcript.lower(), miner_transcript.lower()).ratio()
accuracy_score = similarity

# Example:
# Validator: "Hello world, how are you today?"
# Miner:    "Hello world, how are you today?"
# Accuracy: 1.0 (100% match)

# Validator: "Hello world, how are you today?"
# Miner:    "Hello world, how are you today!"
# Accuracy: 0.96 (96% match - punctuation difference)
```

#### **Summarization Accuracy**
```python
# Compares key concepts and information preservation
# Uses advanced NLP similarity metrics
# Considers:
# - Key point extraction
# - Information density
# - Semantic similarity
# - Length appropriateness
```

#### **Translation Accuracy**
```python
# Compares translated text with validator translation
# Considers:
# - Semantic meaning preservation
# - Grammar correctness
# - Cultural appropriateness
# - Technical term accuracy
```

### **Speed Score Calculation (0.0 - 1.0)**

#### **Optimal Processing Times**
```python
optimal_times = {
    'transcription': 2.0,      # 2 seconds = perfect score
    'video_transcription': 5.0, # 5 seconds = perfect score
    'tts': 3.0,               # 3 seconds = perfect score
    'summarization': 5.0,      # 5 seconds = perfect score
    'translation': 4.0         # 4 seconds = perfect score
}
```

#### **Speed Scoring Logic**
```python
if processing_time <= optimal_time:
    return 1.0        # Perfect score
elif processing_time <= optimal_time * 2:
    return 0.8        # Good score (within 2x optimal)
elif processing_time <= optimal_time * 5:
    return 0.6        # Acceptable score (within 5x optimal)
else:
    return 0.3        # Poor score (too slow)
```

### **Quality Score Calculation (0.0 - 1.0)**

#### **Response Structure Requirements**
```python
# Transcription Quality Checks:
quality_checks = {
    'transcript': 0.4,      # Main transcript content
    'confidence': 0.3,      # Confidence score
    'language': 0.2,        # Language detection
    'timestamps': 0.1       # Time markers (if available)
}

# TTS Quality Checks:
quality_checks = {
    'audio_data': 0.7,      # Audio output
    'duration': 0.2,        # Audio length
    'format': 0.1           # Audio format
}

# Summarization Quality Checks:
quality_checks = {
    'summary': 0.6,         # Main summary text
    'key_points': 0.3,      # Key concepts
    'length': 0.1           # Appropriate length
}
```

## 🏆 **Performance Tiers & Rewards**

### **Tier 1: Elite Performers (450-500 points)**
- **Requirements**: >90% accuracy, <1.5x optimal speed, >90% quality
- **Reward**: Maximum weight allocation
- **Benefits**: Priority task assignment, higher stake rewards

### **Tier 2: High Performers (350-449 points)**
- **Requirements**: 80-90% accuracy, <2x optimal speed, >80% quality
- **Reward**: High weight allocation
- **Benefits**: Regular task assignment, good stake rewards

### **Tier 3: Competent Performers (250-349 points)**
- **Requirements**: 70-80% accuracy, <3x optimal speed, >70% quality
- **Reward**: Moderate weight allocation
- **Benefits**: Occasional task assignment, basic stake rewards

### **Tier 4: Basic Performers (150-249 points)**
- **Requirements**: 60-70% accuracy, <5x optimal speed, >60% quality
- **Reward**: Low weight allocation
- **Benefits**: Limited task assignment, minimal stake rewards

### **Tier 5: Underperformers (<150 points)**
- **Requirements**: <60% accuracy, >5x optimal speed, <60% quality
- **Reward**: Minimal or zero weight allocation
- **Benefits**: No task assignment, no stake rewards

## 📈 **Cumulative Performance Tracking**

### **Score Accumulation**
```python
# Miner performance over multiple tasks:
miner_performance = {
    'miner_uid': {
        'total_score': 1250.0,        # Sum of all task scores
        'task_count': 5,              # Number of tasks completed
        'avg_score_per_task': 250.0,  # Average performance
        'task_scores': {              # Individual task breakdown
            'task_1': 450.0,          # Elite performance
            'task_2': 380.0,          # High performance
            'task_3': 420.0,          # High performance
            'task_4': 0.0,            # Failed task
            'task_5': 0.0             # Failed task
        }
    }
}
```

### **Weight Calculation**
```python
# Final weight = min(total_score, 500.0)
# This ensures compliance with Bittensor's 500-point cap

for miner_uid, performance in miner_performance.items():
    total_score = performance['total_score']
    capped_score = min(total_score, 500.0)
    final_weight = capped_score
```

## 🔄 **Dynamic Weight Adjustment**

### **Performance Decay**
```python
# Recent performance gets higher weight
recent_performance_weight = 0.7
historical_performance_weight = 0.3

# Performance over time:
current_weight = (recent_score * recent_performance_weight) + 
                (historical_score * historical_performance_weight)
```

### **Stake Integration**
```python
# Stake provides base score but doesn't dominate
stake_score = min(1.0, miner_stake / max_network_stake)
final_score = (performance_score * 0.8) + (stake_score * 0.2)
```

## 🎯 **Task Assignment Strategy**

### **Performance-Based Selection**
```python
# Miners are selected based on:
selection_criteria = {
    'performance_score': 0.6,     # Historical performance
    'current_load': 0.2,          # Current capacity
    'specialization': 0.1,        # Task type expertise
    'stake': 0.1                  # Network contribution
}
```

### **Load Balancing**
```python
# Prevents overloading top performers
max_concurrent_tasks = 3
if miner.current_load >= max_concurrent_tasks:
    availability_score = 0.0
else:
    availability_score = 1.0 - (miner.current_load / max_concurrent_tasks)
```

## 📊 **Reward Distribution Example**

### **Scenario: 5 Miners, 1 Task**
```python
# Task: Audio Transcription (English)
# Validator execution time: 2.1 seconds
# Validator output: "Hello world, how are you today?"

miner_results = {
    'miner_48': {
        'transcript': "Hello world, how are you today?",
        'processing_time': 2.5,
        'confidence': 0.95,
        'language': 'en'
    },
    'miner_49': {
        'transcript': "Hello world, how are you today!",
        'processing_time': 1.8,
        'confidence': 0.92,
        'language': 'en'
    },
    'miner_50': {
        'transcript': "Hello world, how are you today?",
        'processing_time': 3.2,
        'confidence': 0.98,
        'language': 'en'
    }
}

# Score calculations:
scores = {
    'miner_48': {
        'accuracy': 1.0,      # Perfect match
        'speed': 0.8,         # 2.5s vs 2.0s optimal
        'quality': 0.95,      # Has all required fields
        'combined': 0.65*1.0 + 0.25*0.8 + 0.10*0.95 = 0.945
    },
    'miner_49': {
        'accuracy': 0.96,     # Minor punctuation difference
        'speed': 1.0,         # 1.8s vs 2.0s optimal (faster)
        'quality': 0.92,      # Has all required fields
        'combined': 0.65*0.96 + 0.25*1.0 + 0.10*0.92 = 0.964
    },
    'miner_50': {
        'accuracy': 1.0,      # Perfect match
        'speed': 0.6,         # 3.2s vs 2.0s optimal
        'quality': 0.98,      # Has all required fields
        'combined': 0.65*1.0 + 0.25*0.6 + 0.10*0.98 = 0.898
    }
}

# Final scores (0-500 scale):
final_scores = {
    'miner_48': 0.945 * 500 = 472.5,
    'miner_49': 0.964 * 500 = 482.0,  # Winner!
    'miner_50': 0.898 * 500 = 449.0
}
```

## 🚀 **Continuous Improvement**

### **Performance Monitoring**
- **Real-time tracking** of all miner performance metrics
- **Automatic alerts** for performance degradation
- **Historical analysis** for trend identification

### **Reward Optimization**
- **Dynamic weight adjustment** based on network performance
- **Task difficulty scaling** for fair competition
- **Specialization bonuses** for expert miners

### **Network Health**
- **Load balancing** to prevent miner overload
- **Quality assurance** through validator verification
- **Stake distribution** optimization for network stability

---

## 📝 **Summary**

This scoring system creates a **fair, transparent, and efficient** reward mechanism that:

1. **Rewards Quality**: Miners with better accuracy get higher scores
2. **Incentivizes Speed**: Faster processing is rewarded appropriately
3. **Ensures Reliability**: Quality checks prevent poor responses
4. **Maintains Fairness**: Performance-based rewards, not just stake
5. **Promotes Competition**: Continuous improvement through ranking
6. **Complies with Bittensor**: Respects the 500-point cap requirement

The system automatically adapts to network conditions and miner performance, ensuring that the best miners receive the most rewards while maintaining network stability and quality.
