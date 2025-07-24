"""
Feedback Loop System for Indexing QA Observability Tool
Learns from human reviewer decisions to automatically adjust thresholds
Builds golden datasets and implements basic machine learning for continuous improvement
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
import statistics
import json

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models import (
    ReviewRecord, QualityCheckRecord, ChunkRecord, ThresholdConfiguration,
    GoldenDatasetRecord, ReviewerDecision, FlagStatus
)
from database import get_db_context
from config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


class ThresholdOptimizer:
    """
    Bayesian-inspired threshold optimization based on reviewer feedback
    Adjusts quality check thresholds to minimize false positives/negatives
    """
    
    def __init__(self):
        self.min_reviews_for_adjustment = 10  # Minimum reviews before adjusting
        self.adjustment_sensitivity = 0.1     # How much to adjust per iteration
        self.confidence_threshold = 0.8       # Confidence needed for major adjustments
        
    def analyze_reviewer_feedback(self, check_name: str, lookback_days: int = 30) -> Dict[str, Any]:
        """
        Analyze reviewer feedback for a specific quality check
        Returns metrics and recommendations for threshold adjustments
        """
        
        with get_db_context() as db:
            cutoff_date = datetime.now(datetime.UTC) - timedelta(days=lookback_days)
            
            # Get reviews for this specific check type
            reviews = db.query(
                ReviewRecord.decision,
                QualityCheckRecord.confidence_score,
                QualityCheckRecord.status,
                QualityCheckRecord.check_metadata
            ).join(
                QualityCheckRecord, ReviewRecord.chunk_id == QualityCheckRecord.chunk_id
            ).filter(
                QualityCheckRecord.check_name == check_name,
                ReviewRecord.reviewed_at >= cutoff_date
            ).all()
            
            if len(reviews) < self.min_reviews_for_adjustment:
                return {
                    "status": "insufficient_data",
                    "review_count": len(reviews),
                    "min_required": self.min_reviews_for_adjustment
                }
            
            # Categorize reviews
            true_positives = []   # Correctly flagged as bad (reviewer agrees)
            false_positives = []  # Incorrectly flagged as bad (reviewer disagrees)
            true_negatives = []   # Correctly passed (no flags, good content)
            false_negatives = []  # Should have been flagged but wasn't
            
            for decision, confidence, status, check_metadata in reviews:
                if status == FlagStatus.FAIL.value:
                    if decision == ReviewerDecision.TRUE_POSITIVE.value:
                        true_positives.append(confidence)
                    elif decision == ReviewerDecision.FALSE_POSITIVE.value:
                        false_positives.append(confidence)
                # Note: True/False negatives harder to track without explicit "should have been flagged" data
            
            # Calculate metrics
            total_flagged = len(true_positives) + len(false_positives)
            precision = len(true_positives) / total_flagged if total_flagged > 0 else 0
            
            # Analyze confidence score distributions
            tp_avg_confidence = statistics.mean(true_positives) if true_positives else 0
            fp_avg_confidence = statistics.mean(false_positives) if false_positives else 0
            
            return {
                "status": "sufficient_data",
                "review_count": len(reviews),
                "precision": precision,
                "true_positives": len(true_positives),
                "false_positives": len(false_positives),
                "tp_avg_confidence": tp_avg_confidence,
                "fp_avg_confidence": fp_avg_confidence,
                "confidence_gap": tp_avg_confidence - fp_avg_confidence,
                "recommendation": self._generate_threshold_recommendation(
                    precision, tp_avg_confidence, fp_avg_confidence
                )
            }
    
    def _generate_threshold_recommendation(
        self, 
        precision: float, 
        tp_confidence: float, 
        fp_confidence: float
    ) -> Dict[str, Any]:
        """Generate threshold adjustment recommendation"""
        
        confidence_gap = tp_confidence - fp_confidence
        
        if precision < 0.7:  # Low precision, too many false positives
            if confidence_gap > 0.2:  # Clear separation in confidence scores
                new_threshold = (tp_confidence + fp_confidence) / 2
                action = "increase_threshold"
                reason = f"Low precision ({precision:.2f}). Increase threshold to reduce false positives."
            else:
                new_threshold = fp_confidence + 0.1
                action = "increase_threshold_cautiously"
                reason = "Low precision with overlapping confidence scores. Cautious increase recommended."
        
        elif precision > 0.9:  # Very high precision, might be missing some issues
            new_threshold = max(0.1, tp_confidence - 0.1)
            action = "decrease_threshold"
            reason = f"High precision ({precision:.2f}). Consider lowering threshold to catch more issues."
        
        else:  # Acceptable precision
            action = "maintain_threshold"
            new_threshold = None
            reason = f"Precision ({precision:.2f}) is acceptable. No adjustment needed."
        
        return {
            "action": action,
            "new_threshold": new_threshold,
            "reason": reason,
            "confidence_level": min(0.9, confidence_gap * 2) if confidence_gap > 0 else 0.5
        }
    
    def apply_threshold_adjustments(self) -> List[Dict[str, Any]]:
        """
        Analyze all quality checks and apply threshold adjustments
        Returns list of adjustments made
        """
        
        adjustments_made = []
        
        # Get all quality check types
        with get_db_context() as db:
            check_types = db.query(QualityCheckRecord.check_name).distinct().all()
            check_types = [ct[0] for ct in check_types]
        
        for check_name in check_types:
            try:
                analysis = self.analyze_reviewer_feedback(check_name)
                
                if analysis["status"] != "sufficient_data":
                    continue
                
                recommendation = analysis["recommendation"]
                
                if recommendation["action"] in ["increase_threshold", "decrease_threshold"]:
                    new_threshold = recommendation["new_threshold"]
                    confidence = recommendation["confidence_level"]
                    
                    # Only apply if we're confident in the recommendation
                    if confidence >= self.confidence_threshold:
                        success = self._update_threshold_config(
                            check_name, 
                            new_threshold, 
                            recommendation["reason"],
                            analysis
                        )
                        
                        if success:
                            adjustments_made.append({
                                "check_name": check_name,
                                "action": recommendation["action"],
                                "old_threshold": None,  # TODO: Get current threshold
                                "new_threshold": new_threshold,
                                "reason": recommendation["reason"],
                                "confidence": confidence,
                                "analysis": analysis
                            })
            
            except Exception as e:
                logger.error(f"Failed to analyze feedback for {check_name}: {e}")
                continue
        
        return adjustments_made
    
    def _update_threshold_config(
        self, 
        check_name: str, 
        new_threshold: float, 
        reason: str,
        analysis: Dict[str, Any]
    ) -> bool:
        """Update threshold configuration in database"""
        
        try:
            with get_db_context() as db:
                # Get current config
                config = db.query(ThresholdConfiguration).filter(
                    ThresholdConfiguration.check_name == check_name
                ).first()
                
                if config:
                    old_threshold = config.threshold_value
                    config.threshold_value = new_threshold
                    config.updated_by = "feedback_loop_auto"
                    config.updated_at = datetime.now(datetime.UTC)
                    config.reason = reason
                    config.precision = analysis.get("precision")
                    config.true_positive_rate = analysis.get("true_positives", 0) / max(1, analysis.get("review_count", 1))
                    config.false_positive_rate = analysis.get("false_positives", 0) / max(1, analysis.get("review_count", 1))
                else:
                    # Create new config
                    config = ThresholdConfiguration(
                        check_name=check_name,
                        threshold_value=new_threshold,
                        confidence_cutoff=0.7,  # Default
                        updated_by="feedback_loop_auto",
                        reason=reason,
                        precision=analysis.get("precision")
                    )
                    db.add(config)
                
                db.commit()
                logger.info(f"Updated threshold for {check_name}: {old_threshold if 'old_threshold' in locals() else 'None'} -> {new_threshold}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update threshold config for {check_name}: {e}")
            return False


class GoldenDatasetBuilder:
    """
    Builds and maintains a golden dataset of known good/bad examples
    Uses reviewer decisions to create training data for future improvements
    """
    
    def __init__(self):
        self.min_confidence_for_golden = 0.8  # Minimum reviewer confidence for inclusion
        self.max_golden_per_check = 1000      # Limit golden examples per check type
        
    def build_golden_dataset_from_reviews(self, lookback_days: int = 90) -> Dict[str, int]:
        """
        Build golden dataset from reviewer decisions
        Returns count of golden examples added by category
        """
        
        with get_db_context() as db:
            cutoff_date = datetime.now(datetime.UTC) - timedelta(days=lookback_days)
            
            # Get high-confidence reviews
            high_confidence_reviews = db.query(
                ReviewRecord,
                ChunkRecord,
                QualityCheckRecord.check_name,
                QualityCheckRecord.status,
                QualityCheckRecord.confidence_score
            ).join(
                ChunkRecord, ReviewRecord.chunk_id == ChunkRecord.id
            ).join(
                QualityCheckRecord, ChunkRecord.id == QualityCheckRecord.chunk_id
            ).filter(
                ReviewRecord.reviewed_at >= cutoff_date,
                ReviewRecord.decision.in_([
                    ReviewerDecision.TRUE_POSITIVE.value,
                    ReviewerDecision.FALSE_POSITIVE.value
                ])
            ).all()
            
            added_counts = {"good_examples": 0, "bad_examples": 0, "updated_examples": 0}
            
            for review, chunk, check_name, check_status, confidence in high_confidence_reviews:
                try:
                    # Determine if this is a good or bad example
                    is_good_quality = (review.decision == ReviewerDecision.FALSE_POSITIVE.value)
                    
                    # Check if this example already exists
                    existing = db.query(GoldenDatasetRecord).filter(
                        GoldenDatasetRecord.record_id == chunk.record_id
                    ).first()
                    
                    if existing:
                        # Update existing record
                        existing.is_good_quality = is_good_quality
                        existing.confidence_level = confidence
                        existing.version += 1
                        existing.added_at = datetime.now(datetime.UTC)
                        added_counts["updated_examples"] += 1
                    else:
                        # Create new golden example
                        golden_record = GoldenDatasetRecord(
                            record_id=chunk.record_id,
                            document_text=chunk.document_text,
                            tags=chunk.tags,
                            source_connector=chunk.source_connector,
                            is_good_quality=is_good_quality,
                            expected_flags=[check_name] if not is_good_quality else [],
                            confidence_level=confidence,
                            added_by=f"reviewer_{review.reviewer_id}",
                            version=1,
                            active=True
                        )
                        
                        db.add(golden_record)
                        
                        if is_good_quality:
                            added_counts["good_examples"] += 1
                        else:
                            added_counts["bad_examples"] += 1
                
                except Exception as e:
                    logger.error(f"Failed to process review for golden dataset: {e}")
                    continue
            
            db.commit()
            
            # Clean up old/excess golden examples
            self._cleanup_golden_dataset(db)
            
            return added_counts
    
    def _cleanup_golden_dataset(self, db: Session):
        """Remove old or excess golden dataset examples"""
        
        # Get counts by quality type
        good_count = db.query(GoldenDatasetRecord).filter(
            GoldenDatasetRecord.is_good_quality == True,
            GoldenDatasetRecord.active == True
        ).count()
        
        bad_count = db.query(GoldenDatasetRecord).filter(
            GoldenDatasetRecord.is_good_quality == False,
            GoldenDatasetRecord.active == True
        ).count()
        
        # Remove excess good examples (keep most recent)
        if good_count > self.max_golden_per_check:
            excess_good = db.query(GoldenDatasetRecord).filter(
                GoldenDatasetRecord.is_good_quality == True,
                GoldenDatasetRecord.active == True
            ).order_by(GoldenDatasetRecord.added_at).limit(
                good_count - self.max_golden_per_check
            ).all()
            
            for record in excess_good:
                record.active = False
        
        # Remove excess bad examples
        if bad_count > self.max_golden_per_check:
            excess_bad = db.query(GoldenDatasetRecord).filter(
                GoldenDatasetRecord.is_good_quality == False,
                GoldenDatasetRecord.active == True
            ).order_by(GoldenDatasetRecord.added_at).limit(
                bad_count - self.max_golden_per_check
            ).all()
            
            for record in excess_bad:
                record.active = False
        
        db.commit()
    
    def get_golden_dataset_stats(self) -> Dict[str, Any]:
        """Get statistics about the golden dataset"""
        
        with get_db_context() as db:
            stats = {}
            
            # Total counts
            stats["total_examples"] = db.query(GoldenDatasetRecord).filter(
                GoldenDatasetRecord.active == True
            ).count()
            
            stats["good_examples"] = db.query(GoldenDatasetRecord).filter(
                GoldenDatasetRecord.is_good_quality == True,
                GoldenDatasetRecord.active == True
            ).count()
            
            stats["bad_examples"] = db.query(GoldenDatasetRecord).filter(
                GoldenDatasetRecord.is_good_quality == False,
                GoldenDatasetRecord.active == True
            ).count()
            
            # Source breakdown
            source_breakdown = db.query(
                GoldenDatasetRecord.source_connector,
                func.count(GoldenDatasetRecord.id)
            ).filter(
                GoldenDatasetRecord.active == True
            ).group_by(GoldenDatasetRecord.source_connector).all()
            
            stats["source_breakdown"] = {source: count for source, count in source_breakdown}
            
            # Average confidence
            avg_confidence = db.query(
                func.avg(GoldenDatasetRecord.confidence_level)
            ).filter(
                GoldenDatasetRecord.active == True
            ).scalar()
            
            stats["average_confidence"] = avg_confidence or 0.0
            
            return stats


class ContinuousLearningEngine:
    """
    Orchestrates the continuous learning process
    Combines threshold optimization and golden dataset building
    """
    
    def __init__(self):
        self.threshold_optimizer = ThresholdOptimizer()
        self.golden_builder = GoldenDatasetBuilder()
        
    def run_learning_cycle(self) -> Dict[str, Any]:
        """
        Run a complete learning cycle
        Returns summary of actions taken
        """
        
        cycle_start = datetime.now(datetime.UTC)
        results = {
            "cycle_start": cycle_start.isoformat(),
            "threshold_adjustments": [],
            "golden_dataset_updates": {},
            "errors": [],
            "summary": {}
        }
        
        try:
            # 1. Update golden dataset from recent reviews
            logger.info("Building golden dataset from reviewer feedback...")
            golden_updates = self.golden_builder.build_golden_dataset_from_reviews()
            results["golden_dataset_updates"] = golden_updates
            
            # 2. Optimize thresholds based on feedback
            logger.info("Analyzing reviewer feedback for threshold optimization...")
            adjustments = self.threshold_optimizer.apply_threshold_adjustments()
            results["threshold_adjustments"] = adjustments
            
            # 3. Generate summary
            results["summary"] = {
                "thresholds_adjusted": len(adjustments),
                "golden_examples_added": golden_updates.get("good_examples", 0) + golden_updates.get("bad_examples", 0),
                "golden_examples_updated": golden_updates.get("updated_examples", 0),
                "cycle_duration_seconds": (datetime.now(datetime.UTC) - cycle_start).total_seconds()
            }
            
            logger.info(f"Learning cycle completed: {results['summary']}")
            
        except Exception as e:
            error_msg = f"Learning cycle failed: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        return results
    
    def get_learning_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get recommendations for manual review based on learning analysis
        """
        
        recommendations = []
        
        try:
            with get_db_context() as db:
                # Find quality checks with high disagreement between system and reviewers
                disagreement_query = db.query(
                    QualityCheckRecord.check_name,
                    func.count(ReviewRecord.id).label('review_count'),
                    func.avg(
                        func.case(
                            (ReviewRecord.decision == ReviewerDecision.FALSE_POSITIVE.value, 1),
                            else_=0
                        )
                    ).label('disagreement_rate')
                ).join(
                    ReviewRecord, QualityCheckRecord.chunk_id == ReviewRecord.chunk_id
                ).filter(
                    QualityCheckRecord.status == FlagStatus.FAIL.value,
                    QualityCheckRecord.executed_at >= datetime.now(datetime.UTC) - timedelta(days=30)
                ).group_by(QualityCheckRecord.check_name).having(
                    func.count(ReviewRecord.id) >= 5  # Minimum reviews for analysis
                ).all()
                
                for check_name, review_count, disagreement_rate in disagreement_query:
                    if disagreement_rate > 0.4:  # More than 40% disagreement
                        recommendations.append({
                            "type": "high_disagreement",
                            "check_name": check_name,
                            "disagreement_rate": disagreement_rate,
                            "review_count": review_count,
                            "recommendation": f"Review {check_name} configuration - high reviewer disagreement ({disagreement_rate:.1%})",
                            "priority": "high" if disagreement_rate > 0.6 else "medium"
                        })
                
                # Find checks with insufficient reviewer feedback
                all_checks = db.query(QualityCheckRecord.check_name).distinct().all()
                for (check_name,) in all_checks:
                    recent_reviews = db.query(ReviewRecord).join(
                        QualityCheckRecord
                    ).filter(
                        QualityCheckRecord.check_name == check_name,
                        ReviewRecord.reviewed_at >= datetime.now(datetime.UTC) - timedelta(days=30)
                    ).count()
                    
                    if recent_reviews < 5:
                        recommendations.append({
                            "type": "insufficient_feedback",
                            "check_name": check_name,
                            "review_count": recent_reviews,
                            "recommendation": f"Need more reviewer feedback for {check_name} (only {recent_reviews} reviews in 30 days)",
                            "priority": "low"
                        })
        
        except Exception as e:
            logger.error(f"Failed to generate learning recommendations: {e}")
            recommendations.append({
                "type": "error",
                "recommendation": f"Failed to analyze learning data: {e}",
                "priority": "high"
            })
        
        return recommendations


# Scheduled tasks and utilities
async def run_daily_learning_cycle():
    """Daily learning cycle for continuous improvement"""
    
    try:
        learning_engine = ContinuousLearningEngine()
        results = learning_engine.run_learning_cycle()
        
        # Log results
        logger.info(f"Daily learning cycle completed: {results['summary']}")
        
        # Send alerts if significant changes
        if results['summary']['thresholds_adjusted'] > 0:
            from alerts import alert_manager
            await alert_manager.trigger_alert(
                alert_type="SYSTEM_UPDATE",
                severity="INFO",
                message=f"Automatic threshold adjustments applied: {results['summary']['thresholds_adjusted']} checks updated",
                details=results['summary']
            )
        
        return results
        
    except Exception as e:
        logger.error(f"Daily learning cycle failed: {e}")
        return {"error": str(e)}


def export_golden_dataset(file_format: str = "json") -> str:
    """Export golden dataset for external training or analysis"""
    
    with get_db_context() as db:
        golden_records = db.query(GoldenDatasetRecord).filter(
            GoldenDatasetRecord.active == True
        ).all()
        
        export_data = []
        for record in golden_records:
            export_data.append({
                "record_id": record.record_id,
                "document_text": record.document_text,
                "tags": record.tags,
                "source_connector": record.source_connector,
                "is_good_quality": record.is_good_quality,
                "expected_flags": record.expected_flags,
                "confidence_level": record.confidence_level,
                "added_by": record.added_by,
                "added_at": record.added_at.isoformat(),
                "version": record.version
            })
        
        if file_format == "json":
            import json
            filename = f"golden_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            return filename
        
        elif file_format == "csv":
            import pandas as pd
            df = pd.DataFrame(export_data)
            filename = f"golden_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            return filename
        
        else:
            raise ValueError(f"Unsupported export format: {file_format}") 