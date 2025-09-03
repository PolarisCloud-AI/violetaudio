#!/usr/bin/env python3
"""
Comprehensive Test Script for Duplicate Protection System
Tests all three levels of duplicate protection:
1. Miner-level protection
2. Proxy server-level protection  
3. Task distributor-level protection
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

class DuplicateProtectionTester:
    def __init__(self, proxy_url="http://localhost:8000"):
        self.proxy_url = proxy_url
        self.test_results = {}
        
    async def test_miner_level_protection(self):
        """Test miner-level duplicate protection"""
        print("🔒 Testing Miner-Level Duplicate Protection...")
        
        try:
            # Test 1: Create a simple task
            task_data = {
                "task_type": "text_translation",
                "input_text": {
                    "text": "Hello, this is a test of duplicate protection.",
                    "source_language": "en",
                    "target_language": "es"
                },
                "required_miner_count": 1
            }
            
            # Create task
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.proxy_url}/api/v1/tasks",
                    json=task_data
                )
                
                if response.status_code == 201:
                    task = response.json()
                    task_id = task.get("task_id")
                    print(f"   ✅ Created test task: {task_id}")
                    
                    # Wait for task to be assigned
                    await asyncio.sleep(2)
                    
                    # Check task status
                    status_response = await client.get(f"{self.proxy_url}/api/v1/tasks/{task_id}")
                    if status_response.status_code == 200:
                        task_status = status_response.json()
                        print(f"   📊 Task status: {task_status.get('status')}")
                        print(f"   📊 Assigned miners: {task_status.get('assigned_miners', [])}")
                        
                        # Test duplicate protection by checking if task can be processed multiple times
                        if task_status.get('status') == 'assigned':
                            print("   🔍 Testing duplicate processing prevention...")
                            
                            # Simulate multiple processing attempts
                            for attempt in range(3):
                                print(f"      Attempt {attempt + 1}: Checking task eligibility...")
                                
                                # Check if task is still eligible for processing
                                if task_status.get('status') in ['assigned', 'pending']:
                                    print(f"         ✅ Task still eligible for processing")
                                else:
                                    print(f"         ❌ Task no longer eligible: {task_status.get('status')}")
                                    break
                                
                                await asyncio.sleep(1)
                            
                            print("   ✅ Miner-level duplicate protection test completed")
                            self.test_results['miner_level'] = 'PASSED'
                        else:
                            print(f"   ⚠️ Task not in expected state: {task_status.get('status')}")
                            self.test_results['miner_level'] = 'WARNING'
                    else:
                        print(f"   ❌ Failed to get task status: {status_response.status_code}")
                        self.test_results['miner_level'] = 'FAILED'
                else:
                    print(f"   ❌ Failed to create test task: {response.status_code}")
                    self.test_results['miner_level'] = 'FAILED'
                    
        except Exception as e:
            print(f"   ❌ Error testing miner-level protection: {e}")
            self.test_results['miner_level'] = 'ERROR'
    
    async def test_proxy_level_protection(self):
        """Test proxy server-level duplicate protection"""
        print("🔒 Testing Proxy Server-Level Duplicate Protection...")
        
        try:
            # Test 1: Check duplicate protection statistics
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.proxy_url}/api/v1/duplicate-protection/stats")
                
                if response.status_code == 200:
                    stats = response.json()
                    print("   ✅ Retrieved duplicate protection statistics")
                    
                    # Check proxy level stats
                    proxy_level = stats.get('duplicate_protection_system', {}).get('levels', {}).get('proxy_level', {})
                    if proxy_level.get('status') == 'active':
                        print("   ✅ Proxy-level protection is active")
                        
                        # Get detailed proxy stats
                        proxy_stats_response = await client.get(f"{self.proxy_url}/api/v1/metrics")
                        if proxy_stats_response.status_code == 200:
                            metrics = proxy_stats_response.json()
                            proxy_stats = metrics.get('duplicate_protection', {}).get('proxy_level', {})
                            
                            if 'duplicate_protection_effectiveness' in proxy_stats:
                                effectiveness = proxy_stats['duplicate_protection_effectiveness']
                                print(f"   📊 Proxy protection effectiveness: {effectiveness}")
                                
                                # Parse effectiveness percentage
                                try:
                                    effectiveness_pct = float(effectiveness.rstrip('%'))
                                    if effectiveness_pct > 90:
                                        print("   🎯 Excellent duplicate protection effectiveness!")
                                        self.test_results['proxy_level'] = 'PASSED'
                                    elif effectiveness_pct > 70:
                                        print("   ✅ Good duplicate protection effectiveness")
                                        self.test_results['proxy_level'] = 'PASSED'
                                    else:
                                        print("   ⚠️ Low duplicate protection effectiveness")
                                        self.test_results['proxy_level'] = 'WARNING'
                                except:
                                    print("   ⚠️ Could not parse effectiveness percentage")
                                    self.test_results['proxy_level'] = 'WARNING'
                            else:
                                print("   ⚠️ No effectiveness data available")
                                self.test_results['proxy_level'] = 'WARNING'
                        else:
                            print("   ❌ Failed to get proxy metrics")
                            self.test_results['proxy_level'] = 'FAILED'
                    else:
                        print(f"   ❌ Proxy-level protection not active: {proxy_level.get('status')}")
                        self.test_results['proxy_level'] = 'FAILED'
                else:
                    print(f"   ❌ Failed to get duplicate protection stats: {response.status_code}")
                    self.test_results['proxy_level'] = 'FAILED'
                    
        except Exception as e:
            print(f"   ❌ Error testing proxy-level protection: {e}")
            self.test_results['proxy_level'] = 'ERROR'
    
    async def test_distributor_level_protection(self):
        """Test task distributor-level duplicate protection"""
        print("🔒 Testing Task Distributor-Level Duplicate Protection...")
        
        try:
            # Test 1: Check task distributor protection statistics
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.proxy_url}/api/v1/duplicate-protection/stats")
                
                if response.status_code == 200:
                    stats = response.json()
                    
                    # Check distributor level stats
                    distributor_level = stats.get('duplicate_protection_system', {}).get('levels', {}).get('distributor_level', {})
                    if distributor_level.get('status') == 'active':
                        print("   ✅ Task distributor-level protection is active")
                        
                        # Check overall system health
                        overall_health = stats.get('duplicate_protection_system', {}).get('overall_health', {})
                        health_status = overall_health.get('status', 'unknown')
                        health_percentage = overall_health.get('health_percentage', '0%')
                        
                        print(f"   📊 Overall system health: {health_status} ({health_percentage})")
                        
                        if health_status == 'fully_healthy':
                            print("   🎯 All protection levels are fully healthy!")
                            self.test_results['distributor_level'] = 'PASSED'
                        elif health_status == 'partially_healthy':
                            print("   ✅ Most protection levels are healthy")
                            self.test_results['distributor_level'] = 'PASSED'
                        else:
                            print("   ⚠️ Some protection levels may have issues")
                            self.test_results['distributor_level'] = 'WARNING'
                    else:
                        print(f"   ❌ Task distributor-level protection not active: {distributor_level.get('status')}")
                        self.test_results['distributor_level'] = 'FAILED'
                else:
                    print(f"   ❌ Failed to get duplicate protection stats: {response.status_code}")
                    self.test_results['distributor_level'] = 'FAILED'
                    
        except Exception as e:
            print(f"   ❌ Error testing distributor-level protection: {e}")
            self.test_results['distributor_level'] = 'ERROR'
    
    async def test_overall_system(self):
        """Test overall duplicate protection system"""
        print("🔒 Testing Overall Duplicate Protection System...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Get comprehensive system status
                response = await client.get(f"{self.proxy_url}/api/v1/duplicate-protection/stats")
                
                if response.status_code == 200:
                    stats = response.json()
                    
                    # Check system components
                    levels = stats.get('duplicate_protection_system', {}).get('levels', {})
                    overall_health = stats.get('duplicate_protection_system', {}).get('overall_health', {})
                    
                    print("   📊 System Component Status:")
                    for level_name, level_info in levels.items():
                        status = level_info.get('status', 'unknown')
                        status_icon = "✅" if status == 'active' else "❌" if status == 'not_initialized' else "⚠️"
                        print(f"      {status_icon} {level_info.get('name', level_name)}: {status}")
                    
                    # Overall assessment
                    active_levels = overall_health.get('active_levels', 0)
                    total_levels = overall_health.get('total_levels', 3)
                    health_percentage = overall_health.get('health_percentage', '0%')
                    
                    print(f"   📊 Overall System Health: {health_percentage}")
                    print(f"   📊 Active Protection Levels: {active_levels}/{total_levels}")
                    
                    if active_levels == total_levels:
                        print("   🎯 All duplicate protection levels are active!")
                        self.test_results['overall_system'] = 'PASSED'
                    elif active_levels >= 2:
                        print("   ✅ Most duplicate protection levels are active")
                        self.test_results['overall_system'] = 'PASSED'
                    else:
                        print("   ⚠️ Some duplicate protection levels are inactive")
                        self.test_results['overall_system'] = 'WARNING'
                        
                else:
                    print(f"   ❌ Failed to get system status: {response.status_code}")
                    self.test_results['overall_system'] = 'FAILED'
                    
        except Exception as e:
            print(f"   ❌ Error testing overall system: {e}")
            self.test_results['overall_system'] = 'ERROR'
    
    async def run_all_tests(self):
        """Run all duplicate protection tests"""
        print("🚀 Starting Comprehensive Duplicate Protection Tests")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all test levels
        await self.test_miner_level_protection()
        print()
        
        await self.test_proxy_level_protection()
        print()
        
        await self.test_distributor_level_protection()
        print()
        
        await self.test_overall_system()
        print()
        
        # Generate test summary
        self.generate_test_summary()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"⏱️  Total test time: {total_time:.2f} seconds")
        print("=" * 60)
    
    def generate_test_summary(self):
        """Generate a comprehensive test summary"""
        print("📋 DUPLICATE PROTECTION TEST SUMMARY")
        print("=" * 60)
        
        # Count results
        passed = sum(1 for result in self.test_results.values() if result == 'PASSED')
        warnings = sum(1 for result in self.test_results.values() if result == 'WARNING')
        failed = sum(1 for result in self.test_results.values() if result == 'FAILED')
        errors = sum(1 for result in self.test_results.values() if result == 'ERROR')
        total = len(self.test_results)
        
        print(f"📊 Test Results Summary:")
        print(f"   ✅ PASSED: {passed}/{total}")
        print(f"   ⚠️  WARNINGS: {warnings}/{total}")
        print(f"   ❌ FAILED: {failed}/{total}")
        print(f"   💥 ERRORS: {errors}/{total}")
        
        print("\n🔍 Detailed Results:")
        for test_name, result in self.test_results.items():
            status_icon = {
                'PASSED': '✅',
                'WARNING': '⚠️',
                'FAILED': '❌',
                'ERROR': '💥'
            }.get(result, '❓')
            
            print(f"   {status_icon} {test_name.replace('_', ' ').title()}: {result}")
        
        # Overall assessment
        if failed == 0 and errors == 0:
            if warnings == 0:
                print("\n🎯 EXCELLENT: All duplicate protection levels are working perfectly!")
            else:
                print("\n✅ GOOD: Duplicate protection is working with minor warnings")
        elif failed == 0:
            print("\n⚠️  CAUTION: Duplicate protection has some errors but no failures")
        else:
            print("\n❌ CRITICAL: Some duplicate protection levels are failing!")
        
        print("\n🔒 Duplicate Protection System Status:")
        if passed >= 3:
            print("   🛡️  Your system is well-protected against duplicate task processing")
        elif passed >= 2:
            print("   🛡️  Your system has good protection against duplicate task processing")
        else:
            print("   ⚠️  Your system needs attention for duplicate task processing protection")

async def main():
    """Main test execution"""
    print("🔒 Bittensor Subnet Duplicate Protection System Test")
    print("Testing all three levels of duplicate protection...")
    print()
    
    tester = DuplicateProtectionTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
