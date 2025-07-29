# =============================================================================
# DYNAMIC RULES MANAGER - REAL-TIME THRESHOLD & WEIGHT MANAGEMENT
# =============================================================================
# Comprehensive system for managing quality rules, thresholds, and weights
# with real-time updates and persistence

import json
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path

from ..core.config import get_settings


class RuleCategory(str, Enum):
    """Categories for organizing rules"""
    CONTENT_QUALITY = "content_quality"
    TAG_VALIDATION = "tag_validation" 
    SEMANTIC_ANALYSIS = "semantic_analysis"
    SPAM_DETECTION = "spam_detection"
    DUPLICATE_DETECTION = "duplicate_detection"
    DOMAIN_SPECIFIC = "domain_specific"


class RuleSeverity(str, Enum):
    """Severity levels for rules"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RuleDefinition:
    """Definition of a quality rule with all its parameters"""
    name: str
    display_name: str
    description: str
    category: RuleCategory
    severity: RuleSeverity
    weight: float = 1.0
    enabled: bool = True
    threshold_value: Optional[float] = None
    min_threshold: Optional[float] = None
    max_threshold: Optional[float] = None
    threshold_unit: str = "score"
    auto_fixable: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class QualityThreshold:
    """Dynamic threshold configuration"""
    name: str
    display_name: str
    current_value: float
    default_value: float
    min_value: float
    max_value: float
    description: str
    category: str
    unit: str
    affects_rules: List[str]  # Which rules are affected by this threshold
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DynamicRulesManager:
    """
    Comprehensive manager for dynamic rules, thresholds, and weights
    Provides real-time updates with persistence and notification system
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.settings = get_settings()
        self.db_path = db_path or "backend/dynamic_rules.db"
        self._lock = threading.RLock()
        self._subscribers = []  # Components that want to be notified of changes
        
        # Initialize storage
        self._init_database()
        
        # Load default configurations
        self.rules: Dict[str, RuleDefinition] = {}
        self.thresholds: Dict[str, QualityThreshold] = {}
        
        # Load from database or create defaults
        self._load_configurations()
        
        print(f"✅ Dynamic Rules Manager initialized with {len(self.rules)} rules and {len(self.thresholds)} thresholds")
    
    def _init_database(self):
        """Initialize SQLite database for persistence"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Rules table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS rules (
                        name TEXT PRIMARY KEY,
                        display_name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        category TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        weight REAL NOT NULL DEFAULT 1.0,
                        enabled BOOLEAN NOT NULL DEFAULT 1,
                        threshold_value REAL,
                        min_threshold REAL,
                        max_threshold REAL,
                        threshold_unit TEXT DEFAULT 'score',
                        auto_fixable BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Thresholds table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS thresholds (
                        name TEXT PRIMARY KEY,
                        display_name TEXT NOT NULL,
                        current_value REAL NOT NULL,
                        default_value REAL NOT NULL,
                        min_value REAL NOT NULL,
                        max_value REAL NOT NULL,
                        description TEXT NOT NULL,
                        category TEXT NOT NULL,
                        unit TEXT NOT NULL,
                        affects_rules TEXT NOT NULL,  -- JSON array of rule names
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Changes history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS changes_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        change_type TEXT NOT NULL,  -- 'rule' or 'threshold'
                        item_name TEXT NOT NULL,
                        field_name TEXT NOT NULL,
                        old_value TEXT,
                        new_value TEXT,
                        changed_by TEXT,
                        reason TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                print("✅ Dynamic rules database initialized")
                
        except Exception as e:
            print(f"❌ Failed to initialize dynamic rules database: {e}")
            raise
    
    def _load_configurations(self):
        """Load configurations from database or create defaults"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Load rules
                cursor.execute("SELECT COUNT(*) FROM rules")
                rules_count = cursor.fetchone()[0]
                
                if rules_count == 0:
                    print("📝 Creating default rule configurations...")
                    self._create_default_rules()
                else:
                    print(f"📖 Loading {rules_count} rules from database...")
                    self._load_rules_from_db()
                
                # Load thresholds
                cursor.execute("SELECT COUNT(*) FROM thresholds")
                thresholds_count = cursor.fetchone()[0]
                
                if thresholds_count == 0:
                    print("📝 Creating default threshold configurations...")
                    self._create_default_thresholds()
                else:
                    print(f"📖 Loading {thresholds_count} thresholds from database...")
                    self._load_thresholds_from_db()
                    
        except Exception as e:
            print(f"❌ Failed to load configurations: {e}")
            # Fallback to in-memory defaults
            self._create_default_rules()
            self._create_default_thresholds()
    
    def _create_default_rules(self):
        """Create default rule definitions using dynamic Unified Config values (no hardcoded weights!)"""
        
        # 🔧 Get current values from Unified Config Service instead of hardcoded defaults
        try:
            from .unified_config_service import get_unified_config_service
            config_service = get_unified_config_service()
            print("🔄 Getting rule weights from Unified Config Service...")
        except Exception as e:
            print(f"⚠️  Warning: Could not load Unified Config Service for rules: {e}")
            config_service = None
        
        # Helper function to get dynamic weight value or fallback
        def get_dynamic_weight(rule_name: str, fallback: float) -> float:
            if config_service:
                # Try to get weight from rule weights configuration
                weight = config_service.get_threshold(f"{rule_name}_weight")
                if weight is not None:
                    print(f"   🎯 {rule_name} weight: {weight} (from Unified Config)")
                    return weight
            print(f"   ⚠️  {rule_name} weight: {fallback} (fallback - Unified Config unavailable)")
            return fallback
        
        default_rules = [
            RuleDefinition(
                name="empty_tags",
                display_name="Empty Tags Check",
                description="Validates that content has meaningful tags",
                category=RuleCategory.TAG_VALIDATION,
                severity=RuleSeverity.HIGH,
                weight=get_dynamic_weight("empty_tags", 1.0),
                threshold_value=1.0,
                auto_fixable=True
            ),
            RuleDefinition(
                name="tag_count_validation",
                display_name="Tag Count Validation", 
                description="Ensures tag count is within reasonable bounds",
                category=RuleCategory.TAG_VALIDATION,
                severity=RuleSeverity.MEDIUM,
                weight=get_dynamic_weight("tag_count_validation", 0.8),
                threshold_value=0.8
            ),
            RuleDefinition(
                name="text_quality",
                display_name="Text Quality Check",
                description="Validates text length and meaningful content",
                category=RuleCategory.CONTENT_QUALITY,
                severity=RuleSeverity.HIGH,
                weight=get_dynamic_weight("text_quality", 1.2),
                threshold_value=0.7
            ),
            RuleDefinition(
                name="stopwords_detection",
                display_name="Stopwords Detection",
                description="Detects excessive generic/meaningless terms",
                category=RuleCategory.TAG_VALIDATION,
                severity=RuleSeverity.MEDIUM,
                weight=get_dynamic_weight("stopwords_detection", 0.6),
                threshold_value=0.5
            ),
            RuleDefinition(
                name="spam_patterns",
                display_name="Spam Pattern Detection",
                description="Identifies spam and low-quality content patterns",
                category=RuleCategory.SPAM_DETECTION,
                severity=RuleSeverity.CRITICAL,
                weight=get_dynamic_weight("spam_patterns", 1.5),
                threshold_value=0.3
            ),
            RuleDefinition(
                name="duplicate_content_detection", 
                display_name="Duplicate Content Detection",
                description="Detects duplicate or near-duplicate content",
                category=RuleCategory.DUPLICATE_DETECTION,
                severity=RuleSeverity.MEDIUM,
                weight=get_dynamic_weight("duplicate_content_detection", 0.9),
                threshold_value=0.85
            ),
            RuleDefinition(
                name="tag_text_relevance",
                display_name="Tag-Text Relevance",
                description="Checks relevance between tags and text content",
                category=RuleCategory.SEMANTIC_VALIDATION,
                severity=RuleSeverity.HIGH,
                weight=get_dynamic_weight("tag_text_relevance", 1.1),
                threshold_value=0.3
            ),
            RuleDefinition(
                name="semantic_relevance",
                display_name="Semantic Relevance",
                description="Validates semantic consistency between tags and content",
                category=RuleCategory.SEMANTIC_VALIDATION,
                severity=RuleSeverity.HIGH,
                weight=get_dynamic_weight("semantic_relevance", 1.3),
                threshold_value=0.4
            ),
            RuleDefinition(
                name="domain_relevance",
                display_name="Domain Relevance",
                description="Checks domain-specific relevance of content",
                category=RuleCategory.SEMANTIC_VALIDATION,
                severity=RuleSeverity.MEDIUM,
                weight=get_dynamic_weight("domain_relevance", 1.0),
                threshold_value=0.5
            ),
            RuleDefinition(
                name="tag_specificity",
                display_name="Tag Specificity",
                description="Validates specificity and meaningfulness of tags",
                category=RuleCategory.TAG_VALIDATION,
                severity=RuleSeverity.MEDIUM,
                weight=get_dynamic_weight("tag_specificity", 0.8),
                threshold_value=0.6
            ),
            RuleDefinition(
                name="context_coherence",
                display_name="Context Coherence",
                description="Validates coherence and consistency of content context",
                category=RuleCategory.CONTENT_QUALITY,
                severity=RuleSeverity.MEDIUM,
                weight=get_dynamic_weight("context_coherence", 0.9),
                threshold_value=0.1
            )
        ]
        
        print(f"🔧 Created {len(default_rules)} rules with dynamic Unified Config weights")
        
        for rule in default_rules:
            self.rules[rule.name] = rule
            self._save_rule_to_db(rule)
    
    def _create_default_thresholds(self):
        """Create default threshold configurations using Unified Config values (no hardcoded values!)"""
        
        # 🔧 Get current values from Unified Config Service instead of hardcoded defaults
        try:
            from .unified_config_service import get_unified_config_service
            config_service = get_unified_config_service()
            print("🔄 Getting threshold values from Unified Config Service...")
        except Exception as e:
            print(f"⚠️  Warning: Could not load Unified Config Service: {e}")
            config_service = None
        
        # Helper function to get dynamic value or fallback
        def get_dynamic_value(threshold_name: str, fallback: float) -> float:
            if config_service:
                value = config_service.get_threshold(threshold_name)
                if value is not None:
                    print(f"   📊 {threshold_name}: {value} (from Unified Config)")
                    return value
            print(f"   ⚠️  {threshold_name}: {fallback} (fallback - Unified Config unavailable)")
            return fallback
        
        default_thresholds = [
            QualityThreshold(
                name="approval_quality_score_threshold",
                display_name="Approval Quality Score",
                current_value=get_dynamic_value("approval_quality_score_threshold", 50.0),
                default_value=50.0,
                min_value=0.0,
                max_value=100.0,
                description="Minimum quality score for automatic approval",
                category="quality",
                unit="percentage",
                affects_rules=[]
            ),
            QualityThreshold(
                name="semantic_relevance_threshold",
                display_name="Semantic Relevance Threshold",
                current_value=get_dynamic_value("semantic_relevance_threshold", 0.15),
                default_value=0.15,
                min_value=0.0,
                max_value=1.0,
                description="Minimum semantic relevance score between tags and content",
                category="semantic",
                unit="score",
                affects_rules=["semantic_relevance"]
            ),
            QualityThreshold(
                name="domain_relevance_threshold",
                display_name="Domain Relevance Threshold",
                current_value=get_dynamic_value("domain_relevance_threshold", 0.1),
                default_value=0.1,
                min_value=0.0,
                max_value=1.0,
                description="Minimum domain-specific relevance score",
                category="semantic",
                unit="score",
                affects_rules=["domain_relevance"]
            ),
            QualityThreshold(
                name="tag_specificity_threshold",
                display_name="Tag Specificity Threshold",
                current_value=get_dynamic_value("tag_specificity_threshold", 0.2),
                default_value=0.2,
                min_value=0.0,
                max_value=1.0,
                description="Minimum tag specificity score",
                category="semantic",
                unit="score",
                affects_rules=["tag_specificity"]
            ),
            QualityThreshold(
                name="context_coherence_threshold",
                display_name="Context Coherence Threshold",
                current_value=get_dynamic_value("context_coherence_threshold", 0.1),
                default_value=0.1,
                min_value=0.0,
                max_value=1.0,
                description="Minimum context coherence score",
                category="semantic",
                unit="score",
                affects_rules=["context_coherence"]
            ),
            QualityThreshold(
                name="tag_text_relevance_threshold",
                display_name="Tag-Text Relevance Threshold",
                current_value=get_dynamic_value("tag_text_relevance_threshold", 0.3),
                default_value=0.3,
                min_value=0.0,
                max_value=1.0,
                description="Minimum relevance between tags and text content",
                category="semantic",
                unit="score",
                affects_rules=["tag_text_relevance"]
            ),
            QualityThreshold(
                name="spam_threshold",
                display_name="Spam Detection Threshold",
                current_value=get_dynamic_value("spam_threshold", 0.3),
                default_value=0.3,
                min_value=0.0,
                max_value=1.0,
                description="Maximum spam probability threshold",
                category="content",
                unit="probability",
                affects_rules=["spam_patterns"]
            ),
            QualityThreshold(
                name="stopword_threshold",
                display_name="Stopword Ratio Threshold",
                current_value=get_dynamic_value("stopword_threshold", 0.5),
                default_value=0.5,
                min_value=0.0,
                max_value=1.0,
                description="Maximum stopword ratio threshold",
                category="content",
                unit="ratio",
                affects_rules=["stopwords_detection"]
            ),
            QualityThreshold(
                name="language_consistency_threshold",
                display_name="Language Consistency Threshold",
                current_value=get_dynamic_value("language_consistency_threshold", 0.8),
                default_value=0.8,
                min_value=0.0,
                max_value=1.0,
                description="Minimum language consistency score",
                category="content",
                unit="score",
                affects_rules=["language_consistency"]
            ),
            QualityThreshold(
                name="min_tag_count",
                display_name="Minimum Tag Count",
                current_value=get_dynamic_value("min_tag_count", 1),
                default_value=1,
                min_value=0,
                max_value=50,
                description="Minimum number of tags required",
                category="tags",
                unit="count",
                affects_rules=["tag_count_validation", "empty_tags"]
            ),
            QualityThreshold(
                name="max_tag_count",
                display_name="Maximum Tag Count",
                current_value=get_dynamic_value("max_tag_count", 20),
                default_value=20,
                min_value=1,
                max_value=100,
                description="Maximum number of tags allowed",
                category="tags",
                unit="count",
                affects_rules=["tag_count_validation"]
            )
        ]
        
        print(f"🔧 Created {len(default_thresholds)} thresholds with dynamic Unified Config values")
        
        for threshold in default_thresholds:
            self.thresholds[threshold.name] = threshold
            self._save_threshold_to_db(threshold)
    
    def _load_rules_from_db(self):
        """Load rules from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM rules")
                
                for row in cursor.fetchall():
                    rule = RuleDefinition(
                        name=row[0],
                        display_name=row[1],
                        description=row[2],
                        category=RuleCategory(row[3]),
                        severity=RuleSeverity(row[4]),
                        weight=row[5],
                        enabled=bool(row[6]),
                        threshold_value=row[7],
                        min_threshold=row[8],
                        max_threshold=row[9],
                        threshold_unit=row[10],
                        auto_fixable=bool(row[11])
                    )
                    self.rules[rule.name] = rule
                    
        except Exception as e:
            print(f"❌ Failed to load rules from database: {e}")
    
    def _load_thresholds_from_db(self):
        """Load thresholds from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM thresholds")
                
                for row in cursor.fetchall():
                    threshold = QualityThreshold(
                        name=row[0],
                        display_name=row[1],
                        current_value=row[2],
                        default_value=row[3],
                        min_value=row[4],
                        max_value=row[5],
                        description=row[6],
                        category=row[7],
                        unit=row[8],
                        affects_rules=json.loads(row[9]) if row[9] else []
                    )
                    self.thresholds[threshold.name] = threshold
                    
        except Exception as e:
            print(f"❌ Failed to load thresholds from database: {e}")
    
    def _save_rule_to_db(self, rule: RuleDefinition):
        """Save rule to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO rules 
                    (name, display_name, description, category, severity, weight, enabled,
                     threshold_value, min_threshold, max_threshold, threshold_unit, auto_fixable)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    rule.name, rule.display_name, rule.description, rule.category.value, 
                    rule.severity.value, rule.weight, rule.enabled, rule.threshold_value,
                    rule.min_threshold, rule.max_threshold, rule.threshold_unit, rule.auto_fixable
                ))
                conn.commit()
        except Exception as e:
            print(f"❌ Failed to save rule {rule.name}: {e}")
    
    def _save_threshold_to_db(self, threshold: QualityThreshold):
        """Save threshold to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO thresholds 
                    (name, display_name, current_value, default_value, min_value, max_value,
                     description, category, unit, affects_rules)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    threshold.name, threshold.display_name, threshold.current_value,
                    threshold.default_value, threshold.min_value, threshold.max_value,
                    threshold.description, threshold.category, threshold.unit,
                    json.dumps(threshold.affects_rules)
                ))
                conn.commit()
        except Exception as e:
            print(f"❌ Failed to save threshold {threshold.name}: {e}")
    
    def _record_change(self, change_type: str, item_name: str, field_name: str, 
                      old_value: Any, new_value: Any, changed_by: str, reason: str):
        """Record configuration change to history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO changes_history 
                    (change_type, item_name, field_name, old_value, new_value, changed_by, reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (change_type, item_name, field_name, str(old_value), str(new_value), changed_by, reason))
                conn.commit()
        except Exception as e:
            print(f"❌ Failed to record change: {e}")
    
    def _notify_subscribers(self, change_type: str, item_name: str, old_value: Any, new_value: Any):
        """Notify all subscribers of configuration changes"""
        for subscriber in self._subscribers:
            try:
                subscriber(change_type, item_name, old_value, new_value)
            except Exception as e:
                print(f"❌ Subscriber notification failed: {e}")
    
    # Public API Methods
    
    def subscribe_to_changes(self, callback):
        """Subscribe to configuration changes"""
        self._subscribers.append(callback)
    
    def unsubscribe_from_changes(self, callback):
        """Unsubscribe from configuration changes"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def get_all_rules(self) -> Dict[str, RuleDefinition]:
        """Get all rule definitions"""
        with self._lock:
            return self.rules.copy()
    
    def get_rule(self, rule_name: str) -> Optional[RuleDefinition]:
        """Get specific rule definition"""
        with self._lock:
            return self.rules.get(rule_name)
    
    def get_all_thresholds(self) -> Dict[str, QualityThreshold]:
        """Get all threshold configurations"""
        with self._lock:
            return self.thresholds.copy()
    
    def get_threshold(self, threshold_name: str) -> Optional[QualityThreshold]:
        """Get specific threshold configuration"""
        with self._lock:
            return self.thresholds.get(threshold_name)
    
    def update_rule_weight(self, rule_name: str, new_weight: float, 
                          changed_by: str = "admin", reason: str = "Manual update") -> bool:
        """Update rule weight with real-time notification"""
        with self._lock:
            if rule_name not in self.rules:
                print(f"❌ Rule '{rule_name}' not found")
                return False
            
            old_weight = self.rules[rule_name].weight
            if old_weight == new_weight:
                return True  # No change needed
            
            # Validate weight range
            if not (0.0 <= new_weight <= 5.0):
                print(f"❌ Invalid weight {new_weight}, must be between 0.0 and 5.0")
                return False
            
            # Update rule
            self.rules[rule_name].weight = new_weight
            self.rules[rule_name].updated_at = datetime.now(timezone.utc)
            
            # Persist to database
            self._save_rule_to_db(self.rules[rule_name])
            
            # Record change
            self._record_change("rule", rule_name, "weight", old_weight, new_weight, changed_by, reason)
            
            # Notify subscribers
            self._notify_subscribers("rule_weight_update", rule_name, old_weight, new_weight)
            
            print(f"✅ Updated rule weight: {rule_name} = {new_weight} (was {old_weight})")
            return True
    
    def update_threshold_value(self, threshold_name: str, new_value: float,
                              changed_by: str = "admin", reason: str = "Manual update") -> bool:
        """Update threshold value with real-time notification"""
        with self._lock:
            if threshold_name not in self.thresholds:
                print(f"❌ Threshold '{threshold_name}' not found")
                return False
            
            threshold = self.thresholds[threshold_name]
            old_value = threshold.current_value
            
            if old_value == new_value:
                return True  # No change needed
            
            # Validate value range
            if not (threshold.min_value <= new_value <= threshold.max_value):
                print(f"❌ Invalid value {new_value}, must be between {threshold.min_value} and {threshold.max_value}")
                return False
            
            # Update threshold
            threshold.current_value = new_value
            threshold.updated_at = datetime.now(timezone.utc)
            
            # Update affected rules
            for rule_name in threshold.affects_rules:
                if rule_name in self.rules:
                    self.rules[rule_name].threshold_value = new_value
                    self._save_rule_to_db(self.rules[rule_name])
            
            # Persist to database
            self._save_threshold_to_db(threshold)
            
            # Record change
            self._record_change("threshold", threshold_name, "current_value", old_value, new_value, changed_by, reason)
            
            # Notify subscribers
            self._notify_subscribers("threshold_update", threshold_name, old_value, new_value)
            
            print(f"✅ Updated threshold: {threshold_name} = {new_value} (was {old_value})")
            return True
    
    def bulk_update_rules(self, updates: List[Dict[str, Any]], 
                         changed_by: str = "admin", reason: str = "Bulk update") -> Dict[str, bool]:
        """Update multiple rules at once"""
        results = {}
        
        for update in updates:
            rule_name = update.get("rule_name")
            if not rule_name:
                continue
                
            success = True
            if "weight" in update:
                success &= self.update_rule_weight(rule_name, update["weight"], changed_by, reason)
            
            results[rule_name] = success
        
        return results
    
    def bulk_update_thresholds(self, updates: List[Dict[str, Any]],
                              changed_by: str = "admin", reason: str = "Bulk update") -> Dict[str, bool]:
        """Update multiple thresholds at once"""
        results = {}
        
        for update in updates:
            threshold_name = update.get("threshold_name")
            if not threshold_name:
                continue
                
            success = self.update_threshold_value(threshold_name, update["new_value"], changed_by, reason)
            results[threshold_name] = success
        
        return results
    
    def reset_rule_weight(self, rule_name: str, changed_by: str = "admin") -> bool:
        """Reset rule weight to default value"""
        if rule_name not in self.rules:
            return False
        
        # Default weight is 1.0
        return self.update_rule_weight(rule_name, 1.0, changed_by, "Reset to default")
    
    def reset_threshold(self, threshold_name: str, changed_by: str = "admin") -> bool:
        """Reset threshold to default value"""
        if threshold_name not in self.thresholds:
            return False
        
        default_value = self.thresholds[threshold_name].default_value
        return self.update_threshold_value(threshold_name, default_value, changed_by, "Reset to default")
    
    def get_changes_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent configuration changes"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT change_type, item_name, field_name, old_value, new_value, 
                           changed_by, reason, timestamp
                    FROM changes_history 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
                return [
                    {
                        "change_type": row[0],
                        "item_name": row[1], 
                        "field_name": row[2],
                        "old_value": row[3],
                        "new_value": row[4],
                        "changed_by": row[5],
                        "reason": row[6],
                        "timestamp": row[7]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            print(f"❌ Failed to get changes history: {e}")
            return []
    
    def get_rules_by_category(self, category: RuleCategory) -> Dict[str, RuleDefinition]:
        """Get rules filtered by category"""
        with self._lock:
            return {name: rule for name, rule in self.rules.items() if rule.category == category}
    
    def get_thresholds_by_category(self, category: str) -> Dict[str, QualityThreshold]:
        """Get thresholds filtered by category"""
        with self._lock:
            return {name: threshold for name, threshold in self.thresholds.items() if threshold.category == category}
    
    def calculate_weighted_score(self, rule_results: List[Dict[str, Any]]) -> float:
        """Calculate weighted quality score based on current rule weights"""
        total_score = 0.0
        total_weight = 0.0
        
        for result in rule_results:
            rule_name = result.get("check_name", "")
            confidence_score = result.get("confidence_score", 0.0)
            
            if rule_name in self.rules:
                weight = self.rules[rule_name].weight
                total_score += confidence_score * weight
                total_weight += weight
        
        return (total_score / total_weight) if total_weight > 0 else 0.0
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current configuration for backup or transfer"""
        with self._lock:
            return {
                "rules": {name: asdict(rule) for name, rule in self.rules.items()},
                "thresholds": {name: asdict(threshold) for name, threshold in self.thresholds.items()},
                "exported_at": datetime.now(timezone.utc).isoformat()
            }
    
    def import_configuration(self, config: Dict[str, Any], changed_by: str = "admin") -> bool:
        """Import configuration from backup or transfer"""
        try:
            # Import rules
            if "rules" in config:
                for rule_data in config["rules"].values():
                    rule = RuleDefinition(**rule_data)
                    self.rules[rule.name] = rule
                    self._save_rule_to_db(rule)
            
            # Import thresholds  
            if "thresholds" in config:
                for threshold_data in config["thresholds"].values():
                    threshold = QualityThreshold(**threshold_data)
                    self.thresholds[threshold.name] = threshold
                    self._save_threshold_to_db(threshold)
            
            # Record import
            self._record_change("system", "configuration", "import", "", "imported", changed_by, "Configuration import")
            
            print("✅ Configuration imported successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to import configuration: {e}")
            return False


# Global instance for the application
dynamic_rules_manager: Optional[DynamicRulesManager] = None

def get_dynamic_rules_manager() -> DynamicRulesManager:
    """Get or create the global dynamic rules manager instance"""
    global dynamic_rules_manager
    if dynamic_rules_manager is None:
        dynamic_rules_manager = DynamicRulesManager()
    return dynamic_rules_manager


def initialize_dynamic_rules_manager():
    """Initialize the global dynamic rules manager"""
    global dynamic_rules_manager
    if dynamic_rules_manager is None:
        dynamic_rules_manager = DynamicRulesManager()
        print("✅ Global dynamic rules manager initialized")
    return dynamic_rules_manager 