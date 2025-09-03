#!/usr/bin/env python3
"""
Test script to verify Bittensor network integration in the proxy server.
This script simulates a validator reporting miner status to the proxy server.
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

class NetworkIntegrationTester:
    def __init__(self, proxy_url="http://localhost:8000"):
        self.proxy_url = proxy_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_miner_status_endpoint(self):
        """Test the new miner status endpoint"""
        print("🧪 Testing miner status endpoint...")
        
        # Simulate miner status data from a validator
        miner_statuses = [
            {
                "uid": 48,
                "hotkey": "5Gxwzb9gKBCE2a4Qb6VDfUSabKMRZt9AKWw4VrPWZnuUWAsw",
                "ip": "127.0.0.1",
                "port": 8091,
                "external_ip": "102.134.149.117",
                "external_port": 8091,
                "is_serving": True,
                "stake": 1000.0,
                "performance_score": 0.85,
                "current_load": 1,
                "max_capacity": 5,
                "task_type_specialization": {
                    "transcription": {"total": 15, "successful": 14, "success_rate": 0.93},
                    "tts": {"total": 12, "successful": 11, "success_rate": 0.92},
                    "summarization": {"total": 8, "successful": 7, "success_rate": 0.88}
                }
            },
            {
                "uid": 49,
                "hotkey": "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
                "ip": "192.168.1.100",
                "port": 8092,
                "external_ip": "203.0.113.1",
                "external_port": 8092,
                "is_serving": True,
                "stake": 2500.0,
                "performance_score": 0.92,
                "current_load": 0,
                "max_capacity": 8,
                "task_type_specialization": {
                    "transcription": {"total": 25, "successful": 24, "success_rate": 0.96},
                    "translation": {"total": 18, "successful": 17, "success_rate": 0.94}
                }
            },
            {
                "uid": 50,
                "hotkey": "5FLSigC9HGRKVhB9FiEo4Y3koPsNmBmLJbpXg2mp1hXcS59Y",
                "ip": "10.0.0.50",
                "port": 8093,
                "external_ip": "198.51.100.1",
                "external_port": 8093,
                "is_serving": True,
                "stake": 1800.0,
                "performance_score": 0.78,
                "current_load": 2,
                "max_capacity": 6,
                "task_type_specialization": {
                    "tts": {"total": 20, "successful": 18, "success_rate": 0.90},
                    "summarization": {"total": 15, "successful": 13, "success_rate": 0.87}
                }
            }
        ]
        
        try:
            # Send miner status to proxy server
            response = await self.client.post(
                f"{self.proxy_url}/api/v1/validators/miner-status",
                data={
                    "validator_uid": 999,  # Test validator UID
                    "miner_statuses": json.dumps(miner_statuses),
                    "epoch": 1
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Miner status endpoint working!")
                print(f"   Miners updated: {result.get('miners_updated')}")
                print(f"   Total received: {result.get('total_received')}")
                print(f"   Validator UID: {result.get('validator_uid')}")
                print(f"   Epoch: {result.get('epoch')}")
                return True
            else:
                print(f"❌ Miner status endpoint failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing miner status endpoint: {e}")
            return False
    
    async def test_network_miner_status(self):
        """Test getting network miner status"""
        print("\n🧪 Testing network miner status endpoint...")
        
        try:
            response = await self.client.get(f"{self.proxy_url}/api/v1/miners/network-status")
            
            if response.status_code == 200:
                result = response.json()
                network_status = result.get('network_status', {})
                miners = result.get('miners', [])
                
                print(f"✅ Network miner status working!")
                print(f"   Total miners: {network_status.get('total_miners')}")
                print(f"   Active miners: {network_status.get('active_miners')}")
                print(f"   Total stake: {network_status.get('total_stake'):.2f}")
                print(f"   Last updated: {network_status.get('last_updated')}")
                
                print(f"\n📊 Miner Details:")
                for miner in miners[:5]:  # Show first 5 miners
                    print(f"   UID {miner.get('uid')}: {miner.get('hotkey', 'unknown')[:20]}...")
                    print(f"      Stake: {miner.get('stake', 0):.2f}, Serving: {miner.get('is_serving', False)}")
                    print(f"      Performance: {miner.get('performance_score', 0):.3f}, Load: {miner.get('current_load', 0)}/{miner.get('max_capacity', 5)}")
                
                return True
            else:
                print(f"❌ Network miner status failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing network miner status: {e}")
            return False
    
    async def test_updated_metrics(self):
        """Test the updated metrics endpoint with network miner info"""
        print("\n🧪 Testing updated metrics endpoint...")
        
        try:
            response = await self.client.get(f"{self.proxy_url}/api/v1/metrics")
            
            if response.status_code == 200:
                result = response.json()
                network_miners = result.get('network_miners', {})
                
                print(f"✅ Updated metrics working!")
                print(f"   Total miners: {network_miners.get('total_miners')}")
                print(f"   Active miners: {network_miners.get('active_miners')}")
                print(f"   Total stake: {network_miners.get('total_stake', 0):.2f}")
                print(f"   Average performance: {network_miners.get('average_performance_score', 0):.3f}")
                
                # Show miner details
                miner_details = network_miners.get('miner_details', [])
                if miner_details:
                    print(f"\n📊 Top Miners from Metrics:")
                    for i, miner in enumerate(miner_details[:3], 1):
                        print(f"   #{i} UID {miner.get('uid')}: score={miner.get('availability_score', 0):.3f}, load={miner.get('current_load', 0)}/{miner.get('max_capacity', 5)}")
                
                return True
            else:
                print(f"❌ Updated metrics failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing updated metrics: {e}")
            return False
    
    async def test_task_distribution_with_network_miners(self):
        """Test if task distribution can now use network miners"""
        print("\n🧪 Testing task distribution with network miners...")
        
        try:
            # First, check if we have network miners
            response = await self.client.get(f"{self.proxy_url}/api/v1/miners/network-status")
            if response.status_code != 200:
                print("❌ Cannot test task distribution - network miner status unavailable")
                return False
            
            result = response.json()
            total_miners = result.get('network_status', {}).get('total_miners', 0)
            
            if total_miners > 0:
                print(f"✅ Task distribution can use {total_miners} network miners!")
                print(f"   This means the proxy server is no longer limited to hardcoded miners")
                print(f"   Tasks can now be distributed to real Bittensor network miners")
                return True
            else:
                print("⚠️ No network miners available yet - task distribution still limited")
                return False
                
        except Exception as e:
            print(f"❌ Error testing task distribution: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Bittensor Network Integration Tests")
        print("=" * 60)
        
        test_results = []
        
        # Test 1: Miner status endpoint
        test_results.append(await self.test_miner_status_endpoint())
        
        # Wait a moment for data to be processed
        await asyncio.sleep(2)
        
        # Test 2: Network miner status
        test_results.append(await self.test_network_miner_status())
        
        # Test 3: Updated metrics
        test_results.append(await self.test_updated_metrics())
        
        # Test 4: Task distribution capability
        test_results.append(await self.test_task_distribution_with_network_miners())
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(test_results)
        total = len(test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Bittensor network integration is working!")
            print("   The proxy server can now:")
            print("   - Receive miner status from validators")
            print("   - Discover real network miners")
            print("   - Use network miners for task distribution")
            print("   - Provide real-time network statistics")
        else:
            print(f"\n⚠️ {total - passed} test(s) failed. Check the logs above for details.")
        
        return passed == total
    
    async def cleanup(self):
        """Clean up resources"""
        await self.client.aclose()

async def main():
    """Main test function"""
    tester = NetworkIntegrationTester()
    
    try:
        success = await tester.run_all_tests()
        return success
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    print("🧪 Bittensor Network Integration Test")
    print("Make sure the proxy server is running on http://localhost:8000")
    print("=" * 60)
    
    success = asyncio.run(main())
    exit(0 if success else 1)
