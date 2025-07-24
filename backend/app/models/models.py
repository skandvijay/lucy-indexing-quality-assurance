"""
Data models for Indexing QA Observability Tool
Includes Pydantic schemas for API validation and SQLAlchemy models for Azure SQL
"""

from datetime import datetime, UTC
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, DateTime, Text, Float, Integer, Boolean, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER


Base = declarative_base()


class SourceConnector(str, Enum):
    """Supported source connectors"""
    SHAREPOINT = "SharePoint"
    CONFLUENCE = "Confluence"
    NOTION = "Notion"
    GDRIVE = "GDrive"
    # Add more flexible connector types
    ELASTICSEARCH = "Elasticsearch"
    CUSTOM = "Custom"
    UNKNOWN = "Unknown"
    # Allow any string value for backward compatibility
    def __new__(cls, value):
        if value not in cls._value2member_map_:
            # Create a new member for unknown values
            obj = str.__new__(cls, value)
            obj._name_ = value.upper()
            obj._value_ = value
            return obj
        return super().__new__(cls, value)


class FlagStatus(str, Enum):
    """Quality check flag statuses"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"  # Moderate issues that don't require immediate action
    PENDING_REVIEW = "pending_review"
    MANUAL_OVERRIDE = "manual_override"


class ReviewerDecision(str, Enum):
    """Reviewer decisions for flagged records"""
    TRUE_POSITIVE = "true_positive"  # Correctly flagged as bad
    FALSE_POSITIVE = "false_positive"  # Incorrectly flagged as bad
    NEEDS_INVESTIGATION = "needs_investigation"


# === Pydantic Models for API ===

class ChunkIngestRequest(BaseModel):
    """Input schema for chunk ingestion API"""
    record_id: str = Field(..., description="Unique identifier for the chunk")
    document_text: str = Field(..., min_length=1, description="The actual text content")
    tags: List[str] = Field(..., description="Associated tags/metadata")
    source_connector: str = Field(..., description="Source system")
    file_id: str = Field(..., description="Source file identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    @validator('tags')
    def validate_tags(cls, v):
        """Ensure tags are non-empty strings"""
        if not all(tag.strip() for tag in v):
            raise ValueError("All tags must be non-empty strings")
        return [tag.strip() for tag in v]
    
    @validator('document_text')
    def validate_text(cls, v):
        """Ensure document text meets minimum requirements"""
        if len(v.strip()) < 10:
            raise ValueError("Document text must be at least 10 characters")
        return v.strip()
    
    @validator('source_connector')
    def validate_source_connector(cls, v):
        """Accept any string for source_connector but warn about unknown values"""
        valid_connectors = [conn.value for conn in SourceConnector]
        if v not in valid_connectors:
            print(f"Warning: Unknown source_connector '{v}'. Valid values are: {valid_connectors}")
        return v


class BatchIngestRequest(BaseModel):
    """Batch upload schema"""
    chunks: List[ChunkIngestRequest] = Field(..., description="List of chunks to process")
    batch_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class QualityCheckResult(BaseModel):
    """Quality check results for a chunk"""
    check_name: str
    status: FlagStatus
    confidence_score: float = Field(ge=0.0, le=1.0)
    failure_reason: Optional[str] = None
    check_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Additional fields for detailed quality check information
    type: Optional[str] = None  # e.g., "stopwords detection", "tag validation", "llm_semantic_validation"
    severity: Optional[str] = None  # e.g., "low", "medium", "high", "critical"
    description: Optional[str] = None  # Detailed description of the check
    suggestion: Optional[str] = None  # Suggested fix or improvement
    autoFixable: Optional[bool] = None  # Whether this issue can be auto-fixed
    category: Optional[str] = None  # e.g., "tags", "content", "metadata", "llm"
    reasoning: Optional[str] = None  # LLM reasoning for the decision
    issues: Optional[List[Dict[str, Any]]] = None  # List of specific issues found
    llm_assessment: Optional[str] = None  # LLM's overall assessment
    llm_reasoning: Optional[str] = None  # LLM's detailed reasoning
    issues_found: Optional[int] = None  # Number of issues found
    processing_time_ms: Optional[float] = None  # Processing time for this check


class ChunkAnalysisResponse(BaseModel):
    """API response for chunk analysis"""
    trace_id: str
    record_id: str
    overall_status: FlagStatus
    status: str  # 'flagged' or 'approved'
    quality_checks: List[QualityCheckResult]
    processing_time_ms: float
    created_at: datetime
    content_metadata: Optional[Dict[str, Any]] = None


class ReviewerFeedback(BaseModel):
    """Reviewer feedback input"""
    trace_id: str
    decision: ReviewerDecision
    comments: Optional[str] = None
    reviewer_id: str
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)


# === SQLAlchemy Models for Azure SQL ===

class ChunkRecord(Base):
    """Main chunk record table - mirrors Lucy's chunk storage"""
    __tablename__ = "chunk_records"
    
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    trace_id = Column(String(64), unique=True, nullable=False, index=True)
    record_id = Column(String(256), nullable=False, index=True)  # Lucy's record_id
    document_text = Column(Text, nullable=False)
    tags = Column(JSON, nullable=False)  # Store as JSON array
    source_connector = Column(String(50), nullable=False, index=True)
    file_id = Column(String(256), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    content_metadata = Column(JSON, nullable=True)  # Store extra metadata
    
    # Relationships
    quality_checks = relationship("QualityCheckRecord", back_populates="chunk", cascade="all, delete-orphan")
    reviews = relationship("ReviewRecord", back_populates="chunk", cascade="all, delete-orphan")
    
    # Indexes for performance on high volume
    __table_args__ = (
        Index('ix_chunk_records_processed_at_connector', 'processed_at', 'source_connector'),
        Index('ix_chunk_records_record_id_created', 'record_id', 'created_at'),
    )


class QualityCheckRecord(Base):
    """Individual quality check results"""
    __tablename__ = "quality_check_records"
    
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    chunk_id = Column(UNIQUEIDENTIFIER, ForeignKey("chunk_records.id"), nullable=False, index=True)
    check_name = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)  # FlagStatus enum
    confidence_score = Column(Float, nullable=False)
    failure_reason = Column(Text, nullable=True)
    check_metadata_json = Column(JSON, nullable=True)  # Renamed from metadata to avoid conflict
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processing_time_ms = Column(Float, nullable=False)
    
    # Relationships
    chunk = relationship("ChunkRecord", back_populates="quality_checks")
    
    # Composite index for analytics queries
    __table_args__ = (
        Index('ix_qc_status_check_date', 'status', 'check_name', 'executed_at'),
    )


class ReviewRecord(Base):
    """Human reviewer decisions and feedback"""
    __tablename__ = "review_records"
    
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    chunk_id = Column(UNIQUEIDENTIFIER, ForeignKey("chunk_records.id"), nullable=False, index=True)
    decision = Column(String(30), nullable=False)  # ReviewerDecision enum
    comments = Column(Text, nullable=True)
    reviewer_id = Column(String(100), nullable=False, index=True)
    reviewed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # For tracking threshold adjustments
    previous_thresholds = Column(JSON, nullable=True)
    triggered_threshold_update = Column(Boolean, default=False)
    
    # Relationships
    chunk = relationship("ChunkRecord", back_populates="reviews")


class DeadLetterRecord(Base):
    """Failed/invalid records for debugging"""
    __tablename__ = "dead_letter_records"
    
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    trace_id = Column(String(64), nullable=True, index=True)
    raw_input = Column(Text, nullable=False)  # Original JSON
    error_message = Column(Text, nullable=False)
    error_type = Column(String(100), nullable=False, index=True)
    failed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    source_connector = Column(String(50), nullable=True, index=True)
    retry_count = Column(Integer, default=0)
    resolved = Column(Boolean, default=False, index=True)


class GoldenDatasetRecord(Base):
    """Known good/bad examples for training and testing"""
    __tablename__ = "golden_dataset_records"
    
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    record_id = Column(String(256), nullable=False, index=True)
    document_text = Column(Text, nullable=False)
    tags = Column(JSON, nullable=False)
    source_connector = Column(String(50), nullable=False)
    
    # Golden labels
    is_good_quality = Column(Boolean, nullable=False, index=True)
    expected_flags = Column(JSON, nullable=True)  # Array of expected check failures
    confidence_level = Column(Float, nullable=False)  # 0-1 how sure we are
    
    # Metadata
    added_by = Column(String(100), nullable=False)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    version = Column(Integer, default=1)
    active = Column(Boolean, default=True, index=True)


class ThresholdConfiguration(Base):
    """Dynamic threshold management"""
    __tablename__ = "threshold_configurations"
    
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    check_name = Column(String(100), nullable=False, index=True)
    threshold_value = Column(Float, nullable=False)
    confidence_cutoff = Column(Float, nullable=False)
    
    # Tracking
    updated_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reason = Column(Text, nullable=True)
    
    # Performance tracking
    true_positive_rate = Column(Float, nullable=True)
    false_positive_rate = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)


class AlertRecord(Base):
    """Alert and notification history"""
    __tablename__ = "alert_records"
    
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    
    # Alert details
    triggered_by = Column(String(100), nullable=True)  # System or user
    alert_data = Column(JSON, nullable=True)
    sent_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Delivery tracking
    slack_sent = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)
    webhook_sent = Column(Boolean, default=False)
    delivery_errors = Column(JSON, nullable=True)


# === Utility Functions ===

def generate_trace_id() -> str:
    """Generate a unique trace ID for request tracking"""
    return f"qa-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"


def mask_pii_text(text: str) -> str:
    """Mask PII patterns before sending to LLM"""
    import re
    
    # Email patterns
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    
    # Phone patterns (US format)
    text = re.sub(r'\b(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b', '[PHONE]', text)
    
    # Employee ID patterns (assuming format EMP-12345)
    text = re.sub(r'\b[A-Z]{2,4}-\d{4,6}\b', '[EMPLOYEE_ID]', text)
    
    # SSN patterns
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    
    return text 