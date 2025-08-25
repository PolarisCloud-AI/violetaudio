"""
Multi-Validator Manager for Enhanced Proxy Server
Handles miner status reports from multiple validators with conflict resolution
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from firebase_admin import firestore
import statistics

@dataclass
class ValidatorReport:
    """Individual validator report for a miner"""
    validator_uid: int
    miner_uid: int
    timestamp: datetime
    epoch: int
    miner_status: Dict[str, Any]
    confidence_score: float = 1.0  # Validator's confidence in this report
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'validator_uid': self.validator_uid,
            'miner_uid': self.miner_uid,
            'timestamp': self.timestamp,
            'epoch': self.epoch,
            'miner_status': self.miner_status,
            'confidence_score': self.confidence_score
        }

@dataclass
class MinerConsensusStatus:
    """Consensus status for a miner based on multiple validator reports"""
    miner_uid: int
    hotkey: str
    consensus_status: Dict[str, Any]
    validator_reports: List[ValidatorReport] = field(default_factory=list)
    last_consensus: datetime = field(default_factory=datetime.now)
    consensus_confidence: float = 0.0
    conflicting_reports: List[Tuple[int, str]] = field(default_factory=list)  # (validator_uid, conflict_type)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'miner_uid': self.miner_uid,
            'hotkey': self.hotkey,
            'consensus_status': self.consensus_status,
            'validator_reports_count': len(self.validator_reports),
            'last_consensus': self.last_consensus,
            'consensus_confidence': self.consensus_confidence,
            'conflicting_reports': self.conflicting_reports
        }

class MultiValidatorManager:
    """
    Manages miner status reports from multiple validators with conflict resolution
    """
    
    def __init__(self, db):
        self.db = db
        self.miner_status_collection = db.collection('miner_status')
        self.validator_reports_collection = db.collection('validator_reports')
        self.consensus_collection = db.collection('miner_consensus')
        
        # Configuration
        self.min_consensus_validators = 2  # Minimum validators needed for consensus
        self.consensus_timeout = timedelta(minutes=5)  # Time to wait for consensus
        self.max_conflict_threshold = 0.3  # Maximum allowed conflict ratio
        
        # In-memory cache for performance
        self.consensus_cache = {}
        self.last_cache_update = datetime.now()
        self.cache_ttl = timedelta(minutes=1)
    
    async def receive_validator_report(self, validator_uid: int, miner_statuses: List[Dict], epoch: int) -> Dict[str, Any]:
        """
        Receive and process miner status report from a validator
        
        Args:
            validator_uid: ID of the reporting validator
            miner_statuses: List of miner status reports
            epoch: Current Bittensor epoch
            
        Returns:
            Dict with processing results
        """
        try:
            print(f"📥 Processing miner status report from validator {validator_uid}")
            print(f"   Miners reported: {len(miner_statuses)}")
            print(f"   Epoch: {epoch}")
            
            processed_count = 0
            consensus_updated = 0
            
            for miner_status in miner_statuses:
                try:
                    miner_uid = miner_status.get('uid')
                    if miner_uid is None:
                        print(f"      ⚠️ Skipping miner without UID: {miner_status}")
                        continue
                    
                    # Store individual validator report
                    report = ValidatorReport(
                        validator_uid=validator_uid,
                        miner_uid=miner_uid,
                        timestamp=datetime.now(),
                        epoch=epoch,
                        miner_status=miner_status,
                        confidence_score=self._calculate_validator_confidence(validator_uid, miner_status)
                    )
                    
                    # Store report in database
                    await self._store_validator_report(report)
                    
                    # Update consensus status
                    consensus_updated += await self._update_miner_consensus(miner_uid)
                    
                    processed_count += 1
                    print(f"      ✅ Processed miner {miner_uid}: {miner_status.get('hotkey', 'unknown')}")
                    
                except Exception as e:
                    print(f"      ❌ Error processing miner {miner_status.get('uid', 'unknown')}: {e}")
                    continue
            
            # Update cache
            await self._update_consensus_cache()
            
            print(f"   Successfully processed {processed_count}/{len(miner_statuses)} miners")
            print(f"   Consensus updated for {consensus_updated} miners")
            
            return {
                "success": True,
                "miners_processed": processed_count,
                "consensus_updated": consensus_updated,
                "validator_uid": validator_uid,
                "epoch": epoch
            }
            
        except Exception as e:
            print(f"❌ Error processing validator report: {e}")
            return {
                "success": False,
                "error": str(e),
                "validator_uid": validator_uid
            }
    
    async def _store_validator_report(self, report: ValidatorReport):
        """Store individual validator report in database"""
        try:
            # Create unique document ID for this report
            doc_id = f"{report.validator_uid}_{report.miner_uid}_{report.timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            # Store in validator_reports collection
            report_ref = self.validator_reports_collection.document(doc_id)
            report_ref.set(report.to_dict())
            
            # Also update miner_status collection with latest report
            miner_ref = self.miner_status_collection.document(str(report.miner_uid))
            miner_ref.set({
                'last_updated': report.timestamp,
                'last_reported_by_validator': report.validator_uid,
                'epoch': report.epoch,
                'validator_reports_count': firestore.Increment(1)
            }, merge=True)
            
        except Exception as e:
            print(f"❌ Error storing validator report: {e}")
            raise
    
    async def _update_miner_consensus(self, miner_uid: int) -> int:
        """
        Update consensus status for a specific miner
        
        Returns:
            Number of consensus updates made
        """
        try:
            # Get all recent reports for this miner
            recent_reports = await self._get_recent_miner_reports(miner_uid)
            
            if len(recent_reports) < self.min_consensus_validators:
                print(f"      ⏳ Insufficient reports for consensus on miner {miner_uid}: {len(recent_reports)} < {self.min_consensus_validators}")
                return 0
            
            # Calculate consensus status
            consensus_status = await self._calculate_consensus_status(miner_uid, recent_reports)
            
            # Store consensus status
            consensus_ref = self.consensus_collection.document(str(miner_uid))
            consensus_ref.set({
                'miner_uid': miner_uid,
                'consensus_status': consensus_status,
                'last_consensus': datetime.now(),
                'validator_reports_count': len(recent_reports),
                'consensus_confidence': consensus_status.get('confidence', 0.0)
            }, merge=True)
            
            # Update cache
            self.consensus_cache[miner_uid] = consensus_status
            
            return 1
            
        except Exception as e:
            print(f"❌ Error updating miner consensus {miner_uid}: {e}")
            return 0
    
    async def _get_recent_miner_reports(self, miner_uid: int) -> List[ValidatorReport]:
        """Get recent validator reports for a specific miner"""
        try:
            # Query recent reports (within consensus timeout)
            cutoff_time = datetime.now() - self.consensus_timeout
            
            query = self.validator_reports_collection.where('miner_uid', '==', miner_uid)
            docs = query.stream()
            
            recent_reports = []
            for doc in docs:
                report_data = doc.to_dict()
                report_timestamp = report_data['timestamp']
                
                # Convert Firestore timestamp to datetime if needed
                if hasattr(report_timestamp, 'timestamp'):
                    report_timestamp = datetime.fromtimestamp(report_timestamp.timestamp())
                
                if report_timestamp >= cutoff_time:
                    recent_reports.append(ValidatorReport(**report_data))
            
            return recent_reports
            
        except Exception as e:
            print(f"❌ Error getting recent miner reports: {e}")
            return []
    
    async def _calculate_consensus_status(self, miner_uid: int, reports: List[ValidatorReport]) -> Dict[str, Any]:
        """
        Calculate consensus status from multiple validator reports
        
        Args:
            miner_uid: ID of the miner
            reports: List of validator reports
            
        Returns:
            Consensus status dictionary
        """
        try:
            if not reports:
                return {}
            
            # Group reports by validator
            validator_reports = {}
            for report in reports:
                if report.validator_uid not in validator_reports:
                    validator_reports[report.validator_uid] = []
                validator_reports[report.validator_uid].append(report)
            
            # Calculate consensus for each field
            consensus_status = {}
            conflicts = []
            
            # Get all possible fields from reports
            all_fields = set()
            for report in reports:
                all_fields.update(report.miner_status.keys())
            
            for field in all_fields:
                field_values = []
                field_weights = []
                
                for report in reports:
                    if field in report.miner_status:
                        field_values.append(report.miner_status[field])
                        field_weights.append(report.confidence_score)
                
                if not field_values:
                    continue
                
                # Handle different field types
                if field in ['stake', 'performance_score', 'current_load']:
                    # Numeric fields - use weighted average
                    consensus_value = self._weighted_average(field_values, field_weights)
                    consensus_status[field] = consensus_value
                    
                elif field in ['is_serving', 'hotkey']:
                    # Boolean/String fields - use majority vote
                    consensus_value, conflict = self._majority_vote(field_values, field_weights)
                    consensus_status[field] = consensus_value
                    if conflict:
                        conflicts.append((field, conflict))
                        
                else:
                    # Other fields - use most recent high-confidence report
                    consensus_value = self._most_recent_high_confidence(field_values, field_weights, reports)
                    consensus_status[field] = consensus_value
            
            # Add consensus metadata
            consensus_status['consensus_timestamp'] = datetime.now()
            consensus_status['consensus_validators'] = list(validator_reports.keys())
            consensus_status['consensus_confidence'] = self._calculate_overall_confidence(reports)
            consensus_status['conflicts_detected'] = conflicts
            
            return consensus_status
            
        except Exception as e:
            print(f"❌ Error calculating consensus status: {e}")
            return {}
    
    def _weighted_average(self, values: List[float], weights: List[float]) -> float:
        """Calculate weighted average of numeric values"""
        if not values or not weights:
            return 0.0
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return sum(values) / len(values)
        
        weighted_sum = sum(v * w for v, w in zip(values, weights))
        return weighted_sum / total_weight
    
    def _majority_vote(self, values: List[Any], weights: List[float]) -> Tuple[Any, bool]:
        """Calculate majority vote with conflict detection"""
        if not values:
            return None, False
        
        # Count occurrences
        value_counts = {}
        for value, weight in zip(values, weights):
            if value not in value_counts:
                value_counts[value] = 0
            value_counts[value] += weight
        
        # Find majority
        total_weight = sum(weights)
        majority_threshold = total_weight * 0.6  # 60% threshold
        
        for value, count in value_counts.items():
            if count >= majority_threshold:
                return value, False
        
        # No clear majority - conflict detected
        return values[0], True  # Return first value as fallback
    
    def _most_recent_high_confidence(self, values: List[Any], weights: List[float], reports: List[ValidatorReport]) -> Any:
        """Get most recent value from high-confidence reports"""
        if not values or not reports:
            return None
        
        # Find report with highest confidence
        max_confidence = max(weights)
        high_confidence_reports = [r for r, w in zip(reports, weights) if w >= max_confidence * 0.8]
        
        if high_confidence_reports:
            # Return value from most recent high-confidence report
            most_recent = max(high_confidence_reports, key=lambda r: r.timestamp)
            return most_recent.miner_status.get(list(most_recent.miner_status.keys())[0])
        
        # Fallback to first value
        return values[0]
    
    def _calculate_overall_confidence(self, reports: List[ValidatorReport]) -> float:
        """Calculate overall confidence score for consensus"""
        if not reports:
            return 0.0
        
        # Average confidence of all reports
        avg_confidence = sum(r.confidence_score for r in reports) / len(reports)
        
        # Bonus for having multiple validators
        validator_bonus = min(0.2, len(set(r.validator_uid for r in reports)) * 0.1)
        
        # Penalty for conflicts
        conflict_penalty = 0.0
        # TODO: Implement conflict detection penalty
        
        return min(1.0, avg_confidence + validator_bonus - conflict_penalty)
    
    def _calculate_validator_confidence(self, validator_uid: int, miner_status: Dict[str, Any]) -> float:
        """Calculate confidence score for a validator's report"""
        try:
            # Base confidence
            confidence = 1.0
            
            # Penalty for incomplete data
            required_fields = ['uid', 'hotkey', 'stake', 'is_serving']
            missing_fields = [f for f in required_fields if f not in miner_status]
            if missing_fields:
                confidence -= len(missing_fields) * 0.1
            
            # Bonus for detailed data
            detailed_fields = ['performance_score', 'current_load', 'task_type_specialization']
            detailed_count = sum(1 for f in detailed_fields if f in miner_status)
            confidence += detailed_count * 0.05
            
            # Bonus for recent data
            if 'last_seen' in miner_status:
                try:
                    last_seen = datetime.fromisoformat(miner_status['last_seen'])
                    time_diff = datetime.now() - last_seen
                    if time_diff < timedelta(minutes=5):
                        confidence += 0.1
                    elif time_diff < timedelta(minutes=15):
                        confidence += 0.05
                except:
                    pass
            
            return max(0.1, min(1.0, confidence))
            
        except Exception as e:
            print(f"❌ Error calculating validator confidence: {e}")
            return 0.5
    
    async def get_consensus_miner_status(self, miner_uid: int) -> Optional[Dict[str, Any]]:
        """Get consensus status for a specific miner"""
        try:
            # Check cache first
            if miner_uid in self.consensus_cache:
                cache_age = datetime.now() - self.last_cache_update
                if cache_age < self.cache_ttl:
                    return self.consensus_cache[miner_uid]
            
            # Query database
            consensus_ref = self.consensus_collection.document(str(miner_uid))
            consensus_doc = consensus_ref.get()
            
            if consensus_doc.exists:
                consensus_data = consensus_doc.to_dict()
                consensus_status = consensus_data.get('consensus_status', {})
                
                # Update cache
                self.consensus_cache[miner_uid] = consensus_status
                return consensus_status
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting consensus miner status: {e}")
            return None
    
    async def get_all_consensus_miners(self) -> List[Dict[str, Any]]:
        """Get consensus status for all miners"""
        try:
            # Query all consensus documents
            docs = self.consensus_collection.stream()
            
            miners = []
            for doc in docs:
                consensus_data = doc.to_dict()
                miner_uid = consensus_data.get('miner_uid')
                
                if miner_uid:
                    consensus_status = consensus_data.get('consensus_status', {})
                    consensus_status['miner_uid'] = miner_uid
                    consensus_status['consensus_confidence'] = consensus_data.get('consensus_confidence', 0.0)
                    consensus_status['last_consensus'] = consensus_data.get('last_consensus')
                    
                    miners.append(consensus_status)
            
            return miners
            
        except Exception as e:
            print(f"❌ Error getting all consensus miners: {e}")
            return []
    
    async def _update_consensus_cache(self):
        """Update in-memory consensus cache"""
        try:
            self.last_cache_update = datetime.now()
            # Cache is updated incrementally in _update_miner_consensus
            
        except Exception as e:
            print(f"❌ Error updating consensus cache: {e}")
    
    async def get_validator_report_stats(self) -> Dict[str, Any]:
        """Get statistics about validator reports and consensus"""
        try:
            # Count total reports
            total_reports = len(list(self.validator_reports_collection.stream()))
            
            # Count consensus miners
            consensus_miners = len(list(self.consensus_collection.stream()))
            
            # Count active validators
            active_validators = set()
            recent_reports = self.validator_reports_collection.where('timestamp', '>=', datetime.now() - timedelta(hours=1))
            for doc in recent_reports.stream():
                active_validators.add(doc.to_dict().get('validator_uid'))
            
            # Calculate consensus confidence distribution
            confidence_scores = []
            for doc in self.consensus_collection.stream():
                confidence = doc.to_dict().get('consensus_confidence', 0.0)
                confidence_scores.append(confidence)
            
            avg_confidence = statistics.mean(confidence_scores) if confidence_scores else 0.0
            
            return {
                'total_validator_reports': total_reports,
                'consensus_miners': consensus_miners,
                'active_validators': len(active_validators),
                'average_consensus_confidence': avg_confidence,
                'consensus_timeout_minutes': self.consensus_timeout.total_seconds() / 60,
                'min_consensus_validators': self.min_consensus_validators
            }
            
        except Exception as e:
            print(f"❌ Error getting validator report stats: {e}")
            return {}
