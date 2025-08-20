#!/usr/bin/env python3
"""
Test script for the enhanced miner tracking and load balancing system
"""

import sys
import os
import time
import asyncio
import requests
import json

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from template.validator.miner_tracker import MinerTracker, MinerMetrics


class MockConfig:
    """Mock configuration for testing"""
    def __init__(self):
        self.testing = True


def test_miner_metrics():
    """Test MinerMetrics class functionality"""
    print("🧪 Testing MinerMetrics class...")
    
    # Create a miner
    miner = MinerMetrics(uid=1, hotkey="test_hotkey_123", stake=1000.0)
    
    # Test initial state
    assert miner.uid == 1
    assert miner.hotkey == "test_hotkey_123"
    assert miner.stake == 1000.0
    assert miner.total_tasks == 0
    assert miner.current_load == 0
    
    # Test task assignment
    assert miner.assign_task("transcription") == True
    assert miner.current_load == 1
    assert miner.assign_task("tts") == True
    assert miner.current_load == 2
    
    # Test max capacity
    for _ in range(3):  # Should fail after 3 more
        miner.assign_task("summarization")
    
    assert miner.current_load == 5  # Max capacity
    assert miner.assign_task("transcription") == False  # Should fail
    
    # Test task completion
    miner.update_task_completion("transcription", True, 2.5)
    assert miner.total_tasks == 1
    assert miner.successful_tasks == 1
    assert miner.current_load == 4  # Reduced load
    assert miner.average_processing_time == 2.5
    
    # Test performance score
    score = miner.get_performance_score("transcription")
    assert 0.0 <= score <= 1.0
    
    print("✅ MinerMetrics tests passed!")


def test_miner_tracker():
    """Test MinerTracker class functionality"""
    print("🧪 Testing MinerTracker class...")
    
    config = MockConfig()
    tracker = MinerTracker(config)
    
    # Test miner registration
    tracker.register_miner(1, "hotkey1", 1000.0)
    tracker.register_miner(2, "hotkey2", 2000.0)
    tracker.register_miner(3, "hotkey3", 500.0)
    
    assert len(tracker.miners) == 3
    assert 1 in tracker.miners
    assert 2 in tracker.miners
    assert 3 in tracker.miners
    
    # Test available miners
    available = tracker.get_available_miners()
    assert len(available) == 3
    
    # Test miner selection for task
    selected = tracker.select_miners_for_task("transcription", required_count=2)
    assert len(selected) == 2
    
    # Test load tracking
    miner1 = tracker.miners[1]
    assert miner1.current_load == 1  # Assigned one task
    
    # Test task completion
    tracker.update_task_result(1, "transcription", True, 3.0)
    assert miner1.current_load == 0  # Task completed
    assert miner1.total_tasks == 1
    assert miner1.successful_tasks == 1
    
    # Test performance ranking
    rankings = tracker.get_performance_ranking()
    assert len(rankings) == 3
    
    # Test stats
    stats = tracker.get_miner_stats()
    assert stats['total_miners'] == 3
    assert stats['available_miners'] == 3
    
    print("✅ MinerTracker tests passed!")


def test_load_balancing():
    """Test load balancing functionality"""
    print("🧪 Testing load balancing...")
    
    config = MockConfig()
    tracker = MinerTracker(config)
    
    # Register miners with different capacities
    tracker.register_miner(1, "hotkey1", 1000.0)
    tracker.register_miner(2, "hotkey2", 2000.0)
    tracker.register_miner(3, "hotkey3", 500.0)
    tracker.register_miner(4, "hotkey4", 1500.0)
    tracker.register_miner(5, "hotkey5", 800.0)
    
    # Simulate some miners being busy
    tracker.miners[1].current_load = 3  # 60% loaded
    tracker.miners[2].current_load = 4  # 80% loaded
    tracker.miners[3].current_load = 1  # 20% loaded
    tracker.miners[4].current_load = 5  # 100% loaded (maxed out)
    tracker.miners[5].current_load = 0  # 0% loaded
    
    # Test task distribution
    selected1 = tracker.select_miners_for_task("transcription", required_count=3)
    print(f"   Selected for transcription: {selected1}")
    
    # Verify that overloaded miners are avoided
    assert 4 not in selected1  # 100% loaded miner should be avoided
    
    # Test multiple task types
    selected2 = tracker.select_miners_for_task("tts", required_count=2)
    print(f"   Selected for TTS: {selected2}")
    
    selected3 = tracker.select_miners_for_task("summarization", required_count=2)
    print(f"   Selected for summarization: {selected3}")
    
    # Check load distribution
    for uid in tracker.miners:
        miner = tracker.miners[uid]
        print(f"   UID {uid}: Load {miner.current_load}/{miner.max_concurrent_tasks}")
    
    print("✅ Load balancing tests passed!")


def test_performance_tracking():
    """Test performance tracking and scoring"""
    print("🧪 Testing performance tracking...")
    
    config = MockConfig()
    tracker = MinerTracker(config)
    
    # Register miners
    tracker.register_miner(1, "hotkey1", 1000.0)
    tracker.register_miner(2, "hotkey2", 2000.0)
    
    # Simulate task performance
    # Miner 1: Good performance
    for i in range(10):
        success = i < 8  # 80% success rate
        time = 2.0 if success else 15.0  # Fast when successful, slow when failed
        tracker.update_task_result(1, "transcription", success, time)
    
    # Miner 2: Poor performance
    for i in range(10):
        success = i < 3  # 30% success rate
        time = 8.0 if success else 20.0  # Always slow
        tracker.update_task_result(2, "transcription", success, time)
    
    # Test performance scores
    score1 = tracker.miners[1].get_performance_score("transcription")
    score2 = tracker.miners[2].get_performance_score("transcription")
    
    print(f"   Miner 1 performance score: {score1:.3f}")
    print(f"   Miner 2 performance score: {score2:.3f}")
    
    # Better miner should have higher score
    assert score1 > score2
    
    # Test task type specialization
    tracker.update_task_result(1, "tts", True, 1.5)
    tracker.update_task_result(1, "tts", True, 1.8)
    tracker.update_task_result(1, "tts", True, 1.2)
    
    # TTS specialization should improve score
    score_with_tts = tracker.miners[1].get_performance_score("tts")
    print(f"   Miner 1 TTS specialization score: {score_with_tts:.3f}")
    
    print("✅ Performance tracking tests passed!")


def test_persistence():
    """Test metrics persistence"""
    print("🧪 Testing metrics persistence...")
    
    config = MockConfig()
    tracker = MinerTracker(config)
    
    # Register and update miners
    tracker.register_miner(1, "hotkey1", 1000.0)
    tracker.update_task_result(1, "transcription", True, 2.0)
    tracker.update_task_result(1, "transcription", True, 1.8)
    
    # Save metrics
    tracker.save_metrics()
    
    # Create new tracker and load metrics
    tracker2 = MinerTracker(config)
    
    # Verify data was loaded
    assert 1 in tracker2.miners
    miner = tracker2.miners[1]
    assert miner.total_tasks == 2
    assert miner.successful_tasks == 2
    
    print("✅ Persistence tests passed!")


async def main():
    """Run all tests"""
    print("🚀 Starting Enhanced System Tests")
    print("=" * 50)
    
    try:
        test_miner_metrics()
        test_miner_tracker()
        test_load_balancing()
        test_performance_tracking()
        test_persistence()
        
        print("\n🎉 All tests passed successfully!")
        print("✅ Enhanced miner tracking and load balancing system is working correctly")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
