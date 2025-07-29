"""
High-Performance Rules Engine for Indexing QA Observability Tool
Optimized to filter 80-90% of chunks before expensive LLM processing

Implements fast, cheap quality checks:
- Empty/missing tags
- Generic stopwords detection
- Spam/duplicate content detection
- Implausible tag counts
- Content-tag mismatch (basic)
- Enhanced semantic similarity using TF-IDF and cosine similarity
- Domain-specific knowledge integration
- Advanced NLP techniques for relevance detection
- Context-aware scoring algorithms
- Multi-dimensional quality assessment
"""

import re
import time
import hashlib
import numpy as np
from typing import List, Dict, Set, Optional, Tuple, Any
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import unicodedata
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

from ..models.models import ChunkIngestRequest, QualityCheckResult, FlagStatus
from ..core.config import get_settings
from .dynamic_rules_manager import get_dynamic_rules_manager, DynamicRulesManager


class RulesEngine:
    """Fast, scalable rules engine for chunk quality validation with enhanced NLP capabilities and real-time dynamic configuration"""
    
    def __init__(self):
        self.settings = get_settings()
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # Initialize dynamic rules manager for real-time configuration
        self.dynamic_manager = get_dynamic_rules_manager()
        
        # Subscribe to configuration changes for real-time updates
        self.dynamic_manager.subscribe_to_changes(self._on_configuration_change)
        
        self._load_stopwords()
        self._load_spam_signatures()
        self._load_domain_knowledge()
        self._load_advanced_stopwords()
        self._initialize_thresholds()
        
        # Performance tracking
        self.check_metrics = defaultdict(list)
    
    def _on_configuration_change(self, change_type: str, item_name: str, old_value: Any, new_value: Any):
        """Handle real-time configuration changes"""
        try:
            if change_type == "threshold_update":
                print(f"🔄 Rules Engine: Threshold '{item_name}' updated: {old_value} → {new_value}")
                # Thresholds are now fetched dynamically, so no action needed
            elif change_type == "rule_weight_update":
                print(f"🔄 Rules Engine: Rule weight '{item_name}' updated: {old_value} → {new_value}")
                # Rule weights are now fetched dynamically, so no action needed
            
            # Optional: Clear any cached calculations that depend on these values
            self.check_metrics.clear()
            
        except Exception as e:
            print(f"❌ Failed to handle configuration change: {e}")
        
    def _load_stopwords(self):
        """Load generic stopwords that shouldn't be primary tags"""
        self.generic_stopwords = {
            # Common business terms that are too generic
            'document', 'file', 'content', 'text', 'information', 'data',
            'report', 'summary', 'overview', 'details', 'description',
            'general', 'misc', 'miscellaneous', 'other', 'various',
            'company', 'business', 'corporate', 'organization',
            'important', 'urgent', 'critical', 'high', 'low', 'medium',
            'new', 'old', 'recent', 'current', 'updated', 'latest',
            'final', 'draft', 'version', 'revision', 'edit',
            'meeting', 'call', 'discussion', 'conversation',
            'email', 'message', 'communication', 'note', 'memo',
            'project', 'task', 'work', 'job', 'assignment',
            'process', 'procedure', 'method', 'approach',
            'team', 'group', 'department', 'division',
            'customer', 'client', 'user', 'person', 'people',
            'product', 'service', 'solution', 'system',
            'policy', 'guideline', 'rule', 'requirement',
            'review', 'analysis', 'evaluation', 'assessment',
            'planning', 'strategy', 'goal', 'objective',
            'training', 'education', 'learning', 'knowledge',
            'support', 'help', 'assistance', 'guidance',
            'management', 'admin', 'administration', 'operational',
            'technical', 'operational', 'functional', 'business',
            
            # Stop words from NLP
            'and', 'or', 'but', 'the', 'a', 'an', 'is', 'are', 'was', 'were',
            'for', 'with', 'about', 'from', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off',
            'over', 'under', 'again', 'further', 'then', 'once'
        }
        
        # Industry-specific stopwords can be added here
        self.domain_stopwords = {
            # Tech/Software
            'api', 'database', 'server', 'client', 'application', 'software',
            'hardware', 'network', 'security', 'backup', 'maintenance',
            
            # HR/Business
            'employee', 'staff', 'personnel', 'human resources', 'hr',
            'benefits', 'payroll', 'performance', 'evaluation',
            
            # Legal/Compliance
            'compliance', 'regulation', 'legal', 'contract', 'agreement',
            'terms', 'conditions', 'privacy', 'confidential'
        }
        
        self.all_stopwords = self.generic_stopwords | self.domain_stopwords
    
    def _load_spam_signatures(self):
        """Initialize spam detection with content hashing"""
        self.content_hashes = defaultdict(list)  # hash -> [(timestamp, source_connector)]
        self.hash_retention_hours = 24  # How long to keep hashes for spam detection
        
        # Common spam patterns
        self.spam_patterns = [
            r'lorem ipsum',
            r'test\s*(document|content|text|data)',
            r'sample\s*(document|content|text|data)',
            r'placeholder\s*(text|content)',
            r'dummy\s*(text|content|data)',
            r'(\w+)\1{3,}',  # Repeated words: "test test test test"
            r'(.{10,})\1{2,}',  # Repeated phrases
            r'^(.)\1{20,}',  # Character spam: "aaaaaaaaaaaaa..."
            r'asdf|qwerty|123456|abcdef',  # Keyboard mashing
        ]
        
        self.compiled_spam_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.spam_patterns]
    
    def _load_domain_knowledge(self):
        """Load domain-specific stopwords and knowledge"""
        self.domain_knowledge = {
            'technology': {
                'terms': ['api', 'database', 'server', 'client', 'application', 'software', 'hardware', 'network', 'security', 'backup', 'maintenance'],
                'lemmas': ['api', 'database', 'server', 'client', 'application', 'software', 'hardware', 'network', 'security', 'backup', 'maintenance']
            },
            'human_resources': {
                'terms': ['employee', 'staff', 'personnel', 'human resources', 'hr', 'benefits', 'payroll', 'performance', 'evaluation'],
                'lemmas': ['employee', 'staff', 'personnel', 'human resources', 'hr', 'benefits', 'payroll', 'performance', 'evaluation']
            },
            'legal': {
                'terms': ['compliance', 'regulation', 'legal', 'contract', 'agreement', 'terms', 'conditions', 'privacy', 'confidential'],
                'lemmas': ['compliance', 'regulation', 'legal', 'contract', 'agreement', 'terms', 'conditions', 'privacy', 'confidential']
            }
        }
    
    def _load_advanced_stopwords(self):
        """Load advanced stopwords for more sophisticated filtering"""
        self.advanced_stopwords = {
            'very_short_words': ['a', 'an', 'is', 'are', 'was', 'were', 'for', 'with', 'about', 'from', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once'],
            'very_common_words': ['and', 'or', 'but', 'the', 'a', 'an', 'is', 'are', 'was', 'were', 'for', 'with', 'about', 'from', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once'],
            'very_short_phrases': ['asdf', 'qwerty', '123456', 'abcdef'],
            'very_common_phrases': ['lorem ipsum', 'test document', 'sample content', 'placeholder text', 'dummy data', 'test test test test', 'test content test content', 'test text test text', 'test data test data', 'test document test document']
        }
    
    def _initialize_thresholds(self):
        """Initialize thresholds using the new Dynamic Rules Manager"""
        try:
            print("🔄 Loading thresholds from Dynamic Rules Manager...")
            
            # The dynamic_manager is now initialized and ready to use
            # All thresholds are managed dynamically, no local caching needed
            print("✅ Rules Engine connected to Dynamic Rules Manager for real-time threshold updates")
            
        except Exception as e:
            print(f"❌ Failed to initialize thresholds from Dynamic Rules Manager: {e}")
            # The system will still work because _get_dynamic_threshold has fallbacks

    def _get_dynamic_threshold(self, threshold_name: str, fallback_value: float) -> float:
        """Get the latest dynamic threshold value with UnifiedConfigService fallback"""
        try:
            # Get threshold from dynamic rules manager
            threshold = self.dynamic_manager.get_threshold(threshold_name)
            if threshold is not None:
                return threshold.current_value
            
            # If not found in thresholds, check if it's a rule with a threshold_value
            rule = self.dynamic_manager.get_rule(threshold_name)
            if rule is not None and rule.threshold_value is not None:
                return rule.threshold_value
                
        except Exception as e:
            print(f"Warning: Could not get {threshold_name} from Dynamic Rules Manager: {e}")
        
        # Fallback to UnifiedConfigService instead of hardcoded values
        try:
            from ..services.unified_config_service import get_unified_config_service
            config_service = get_unified_config_service()
            unified_value = config_service.get_threshold(threshold_name)
            if unified_value is not None:
                print(f"📊 Using UnifiedConfigService fallback for {threshold_name}: {unified_value}")
                return unified_value
        except Exception as e:
            print(f"Warning: Could not get {threshold_name} from UnifiedConfigService: {e}")
        
        # Final fallback to provided default only if all else fails
        print(f"⚠️  Using hardcoded fallback value {fallback_value} for {threshold_name}")
        return fallback_value
    
    def check_chunk(self, chunk: ChunkIngestRequest) -> List[QualityCheckResult]:
        """
        Run all rules engine checks on a chunk
        Optimized for high throughput (target: <10ms per chunk)
        
        ✅ ALWAYS PERFORMS EXACTLY 11 CHECKS:
        1. Empty/Missing Tags Check (fastest)
        2. Tag Count Validation
        3. Text Length and Quality
        4. Stopwords Detection
        5. Spam Detection (content patterns)
        6. Duplicate Content Detection
        7. Basic Tag-Text Relevance (lightweight NLP)
        8. Enhanced Semantic Relevance
        9. Domain-Specific Relevance
        10. Tag Specificity Analysis
        11. Context Coherence Check
        
        Returns EXACTLY 11 QualityCheckResult objects - no more, no less.
        """
        start_time = time.time()
        results = []
        
        # ===== RULES ENGINE CHECK SEQUENCE =====
        # Each check MUST be performed exactly once
        
        # 1. Empty/Missing Tags Check (fastest)
        results.append(self._check_empty_tags(chunk))
        
        # 2. Tag Count Validation
        results.append(self._check_tag_count(chunk))
        
        # 3. Text Length and Quality
        results.append(self._check_text_quality(chunk))
        
        # 4. Stopwords Detection
        results.append(self._check_generic_stopwords(chunk))
        
        # 5. Spam Detection (content patterns)
        results.append(self._check_spam_patterns(chunk))
        
        # 6. Duplicate Content Detection
        results.append(self._check_duplicate_content(chunk))
        
        # 7. Basic Tag-Text Relevance (lightweight NLP)
        results.append(self._check_tag_text_relevance(chunk))
        
        # 8. Enhanced Semantic Relevance (NEW)
        results.append(self._check_semantic_relevance(chunk))
        
        # 9. Domain-Specific Relevance (NEW)
        results.append(self._check_domain_relevance(chunk))
        
        # 10. Tag Specificity Analysis (NEW)
        results.append(self._check_tag_specificity(chunk))
        
        # 11. Context Coherence Check (NEW)
        results.append(self._check_context_coherence(chunk))
        
        # ===== VALIDATION =====
        # Ensure exactly 11 checks were performed
        expected_checks = 11
        actual_checks = len(results)
        
        if actual_checks != expected_checks:
            error_msg = f"❌ RULES ENGINE ERROR: Expected {expected_checks} checks, got {actual_checks}"
            print(error_msg)
            
            # Add error check result if mismatch
            error_result = QualityCheckResult(
                check_name="rules_engine_consistency_check",
                status=FlagStatus.FAIL,
                confidence_score=0.0,
                failure_reason=error_msg,
                check_metadata={
                    "expected_checks": expected_checks,
                    "actual_checks": actual_checks,
                    "check_names": [r.check_name for r in results]
                },
                type="rules_engine_consistency_check",
                severity="critical",
                description="Validation that exactly 11 rules engine checks were performed",
                suggestion="Check rules engine implementation for missing or duplicate checks",
                autoFixable=False,
                category="system",
                reasoning=f"Rules engine must perform exactly {expected_checks} checks for consistency",
                issues=[{"check": "consistency", "problem": f"Expected {expected_checks}, got {actual_checks}"}],
                issues_found=1,
                processing_time_ms=0
            )
            results.append(error_result)
        
        # Remove any potential duplicates based on check_name
        unique_results = []
        seen_checks = set()
        
        for result in results:
            if result.check_name not in seen_checks:
                unique_results.append(result)
                seen_checks.add(result.check_name)
            else:
                print(f"⚠️ WARNING: Duplicate check detected and removed: {result.check_name}")
        
        # Record performance metrics
        processing_time = (time.time() - start_time) * 1000
        self.check_metrics['total_processing_time'].append(processing_time)
        
        # Add processing time to metadata
        for result in unique_results:
            if not result.check_metadata:
                result.check_metadata = {}
            result.check_metadata['processing_time_ms'] = processing_time / len(unique_results)
            result.check_metadata['total_checks_performed'] = len(unique_results)
            result.check_metadata['rules_engine_version'] = "v2.0_consistent"
        
        print(f"✅ Rules Engine: Performed {len(unique_results)} checks in {processing_time:.1f}ms")
        return unique_results
    
    def get_expected_check_names(self) -> List[str]:
        """
        Return the exact list of check names that should always be performed
        Used for validation and consistency checking
        """
        return [
            "empty_tags",
            "tag_count_validation", 
            "text_quality",
            "stopwords_detection",
            "spam_patterns",
            "duplicate_content_detection",
            "tag_text_relevance",
            "semantic_relevance",
            "domain_relevance",
            "tag_specificity",
            "context_coherence"
        ]
    
    def _check_empty_tags(self, chunk: ChunkIngestRequest) -> QualityCheckResult:
        """Check for empty or missing tags - fastest check"""
        start_time = time.time()
        
        if not chunk.tags or len(chunk.tags) == 0:
            return QualityCheckResult(
                check_name="empty_tags",
                status=FlagStatus.FAIL,
                confidence_score=0.0,  # Very low score for missing tags
                failure_reason="No tags provided - content cannot be properly categorized without tags",
                check_metadata={"empty_tag_count": 0},
                type="empty_tags",
                severity="critical",
                description="Check for empty or missing tags",
                suggestion="Add specific, descriptive tags to categorize this content",
                autoFixable=True,
                category="tags",
                reasoning="No tags provided - content cannot be properly categorized without tags",
                issues=[{"tag": "missing", "problem": "No tags provided"}],
                issues_found=1,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Check for empty string tags
        empty_tags = [tag for tag in chunk.tags if not tag.strip()]
        if empty_tags:
            return QualityCheckResult(
                check_name="empty_tags",
                status=FlagStatus.FAIL,
                confidence_score=0.2,  # Low score for empty tags
                failure_reason=f"Found {len(empty_tags)} empty tags - remove empty tags or add meaningful content",
                check_metadata={"empty_tag_count": len(empty_tags)},
                type="empty_tags",
                severity="high",
                description="Check for empty or missing tags",
                suggestion=f"Remove {len(empty_tags)} empty tags and add meaningful content",
                autoFixable=True,
                category="tags",
                reasoning=f"Found {len(empty_tags)} empty tags that provide no categorization value",
                issues=[{"tag": tag, "problem": "Empty tag"} for tag in empty_tags[:3]],
                issues_found=len(empty_tags),
                processing_time_ms=(time.time() - start_time) * 1000
            )
        return QualityCheckResult(
            check_name="empty_tags",
            status=FlagStatus.PASS,
            confidence_score=1.0,
            check_metadata={"tag_count": len(chunk.tags)},
            type="empty_tags",
            severity="low",
            description="Check for empty or missing tags",
            suggestion=None,
            autoFixable=False,
            category="tags",
            reasoning="All tags have meaningful content",
            issues=[],
            issues_found=0,
            processing_time_ms=(time.time() - start_time) * 1000
        )
    
    def _check_tag_count(self, chunk: ChunkIngestRequest) -> QualityCheckResult:
        """Check if tag count is within reasonable bounds"""
        start_time = time.time()
        tag_count = len(chunk.tags)
        
        min_tag_count = self._get_dynamic_threshold('min_tag_count', 1)
        max_tag_count = self._get_dynamic_threshold('max_tag_count', 20)

        if tag_count < min_tag_count:
            return QualityCheckResult(
                check_name="tag_count_validation",
                status=FlagStatus.FAIL,
                confidence_score=0.3,  # Low score for too few tags
                failure_reason=f"Too few tags: {tag_count} < {min_tag_count} - add more specific tags to improve categorization",
                check_metadata={"tag_count": tag_count, "min_required": min_tag_count},
                type="tag_count_validation",
                severity="medium",
                description="Validate tag count is within reasonable bounds",
                suggestion=f"Add {min_tag_count - tag_count} more specific tags to improve categorization",
                autoFixable=True,
                category="tags",
                reasoning=f"Only {tag_count} tags provided, need at least {min_tag_count} for proper categorization",
                issues=[{"tag": "count", "problem": f"Too few tags: {tag_count} < {min_tag_count}"}],
                issues_found=1,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        if tag_count > max_tag_count:
            return QualityCheckResult(
                check_name="tag_count_validation",
                status=FlagStatus.FAIL,
                confidence_score=0.6,  # Moderate score for too many tags
                failure_reason=f"Too many tags: {tag_count} > {max_tag_count} - consolidate tags for better organization",
                check_metadata={"tag_count": tag_count, "max_allowed": max_tag_count},
                type="tag_count_validation",
                severity="medium",
                description="Validate tag count is within reasonable bounds",
                suggestion=f"Consolidate {tag_count - max_tag_count} tags for better organization",
                autoFixable=True,
                category="tags",
                reasoning=f"Too many tags ({tag_count}) can make content harder to find and organize",
                issues=[{"tag": "count", "problem": f"Too many tags: {tag_count} > {max_tag_count}"}],
                issues_found=1,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        return QualityCheckResult(
            check_name="tag_count_validation",
            status=FlagStatus.PASS,
            confidence_score=1.0,
            check_metadata={"tag_count": tag_count},
            type="tag_count_validation",
            severity="low",
            description="Validate tag count is within reasonable bounds",
            suggestion=None,
            autoFixable=False,
            category="tags",
            reasoning=f"Tag count ({tag_count}) is within acceptable range",
            issues=[],
            issues_found=0,
            processing_time_ms=(time.time() - start_time) * 1000
        )
    
    def _check_text_quality(self, chunk: ChunkIngestRequest) -> QualityCheckResult:
        """Basic text quality and length validation"""
        start_time = time.time()
        text = chunk.document_text.strip()
        text_length = len(text)
        
        min_text_length = self._get_dynamic_threshold('min_text_length', 50)
        max_text_length = self._get_dynamic_threshold('max_text_length', 10000)
        
        # Check minimum length
        if text_length < min_text_length:
            return QualityCheckResult(
                check_name="text_quality",
                status=FlagStatus.FAIL,
                confidence_score=0.1,  # Very low score for too short text
                failure_reason=f"Text too short: {text_length} characters - add more detailed content for better quality",
                check_metadata={"text_length": text_length, "min_required": min_text_length},
                type="text_quality",
                severity="high",
                description="Validate text quality and length",
                suggestion=f"Add at least {min_text_length - text_length} more characters of detailed content",
                autoFixable=False,
                category="content",
                reasoning=f"Text length ({text_length}) is below minimum requirement ({min_text_length})",
                issues=[{"tag": "length", "problem": f"Text too short: {text_length} characters"}],
                issues_found=1,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Check maximum length
        if text_length > max_text_length:
            return QualityCheckResult(
                check_name="text_quality",
                status=FlagStatus.FAIL,
                confidence_score=0.7,  # Moderate score for too long text
                failure_reason=f"Text too long: {text_length} characters - consider breaking into smaller, focused sections",
                check_metadata={"text_length": text_length, "max_allowed": max_text_length},
                type="text_quality",
                severity="medium",
                description="Validate text quality and length",
                suggestion="Break content into smaller, focused sections for better readability",
                autoFixable=False,
                category="content",
                reasoning=f"Text length ({text_length}) exceeds maximum recommended length ({max_text_length})",
                issues=[{"tag": "length", "problem": f"Text too long: {text_length} characters"}],
                issues_found=1,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Check for meaningful content (word count)
        words = re.findall(r'\b\w+\b', text.lower())
        meaningful_words = [w for w in words if len(w) > 2 and not w.isdigit()]
        
        min_meaningful_words = self._get_dynamic_threshold('min_meaningful_words', 5)

        if len(meaningful_words) < min_meaningful_words:
            return QualityCheckResult(
                check_name="text_quality",
                status=FlagStatus.FAIL,
                confidence_score=0.4,  # Low score for insufficient meaningful content
                failure_reason=f"Too few meaningful words: {len(meaningful_words)} - add more substantive content with specific details",
                check_metadata={"meaningful_word_count": len(meaningful_words), "total_words": len(words)},
                type="text_quality",
                severity="medium",
                description="Validate text quality and length",
                suggestion=f"Add at least {min_meaningful_words - len(meaningful_words)} more meaningful words with specific details",
                autoFixable=False,
                category="content",
                reasoning=f"Only {len(meaningful_words)} meaningful words found, need at least {min_meaningful_words}",
                issues=[{"tag": "content", "problem": f"Too few meaningful words: {len(meaningful_words)}"}],
                issues_found=1,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        return QualityCheckResult(
            check_name="text_quality",
            status=FlagStatus.PASS,
            confidence_score=1.0,
            check_metadata={"text_length": text_length, "word_count": len(words)},
            type="text_quality",
            severity="low",
            description="Validate text quality and length",
            suggestion=None,
            autoFixable=False,
            category="content",
            reasoning=f"Text quality is good: {text_length} characters, {len(meaningful_words)} meaningful words",
            issues=[],
            issues_found=0,
            processing_time_ms=(time.time() - start_time) * 1000
        )
    
    def _check_generic_stopwords(self, chunk: ChunkIngestRequest) -> QualityCheckResult:
        """Check if tags contain too many generic/meaningless terms"""
        start_time = time.time()
        
        if not chunk.tags:
            return QualityCheckResult(
                check_name="stopwords_detection",
                status=FlagStatus.PASS,
                confidence_score=1.0,
                check_metadata={"stopword_ratio": 0.0},
                type="stopwords_detection",
                severity="low",
                description="Check for generic/meaningless tags",
                suggestion=None,
                autoFixable=False,
                category="tags",
                reasoning="No tags to check for stopwords",
                issues=[],
                issues_found=0,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Normalize tags for comparison
        normalized_tags = [tag.lower().strip() for tag in chunk.tags]
        
        # Count stopwords
        stopword_matches = []
        for tag in normalized_tags:
            # Check exact matches
            if tag in self.all_stopwords:
                stopword_matches.append(tag)
            # Check if tag is mostly stopwords (for multi-word tags)
            elif ' ' in tag:
                tag_words = tag.split()
                stopword_count = sum(1 for word in tag_words if word in self.all_stopwords)
                if stopword_count / len(tag_words) > 0.6:  # More than 60% stopwords
                    stopword_matches.append(tag)
        
        stopword_ratio = len(stopword_matches) / len(chunk.tags)
        
        stopword_threshold = self._get_dynamic_threshold('stopword_threshold', 0.5)

        if stopword_ratio > stopword_threshold:
            return QualityCheckResult(
                check_name="stopwords_detection",
                status=FlagStatus.FAIL,
                confidence_score=max(0.2, 1.0 - stopword_ratio),  # Score inversely proportional to stopword ratio
                failure_reason=f"Too many generic tags: {stopword_ratio:.1%} are stopwords - replace generic terms with specific, descriptive tags",
                check_metadata={
                    "stopword_ratio": stopword_ratio,
                    "stopword_matches": stopword_matches,
                    "threshold": stopword_threshold
                },
                type="stopwords_detection",
                severity="medium",
                description="Check for generic/meaningless tags",
                suggestion=f"Replace {len(stopword_matches)} generic tags with specific, descriptive terms",
                autoFixable=True,
                category="tags",
                reasoning=f"{stopword_ratio:.1%} of tags are generic stopwords, reducing content discoverability",
                issues=[{"tag": tag, "problem": "Generic stopword"} for tag in stopword_matches[:3]],
                issues_found=len(stopword_matches),
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        return QualityCheckResult(
            check_name="stopwords_detection",
            status=FlagStatus.PASS,
            confidence_score=1.0 - stopword_ratio,
            check_metadata={"stopword_ratio": stopword_ratio},
            type="stopwords_detection",
            severity="low",
            description="Check for generic/meaningless tags",
            suggestion=None,
            autoFixable=False,
            category="tags",
            reasoning=f"Stopword ratio ({stopword_ratio:.1%}) is within acceptable limits",
            issues=[],
            issues_found=0,
            processing_time_ms=(time.time() - start_time) * 1000
        )
    
    def _check_spam_patterns(self, chunk: ChunkIngestRequest) -> QualityCheckResult:
        """Detect spam/test content using pattern matching"""
        start_time = time.time()
        text = chunk.document_text.lower()
        
        # Check against known spam patterns
        spam_matches = []
        for pattern in self.compiled_spam_patterns:
            matches = pattern.findall(text)
            if matches:
                spam_matches.extend(matches)
        
        spam_threshold = self._get_dynamic_threshold('spam_threshold', 0.3)
        
        if spam_matches:
            confidence = max(0.1, 1.0 - len(spam_matches) * 0.3)  # Lower score for more spam patterns
            return QualityCheckResult(
                check_name="spam_patterns",
                status=FlagStatus.FAIL,
                confidence_score=confidence,
                failure_reason=f"Detected spam patterns: {len(spam_matches)} matches - review content for test data or inappropriate content",
                check_metadata={"spam_patterns_found": len(spam_matches)},
                type="spam_patterns",
                severity="high",
                description="Detect spam/test content using pattern matching",
                suggestion=f"Review content for {len(spam_matches)} detected spam patterns and remove test data",
                autoFixable=False,
                category="content",
                reasoning=f"Found {len(spam_matches)} spam patterns indicating test or inappropriate content",
                issues=[{"tag": "spam", "problem": f"Spam pattern detected: {match}"} for match in spam_matches[:3]],
                issues_found=len(spam_matches),
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Check for excessive repetition
        words = text.split()
        if len(words) > 10:
            word_freq = Counter(words)
            most_common_word, max_freq = word_freq.most_common(1)[0]
            repetition_ratio = max_freq / len(words)
            
            if repetition_ratio > 0.3:  # More than 30% is one word
                return QualityCheckResult(
                    check_name="spam_patterns",
                    status=FlagStatus.FAIL,
                    confidence_score=max(0.3, 1.0 - repetition_ratio),  # Lower score for more repetition
                    failure_reason=f"Excessive word repetition: '{most_common_word}' appears {repetition_ratio:.1%} - diversify content vocabulary",
                    check_metadata={"repetition_ratio": repetition_ratio, "repeated_word": most_common_word},
                    type="spam_patterns",
                    severity="medium",
                    description="Detect spam/test content using pattern matching",
                    suggestion=f"Replace repetitive use of '{most_common_word}' with diverse vocabulary",
                    autoFixable=False,
                    category="content",
                    reasoning=f"Word '{most_common_word}' appears {repetition_ratio:.1%} of the time, indicating low-quality content",
                    issues=[{"tag": "repetition", "problem": f"Excessive repetition: '{most_common_word}' appears {repetition_ratio:.1%}"}],
                    issues_found=1,
                    processing_time_ms=(time.time() - start_time) * 1000
                )
        
        return QualityCheckResult(
            check_name="spam_patterns",
            status=FlagStatus.PASS,
            confidence_score=1.0,
            check_metadata={"spam_patterns_found": 0},
            type="spam_patterns",
            severity="low",
            description="Detect spam/test content using pattern matching",
            suggestion=None,
            autoFixable=False,
            category="content",
            reasoning="No spam patterns or excessive repetition detected",
            issues=[],
            issues_found=0,
            processing_time_ms=(time.time() - start_time) * 1000
        )
    
    def _check_duplicate_content(self, chunk: ChunkIngestRequest) -> QualityCheckResult:
        """Check for duplicate content using content hashing"""
        start_time = time.time()
        
        # Create content hash
        content_hash = self._hash_content(chunk.document_text)
        current_time = datetime.now(timezone.utc)
        
        # Clean old hashes (older than retention period)
        cutoff_time = current_time - timedelta(hours=self.hash_retention_hours)
        for hash_key in list(self.content_hashes.keys()):
            self.content_hashes[hash_key] = [
                (timestamp, connector) for timestamp, connector in self.content_hashes[hash_key]
                if timestamp > cutoff_time
            ]
            if not self.content_hashes[hash_key]:
                del self.content_hashes[hash_key]
        
        # Check for duplicates
        if content_hash in self.content_hashes:
            existing_entries = self.content_hashes[content_hash]
            recent_duplicates = len(existing_entries)
            
            max_duplicate_content_per_hour = self._get_dynamic_threshold('max_duplicate_content_per_hour', 5)

            if recent_duplicates >= max_duplicate_content_per_hour:
                return QualityCheckResult(
                    check_name="duplicate_content_detection",
                    status=FlagStatus.FAIL,
                    confidence_score=0.1,  # Very low score for duplicate content
                    failure_reason=f"Content appears {recent_duplicates} times in last {self.hash_retention_hours}h - duplicate content detected, review for redundancy",
                    check_metadata={
                        "duplicate_count": recent_duplicates,
                        "content_hash": content_hash,
                        "connectors": list(set(connector for _, connector in existing_entries))
                    },
                    type="duplicate_content_detection",
                    severity="high",
                    description="Check for duplicate content using content hashing",
                    suggestion=f"Review and remove {recent_duplicates} duplicate content instances",
                    autoFixable=False,
                    category="content",
                    reasoning=f"Content hash appears {recent_duplicates} times in the last {self.hash_retention_hours} hours",
                    issues=[{"tag": "duplicate", "problem": f"Duplicate content detected {recent_duplicates} times"}],
                    issues_found=recent_duplicates,
                    processing_time_ms=(time.time() - start_time) * 1000
                )
        
        # Store this hash
        self.content_hashes[content_hash].append((current_time, chunk.source_connector))
        
        return QualityCheckResult(
            check_name="duplicate_content_detection",
            status=FlagStatus.PASS,
            confidence_score=1.0,
            check_metadata={"content_hash": content_hash},
            type="duplicate_content_detection",
            severity="low",
            description="Check for duplicate content using content hashing",
            suggestion=None,
            autoFixable=False,
            category="content",
            reasoning="No duplicate content detected",
            issues=[],
            issues_found=0,
            processing_time_ms=(time.time() - start_time) * 1000
        )
    
    def _check_tag_text_relevance(self, chunk: ChunkIngestRequest) -> QualityCheckResult:
        """Basic tag-text relevance check using keyword matching"""
        start_time = time.time()
        
        if not chunk.tags:
            return QualityCheckResult(
                check_name="tag_text_relevance",
                status=FlagStatus.PASS,
                confidence_score=1.0,
                check_metadata={"relevance_score": 0.0},
                type="tag_text_relevance",
                severity="low",
                description="Basic tag-text relevance check using keyword matching",
                suggestion=None,
                autoFixable=False,
                category="tags",
                reasoning="No tags to check for relevance",
                issues=[],
                issues_found=0,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        text_lower = chunk.document_text.lower()
        text_words = set(re.findall(r'\b\w+\b', text_lower))
        
        relevant_tags = 0
        total_tags = len(chunk.tags)
        irrelevant_tags = []
        
        for tag in chunk.tags:
            tag_words = set(re.findall(r'\b\w+\b', tag.lower()))
            
            # Check if any tag words appear in text
            if tag_words & text_words:  # Set intersection
                relevant_tags += 1
            # Check for partial matches (for compound words)
            elif any(tag_word in text_lower for tag_word in tag_words if len(tag_word) > 3):
                relevant_tags += 0.5
            else:
                irrelevant_tags.append(tag)
        
        tag_text_relevance_threshold = self._get_dynamic_threshold('tag_text_relevance_threshold', 0.3)
        
        relevance_score = relevant_tags / total_tags if total_tags > 0 else 0
        
        if relevance_score < tag_text_relevance_threshold:
            return QualityCheckResult(
                check_name="tag_text_relevance",
                status=FlagStatus.FAIL,
                confidence_score=relevance_score,  # Score directly reflects relevance
                failure_reason=f"Low tag-text relevance: {relevance_score:.1%} - tags don't match content well, review tag accuracy",
                check_metadata={
                    "relevance_score": relevance_score,
                    "relevant_tags": relevant_tags,
                    "total_tags": total_tags
                },
                type="tag_text_relevance",
                severity="medium",
                description="Basic tag-text relevance check using keyword matching",
                suggestion=f"Review {len(irrelevant_tags)} tags that don't match content: {', '.join(irrelevant_tags[:3])}",
                autoFixable=True,
                category="tags",
                reasoning=f"Only {relevance_score:.1%} of tags are relevant to content",
                issues=[{"tag": tag, "problem": "Tag not relevant to content"} for tag in irrelevant_tags[:3]],
                issues_found=len(irrelevant_tags),
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        return QualityCheckResult(
            check_name="tag_text_relevance",
            status=FlagStatus.PASS,
            confidence_score=relevance_score,
            check_metadata={"relevance_score": relevance_score},
            type="tag_text_relevance",
            severity="low",
            description="Basic tag-text relevance check using keyword matching",
            suggestion=None,
            autoFixable=False,
            category="tags",
            reasoning=f"Tag relevance score ({relevance_score:.1%}) is within acceptable limits",
            issues=[],
            issues_found=0,
            processing_time_ms=(time.time() - start_time) * 1000
        )
    
    def _check_semantic_relevance(self, chunk: ChunkIngestRequest) -> QualityCheckResult:
        """Advanced semantic similarity using TF-IDF and cosine similarity"""
        start_time = time.time()
        
        if not chunk.tags:
            return QualityCheckResult(
                check_name="semantic_relevance",
                status=FlagStatus.PASS,
                confidence_score=1.0,
                check_metadata={"semantic_score": 0.0},
                type="semantic_relevance",
                severity="low",
                description="Advanced semantic similarity using TF-IDF and cosine similarity",
                suggestion=None,
                autoFixable=False,
                category="semantic",
                reasoning="No tags to check for semantic relevance",
                issues=[],
                issues_found=0,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        try:
            # Preprocess text and tags
            text = self._preprocess_text(chunk.document_text)
            tag_texts = [self._preprocess_text(tag) for tag in chunk.tags]
            
            if not text.strip() or not any(tag.strip() for tag in tag_texts):
                return QualityCheckResult(
                    check_name="semantic_relevance",
                    status=FlagStatus.FAIL,
                    confidence_score=0.1,
                    failure_reason="Insufficient text or tag content for semantic analysis",
                    check_metadata={"semantic_score": 0.0},
                    type="semantic_relevance",
                    severity="medium",
                    description="Advanced semantic similarity using TF-IDF and cosine similarity",
                    suggestion="Add more descriptive content and specific tags",
                    autoFixable=False,
                    category="semantic",
                    reasoning="Text or tags too short for meaningful semantic analysis",
                    issues=[{"tag": "content", "problem": "Insufficient content for semantic analysis"}],
                    issues_found=1,
                    processing_time_ms=(time.time() - start_time) * 1000
                )
            
            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer(
                stop_words='english',
                ngram_range=(1, 2),
                max_features=1000,
                min_df=1,
                max_df=0.95
            )
            
            # Combine text and tags for vectorization
            all_texts = [text] + tag_texts
            tfidf_matrix = vectorizer.fit_transform(all_texts)
            
            # Calculate cosine similarity between text and each tag
            text_vector = tfidf_matrix[0:1]
            tag_vectors = tfidf_matrix[1:]
            
            similarities = cosine_similarity(text_vector, tag_vectors).flatten()
            avg_similarity = np.mean(similarities)
            max_similarity = np.max(similarities)
            
            # Calculate semantic score
            semantic_score = (avg_similarity * 0.6) + (max_similarity * 0.4)
            
            # Get the latest dynamic threshold
            semantic_relevance_threshold = self._get_dynamic_threshold('semantic_relevance_threshold', 0.15)
            
            # Find low-relevance tags
            low_relevance_tags = []
            for i, tag in enumerate(chunk.tags):
                if similarities[i] < 0.3:  # Threshold for low relevance
                    low_relevance_tags.append(tag)
            
            if semantic_score < semantic_relevance_threshold:  # ✅ Dynamic threshold
                # Add debug logging to track threshold usage
                used_threshold = semantic_relevance_threshold
                print(f"🔍 SEMANTIC_RELEVANCE DEBUG: score={semantic_score:.3f}, threshold={used_threshold}, will_fail={semantic_score < used_threshold}")
                return QualityCheckResult(
                    check_name="semantic_relevance",
                    status=FlagStatus.FAIL,
                    confidence_score=float(semantic_score),
                    failure_reason=f"Low semantic relevance: {semantic_score:.2f} - tags don't semantically match content",
                    check_metadata={
                        "semantic_score": semantic_score,
                        "avg_similarity": float(avg_similarity),
                        "max_similarity": float(max_similarity),
                        "low_relevance_tags": low_relevance_tags
                    },
                    type="semantic_relevance",
                    severity="high",
                    description="Advanced semantic similarity using TF-IDF and cosine similarity",
                    suggestion=f"Review {len(low_relevance_tags)} tags with low semantic relevance: {', '.join(low_relevance_tags[:3])}",
                    autoFixable=True,
                    category="semantic",
                    reasoning=f"Semantic similarity score ({semantic_score:.2f}) indicates poor tag-content alignment",
                    issues=[{"tag": tag, "problem": f"Low semantic relevance: {similarities[i]:.2f}"} for i, tag in enumerate(chunk.tags) if similarities[i] < 0.3],
                    issues_found=len(low_relevance_tags),
                    processing_time_ms=(time.time() - start_time) * 1000
                )
            
            # Add debug logging for PASS case too
            used_threshold = semantic_relevance_threshold
            print(f"✅ SEMANTIC_RELEVANCE DEBUG: score={semantic_score:.3f}, threshold={used_threshold}, will_pass={semantic_score >= used_threshold}")
            
            return QualityCheckResult(
                check_name="semantic_relevance",
                status=FlagStatus.PASS,
                confidence_score=float(semantic_score),
                check_metadata={
                    "semantic_score": semantic_score,
                    "avg_similarity": float(avg_similarity),
                    "max_similarity": float(max_similarity)
                },
                type="semantic_relevance",
                severity="low",
                description="Advanced semantic similarity using TF-IDF and cosine similarity",
                suggestion=None,
                autoFixable=False,
                category="semantic",
                reasoning=f"Good semantic relevance score: {semantic_score:.2f}",
                issues=[],
                issues_found=0,
                processing_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return QualityCheckResult(
                check_name="semantic_relevance",
                status=FlagStatus.FAIL,
                confidence_score=0.3,
                failure_reason=f"Semantic analysis failed: {str(e)}",
                check_metadata={"error": str(e)},
                type="semantic_relevance",
                severity="medium",
                description="Advanced semantic similarity using TF-IDF and cosine similarity",
                suggestion="Review content and tags for semantic consistency",
                autoFixable=False,
                category="semantic",
                reasoning=f"Semantic analysis error: {str(e)}",
                issues=[{"tag": "error", "problem": f"Analysis failed: {str(e)}"}],
                issues_found=1,
                processing_time_ms=(time.time() - start_time) * 1000
            )
    
    def _check_domain_relevance(self, chunk: ChunkIngestRequest) -> QualityCheckResult:
        """Check domain-specific relevance using knowledge bases"""
        start_time = time.time()
        
        if not chunk.tags:
            return QualityCheckResult(
                check_name="domain_relevance",
                status=FlagStatus.PASS,
                confidence_score=1.0,
                check_metadata={"domain_score": 0.0},
                type="domain_relevance",
                severity="low",
                description="Check domain-specific relevance using knowledge bases",
                suggestion=None,
                autoFixable=False,
                category="domain",
                reasoning="No tags to check for domain relevance",
                issues=[],
                issues_found=0,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Analyze text for domain indicators
        text_lower = chunk.document_text.lower()
        domain_scores = {}
        
        for domain, knowledge in self.domain_knowledge.items():
            domain_terms = knowledge['terms']
            matches = sum(1 for term in domain_terms if term in text_lower)
            domain_scores[domain] = matches / len(domain_terms) if domain_terms else 0
        
        # Check if tags match detected domains
        tag_domain_matches = 0
        total_tags = len(chunk.tags)
        
        for tag in chunk.tags:
            tag_lower = tag.lower()
            for domain, knowledge in self.domain_knowledge.items():
                if any(term in tag_lower for term in knowledge['terms']):
                    tag_domain_matches += 1
                    break
        
        domain_relevance_score = tag_domain_matches / total_tags if total_tags > 0 else 0
        
        # Find domain-mismatched tags
        domain_mismatched_tags = []
        for tag in chunk.tags:
            tag_lower = tag.lower()
            has_domain_match = False
            for domain, knowledge in self.domain_knowledge.items():
                if any(term in tag_lower for term in knowledge['terms']):
                    has_domain_match = True
                    break
            if not has_domain_match:
                domain_mismatched_tags.append(tag)
        
        domain_relevance_threshold = self._get_dynamic_threshold('domain_relevance_threshold', 0.1)

        if domain_relevance_score < domain_relevance_threshold:  # ✅ Dynamic threshold
            return QualityCheckResult(
                check_name="domain_relevance",
                status=FlagStatus.FAIL,
                confidence_score=float(domain_relevance_score),
                failure_reason=f"Low domain relevance: {domain_relevance_score:.2f} - tags don't match content domain",
                check_metadata={
                    "domain_score": domain_relevance_score,
                    "domain_scores": domain_scores,
                    "domain_mismatched_tags": domain_mismatched_tags
                },
                type="domain_relevance",
                severity="medium",
                description="Check domain-specific relevance using knowledge bases",
                suggestion=f"Review {len(domain_mismatched_tags)} tags for domain consistency: {', '.join(domain_mismatched_tags[:3])}",
                autoFixable=True,
                category="domain",
                reasoning=f"Domain relevance score ({domain_relevance_score:.2f}) indicates poor domain alignment",
                issues=[{"tag": tag, "problem": "Domain mismatch"} for tag in domain_mismatched_tags],
                issues_found=len(domain_mismatched_tags),
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        return QualityCheckResult(
            check_name="domain_relevance",
            status=FlagStatus.PASS,
            confidence_score=float(domain_relevance_score),
            check_metadata={
                "domain_score": domain_relevance_score,
                "domain_scores": domain_scores
            },
            type="domain_relevance",
            severity="low",
            description="Check domain-specific relevance using knowledge bases",
            suggestion=None,
            autoFixable=False,
            category="domain",
            reasoning=f"Good domain relevance score: {domain_relevance_score:.2f}",
            issues=[],
            issues_found=0,
            processing_time_ms=(time.time() - start_time) * 1000
        )
    
    def _check_tag_specificity(self, chunk: ChunkIngestRequest) -> QualityCheckResult:
        """Analyze tag specificity vs generic terms"""
        start_time = time.time()
        
        if not chunk.tags:
            return QualityCheckResult(
                check_name="tag_specificity",
                status=FlagStatus.PASS,
                confidence_score=1.0,
                check_metadata={"specificity_score": 0.0},
                type="tag_specificity",
                severity="low",
                description="Analyze tag specificity vs generic terms",
                suggestion=None,
                autoFixable=False,
                category="specificity",
                reasoning="No tags to check for specificity",
                issues=[],
                issues_found=0,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Calculate specificity scores for each tag
        specificity_scores = []
        generic_tags = []
        
        for tag in chunk.tags:
            tag_lower = tag.lower().strip()
            
            # Check against generic stopwords
            if tag_lower in self.all_stopwords:
                specificity_scores.append(0.0)
                generic_tags.append(tag)
                continue
            
            # Check for compound words (more specific)
            word_count = len(tag_lower.split())
            if word_count > 1:
                specificity_scores.append(0.8)  # Compound tags are more specific
            else:
                # Check against domain knowledge for specificity
                is_domain_specific = False
                for domain, knowledge in self.domain_knowledge.items():
                    if tag_lower in knowledge['terms']:
                        is_domain_specific = True
                        break
                
                if is_domain_specific:
                    specificity_scores.append(0.7)
                else:
                    # Check word length and uniqueness
                    if len(tag_lower) > 8:
                        specificity_scores.append(0.6)
                    elif len(tag_lower) > 5:
                        specificity_scores.append(0.5)
                    else:
                        specificity_scores.append(0.3)
        
        avg_specificity = np.mean(specificity_scores) if specificity_scores else 0
        
        tag_specificity_threshold = self._get_dynamic_threshold('tag_specificity_threshold', 0.5)

        if avg_specificity < tag_specificity_threshold:  # Enhanced threshold
            return QualityCheckResult(
                check_name="tag_specificity",
                status=FlagStatus.FAIL,
                confidence_score=float(avg_specificity),
                failure_reason=f"Low tag specificity: {avg_specificity:.2f} - too many generic tags",
                check_metadata={
                    "specificity_score": avg_specificity,
                    "generic_tags": generic_tags,
                    "individual_scores": dict(zip(chunk.tags, specificity_scores))
                },
                type="tag_specificity",
                severity="medium",
                description="Analyze tag specificity vs generic terms",
                suggestion=f"Replace {len(generic_tags)} generic tags with more specific terms: {', '.join(generic_tags[:3])}",
                autoFixable=True,
                category="specificity",
                reasoning=f"Average specificity score ({avg_specificity:.2f}) indicates too many generic tags",
                issues=[{"tag": tag, "problem": f"Low specificity: {score:.2f}"} for tag, score in zip(chunk.tags, specificity_scores) if score < tag_specificity_threshold],
                issues_found=len([s for s in specificity_scores if s < tag_specificity_threshold]),
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        return QualityCheckResult(
            check_name="tag_specificity",
            status=FlagStatus.PASS,
            confidence_score=float(avg_specificity),
            check_metadata={
                "specificity_score": avg_specificity,
                "individual_scores": dict(zip(chunk.tags, specificity_scores))
            },
            type="tag_specificity",
            severity="low",
            description="Analyze tag specificity vs generic terms",
            suggestion=None,
            autoFixable=False,
            category="specificity",
            reasoning=f"Good tag specificity score: {avg_specificity:.2f}",
            issues=[],
            issues_found=0,
            processing_time_ms=(time.time() - start_time) * 1000
        )
    
    def _check_context_coherence(self, chunk: ChunkIngestRequest) -> QualityCheckResult:
        """Check tag coherence and context consistency"""
        start_time = time.time()
        
        if not chunk.tags or len(chunk.tags) < 2:
            return QualityCheckResult(
                check_name="context_coherence",
                status=FlagStatus.PASS,
                confidence_score=1.0,
                check_metadata={"coherence_score": 1.0},
                type="context_coherence",
                severity="low",
                description="Check tag coherence and context consistency",
                suggestion=None,
                autoFixable=False,
                category="coherence",
                reasoning="Insufficient tags for coherence analysis",
                issues=[],
                issues_found=0,
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Analyze tag coherence using semantic similarity
        try:
            tag_texts = [self._preprocess_text(tag) for tag in chunk.tags]
            valid_tags = [tag for tag, text in zip(chunk.tags, tag_texts) if text.strip()]
            
            if len(valid_tags) < 2:
                return QualityCheckResult(
                    check_name="context_coherence",
                    status=FlagStatus.PASS,
                    confidence_score=1.0,
                    check_metadata={"coherence_score": 1.0},
                    type="context_coherence",
                    severity="low",
                    description="Check tag coherence and context consistency",
                    suggestion=None,
                    autoFixable=False,
                    category="coherence",
                    reasoning="Insufficient valid tags for coherence analysis",
                    issues=[],
                    issues_found=0,
                    processing_time_ms=(time.time() - start_time) * 1000
                )
            
            # Create TF-IDF vectors for tags
            vectorizer = TfidfVectorizer(
                stop_words='english',
                ngram_range=(1, 2),
                max_features=500,
                min_df=1,
                max_df=0.95
            )
            
            tfidf_matrix = vectorizer.fit_transform(tag_texts)
            
            # Calculate pairwise similarities between tags
            similarities = cosine_similarity(tfidf_matrix)
            
            # Calculate coherence metrics
            coherence_scores = []
            incoherent_pairs = []
            
            for i in range(len(valid_tags)):
                for j in range(i + 1, len(valid_tags)):
                    similarity = similarities[i][j]
                    coherence_scores.append(similarity)
                    
                    if similarity < 0.2:  # Low coherence threshold
                        incoherent_pairs.append((valid_tags[i], valid_tags[j], similarity))
            
            avg_coherence = np.mean(coherence_scores) if coherence_scores else 0
            
            context_coherence_threshold = self._get_dynamic_threshold('context_coherence_threshold', 0.1)

            if avg_coherence < context_coherence_threshold:  # ✅ Dynamic threshold
                return QualityCheckResult(
                    check_name="context_coherence",
                    status=FlagStatus.FAIL,
                    confidence_score=float(avg_coherence),
                    failure_reason=f"Low tag coherence: {avg_coherence:.2f} - tags lack contextual consistency",
                    check_metadata={
                        "coherence_score": avg_coherence,
                        "incoherent_pairs": [(pair[0], pair[1], float(pair[2])) for pair in incoherent_pairs[:5]]
                    },
                    type="context_coherence",
                    severity="medium",
                    description="Check tag coherence and context consistency",
                    suggestion=f"Review {len(incoherent_pairs)} tag pairs for better coherence",
                    autoFixable=True,
                    category="coherence",
                    reasoning=f"Average coherence score ({avg_coherence:.2f}) indicates poor tag consistency",
                    issues=[{"tag": f"{pair[0]} vs {pair[1]}", "problem": f"Low coherence: {pair[2]:.2f}"} for pair in incoherent_pairs[:3]],
                    issues_found=len(incoherent_pairs),
                    processing_time_ms=(time.time() - start_time) * 1000
                )
            
            return QualityCheckResult(
                check_name="context_coherence",
                status=FlagStatus.PASS,
                confidence_score=float(avg_coherence),
                check_metadata={"coherence_score": avg_coherence},
                type="context_coherence",
                severity="low",
                description="Check tag coherence and context consistency",
                suggestion=None,
                autoFixable=False,
                category="coherence",
                reasoning=f"Good tag coherence score: {avg_coherence:.2f}",
                issues=[],
                issues_found=0,
                processing_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return QualityCheckResult(
                check_name="context_coherence",
                status=FlagStatus.FAIL,
                confidence_score=0.3,
                failure_reason=f"Coherence analysis failed: {str(e)}",
                check_metadata={"error": str(e)},
                type="context_coherence",
                severity="medium",
                description="Check tag coherence and context consistency",
                suggestion="Review tags for contextual consistency",
                autoFixable=False,
                category="coherence",
                reasoning=f"Coherence analysis error: {str(e)}",
                issues=[{"tag": "error", "problem": f"Analysis failed: {str(e)}"}],
                issues_found=1,
                processing_time_ms=(time.time() - start_time) * 1000
            )
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for NLP analysis"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _hash_content(self, text: str) -> str:
        """Create a hash for duplicate detection"""
        # Normalize text for better duplicate detection
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def update_thresholds(self, new_thresholds: Dict[str, float], reason: str = "Manual update"):
        """Update rules engine thresholds based on feedback"""
        for key, value in new_thresholds.items():
            if key in self.thresholds:
                old_value = self.thresholds[key]
                self.thresholds[key] = value
                print(f"Updated threshold {key}: {old_value} → {value} ({reason})")
        
        # Reinitialize thresholds from database to get the latest values
        self._initialize_thresholds()
    
    def reload_thresholds(self):
        """Force reload thresholds from all sources - fixes persistence issues"""
        print("🔄 Reloading rules engine thresholds...")
        
        # Clear existing thresholds to force fresh reload
        self.thresholds = {}
        
        # Force reinitialize from dynamic threshold manager
        self._initialize_thresholds()
        
        print(f"✅ Thresholds reloaded: {self.thresholds}")
        
        # Log specific critical thresholds for debugging
        critical_thresholds = ['semantic_relevance_threshold', 'domain_relevance_threshold', 
                              'context_coherence_threshold', 'tag_specificity_threshold']
        print("🎯 Critical thresholds after reload:")
        for threshold in critical_thresholds:
            value = self.thresholds.get(threshold, 'NOT_FOUND')
            print(f"   {threshold}: {value}")
        
        return True
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics for monitoring"""
        if not self.check_metrics['total_processing_time']:
            return {"avg_processing_time_ms": 0.0, "checks_run": 0}
        
        times = self.check_metrics['total_processing_time']
        return {
            "avg_processing_time_ms": sum(times) / len(times),
            "max_processing_time_ms": max(times),
            "min_processing_time_ms": min(times),
            "checks_run": len(times),
            "throughput_per_second": 1000 / (sum(times) / len(times)) if times else 0
        }
    
    def reset_metrics(self):
        """Reset performance tracking"""
        self.check_metrics.clear() 