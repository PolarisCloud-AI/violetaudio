"""
Quota Monitor for Enhanced Proxy Server
Tracks database operations and implements rate limiting to prevent Firebase quota exceeded errors
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
import threading

class QuotaMonitor:
    def __init__(self):
        # Firebase quotas (conservative estimates)
        self.quota_limits = {
            'writes_per_second': 1000,
            'reads_per_second': 10000,
            'deletes_per_second': 500,
            'writes_per_minute': 60000,
            'reads_per_minute': 600000,
            'deletes_per_minute': 30000
        }
        
        # Operation tracking
        self.operation_counts = defaultdict(int)
        self.operation_timestamps = defaultdict(deque)
        self.last_reset = time.time()
        self.reset_interval = 3600  # 1 hour
        
        # Rate limiting
        self.rate_limits = {
            'writes': {'per_second': 800, 'per_minute': 50000},  # 80% of quota
            'reads': {'per_second': 8000, 'per_minute': 500000},
            'deletes': {'per_second': 400, 'per_minute': 25000}
        }
        
        # Throttling state
        self.throttling_enabled = False
        self.throttle_multiplier = 1.0
        self.max_throttle_multiplier = 10.0
        
        # Monitoring
        self.quota_warnings = []
        self.quota_errors = []
        
        # Start background monitoring
        self.monitoring_active = True
        asyncio.create_task(self._background_monitor())
        
        print("✅ Quota Monitor initialized")
        print(f"   Write limit: {self.quota_limits['writes_per_second']}/sec")
        print(f"   Read limit: {self.quota_limits['reads_per_second']}/sec")
        print(f"   Delete limit: {self.quota_limits['deletes_per_second']}/sec")
    
    async def check_quota(self, operation_type: str) -> bool:
        """Check if operation is within quota limits"""
        try:
            current_time = time.time()
            
            # Reset counters hourly
            if current_time - self.last_reset >= self.reset_interval:
                self._reset_counters()
                self.last_reset = current_time
            
            # Get current limits
            per_second_limit = self.rate_limits[operation_type]['per_second']
            per_minute_limit = self.rate_limits[operation_type]['per_minute']
            
            # Check per-second limit
            current_second_count = self._get_operation_count(operation_type, 1)
            if current_second_count >= per_second_limit:
                await self._record_quota_warning(operation_type, 'per_second', current_second_count, per_second_limit)
                return False
            
            # Check per-minute limit
            current_minute_count = self._get_operation_count(operation_type, 60)
            if current_minute_count >= per_minute_limit:
                await self._record_quota_warning(operation_type, 'per_minute', current_minute_count, per_minute_limit)
                return False
            
            # Record operation
            self._record_operation(operation_type)
            return True
            
        except Exception as e:
            print(f"❌ Quota check failed: {e}")
            return True  # Allow operation if check fails
    
    def _get_operation_count(self, operation_type: str, time_window: int) -> int:
        """Get operation count for a specific time window"""
        try:
            current_time = time.time()
            cutoff_time = current_time - time_window
            
            timestamps = self.operation_timestamps[operation_type]
            
            # Remove old timestamps
            while timestamps and timestamps[0] < cutoff_time:
                timestamps.popleft()
            
            return len(timestamps)
            
        except Exception as e:
            print(f"❌ Error getting operation count: {e}")
            return 0
    
    def _record_operation(self, operation_type: str):
        """Record an operation for quota tracking"""
        try:
            current_time = time.time()
            
            # Add to counts
            self.operation_counts[operation_type] += 1
            
            # Add to timestamps
            if operation_type not in self.operation_timestamps:
                self.operation_timestamps[operation_type] = deque(maxlen=10000)
            
            self.operation_timestamps[operation_type].append(current_time)
            
        except Exception as e:
            print(f"❌ Error recording operation: {e}")
    
    def _reset_counters(self):
        """Reset operation counters"""
        try:
            self.operation_counts.clear()
            for operation_type in self.operation_timestamps:
                self.operation_timestamps[operation_type].clear()
            
            print("🔄 Quota counters reset")
            
        except Exception as e:
            print(f"❌ Error resetting counters: {e}")
    
    async def _record_quota_warning(self, operation_type: str, limit_type: str, current: int, limit: int):
        """Record a quota warning"""
        try:
            warning = {
                'timestamp': datetime.now(),
                'operation_type': operation_type,
                'limit_type': limit_type,
                'current_count': current,
                'limit': limit,
                'percentage': (current / limit) * 100
            }
            
            self.quota_warnings.append(warning)
            
            # Keep only last 100 warnings
            if len(self.quota_warnings) > 100:
                self.quota_warnings = self.quota_warnings[-100:]
            
            print(f"⚠️ QUOTA WARNING: {operation_type} {limit_type}")
            print(f"   Current: {current}, Limit: {limit} ({warning['percentage']:.1f}%)")
            
            # Enable throttling if approaching hard limits
            if warning['percentage'] >= 90:
                await self._enable_emergency_throttling()
            
        except Exception as e:
            print(f"❌ Error recording quota warning: {e}")
    
    async def _enable_emergency_throttling(self):
        """Enable emergency throttling when approaching hard limits"""
        try:
            if not self.throttling_enabled:
                self.throttling_enabled = True
                self.throttle_multiplier = 2.0
                print("🚨 EMERGENCY THROTTLING ENABLED")
            
            # Increase throttle multiplier
            self.throttle_multiplier = min(self.throttle_multiplier * 1.5, self.max_throttle_multiplier)
            
        except Exception as e:
            print(f"❌ Error enabling emergency throttling: {e}")
    
    async def enforce_quota(self, operation_type: str):
        """Enforce quota limits with intelligent throttling"""
        try:
            # Check quota
            if not await self.check_quota(operation_type):
                # Quota exceeded, implement throttling
                await self._throttle_operation(operation_type)
            
        except Exception as e:
            print(f"❌ Quota enforcement failed: {e}")
    
    async def _throttle_operation(self, operation_type: str):
        """Throttle operations when quota is exceeded"""
        try:
            if self.throttling_enabled:
                # Calculate delay based on throttle multiplier
                base_delay = 1.0  # 1 second base delay
                delay = base_delay * self.throttle_multiplier
                
                print(f"⏳ Throttling {operation_type} operation for {delay:.1f} seconds")
                await asyncio.sleep(delay)
                
                # Gradually reduce throttle if quota improves
                if self.throttle_multiplier > 1.0:
                    self.throttle_multiplier = max(1.0, self.throttle_multiplier * 0.9)
                    
                    if self.throttle_multiplier == 1.0:
                        self.throttling_enabled = False
                        print("✅ Throttling disabled - quota recovered")
            
        except Exception as e:
            print(f"❌ Throttling failed: {e}")
    
    async def _background_monitor(self):
        """Background task to monitor quota usage"""
        while self.monitoring_active:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Check current usage
                await self._check_quota_health()
                
                # Clean up old warnings
                await self._cleanup_old_warnings()
                
            except Exception as e:
                print(f"❌ Background monitoring error: {e}")
                await asyncio.sleep(60)  # Longer sleep on error
    
    async def _check_quota_health(self):
        """Check overall quota health"""
        try:
            current_time = time.time()
            
            for operation_type in ['writes', 'reads', 'deletes']:
                # Check per-minute usage
                minute_count = self._get_operation_count(operation_type, 60)
                minute_limit = self.rate_limits[operation_type]['per_minute']
                
                usage_percentage = (minute_count / minute_limit) * 100
                
                if usage_percentage >= 80:
                    print(f"⚠️ {operation_type.upper()} usage: {minute_count}/{minute_limit} ({usage_percentage:.1f}%)")
                
                # Reduce throttling if usage is low
                if usage_percentage < 50 and self.throttling_enabled:
                    self.throttle_multiplier = max(1.0, self.throttle_multiplier * 0.8)
                    
                    if self.throttle_multiplier == 1.0:
                        self.throttling_enabled = False
                        print(f"✅ Throttling reduced for {operation_type} - usage normalized")
            
        except Exception as e:
            print(f"❌ Quota health check failed: {e}")
    
    async def _cleanup_old_warnings(self):
        """Clean up old quota warnings"""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=24)
            
            # Remove warnings older than 24 hours
            self.quota_warnings = [
                warning for warning in self.quota_warnings
                if warning['timestamp'] > cutoff_time
            ]
            
        except Exception as e:
            print(f"❌ Warning cleanup failed: {e}")
    
    def get_quota_stats(self) -> Dict[str, Any]:
        """Get current quota statistics"""
        try:
            stats = {
                'current_usage': {},
                'quota_limits': self.quota_limits,
                'rate_limits': self.rate_limits,
                'throttling': {
                    'enabled': self.throttling_enabled,
                    'multiplier': self.throttle_multiplier,
                    'max_multiplier': self.max_throttle_multiplier
                },
                'warnings': len(self.quota_warnings),
                'errors': len(self.quota_errors),
                'last_reset': self.last_reset,
                'time_since_reset': time.time() - self.last_reset
            }
            
            # Add current usage for each operation type
            for operation_type in ['writes', 'reads', 'deletes']:
                stats['current_usage'][operation_type] = {
                    'per_second': self._get_operation_count(operation_type, 1),
                    'per_minute': self._get_operation_count(operation_type, 60),
                    'total': self.operation_counts[operation_type]
                }
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_recent_warnings(self, limit: int = 10) -> List[Dict]:
        """Get recent quota warnings"""
        try:
            return self.quota_warnings[-limit:]
        except Exception as e:
            return []
    
    async def shutdown(self):
        """Shutdown the quota monitor"""
        try:
            self.monitoring_active = False
            print("🔄 Quota monitor shutting down...")
            
            # Wait for background task to finish
            await asyncio.sleep(1)
            
            print("✅ Quota monitor shutdown complete")
            
        except Exception as e:
            print(f"❌ Quota monitor shutdown failed: {e}")
    
    # Convenience methods for common operations
    async def check_write_quota(self) -> bool:
        """Check if write operation is allowed"""
        return await self.check_quota('writes')
    
    async def check_read_quota(self) -> bool:
        """Check if read operation is allowed"""
        return await self.check_quota('reads')
    
    async def check_delete_quota(self) -> bool:
        """Check if delete operation is allowed"""
        return await self.check_quota('deletes')
    
    async def enforce_write_quota(self):
        """Enforce write quota limits"""
        await self.enforce_quota('writes')
    
    async def enforce_read_quota(self):
        """Enforce read quota limits"""
        await self.enforce_quota('reads')
    
    async def enforce_delete_quota(self):
        """Enforce delete quota limits"""
        await self.enforce_quota('deletes')
