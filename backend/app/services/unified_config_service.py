"""
Unified Configuration Service - Single Source of Truth for All Thresholds
Follows SOLID principles to eliminate configuration conflicts and ensure real-time updates.
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import lru_cache
from pydantic import BaseModel

class ThresholdUpdate(BaseModel):
    """Model for threshold updates"""
    name: str
    value: float
    updated_by: str
    reason: str

class ConfigChangeEvent(BaseModel):
    """Model for configuration change events"""
    timestamp: datetime
    threshold_name: str
    old_value: float
    new_value: float
    updated_by: str
    reason: str

class UnifiedConfigService:
    """
    Single Source of Truth for all configuration management.
    Implements SOLID principles:
    - Single Responsibility: Only handles configuration
    - Open/Closed: Extensible without modification
    - Interface Segregation: Clear interface for config operations
    - Dependency Inversion: Other services depend on this abstraction
    """
    
    def __init__(self):
        self.config_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "core", "config.py"
        )
        self.runtime_overrides: Dict[str, float] = {}
        self.change_history: List[ConfigChangeEvent] = []
        
        # Initialize with current values from config.py
        self._load_current_config()
    
    def _load_current_config(self):
        """Load current configuration from config.py"""
        try:
            from ..core.config import get_settings
            settings = get_settings()
            
            # Load all threshold values into runtime_overrides for fast access
            self.runtime_overrides = {
                "approval_quality_score_threshold": float(settings.approval_quality_score_threshold),
                "quality_pass_rate_threshold": float(getattr(settings, 'quality_pass_rate_threshold', 95.0)),
                "quality_confidence_threshold": float(getattr(settings, 'quality_confidence_threshold', 0.8)),
                "llm_confidence_threshold": float(getattr(settings, 'llm_confidence_threshold', 0.6)),
                "llm_percentage_threshold": float(getattr(settings, 'llm_percentage_threshold', 85.0)),
                "llm_weighted_threshold": float(getattr(settings, 'llm_weighted_threshold', 0.8)),
                "llm_range_min_threshold": float(getattr(settings, 'llm_range_min_threshold', 70.0)),
                "llm_range_max_threshold": float(getattr(settings, 'llm_range_max_threshold', 80.0)),
                "spam_threshold": float(getattr(settings, 'spam_threshold', 0.3)),
                "stopword_threshold": float(getattr(settings, 'stopword_threshold', 0.5)),
                "context_coherence_threshold": float(getattr(settings, 'context_coherence_threshold', 0.1)),
                "cost_budget_daily_limit": float(getattr(settings, 'cost_budget_daily_limit', 100.0)),
                "cost_alert_threshold_percentage": float(getattr(settings, 'cost_alert_threshold_percentage', 80.0)),
                # Rules engine thresholds
                "min_tag_count": float(getattr(settings, 'min_tag_count', 1)),
                "max_tag_count": float(getattr(settings, 'max_tag_count', 50)),
                "min_content_length": float(getattr(settings, 'min_content_length', 10)),
                "max_content_length": float(getattr(settings, 'max_content_length', 50000)),
                "tag_text_relevance_threshold": float(getattr(settings, 'tag_text_relevance_threshold', 0.3)),
                "semantic_relevance_threshold": float(getattr(settings, 'semantic_relevance_threshold', 0.4)),
                "domain_relevance_threshold": float(getattr(settings, 'domain_relevance_threshold', 0.5)),
                "tag_specificity_threshold": float(getattr(settings, 'tag_specificity_threshold', 0.6)),
                "language_consistency_threshold": float(getattr(settings, 'language_consistency_threshold', 0.8)),
                
                # 🔧 NEW: Dynamic rule weights (no hardcoded values in Dynamic Rules Manager!)
                "empty_tags_weight": float(getattr(settings, 'empty_tags_weight', 1.0)),
                "tag_count_validation_weight": float(getattr(settings, 'tag_count_validation_weight', 0.8)),
                "text_quality_weight": float(getattr(settings, 'text_quality_weight', 1.2)),
                "stopwords_detection_weight": float(getattr(settings, 'stopwords_detection_weight', 0.6)),
                "spam_patterns_weight": float(getattr(settings, 'spam_patterns_weight', 1.5)),
                "duplicate_content_detection_weight": float(getattr(settings, 'duplicate_content_detection_weight', 0.9)),
                "tag_text_relevance_weight": float(getattr(settings, 'tag_text_relevance_weight', 1.1)),
                "semantic_relevance_weight": float(getattr(settings, 'semantic_relevance_weight', 1.3)),
                "domain_relevance_weight": float(getattr(settings, 'domain_relevance_weight', 1.0)),
                "tag_specificity_weight": float(getattr(settings, 'tag_specificity_weight', 0.8)),
                "context_coherence_weight": float(getattr(settings, 'context_coherence_weight', 0.9)),
            }
        except Exception as e:
            print(f"Warning: Could not load config.py settings: {e}")
            # Use safe defaults
            self.runtime_overrides = {
                "approval_quality_score_threshold": 50.0,
                "quality_pass_rate_threshold": 95.0,
                "quality_confidence_threshold": 0.8,
                "llm_confidence_threshold": 0.6,
                "spam_threshold": 0.3,
                "stopword_threshold": 0.5,
            }
    
    def get_threshold(self, threshold_name: str) -> Optional[float]:
        """
        Get threshold value - Single point of access for all threshold reads
        """
        return self.runtime_overrides.get(threshold_name)
    
    def update_threshold(self, update: ThresholdUpdate) -> bool:
        """
        Update threshold value - Single point of access for all threshold writes
        Ensures real-time updates and persistence with Dynamic Rules Manager sync
        """
        try:
            old_value = self.runtime_overrides.get(update.name, 0.0)
            
            # Update runtime value immediately for real-time effect
            self.runtime_overrides[update.name] = update.value
            
            # Record change event
            event = ConfigChangeEvent(
                timestamp=datetime.utcnow(),
                threshold_name=update.name,
                old_value=old_value,
                new_value=update.value,
                updated_by=update.updated_by,
                reason=update.reason
            )
            self.change_history.append(event)
            
            # Persist to config.py for permanent storage
            self._persist_to_config_file(update.name, update.value)
            
            # Clear settings cache to force reload
            self._clear_settings_cache()
            
            # 🔄 SYNC with Dynamic Rules Manager if threshold exists there
            try:
                from .dynamic_rules_manager import get_dynamic_rules_manager
                dynamic_manager = get_dynamic_rules_manager()
                
                # Check if this threshold exists in Dynamic Rules Manager
                if dynamic_manager.get_threshold(update.name) is not None:
                    # Update Dynamic Rules Manager to stay in sync
                    dynamic_manager.update_threshold_value(
                        threshold_name=update.name,
                        new_value=update.value,
                        changed_by=update.updated_by,
                        reason=f"Synced from UnifiedConfigService: {update.reason}"
                    )
                    print(f"🔄 Synced {update.name} = {update.value} to Dynamic Rules Manager")
                
                # 🔧 NEW: Sync rule weights if this is a rule weight update
                if update.name.endswith("_weight"):
                    rule_name = update.name.replace("_weight", "")
                    rule = dynamic_manager.get_rule(rule_name)
                    if rule is not None:
                        # Update the rule weight in Dynamic Rules Manager
                        dynamic_manager.update_rule_weight(
                            rule_name=rule_name,
                            new_weight=update.value,
                            changed_by=update.updated_by,
                            reason=f"Synced from UnifiedConfigService: {update.reason}"
                        )
                        print(f"🔄 Synced rule weight {rule_name} = {update.value} to Dynamic Rules Manager")
                    
            except Exception as sync_error:
                print(f"⚠️  Warning: Could not sync {update.name} with Dynamic Rules Manager: {sync_error}")
            
            return True
            
        except Exception as e:
            print(f"Error updating threshold {update.name}: {e}")
            return False
    
    def _persist_to_config_file(self, threshold_name: str, value: float):
        """Persist threshold change to config.py file"""
        try:
            # Read current config.py content
            with open(self.config_file_path, 'r') as f:
                content = f.read()
            
            # Update the specific threshold line
            import re
            pattern = rf"(\s*{threshold_name}:\s*float\s*=\s*)[0-9]+\.?[0-9]*"
            replacement = f"\\g<1>{value}"
            
            updated_content = re.sub(pattern, replacement, content)
            
            # Write back to file
            with open(self.config_file_path, 'w') as f:
                f.write(updated_content)
                
        except Exception as e:
            print(f"Warning: Could not persist {threshold_name} to config.py: {e}")
    
    def _clear_settings_cache(self):
        """Clear the LRU cache of settings to force reload"""
        try:
            from ..core.config import get_settings
            if hasattr(get_settings, 'cache_clear'):
                get_settings.cache_clear()
        except Exception as e:
            print(f"Warning: Could not clear settings cache: {e}")
    
    def get_all_thresholds(self) -> Dict[str, Any]:
        """Get all thresholds with metadata"""
        result = {}
        
        threshold_metadata = {
            "approval_quality_score_threshold": {
                "display_name": "Approval Quality Score Threshold",
                "description": "Quality score threshold for automatic approval (records >= this score are approved)",
                "category": "quality",
                "unit": "percentage",
                "min_value": 0.0,
                "max_value": 100.0
            },
            "quality_pass_rate_threshold": {
                "display_name": "Quality Pass Rate Threshold", 
                "description": "Minimum percentage of quality checks that must pass",
                "category": "quality",
                "unit": "percentage", 
                "min_value": 50.0,
                "max_value": 100.0
            },
            "llm_confidence_threshold": {
                "display_name": "LLM Confidence Threshold",
                "description": "Minimum confidence score required for LLM validation",
                "category": "llm",
                "unit": "score",
                "min_value": 0.0,
                "max_value": 1.0
            },
            "spam_threshold": {
                "display_name": "Spam Detection Threshold",
                "description": "Threshold for detecting spam content",
                "category": "rules",
                "unit": "score",
                "min_value": 0.0,
                "max_value": 1.0
            },
            "cost_alert_threshold_percentage": {
                "display_name": "Cost Alert Threshold",
                "description": "Percentage of budget that triggers cost alerts",
                "category": "cost",
                "unit": "percentage",
                "min_value": 50.0,
                "max_value": 100.0
            },
            # Rule Weight Metadata (NEW - makes rule weights configurable via frontend)
            "empty_tags_weight": {
                "display_name": "Empty Tags Rule Weight",
                "description": "Weight for empty tags validation rule",
                "category": "rules",
                "unit": "weight",
                "min_value": 0.0,
                "max_value": 3.0
            },
            "tag_count_validation_weight": {
                "display_name": "Tag Count Validation Weight",
                "description": "Weight for tag count validation rule",
                "category": "rules",
                "unit": "weight",
                "min_value": 0.0,
                "max_value": 3.0
            },
            "text_quality_weight": {
                "display_name": "Text Quality Rule Weight",
                "description": "Weight for text quality validation rule",
                "category": "rules",
                "unit": "weight",
                "min_value": 0.0,
                "max_value": 3.0
            },
            "semantic_relevance_weight": {
                "display_name": "Semantic Relevance Rule Weight",
                "description": "Weight for semantic relevance validation rule",
                "category": "rules",
                "unit": "weight",
                "min_value": 0.0,
                "max_value": 3.0
            },
            "spam_patterns_weight": {
                "display_name": "Spam Detection Rule Weight",
                "description": "Weight for spam pattern detection rule",
                "category": "rules",
                "unit": "weight",
                "min_value": 0.0,
                "max_value": 3.0
            },
            "domain_relevance_weight": {
                "display_name": "Domain Relevance Rule Weight",
                "description": "Weight for domain relevance validation rule",
                "category": "rules",
                "unit": "weight",
                "min_value": 0.0,
                "max_value": 3.0
            }
        }
        
        for name, value in self.runtime_overrides.items():
            metadata = threshold_metadata.get(name, {
                "display_name": name.replace("_", " ").title(),
                "description": f"Threshold for {name}",
                "category": "general",
                "unit": "value",
                "min_value": 0.0,
                "max_value": 100.0
            })
            
            result[name] = {
                "name": name,
                "current_value": value,
                "default_value": metadata.get("min_value", 0.0),
                **metadata
            }
        
        return result
    
    def get_change_history(self, limit: int = 50) -> List[ConfigChangeEvent]:
        """Get recent configuration changes"""
        return sorted(self.change_history, key=lambda x: x.timestamp, reverse=True)[:limit]


# Global singleton instance
_unified_config_service = None

def get_unified_config_service() -> UnifiedConfigService:
    """Get the global unified configuration service instance"""
    global _unified_config_service
    if _unified_config_service is None:
        _unified_config_service = UnifiedConfigService()
    return _unified_config_service 