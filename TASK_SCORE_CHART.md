# 📊 Task Score Chart & Performance Tiers

## 🎯 **Task-Specific Scoring Matrix**

### **1. Audio Transcription Tasks**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUDIO TRANSCRIPTION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Component        │ Weight │ Scoring Criteria           │ Perfect Score │
├─────────────────────────────────────────────────────────────────────────────┤
│ Accuracy         │  65%   │ Text similarity to validator│     1.0      │
│ Speed            │  25%   │ Processing time efficiency │     1.0      │
│ Quality          │  10%   │ Response structure         │     1.0      │
├─────────────────────────────────────────────────────────────────────────────┤
│ TOTAL WEIGHT     │ 100%   │                            │     1.0      │
└─────────────────────────────────────────────────────────────────────────────┘

Optimal Processing Time: 2.0 seconds
Max Acceptable Time: 10.0 seconds
Quality Requirements: transcript, confidence, language, timestamps
```

### **2. Video Transcription Tasks**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          VIDEO TRANSCRIPTION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Component        │ Weight │ Scoring Criteria           │ Perfect Score │
├─────────────────────────────────────────────────────────────────────────────┤
│ Accuracy         │  65%   │ Text similarity to validator│     1.0      │
│ Speed            │  25%   │ Processing time efficiency │     1.0      │
│ Quality          │  10%   │ Response structure         │     1.0      │
├─────────────────────────────────────────────────────────────────────────────┤
│ TOTAL WEIGHT     │ 100%   │                            │     1.0      │
└─────────────────────────────────────────────────────────────────────────────┘

Optimal Processing Time: 5.0 seconds
Max Acceptable Time: 25.0 seconds
Quality Requirements: transcript, confidence, language, timestamps, video_metadata
```

### **3. Text-to-Speech (TTS) Tasks**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TEXT-TO-SPEECH                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Component        │ Weight │ Scoring Criteria           │ Perfect Score │
├─────────────────────────────────────────────────────────────────────────────┤
│ Accuracy         │  50%   │ Audio quality & faithfulness│     1.0      │
│ Speed            │  20%   │ Generation time            │     1.0      │
│ Quality          │  30%   │ Audio format & metadata    │     1.0      │
├─────────────────────────────────────────────────────────────────────────────┤
│ TOTAL WEIGHT     │ 100%   │                            │     1.0      │
└─────────────────────────────────────────────────────────────────────────────┘

Optimal Processing Time: 3.0 seconds
Max Acceptable Time: 15.0 seconds
Quality Requirements: audio_data, duration, format, sample_rate, bit_depth
```

### **4. Text Summarization Tasks**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            TEXT SUMMARIZATION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ Component        │ Weight │ Scoring Criteria           │ Perfect Score │
├─────────────────────────────────────────────────────────────────────────────┤
│ Accuracy         │  60%   │ Content preservation      │     1.0      │
│ Speed            │  20%   │ Processing time           │     1.0      │
│ Quality          │  20%   │ Summary structure         │     1.0      │
├─────────────────────────────────────────────────────────────────────────────┤
│ TOTAL WEIGHT     │ 100%   │                            │     1.0      │
└─────────────────────────────────────────────────────────────────────────────┘

Optimal Processing Time: 5.0 seconds
Max Acceptable Time: 25.0 seconds
Quality Requirements: summary, key_points, length_ratio, readability
```

### **5. Text Translation Tasks**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             TEXT TRANSLATION                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Component        │ Weight │ Scoring Criteria           │ Perfect Score │
├─────────────────────────────────────────────────────────────────────────────┤
│ Accuracy         │  70%   │ Translation quality        │     1.0      │
│ Speed            │  20%   │ Processing time            │     1.0      │
│ Quality          │  10%   │ Output format              │     1.0      │
├─────────────────────────────────────────────────────────────────────────────┤
│ TOTAL WEIGHT     │ 100%   │                            │     1.0      │
└─────────────────────────────────────────────────────────────────────────────┘

Optimal Processing Time: 4.0 seconds
Max Acceptable Time: 20.0 seconds
Quality Requirements: translated_text, source_language, target_language
```

### **6. Document Translation Tasks**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DOCUMENT TRANSLATION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ Component        │ Weight │ Scoring Criteria           │ Perfect Score │
├─────────────────────────────────────────────────────────────────────────────┤
│ Accuracy         │  70%   │ Translation quality        │     1.0      │
│ Speed            │  20%   │ Processing time            │     1.0      │
│ Quality          │  10%   │ Document format            │     1.0      │
├─────────────────────────────────────────────────────────────────────────────┤
│ TOTAL WEIGHT     │ 100%   │                            │     1.0      │
└─────────────────────────────────────────────────────────────────────────────┘

Optimal Processing Time: 8.0 seconds
Max Acceptable Time: 40.0 seconds
Quality Requirements: translated_document, format_preservation, metadata
```

## 🏆 **Performance Tiers & Point Allocation**

### **Tier 1: Elite Performers (450-500 points)**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ELITE PERFORMERS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Score Range      │ 450-500 points (90-100% of max)                        │
│ Requirements     │ >90% accuracy, <1.5x optimal speed, >90% quality      │
│ Weight Allocation│ Maximum network weight                                  │
│ Task Priority    │ Highest priority assignment                            │
│ Stake Rewards    │ Maximum stake-based rewards                            │
│ Network Status   │ Top-tier miner, network backbone                       │
└─────────────────────────────────────────────────────────────────────────────┘

Examples:
• Miner 49: 482.0 points (96.4% performance)
• Miner 48: 472.5 points (94.5% performance)
• Miner 50: 449.0 points (89.8% performance) - Borderline Elite
```

### **Tier 2: High Performers (350-449 points)**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HIGH PERFORMERS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Score Range      │ 350-449 points (70-89.8% of max)                       │
│ Requirements     │ 80-90% accuracy, <2x optimal speed, >80% quality      │
│ Weight Allocation│ High network weight                                    │
│ Task Priority    │ High priority assignment                               │
│ Stake Rewards    │ High stake-based rewards                               │
│ Network Status   │ Reliable performer, consistent quality                 │
└─────────────────────────────────────────────────────────────────────────────┘

Examples:
• Miner 51: 420.0 points (84% performance)
• Miner 52: 380.0 points (76% performance)
• Miner 53: 350.0 points (70% performance)
```

### **Tier 3: Competent Performers (250-349 points)**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            COMPETENT PERFORMERS                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ Score Range      │ 250-349 points (50-69.8% of max)                       │
│ Requirements     │ 70-80% accuracy, <3x optimal speed, >70% quality      │
│ Weight Allocation│ Moderate network weight                                │
│ Task Priority    │ Medium priority assignment                             │
│ Stake Rewards    │ Basic stake-based rewards                              │
│ Network Status   │ Adequate performer, room for improvement               │
└─────────────────────────────────────────────────────────────────────────────┘

Examples:
• Miner 54: 320.0 points (64% performance)
• Miner 55: 280.0 points (56% performance)
• Miner 56: 250.0 points (50% performance)
```

### **Tier 4: Basic Performers (150-249 points)**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BASIC PERFORMERS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Score Range      │ 150-249 points (30-49.8% of max)                       │
│ Requirements     │ 60-70% accuracy, <5x optimal speed, >60% quality      │
│ Weight Allocation│ Low network weight                                     │
│ Task Priority    │ Low priority assignment                                │
│ Stake Rewards    │ Minimal stake-based rewards                            │
│ Network Status   │ Below average, needs improvement                      │
└─────────────────────────────────────────────────────────────────────────────┘

Examples:
• Miner 57: 200.0 points (40% performance)
• Miner 58: 180.0 points (36% performance)
• Miner 59: 150.0 points (30% performance)
```

### **Tier 5: Underperformers (<150 points)**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              UNDERPERFORMERS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Score Range      │ 0-149 points (0-29.8% of max)                          │
│ Requirements     │ <60% accuracy, >5x optimal speed, <60% quality        │
│ Weight Allocation│ Minimal or zero network weight                         │
│ Task Priority    │ No task assignment                                     │
│ Stake Rewards    │ No stake-based rewards                                 │
│ Network Status   │ Poor performer, potential removal                      │
└─────────────────────────────────────────────────────────────────────────────┘

Examples:
• Miner 60: 100.0 points (20% performance)
• Miner 61: 50.0 points (10% performance)
• Miner 62: 0.0 points (0% performance - failed)
```

## 📈 **Score Calculation Examples**

### **Example 1: Perfect Transcription Performance**
```python
# Task: Audio Transcription
# Miner Response: Perfect match, fast processing, complete metadata

accuracy_score = 1.0      # Perfect text match
speed_score = 1.0         # 1.8s vs 2.0s optimal (faster)
quality_score = 1.0       # All required fields present

# Weighted calculation:
combined_score = (0.65 * 1.0) + (0.25 * 1.0) + (0.10 * 1.0)
combined_score = 0.65 + 0.25 + 0.10 = 1.0

# Final score (0-500 scale):
final_score = 1.0 * 500 = 500.0 points
tier = "Elite Performer"
```

### **Example 2: Good Summarization Performance**
```python
# Task: Text Summarization
# Miner Response: Good content, acceptable speed, complete structure

accuracy_score = 0.85     # Good content preservation
speed_score = 0.8         # 6.25s vs 5.0s optimal
quality_score = 0.9       # Complete summary with key points

# Weighted calculation:
combined_score = (0.60 * 0.85) + (0.20 * 0.8) + (0.20 * 0.9)
combined_score = 0.51 + 0.16 + 0.18 = 0.85

# Final score (0-500 scale):
final_score = 0.85 * 500 = 425.0 points
tier = "High Performer"
```

### **Example 3: Average Translation Performance**
```python
# Task: Text Translation
# Miner Response: Acceptable translation, slow processing, basic quality

accuracy_score = 0.75     # Acceptable translation quality
speed_score = 0.6         # 6.67s vs 4.0s optimal
quality_score = 0.8       # Basic output format

# Weighted calculation:
combined_score = (0.70 * 0.75) + (0.20 * 0.6) + (0.10 * 0.8)
combined_score = 0.525 + 0.12 + 0.08 = 0.725

# Final score (0-500 scale):
final_score = 0.725 * 500 = 362.5 points
tier = "Competent Performer"
```

### **Example 4: Poor TTS Performance**
```python
# Task: Text-to-Speech
# Miner Response: Low quality audio, slow processing, incomplete metadata

accuracy_score = 0.6      # Low audio quality
speed_score = 0.3         # 10.0s vs 3.0s optimal (too slow)
quality_score = 0.5       # Missing required fields

# Weighted calculation:
combined_score = (0.50 * 0.6) + (0.20 * 0.3) + (0.30 * 0.5)
combined_score = 0.30 + 0.06 + 0.15 = 0.51

# Final score (0-500 scale):
final_score = 0.51 * 500 = 255.0 points
tier = "Competent Performer" (barely)
```

## 🔄 **Dynamic Score Adjustment**

### **Performance Decay Over Time**
```python
# Recent performance gets higher weight
recent_weight = 0.7
historical_weight = 0.3

# Calculate current effective score:
current_score = (recent_performance * recent_weight) + 
                (historical_performance * historical_weight)

# Example:
# Miner has recent score: 450, historical score: 400
# Current effective score: (450 * 0.7) + (400 * 0.3) = 315 + 120 = 435
```

### **Stake Integration**
```python
# Stake provides base score but doesn't dominate
stake_score = min(1.0, miner_stake / max_network_stake)
performance_score = calculated_performance_score

# Final score with stake consideration:
final_score = (performance_score * 0.8) + (stake_score * 0.2)

# Example:
# Miner has 90% performance and 80% stake ratio
# Final score: (0.90 * 0.8) + (0.80 * 0.2) = 0.72 + 0.16 = 0.88
```

## 📊 **Network Performance Metrics**

### **Overall Network Health**
```python
# Calculate network-wide metrics:
network_metrics = {
    'total_miners': len(active_miners),
    'elite_performers': len([m for m in miners if m.score >= 450]),
    'high_performers': len([m for m in miners if 350 <= m.score < 450]),
    'competent_performers': len([m for m in miners if 250 <= m.score < 350]),
    'basic_performers': len([m for m in miners if 150 <= m.score < 250]),
    'underperformers': len([m for m in miners if m.score < 150]),
    'average_score': sum(m.score for m in miners) / len(miners),
    'score_standard_deviation': calculate_std_dev([m.score for m in miners])
}
```

### **Task Completion Rates**
```python
# Track task completion by tier:
completion_rates = {
    'elite': {'assigned': 100, 'completed': 98, 'rate': 0.98},
    'high': {'assigned': 150, 'completed': 135, 'rate': 0.90},
    'competent': {'assigned': 200, 'completed': 160, 'rate': 0.80},
    'basic': {'assigned': 100, 'completed': 60, 'rate': 0.60},
    'underperformer': {'assigned': 50, 'completed': 10, 'rate': 0.20}
}
```

## 🎯 **Reward Distribution Strategy**

### **Weight Allocation by Tier**
```python
# Network weight distribution:
weight_allocation = {
    'elite_performers': 0.40,      # 40% of total network weight
    'high_performers': 0.35,       # 35% of total network weight
    'competent_performers': 0.20,  # 20% of total network weight
    'basic_performers': 0.05,      # 5% of total network weight
    'underperformers': 0.00        # 0% of total network weight
}
```

### **Task Assignment Priority**
```python
# Task assignment by tier:
task_assignment = {
    'elite_performers': {'priority': 1, 'max_concurrent': 3, 'load_factor': 1.0},
    'high_performers': {'priority': 2, 'max_concurrent': 2, 'load_factor': 0.8},
    'competent_performers': {'priority': 3, 'max_concurrent': 2, 'load_factor': 0.6},
    'basic_performers': {'priority': 4, 'max_concurrent': 1, 'load_factor': 0.4},
    'underperformers': {'priority': 5, 'max_concurrent': 0, 'load_factor': 0.0}
}
```

---

## 📝 **Summary**

This comprehensive scoring system ensures:

1. **Fair Competition**: Performance-based rewards, not stake-based
2. **Quality Assurance**: Accuracy is weighted highest for most tasks
3. **Efficiency Incentives**: Speed is rewarded appropriately
4. **Reliability Standards**: Quality checks prevent poor responses
5. **Network Health**: Load balancing prevents miner overload
6. **Continuous Improvement**: Performance tracking enables optimization

The system automatically adapts to network conditions and miner performance, creating a meritocratic environment where the best miners receive the most rewards while maintaining network stability and quality.
