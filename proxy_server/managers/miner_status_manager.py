"""
Miner Status Manager for Enhanced Proxy Server
Handles miner status reports from multiple validators and resolves conflicts.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import firebase_admin
from firebase_admin import firestore

@dataclass
class MinerStatusReport:
    """Miner status report from a validator"""
    uid: int
    hotkey: str
    ip: str
    port: int
    external_ip: Optional[str] = None
    external_port: Optional[int] = None
    is_serving: bool = True
    stake: float = 0.0
    performance_score: float = 0.0
    current_load: float = 0.0
    max_capacity: float = 100.0
    task_type_specialization: Optional[str] = None
    last_seen: datetime = None
    reported_by_validators: List[str] = field(default_factory=list)
    updated_at: datetime = None

class MinerStatusManager:
    """Manages miner status information from multiple validators"""
    
    def __init__(self, db):
        self.db = db
        self.miner_status_collection = db.collection('miner_status')
        self.validators_collection = db.collection('validators')
        self.cleanup_interval = 300  # 5 minutes
        self.validator_timeout = 600  # 10 minutes
        self.miner_timeout = 900     # 15 minutes
        
    async def update_miner_status(self, validator_uid: int, miner_statuses: List[Dict], epoch: int) -> bool:
        """Update miner status from a validator report"""
        try:
            print(f"📥 Updating miner status from validator {validator_uid} for epoch {epoch}")
            print(f"   Received {len(miner_statuses)} miner status reports")
            
            # Update validator last seen
            await self._update_validator_last_seen(validator_uid, epoch)
            
            # Process each miner status
            for miner_data in miner_statuses:
                await self._process_miner_status(validator_uid, miner_data)
            
            print(f"✅ Successfully updated miner status from validator {validator_uid}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating miner status from validator {validator_uid}: {e}")
            return False
    
    async def _update_validator_last_seen(self, validator_uid: int, epoch: int):
        """Update validator's last seen timestamp"""
        try:
            validator_doc = {
                'validator_uid': validator_uid,
                'last_seen': datetime.utcnow(),
                'last_epoch': epoch,
                'updated_at': datetime.utcnow()
            }
            
            self.validators_collection.document(str(validator_uid)).set(validator_doc)
            
        except Exception as e:
            print(f"⚠️ Failed to update validator {validator_uid} last seen: {e}")
    
    async def _process_miner_status(self, validator_uid: int, miner_data: Dict):
        """Process individual miner status from validator"""
        try:
            miner_uid = miner_data.get('uid')
            if not miner_uid:
                print(f"⚠️ Skipping miner status without UID: {miner_data}")
                return
            
            # Get existing miner status
            miner_doc_ref = self.miner_status_collection.document(str(miner_uid))
            existing_doc = miner_doc_ref.get()
            
            if existing_doc.exists:
                # Update existing miner status with conflict resolution
                existing_data = existing_doc.to_dict()
                updated_data = self._resolve_miner_status_conflicts(existing_data, miner_data, validator_uid)
            else:
                # Create new miner status
                updated_data = self._create_new_miner_status(miner_data, validator_uid)
            
            # Update the document
            miner_doc_ref.set(updated_data)
            
            print(f"   ✅ Updated miner {miner_uid} status")
            
        except Exception as e:
            print(f"⚠️ Failed to process miner status: {e}")
    
    def _resolve_miner_status_conflicts(self, existing_data: Dict, new_data: Dict, validator_uid: str) -> Dict:
        """Resolve conflicts between existing and new miner status data"""
        try:
            # Add this validator to the list of reporters
            reported_by = existing_data.get('reported_by_validators', [])
            if validator_uid not in reported_by:
                reported_by.append(validator_uid)
            
            # Resolve conflicts using intelligent merging
            resolved_data = {
                'uid': existing_data['uid'],
                'hotkey': existing_data.get('hotkey', new_data.get('hotkey', '')),
                'ip': existing_data.get('ip', new_data.get('ip', '')),
                'port': existing_data.get('port', new_data.get('port', 0)),
                'external_ip': existing_data.get('external_ip', new_data.get('external_ip')),
                'external_port': existing_data.get('external_port', new_data.get('external_port')),
                'is_serving': existing_data.get('is_serving', False) or new_data.get('is_serving', False),  # Any True = True
                'stake': max(existing_data.get('stake', 0.0), new_data.get('stake', 0.0)),  # Take highest
                'performance_score': self._calculate_weighted_average(
                    existing_data.get('performance_score', 0.0),
                    new_data.get('performance_score', 0.0),
                    existing_data.get('reported_by_validators', []),
                    [validator_uid]
                ),
                'current_load': self._calculate_weighted_average(
                    existing_data.get('current_load', 0.0),
                    new_data.get('current_load', 0.0),
                    existing_data.get('reported_by_validators', []),
                    [validator_uid]
                ),
                'max_capacity': max(existing_data.get('max_capacity', 100.0), new_data.get('max_capacity', 100.0)),
                'task_type_specialization': self._resolve_specialization_conflict(
                    existing_data.get('task_type_specialization'),
                    new_data.get('task_type_specialization')
                ),
                'last_seen': datetime.utcnow(),
                'reported_by_validators': reported_by,
                'updated_at': datetime.utcnow()
            }
            
            return resolved_data
            
        except Exception as e:
            print(f"⚠️ Error resolving miner status conflicts: {e}")
            return existing_data
    
    def _create_new_miner_status(self, miner_data: Dict, validator_uid: str) -> Dict:
        """Create new miner status document"""
        try:
            return {
                'uid': miner_data.get('uid'),
                'hotkey': miner_data.get('hotkey', ''),
                'ip': miner_data.get('ip', ''),
                'port': miner_data.get('port', 0),
                'external_ip': miner_data.get('external_ip'),
                'external_port': miner_data.get('external_port'),
                'is_serving': miner_data.get('is_serving', True),
                'stake': miner_data.get('stake', 0.0),
                'performance_score': miner_data.get('performance_score', 0.0),
                'current_load': miner_data.get('current_load', 0.0),
                'max_capacity': miner_data.get('max_capacity', 100.0),
                'task_type_specialization': miner_data.get('task_type_specialization'),
                'last_seen': datetime.utcnow(),
                'reported_by_validators': [validator_uid],
                'updated_at': datetime.utcnow()
            }
            
        except Exception as e:
            print(f"⚠️ Error creating new miner status: {e}")
            return {}
    
    def _calculate_weighted_average(self, existing_value: float, new_value: float, 
                                   existing_reporters: List, new_reporters: List) -> float:
        """Calculate weighted average of conflicting values"""
        try:
            if not existing_reporters and not new_reporters:
                return (existing_value + new_value) / 2
            
            total_weight = len(existing_reporters) + len(new_reporters)
            weighted_sum = (existing_value * len(existing_reporters)) + (new_value * len(new_reporters))
            
            return weighted_sum / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            print(f"⚠️ Error calculating weighted average: {e}")
            return (existing_value + new_value) / 2
    
    def _resolve_specialization_conflict(self, existing_spec: Optional[str], new_spec: Optional[str]) -> Optional[str]:
        """Resolve task type specialization conflicts"""
        try:
            if not existing_spec and not new_spec:
                return None
            elif not existing_spec:
                return new_spec
            elif not new_spec:
                return existing_spec
            elif existing_spec == new_spec:
                return existing_spec
            else:
                # Different specializations - prefer the more specific one
                if 'transcription' in existing_spec and 'transcription' not in new_spec:
                    return existing_spec
                elif 'transcription' in new_spec and 'transcription' not in existing_spec:
                    return new_spec
                else:
                    # If both are equally specific, prefer existing
                    return existing_spec
                    
        except Exception as e:
            print(f"⚠️ Error resolving specialization conflict: {e}")
            return existing_spec or new_spec
    
    async def get_available_miners(self, task_type: str = None, min_count: int = 1, max_count: int = 5) -> List[Dict]:
        """Get list of available miners for task assignment"""
        try:
            # Get all miner status documents
            docs = self.miner_status_collection.stream()
            available_miners = []
            
            current_time = datetime.utcnow()
            
            for doc in docs:
                miner_data = doc.to_dict()
                
                # Check if miner is currently serving and recently seen
                if (miner_data.get('is_serving', False) and 
                    miner_data.get('last_seen') and
                    (current_time - miner_data['last_seen']).total_seconds() < self.miner_timeout):
                    
                    # Check task type specialization if specified
                    if task_type and miner_data.get('task_type_specialization'):
                        if task_type not in miner_data['task_type_specialization']:
                            continue
                    
                    # Calculate availability score
                    availability_score = self._calculate_miner_availability_score(miner_data)
                    
                    available_miners.append({
                        **miner_data,
                        'availability_score': availability_score
                    })
            
            # Sort by availability score (higher is better)
            available_miners.sort(key=lambda x: x.get('availability_score', 0), reverse=True)
            
            # Return requested number of miners
            return available_miners[:max_count]
            
        except Exception as e:
            print(f"❌ Error getting available miners: {e}")
            return []
    
    def _calculate_miner_availability_score(self, miner_data: Dict) -> float:
        """Calculate miner availability score for task assignment"""
        try:
            # Base score from performance
            performance_score = miner_data.get('performance_score', 0.0)
            
            # Load factor (lower load = higher score)
            current_load = miner_data.get('current_load', 0.0)
            max_capacity = miner_data.get('max_capacity', 100.0)
            load_factor = max(0.0, 1.0 - (current_load / max_capacity))
            
            # Stake factor (higher stake = higher score)
            stake = miner_data.get('stake', 0.0)
            stake_factor = min(1.0, stake / 1000.0)  # Normalize to 0-1
            
            # Recency factor (more recent = higher score)
            last_seen = miner_data.get('last_seen')
            if last_seen:
                recency_seconds = (datetime.utcnow() - last_seen).total_seconds()
                recency_factor = max(0.0, 1.0 - (recency_seconds / self.miner_timeout))
            else:
                recency_factor = 0.0
            
            # Weighted combination
            final_score = (
                performance_score * 0.4 +
                load_factor * 0.3 +
                stake_factor * 0.2 +
                recency_factor * 0.1
            )
            
            return max(0.0, min(1.0, final_score))
            
        except Exception as e:
            print(f"⚠️ Error calculating miner availability score: {e}")
            return 0.0
    
    async def cleanup_stale_validators(self):
        """Remove validators that haven't reported recently"""
        try:
            current_time = datetime.utcnow()
            timeout_threshold = current_time - timedelta(seconds=self.validator_timeout)
            
            # Find stale validators
            stale_validators = []
            docs = self.validators_collection.stream()
            
            for doc in docs:
                validator_data = doc.to_dict()
                last_seen = validator_data.get('last_seen')
                
                if last_seen and last_seen < timeout_threshold:
                    stale_validators.append(doc.id)
            
            # Remove stale validators
            for validator_id in stale_validators:
                self.validators_collection.document(validator_id).delete()
            
            if stale_validators:
                print(f"🧹 Cleaned up {len(stale_validators)} stale validators")
                
        except Exception as e:
            print(f"⚠️ Error cleaning up stale validators: {e}")
    
    async def cleanup_stale_miners(self):
        """Remove miners that haven't been reported recently"""
        try:
            current_time = datetime.utcnow()
            timeout_threshold = current_time - timedelta(seconds=self.miner_timeout)
            
            # Find stale miners
            stale_miners = []
            docs = self.miner_status_collection.stream()
            
            for doc in docs:
                miner_data = doc.to_dict()
                last_seen = miner_data.get('last_seen')
                
                if last_seen and last_seen < timeout_threshold:
                    stale_miners.append(doc.id)
            
            # Remove stale miners
            for miner_id in stale_miners:
                self.miner_status_collection.document(miner_id).delete()
            
            if stale_miners:
                print(f"🧹 Cleaned up {len(stale_miners)} stale miners")
                
        except Exception as e:
            print(f"⚠️ Error cleaning up stale miners: {e}")
    
    async def get_miner_status_summary(self) -> Dict[str, Any]:
        """Get summary of all miner statuses"""
        try:
            docs = self.miner_status_collection.stream()
            miners = []
            
            for doc in docs:
                miner_data = doc.to_dict()
                miners.append(miner_data)
            
            # Calculate statistics
            total_miners = len(miners)
            serving_miners = len([m for m in miners if m.get('is_serving', False)])
            online_miners = len([m for m in miners if m.get('last_seen') and 
                               (datetime.utcnow() - m['last_seen']).total_seconds() < self.miner_timeout])
            
            return {
                'total_miners': total_miners,
                'serving_miners': serving_miners,
                'online_miners': online_miners,
                'miners': miners
            }
            
        except Exception as e:
            print(f"❌ Error getting miner status summary: {e}")
            return {
                'total_miners': 0,
                'serving_miners': 0,
                'online_miners': 0,
                'miners': []
            }
