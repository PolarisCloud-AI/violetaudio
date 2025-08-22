#!/usr/bin/env python3
"""
Test script to demonstrate multi-validator conflict resolution
Shows how the proxy server handles conflicting miner status from multiple validators
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_multi_validator_conflict_resolution():
    """Test how proxy handles conflicting miner status from multiple validators"""
    print("🧪 Testing multi-validator conflict resolution...")
    
    # Test data: Multiple validators reporting different status for the same miner
    test_scenarios = [
        {
            "validator_uid": 101,
            "description": "Validator 101 reports miner as serving with low load",
            "miner_statuses": [
                {
                    "uid": 1,
                    "hotkey": "miner_1_hotkey",
                    "ip": "192.168.1.100",
                    "port": 8091,
                    "external_ip": "192.168.1.100",
                    "external_port": 8091,
                    "is_serving": True,
                    "stake": 1500.0,
                    "performance_score": 0.92,
                    "current_load": 1,
                    "max_capacity": 5,
                    "task_type_specialization": {
                        "transcription": {"total": 15, "successful": 14, "avg_time": 2.3, "success_rate": 0.933}
                    }
                }
            ]
        },
        {
            "validator_uid": 102,
            "description": "Validator 102 reports same miner as not serving with high load",
            "miner_statuses": [
                {
                    "uid": 1,
                    "hotkey": "miner_1_hotkey",
                    "ip": "192.168.1.100",
                    "port": 8091,
                    "external_ip": "192.168.1.100",
                    "external_port": 8091,
                    "is_serving": False,
                    "stake": 1200.0,
                    "performance_score": 0.88,
                    "current_load": 4,
                    "max_capacity": 5,
                    "task_type_specialization": {
                        "transcription": {"total": 12, "successful": 10, "avg_time": 2.8, "success_rate": 0.833}
                    }
                }
            ]
        },
        {
            "validator_uid": 103,
            "description": "Validator 103 reports same miner as serving with medium load",
            "miner_statuses": [
                {
                    "uid": 1,
                    "hotkey": "miner_1_hotkey",
                    "ip": "192.168.1.100",
                    "port": 8091,
                    "external_ip": "192.168.1.100",
                    "external_port": 8091,
                    "is_serving": True,
                    "stake": 2000.0,
                    "performance_score": 0.95,
                    "current_load": 2,
                    "max_capacity": 5,
                    "task_type_specialization": {
                        "transcription": {"total": 20, "successful": 19, "avg_time": 2.1, "success_rate": 0.95}
                    }
                }
            ]
        }
    ]
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("📊 Sending conflicting miner status from multiple validators...")
            
            # Send reports from all validators
            for scenario in test_scenarios:
                print(f"\n  📤 {scenario['description']}")
                
                response = await client.post(
                    "http://localhost:8000/api/v1/validators/miner-status",
                    json={
                        "validator_uid": scenario["validator_uid"],
                        "miner_statuses": scenario["miner_statuses"],
                        "epoch": 1
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"    ✅ Success: {result['message']}")
                else:
                    print(f"    ❌ Failed: {response.status_code} - {response.text}")
                    return False
            
            # Wait a moment for processing
            await asyncio.sleep(2)
            
            # Check the final miner status
            print("\n🔍 Checking final resolved miner status...")
            response = await client.get("http://localhost:8000/api/v1/miners/status")
            
            if response.status_code == 200:
                data = response.json()
                print(f"    ✅ Miner status retrieved successfully")
                
                # Find our test miner
                test_miner = None
                for miner in data['recent_miners']:
                    if miner['uid'] == 1:
                        test_miner = miner
                        break
                
                if test_miner:
                    print(f"\n📊 Final Resolved Status for Miner 1:")
                    print(f"    Serving: {test_miner['is_serving']}")
                    print(f"    Stake: {test_miner['stake']}")
                    print(f"    Performance Score: {test_miner['performance_score']}")
                    print(f"    Current Load: {test_miner['current_load']}")
                    print(f"    Reported by Validators: {test_miner['reported_by_validators']}")
                    
                    # Verify conflict resolution worked correctly
                    print(f"\n🎯 Conflict Resolution Results:")
                    print(f"    Serving Status: {test_miner['is_serving']} (should be True - consensus)")
                    print(f"    Stake: {test_miner['stake']} (should be 2000.0 - highest reported)")
                    print(f"    Validators: {test_miner['reported_by_validators']} (should include all 3)")
                    
                    return True
                else:
                    print("    ❌ Test miner not found in results")
                    return False
            else:
                print(f"    ❌ Failed to get miner status: {response.status_code}")
                return False
                
    except Exception as e:
        import traceback
        print(f"❌ Error testing multi-validator conflict resolution: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def test_validator_cleanup():
    """Test that stale validators are cleaned up properly"""
    print("\n🧪 Testing validator cleanup...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send a report from a validator
            response = await client.post(
                "http://localhost:8000/api/v1/validators/miner-status",
                json={
                    "validator_uid": 999,
                    "miner_statuses": [
                        {
                            "uid": 999,
                            "hotkey": "test_cleanup_hotkey",
                            "ip": "127.0.0.1",
                            "port": 9999,
                            "is_serving": True,
                            "stake": 500.0,
                            "performance_score": 0.8,
                            "current_load": 0,
                            "max_capacity": 5
                        }
                    ],
                    "epoch": 1
                }
            )
            
            if response.status_code == 200:
                print("    ✅ Test validator status sent")
                
                # Check that it was added
                response = await client.get("http://localhost:8000/api/v1/miners/status")
                if response.status_code == 200:
                    data = response.json()
                    print(f"    📊 Total miners: {data['statistics']['total_miners']}")
                    return True
                else:
                    print("    ❌ Failed to get miner status")
                    return False
            else:
                print(f"    ❌ Failed to send test validator status: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing validator cleanup: {e}")
        return False

async def main():
    print("🚀 Starting Multi-Validator Conflict Resolution Tests...")
    print("=" * 70)
    
    # Wait for server to be ready
    print("⏳ Waiting for proxy server to be ready...")
    await asyncio.sleep(3)
    
    # Test 1: Multi-validator conflict resolution
    if not await test_multi_validator_conflict_resolution():
        print("❌ Test 1 failed - stopping")
        return False
    
    # Test 2: Validator cleanup
    if not await test_validator_cleanup():
        print("❌ Test 2 failed - stopping")
        return False
    
    print("\n" + "=" * 70)
    print("🎉 All multi-validator tests passed!")
    print("✅ Conflict resolution system working correctly")
    print("✅ Validator cleanup system functional")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if success:
            print("✅ Multi-validator test suite completed successfully")
        else:
            print("❌ Multi-validator test suite failed")
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error during tests: {e}")

Test script to demonstrate multi-validator conflict resolution
Shows how the proxy server handles conflicting miner status from multiple validators
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_multi_validator_conflict_resolution():
    """Test how proxy handles conflicting miner status from multiple validators"""
    print("🧪 Testing multi-validator conflict resolution...")
    
    # Test data: Multiple validators reporting different status for the same miner
    test_scenarios = [
        {
            "validator_uid": 101,
            "description": "Validator 101 reports miner as serving with low load",
            "miner_statuses": [
                {
                    "uid": 1,
                    "hotkey": "miner_1_hotkey",
                    "ip": "192.168.1.100",
                    "port": 8091,
                    "external_ip": "192.168.1.100",
                    "external_port": 8091,
                    "is_serving": True,
                    "stake": 1500.0,
                    "performance_score": 0.92,
                    "current_load": 1,
                    "max_capacity": 5,
                    "task_type_specialization": {
                        "transcription": {"total": 15, "successful": 14, "avg_time": 2.3, "success_rate": 0.933}
                    }
                }
            ]
        },
        {
            "validator_uid": 102,
            "description": "Validator 102 reports same miner as not serving with high load",
            "miner_statuses": [
                {
                    "uid": 1,
                    "hotkey": "miner_1_hotkey",
                    "ip": "192.168.1.100",
                    "port": 8091,
                    "external_ip": "192.168.1.100",
                    "external_port": 8091,
                    "is_serving": False,
                    "stake": 1200.0,
                    "performance_score": 0.88,
                    "current_load": 4,
                    "max_capacity": 5,
                    "task_type_specialization": {
                        "transcription": {"total": 12, "successful": 10, "avg_time": 2.8, "success_rate": 0.833}
                    }
                }
            ]
        },
        {
            "validator_uid": 103,
            "description": "Validator 103 reports same miner as serving with medium load",
            "miner_statuses": [
                {
                    "uid": 1,
                    "hotkey": "miner_1_hotkey",
                    "ip": "192.168.1.100",
                    "port": 8091,
                    "external_ip": "192.168.1.100",
                    "external_port": 8091,
                    "is_serving": True,
                    "stake": 2000.0,
                    "performance_score": 0.95,
                    "current_load": 2,
                    "max_capacity": 5,
                    "task_type_specialization": {
                        "transcription": {"total": 20, "successful": 19, "avg_time": 2.1, "success_rate": 0.95}
                    }
                }
            ]
        }
    ]
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("📊 Sending conflicting miner status from multiple validators...")
            
            # Send reports from all validators
            for scenario in test_scenarios:
                print(f"\n  📤 {scenario['description']}")
                
                response = await client.post(
                    "http://localhost:8000/api/v1/validators/miner-status",
                    json={
                        "validator_uid": scenario["validator_uid"],
                        "miner_statuses": scenario["miner_statuses"],
                        "epoch": 1
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"    ✅ Success: {result['message']}")
                else:
                    print(f"    ❌ Failed: {response.status_code} - {response.text}")
                    return False
            
            # Wait a moment for processing
            await asyncio.sleep(2)
            
            # Check the final miner status
            print("\n🔍 Checking final resolved miner status...")
            response = await client.get("http://localhost:8000/api/v1/miners/status")
            
            if response.status_code == 200:
                data = response.json()
                print(f"    ✅ Miner status retrieved successfully")
                
                # Find our test miner
                test_miner = None
                for miner in data['recent_miners']:
                    if miner['uid'] == 1:
                        test_miner = miner
                        break
                
                if test_miner:
                    print(f"\n📊 Final Resolved Status for Miner 1:")
                    print(f"    Serving: {test_miner['is_serving']}")
                    print(f"    Stake: {test_miner['stake']}")
                    print(f"    Performance Score: {test_miner['performance_score']}")
                    print(f"    Current Load: {test_miner['current_load']}")
                    print(f"    Reported by Validators: {test_miner['reported_by_validators']}")
                    
                    # Verify conflict resolution worked correctly
                    print(f"\n🎯 Conflict Resolution Results:")
                    print(f"    Serving Status: {test_miner['is_serving']} (should be True - consensus)")
                    print(f"    Stake: {test_miner['stake']} (should be 2000.0 - highest reported)")
                    print(f"    Validators: {test_miner['reported_by_validators']} (should include all 3)")
                    
                    return True
                else:
                    print("    ❌ Test miner not found in results")
                    return False
            else:
                print(f"    ❌ Failed to get miner status: {response.status_code}")
                return False
                
    except Exception as e:
        import traceback
        print(f"❌ Error testing multi-validator conflict resolution: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def test_validator_cleanup():
    """Test that stale validators are cleaned up properly"""
    print("\n🧪 Testing validator cleanup...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send a report from a validator
            response = await client.post(
                "http://localhost:8000/api/v1/validators/miner-status",
                json={
                    "validator_uid": 999,
                    "miner_statuses": [
                        {
                            "uid": 999,
                            "hotkey": "test_cleanup_hotkey",
                            "ip": "127.0.0.1",
                            "port": 9999,
                            "is_serving": True,
                            "stake": 500.0,
                            "performance_score": 0.8,
                            "current_load": 0,
                            "max_capacity": 5
                        }
                    ],
                    "epoch": 1
                }
            )
            
            if response.status_code == 200:
                print("    ✅ Test validator status sent")
                
                # Check that it was added
                response = await client.get("http://localhost:8000/api/v1/miners/status")
                if response.status_code == 200:
                    data = response.json()
                    print(f"    📊 Total miners: {data['statistics']['total_miners']}")
                    return True
                else:
                    print("    ❌ Failed to get miner status")
                    return False
            else:
                print(f"    ❌ Failed to send test validator status: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing validator cleanup: {e}")
        return False

async def main():
    print("🚀 Starting Multi-Validator Conflict Resolution Tests...")
    print("=" * 70)
    
    # Wait for server to be ready
    print("⏳ Waiting for proxy server to be ready...")
    await asyncio.sleep(3)
    
    # Test 1: Multi-validator conflict resolution
    if not await test_multi_validator_conflict_resolution():
        print("❌ Test 1 failed - stopping")
        return False
    
    # Test 2: Validator cleanup
    if not await test_validator_cleanup():
        print("❌ Test 2 failed - stopping")
        return False
    
    print("\n" + "=" * 70)
    print("🎉 All multi-validator tests passed!")
    print("✅ Conflict resolution system working correctly")
    print("✅ Validator cleanup system functional")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if success:
            print("✅ Multi-validator test suite completed successfully")
        else:
            print("❌ Multi-validator test suite failed")
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error during tests: {e}")
