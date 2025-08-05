#!/usr/bin/env python3
"""
IndexingQA Local Development Server
Enhanced with custom LLM prompts, constraints, and red-team testing
"""


# Path setup for direct execution
import sys
import os

# Add the backend directory to Python path if not already present
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
    print(f"📁 Added {backend_dir} to Python path")
import json
import time
import uuid
import re
import os
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict
import sqlite3
import threading
from fastapi import Body, File, UploadFile

from fastapi import FastAPI, HTTPException, Request, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
import uvicorn
import aiohttp

# Import unified bulk processor
try:
    from .unified_bulk_ingest import bulk_processor, extract_records_from_upload, create_streaming_response
    UNIFIED_BULK_AVAILABLE = True
    print("✅ Unified bulk processor available")
except ImportError as e:
    print(f"⚠️  Unified bulk processor not available: {e}")
    UNIFIED_BULK_AVAILABLE = False

# Import our rules engine
try:
    from app.services.rules_engine import RulesEngine
    from app.models.models import ChunkIngestRequest, QualityCheckResult, FlagStatus, SourceConnector
    from app.core.config import get_settings
    from app.services.alerts import AlertManager
    from app.services.schema_validator import SchemaValidator
    from app.services.dynamic_rules_manager import get_dynamic_rules_manager, initialize_dynamic_rules_manager
    RULES_ENGINE_AVAILABLE = True
    ALERT_MANAGER_AVAILABLE = True
    SCHEMA_VALIDATOR_AVAILABLE = True
    DYNAMIC_RULES_AVAILABLE = True
    print("✅ Rules engine, alert manager, schema validator, and dynamic rules manager available")
except ImportError as e:
    print(f"⚠️  Services not available - using enhanced mock responses: {e}")
    RULES_ENGINE_AVAILABLE = False
    ALERT_MANAGER_AVAILABLE = False
    SCHEMA_VALIDATOR_AVAILABLE = False
    DYNAMIC_RULES_AVAILABLE = False

# Check for LLM libraries
try:
    import openai
    LLM_AVAILABLE = True
    print("✅ OpenAI library available")
except ImportError:
    LLM_AVAILABLE = False
    print("⚠️  OpenAI library not available - using fallback mode")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
    print("✅ Anthropic library available")
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️  Anthropic library not available")

# Initialize global variables
processed_records = []
processed_count = 0
llm_processed_count = 0
redteam_results = []
start_time = datetime.now(UTC)
evaluation_metrics = {
    'total_analyses': 0,
    'methodology_performance': defaultdict(list),
    'user_feedback': []
}

# Initialize settings
settings = None
if RULES_ENGINE_AVAILABLE:
    try:
        settings = get_settings()
    except Exception as e:
        print(f"⚠️ Warning: Could not load settings: {e}")
        settings = None

# Initialize rules engine if available
rules_engine = None
alert_manager = None
llm_judge = None

if RULES_ENGINE_AVAILABLE:
    try:
        rules_engine = RulesEngine()
        print("✅ Rules engine initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize rules engine: {e}")
        RULES_ENGINE_AVAILABLE = False

if ALERT_MANAGER_AVAILABLE:
    try:
        alert_manager = AlertManager()
        print("✅ Alert manager initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize alert manager: {e}")
        ALERT_MANAGER_AVAILABLE = False

# Initialize LLM judge for semantic validation
try:
    from app.services.llm_judge import LLMJudge
    llm_judge = LLMJudge()
    print("✅ LLM judge initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize LLM judge: {e}")
    llm_judge = None

# Initialize schema validator
schema_validator = None
if SCHEMA_VALIDATOR_AVAILABLE:
    try:
        schema_validator = SchemaValidator()
        print("✅ Schema validator initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize schema validator: {e}")
        SCHEMA_VALIDATOR_AVAILABLE = False

# Initialize dynamic rules manager
rules_manager = None
if DYNAMIC_RULES_AVAILABLE:
    try:
        rules_manager = initialize_dynamic_rules_manager()
        print("✅ Dynamic Rules Manager initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Dynamic Rules Manager: {e}")
        DYNAMIC_RULES_AVAILABLE = False

# Initialize SQLite database for persistent storage - Fixed path to use main database
DB_PATH = os.path.join(backend_dir, "indexing_qa.db")
print(f"🗄️  Database path: {DB_PATH}")
print(f"🗄️  Database exists: {os.path.exists(DB_PATH)}")
if os.path.exists(DB_PATH):
    print(f"🗄️  Database size: {os.path.getsize(DB_PATH)} bytes")

# Verify we're using the right database
if not os.path.exists(DB_PATH):
    # Fallback to the main backend directory database
    fallback_path = os.path.join(os.path.dirname(backend_dir), "backend", "indexing_qa.db")
    if os.path.exists(fallback_path):
        DB_PATH = fallback_path
        print(f"🔄 Using fallback database path: {DB_PATH}")
    else:
        print(f"⚠️  Database not found at {DB_PATH} or {fallback_path}")

print(f"✅ Final database path: {DB_PATH} (exists: {os.path.exists(DB_PATH)})")

def init_database():
    """Initialize database with proper schema"""
    try:
        # Create database connection
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create all required tables from create_table.py
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_records (
                id TEXT PRIMARY KEY,
                record_id TEXT,
                title TEXT,
                content TEXT,
                tags TEXT,
                source_connector TEXT,
                company TEXT,
                quality_score REAL,
                quality_level TEXT,
                quality_checks TEXT,
                content_metadata TEXT,
                created_at TEXT,
                processing_time_ms REAL,
                trace_id TEXT,
                llm_suggestions TEXT,
                llm_reasoning TEXT,
                status TEXT,
                manual_review_status TEXT,
                issues TEXT,
                alert_sent BOOLEAN DEFAULT 0,
                email_recipients TEXT,
                alert_type TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quality_checks (
                id TEXT PRIMARY KEY,
                record_id TEXT,
                check_name TEXT,
                status TEXT,
                confidence_score REAL,
                failure_reason TEXT,
                check_metadata_json TEXT,
                executed_at TEXT,
                processing_time_ms REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS request_logs (
                id TEXT PRIMARY KEY,
                trace_id TEXT,
                endpoint TEXT,
                method TEXT,
                request_data TEXT,
                response_status INTEGER,
                response_data TEXT,
                processing_time_ms REAL,
                created_at TEXT,
                error_message TEXT,
                source_connector TEXT,
                success BOOLEAN DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dynamic_thresholds (
                threshold_name TEXT PRIMARY KEY,
                current_value REAL,
                default_value REAL,
                min_value REAL,
                max_value REAL,
                description TEXT,
                category TEXT,
                unit TEXT,
                updated_by TEXT,
                updated_at TEXT,
                reason TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS threshold_history (
                id TEXT PRIMARY KEY,
                threshold_name TEXT,
                old_value REAL,
                new_value REAL,
                changed_by TEXT,
                reason TEXT,
                timestamp TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_templates (
                id TEXT PRIMARY KEY,
                name TEXT,
                subject TEXT,
                body TEXT,
                type TEXT,
                is_active BOOLEAN,
                created_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_recipients (
                id TEXT PRIMARY KEY,
                email TEXT,
                name TEXT,
                role TEXT,
                alert_types TEXT,
                is_active BOOLEAN,
                created_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS llm_settings_history (
                id TEXT PRIMARY KEY,
                changed_by TEXT,
                old_mode TEXT,
                new_mode TEXT,
                old_threshold REAL,
                new_threshold REAL,
                timestamp TEXT,
                reason TEXT
            )
        ''')
        
        # Create dead_letters table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dead_letters (
                id TEXT PRIMARY KEY,
                trace_id TEXT,
                raw_input TEXT NOT NULL,
                error_message TEXT NOT NULL,
                error_type TEXT NOT NULL,
                failed_at TEXT NOT NULL,
                source_connector TEXT,
                retry_count INTEGER DEFAULT 0,
                resolved BOOLEAN DEFAULT 0
            )
        ''')
        
        # Check if processed_records table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_records'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Check for missing columns and add them
            cursor.execute("PRAGMA table_info(processed_records)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add missing columns if they don't exist
            missing_columns = [
                ('trace_id', 'TEXT'),
                ('llm_suggestions', 'TEXT'),
                ('llm_reasoning', 'TEXT'),
                ('status', 'TEXT'),
                ('manual_review_status', 'TEXT'),
                ('issues', 'TEXT'),
                ('alert_sent', 'BOOLEAN DEFAULT 0'),
                ('email_recipients', 'TEXT'),
                ('alert_type', 'TEXT')
            ]
            
            for column_name, column_type in missing_columns:
                if column_name not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE processed_records ADD COLUMN {column_name} {column_type}")
                        print(f"Added missing column: {column_name}")
                    except Exception as e:
                        print(f"Error adding column {column_name}: {e}")
        
        conn.commit()
        conn.close()
        print("Database initialization completed")
        
    except Exception as e:
        print(f"Error initializing database: {e}")

def populate_sample_data():
    """Populate database with sample data for testing"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if we already have data
    cursor.execute("SELECT COUNT(*) FROM processed_records")
    if cursor.fetchone()[0] > 0:
        print("Database already has data, skipping sample data population")
        conn.close()
        return
    
    print("Populating database with sample data...")
    
    sample_records = [
        {
            'record_id': 'sample-001',
            'title': 'Machine Learning Best Practices',
            'content': 'This document outlines the best practices for implementing machine learning algorithms in production environments. It covers data preprocessing, model selection, and deployment strategies.',
            'tags': ['machine learning', 'best practices', 'production', 'algorithms'],
            'source_connector': 'SharePoint',
            'company': 'TechCorp Inc',
            'quality_score': 85.5,
            'quality_level': 'high',
            'quality_checks': [
                {
                    'check_name': 'text_quality',
                    'status': 'pass',
                    'confidence_score': 0.9,
                    'failure_reason': None
                },
                {
                    'check_name': 'tag_text_relevance',
                    'status': 'pass',
                    'confidence_score': 0.85,
                    'failure_reason': None
                }
            ],
            'content_metadata': {
                'author': 'Dr. Sarah Johnson',
                'department': 'Data Science',
                'document_type': 'technical_guide',
                'word_count': 1250
            },
            'llm_suggestions': ['Consider adding more specific examples', 'Include code snippets for clarity'],
            'llm_reasoning': 'Content is well-structured and relevant. Tags are appropriate and descriptive.'
        },
        {
            'record_id': 'sample-002',
            'title': 'Employee Handbook - Vacation Policy',
            'content': 'Employees are entitled to 20 days of paid vacation per year. Vacation requests must be submitted at least 2 weeks in advance.',
            'tags': ['hr', 'vacation', 'policy'],
            'source_connector': 'Confluence',
            'company': 'TechCorp Inc',
            'quality_score': 72.0,
            'quality_level': 'medium',
            'quality_checks': [
                {
                    'check_name': 'text_quality',
                    'status': 'pass',
                    'confidence_score': 0.7,
                    'failure_reason': None
                },
                {
                    'check_name': 'tag_count_validation',
                    'status': 'fail',
                    'confidence_score': 0.6,
                    'failure_reason': 'Too few tags: 3 < 5'
                }
            ],
            'content_metadata': {
                'author': 'HR Department',
                'department': 'Human Resources',
                'document_type': 'policy',
                'word_count': 45
            },
            'llm_suggestions': ['Add more specific details about vacation accrual', 'Include examples of acceptable vacation reasons'],
            'llm_reasoning': 'Content is clear but could be more detailed. Tags are relevant but could be more specific.'
        },
        {
            'record_id': 'sample-003',
            'title': 'API Documentation - User Authentication',
            'content': 'This API provides user authentication endpoints. Use POST /auth/login to authenticate users and GET /auth/verify to validate tokens.',
            'tags': ['api', 'authentication', 'documentation'],
            'source_connector': 'Notion',
            'company': 'TechCorp Inc',
            'quality_score': 91.0,
            'quality_level': 'high',
            'quality_checks': [
                {
                    'check_name': 'text_quality',
                    'status': 'pass',
                    'confidence_score': 0.95,
                    'failure_reason': None
                },
                {
                    'check_name': 'tag_text_relevance',
                    'status': 'pass',
                    'confidence_score': 0.92,
                    'failure_reason': None
                }
            ],
            'content_metadata': {
                'author': 'Engineering Team',
                'department': 'Engineering',
                'document_type': 'api_docs',
                'word_count': 89
            },
            'llm_suggestions': ['Add code examples for each endpoint', 'Include error handling scenarios'],
            'llm_reasoning': 'Excellent technical documentation with clear structure and relevant tags.'
        }
    ]
    
    for record in sample_records:
        cursor.execute('''
            INSERT INTO processed_records (
                id, record_id, title, content, tags, source_connector, company,
                quality_score, quality_level, quality_checks, content_metadata,
                created_at, processing_time_ms, llm_suggestions, llm_reasoning, trace_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"record-{record['record_id']}",  # Generate proper ID
            record['record_id'],
            record['title'],
            record['content'],
            json.dumps(record['tags']),
            record['source_connector'],
            record['company'],
            record['quality_score'],
            record['quality_level'],
            json.dumps(record['quality_checks']),
            json.dumps(record['content_metadata']),
            datetime.now(UTC).isoformat(),
            150.0,  # processing time
            json.dumps(record['llm_suggestions']),
            record['llm_reasoning'],
            f"trace-{record['record_id']}"
        ))
    
    conn.commit()
    conn.close()
    print(f"Added {len(sample_records)} sample records to database")

# Initialize database
init_database()

# Populate with sample data if empty
populate_sample_data()

# Data models for API
class ContentIngestRequest(BaseModel):
    record_id: str
    content: str
    tags: List[str]
    source_connector: str
    content_metadata: Optional[Dict] = None

class RulesCheckRequest(BaseModel):
    content: str = Field(..., alias="document_text")
    tags: List[str] 
    source_connector: str
    
    class Config:
        allow_population_by_field_name = True

class LLMAnalysisRequest(BaseModel):
    content: str
    tags: List[str]
    context: Optional[Dict] = None



class RedTeamRequest(BaseModel):
    scenario_id: str
    content: str
    tags: List[str]
    test_objectives: List[str]
    expected_issues: Optional[List[str]] = None

class QualityConstraint(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool
    weight: float
    rule: str

class SystemStats(BaseModel):
    total_processed: int
    rules_engine_processed: int
    llm_judge_processed: int
    avg_processing_time_ms: float
    active_connectors: int
    system_health: str
    uptime_seconds: float

# SharePoint/Jira JSON Data Models
class SharePointAnswerRequest(BaseModel):
    answers: List[Dict[str, Any]]

class ElasticsearchDataRequest(BaseModel):
    hits: List[Dict[str, Any]]

class ProcessedSharePointRecord(BaseModel):
    id: str
    record_id: str
    title: str
    content: str
    tags: List[str]
    source_type: str
    source_url: str
    confidence: float
    quality_score: float
    quality_checks: List[Dict[str, Any]]
    author_name: str
    company: str
    document_date: str
    created_at: str
    processing_time_ms: float
    trace_id: str  # Add unique trace ID for tracking
    llm_suggestions: Optional[List[str]] = None
    llm_reasoning: Optional[str] = None

def store_record(record_data: Dict):
    """Store record in SQLite database with enhanced schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO processed_records 
        (id, record_id, title, content, tags, source_connector, company, 
         quality_score, quality_level, quality_checks, content_metadata,
         created_at, processing_time_ms, trace_id, llm_suggestions, llm_reasoning,
         status, manual_review_status, issues)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record_data.get('id'),
        record_data.get('record_id'),
        record_data.get('title', ''),
        record_data.get('content', ''),
        json.dumps(record_data.get('tags', [])),
        record_data.get('source_connector'),
        record_data.get('company', ''),
        record_data.get('quality_score', 0),
        record_data.get('quality_level', 'medium'),
        json.dumps(record_data.get('quality_checks', [])),
        json.dumps(record_data.get('content_metadata', {})),
        record_data.get('created_at'),
        record_data.get('processing_time_ms', 0),
        record_data.get('trace_id', ''),
        json.dumps(record_data.get('llm_suggestions', [])),
        record_data.get('llm_reasoning'),
        record_data.get('status', 'flagged'),  # Use status as determined by dynamic threshold logic
        record_data.get('manual_review_status', 'pending'),
        json.dumps(record_data.get('issues', []))
    ))
    
    conn.commit()
    conn.close()

def store_dead_letter(trace_id: str, raw_input: str, error_message: str, error_type: str, source_connector: str = None):
    """Store failed records in dead letter queue"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure source_connector is a string
    if source_connector is None:
        source_connector = ""
    
    cursor.execute('''
        INSERT INTO dead_letters 
        (id, trace_id, raw_input, error_message, error_type, failed_at, source_connector)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        str(uuid.uuid4()),
        trace_id,
        raw_input,
        error_message,
        error_type,
        datetime.now(UTC).isoformat(),
        source_connector
    ))
    
    conn.commit()
    conn.close()

#!/usr/bin/env python3
"""
IndexingQA Local Development Server
Enhanced with custom LLM prompts, constraints, and red-team testing
"""


# Path setup for direct execution
import sys
import os

# Add the backend directory to Python path if not already present
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
    print(f"📁 Added {backend_dir} to Python path")
import json
import time
import uuid
import re
import os
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict
import sqlite3
import threading
from fastapi import Body, File, UploadFile

from fastapi import FastAPI, HTTPException, Request, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
import uvicorn
import aiohttp

# Import unified bulk processor
try:
    from .unified_bulk_ingest import bulk_processor, extract_records_from_upload, create_streaming_response
    UNIFIED_BULK_AVAILABLE = True
    print("✅ Unified bulk processor available")
except ImportError as e:
    print(f"⚠️  Unified bulk processor not available: {e}")
    UNIFIED_BULK_AVAILABLE = False

# Import our rules engine
try:
    from app.services.rules_engine import RulesEngine
    from app.models.models import ChunkIngestRequest, QualityCheckResult, FlagStatus, SourceConnector
    from app.core.config import get_settings
    from app.services.alerts import AlertManager
    from app.services.schema_validator import SchemaValidator
    from app.services.dynamic_rules_manager import get_dynamic_rules_manager, initialize_dynamic_rules_manager
    RULES_ENGINE_AVAILABLE = True
    ALERT_MANAGER_AVAILABLE = True
    SCHEMA_VALIDATOR_AVAILABLE = True
    DYNAMIC_RULES_AVAILABLE = True
    print("✅ Rules engine, alert manager, schema validator, and dynamic rules manager available")
except ImportError as e:
    print(f"⚠️  Services not available - using enhanced mock responses: {e}")
    RULES_ENGINE_AVAILABLE = False
    ALERT_MANAGER_AVAILABLE = False
    SCHEMA_VALIDATOR_AVAILABLE = False
    DYNAMIC_RULES_AVAILABLE = False

# Check for LLM libraries
try:
    import openai
    LLM_AVAILABLE = True
    print("✅ OpenAI library available")
except ImportError:
    LLM_AVAILABLE = False
    print("⚠️  OpenAI library not available - using fallback mode")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
    print("✅ Anthropic library available")
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️  Anthropic library not available")

# Initialize global variables
processed_records = []
processed_count = 0
llm_processed_count = 0
redteam_results = []
start_time = datetime.now(UTC)
evaluation_metrics = {
    'total_analyses': 0,
    'methodology_performance': defaultdict(list),
    'user_feedback': []
}

# Initialize settings
settings = None
if RULES_ENGINE_AVAILABLE:
    try:
        settings = get_settings()
    except Exception as e:
        print(f"⚠️ Warning: Could not load settings: {e}")
        settings = None

# Initialize rules engine if available
rules_engine = None
alert_manager = None
llm_judge = None

if RULES_ENGINE_AVAILABLE:
    try:
        rules_engine = RulesEngine()
        print("✅ Rules engine initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize rules engine: {e}")
        RULES_ENGINE_AVAILABLE = False

if ALERT_MANAGER_AVAILABLE:
    try:
        alert_manager = AlertManager()
        print("✅ Alert manager initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize alert manager: {e}")
        ALERT_MANAGER_AVAILABLE = False

# Initialize LLM judge for semantic validation
try:
    from app.services.llm_judge import LLMJudge
    llm_judge = LLMJudge()
    print("✅ LLM judge initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize LLM judge: {e}")
    llm_judge = None

# Initialize schema validator
schema_validator = None
if SCHEMA_VALIDATOR_AVAILABLE:
    try:
        schema_validator = SchemaValidator()
        print("✅ Schema validator initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize schema validator: {e}")
        SCHEMA_VALIDATOR_AVAILABLE = False

# Initialize dynamic rules manager
rules_manager = None
if DYNAMIC_RULES_AVAILABLE:
    try:
        rules_manager = initialize_dynamic_rules_manager()
        print("✅ Dynamic Rules Manager initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Dynamic Rules Manager: {e}")
        DYNAMIC_RULES_AVAILABLE = False

# Initialize SQLite database for persistent storage - Fixed path to use main database
DB_PATH = os.path.join(backend_dir, "indexing_qa.db")
print(f"🗄️  Database path: {DB_PATH}")
print(f"🗄️  Database exists: {os.path.exists(DB_PATH)}")
if os.path.exists(DB_PATH):
    print(f"🗄️  Database size: {os.path.getsize(DB_PATH)} bytes")

# Verify we're using the right database
if not os.path.exists(DB_PATH):
    # Fallback to the main backend directory database
    fallback_path = os.path.join(os.path.dirname(backend_dir), "backend", "indexing_qa.db")
    if os.path.exists(fallback_path):
        DB_PATH = fallback_path
        print(f"🔄 Using fallback database path: {DB_PATH}")
    else:
        print(f"⚠️  Database not found at {DB_PATH} or {fallback_path}")

print(f"✅ Final database path: {DB_PATH} (exists: {os.path.exists(DB_PATH)})")

def init_database():
    """Initialize database with proper schema"""
    try:
        # Create database connection
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create all required tables from create_table.py
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_records (
                id TEXT PRIMARY KEY,
                record_id TEXT,
                title TEXT,
                content TEXT,
                tags TEXT,
                source_connector TEXT,
                company TEXT,
                quality_score REAL,
                quality_level TEXT,
                quality_checks TEXT,
                content_metadata TEXT,
                created_at TEXT,
                processing_time_ms REAL,
                trace_id TEXT,
                llm_suggestions TEXT,
                llm_reasoning TEXT,
                status TEXT,
                manual_review_status TEXT,
                issues TEXT,
                alert_sent BOOLEAN DEFAULT 0,
                email_recipients TEXT,
                alert_type TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quality_checks (
                id TEXT PRIMARY KEY,
                record_id TEXT,
                check_name TEXT,
                status TEXT,
                confidence_score REAL,
                failure_reason TEXT,
                check_metadata_json TEXT,
                executed_at TEXT,
                processing_time_ms REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS request_logs (
                id TEXT PRIMARY KEY,
                trace_id TEXT,
                endpoint TEXT,
                method TEXT,
                request_data TEXT,
                response_status INTEGER,
                response_data TEXT,
                processing_time_ms REAL,
                created_at TEXT,
                error_message TEXT,
                source_connector TEXT,
                success BOOLEAN DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dynamic_thresholds (
                threshold_name TEXT PRIMARY KEY,
                current_value REAL,
                default_value REAL,
                min_value REAL,
                max_value REAL,
                description TEXT,
                category TEXT,
                unit TEXT,
                updated_by TEXT,
                updated_at TEXT,
                reason TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS threshold_history (
                id TEXT PRIMARY KEY,
                threshold_name TEXT,
                old_value REAL,
                new_value REAL,
                changed_by TEXT,
                reason TEXT,
                timestamp TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_templates (
                id TEXT PRIMARY KEY,
                name TEXT,
                subject TEXT,
                body TEXT,
                type TEXT,
                is_active BOOLEAN,
                created_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_recipients (
                id TEXT PRIMARY KEY,
                email TEXT,
                name TEXT,
                role TEXT,
                alert_types TEXT,
                is_active BOOLEAN,
                created_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS llm_settings_history (
                id TEXT PRIMARY KEY,
                changed_by TEXT,
                old_mode TEXT,
                new_mode TEXT,
                old_threshold REAL,
                new_threshold REAL,
                timestamp TEXT,
                reason TEXT
            )
        ''')
        
        # Create dead_letters table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dead_letters (
                id TEXT PRIMARY KEY,
                trace_id TEXT,
                raw_input TEXT NOT NULL,
                error_message TEXT NOT NULL,
                error_type TEXT NOT NULL,
                failed_at TEXT NOT NULL,
                source_connector TEXT,
                retry_count INTEGER DEFAULT 0,
                resolved BOOLEAN DEFAULT 0
            )
        ''')
        
        # Check if processed_records table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_records'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Check for missing columns and add them
            cursor.execute("PRAGMA table_info(processed_records)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add missing columns if they don't exist
            missing_columns = [
                ('trace_id', 'TEXT'),
                ('llm_suggestions', 'TEXT'),
                ('llm_reasoning', 'TEXT'),
                ('status', 'TEXT'),
                ('manual_review_status', 'TEXT'),
                ('issues', 'TEXT'),
                ('alert_sent', 'BOOLEAN DEFAULT 0'),
                ('email_recipients', 'TEXT'),
                ('alert_type', 'TEXT')
            ]
            
            for column_name, column_type in missing_columns:
                if column_name not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE processed_records ADD COLUMN {column_name} {column_type}")
                        print(f"Added missing column: {column_name}")
                    except Exception as e:
                        print(f"Error adding column {column_name}: {e}")
        
        conn.commit()
        conn.close()
        print("Database initialization completed")
        
    except Exception as e:
        print(f"Error initializing database: {e}")

def populate_sample_data():
    """Populate database with sample data for testing"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if we already have data
    cursor.execute("SELECT COUNT(*) FROM processed_records")
    if cursor.fetchone()[0] > 0:
        print("Database already has data, skipping sample data population")
        conn.close()
        return
    
    print("Populating database with sample data...")
    
    sample_records = [
        {
            'record_id': 'sample-001',
            'title': 'Machine Learning Best Practices',
            'content': 'This document outlines the best practices for implementing machine learning algorithms in production environments. It covers data preprocessing, model selection, and deployment strategies.',
            'tags': ['machine learning', 'best practices', 'production', 'algorithms'],
            'source_connector': 'SharePoint',
            'company': 'TechCorp Inc',
            'quality_score': 85.5,
            'quality_level': 'high',
            'quality_checks': [
                {
                    'check_name': 'text_quality',
                    'status': 'pass',
                    'confidence_score': 0.9,
                    'failure_reason': None
                },
                {
                    'check_name': 'tag_text_relevance',
                    'status': 'pass',
                    'confidence_score': 0.85,
                    'failure_reason': None
                }
            ],
            'content_metadata': {
                'author': 'Dr. Sarah Johnson',
                'department': 'Data Science',
                'document_type': 'technical_guide',
                'word_count': 1250
            },
            'llm_suggestions': ['Consider adding more specific examples', 'Include code snippets for clarity'],
            'llm_reasoning': 'Content is well-structured and relevant. Tags are appropriate and descriptive.'
        },
        {
            'record_id': 'sample-002',
            'title': 'Employee Handbook - Vacation Policy',
            'content': 'Employees are entitled to 20 days of paid vacation per year. Vacation requests must be submitted at least 2 weeks in advance.',
            'tags': ['hr', 'vacation', 'policy'],
            'source_connector': 'Confluence',
            'company': 'TechCorp Inc',
            'quality_score': 72.0,
            'quality_level': 'medium',
            'quality_checks': [
                {
                    'check_name': 'text_quality',
                    'status': 'pass',
                    'confidence_score': 0.7,
                    'failure_reason': None
                },
                {
                    'check_name': 'tag_count_validation',
                    'status': 'fail',
                    'confidence_score': 0.6,
                    'failure_reason': 'Too few tags: 3 < 5'
                }
            ],
            'content_metadata': {
                'author': 'HR Department',
                'department': 'Human Resources',
                'document_type': 'policy',
                'word_count': 45
            },
            'llm_suggestions': ['Add more specific details about vacation accrual', 'Include examples of acceptable vacation reasons'],
            'llm_reasoning': 'Content is clear but could be more detailed. Tags are relevant but could be more specific.'
        },
        {
            'record_id': 'sample-003',
            'title': 'API Documentation - User Authentication',
            'content': 'This API provides user authentication endpoints. Use POST /auth/login to authenticate users and GET /auth/verify to validate tokens.',
            'tags': ['api', 'authentication', 'documentation'],
            'source_connector': 'Notion',
            'company': 'TechCorp Inc',
            'quality_score': 91.0,
            'quality_level': 'high',
            'quality_checks': [
                {
                    'check_name': 'text_quality',
                    'status': 'pass',
                    'confidence_score': 0.95,
                    'failure_reason': None
                },
                {
                    'check_name': 'tag_text_relevance',
                    'status': 'pass',
                    'confidence_score': 0.92,
                    'failure_reason': None
                }
            ],
            'content_metadata': {
                'author': 'Engineering Team',
                'department': 'Engineering',
                'document_type': 'api_docs',
                'word_count': 89
            },
            'llm_suggestions': ['Add code examples for each endpoint', 'Include error handling scenarios'],
            'llm_reasoning': 'Excellent technical documentation with clear structure and relevant tags.'
        }
    ]
    
    for record in sample_records:
        cursor.execute('''
            INSERT INTO processed_records (
                id, record_id, title, content, tags, source_connector, company,
                quality_score, quality_level, quality_checks, content_metadata,
                created_at, processing_time_ms, llm_suggestions, llm_reasoning, trace_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"record-{record['record_id']}",  # Generate proper ID
            record['record_id'],
            record['title'],
            record['content'],
            json.dumps(record['tags']),
            record['source_connector'],
            record['company'],
            record['quality_score'],
            record['quality_level'],
            json.dumps(record['quality_checks']),
            json.dumps(record['content_metadata']),
            datetime.now(UTC).isoformat(),
            150.0,  # processing time
            json.dumps(record['llm_suggestions']),
            record['llm_reasoning'],
            f"trace-{record['record_id']}"
        ))
    
    conn.commit()
    conn.close()
    print(f"Added {len(sample_records)} sample records to database")

# Initialize database
init_database()

# Populate with sample data if empty
populate_sample_data()

# Data models for API
class ContentIngestRequest(BaseModel):
    record_id: str
    content: str
    tags: List[str]
    source_connector: str
    content_metadata: Optional[Dict] = None

class RulesCheckRequest(BaseModel):
    content: str = Field(..., alias="document_text")
    tags: List[str] 
    source_connector: str
    
    class Config:
        allow_population_by_field_name = True

class LLMAnalysisRequest(BaseModel):
    content: str
    tags: List[str]
    context: Optional[Dict] = None



class RedTeamRequest(BaseModel):
    scenario_id: str
    content: str
    tags: List[str]
    test_objectives: List[str]
    expected_issues: Optional[List[str]] = None

class QualityConstraint(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool
    weight: float
    rule: str

class SystemStats(BaseModel):
    total_processed: int
    rules_engine_processed: int
    llm_judge_processed: int
    avg_processing_time_ms: float
    active_connectors: int
    system_health: str
    uptime_seconds: float

# SharePoint/Jira JSON Data Models
class SharePointAnswerRequest(BaseModel):
    answers: List[Dict[str, Any]]

class ElasticsearchDataRequest(BaseModel):
    hits: List[Dict[str, Any]]

class ProcessedSharePointRecord(BaseModel):
    id: str
    record_id: str
    title: str
    content: str
    tags: List[str]
    source_type: str
    source_url: str
    confidence: float
    quality_score: float
    quality_checks: List[Dict[str, Any]]
    author_name: str
    company: str
    document_date: str
    created_at: str
    processing_time_ms: float
    trace_id: str  # Add unique trace ID for tracking
    llm_suggestions: Optional[List[str]] = None
    llm_reasoning: Optional[str] = None

def store_record(record_data: Dict):
    """Store record in SQLite database with enhanced schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO processed_records 
        (id, record_id, title, content, tags, source_connector, company, 
         quality_score, quality_level, quality_checks, content_metadata,
         created_at, processing_time_ms, trace_id, llm_suggestions, llm_reasoning,
         status, manual_review_status, issues)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record_data.get('id'),
        record_data.get('record_id'),
        record_data.get('title', ''),
        record_data.get('content', ''),
        json.dumps(record_data.get('tags', [])),
        record_data.get('source_connector'),
        record_data.get('company', ''),
        record_data.get('quality_score', 0),
        record_data.get('quality_level', 'medium'),
        json.dumps(record_data.get('quality_checks', [])),
        json.dumps(record_data.get('content_metadata', {})),
        record_data.get('created_at'),
        record_data.get('processing_time_ms', 0),
        record_data.get('trace_id', ''),
        json.dumps(record_data.get('llm_suggestions', [])),
        record_data.get('llm_reasoning'),
        record_data.get('status', 'flagged'),  # Use status as determined by dynamic threshold logic
        record_data.get('manual_review_status', 'pending'),
        json.dumps(record_data.get('issues', []))
    ))
    
    conn.commit()
    conn.close()

def store_dead_letter(trace_id: str, raw_input: str, error_message: str, error_type: str, source_connector: str = None):
    """Store failed records in dead letter queue"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure source_connector is a string
    if source_connector is None:
        source_connector = ""
    
    cursor.execute('''
        INSERT INTO dead_letters 
        (id, trace_id, raw_input, error_message, error_type, failed_at, source_connector)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        str(uuid.uuid4()),
        trace_id,
        raw_input,
        error_message,
        error_type,
        datetime.now(UTC).isoformat(),
        source_connector
    ))
    
    conn.commit()
    conn.close()

def get_records_from_db(filters: Dict = None, page: int = 1, page_size: int = 25):
    """Get records from SQLite database with filtering using enhanced schema"""
    try:
        # Use hardcoded thresholds for now to avoid settings dependency issues
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        query = "SELECT * FROM processed_records WHERE 1=1"
        params = []
        
        if filters:
            # Handle companies filter
            if filters.get('companies'):
                companies_list = filters['companies'] if isinstance(filters['companies'], list) else [filters['companies']]
                placeholders = ','.join(['?' for _ in companies_list])
                query += f" AND company IN ({placeholders})"
                params.extend(companies_list)
            
            # Handle sourceConnectors filter
            if filters.get('sourceConnectors'):
                connectors_list = filters['sourceConnectors'] if isinstance(filters['sourceConnectors'], list) else [filters['sourceConnectors']]
                placeholders = ','.join(['?' for _ in connectors_list])
                query += f" AND source_connector IN ({placeholders})"
                params.extend(connectors_list)
            
            # Handle statuses filter (map to quality_level) - using hardcoded thresholds
            if filters.get('statuses'):
                statuses_list = filters['statuses'] if isinstance(filters['statuses'], list) else [filters['statuses']]
                status_conditions = []
                
                # Get dynamic approval threshold for fallback
                try:
                    approval_threshold = get_threshold_value("approval_quality_score_threshold") or 50.0
                except (AttributeError, ValueError):
                    approval_threshold = 50.0
                
                for status in statuses_list:
                    # Use real current status from audit trails, then actual status field, fallback to quality score
                    condition = f"""(
                        CASE 
                            WHEN manual_review_status IS NOT NULL AND manual_review_status != 'pending' AND 
                                 manual_review_status LIKE '%status_change%' THEN
                                (
                                    SELECT json_extract(value, '$.status_change.new')
                                    FROM json_each(manual_review_status)
                                    WHERE json_extract(value, '$.status_change') IS NOT NULL
                                    ORDER BY json_extract(value, '$.timestamp') DESC
                                    LIMIT 1
                                )
                            WHEN status IS NOT NULL THEN status
                            WHEN CAST(quality_score AS REAL) >= {approval_threshold} THEN 'approved'
                            ELSE 'flagged'
                        END = '{status}'
                    )"""
                    status_conditions.append(condition)
                if status_conditions:
                    query += f" AND ({' OR '.join(status_conditions)})"
            
            # Handle priorities filter - using hardcoded thresholds
            if filters.get('priorities'):
                priorities_list = filters['priorities'] if isinstance(filters['priorities'], list) else [filters['priorities']]
                priority_conditions = []
                for priority in priorities_list:
                    if priority == 'high':
                        priority_conditions.append(f"CAST(quality_score AS REAL) >= 40.0 AND CAST(quality_score AS REAL) < 80.0")
                    elif priority == 'medium':
                        priority_conditions.append(f"0.8 <= CAST(quality_score AS REAL)")
                    elif priority == 'low':
                        priority_conditions.append(f"CAST(quality_score AS REAL) >= 80.0")
                if priority_conditions:
                    query += f" AND ({' OR '.join(priority_conditions)})"
            
            # Handle tags filter
            if filters.get('tags'):
                tags_list = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
                for tag in tags_list:
                    query += " AND tags LIKE ?"
                    params.append(f'%{tag}%')
            
            # Handle departments filter (from content_metadata)
            if filters.get('departments'):
                departments_list = filters['departments'] if isinstance(filters['departments'], list) else [filters['departments']]
                for dept in departments_list:
                    query += " AND content_metadata LIKE ?"
                    params.append(f'%"department":"{dept}"%')
            
            # Handle authors filter (from content_metadata)
            if filters.get('authors'):
                authors_list = filters['authors'] if isinstance(filters['authors'], list) else [filters['authors']]
                for author in authors_list:
                    query += " AND content_metadata LIKE ?"
                    params.append(f'%"author":"{author}"%')
            
            # Handle searchQuery filter
            if filters.get('searchQuery'):
                search_term = filters['searchQuery']
                query += " AND (content LIKE ? OR title LIKE ? OR company LIKE ?)"
                params.extend([f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'])
        
        # Add sorting
        sort_by = filters.get('sortBy', 'created_at') if filters else 'created_at'
        sort_order = filters.get('sortOrder', 'desc') if filters else 'desc'
        
        # Map frontend sort fields to database columns
        sort_field_mapping = {
            'createdAt': 'created_at',
            'updatedAt': 'created_at',  # Using created_at as fallback
            'qualityScore': 'quality_score',
            'companyName': 'company',
            'sourceConnectorName': 'source_connector'
        }
        
        db_sort_field = sort_field_mapping.get(sort_by, 'created_at')
        query += f" ORDER BY {db_sort_field} {sort_order.upper()}"
        
        # Add pagination
        offset = (page - 1) * page_size
        query += f" LIMIT ? OFFSET ?"
        params.extend([page_size, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            try:
                # Map enhanced schema columns to expected format
                # Column order: id, record_id, title, content, tags, source_connector, company, 
                # quality_score, quality_level, quality_checks, content_metadata, created_at, 
                # processing_time_ms, trace_id, llm_suggestions, llm_reasoning, status, 
                # manual_review_status, reviewer_comments, reviewed_at, reviewer_id
                
                # Safely parse JSON fields
                tags = []
                print(f"🔧 DEBUG: Processing record {row[1]} - row[5] (tags): {row[5]}")
                if len(row) > 5 and row[5] and row[5] != 'null' and isinstance(row[5], str):
                    try:
                        tags = json.loads(row[5])
                        print(f"✅ DEBUG: Successfully parsed tags for {row[1]}: {tags}")
                    except Exception as e:
                        print(f"❌ DEBUG: Failed to parse tags for {row[1]}: {e}")
                        tags = []
                else:
                    print(f"⚠️ DEBUG: No tags or invalid tags for {row[1]}: len(row)={len(row)}, row[5]={row[5]}")
                
                quality_checks = []
                if row[9] and row[9] != 'null' and isinstance(row[9], str):
                    try:
                        quality_checks = json.loads(row[9])
                    except:
                        quality_checks = []
                
                content_metadata = {}
                if row[10] and row[10] != 'null' and isinstance(row[10], str):
                    try:
                        content_metadata = json.loads(row[10])
                    except:
                        content_metadata = {}
                
                llm_suggestions = []
                if len(row) > 33 and row[33] and row[33] != 'null' and isinstance(row[33], str):
                    try:
                        llm_suggestions = json.loads(row[33])
                    except:
                        llm_suggestions = []
                
                # Parse additional JSON fields safely
                issues = []
                if len(row) > 36 and row[36] and row[36] != 'null' and isinstance(row[36], str):
                    try:
                        issues = json.loads(row[36])
                    except:
                        issues = []
                
                records.append({
                    'id': row[0],
                    'record_id': row[1],
                    'title': row[4] if len(row) > 4 and row[4] else (row[3][:100] + '...' if row[3] and len(row[3]) > 100 else row[3] or ''),
                    'content': row[3] or '',  # content is column 3
                    'tags': tags,
                    'source_connector': row[6] if len(row) > 6 and row[6] else '',
                    'company': row[29] if len(row) > 29 and row[29] else 'Default Company',
                    'quality_score': float(row[8]) if len(row) > 8 and row[8] is not None else 0.8,
                    'quality_level': row[9] if len(row) > 9 and row[9] else 'medium',
                    'quality_checks': quality_checks,
                    'content_metadata': content_metadata,
                    'created_at': row[13] if len(row) > 13 and row[13] else datetime.now(UTC).isoformat(),
                    'processing_time_ms': row[12] if len(row) > 12 and row[12] else 0,
                    'trace_id': row[14] if len(row) > 14 and row[14] else f"trace-{row[1]}",
                    # Add missing fields for compatibility
                    'status': row[34] if len(row) > 34 and row[34] else 'processed',
                    'priority': row[30] if len(row) > 30 and row[30] else 'medium',
                    'issues': issues,
                    'llm_suggestions': llm_suggestions,
                    'llm_reasoning': row[20] if len(row) > 20 and row[20] else None,
                    'company_name': row[29] if len(row) > 29 and row[29] else 'Default Company',  # company
                    'source_connector_name': row[6] if len(row) > 6 and row[6] else ''  # source_connector
                })
            except Exception as e:
                print(f"Error processing row {row[0]}: {e}")
                continue
        
        conn.close()
        return records
    except Exception as e:
        print(f"Error in get_records_from_db: {e}")
        return []

def get_unified_metrics_data():
    """Get unified real-time metrics data for both dashboard and analytics"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table exists and has data
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_records'")
        if not cursor.fetchone():
            conn.close()
            return {
                'total_records': 0,
                'todays_records': 0,
                'avg_quality_score': 0,
                'issues_count': 0,
                'critical_issues': 0,
                'active_sources': 0,
                'companies_count': 0,
                'today': {
                    'total_processed': 0,
                    'avg_quality_score': 0,
                    'total_issues': 0
                },
                'weekly_trend': [],
                'source_performance': []
            }
        
        # Get comprehensive stats (ALL records)
        cursor.execute('''
            SELECT COUNT(*) as total, AVG(quality_score) as avg_score, 
                   SUM(CASE WHEN CAST(quality_score AS REAL) < 50 THEN 1 ELSE 0 END) as low_quality_issues,
                   COUNT(DISTINCT source_connector) as sources,
                   COUNT(DISTINCT company) as companies
            FROM processed_records
        ''')
        
        total_stats = cursor.fetchone()
        
        # Get today's stats specifically 
        today = datetime.now(UTC).date().isoformat()
        cursor.execute('''
            SELECT COUNT(*) as total, AVG(quality_score) as avg_score, 
                   SUM(CASE WHEN CAST(quality_score AS REAL) < 50 THEN 1 ELSE 0 END) as issues
            FROM processed_records 
            WHERE DATE(created_at) = ?
        ''', (today,))
        
        today_stats = cursor.fetchone()
        
        # Get weekly trend
        week_ago = (datetime.now(UTC) - timedelta(days=7)).date().isoformat()
        cursor.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as count, AVG(quality_score) as avg_score
            FROM processed_records 
            WHERE DATE(created_at) >= ?
            GROUP BY DATE(created_at)
            ORDER BY date
        ''', (week_ago,))
        
        weekly_trend = cursor.fetchall()
        
        # Get source performance
        cursor.execute('''
            SELECT source_connector, COUNT(*) as count, AVG(quality_score) as avg_score
            FROM processed_records 
            WHERE DATE(created_at) >= ?
            GROUP BY source_connector
        ''', (week_ago,))
        
        source_performance = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_records': total_stats[0] if total_stats else 0,
            'todays_records': today_stats[0] if today_stats else 0,
            'avg_quality_score': round(total_stats[1], 1) if total_stats and total_stats[1] else 0,
            'issues_count': total_stats[2] if total_stats else 0,
            'critical_issues': max(0, (total_stats[2] if total_stats else 0) - 3),
            'active_sources': total_stats[3] if total_stats else 0,
            'companies_count': total_stats[4] if total_stats else 0,
            'today': {
                'total_processed': today_stats[0] if today_stats else 0,
                'avg_quality_score': round(today_stats[1], 1) if today_stats and today_stats[1] else 0,
                'total_issues': today_stats[2] if today_stats else 0
            },
            'weekly_trend': [
                {'date': row[0], 'processed': row[1], 'avg_quality': round(row[2], 1)}
                for row in weekly_trend
            ],
            'source_performance': [
                {'source': row[0], 'processed': row[1], 'avg_quality': round(row[2], 1)}
                for row in source_performance
            ]
        }
    except Exception as e:
        print(f"Error in get_analytics_data: {e}")
        return {
            'today': {
                'total_processed': 0,
                'avg_quality_score': 0,
                'total_issues': 0
            },
            'weekly_trend': [],
            'source_performance': []
        }

def get_issues_data():
    """Get real-time issues data using enhanced schema"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_records'")
        if not cursor.fetchone():
            # Table doesn't exist, return empty data
            conn.close()
            return []
        
        # Get records with low quality or issues using enhanced schema
        cursor.execute('''
            SELECT quality_checks, quality_level, created_at, company, record_id, title, quality_score
            FROM processed_records 
            WHERE quality_level IN ('low', 'medium') OR CAST(quality_score AS REAL) < 80
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        issues = []
        
        for row in rows:
            quality_checks = json.loads(row[0]) if row[0] else []
            quality_level = row[1]
            created_at = row[2]
            company = row[3]
            record_id = row[4]
            title = row[5]
            quality_score = float(row[6]) if row[6] is not None else 0.0
            
            # Create issues from quality checks
            for check in quality_checks:
                if check.get('status') == 'fail':
                    issues.append({
                        'id': f"issue-{len(issues)+1}",
                        'type': check.get('check_name', 'unknown'),
                        'severity': 'high' if float(quality_score) < 50 else 'medium',
                        'description': check.get('failure_reason', 'Quality check failed'),
                        'autoFixable': check.get('check_name') in ['empty_tags', 'tag_count_validation'],
                        'category': 'content',
                        'record': {
                            'id': record_id,
                            'recordId': record_id,
                            'companyName': company,
                            'status': quality_level,
                            'priority': 'high' if float(quality_score) < 50 else 'medium',
                            'createdAt': created_at,
                            'title': title,
                            'qualityScore': quality_score
                        }
                    })
        
        conn.close()
        return issues
    except Exception as e:
        print(f"Error in get_issues_data: {e}")
        return []

def extract_tags_from_sharepoint_content(content: str, title: str = "", company: str = "") -> List[str]:
    """Extract meaningful tags from SharePoint/Jira content"""
    # Clean HTML tags
    clean_content = re.sub(r'<[^>]+>', ' ', content)
    clean_title = re.sub(r'<[^>]+>', ' ', title)
    
    # Combine all text
    full_text = f"{clean_title} {clean_content}".lower()
    
    tags = []
    
    # Business terms
    business_terms = ['strategy', 'process', 'workflow', 'analysis', 'report', 'dashboard', 
                     'metrics', 'performance', 'optimization', 'framework', 'methodology']
    for term in business_terms:
        if term in full_text:
            tags.append(term)
    
    # Technical terms
    tech_terms = ['api', 'database', 'integration', 'architecture', 'deployment', 'monitoring',
                 'security', 'authentication', 'authorization', 'encryption', 'backup']
    for term in tech_terms:
        if term in full_text:
            tags.append(term)
    
    # Document types
    doc_types = ['guide', 'tutorial', 'documentation', 'manual', 'specification', 'requirements',
                'presentation', 'slide', 'spreadsheet', 'template', 'checklist']
    for doc_type in doc_types:
        if doc_type in full_text:
            tags.append(doc_type)
    
    # Company/Product specific terms
    if 'lucy' in full_text or 'jira' in full_text:
        tags.append('lucy-ai')
    if 'jira' in full_text:
        tags.append('jira')
    if 'sharepoint' in full_text:
        tags.append('sharepoint')
    if 'amex' in full_text or 'american express' in full_text:
        tags.append('american-express')
    if company and company.lower() not in ['bingsearch']:
        tags.append(f"company-{company.lower()}")
    
    # Remove duplicates and limit to reasonable number
    return list(set(tags))[:15]

def analyze_sharepoint_content_quality(content: str, tags: List[str], source_type: str) -> tuple[float, List[Dict[str, Any]]]:
    """Analyze SharePoint/Jira content quality and return score with detailed checks"""
    checks = []
    total_score = 0
    check_count = 0
    
    # 1. Content Length Check
    content_length = len(content.strip())
    if content_length > 500:
        checks.append({
            "check_name": "content_length",
            "status": "PASS",
            "confidence_score": 0.95,
            "metadata": {"length": content_length}
        })
        total_score += 90
    elif content_length > 100:
        checks.append({
            "check_name": "content_length", 
            "status": "PASS",
            "confidence_score": 0.8,
            "metadata": {"length": content_length}
        })
        total_score += 75
    else:
        checks.append({
            "check_name": "content_length",
            "status": "FAIL", 
            "confidence_score": 0.9,
            "failure_reason": f"Content too short: {content_length} characters",
            "metadata": {"length": content_length}
        })
        total_score += 40
    check_count += 1
    
    # 2. HTML Content Quality
    html_ratio = len(re.findall(r'<[^>]+>', content)) / max(len(content.split()), 1)
    if html_ratio < 0.1:
        checks.append({
            "check_name": "html_content_ratio",
            "status": "PASS",
            "confidence_score": 0.85,
            "metadata": {"html_ratio": html_ratio}
        })
        total_score += 85
    elif html_ratio < 0.3:
        checks.append({
            "check_name": "html_content_ratio",
            "status": "WARNING",
            "confidence_score": 0.7,
            "failure_reason": "High HTML content ratio may indicate formatting issues",
            "metadata": {"html_ratio": html_ratio}
        })
        total_score += 65
    else:
        checks.append({
            "check_name": "html_content_ratio",
            "status": "FAIL",
            "confidence_score": 0.8,
            "failure_reason": "Content mostly HTML tags, lacks substantial text",
            "metadata": {"html_ratio": html_ratio}
        })
        total_score += 30
    check_count += 1
    
    # 3. Tag Quality Check
    if len(tags) >= 3:
        checks.append({
            "check_name": "tag_quantity",
            "status": "PASS",
            "confidence_score": 0.9,
            "metadata": {"tag_count": len(tags)}
        })
        total_score += 85
    elif len(tags) >= 1:
        checks.append({
            "check_name": "tag_quantity",
            "status": "WARNING",
            "confidence_score": 0.7,
            "failure_reason": "Insufficient tags for good discoverability",
            "metadata": {"tag_count": len(tags)}
        })
        total_score += 65
    else:
        checks.append({
            "check_name": "tag_quantity",
            "status": "FAIL",
            "confidence_score": 0.9,
            "failure_reason": "No meaningful tags extracted",
            "metadata": {"tag_count": len(tags)}
        })
        total_score += 20
    check_count += 1
    
    # 4. Information Density Check  
    clean_content = re.sub(r'<[^>]+>', ' ', content)
    words = clean_content.split()
    unique_words = set(word.lower() for word in words if len(word) > 3)
    
    if len(words) > 0:
        density = len(unique_words) / len(words)
        if density > 0.4:
            checks.append({
                "check_name": "information_density",
                "status": "PASS",
                "confidence_score": 0.8,
                "metadata": {"density": density, "unique_words": len(unique_words)}
            })
            total_score += 80
        elif density > 0.2:
            checks.append({
                "check_name": "information_density",
                "status": "WARNING",
                "confidence_score": 0.7,
                "failure_reason": "Moderate information density",
                "metadata": {"density": density, "unique_words": len(unique_words)}
            })
            total_score += 60
        else:
            checks.append({
                "check_name": "information_density",
                "status": "FAIL",
                "confidence_score": 0.8,
                "failure_reason": "Low information density, possible duplication",
                "metadata": {"density": density, "unique_words": len(unique_words)}
            })
            total_score += 40
        check_count += 1
    
    # 5. Source-Specific Quality Checks
    if source_type == "jira":
        # Jira specific checks
        if any(keyword in content.lower() for keyword in ["story", "task", "bug", "epic", "ticket", "acceptance criteria"]):
            checks.append({
                "check_name": "jira_type_detected",
                "status": "PASS",
                "confidence_score": 0.95,
                "metadata": {"jira_content": True}
            })
            total_score += 90
        check_count += 1
    elif source_type == "sharepoint":
        # SharePoint specific checks
        if "pdf" in content.lower() or ".pdf" in content.lower():
            checks.append({
                "check_name": "document_type",
                "status": "PASS",
                "confidence_score": 0.9,
                "metadata": {"document_type": "pdf"}
            })
            total_score += 85
        check_count += 1
    
    # Calculate final score
    final_score = total_score / max(check_count, 1) if check_count > 0 else 50
    return min(100, max(0, final_score)), checks

def transform_sharepoint_answer(answer: Dict[str, Any]) -> ProcessedSharePointRecord:
    """Transform a SharePoint/Jira answer into our processed record format"""
    start_time = time.time()
    
    # Extract core data
    answer_id = answer.get("AnswerID", "unknown")
    title = answer.get("Title", "").strip()
    text_content = answer.get("Text", "")
    combined_data = answer.get("combinedData", "")
    
    # Use combinedData if it has more content, otherwise use Text
    content = combined_data if len(combined_data) > len(text_content) else text_content
    
    # Determine source type
    source_type = "jira" if "jira" in answer.get("Cite", "").lower() or "jira" in answer.get("Source", "").lower() else "sharepoint"
    
    # Extract tags from content
    company = answer.get("Company", "")
    extracted_tags = extract_tags_from_sharepoint_content(content, title, company)
    
    # Analyze quality
    quality_score, quality_checks = analyze_sharepoint_content_quality(content, extracted_tags, source_type)
    
    processing_time = (time.time() - start_time) * 1000
    
    return ProcessedSharePointRecord(
        id=answer_id,
        record_id=answer_id,
        title=title,
        content=content,
        tags=extracted_tags,
        source_type=source_type,
        source_url=answer.get("Source", ""),
        confidence=float(answer.get("Confidence", 0.0)),
        quality_score=quality_score,
        quality_checks=quality_checks,
        author_name=answer.get("author_name", ""),
        company=company,
        document_date=answer.get("documentDate", ""),
        created_at=datetime.now(UTC).isoformat(),
        processing_time_ms=processing_time,
        trace_id=str(uuid.uuid4())  # Add unique trace ID
    )

def transform_elasticsearch_hit(hit: Dict[str, Any]) -> ProcessedSharePointRecord:
    """Transform an Elasticsearch hit with _source structure into our processed record format"""
    start_time = time.time()
    
    # Extract data from _source
    source = hit.get("_source", {})
    
    # Extract core data
    record_id = source.get("id", str(uuid.uuid4()))
    title = source.get("title", "").strip()
    
    # Get content from various possible fields
    content = source.get("combined_data", "")
    if not content:
        content = source.get("parser_data", "")
    if not content:
        content = source.get("text", "")
    
    # Clean HTML tags from content
    content = re.sub(r'<[^>]+>', ' ', content)
    
    # Extract tags from concepts_nlu and keywords_nlu if available
    extracted_tags = []
    concepts = source.get("concepts_nlu", [])
    keywords = source.get("keywords_nlu", [])
    
    # Extract tags from concepts
    for concept in concepts:
        if isinstance(concept, dict) and "text" in concept:
            if isinstance(concept["text"], list):
                extracted_tags.extend(concept["text"])
            else:
                extracted_tags.append(str(concept["text"]))
    
    # Extract tags from keywords
    for keyword in keywords:
        if isinstance(keyword, dict) and "text" in keyword:
            extracted_tags.append(str(keyword["text"]))
    
    # If no tags extracted, generate from content
    if not extracted_tags:
        company = source.get("company", "")
        extracted_tags = extract_tags_from_sharepoint_content(content, title, company)
    
    # Determine source type
    source_type = "sharepoint"  # Default to SharePoint for this format
    
    # Analyze quality
    quality_score, quality_checks = analyze_sharepoint_content_quality(content, extracted_tags, source_type)
    
    processing_time = (time.time() - start_time) * 1000
    
    return ProcessedSharePointRecord(
        id=record_id,
        record_id=record_id,
        title=title,
        content=content,
        tags=extracted_tags[:15],  # Limit tags to 15
        source_type=source_type,
        source_url=source.get("source", ""),
        confidence=float(source.get("confidence", 0.0)),
        quality_score=quality_score,
        quality_checks=quality_checks,
        author_name=source.get("author_name", ""),
        company=source.get("company", ""),
        document_date=source.get("document_date", ""),
        created_at=datetime.now(UTC).isoformat(),
        processing_time_ms=processing_time,
        trace_id=str(uuid.uuid4())  # Add unique trace ID
    )

# Add LLM judge import at the top
from app.services.llm_judge import LLMJudge

# Initialize LLM judge
llm_judge = LLMJudge()

# Initialize FastAPI app
app = FastAPI(
    title="IndexingQA Enhanced Local API",
    description="Local development server with custom LLM prompts and red-team testing",
    version="1.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handler for FastAPI validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation errors and store them in dead letters"""
    
    # Generate trace ID for tracking
    trace_id = f"validation-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    # Get raw request body
    try:
        raw_body = await request.body()
        raw_input = raw_body.decode('utf-8') if raw_body else "{}"
    except Exception:
        raw_input = "{}"
    
    # Extract source connector from raw data if possible
    source_connector = "Unknown"
    try:
        raw_data = json.loads(raw_input) if raw_input != "{}" else {}
        source_connector = raw_data.get('source_connector', 'Unknown')
    except:
        pass
    
    # Format validation errors
    error_details = []
    for error in exc.errors():
        field = '.'.join(str(x) for x in error['loc']) if error['loc'] else 'request'
        message = error['msg']
        error_details.append(f"{field}: {message}")
    
    error_message = f"FastAPI validation failed: {'; '.join(error_details)}"
    
    # Store in dead letters using our existing function
    try:
        store_dead_letter(
            trace_id=trace_id,
            raw_input=raw_input,
            error_message=error_message,
            error_type="FASTAPI_VALIDATION_ERROR",
            source_connector=source_connector
        )
        
        print(f"[VALIDATION ERROR] Stored in dead letters: {trace_id} - {error_message[:100]}...")
        
    except Exception as db_error:
        print(f"[ERROR] Failed to store validation error in dead letters: {db_error}")
    
    # Return standard FastAPI validation error response with our trace ID
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "trace_id": trace_id,
            "stored_in_dead_letters": True,
            "message": f"Validation failed and stored in dead letters with trace_id: {trace_id}"
        }
    )

# Sample data for testing
sample_companies = [
    {"id": "1", "name": "TechCorp Inc", "count": 1250},
    {"id": "2", "name": "DataFlow Ltd", "count": 890},
    {"id": "3", "name": "InnovateCorp", "count": 567},
]

sample_connectors = [
    {"id": "sharepoint-prod", "name": "SharePoint Production", "type": "sharepoint", "status": "active"},
    {"id": "confluence-wiki", "name": "Confluence Wiki", "type": "confluence", "status": "active"},
    {"id": "google-drive", "name": "Google Drive Files", "type": "googledrive", "status": "active"},
    {"id": "slack-archive", "name": "Slack Archive", "type": "slack", "status": "warning"},
]

# Default constraints for LLM judge
default_constraints = {
    'tag_relevance': {
        'name': 'Tag Relevance',
        'description': 'Tags must be highly relevant to content',
        'weight': 0.3,
        'rule': 'At least 80% of tags should directly relate to content topics'
    },
    'content_depth': {
        'name': 'Content Depth', 
        'description': 'Content should be substantial and informative',
        'weight': 0.25,
        'rule': 'Content should be at least 100 words and provide actionable information'
    },
    'no_generic_tags': {
        'name': 'No Generic Tags',
        'description': 'Avoid overly generic or meaningless tags',
        'weight': 0.2,
        'rule': 'Generic tags like "document", "file", "content" should be avoided'
    },
    'technical_accuracy': {
        'name': 'Technical Accuracy',
        'description': 'Technical content should be accurate and current',
        'weight': 0.15,
        'rule': 'Technical information should be verifiable and up-to-date'
    },
    'business_value': {
        'name': 'Business Value',
        'description': 'Content should provide clear business or educational value',
        'weight': 0.1,
        'rule': 'Content should help users achieve specific goals or learn something valuable'
    }
}

def apply_custom_llm_analysis(content: str, tags: List[str], prompt: str, constraints: List[Dict], quality_weights: Dict[str, float], context: Optional[Dict] = None) -> Dict:
    """
    Enhanced LLM analysis with custom prompts and constraints
    """
    global llm_processed_count
    llm_processed_count += 1
    
    # Simulate more sophisticated analysis time
    time.sleep(0.3)
    
    # Parse the custom prompt and replace placeholders
    formatted_prompt = prompt.replace('{{content}}', content)
    formatted_prompt = formatted_prompt.replace('{{tags}}', ', '.join(tags))
    formatted_prompt = formatted_prompt.replace('{{source}}', context.get('source', 'unknown') if context else 'unknown')
    formatted_prompt = formatted_prompt.replace('{{context}}', json.dumps(context) if context else '{}')
    
    # Apply constraints and calculate weighted score
    content_length = len(content)
    tag_count = len(tags)
    
    # Base scoring with constraint weights
    scores = {}
    total_weight = sum(quality_weights.values()) if quality_weights else 1.0
    
    for constraint in constraints:
        if not constraint.get('enabled', True):
            continue
            
        constraint_id = constraint['id']
        weight = quality_weights.get(constraint_id, 0.2)
        
        # Apply constraint-specific analysis
        if constraint_id == 'tag_relevance':
            # Simulate tag relevance analysis
            generic_tags = ['document', 'file', 'content', 'generic', 'misc', 'general', 'data']
            non_generic_ratio = 1 - (sum(1 for tag in tags if tag.lower() in generic_tags) / max(len(tags), 1))
            scores[constraint_id] = min(100, non_generic_ratio * 100)
            
        elif constraint_id == 'content_depth':
            # Content depth analysis
            word_count = len(content.split())
            if word_count >= 200:
                scores[constraint_id] = 95
            elif word_count >= 100:
                scores[constraint_id] = 80
            elif word_count >= 50:
                scores[constraint_id] = 65
            else:
                scores[constraint_id] = 40
                
        elif constraint_id == 'no_generic_tags':
            # Generic tags penalty
            generic_tags = ['document', 'file', 'content', 'generic', 'misc', 'general', 'data', 'information', 'test']
            generic_count = sum(1 for tag in tags if tag.lower() in generic_tags)
            scores[constraint_id] = max(0, 100 - (generic_count * 25))
            
        elif constraint_id == 'technical_accuracy':
            # Technical content indicators
            technical_terms = ['api', 'algorithm', 'database', 'framework', 'architecture', 'deployment', 'monitoring']
            has_technical = any(term in content.lower() for term in technical_terms)
            scores[constraint_id] = 85 if has_technical else 70
            
        elif constraint_id == 'business_value':
            # Business value indicators
            value_words = ['best practice', 'guide', 'tutorial', 'solution', 'strategy', 'process', 'methodology']
            has_value = any(word in content.lower() for word in value_words)
            scores[constraint_id] = 90 if has_value else 60
        else:
            # Default scoring for unknown constraints
            scores[constraint_id] = 75
    
    # Calculate weighted average
    if scores and total_weight > 0:
        weighted_score = sum(score * quality_weights.get(cid, 0.2) for cid, score in scores.items())
        final_score = min(100, max(0, weighted_score / total_weight))
    else:
        # Fallback to simple scoring
        final_score = min(100, 70 + (content_length / 50) + (tag_count * 3))
    
    # Generate constraint-based reasoning
    reasoning_parts = []
    for constraint in constraints:
        if not constraint.get('enabled', True):
            continue
        constraint_id = constraint['id']
        if constraint_id in scores:
            score = scores[constraint_id]
            weight = quality_weights.get(constraint_id, 0.2)
            reasoning_parts.append(f"{constraint['name']}: {score:.1f}% (weight: {weight:.1%})")
    
    reasoning = f"Analysis based on {len(constraints)} active constraints: " + "; ".join(reasoning_parts)
    
    # Generate suggestions based on constraints
    suggestions = []
    for constraint in constraints:
        if not constraint.get('enabled', True):
            continue
        constraint_id = constraint['id']
        score = scores.get(constraint_id, 70)
        
        if score < 70:
            if constraint_id == 'tag_relevance':
                suggestions.append("Improve tag relevance by using more specific, content-related tags")
            elif constraint_id == 'content_depth':
                suggestions.append("Expand content with more detailed information and examples")
            elif constraint_id == 'no_generic_tags':
                suggestions.append("Replace generic tags with more specific, descriptive terms")
            elif constraint_id == 'technical_accuracy':
                suggestions.append("Add more technical details and verify accuracy of technical claims")
            elif constraint_id == 'business_value':
                suggestions.append("Include more actionable insights and practical value for users")
    
    if not suggestions:
        suggestions = ["Content meets quality standards - consider minor improvements in specificity"]
    
    return {
        "quality_score": round(final_score, 1),
        "reasoning": reasoning,
        "suggested_improvements": suggestions,
        "constraint_scores": scores,
        "confidence": 0.85,
        "custom_prompt_used": True,
        "constraints_applied": len([c for c in constraints if c.get('enabled', True)])
    }

def apply_chain_of_thought_analysis(content: str, tags: List[str], prompt: str, constraints: List[Dict], quality_weights: Dict[str, float], context: Optional[Dict] = None) -> Dict:
    """
    Enhanced LLM analysis using OpenAI's chain-of-thought reasoning
    """
    global llm_processed_count
    llm_processed_count += 1
    
    # Simulate enhanced analysis time for chain-of-thought
    time.sleep(0.4)
    
    # Step-by-step reasoning based on OpenAI's framework
    reasoning_steps = []
    step_scores = {}
    
    # Step 1: Content Quality Assessment
    word_count = len(content.split())
    if word_count >= 200:
        content_quality = 90
        reasoning_steps.append("Step 1 - Content Quality: Excellent depth with 200+ words, comprehensive coverage")
    elif word_count >= 100:
        content_quality = 75
        reasoning_steps.append("Step 1 - Content Quality: Good depth with 100+ words, adequate detail")
    elif word_count >= 50:
        content_quality = 60
        reasoning_steps.append("Step 1 - Content Quality: Minimal depth with 50+ words, needs expansion")
    else:
        content_quality = 30
        reasoning_steps.append("Step 1 - Content Quality: Insufficient depth, very short content")
    
    step_scores['content_quality'] = content_quality
    
    # Step 2: Tag Relevance Analysis
    content_words = set(content.lower().split())
    tag_words = set(' '.join(tags).lower().split())
    overlap = len(content_words & tag_words)
    relevance_ratio = overlap / max(len(tag_words), 1)
    
    if relevance_ratio > 0.7:
        tag_relevance = 95
        reasoning_steps.append(f"Step 2 - Tag Relevance: Excellent match ({overlap} overlapping terms, {relevance_ratio:.1%} relevance)")
    elif relevance_ratio > 0.4:
        tag_relevance = 80
        reasoning_steps.append(f"Step 2 - Tag Relevance: Good match ({overlap} overlapping terms, {relevance_ratio:.1%} relevance)")
    elif relevance_ratio > 0.2:
        tag_relevance = 60
        reasoning_steps.append(f"Step 2 - Tag Relevance: Moderate match ({overlap} overlapping terms, {relevance_ratio:.1%} relevance)")
    else:
        tag_relevance = 40
        reasoning_steps.append(f"Step 2 - Tag Relevance: Poor match ({overlap} overlapping terms, {relevance_ratio:.1%} relevance)")
    
    step_scores['tag_relevance'] = tag_relevance
    
    # Step 3: Information Completeness
    completeness_indicators = ['example', 'detail', 'step', 'process', 'method', 'guide', 'tutorial']
    found_indicators = [ind for ind in completeness_indicators if ind in content.lower()]
    completeness_score = min(100, 50 + len(found_indicators) * 10)
    
    if completeness_score >= 90:
        reasoning_steps.append(f"Step 3 - Completeness: Excellent structure with clear examples and detailed guidance")
    elif completeness_score >= 70:
        reasoning_steps.append(f"Step 3 - Completeness: Good structure with some examples and guidance")
    else:
        reasoning_steps.append(f"Step 3 - Completeness: Basic structure, lacks detailed examples or guidance")
    
    step_scores['completeness'] = completeness_score
    
    # Step 4: Technical Accuracy Assessment
    technical_terms = ['api', 'algorithm', 'database', 'framework', 'architecture', 'deployment', 'monitoring', 'security']
    tech_indicators = [term for term in technical_terms if term in content.lower()]
    
    if tech_indicators:
        technical_accuracy = 85 + min(15, len(tech_indicators) * 3)
        reasoning_steps.append(f"Step 4 - Technical Accuracy: Technical content with {len(tech_indicators)} domain terms detected")
    else:
        technical_accuracy = 70
        reasoning_steps.append("Step 4 - Technical Accuracy: Non-technical content, general accuracy assumed")
    
    step_scores['technical_accuracy'] = technical_accuracy
    
    # Step 5: Business Value Assessment
    value_indicators = ['best practice', 'solution', 'strategy', 'improvement', 'optimization', 'efficiency', 'ROI']
    business_terms = [term for term in value_indicators if term in content.lower()]
    
    if business_terms:
        business_value = 80 + min(20, len(business_terms) * 5)
        reasoning_steps.append(f"Step 5 - Business Value: High value content with {len(business_terms)} business-relevant terms")
    else:
        business_value = 60
        reasoning_steps.append("Step 5 - Business Value: Moderate value, could include more actionable insights")
    
    step_scores['business_value'] = business_value
    
    # Apply constraint weights from OpenAI framework
    final_score = 0
    total_weight = 0
    
    for constraint in constraints:
        if not constraint.get('enabled', True):
            continue
        
        constraint_id = constraint['id']
        weight = quality_weights.get(constraint_id, 0.2)
        
        # Map constraint IDs to our step scores
        if constraint_id in ['content_depth', 'content_quality']:
            score = step_scores['content_quality']
        elif constraint_id in ['tag_relevance', 'no_generic_tags']:
            score = step_scores['tag_relevance']
        elif constraint_id == 'technical_accuracy':
            score = step_scores['technical_accuracy']
        elif constraint_id == 'business_value':
            score = step_scores['business_value']
        else:
            score = step_scores['completeness']  # Default
        
        final_score += score * weight
        total_weight += weight
    
    if total_weight > 0:
        final_score = final_score / total_weight
    else:
        # Fallback weighted average
        final_score = (
            step_scores['content_quality'] * 0.3 +
            step_scores['tag_relevance'] * 0.25 +
            step_scores['completeness'] * 0.2 +
            step_scores['technical_accuracy'] * 0.15 +
            step_scores['business_value'] * 0.1
        )
    
    # Generate improvement suggestions based on lowest scores
    suggestions = []
    for step, score in step_scores.items():
        if score < 70:
            if step == 'content_quality':
                suggestions.append("Expand content with more detailed information and examples")
            elif step == 'tag_relevance':
                suggestions.append("Use more specific tags that directly relate to content topics")
            elif step == 'completeness':
                suggestions.append("Add structured examples, step-by-step processes, or detailed guidance")
            elif step == 'technical_accuracy':
                suggestions.append("Include more technical details and verify accuracy of technical claims")
            elif step == 'business_value':
                suggestions.append("Add actionable insights and practical business value")
    
    if not suggestions:
        suggestions = ["Content meets quality standards - consider minor improvements in specificity"]
    
    # Combine all reasoning steps
    full_reasoning = "Chain-of-thought analysis:\n" + "\n".join(reasoning_steps)
    
    return {
        "quality_score": round(final_score, 1),
        "reasoning": full_reasoning,
        "suggested_improvements": suggestions,
        "step_scores": step_scores,
        "confidence": 0.90,
        "methodology": "chain_of_thought",
        "constraints_applied": len([c for c in constraints if c.get('enabled', True)])
    }

def apply_self_consistency_analysis(content: str, tags: List[str], prompt: str, constraints: List[Dict], quality_weights: Dict[str, float], context: Optional[Dict] = None, iterations: int = 3) -> Dict:
    """
    Apply OpenAI's self-consistency technique - generate multiple analyses and pick most consistent
    """
    global llm_processed_count
    
    analyses = []
    
    # Generate multiple independent analyses
    for i in range(iterations):
        llm_processed_count += 1
        
        # Add slight variation to avoid identical results
        varied_analysis = apply_chain_of_thought_analysis(content, tags, prompt, constraints, quality_weights, context)
        
        # Add small random variation to simulate different "reasoning paths"
        import random
        variation = random.uniform(-2, 2)
        varied_analysis['quality_score'] = max(0, min(100, varied_analysis['quality_score'] + variation))
        
        analyses.append(varied_analysis)
        time.sleep(0.1)  # Small delay between analyses
    
    # Calculate consensus
    scores = [a['quality_score'] for a in analyses]
    suggestions_lists = [a['suggested_improvements'] for a in analyses]
    
    # Use median for final score (more robust than mean)
    final_score = sorted(scores)[len(scores) // 2]
    
    # Find common suggestions across analyses
    all_suggestions = []
    for suggestions in suggestions_lists:
        all_suggestions.extend(suggestions)
    
    # Count suggestion frequency and keep most common ones
    from collections import Counter
    suggestion_counts = Counter(all_suggestions)
    consensus_suggestions = [s for s, count in suggestion_counts.items() if count >= iterations // 2]
    
    if not consensus_suggestions:
        consensus_suggestions = analyses[0]['suggested_improvements']  # Fallback
    
    # Calculate confidence based on score consistency
    score_std = (sum((s - final_score) ** 2 for s in scores) / len(scores)) ** 0.5
    confidence = max(0.5, 1.0 - (score_std / 50))  # Higher consistency = higher confidence
    
    return {
        "quality_score": round(final_score, 1),
        "reasoning": f"Self-consistency analysis across {iterations} iterations. Score range: {min(scores):.1f}-{max(scores):.1f}, consensus: {final_score:.1f}",
        "suggested_improvements": consensus_suggestions,
        "confidence": round(confidence, 2),
        "methodology": "self_consistency",
        "individual_scores": scores,
        "score_variance": round(score_std, 2),
        "constraints_applied": len([c for c in constraints if c.get('enabled', True)])
    }

# Add evaluation metrics tracking
evaluation_metrics = {
    'total_analyses': 0,
    'methodology_performance': defaultdict(list),
    'accuracy_trends': [],
    'user_feedback': []
}

def track_analysis_performance(methodology: str, quality_score: float, confidence: float, user_feedback: Optional[Dict] = None):
    """Track performance metrics for continuous improvement"""
    global evaluation_metrics
    
    evaluation_metrics['total_analyses'] += 1
    evaluation_metrics['methodology_performance'][methodology].append({
        'score': quality_score,
        'confidence': confidence,
        'timestamp': datetime.now(UTC).isoformat()
    })
    
    if user_feedback:
        evaluation_metrics['user_feedback'].append({
            'methodology': methodology,
            'feedback': user_feedback,
            'timestamp': datetime.now(UTC).isoformat()
        })

def analyze_redteam_scenario(scenario_id: str, content: str, tags: List[str], objectives: List[str], expected_issues: Optional[List[str]] = None) -> Dict:
    """
    Analyze content using red-team testing scenarios
    """
    results = {
        "scenario_id": scenario_id,
        "detected_issues": [],
        "severity_scores": {},
        "attack_success": False,
        "recommendations": []
    }
    
    # Red team specific analysis
    if scenario_id == 'generic_tags_attack':
        generic_count = sum(1 for tag in tags if tag.lower() in ['document', 'generic', 'content', 'misc', 'general', 'data', 'information'])
        results["detected_issues"].append(f"Generic tags detected: {generic_count}/{len(tags)}")
        results["severity_scores"]["generic_tags"] = min(100, generic_count * 20)
        if generic_count >= 3:
            results["attack_success"] = True
            
    elif scenario_id == 'tag_content_mismatch':
        # Simulate content-tag analysis
        content_words = set(content.lower().split())
        tag_words = set(' '.join(tags).lower().split())
        overlap = len(content_words & tag_words)
        mismatch_score = max(0, 100 - (overlap * 10))
        results["detected_issues"].append(f"Tag-content overlap: {overlap} matching terms")
        results["severity_scores"]["content_mismatch"] = mismatch_score
        if mismatch_score > 70:
            results["attack_success"] = True
            
    elif scenario_id == 'minimal_content':
        word_count = len(content.split())
        results["detected_issues"].append(f"Content length: {word_count} words")
        results["severity_scores"]["content_length"] = max(0, 100 - word_count * 2)
        if word_count < 10:
            results["attack_success"] = True
            
    elif scenario_id == 'spam_content':
        spam_indicators = ['lorem ipsum', 'test test', 'document document', 'placeholder', 'sample']
        detected_spam = [indicator for indicator in spam_indicators if indicator in content.lower()]
        results["detected_issues"].extend([f"Spam pattern: {pattern}" for pattern in detected_spam])
        results["severity_scores"]["spam_detection"] = len(detected_spam) * 30
        if len(detected_spam) >= 2:
            results["attack_success"] = True
            
    elif scenario_id == 'over_tagging':
        tag_ratio = len(tags) / max(len(content.split()), 1)
        results["detected_issues"].append(f"Tag-to-word ratio: {tag_ratio:.2f}")
        results["severity_scores"]["over_tagging"] = min(100, tag_ratio * 50)
        if tag_ratio > 0.5:
            results["attack_success"] = True
            
    elif scenario_id == 'duplicate_content':
        words = content.split()
        unique_words = set(words)
        repetition_ratio = 1 - (len(unique_words) / max(len(words), 1))
        results["detected_issues"].append(f"Content repetition: {repetition_ratio:.1%}")
        results["severity_scores"]["duplicate_content"] = repetition_ratio * 100
        if repetition_ratio > 0.6:
            results["attack_success"] = True
    
    # Generate recommendations
    if results["attack_success"]:
        results["recommendations"] = [
            "System successfully detected quality issues",
            "Consider strengthening validation rules",
            "Implement additional content quality checks"
        ]
    else:
        results["recommendations"] = [
            "System resisted the attack scenario",
            "Quality controls are working effectively",
            "Continue monitoring for edge cases"
        ]
    
    # Compare with expected issues
    if expected_issues:
        detected_keywords = ' '.join(results["detected_issues"]).lower()
        matched_expectations = [issue for issue in expected_issues if any(word in detected_keywords for word in issue.lower().split())]
        results["expected_vs_detected"] = {
            "expected": expected_issues,
            "matched": matched_expectations,
            "accuracy": len(matched_expectations) / len(expected_issues) if expected_issues else 0
        }
    
    return results

@app.get("/health")
async def health_check():
    """System health check endpoint"""
    global start_time
    uptime = (datetime.now(UTC) - start_time).total_seconds()
    
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": uptime,
        "rules_engine_available": RULES_ENGINE_AVAILABLE,
        "llm_judge_enhanced": True,
        "version": "1.1.0-local",
        "features": ["custom_prompts", "quality_constraints", "redteam_testing"],
        "message": "IndexingQA enhanced local development server is running"
    })



@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    global processed_count, llm_processed_count, start_time
    uptime = (datetime.now(UTC) - start_time).total_seconds()
    
    stats = SystemStats(
        total_processed=processed_count,
        rules_engine_processed=processed_count if RULES_ENGINE_AVAILABLE else 0,
        llm_judge_processed=llm_processed_count,
        avg_processing_time_ms=18.5,  # Slightly higher for enhanced processing
        active_connectors=len([c for c in sample_connectors if c["status"] == "active"]),
        system_health="healthy",
        uptime_seconds=uptime
    )
    
    return JSONResponse({
        "total_processed": stats.total_processed,
        "rules_engine_processed": stats.rules_engine_processed,
        "llm_judge_processed": stats.llm_judge_processed,
        "avg_processing_time_ms": stats.avg_processing_time_ms,
        "active_connectors": stats.active_connectors,
        "system_health": stats.system_health,
        "uptime_seconds": stats.uptime_seconds
    })

@app.get("/metrics")
async def get_dashboard_metrics():
    """Get dashboard metrics for frontend using unified data source"""
    try:
        # Use unified data source for consistency with analytics
        unified_data = get_unified_metrics_data()
        
        return JSONResponse({
            "totalRecords": unified_data['total_records'],
            "todaysRecords": unified_data['todays_records'],
            "avgQualityScore": unified_data['avg_quality_score'],
            "qualityTrend": 5.2,  # Mock trend for now
            "issuesCount": unified_data['issues_count'],
            "criticalIssues": unified_data['critical_issues'],
            "activeSources": unified_data['active_sources'],
            "companiesCount": unified_data['companies_count'],
            "processingRate": 120,  # Mock processing rate
            "systemHealth": "healthy",
            "costMetrics": {
                "dailyCost": 12.50,
                "monthlyBudget": 500.00,
                "budgetUsed": 25.0
            }
        })
    except Exception as e:
        return JSONResponse({"error": str(e)})

@app.post("/ingest")
async def ingest_content(request: ContentIngestRequest):
    """Ingest content for quality analysis with enhanced LLM suggestions"""

    global processed_count, llm_processed_count
    
    start_time = time.time()
    trace_id = f"qa-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    # Track request start
    request_data = request.dict()
    
    try:
        # Validate input
        if len(request.content.strip()) < 10:
            error_response = {
                "success": False,
                "error": "Content must be at least 10 characters",
                "trace_id": trace_id
            }
            
            # Store failed request
            store_request_log(
                trace_id=trace_id,
                endpoint="/ingest",
                method="POST",
                request_data=request_data,
                response_status=422,
                response_data=error_response,
                processing_time_ms=(time.time() - start_time) * 1000,
                error_message="Content too short (minimum 10 characters)",
                source_connector=request.source_connector
            )
            
            # Log validation error but don't store in dead letters
            print(f"Validation error for {trace_id}: Content too short")
            
            raise HTTPException(status_code=422, detail="Content must be at least 10 characters")
        
        # STEP 2: Schema validation (validate record ID format, etc.)
        if SCHEMA_VALIDATOR_AVAILABLE and schema_validator:
            try:
                # Map field names: content -> document_text for schema validator
                schema_data = request_data.copy()
                schema_data['document_text'] = schema_data.pop('content', '')
                schema_data['file_id'] = schema_data.get('record_id', 'unknown')  # Use record_id as file_id if missing
                
                # Convert request to dict for schema validation
                schema_validation_result = schema_validator.validate_chunk(schema_data)
                
                if not schema_validation_result.is_valid:
                    # Format validation errors
                    error_details = []
                    for error in schema_validation_result.errors:
                        field = error.get('field', 'unknown')
                        message = error.get('message', 'validation error')
                        error_details.append(f"{field}: {message}")
                    
                    error_message = f"Schema validation failed: {'; '.join(error_details)}"
                    
                    # Store in dead letters
                    store_dead_letter(
                        trace_id=trace_id,
                        raw_input=json.dumps(request_data),
                        error_message=error_message,
                        error_type="SCHEMA_VALIDATION_ERROR",
                        source_connector=request.source_connector
                    )
                    
                    print(f"[SCHEMA VALIDATION] Failed for {trace_id}: {error_message}")
                    
                    # Return error response
                    error_response = {
                        "success": False,
                        "error": error_message,
                        "trace_id": trace_id,
                        "validation_errors": schema_validation_result.errors
                    }
                    
                    store_request_log(
                        trace_id=trace_id,
                        endpoint="/ingest",
                        method="POST",
                        request_data=request_data,
                        response_status=422,
                        response_data=error_response,
                        processing_time_ms=(time.time() - start_time) * 1000,
                        error_message=error_message,
                        source_connector=request.source_connector
                    )
                    
                    raise HTTPException(status_code=422, detail=error_message)
                
                print(f"[SCHEMA VALIDATION] Passed for {trace_id}")
                
            except HTTPException:
                # Re-raise HTTPException
                raise
            except Exception as e:
                print(f"[SCHEMA VALIDATION] Error during validation: {e}")
                # Continue processing without schema validation if there's an error
        
        # Extract tags if not provided
        if not request.tags:
            request.tags = extract_tags_from_sharepoint_content(request.content)
        
        # STEP 3: Run rules engine checks
        quality_checks = []
        rules_engine_score = 0
        if RULES_ENGINE_AVAILABLE and rules_engine:
            try:
                # Handle source connector validation more gracefully
                try:
                    source_connector_enum = SourceConnector(request.source_connector)
                except ValueError:
                    # If source connector is not in enum, create a custom one
                    source_connector_enum = SourceConnector.CUSTOM
                    # Log invalid source connector warning
                    print(f"Warning for {trace_id}: Invalid source connector '{request.source_connector}', using CUSTOM")
                
                chunk_request = ChunkIngestRequest(
                    record_id=request.record_id,
                    document_text=request.content,
                    tags=request.tags,
                    source_connector=source_connector_enum,
                    file_id=request.record_id,
                    created_at=datetime.now(UTC)
                )
                
                quality_checks = rules_engine.check_chunk(chunk_request)
                # Calculate average confidence using ONLY rules engine checks (exclude LLM-related checks)
                rules_only_checks = [check for check in quality_checks if check.check_name not in ['llm_semantic_validation', 'llm_invocation_decision']]
                rules_engine_score = sum(check.confidence_score for check in rules_only_checks) / len(rules_only_checks) if rules_only_checks else 0
                processed_count += 1
                
                # Store individual quality checks with enhanced structure
                for check in quality_checks:
                    # Enhanced quality check structure
                    enhanced_check = {
                        "type": check.check_name,
                        "severity": "high" if check.confidence_score < 0.3 else "medium" if check.confidence_score < 0.7 else "low",
                        "description": check.failure_reason or f"{check.check_name} check completed",
                        "suggestion": _generate_suggestion(check.check_name, check.failure_reason, check.check_metadata),
                        "autoFixable": _is_auto_fixable(check.check_name),
                        "category": _get_check_category(check.check_name),
                        "confidence": check.confidence_score,
                        "status": check.status.value,
                        "processing_time_ms": check.check_metadata.get('processing_time_ms', 0) if check.check_metadata else 0
                    }
                    
                    # Add additional metadata if available
                    if check.check_metadata:
                        enhanced_check.update(check.check_metadata)
                    
                    store_quality_check(
                        record_id=request.record_id,
                        check_name=check.check_name,
                        status=check.status.value,
                        confidence_score=check.confidence_score,
                        failure_reason=check.failure_reason,
                        check_metadata=enhanced_check
                    )
                
            except Exception as e:
                print(f"Rules engine error: {e}")
                # Log rules engine error but don't store in dead letters
                
                # Fallback to basic checks
                quality_checks = [
                    QualityCheckResult(
                        check_name="basic_content_check",
                        status=FlagStatus.PASS,
                        confidence_score=0.7,
                        check_metadata={"content_length": len(request.content)}
                    )
                ]
                rules_engine_score = 0.7
                
                # Store fallback check
                store_quality_check(
                    record_id=request.record_id,
                    check_name="basic_content_check",
                    status="pass",
                    confidence_score=0.7,
                    check_metadata={"content_length": len(request.content)}
                )
        else:
            # Mock rules engine response
            quality_checks = [
                QualityCheckResult(
                    check_name="mock_content_check",
                    status=FlagStatus.PASS,
                    confidence_score=0.8,
                    check_metadata={"content_length": len(request.content)}
                )
            ]
            rules_engine_score = 0.8
            
            # Store mock check
            store_quality_check(
                record_id=request.record_id,
                check_name="mock_content_check",
                status="pass",
                confidence_score=0.8,
                check_metadata={"content_length": len(request.content)}
            )
        
        # Run LLM judge analysis ONLY if rules engine meets threshold based on LLM invocation mode
        llm_suggestions = []
        llm_reasoning = ""
        llm_score = 0
        should_run_llm = False
        llm_decision_reason = ""
        
        try:
            # Get LLM invocation settings
            global llm_invocation_settings
            
            # Evaluate LLM invocation decision based on rules engine results
            llm_decision = evaluate_llm_invocation_decision(quality_checks, llm_invocation_settings)
            should_run_llm = llm_decision.should_invoke_llm  # Fixed: was should_invoke
            llm_decision_reason = llm_decision.reason
            
            # DEBUG: Log detailed decision info
            print(f"\n" + "="*80)
            print(f"🔍 LLM INVOCATION DEBUG - CRITICAL BUG INVESTIGATION")
            print(f"="*80)
            print(f"   Mode: {llm_invocation_settings.mode}")
            print(f"   Total rules: {len(quality_checks)}")
            print(f"   Passed rules: {sum(1 for r in quality_checks if r.status == FlagStatus.PASS)}")
            print(f"   Failed rules: {sum(1 for r in quality_checks if r.status == FlagStatus.FAIL)}")
            print(f"   Decision: {should_run_llm}")
            print(f"   Reason: {llm_decision_reason}")
            print(f"   Rules summary: {llm_decision.rules_summary}")
            
            # Print individual rule statuses
            print(f"\n   INDIVIDUAL RULE STATUS:")
            for i, rule in enumerate(quality_checks):
                print(f"     {i+1}. {rule.check_name}: {rule.status.value} (confidence: {rule.confidence_score})")
            
            print(f"="*80)
            print(f"🔍 END DEBUG")
            print(f"="*80 + "\n")
            
            # Store LLM invocation decision
            store_quality_check(
                record_id=request.record_id,
                check_name="llm_invocation_decision",
                status="triggered" if should_run_llm else "skipped",
                confidence_score=1.0,
                failure_reason=llm_decision_reason,
                check_metadata={"llm_decision_reason": llm_decision_reason, "should_invoke": should_run_llm}
            )

            if should_run_llm:
                # Use actual LLM judge for semantic validation
                llm_result = await llm_judge.check_chunk(request.content, request.tags)
                
                llm_score = llm_result.confidence_score
                llm_reasoning = llm_result.failure_reason if llm_result.failure_reason else "LLM semantic validation completed"
                
                # Calculate preliminary overall score for suggestions generation
                preliminary_overall_score = (rules_engine_score * 0.6 + llm_score * 0.4) * 100
                
                # Generate dynamic suggestions based on quality check results
                try:
                    # Convert quality_checks to dict format for the LLM
                    quality_checks_dict = []
                    for check in quality_checks:
                        check_dict = {
                            'check_name': check.check_name,
                            'status': check.status.value,
                            'confidence_score': check.confidence_score,
                            'failure_reason': check.failure_reason,
                            'severity': 'high' if check.confidence_score < 0.3 else 'medium' if check.confidence_score < 0.7 else 'low'
                        }
                        if check.check_metadata:
                            check_dict.update(check.check_metadata)
                        quality_checks_dict.append(check_dict)
                    
                    # Get improvement suggestions from LLM based on quality checks
                    suggestions_result = await llm_judge.generate_improvement_suggestions(
                        content=request.content,
                        tags=request.tags,
                        quality_checks=quality_checks_dict,
                        overall_score=preliminary_overall_score
                    )
                    
                    llm_suggestions = suggestions_result.get('suggestions', [
                        "Review and address quality check failures",
                        "Improve content structure and clarity"
                    ])
                    
                    # Add reasoning to metadata
                    llm_reasoning = llm_reasoning + f" | Improvement suggestions: {suggestions_result.get('reasoning', '')}"
                    
                except Exception as e:
                    print(f"Error generating LLM suggestions: {e}")
                    # Fallback to basic suggestions based on LLM result
                    if llm_result.status == FlagStatus.FAIL:
                        llm_suggestions = [
                            "Content quality needs improvement",
                            "Tags may not accurately reflect content",
                            "Consider adding more specific and relevant tags"
                        ]
                    elif llm_result.status == FlagStatus.PENDING_REVIEW:
                        llm_suggestions = [
                            "Content and tags have moderate alignment",
                            "Consider adding more specific tags",
                            "Content could benefit from additional context"
                        ]
                    else:
                        llm_suggestions = [
                            "Content and tags are well-aligned",
                            "Quality standards met"
                        ]
            
                llm_processed_count += 1
                
                # Add LLM judge result as a quality check
                llm_check = {
                "type": "llm_semantic_validation",
                "severity": "high" if llm_score < 0.3 else "medium" if llm_score < 0.7 else "low",
                "description": llm_reasoning or "LLM semantic validation completed",
                "suggestion": _generate_suggestion("llm_semantic_validation", llm_reasoning, {"llm_score": llm_score}),
                "autoFixable": _is_auto_fixable("llm_semantic_validation"),
                "category": _get_check_category("llm_semantic_validation"),
                "confidence": llm_score,
                "status": llm_result.status.value,
                "llm_score": llm_score,
                "llm_reasoning": llm_reasoning
            }
            
                # Store LLM check
                store_quality_check(
                record_id=request.record_id,
                check_name="llm_semantic_validation",
                status=llm_result.status.value,
                confidence_score=llm_score,
                failure_reason=llm_reasoning,
                check_metadata=llm_check
            )
            
                # Add LLM check to quality_checks list
                quality_checks.append(QualityCheckResult(
                check_name="llm_semantic_validation",
                status=llm_result.status,
                confidence_score=llm_score,
                failure_reason=llm_reasoning,
                check_metadata=llm_check
            ))
            else:
                # LLM was not invoked - generate suggestions based on rules engine results
                print(f"LLM not invoked - generating suggestions based on rules engine results")
                
                # Analyze failed checks to provide targeted suggestions
                failed_checks = [check for check in quality_checks if check.status == FlagStatus.FAIL]
                warning_checks = [check for check in quality_checks if check.status == FlagStatus.WARNING]
                
                if failed_checks:
                    llm_suggestions = []
                    
                    # Categorize failures for better suggestions
                    tag_issues = any('tag' in c.check_name.lower() for c in failed_checks)
                    content_issues = any(any(word in c.check_name.lower() for word in ['text', 'content', 'quality']) for c in failed_checks)
                    spam_issues = any(any(word in c.check_name.lower() for word in ['spam', 'generic', 'stopword']) for c in failed_checks)
                    
                    if tag_issues:
                        llm_suggestions.append("Add more specific and relevant tags to improve searchability")
                    if content_issues:
                        llm_suggestions.append("Expand content with more detailed and specific information")
                    if spam_issues:
                        llm_suggestions.append("Remove generic or promotional content, focus on valuable information")
                    
                    # Add specific suggestions based on top failures
                    for check in failed_checks[:2]:
                        if check.failure_reason:
                            llm_suggestions.append(f"Fix: {check.failure_reason}")
                    
                    # Limit suggestions
                    llm_suggestions = llm_suggestions[:5]
                    
                elif warning_checks:
                    llm_suggestions = [
                        "Content meets basic standards but has room for improvement",
                        f"Review {len(warning_checks)} warnings for optimization opportunities",
                        "Consider enhancing content structure and clarity"
                    ]
                else:
                    llm_suggestions = [
                        "Content meets all quality standards",
                        "Good tag coverage and content structure",
                        "Continue maintaining current quality level"
                    ]
                
                llm_reasoning = f"LLM analysis skipped - {llm_decision_reason}"

        
        except Exception as e:
            print(f"LLM judge error: {e}")
            # Store LLM error in dead letters
            store_dead_letter(
                trace_id=trace_id,
                raw_input=json.dumps(request_data),
                error_message=f"LLM judge error: {str(e)}",
                error_type="LLM_JUDGE_ERROR",
                source_connector=request.source_connector
            )
            
            llm_score = 0.7
            llm_reasoning = "LLM judge unavailable - using fallback scoring"
            llm_suggestions = ["Consider adding more context and specific details"]
        
        # Calculate unified quality score using consistent formula
        if llm_score is not None and llm_score != "Not Triggered" and llm_score > 0:
            # LLM was triggered - use weighted combination
            overall_score = (rules_engine_score * 0.6 + llm_score * 0.4) * 100
        else:
            # LLM was not triggered - use only rules engine score
            overall_score = rules_engine_score * 100
        
        # Get approval threshold from dynamic threshold system
        approval_threshold = get_threshold_value("approval_quality_score_threshold")
        if approval_threshold is None:
            # Fallback to settings
            settings = get_settings()
            approval_threshold = float(settings.approval_quality_score_threshold) if settings else 50.0
        
        # Determine status using configurable threshold
        if overall_score >= approval_threshold:
            status = "approved"
        else:
            status = "flagged"
            

        
        # Extract issues from failed quality checks
        issues = []
        for check in quality_checks:
            if check.status == FlagStatus.FAIL:
                issues.append({
                    "id": f"{trace_id}-{check.check_name}",
                    "type": check.check_name.replace("_", " "),
                    "severity": "high" if check.confidence_score < 0.3 else "medium" if check.confidence_score < 0.7 else "low",
                    "description": check.failure_reason or f"{check.check_name} check failed",
                    "suggestion": _generate_suggestion(check.check_name, check.failure_reason, check.check_metadata),
                    "autoFixable": _is_auto_fixable(check.check_name),
                    "category": _get_check_category(check.check_name),
                    "confidence": check.confidence_score
                })
        
        # Create record data
        record_data = {
            "id": request.record_id,
            "trace_id": trace_id,
            "record_id": request.record_id,
            "title": request.content[:100] + "..." if len(request.content) > 100 else request.content,
            "content": request.content,
            "tags": request.tags,
            "source_connector": request.source_connector,
            "company": request.content_metadata.get("company", "Unknown Company") if request.content_metadata else "Unknown Company",
            "quality_score": round(overall_score, 1),
            "quality_level": "high" if overall_score >= 90 else "medium" if overall_score >= 70 else "low",
            "quality_checks": [check.dict() for check in quality_checks],
            "content_metadata": request.content_metadata or {},
            "created_at": datetime.now(UTC).isoformat(),
            "processing_time_ms": (time.time() - start_time) * 1000,
            "llm_suggestions": llm_suggestions,
            "llm_reasoning": llm_reasoning,
            "status": status,
            "manual_review_status": "pending",  # Add manual review status
            "issues": issues,
            "llm_confidence": llm_score,
            "rules_engine_confidence": rules_engine_score,
            "quality_score_formula": "quality_score = (rules_engine_confidence * 0.6 + llm_confidence * 0.4) * 100"
        }
        
        # Create ingestion audit entry
        ingestion_audit_entry = {
            "action": "ingestion",
            "user_id": "system",
            "reason": f"Record ingested via {request.source_connector}",
            "ingestion_details": {
                "trace_id": trace_id,
                "source_connector": request.source_connector,
                "quality_score": round(overall_score, 1),
                "status": status,
                "tags_count": len(request.tags),
                "content_length": len(request.content),
                "processing_time_ms": (time.time() - start_time) * 1000
            },
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        # Add audit entry to record data
        record_data["manual_review_status"] = json.dumps([ingestion_audit_entry])
        
        # Store record
        store_record(record_data)
        
        # Send email alerts if record is flagged or under review
        if overall_score < 70:  # Flagged records
            send_alert_email(record_data, "flagged")
        elif overall_score < 85:  # Under review records
            send_alert_email(record_data, "under_review")
        
        # Track request completion
        processing_time = (time.time() - start_time) * 1000
        store_request_log(
            trace_id=trace_id,
            endpoint="/ingest",
            method="POST",
            request_data=request_data,
            response_status=200,
            response_data={"success": True, "trace_id": trace_id},
            processing_time_ms=processing_time,
            source_connector=request.source_connector
        )
        
        return {
            "success": True,
            "trace_id": trace_id,
            "record_id": request.record_id,
            "quality_score": round(overall_score, 1),
            "status": status,
            "llm_suggestions": llm_suggestions,
            "llm_reasoning": llm_reasoning,
            "issues": issues,
            "processing_time_ms": processing_time,
            "llm_confidence": llm_score,
            "rules_engine_confidence": rules_engine_score,
            "quality_score_formula": "quality_score = (rules_engine_confidence * 0.6 + llm_confidence * 0.4) * 100"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_response = {
            "success": False,
            "error": f"Processing failed: {str(e)}",
            "trace_id": trace_id
        }
        
        # Store failed request
        store_request_log(
            trace_id=trace_id,
            endpoint="/ingest",
            method="POST",
            request_data=request_data,
            response_status=500,
            response_data=error_response,
            processing_time_ms=(time.time() - start_time) * 1000,
            error_message=str(e),
            source_connector=request.source_connector
        )
        
        # Store in dead letters
        store_dead_letter(
            trace_id=trace_id,
            raw_input=json.dumps(request_data),
            error_message=str(e),
            error_type="PROCESSING_ERROR",
            source_connector=request.source_connector
        )
        
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

# Initialize unified bulk processor with ingest function after it's defined
if UNIFIED_BULK_AVAILABLE:
    # Create a wrapper function that handles dict to ContentIngestRequest conversion
    async def ingest_content_wrapper(request_data):
        if isinstance(request_data, dict):
            request = ContentIngestRequest(**request_data)
        else:
            request = request_data
        return await ingest_content(request)
    
    bulk_processor.set_ingest_function(ingest_content_wrapper)
    print("✅ Unified bulk processor initialized with ingest function")

@app.post("/rules/check")
async def check_rules_only(request: RulesCheckRequest):
    """
    Test content against rules engine only (fast checks)
    """
    global processed_count
    processed_count += 1
    
    start_time_ms = time.time() * 1000
    
    if RULES_ENGINE_AVAILABLE and rules_engine:
        from app.models.models import SourceConnector
        
        connector_mapping = {
            "sharepoint": SourceConnector.SHAREPOINT,
            "confluence": SourceConnector.CONFLUENCE,
        }
        
        # Add additional connectors if they exist
        if hasattr(SourceConnector, 'GDRIVE'):
            connector_mapping["googledrive"] = SourceConnector.GDRIVE

        
        chunk_request = ChunkIngestRequest(
            record_id=f"rules_test_{int(time.time())}",
            document_text=request.content,
            tags=request.tags,
            source_connector=connector_mapping.get(request.source_connector, SourceConnector.SHAREPOINT),
            file_id=f"test_file_{int(time.time())}"
        )
        
        results = rules_engine.check_chunk(chunk_request)
        
        rules_results = []
        for result in results:
                    rules_results.append({
            "check_name": result.check_name,
            "status": result.status.value,
            "confidence_score": result.confidence_score,
            "failure_reason": result.failure_reason,
            "metadata": result.check_metadata
        })
        
        # Get performance metrics
        performance_metrics = rules_engine.get_performance_metrics()
        
    else:
        # Mock results
        rules_results = [
            {
                "check_name": "empty_tags",
                "status": "PASS" if request.tags else "FAIL",
                "confidence_score": 1.0,
                "failure_reason": None if request.tags else "No tags provided",
                "metadata": {"tag_count": len(request.tags)}
            }
        ]
        performance_metrics = {"avg_processing_time_ms": 8.5}
    
    processing_time = (time.time() * 1000) - start_time_ms
    
    failed_checks = [r for r in rules_results if r["status"] == "fail"]
    passed_checks = [r for r in rules_results if r["status"] == "pass"]
    
    return JSONResponse({
        "success": True,
        "rules_engine_results": rules_results,
        "summary": {
            "total_checks": len(rules_results),
            "passed": len(passed_checks),
            "failed": len(failed_checks),
            "overall_status": "PASS" if len(failed_checks) == 0 else "FAIL"
        },
        "performance_metrics": performance_metrics,
        "processing_time_ms": processing_time
    })

@app.post("/llm/analyze")
async def llm_analysis(request: LLMAnalysisRequest):
    """
    Basic LLM judge analysis endpoint
    """
    start_time_ms = time.time() * 1000
    
    # Simulate LLM processing time
    time.sleep(0.5)  # Simulate slower LLM processing
    
    # Simple scoring algorithm for demo
    content_length = len(request.content)
    tag_count = len(request.tags)
    
    base_score = 70
    if content_length > 100:
        base_score += 10
    if content_length > 300:
        base_score += 10
    if tag_count >= 3:
        base_score += 10
    if tag_count >= 5:
        base_score += 5
    
    # Check for quality indicators
    quality_words = ['best practice', 'comprehensive', 'detailed', 'guidelines', 'framework']
    if any(word in request.content.lower() for word in quality_words):
        base_score += 10
    
    quality_score = min(100, base_score)
    
    suggestions = []
    if content_length < 100:
        suggestions.append("Expand content with more detailed information")
    if tag_count < 3:
        suggestions.append("Add more specific and relevant tags")
    if not any(word in request.content.lower() for word in quality_words):
        suggestions.append("Include more structured information or best practices")
    
    processing_time = (time.time() * 1000) - start_time_ms
    
    return JSONResponse({
        "success": True,
        "quality_score": quality_score,
        "reasoning": f"Content analysis based on {content_length} characters and {tag_count} tags. " +
                    f"Score calculated using content depth, tag relevance, and quality indicators.",
        "suggested_improvements": suggestions,
        "confidence": 0.85,
        "processing_time_ms": processing_time,
        "model_used": "basic-llm-judge-v1"
    })



@app.post("/llm/redteam")
async def redteam_analysis(request: RedTeamRequest):
    """
    Red team testing endpoint for adversarial quality testing
    """
    global redteam_results
    start_time_ms = time.time() * 1000
    
    try:
        # Perform red team analysis
        redteam_result = analyze_redteam_scenario(
            scenario_id=request.scenario_id,
            content=request.content,
            tags=request.tags,
            objectives=request.test_objectives,
            expected_issues=request.expected_issues
        )
        
        # Also run standard rules and LLM checks for comparison
        standard_llm = apply_custom_llm_analysis(
            content=request.content,
            tags=request.tags,
            prompt="Analyze this content for quality issues and potential problems.",
            constraints=[c for c in default_constraints.values()],
            quality_weights={cid: c['weight'] for cid, c in default_constraints.items()}
        )
        
        processing_time = (time.time() * 1000) - start_time_ms
        
        # Store results for analysis
        result_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "scenario_id": request.scenario_id,
            "redteam_results": redteam_result,
            "standard_analysis": standard_llm,
            "test_objectives": request.test_objectives,
            "processing_time_ms": processing_time
        }
        
        redteam_results.append(result_record)
        
        return JSONResponse({
            "success": True,
            "redteam_analysis": redteam_result,
            "standard_analysis": standard_llm,
            "processing_time_ms": processing_time,
            "message": f"Red team test completed. Attack {'succeeded' if redteam_result['attack_success'] else 'failed'}."
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "message": "Red team analysis failed"
        }, status_code=500)





@app.get("/records")
async def get_records(
    companies: Optional[str] = None,
    sourceConnectors: Optional[str] = None,
    statuses: Optional[str] = None,
    priorities: Optional[str] = None,
    issueTypes: Optional[str] = None,
    tags: Optional[str] = None,
    departments: Optional[str] = None,
    authors: Optional[str] = None,
    searchQuery: Optional[str] = None,
    qualityScoreRange: Optional[str] = None,
    dateRange: Optional[str] = None,
    page: int = 1,
    pageSize: int = 25,
    sortBy: str = "createdAt",
    sortOrder: str = "desc"
):
    """Get quality records with filtering and pagination"""
    try:
        # Build filters dictionary
        filters = {}
        
        if companies:
            filters['companies'] = companies.split(',')
        if sourceConnectors:
            filters['sourceConnectors'] = sourceConnectors.split(',')
        if statuses:
            filters['statuses'] = statuses.split(',')
        if priorities:
            filters['priorities'] = priorities.split(',')
        if issueTypes:
            filters['issueTypes'] = issueTypes.split(',')
        if tags:
            filters['tags'] = tags.split(',')
        if departments:
            filters['departments'] = departments.split(',')
        if authors:
            filters['authors'] = authors.split(',')
        if searchQuery:
            filters['searchQuery'] = searchQuery
        
        # Handle qualityScoreRange parameter
        if qualityScoreRange:
            try:
                score_parts = qualityScoreRange.split(',')
                if len(score_parts) == 2:
                    min_score = float(score_parts[0])
                    max_score = float(score_parts[1])
                    filters['qualityScoreRange'] = [min_score, max_score]
            except ValueError:
                pass  # Ignore invalid qualityScoreRange format
        
        # Handle dateRange parameter  
        if dateRange:
            try:
                date_parts = dateRange.split(',')
                if len(date_parts) == 2:
                    filters['dateRange'] = {
                        'from': date_parts[0],
                        'to': date_parts[1]
                    }
            except:
                pass  # Ignore invalid dateRange format
        
        # Add pagination and sorting
        filters['page'] = page
        filters['pageSize'] = pageSize
        filters['sortBy'] = sortBy
        filters['sortOrder'] = sortOrder
        
        # Get records from database
        records = get_records_from_db(filters, page, pageSize)
        
        # Transform to expected format
        transformed_records = []
        
        # Get approval threshold from dynamic system (same as /ingest endpoint)
        settings = get_settings()
        approval_threshold = get_threshold_value("approval_quality_score_threshold") or float(settings.approval_quality_score_threshold)
        
        for record in records:
            # Get detailed quality checks from database
            record_id = record.get('record_id', '')
            detailed_quality_checks = []
            issues = []
            llm_confidence = 0.0  # Default to "Not Triggered" instead of 0.0
            rules_engine_confidence = 0.0
            rules_engine_checks = []
            
            print(f"🔍 Processing record: {record_id}")
            print(f"🔧 DEBUG: record['quality_score']: {record['quality_score']} (type: {type(record['quality_score'])})")
            print(f"🔧 DEBUG: approval_threshold: {approval_threshold} (type: {type(approval_threshold)})")
            print(f"🔧 DEBUG: llm_confidence: {llm_confidence} (type: {type(llm_confidence)})")
            print(f"🔧 DEBUG: rules_engine_confidence: {rules_engine_confidence} (type: {type(rules_engine_confidence)})")            
            # Fetch quality checks from database
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT check_name, status, confidence_score, failure_reason, 
                           check_metadata_json, executed_at, processing_time_ms
                    FROM quality_checks 
                    WHERE record_id = ?
                    ORDER BY executed_at DESC
                """, (record_id,))
                
                quality_check_rows = cursor.fetchall()
                conn.close()
                
                for check_row in quality_check_rows:
                    check_name, status, confidence_score, failure_reason, metadata_json, executed_at, processing_time_ms = check_row
                    
                    # Parse metadata
                    metadata = {}
                    if metadata_json:
                        try:
                            metadata = json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json
                        except:
                            metadata = {}
                    
                    # Create detailed quality check result
                    detailed_check = {
                        'check_name': check_name,
                        'status': status.upper() if status else 'UNKNOWN',
                        'confidence_score': confidence_score or 0.0,
                        'failure_reason': failure_reason or '',
                        'description': metadata.get('description', failure_reason or f"{check_name} check completed"),
                        'suggestion': metadata.get('suggestion', ''),
                        'autoFixable': metadata.get('autoFixable', False),
                        'category': metadata.get('category', 'rules'),
                        'type': metadata.get('type', check_name),
                        'severity': metadata.get('severity', 'medium'),
                        'processing_time_ms': processing_time_ms or 0,
                        'executed_at': executed_at,
                        'metadata': metadata
                    }
                    
                    detailed_quality_checks.append(detailed_check)
                    
                    # Create issues for failed checks
                    if status and status.lower() in ['fail', 'failed', 'flagged']:
                        issues.append({
                            'id': f"issue-{record_id}-{check_name}",
                            'type': check_name,
                            'severity': metadata.get('severity', 'medium'),
                            'description': failure_reason or f"{check_name} check failed",
                            'suggestion': metadata.get('suggestion', f"Fix {check_name.replace('_', ' ')}"),
                            'autoFixable': metadata.get('autoFixable', False),
                            'category': metadata.get('category', 'content'),
                            'confidence': confidence_score or 0.0
                        })
                    
                    # Calculate confidence values by check type
                    if check_name == 'llm_semantic_validation':
                        llm_confidence = confidence_score if confidence_score is not None else 0.0
                    elif check_name == 'llm_invocation_decision':
                        # Skip LLM invocation decision - it's not a rules engine check
                        pass
                    else:
                        # Only actual rules engine checks
                        rules_engine_checks.append(confidence_score or 0.0)
                
                # Calculate average rules engine confidence
                if rules_engine_checks:
                    rules_engine_confidence = sum(rules_engine_checks) / len(rules_engine_checks)
                    
            except Exception as e:
                print(f"❌ ERROR fetching quality checks for record {record_id}: {e}")
                print(f"🔧 Database path: {DB_PATH}")
                print(f"🔧 Record ID type: {type(record_id)}")
                print(f"🔧 SQL query variables: record_id={record_id}")
                import traceback
                traceback.print_exc()
                # Set empty lists explicitly
                detailed_quality_checks = []
                issues = []
                print(f"🔧 Set empty lists due to error")
            
            # Parse metadata
            content_metadata = record.get('content_metadata', {})
            
            transformed_records.append({
                'id': record['id'],
                'recordId': record['record_id'],
                'companyId': f"company-{hash(record['company']) % 1000}",
                'companyName': record['company'] or 'Unknown Company',
                'sourceConnectorName': record['source_connector'],
                'sourceConnectorType': record['source_connector'].lower(),
                'content': record['content'],
                'contentPreview': record['content'][:200] + '...' if len(record['content']) > 200 else record['content'],
                'tags': record['tags'],
                'status': record.get('status', 'approved' if float(record['quality_score']) >= approval_threshold else 'flagged'),
                'qualityScore': record['quality_score'],
                # Use unified scoring formula for combined confidence (same as quality score)
                'confidenceScore': (rules_engine_confidence * 0.6 + llm_confidence * 0.4) if llm_confidence > 0 and rules_engine_confidence > 0 else rules_engine_confidence,
                'llm_confidence': llm_confidence,
                'rules_engine_confidence': rules_engine_confidence,
                'issues': issues,
                'quality_checks': detailed_quality_checks,  # Add detailed quality checks
                'llmSuggestions': record.get('llm_suggestions', []),
                'llmReasoning': record.get('llm_reasoning', ''),
                'metadata': {
                    'author': content_metadata.get('author', 'Unknown'),
                    'department': content_metadata.get('department', 'Unknown'),
                    'documentType': content_metadata.get('document_type', 'document'),
                    'lastModified': record['created_at'],
                    'fileSize': len(record['content']),
                    'language': 'en',
                    'wordCount': content_metadata.get('word_count', len(record['content'].split())),
                    'sensitivity': 'internal'
                },
                'createdAt': record['created_at'],
                'updatedAt': record['created_at'],
                'priority': 'high' if float(record['quality_score']) < 50 else 'medium',
                'trace_id': record.get('trace_id', f"trace-{record['record_id']}")
            })
        
        # Get total count with the same filters
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Build the same query as get_records_from_db but for counting
        count_query = "SELECT COUNT(*) FROM processed_records WHERE 1=1"
        count_params = []
        
        if filters:
            # Apply the same filters as in get_records_from_db
            
            # Handle companies filter
            if filters.get('companies'):
                companies_list = filters['companies'] if isinstance(filters['companies'], list) else [filters['companies']]
                placeholders = ','.join(['?' for _ in companies_list])
                count_query += f" AND company IN ({placeholders})"
                count_params.extend(companies_list)
            
            # Handle sourceConnectors filter
            if filters.get('sourceConnectors'):
                connectors_list = filters['sourceConnectors'] if isinstance(filters['sourceConnectors'], list) else [filters['sourceConnectors']]
                placeholders = ','.join(['?' for _ in connectors_list])
                count_query += f" AND source_connector IN ({placeholders})"
                count_params.extend(connectors_list)
            
            # Handle statuses filter (map to quality_level) - using hardcoded thresholds
            if filters.get('statuses'):
                statuses_list = filters['statuses'] if isinstance(filters['statuses'], list) else [filters['statuses']]
                status_conditions = []
                
                # Get dynamic approval threshold for fallback
                approval_threshold = get_threshold_value("approval_quality_score_threshold") or 50.0
                
                for status in statuses_list:
                    # Use real current status from audit trails, then actual status field, fallback to quality score
                    condition = f"""(
                        CASE 
                            WHEN manual_review_status IS NOT NULL AND manual_review_status != 'pending' AND 
                                 manual_review_status LIKE '%status_change%' THEN
                                (
                                    SELECT json_extract(value, '$.status_change.new')
                                    FROM json_each(manual_review_status)
                                    WHERE json_extract(value, '$.status_change') IS NOT NULL
                                    ORDER BY json_extract(value, '$.timestamp') DESC
                                    LIMIT 1
                                )
                            WHEN status IS NOT NULL THEN status
                            WHEN CAST(quality_score AS REAL) >= {approval_threshold} THEN 'approved'
                            ELSE 'flagged'
                        END = '{status}'
                    )"""
                    status_conditions.append(condition)
                if status_conditions:
                    count_query += f" AND ({' OR '.join(status_conditions)})"
            
            # Handle priorities filter - using hardcoded thresholds
            if filters.get('priorities'):
                priorities_list = filters['priorities'] if isinstance(filters['priorities'], list) else [filters['priorities']]
                priority_conditions = []
                for priority in priorities_list:
                    if priority == 'high':
                        priority_conditions.append(f"CAST(quality_score AS REAL) >= 40.0 AND CAST(quality_score AS REAL) < 80.0")
                    elif priority == 'medium':
                        priority_conditions.append(f"0.8 <= CAST(quality_score AS REAL)")
                    elif priority == 'low':
                        priority_conditions.append(f"CAST(quality_score AS REAL) >= 80.0")
                if priority_conditions:
                    count_query += f" AND ({' OR '.join(priority_conditions)})"
            
            # Handle tags filter
            if filters.get('tags'):
                tags_list = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
                for tag in tags_list:
                    count_query += " AND tags LIKE ?"
                    count_params.append(f'%{tag}%')
            
            # Handle departments filter (from content_metadata)
            if filters.get('departments'):
                departments_list = filters['departments'] if isinstance(filters['departments'], list) else [filters['departments']]
                for dept in departments_list:
                    count_query += " AND content_metadata LIKE ?"
                    count_params.append(f'%"department":"{dept}"%')
            
            # Handle authors filter (from content_metadata)
            if filters.get('authors'):
                authors_list = filters['authors'] if isinstance(filters['authors'], list) else [filters['authors']]
                for author in authors_list:
                    count_query += " AND content_metadata LIKE ?"
                    count_params.append(f'%"author":"{author}"%')
            
            # Handle searchQuery filter
            if filters.get('searchQuery'):
                search_term = filters['searchQuery']
                count_query += " AND (content LIKE ? OR title LIKE ? OR company LIKE ?)"
                count_params.extend([f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'])
        
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]
        conn.close()
        
        return {
            "data": transformed_records,
            "pagination": {
                "page": page,
                "pageSize": pageSize,
                "total": total_count,
                "totalPages": (total_count + pageSize - 1) // pageSize
            },
            "appliedFiltersCount": len([k for k, v in filters.items() if v and k not in ['page', 'pageSize', 'sortBy', 'sortOrder']])
        }
        
    except Exception as e:
        store_dead_letter(
            trace_id=f"records-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
            raw_input=f"GET /records with params: {locals()}",
            error_message=str(e),
            error_type="RECORDS_FETCH_ERROR"
        )
        raise HTTPException(status_code=500, detail=f"Failed to fetch records: {str(e)}")

@app.get("/export/records")
async def export_records(format: str = "json"):
    """
    Export processed records in various formats
    """
    try:
        if format.lower() == "json":
            return JSONResponse({
                "success": True,
                "export_format": "json",
                "total_records": len(processed_records),
                "exported_at": datetime.now(UTC).isoformat(),
                "data": processed_records
            })
        elif format.lower() == "csv":
            # Convert records to CSV format
            csv_data = []
            for record in processed_records:
                csv_row = {
                    "id": record["id"],
                    "title": record.get("title", ""),
                    "quality_score": record["quality_score"],
                    "status": record["status"],
                    "tags": ", ".join(record["tags"]),
                    "source_type": record.get("source_type", record["source_connector"]),
                    "company": record.get("content_metadata", {}).get("company", ""),
                    "author": record.get("content_metadata", {}).get("author_name", ""),
                    "created_at": record["created_at"],
                    "content_preview": record["content"][:200] + "..." if len(record["content"]) > 200 else record["content"]
                }
                csv_data.append(csv_row)
            
            return JSONResponse({
                "success": True,
                "export_format": "csv",
                "total_records": len(csv_data),
                "exported_at": datetime.now(UTC).isoformat(),
                "data": csv_data
            })
        else:
            return JSONResponse({
                "success": False,
                "error": f"Unsupported export format: {format}",
                "supported_formats": ["json", "csv"]
            }, status_code=400)
            
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "message": "Export failed"
        }, status_code=500)

@app.post("/import/records")
async def import_records(file_data: Dict[str, Any]):
    """
    Import records from uploaded data
    """
    global processed_records, processed_count
    
    try:
        imported_records = file_data.get("data", [])
        if not imported_records:
            return JSONResponse({
                "success": False,
                "error": "No data found in import file"
            }, status_code=400)
        
        # Validate and process imported records
        successful_imports = 0
        for record in imported_records:
            # Ensure required fields exist
            if all(field in record for field in ["id", "content", "tags", "source_connector"]):
                # Add created_at if missing
                if "created_at" not in record:
                    record["created_at"] = datetime.now(UTC).isoformat()
                
                # Add processing metadata if missing
                if "processing_time_ms" not in record:
                    record["processing_time_ms"] = 0
                
                processed_records.append(record)
                successful_imports += 1
                processed_count += 1
        
        return JSONResponse({
            "success": True,
            "message": f"Successfully imported {successful_imports} records",
            "total_imported": successful_imports,
            "total_records_now": len(processed_records),
            "imported_at": datetime.now(UTC).isoformat()
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e),
            "message": "Import failed"
        }, status_code=500)

@app.post("/ingest/unified-demo")
async def unified_bulk_demo(records: List[Dict[str, Any]]):
    """
    🚀 UNIFIED BULK DEMO - Simple demonstration of unified bulk processing
    
    This endpoint shows how to process multiple records through the SAME
    robust pipeline as the single /ingest endpoint, ensuring:
    - ✅ Full 11-dimensional quality analysis
    - ✅ LLM integration with smart triggering  
    - ✅ Proper error handling & dead letter queue
    - ✅ Consistent scoring and status determination
    
    Comparison with old /ingest/batch:
    - OLD: Hardcoded quality_score=85, no real analysis
    - NEW: Full analysis with actual quality scores
    """
    if not records:
        raise HTTPException(status_code=400, detail="No records provided")
    
    results = []
    total_start_time = time.time()
    
    for i, record_data in enumerate(records):
        try:
            # Normalize different input formats to ContentIngestRequest
            content = (
                record_data.get("content") or
                record_data.get("document_text") or
                record_data.get("text") or
                str(record_data.get("title", ""))
            )
            
            tags = record_data.get("tags", ["unified-bulk"])
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(",")]
            
            record_id = record_data.get("record_id") or f"unified-{int(time.time())}-{i}"
            source_connector = record_data.get("source_connector", "Custom")
            content_metadata = record_data.get("content_metadata", {})
            
            # Create proper ContentIngestRequest
            unified_request = ContentIngestRequest(
                record_id=record_id,
                content=content,
                tags=tags,
                source_connector=source_connector,
                content_metadata=content_metadata
            )
            
            # Process through the SAME robust pipeline as single /ingest
            result = await ingest_content(unified_request)
            
            results.append({
                "record_id": record_id,
                "status": "success",
                "quality_score": result.get("quality_score"),
                "processing_status": result.get("status"),
                "llm_suggestions": result.get("llm_suggestions", []),
                "processing_time_ms": result.get("processing_time_ms"),
                "original_input": record_data
            })
            
        except Exception as e:
            results.append({
                "record_id": record_data.get("record_id", f"error-{i}"),
                "status": "error", 
                "error": str(e),
                "original_input": record_data
            })
    
    total_processing_time = (time.time() - total_start_time) * 1000
    successful_records = [r for r in results if r["status"] == "success"]
    avg_quality_score = sum(r.get("quality_score", 0) for r in successful_records) / len(successful_records) if successful_records else 0
            
    return {
        "unified_bulk_processing": True,
        "total_records": len(records),
        "successful": len(successful_records),
        "errors": len(results) - len(successful_records),
        "avg_quality_score": round(avg_quality_score, 2),
        "total_processing_time_ms": round(total_processing_time, 2),
        "comparison_note": "Each record processed through full pipeline with real quality analysis",
        "results": results
    }

# ================================================================
# 🚀 UNIFIED BULK + STREAMING INGESTION ENDPOINTS
# ================================================================

if UNIFIED_BULK_AVAILABLE:
    
    @app.post("/ingest/unified-bulk")
    async def unified_bulk_ingest(
        records: List[Dict[str, Any]] = None,
        batch_size: int = 10,
        concurrent_limit: int = 5
    ):
        """
        🚀 UNIFIED BULK INGESTION - New single endpoint for all bulk processing
        
        Processes multiple records through the SAME robust pipeline as /ingest endpoint
        - ✅ Full 11-dimensional quality analysis  
        - ✅ LLM integration with smart triggering
        - ✅ Proper error handling & dead letter queue
        - ✅ Real-time streaming progress updates
        
        Replaces: /ingest/batch, /ingest/sharepoint, /ingest/elasticsearch, etc.
        
        Input formats supported:
        - Array of records with flexible field mapping
        - SharePoint, Elasticsearch, external API formats  
        - Any JSON structure - automatically normalized
        """
        if not records:
            raise HTTPException(status_code=400, detail="No records provided")
        
        if len(records) == 0:
            raise HTTPException(status_code=400, detail="Empty records array")
        
        # Use streaming processor for real-time updates
        return create_streaming_response(
            bulk_processor.process_batch_stream(records, batch_size, concurrent_limit)
        )

    @app.post("/ingest/unified-upload")
    async def unified_file_upload(
        file: UploadFile = File(...),
        batch_size: int = 10,
        concurrent_limit: int = 5
    ):
        """
        📁 UNIFIED FILE UPLOAD - Upload JSON/JSONL files for bulk processing
        
        Supports multiple file formats:
        - ✅ JSON array: [{"content": "...", "tags": [...]}]
        - ✅ JSONL: One JSON per line
        - ✅ Elasticsearch: {"hits": [...]}
        - ✅ SharePoint: {"answers": [...]}
        - ✅ Batch format: {"chunks": [...]}
        
        All records processed through the same robust /ingest pipeline
        """
        try:
            # Extract records from file (supports multiple formats)
            records = await extract_records_from_upload(file)
            
            if not records:
                raise HTTPException(status_code=400, detail="No valid records found in file")
            
            # Process through unified pipeline with streaming
            return create_streaming_response(
                bulk_processor.process_batch_stream(records, batch_size, concurrent_limit)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")

    @app.websocket("/ingest/unified-stream")
    async def unified_streaming_websocket(websocket: WebSocket):
        """
        🌊 UNIFIED STREAMING INGESTION - Real-time WebSocket for continuous processing
        
        Features:
        - ✅ Real-time bidirectional communication
        - ✅ Send records individually or in batches
        - ✅ Live progress updates and results
        - ✅ Same robust /ingest pipeline for each record
        - ✅ Error handling with detailed feedback
        """
        await websocket.accept()
        
        try:
            while True:
                # Receive data from client
                data = await websocket.receive_json()
                
                if data.get("type") == "single_record":
                    # Process single record
                    result = await bulk_processor.process_single_record(data.get("record", {}))
                    await websocket.send_json({
                        "type": "single_result",
                        "result": result
                    })
                    
                elif data.get("type") == "batch_records":
                    # Process batch with streaming updates
                    records = data.get("records", [])
                    batch_size = data.get("batch_size", 10)
                    concurrent_limit = data.get("concurrent_limit", 5)
                    
                    async for update in bulk_processor.process_batch_stream(records, batch_size, concurrent_limit):
                        await websocket.send_json({
                            "type": "batch_update", 
                            "update": update
                        })
                    
                    # Send completion signal
                    await websocket.send_json({
                        "type": "batch_complete",
                        "message": "All records processed"
                    })
                    
                elif data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.close(code=1000, reason=str(e))

    @app.get("/ingest/unified-status")
    async def get_unified_processing_status():
        """
        📊 Get current processing statistics for unified bulk ingestion
        """
        stats = bulk_processor.processing_stats
        elapsed_time = time.time() - stats["start_time"]
        
        return {
            "total_processed": stats["total_processed"],
            "total_errors": stats["total_errors"],
            "success_rate": round(
                (stats["total_processed"] / (stats["total_processed"] + stats["total_errors"])) * 100, 2
            ) if (stats["total_processed"] + stats["total_errors"]) > 0 else 0,
            "processing_rate_per_second": round(
                stats["total_processed"] / elapsed_time, 2
            ) if elapsed_time > 0 else 0,
            "uptime_seconds": round(elapsed_time, 2)
        }

    # External API Integration using unified processor
    @app.post("/external-api/unified-fetch")
    async def unified_external_api_fetch(config_id: str):
        """
        🌐 UNIFIED EXTERNAL API FETCH - Fetch from external APIs using unified processing
        
        Replaces existing external API endpoints with unified pipeline integration
        """
        try:
            if config_id not in ingestion_configs:
                raise HTTPException(status_code=404, detail="Configuration not found")
            
            config_data = ingestion_configs[config_id]
            
            # Fetch data from external API
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(config_data["api_url"], headers=config_data.get("headers", {})) as response:
                        if response.status != 200:
                            raise HTTPException(status_code=response.status, detail="External API request failed")
                        
                        data = await response.json()
                        
                        # Extract records based on API response format
                        records = []
                        if isinstance(data, list):
                            records = data
                        elif isinstance(data, dict):
                            # Handle different response formats
                            for key in ["data", "items", "records", "results", "hits"]:
                                if key in data and isinstance(data[key], list):
                                    records = data[key]
                                    break
                        
                        if not records:
                            return {"message": "No records found in API response", "total_fetched": 0}
                        
                        # Limit to batch size
                        batch_size = config_data.get("batch_size", 50)
                        records = records[:batch_size]
                        
                        # Process through unified pipeline
                        return create_streaming_response(
                            bulk_processor.process_batch_stream(records, 10, 5)
                        )
                        
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"External API fetch failed: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to process external API request: {str(e)}")

    # Migration helpers - redirect old endpoints to unified ones
    @app.post("/ingest/batch-unified")
    async def legacy_batch_redirect(batch_data: Dict[str, Any]):
        """
        🔄 LEGACY REDIRECT - Redirects old /ingest/batch to unified endpoint
        Maintains backward compatibility while using new robust pipeline
        """
        chunks = batch_data.get("chunks", [])
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks provided")
        
        return create_streaming_response(
            bulk_processor.process_batch_stream(chunks, 10, 5)
        )

    @app.post("/ingest/file-unified")
    async def legacy_file_redirect(file: UploadFile = File(...)):
        """
        🔄 LEGACY REDIRECT - Redirects old /ingest/file to unified upload
        """
        return await unified_file_upload(file)

else:
    print("⚠️  Unified bulk endpoints not available - unified_bulk_ingest module not loaded")

def extract_file_type_from_metadata(content_metadata: str, source_connector: str = "") -> str:
    """Extract file type from content metadata or source"""
    try:
        if content_metadata:
            metadata = json.loads(content_metadata) if isinstance(content_metadata, str) else content_metadata
            
            # Check for direct file_type field
            if 'file_type' in metadata:
                return metadata['file_type'].lower()
            
            # Extract from filename or file path
            filename = metadata.get('filename') or metadata.get('file_name') or metadata.get('title', '')
            if '.' in filename:
                ext = filename.split('.')[-1].lower()
                return ext
            
            # Check for document type indicators
            doc_type = metadata.get('document_type') or metadata.get('content_type', '')
            if doc_type:
                if 'pdf' in doc_type.lower():
                    return 'pdf'
                elif 'word' in doc_type.lower() or 'docx' in doc_type.lower():
                    return 'docx'
                elif 'excel' in doc_type.lower() or 'xlsx' in doc_type.lower():
                    return 'xlsx'
                elif 'powerpoint' in doc_type.lower() or 'pptx' in doc_type.lower():
                    return 'pptx'
        
        # Infer from source connector
        source_mapping = {
            'sharepoint': 'docx',
            'confluence': 'html',
            'notion': 'html',
            'jira': 'html',
            'gdrive': 'docx'
        }
        
        return source_mapping.get(source_connector.lower(), 'unknown')
        
    except Exception:
        return 'unknown'

@app.get("/analytics/dashboard")
async def get_dashboard_analytics():
    """Get real-time analytics data for dashboard"""
    try:
        analytics_data = get_unified_metrics_data()
        
        # Get real-time issue breakdown from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_records'")
        if not cursor.fetchone():
            conn.close()
            return {
                "qualityTrendData": analytics_data['weekly_trend'],
                "sourcePerformanceData": analytics_data['source_performance'],
                "issueBreakdownData": [],
                "companyMetricsData": [],
                "topFailureReasons": [],
                "fileTypeData": [],
                "today": {
                    "total_processed": analytics_data['total_records'],
                    "avg_quality_score": analytics_data['avg_quality_score'], 
                    "total_issues": analytics_data['issues_count']
                }
            }
        
        # Get real issue breakdown from processed records
        week_ago = (datetime.now(UTC) - timedelta(days=7)).date().isoformat()
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN quality_level = 'low' THEN 'Content Quality Issues'
                    WHEN quality_level = 'medium' THEN 'Minor Issues'
                    WHEN quality_score < 60 THEN 'Low Quality Records'
                    WHEN CAST(quality_score AS REAL) < 80 THEN 'Medium Quality Records'
                    ELSE 'Other Issues'
                END as issue_type,
                COUNT(*) as count
            FROM processed_records
            WHERE DATE(created_at) >= ? AND quality_level IN ('low', 'medium')
            GROUP BY issue_type
            ORDER BY count DESC
        ''', (week_ago,))
        
        issue_breakdown = cursor.fetchall()
        
        # Get real company metrics
        cursor.execute('''
            SELECT 
                company,
                COUNT(*) as records,
                AVG(quality_score) as avg_quality,
                SUM(CASE WHEN quality_level = 'low' THEN 1 ELSE 0 END) as issues,
                COUNT(*) * 0.05 as cost  -- Simple cost calculation
            FROM processed_records 
            WHERE DATE(created_at) >= ?
            GROUP BY company
            ORDER BY records DESC
        ''', (week_ago,))
        
        company_metrics = cursor.fetchall()
        
        # Get real failure reasons from quality_checks JSON field
        cursor.execute('''
            SELECT quality_checks 
            FROM processed_records 
            WHERE DATE(created_at) >= ? 
            AND quality_checks IS NOT NULL
        ''', (week_ago,))
        
        all_quality_checks = cursor.fetchall()
        
        # Aggregate failure reasons
        failure_reason_counts = defaultdict(int)
        total_records = 0
        
        for row in all_quality_checks:
            if row[0]:
                try:
                    checks = json.loads(row[0])
                    if isinstance(checks, list):
                        total_records += 1
                        has_failure = False
                        for check in checks:
                            if check.get('status') == 'fail':
                                has_failure = True
                                check_name = check.get('check_name', 'unknown')
                                # Map check names to user-friendly labels
                                reason_map = {
                                    'empty_tags': 'Insufficient Tags',
                                    'tag_count_validation': 'Tag Count Issues',
                                    'stopwords_detection': 'Too Many Generic Tags',
                                    'spam_pattern_detection': 'Spam/Test Content Detected',
                                    'duplicate_content_detection': 'Duplicate Content',
                                    'tag_text_relevance': 'Poor Tag-Content Relevance',
                                    'text_quality': 'Text Quality Issues'
                                }
                                reason = reason_map.get(check_name, check_name.replace('_', ' ').title())
                                failure_reason_counts[reason] += 1
                        
                        # If no failures, count as success
                        if not has_failure:
                            failure_reason_counts['No Issues Detected'] += 1
                except json.JSONDecodeError:
                    continue
        
        # Convert to list of tuples for consistency
        failure_reasons = [(reason, count) for reason, count in failure_reason_counts.items()]
        failure_reasons.sort(key=lambda x: x[1], reverse=True)
        failure_reasons = failure_reasons[:10]  # Top 10
        
        # Get file type analytics
        cursor.execute('''
            SELECT content_metadata, source_connector, quality_score, quality_level
            FROM processed_records 
            WHERE DATE(created_at) >= ?
        ''', (week_ago,))
        
        file_type_records = cursor.fetchall()
        file_type_stats = defaultdict(lambda: {
            'count': 0, 
            'avg_quality': 0, 
            'total_quality': 0, 
            'issues': 0,
            'success_rate': 0
        })
        
        for metadata, source, quality_score, quality_level in file_type_records:
            file_type = extract_file_type_from_metadata(metadata, source)
            
            # Normalize file type names
            file_type_mapping = {
                'docx': 'Microsoft Word',
                'doc': 'Microsoft Word',
                'xlsx': 'Microsoft Excel', 
                'xls': 'Microsoft Excel',
                'pptx': 'Microsoft PowerPoint',
                'ppt': 'Microsoft PowerPoint',
                'pdf': 'PDF Document',
                'html': 'Web Content',
                'txt': 'Text Document',
                'csv': 'CSV Data',
                'json': 'JSON Data',
                'xml': 'XML Document',
                'unknown': 'Unknown Type'
            }
            
            display_name = file_type_mapping.get(file_type, file_type.upper())
            stats = file_type_stats[display_name]
            
            stats['count'] += 1
            if quality_score:
                stats['total_quality'] += float(quality_score)
            if quality_level in ['low', 'medium']:
                stats['issues'] += 1
        
        # Calculate averages and success rates
        file_type_data = []
        for file_type, stats in file_type_stats.items():
            if stats['count'] > 0:
                avg_quality = stats['total_quality'] / stats['count'] if stats['total_quality'] > 0 else 0
                success_rate = (stats['count'] - stats['issues']) / stats['count'] if stats['count'] > 0 else 0
                
                file_type_data.append({
                    'fileType': file_type,
                    'count': stats['count'],
                    'avgQuality': round(avg_quality, 1),
                    'issues': stats['issues'],
                    'successRate': round(success_rate * 100, 1),
                    'color': get_file_type_color(file_type)
                })
        
        # Sort by count descending
        file_type_data.sort(key=lambda x: x['count'], reverse=True)
        
        conn.close()
        
        return {
            "qualityTrendData": analytics_data['weekly_trend'],
            "sourcePerformanceData": analytics_data['source_performance'],
            "issueBreakdownData": [
                {"name": row[0], "value": row[1], "color": get_issue_color(row[0])}
                for row in issue_breakdown
            ],
            "companyMetricsData": [
                {
                    "company": row[0] or "Unknown",
                    "records": row[1],
                    "avgQuality": round(row[2], 1) if row[2] else 0,
                    "issues": row[3],
                    "cost": round(row[4], 2)
                }
                for row in company_metrics
            ],
            "topFailureReasons": [
                {
                    "reason": row[0] or "Unknown issue",
                    "count": row[1],
                    "percentage": round((row[1] / sum(r[1] for r in failure_reasons)) * 100, 1) if failure_reasons and sum(r[1] for r in failure_reasons) > 0 else 0
                }
                for row in failure_reasons
            ],
            "fileTypeData": file_type_data,
            "today": {
                "total_processed": analytics_data['total_records'],
                "avg_quality_score": analytics_data['avg_quality_score'], 
                "total_issues": analytics_data['issues_count']
            }
        }
        
    except Exception as e:
        store_dead_letter(
            trace_id=f"analytics-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
            raw_input="GET /analytics/dashboard",
            error_message=str(e),
            error_type="ANALYTICS_FETCH_ERROR"
        )
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")

def get_issue_color(issue_type: str) -> str:
    """Get color for issue type"""
    colors = {
        'Content Quality Issues': '#ef4444',
        'Minor Issues': '#f97316',
        'Low Quality Records': '#dc2626',
        'Medium Quality Records': '#fbbf24',
        'Other Issues': '#6b7280',
        'Generic Tags': '#fbbf24',
        'Content Quality': '#ef4444', 
        'Missing Context': '#f97316',
        'Spam Detection': '#6b7280',
        'Duplicate Content': '#3b82f6',
        'PII Detected': '#dc2626',
        # New failure reason colors
        'Insufficient Tags': '#f59e0b',
        'Tag Count Issues': '#f59e0b',
        'Too Many Generic Tags': '#f97316',
        'Spam/Test Content Detected': '#6b7280',
        'Poor Tag-Content Relevance': '#ef4444',
        'Text Quality Issues': '#dc2626',
        'No Issues Detected': '#10b981'
    }
    return colors.get(issue_type, '#6b7280')

def get_file_type_color(file_type: str) -> str:
    """Get color for file type"""
    colors = {
        'Microsoft Word': '#2563eb',
        'Microsoft Excel': '#16a34a', 
        'Microsoft PowerPoint': '#dc2626',
        'PDF Document': '#dc2626',
        'Web Content': '#f97316',
        'Text Document': '#6b7280',
        'CSV Data': '#16a34a',
        'JSON Data': '#8b5cf6',
        'XML Document': '#f59e0b',
        'Unknown Type': '#6b7280'
    }
    return colors.get(file_type, '#6b7280')

@app.get("/records/filter-options")
async def get_filter_options():
    """Get filter options for analytics dashboard"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get companies with counts
        cursor.execute('''
            SELECT company, COUNT(*) as count 
            FROM processed_records 
            WHERE company IS NOT NULL AND company != '' 
            GROUP BY company 
            ORDER BY count DESC
        ''')
        companies = [
            {"value": row[0], "label": row[0], "count": row[1]} 
            for row in cursor.fetchall()
        ]
        
        # Get connectors with counts
        cursor.execute('''
            SELECT source_connector, COUNT(*) as count 
            FROM processed_records 
            WHERE source_connector IS NOT NULL 
            GROUP BY source_connector 
            ORDER BY count DESC
        ''')
        connectors = [
            {"value": row[0], "label": row[0], "count": row[1]} 
            for row in cursor.fetchall()
        ]
        
        # Get file types with counts
        cursor.execute('''
            SELECT content_metadata, source_connector
            FROM processed_records 
            WHERE content_metadata IS NOT NULL OR source_connector IS NOT NULL
        ''')
        
        file_type_counts = defaultdict(int)
        for metadata, source in cursor.fetchall():
            file_type = extract_file_type_from_metadata(metadata, source)
            
            # Normalize file type names
            file_type_mapping = {
                'docx': 'Microsoft Word',
                'doc': 'Microsoft Word',
                'xlsx': 'Microsoft Excel', 
                'xls': 'Microsoft Excel',
                'pptx': 'Microsoft PowerPoint',
                'ppt': 'Microsoft PowerPoint',
                'pdf': 'PDF Document',
                'html': 'Web Content',
                'txt': 'Text Document',
                'csv': 'CSV Data',
                'json': 'JSON Data',
                'xml': 'XML Document',
                'unknown': 'Unknown Type'
            }
            
            display_name = file_type_mapping.get(file_type, file_type.upper())
            file_type_counts[display_name] += 1
        
        file_types = [
            {"value": file_type, "label": file_type, "count": count}
            for file_type, count in sorted(file_type_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        conn.close()
        
        return {
            "companies": companies,
            "connectors": connectors,
            "fileTypes": file_types,
            "statuses": [
                {"value": "approved", "label": "Approved"},
                {"value": "flagged", "label": "Flagged"},
                {"value": "pending", "label": "Pending"},
                {"value": "under_review", "label": "Under Review"}
            ]
        }
        
    except Exception as e:
        print(f"Error getting filter options: {e}")
        return {
            "companies": [],
            "connectors": [],
            "fileTypes": [],
            "statuses": []
        }



@app.get("/issues")
async def get_issues():
    """Get real-time issues data"""
    try:
        issues = get_issues_data()
        return {"issues": issues}
        
    except Exception as e:
        store_dead_letter(
            trace_id=f"issues-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
            raw_input="GET /issues",
            error_message=str(e),
            error_type="ISSUES_FETCH_ERROR"
        )
        raise HTTPException(status_code=500, detail=f"Failed to fetch issues: {str(e)}")

@app.post("/issues/{issue_id}/auto-fix")
async def auto_fix_issue(issue_id: str):
    """Attempt to auto-fix an issue using OpenAI LLM"""
    try:
        import asyncio
        # Get issue details
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Find the record and its issues
        cursor.execute('''
            SELECT id, record_id, content, tags, issues FROM processed_records 
            WHERE id = ?
        ''', (issue_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Issue not found")
        db_id, record_id, content, tags_json, issues_json = row
        tags = json.loads(tags_json) if tags_json else []
        issues = json.loads(issues_json) if issues_json else []
        # Find the specific issue
        target_issue = None
        for issue in issues:
            if issue.get('id') == issue_id:
                target_issue = issue
                break
        if not target_issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        # Compose LLM prompt
        system_prompt = (
            "You are an expert content quality fixer. Given the following record and its issues, "
            "suggest improved tags and content. Return only a JSON object with 'fixed_tags', 'fixed_content', and 'llm_reasoning'."
        )
        user_prompt = (
            f"RECORD:\nContent: {content}\nTags: {tags}\n\nISSUE:\n{target_issue.get('description', '')}"
        )
        # Call OpenAI via llm_judge
        if llm_judge and hasattr(llm_judge, 'openai_client') and llm_judge.openai_client:
            # Use OpenAI directly for custom prompt
            response = await llm_judge.openai_client.chat.completions.create(
                model=getattr(llm_judge.settings, 'llm_model', 'gpt-3.5-turbo'),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=getattr(llm_judge.settings, 'llm_max_tokens', 1000),
                temperature=getattr(llm_judge.settings, 'llm_temperature', 0.7),
                response_format={"type": "json_object"}
            )
            content_str = response.choices[0].message.content
            try:
                result = json.loads(content_str or "{}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"LLM response parse error: {e}\nRaw: {content_str}")
            # Optionally update the record with the fix
            fixed_tags = result.get('fixed_tags') if result.get('fixed_tags') is not None else tags
            fixed_content = result.get('fixed_content') if result.get('fixed_content') is not None else content
            if not isinstance(fixed_tags, list):
                try:
                    fixed_tags = list(fixed_tags)
                except Exception:
                    fixed_tags = tags
            if not isinstance(fixed_content, str):
                fixed_content = str(fixed_content) if fixed_content is not None else content
            # Update the record in DB
            cursor.execute('''
                UPDATE processed_records 
                SET tags = ?, content = ?, updated_at = ?
                WHERE id = ?
            ''', (json.dumps(fixed_tags), fixed_content, datetime.now(UTC).isoformat(), db_id))
            conn.commit()
            conn.close()
            return {
                "success": True,
                "fixed_tags": fixed_tags,
                "fixed_content": fixed_content,
                "llm_reasoning": result.get('llm_reasoning', ''),
                "raw_llm": result
            }
        else:
            raise HTTPException(status_code=503, detail="OpenAI LLM is not available or not configured.")
    except HTTPException:
        raise
    except Exception as e:
        store_dead_letter(
            trace_id=f"auto-fix-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
            raw_input=f"POST /issues/{issue_id}/auto-fix",
            error_message=str(e),
            error_type="AUTO_FIX_ERROR"
        )
        raise HTTPException(status_code=500, detail=f"Failed to auto-fix issue: {str(e)}")

@app.get("/dead-letters")
async def get_dead_letters():
    """Get dead letter queue for debugging"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, trace_id, error_message, error_type, failed_at, source_connector, retry_count, resolved
            FROM dead_letters 
            ORDER BY failed_at DESC
        ''')
        
        rows = cursor.fetchall()
        dead_letters = []
        
        for row in rows:
            dead_letters.append({
                'id': row[0],
                'trace_id': row[1],
                'error_message': row[2],
                'error_type': row[3],
                'failed_at': row[4],
                'source_connector': row[5],
                'retry_count': row[6],
                'resolved': bool(row[7])
            })
        
        conn.close()
        return {"dead_letters": dead_letters}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dead letters: {str(e)}")

@app.get("/dead-letters/filter-options")
async def get_dead_letters_filter_options():
    """Get dynamic filter options for dead letters based on real data"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get unique error types with counts
        cursor.execute("""
            SELECT error_type, COUNT(*) as count 
            FROM dead_letters 
            WHERE error_type IS NOT NULL AND error_type != '' 
            GROUP BY error_type 
            ORDER BY count DESC
        """)
        error_type_rows = cursor.fetchall()
        error_types = [{"value": row[0], "label": row[0], "count": row[1]} for row in error_type_rows]
        
        # Get unique source connectors with counts
        cursor.execute("""
            SELECT source_connector, COUNT(*) as count 
            FROM dead_letters 
            WHERE source_connector IS NOT NULL AND source_connector != '' 
            GROUP BY source_connector 
            ORDER BY count DESC
        """)
        connector_rows = cursor.fetchall()
        source_connectors = [{"value": row[0], "label": row[0], "count": row[1]} for row in connector_rows]
        
        conn.close()
        
        return {
            'error_types': error_types,
            'source_connectors': source_connectors,
            'time_periods': [
                {"value": 1, "label": "Last Hour"},
                {"value": 6, "label": "Last 6 Hours"},
                {"value": 24, "label": "Last 24 Hours"},
                {"value": 168, "label": "Last Week"},
                {"value": 720, "label": "Last Month"}
            ]
        }
        
    except Exception as e:
        print(f"Error getting dead letter filter options: {e}")
        # Return fallback data
        return {
            'error_types': [
                {"value": "SCHEMA_VALIDATION_ERROR", "label": "Schema Validation", "count": 0},
                {"value": "PROCESSING_ERROR", "label": "Processing Error", "count": 0},
                {"value": "TIMEOUT_ERROR", "label": "Timeout", "count": 0},
                {"value": "LLM_ERROR", "label": "LLM Error", "count": 0},
                {"value": "CONNECTION_ERROR", "label": "Connection Error", "count": 0}
            ],
            'source_connectors': [
                {"value": "SharePoint", "label": "SharePoint", "count": 0},
                {"value": "Confluence", "label": "Confluence", "count": 0},
                {"value": "Notion", "label": "Notion", "count": 0},
                {"value": "GDrive", "label": "Google Drive", "count": 0},
                {"value": "Elasticsearch", "label": "Elasticsearch", "count": 0}
            ],
            'time_periods': [
                {"value": 1, "label": "Last Hour"},
                {"value": 6, "label": "Last 6 Hours"},
                {"value": 24, "label": "Last 24 Hours"},
                {"value": 168, "label": "Last Week"},
                {"value": 720, "label": "Last Month"}
            ]
        }

@app.post("/dead-letters/{letter_id}/retry")
async def retry_dead_letter(letter_id: str):
    """Retry processing a dead letter"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get dead letter details
        cursor.execute('''
            SELECT trace_id, raw_input, error_message, error_type, source_connector
            FROM dead_letters 
            WHERE id = ?
        ''', (letter_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dead letter not found")
        
        trace_id, raw_input, error_message, error_type, source_connector = row
        
        # Attempt to reprocess
        try:
            # Parse the original input and reprocess
            original_data = json.loads(raw_input)
            
            # Create a new ingest request
            ingest_request = ContentIngestRequest(
                record_id=original_data.get('record_id', f"retry-{trace_id}"),
                content=original_data.get('content', ''),
                tags=original_data.get('tags', []),
                source_connector=original_data.get('source_connector', 'unknown'),
                content_metadata=original_data.get('content_metadata')
            )
            
            # Process the request
            result = await ingest_content(ingest_request)
            
            # Mark as resolved
            cursor.execute('''
                UPDATE dead_letters 
                SET resolved = TRUE, retry_count = retry_count + 1
                WHERE id = ?
            ''', (letter_id,))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": "Dead letter reprocessed successfully",
                "result": result
            }
            
        except Exception as retry_error:
            # Update retry count
            cursor.execute('''
                UPDATE dead_letters 
                SET retry_count = retry_count + 1
                WHERE id = ?
            ''', (letter_id,))
            
            conn.commit()
            conn.close()
            
            raise HTTPException(status_code=500, detail=f"Retry failed: {str(retry_error)}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry dead letter: {str(e)}")

@app.get("/dead-letters/stats")
async def get_dead_letter_stats(hours_back: int = Query(24)):
    """Get dead letter statistics for the dashboard"""
    try:
        # Calculate cutoff time
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours_back)
        cutoff_str = cutoff_time.isoformat()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get records within time window
        cursor.execute('''
            SELECT error_type, source_connector, resolved, retry_count, failed_at
            FROM dead_letters 
            WHERE failed_at >= ?
            ORDER BY failed_at DESC
        ''', (cutoff_str,))
        
        rows = cursor.fetchall()
        conn.close()
        
        total_count = len(rows)
        
        # Group by error type
        by_error_type = {}
        by_status = {}
        by_source = {}
        
        for row in rows:
            error_type, source_connector, resolved, retry_count, failed_at = row
            
            # Error type stats
            by_error_type[error_type] = by_error_type.get(error_type, 0) + 1
            
            # Status stats
            if resolved:
                status = "resolved"
            elif retry_count > 0:
                status = "retrying"
            else:
                status = "failed"
            by_status[status] = by_status.get(status, 0) + 1
            
            # Source stats
            source = source_connector or "unknown"
            by_source[source] = by_source.get(source, 0) + 1
        
        return {
            "total_count": total_count,
            "unresolved_count": total_count - by_status.get("resolved", 0),
            "resolved_count": by_status.get("resolved", 0),
            "error_types": by_error_type,
            "source_connectors": by_source,
            "recent_trend": [],  # Could be implemented later
            "analysis_period_hours": hours_back
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting dead letter stats: {str(e)}")

@app.post("/dead-letters/{letter_id}/resolve")
async def resolve_dead_letter(letter_id: str):
    """Mark a dead letter as resolved"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if dead letter exists
        cursor.execute('SELECT id FROM dead_letters WHERE id = ?', (letter_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Dead letter not found")
        
        # Mark as resolved
        cursor.execute('''
            UPDATE dead_letters 
            SET resolved = TRUE, resolved_at = ?
            WHERE id = ?
        ''', (datetime.now(UTC).isoformat(), letter_id))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Dead letter marked as resolved"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving dead letter: {str(e)}")

@app.delete("/dead-letters/{letter_id}")
async def delete_dead_letter(letter_id: str):
    """Delete a dead letter record"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if dead letter exists
        cursor.execute('SELECT id FROM dead_letters WHERE id = ?', (letter_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Dead letter not found")
        
        # Delete the record
        cursor.execute('DELETE FROM dead_letters WHERE id = ?', (letter_id,))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Dead letter deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting dead letter: {str(e)}")

@app.post("/feedback")
async def submit_feedback(request: Dict[str, Any]):
    """Submit feedback for LLM improvement"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO llm_feedback 
            (id, trace_id, feedback_type, feedback_data, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            request.get('trace_id', ''),
            request.get('feedback_type', 'general'),
            json.dumps(request.get('feedback_data', {})),
            datetime.now(UTC).isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Feedback submitted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")

@app.get("/companies")
async def get_companies():
    """Get companies list"""
    return JSONResponse({
        "success": True,
        "companies": sample_companies
    })

@app.get("/connectors")
async def get_connectors():
    """Get available source connectors"""
    return [
        {"id": "1", "name": "SharePoint Production", "type": "sharepoint", "count": 456},
        {"id": "2", "name": "Confluence Wiki", "type": "confluence", "count": 234},
        {"id": "3", "name": "Google Drive Files", "type": "googledrive", "count": 189},
        {"id": "4", "name": "OneDrive Documents", "type": "onedrive", "count": 156},
        {"id": "5", "name": "Slack Channels", "type": "slack", "count": 98},
    ]

@app.get("/filters/options")
async def get_filter_options():
    """Get dynamic filter options with counts from real data"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get unique companies with counts
        cursor.execute("""
            SELECT company, COUNT(*) as count 
            FROM processed_records 
            WHERE company IS NOT NULL AND company != '' 
            GROUP BY company 
            ORDER BY count DESC
        """)
        company_rows = cursor.fetchall()
        companies = [{"id": str(i+1), "name": row[0], "count": row[1]} for i, row in enumerate(company_rows)]
        
        # Get unique source connectors with counts
        cursor.execute("""
            SELECT source_connector, COUNT(*) as count 
            FROM processed_records 
            WHERE source_connector IS NOT NULL AND source_connector != '' 
            GROUP BY source_connector 
            ORDER BY count DESC
        """)
        connector_rows = cursor.fetchall()
        connectors = [{"id": str(i+1), "name": row[0], "count": row[1]} for i, row in enumerate(connector_rows)]
        
        # Get status counts based on quality scores (using dynamic approval threshold)
        approval_threshold = get_threshold_value("approval_quality_score_threshold") or 50.0
        
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN status = 'approved' OR (status IS NULL AND CAST(quality_score AS REAL) >= ?) THEN 'approved'
                    WHEN status = 'flagged' OR (status IS NULL AND CAST(quality_score AS REAL) < ?) THEN 'flagged'
                    WHEN status = 'pending' THEN 'pending'
                    WHEN status = 'under_review' THEN 'under_review'
                    WHEN status = 'rejected' THEN 'rejected'
                    ELSE 'pending'
                END as computed_status,
                COUNT(*) as count
            FROM processed_records 
            GROUP BY computed_status
        """, (approval_threshold, approval_threshold))
        status_rows = cursor.fetchall()
        
        status_labels = {
            'approved': 'Approved',
            'flagged': 'Flagged', 
            'pending': 'Pending',
            'under_review': 'Under Review',
            'rejected': 'Rejected'
        }
        statuses = [{"value": row[0], "label": status_labels.get(row[0], row[0]), "count": row[1]} for row in status_rows]
        
        # Get priority counts based on quality scores
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN CAST(quality_score AS REAL) >= 80 THEN 'low'
                    WHEN CAST(quality_score AS REAL) >= 60 THEN 'medium'
                    WHEN CAST(quality_score AS REAL) >= 40 THEN 'high'
                    ELSE 'critical'
                END as computed_priority,
                COUNT(*) as count
            FROM processed_records 
            GROUP BY computed_priority
        """)
        priority_rows = cursor.fetchall()
        
        priority_labels = {
            'low': 'Low',
            'medium': 'Medium',
            'high': 'High',
            'critical': 'Critical'
        }
        priorities = [{"value": row[0], "label": priority_labels.get(row[0], row[0]), "count": row[1]} for row in priority_rows]
        
        # Get issue types from quality checks (mock for now since structure is complex)
        issue_types = [
            {"value": "context_coherence", "label": "Context Coherence", "count": 45},
            {"value": "domain_relevance", "label": "Domain Relevance", "count": 32},
            {"value": "semantic_relevance", "label": "Semantic Relevance", "count": 28},
            {"value": "duplicate_content_detection", "label": "Duplicate Content", "count": 15},
            {"value": "tag_specificity", "label": "Tag Specificity", "count": 12},
            {"value": "empty_tags", "label": "Empty Tags", "count": 8},
        ]
        
        conn.close()
        
        return {
            "companies": companies,
            "connectors": connectors,
            "statuses": statuses,
            "priorities": priorities,
            "issue_types": issue_types
        }
        
    except Exception as e:
        print(f"Error getting filter options: {e}")
        # Fallback to demo data if database fails
        return {
            "companies": [
                {"id": "1", "name": "Unknown Company", "count": 111}
            ],
            "connectors": [
                {"id": "1", "name": "SharePoint", "count": 85},
                {"id": "2", "name": "SharePoint Integration", "count": 26}
            ],
            "statuses": [
                {"value": "approved", "label": "Approved", "count": 67},
                {"value": "flagged", "label": "Flagged", "count": 44}
            ],
            "priorities": [
                {"value": "medium", "label": "Medium", "count": 78},
                {"value": "high", "label": "High", "count": 33}
            ],
            "issue_types": [
                {"value": "context_coherence", "label": "Context Coherence", "count": 45}
            ]
        }

@app.get("/records/filter-options")
async def get_records_filter_options():
    """Get filter options for the records page (frontend compatible format)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get unique companies with counts
        cursor.execute("""
            SELECT company, COUNT(*) as count 
            FROM processed_records 
            WHERE company IS NOT NULL AND company != '' 
            GROUP BY company 
            ORDER BY count DESC
        """)
        company_rows = cursor.fetchall()
        companies = [{"value": row[0], "label": row[0]} for row in company_rows]
        
        # Get unique source connectors with counts
        cursor.execute("""
            SELECT source_connector, COUNT(*) as count 
            FROM processed_records 
            WHERE source_connector IS NOT NULL AND source_connector != '' 
            GROUP BY source_connector 
            ORDER BY count DESC
        """)
        connector_rows = cursor.fetchall()
        connectors = [{"value": row[0], "label": row[0]} for row in connector_rows]
        
        # Get unique tags (flattened) with counts
        cursor.execute("SELECT tags FROM processed_records WHERE tags IS NOT NULL AND tags != ''")
        tag_rows = cursor.fetchall()
        tag_counts = {}
        
        for row in tag_rows:
            try:
                if row[0] and row[0] != 'null':
                    tags = json.loads(row[0]) if row[0].startswith('[') else [row[0]]
                    for tag in tags:
                        tag = tag.strip()
                        if tag:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except Exception:
                continue
        
        # Sort tags by count and take top 50
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:50]
        tags = [{"value": tag, "label": tag} for tag, count in sorted_tags]
        
        # Dynamic statuses based on actual current status from audit trails
        approval_threshold = get_threshold_value("approval_quality_score_threshold") or (float(settings.approval_quality_score_threshold) if settings else 50.0)
        
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN manual_review_status IS NOT NULL AND manual_review_status != 'pending' AND 
                         manual_review_status LIKE '%status_change%' THEN
                        (
                            SELECT json_extract(value, '$.status_change.new')
                            FROM json_each(manual_review_status)
                            WHERE json_extract(value, '$.status_change') IS NOT NULL
                            ORDER BY json_extract(value, '$.timestamp') DESC
                            LIMIT 1
                        )
                    WHEN CAST(quality_score AS REAL) >= ? THEN 'approved'
                    ELSE 'flagged'
                END as current_status, 
                COUNT(*) as count 
            FROM processed_records 
            GROUP BY current_status
            HAVING current_status IS NOT NULL
            ORDER BY count DESC
        """, (approval_threshold,))
        status_rows = cursor.fetchall()
        statuses = [{"value": row[0], "label": row[0].title(), "count": row[1]} for row in status_rows]
        
        priorities = [
            {"value": "low", "label": "Low"},
            {"value": "medium", "label": "Medium"},
            {"value": "high", "label": "High"},
            {"value": "critical", "label": "Critical"}
        ]
        
        conn.close()
        
        return {
            'companies': companies,
            'connectors': connectors,
            'tags': tags,
            'statuses': statuses,
            'priorities': priorities
        }
        
    except Exception as e:
        print(f"Error getting filter options: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to get filter options: {str(e)}"})

@app.get("/redteam/results")
async def get_redteam_results():
    """Get red team testing results"""
    return JSONResponse({
        "success": True,
        "total_tests": len(redteam_results),
        "results": redteam_results[-20:]  # Return last 20 red team tests
    })

@app.get("/evaluation/metrics")
async def get_evaluation_metrics():
    """Get system evaluation metrics and performance trends"""
    global evaluation_metrics
    
    # Calculate performance statistics
    metrics_summary = {}
    
    for methodology, performances in evaluation_metrics['methodology_performance'].items():
        if performances:
            scores = [p['score'] for p in performances]
            confidences = [p['confidence'] for p in performances]
            
            metrics_summary[methodology] = {
                'total_analyses': len(performances),
                'avg_quality_score': sum(scores) / len(scores),
                'avg_confidence': sum(confidences) / len(confidences),
                'score_std': (sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores))**0.5,
                'recent_performance': performances[-10:]  # Last 10 analyses
            }
    
    return JSONResponse({
        "success": True,
        "total_analyses": evaluation_metrics['total_analyses'],
        "methodology_performance": metrics_summary,
        "user_feedback_count": len(evaluation_metrics['user_feedback']),
        "recommendations": generate_improvement_recommendations(metrics_summary)
    })

def generate_improvement_recommendations(metrics_summary: Dict) -> List[str]:
    """Generate recommendations based on performance metrics"""
    recommendations = []
    
    for methodology, stats in metrics_summary.items():
        if stats['avg_confidence'] < 0.7:
            recommendations.append(f"Consider improving {methodology} - low confidence ({stats['avg_confidence']:.2f})")
        
        if stats['score_std'] > 15:
            recommendations.append(f"{methodology} shows high variance - consider prompt refinement")
        
        if stats['avg_quality_score'] < 70:
            recommendations.append(f"{methodology} producing low scores - review constraint weights")
    
    if not recommendations:
        recommendations.append("System performing well - consider A/B testing new methodologies")
    
    return recommendations

# Alert management endpoints
@app.get("/alerts/emails")
async def get_alert_emails():
    """Get current alert email recipients (To/CC)"""
    if not ALERT_MANAGER_AVAILABLE or not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
    
    to_list, cc_list = alert_manager.get_email_recipients()
    return {"to": to_list, "cc": cc_list}

@app.post("/alerts/emails")
async def add_alert_email(email: str, typ: str = "to"):
    """Add an alert email recipient (To/CC)"""
    if not ALERT_MANAGER_AVAILABLE or not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
    
    if typ not in ['to', 'cc']:
        raise HTTPException(status_code=400, detail="Type must be 'to' or 'cc'")
    
    alert_manager.add_email_recipient(email, typ)
    return {"status": "added", "email": email, "type": typ}

@app.delete("/alerts/emails")
async def remove_alert_email(email: str, typ: str = "to"):
    """Remove an alert email recipient (To/CC)"""
    if not ALERT_MANAGER_AVAILABLE or not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
    
    if typ not in ['to', 'cc']:
        raise HTTPException(status_code=400, detail="Type must be 'to' or 'cc'")
    
    alert_manager.remove_email_recipient(email, typ)
    return {"status": "removed", "email": email, "type": typ}

@app.put("/alerts/emails")
async def set_alert_emails(to_list: List[str], cc_list: List[str]):
    """Set all alert email recipients (To/CC)"""
    if not ALERT_MANAGER_AVAILABLE or not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
    
    alert_manager.set_email_recipients(to_list, cc_list)
    return {"status": "updated", "to": to_list, "cc": cc_list}

@app.get("/alerts/template")
async def get_alert_template():
    """Get current alert email template"""
    if not ALERT_MANAGER_AVAILABLE or not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
    
    template = alert_manager.get_alert_template()
    return template

@app.put("/alerts/template")
async def set_alert_template(subject: str, body: str):
    """Set alert email template"""
    if not ALERT_MANAGER_AVAILABLE or not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
    
    alert_manager.set_alert_template(subject, body)
    return {"status": "updated", "subject": subject, "body": body}

@app.post("/alerts/test")
async def test_alert():
    """Send a test alert to verify configuration"""
    if not ALERT_MANAGER_AVAILABLE or not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
    
    try:
        await alert_manager.send_alert(
            alert_type=AlertType.SYSTEM_ERROR,
            severity=AlertSeverity.MEDIUM,
            message="This is a test alert to verify your alert configuration",
            details={"test": True, "timestamp": datetime.now(UTC).isoformat()},
            trace_id="test-trace-id",
            record_id="test-record-id"
        )
        return {"status": "test_alert_sent", "message": "Test alert sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test alert: {str(e)}")

@app.get("/test")
async def self_test():
    """Self-test endpoint to verify system functionality"""
    tests = []
    
    # Test rules engine
    if RULES_ENGINE_AVAILABLE:
        try:
            # Test with good content
            test_request = RulesCheckRequest(
                document_text="This is a comprehensive guide about software development best practices.",
                tags=["software", "development", "best-practices"],
                source_connector="sharepoint"
            )
            result = await check_rules_only(test_request)
            tests.append({
                "test": "rules_engine_good_content",
                "status": "PASS",
                "details": "Rules engine processed good content successfully"
            })
        except Exception as e:
            tests.append({
                "test": "rules_engine_good_content", 
                "status": "FAIL",
                "details": f"Error: {str(e)}"
            })
    else:
        tests.append({
            "test": "rules_engine",
            "status": "SKIP",
            "details": "Rules engine not available"
        })
    
    # Test LLM endpoint
    try:
        test_llm = LLMAnalysisRequest(
            content="Test content for LLM analysis",
            tags=["test", "analysis"],
            context={"source": "test"}
        )
        result = await llm_analysis(test_llm)
        tests.append({
            "test": "llm_analysis",
            "status": "PASS",
            "details": "LLM analysis endpoint working"
        })
    except Exception as e:
        tests.append({
            "test": "llm_analysis",
            "status": "FAIL", 
            "details": f"Error: {str(e)}"
        })
    

    
    # Test red team
    try:
        test_redteam = RedTeamRequest(
            scenario_id="test_scenario",
            content="test content",
            tags=["generic"],
            test_objectives=["Test system"]
        )
        result = await redteam_analysis(test_redteam)
        tests.append({
            "test": "redteam_analysis",
            "status": "PASS",
            "details": "Red team testing working"
        })
    except Exception as e:
        tests.append({
            "test": "redteam_analysis",
            "status": "FAIL",
            "details": f"Error: {str(e)}"
        })
    
    all_passed = all(test["status"] in ["PASS", "SKIP"] for test in tests)
    
    return JSONResponse({
        "success": all_passed,
        "overall_status": "HEALTHY" if all_passed else "ISSUES_FOUND",
        "tests": tests,
        "timestamp": datetime.now(UTC).isoformat(),
        "system_info": {
            "rules_engine_available": RULES_ENGINE_AVAILABLE,
            "total_processed": processed_count,
            "llm_processed": llm_processed_count,
            "redteam_tests": len(redteam_results),
            "uptime_seconds": (datetime.now(UTC) - start_time).total_seconds()
        }
    })

def store_request_log(trace_id: str, endpoint: str, method: str, request_data: Dict, 
                     response_status: int, response_data: Dict, processing_time_ms: float,
                     error_message: Optional[str] = None, source_connector: Optional[str] = None):
    """Store request log for tracking all requests"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO request_logs 
            (id, trace_id, endpoint, method, request_data, response_status, 
             response_data, processing_time_ms, error_message, created_at, 
             source_connector, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            trace_id,
            endpoint,
            method,
            json.dumps(request_data),
            response_status,
            json.dumps(response_data),
            processing_time_ms,
            error_message or "",
            datetime.now(UTC).isoformat(),
            source_connector or "",
            response_status < 400  # Success if status < 400
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error storing request log: {e}")

def store_quality_check(record_id: str, check_name: str, status: str, confidence_score: float,
                       failure_reason: Optional[str] = None, check_metadata: Optional[Dict] = None):
    """Store individual quality check result with enhanced structure"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Enhanced quality check structure with all fields
        enhanced_metadata = {
            "type": check_name,
            "severity": "high" if confidence_score < 0.3 else "medium" if confidence_score < 0.7 else "low",
            "description": failure_reason or f"{check_name} check completed",
            "suggestion": _generate_suggestion(check_name, failure_reason, check_metadata),
            "autoFixable": _is_auto_fixable(check_name),
            "category": _get_check_category(check_name),
            "confidence": confidence_score,
            "processing_time_ms": check_metadata.get('processing_time_ms', 0) if check_metadata else 0
        }
        
        # Add additional metadata if available
        if check_metadata:
            enhanced_metadata.update(check_metadata)
        
        # ✅ FIX: Delete existing quality check for this record_id + check_name combination
        # This prevents duplication when records are reprocessed
        cursor.execute('''
            DELETE FROM quality_checks 
            WHERE record_id = ? AND check_name = ?
        ''', (record_id, check_name))
        
        # Insert the new quality check
        cursor.execute('''
            INSERT INTO quality_checks 
            (id, record_id, check_name, status, confidence_score, failure_reason,
             check_metadata_json, executed_at, processing_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            record_id,
            check_name,
            status,
            confidence_score,
            failure_reason or "",
            json.dumps(enhanced_metadata),
            datetime.now(UTC).isoformat(),
            enhanced_metadata.get('processing_time_ms', 0)
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error storing quality check: {e}")

def _generate_suggestion(check_name: str, failure_reason: Optional[str], metadata: Optional[Dict]) -> str:
    """Generate helpful suggestions based on check type and failure reason"""
    suggestions = {
        "empty_tags": "Add meaningful tags to improve content categorization and discoverability",
        "tag_count_validation": "Adjust the number of tags - too few reduces discoverability, too many creates noise",
        "text_quality": "Improve content quality by adding more detailed and specific information",
        "stopwords_detection": "Replace generic terms with specific, descriptive tags that accurately represent the content",
        "spam_patterns": "Remove repetitive or low-quality content patterns",
        "duplicate_content": "Ensure content is unique and adds value to the knowledge base",
        "tag_text_relevance": "Align tags more closely with the actual content topics and themes",
        "llm_semantic_validation": "Improve alignment between content and tags for better semantic accuracy"
    }
    
    base_suggestion = suggestions.get(check_name, "Review and improve content quality")
    
    if failure_reason:
        return f"{base_suggestion}. {failure_reason}"
    
    return base_suggestion

def _is_auto_fixable(check_name: str) -> bool:
    """Determine if a quality check can be auto-fixed"""
    auto_fixable_checks = {
        "empty_tags": True,
        "tag_count_validation": True,
        "stopwords_detection": True,
        "tag_text_relevance": True,
        "llm_semantic_validation": True
    }
    
    return auto_fixable_checks.get(check_name, False)

def _get_check_category(check_name: str) -> str:
    """Get the category for a quality check"""
    categories = {
        "empty_tags": "Tagging",
        "tag_count_validation": "Tagging", 
        "text_quality": "Content",
        "stopwords_detection": "Tagging",
        "spam_patterns": "Content",
        "duplicate_content": "Content",
        "tag_text_relevance": "Tagging",
        "llm_semantic_validation": "Semantic"
    }
    
    return categories.get(check_name, "General")

@app.get("/request-logs")
async def get_request_logs(
    page: int = 1,
    page_size: int = 50,
    success_only: bool = False,
    endpoint: Optional[str] = None
):
    """Get request logs for monitoring and debugging"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        query = "SELECT * FROM request_logs WHERE 1=1"
        params = []
        
        if success_only:
            query += " AND success = 1"
        
        if endpoint:
            query += " AND endpoint = ?"
            params.append(endpoint)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        logs = []
        for row in rows:
            # Safely parse JSON with error handling
            try:
                request_data = json.loads(row[4]) if row[4] else {}
            except (json.JSONDecodeError, TypeError):
                request_data = {"error": "Invalid JSON data"}
            
            try:
                response_data = json.loads(row[6]) if row[6] else {}
            except (json.JSONDecodeError, TypeError):
                response_data = {"error": "Invalid JSON data"}
            
            logs.append({
                'id': row[0],
                'trace_id': row[1],
                'endpoint': row[2],
                'method': row[3],
                'request_data': request_data,
                'response_status': row[5],
                'response_data': response_data,
                'processing_time_ms': row[7],
                'error_message': row[8],
                'created_at': row[9],
                'source_connector': row[10],
                'success': bool(row[11])
            })
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM request_logs WHERE 1=1"
        count_params = []
        
        if success_only:
            count_query += " AND success = 1"
        
        if endpoint:
            count_query += " AND endpoint = ?"
            count_params.append(endpoint)
        
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "logs": logs,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch request logs: {str(e)}")

@app.get("/analytics/requests")
async def get_request_analytics():
    """Get analytics data about requests"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='request_logs'")
        if not cursor.fetchone():
            conn.close()
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "avg_processing_time": 0,
                "endpoint_breakdown": [],
                "error_breakdown": []
            }
        
        # Get basic stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                AVG(processing_time_ms) as avg_time
            FROM request_logs
        ''')
        
        stats = cursor.fetchone()
        
        # Get endpoint breakdown
        cursor.execute('''
            SELECT endpoint, COUNT(*) as count, AVG(processing_time_ms) as avg_time
            FROM request_logs 
            GROUP BY endpoint
            ORDER BY count DESC
        ''')
        
        endpoint_breakdown = cursor.fetchall()
        
        # Get error breakdown
        cursor.execute('''
            SELECT error_message, COUNT(*) as count
            FROM request_logs 
            WHERE success = 0 AND error_message != ''
            GROUP BY error_message
            ORDER BY count DESC
            LIMIT 10
        ''')
        
        error_breakdown = cursor.fetchall()
        
        conn.close()
        
        return {
            "total_requests": stats[0] if stats else 0,
            "successful_requests": stats[1] if stats else 0,
            "failed_requests": (stats[0] - stats[1]) if stats else 0,
            "avg_processing_time": round(stats[2], 2) if stats and stats[2] else 0,
            "endpoint_breakdown": [
                {
                    "endpoint": row[0],
                    "count": row[1],
                    "avg_time": round(row[2], 2) if row[2] else 0
                }
                for row in endpoint_breakdown
            ],
            "error_breakdown": [
                {
                    "error": row[0],
                    "count": row[1]
                }
                for row in error_breakdown
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch request analytics: {str(e)}")

# Add manual review models
class ManualReviewRequest(BaseModel):
    action: str  # "approve" or "reject"
    reviewer_comments: Optional[str] = None
    reviewer_id: str = "manual_reviewer"

# Dynamic Threshold Management Models
class ThresholdUpdateRequest(BaseModel):
    """Request model for updating thresholds dynamically"""
    threshold_name: str
    new_value: float
    reason: Optional[str] = None
    user_id: Optional[str] = "admin"

class ThresholdConfig(BaseModel):
    """Configuration model for a single threshold"""
    name: str
    current_value: float
    default_value: float
    min_value: float
    max_value: float
    description: str
    category: str  # "quality", "llm", "rules", "cost"
    unit: str  # "percentage", "score", "count", etc.

class ThresholdHistory(BaseModel):
    """History record for threshold changes"""
    threshold_name: str
    old_value: float
    new_value: float
    changed_by: str
    reason: Optional[str]
    timestamp: str

class ThresholdResponse(BaseModel):
    """Response model for threshold operations"""
    success: bool
    message: str
    threshold: Optional[ThresholdConfig] = None
    history: Optional[List[ThresholdHistory]] = None

# Global threshold management - MIGRATED TO UnifiedConfigService
# All threshold management is now handled by the UnifiedConfigService
# to eliminate conflicts and ensure single source of truth

def get_threshold_value(threshold_name: str) -> Optional[float]:
    """Get the current value of a threshold from the Unified Configuration Service"""
    try:
        from ..services.unified_config_service import get_unified_config_service
        config_service = get_unified_config_service()
        return config_service.get_threshold(threshold_name)
    except Exception as e:
        print(f"Warning: Failed to get threshold {threshold_name}: {e}")
        # Fallback to config.py directly
        try:
            settings = get_settings()
            return float(getattr(settings, threshold_name, None))
        except:
            return None

# Unified threshold management is now handled by UnifiedConfigService

# Unified Configuration Management Endpoints
@app.get("/thresholds")
async def get_all_thresholds():
    """Get all available thresholds from the unified configuration service"""
    try:
        from ..services.unified_config_service import get_unified_config_service
        config_service = get_unified_config_service()
        thresholds_data = config_service.get_all_thresholds()
        
        # Convert to list format for frontend compatibility
        thresholds = []
        for name, data in thresholds_data.items():
            thresholds.append(data)
        
        return {
            "success": True,
            "thresholds": thresholds,
            "total_count": len(thresholds)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get thresholds: {str(e)}")

@app.get("/thresholds/{threshold_name}")
async def get_threshold(threshold_name: str):
    """Get a specific threshold configuration from unified service"""
    try:
        from ..services.unified_config_service import get_unified_config_service
        config_service = get_unified_config_service()
        
        value = config_service.get_threshold(threshold_name)
        if value is None:
            raise HTTPException(status_code=404, detail="Threshold not found")
        
        # Get full threshold data
        all_thresholds = config_service.get_all_thresholds()
        if threshold_name not in all_thresholds:
            raise HTTPException(status_code=404, detail="Threshold metadata not found")
        
        threshold_data = all_thresholds[threshold_name]
        
        return {
            "success": True,
            "message": "Threshold retrieved successfully",
            "threshold": threshold_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get threshold: {str(e)}")

@app.put("/thresholds/{threshold_name}")
async def update_threshold_endpoint(threshold_name: str, request: ThresholdUpdateRequest):
    """Update a threshold value using the unified configuration service"""
    try:
        from ..services.unified_config_service import get_unified_config_service, ThresholdUpdate
        config_service = get_unified_config_service()
        
        # Use the threshold_name from URL path, ignore the one in request body if present
        # This maintains backward compatibility while using the REST-style URL
        actual_threshold_name = threshold_name
        
        # Create update request
        update = ThresholdUpdate(
            name=actual_threshold_name,
            value=float(request.new_value),
            updated_by=request.user_id or "admin",
            reason=request.reason or "Updated via API"
        )
        
        # Update threshold
        success = config_service.update_threshold(update)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update threshold")
        
        # Get updated threshold data
        updated_value = config_service.get_threshold(actual_threshold_name)
        
        # Notify rules engine to reload thresholds for real-time effect
        try:
            if 'rules_engine' in globals() and rules_engine is not None:
                print(f"🔄 Triggering rules engine threshold reload for {actual_threshold_name}...")
                rules_engine.reload_thresholds()
                print(f"✅ Rules engine reload completed")
        except Exception as e:
            print(f"⚠️ Failed to reload rules engine thresholds: {e}")
        
        return {
            "success": True,
            "message": f"Threshold updated: {actual_threshold_name} = {updated_value}",
            "threshold": {
                "name": actual_threshold_name,
                "current_value": updated_value,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update threshold: {str(e)}")

@app.post("/thresholds/{threshold_name}/reset")
async def reset_threshold_endpoint(threshold_name: str, user_id: str = "admin"):
    """Reset a threshold to its default value"""
    try:
        if threshold_name not in dynamic_thresholds:
            raise HTTPException(status_code=404, detail="Threshold not found")
        
        success = reset_threshold_to_default(threshold_name, user_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to reset threshold")
        
        # Get updated threshold config
        config = dynamic_thresholds[threshold_name]
        threshold = ThresholdConfig(
            name=threshold_name,
            current_value=config["current_value"],
            default_value=config["default_value"],
            min_value=config["min_value"],
            max_value=config["max_value"],
            description=config["description"],
            category=config["category"],
            unit=config["unit"]
        )
        
        return ThresholdResponse(
            success=True,
            message=f"Threshold '{threshold_name}' reset to default value {config['default_value']}",
            threshold=threshold
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset threshold: {str(e)}")

@app.get("/thresholds/{threshold_name}/history")
async def get_threshold_history(threshold_name: str, limit: int = 20):
    """Get history of changes for a specific threshold"""
    try:
        if threshold_name not in dynamic_thresholds:
            raise HTTPException(status_code=404, detail="Threshold not found")
        
        # Filter history for this threshold
        threshold_history_filtered = [
            entry for entry in threshold_history 
            if entry.threshold_name == threshold_name
        ]
        
        # Sort by timestamp (newest first) and limit results
        threshold_history_filtered.sort(key=lambda x: x.timestamp, reverse=True)
        threshold_history_filtered = threshold_history_filtered[:limit]
        
        return {
            "success": True,
            "threshold_name": threshold_name,
            "history": threshold_history_filtered,
            "total_changes": len(threshold_history_filtered)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get threshold history: {str(e)}")

@app.get("/thresholds/categories/{category}")
async def get_thresholds_by_category(category: str):
    """Get all thresholds in a specific category"""
    try:
        thresholds = []
        for name, config in dynamic_thresholds.items():
            if config["category"] == category:
                threshold = ThresholdConfig(
                    name=name,
                    current_value=config["current_value"],
                    default_value=config["default_value"],
                    min_value=config["min_value"],
                    max_value=config["max_value"],
                    description=config["description"],
                    category=config["category"],
                    unit=config["unit"]
                )
                thresholds.append(threshold)
        
        return {
            "success": True,
            "category": category,
            "thresholds": thresholds,
            "total_count": len(thresholds)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get thresholds by category: {str(e)}")

@app.post("/thresholds/bulk-update")
async def bulk_update_thresholds(updates: List[ThresholdUpdateRequest]):
    """Update multiple thresholds at once"""
    try:
        results = []
        success_count = 0
        
        for update in updates:
            try:
                if update.threshold_name not in dynamic_thresholds:
                    results.append({
                        "threshold_name": update.threshold_name,
                        "success": False,
                        "error": "Threshold not found"
                    })
                    continue
                
                success = update_threshold(
                    threshold_name=update.threshold_name,
                    new_value=update.new_value,
                    user_id=update.user_id or "admin",
                    reason=update.reason
                )
                
                if success:
                    success_count += 1
                    results.append({
                        "threshold_name": update.threshold_name,
                        "success": True,
                        "new_value": update.new_value
                    })
                else:
                    config = dynamic_thresholds[update.threshold_name]
                    results.append({
                        "threshold_name": update.threshold_name,
                        "success": False,
                        "error": f"Invalid value. Must be between {config['min_value']} and {config['max_value']}"
                    })
                    
            except Exception as e:
                results.append({
                    "threshold_name": update.threshold_name,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": f"Bulk update completed. {success_count}/{len(updates)} thresholds updated successfully",
            "results": results,
            "success_count": success_count,
            "total_count": len(updates)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to perform bulk update: {str(e)}")

@app.post("/llm/tag-suggestions")
async def get_tag_suggestions(request: Dict[str, Any]):
    """Get LLM-powered tag suggestions for content using real OpenAI API"""
    try:
        content = request.get("content", "")
        current_tags = request.get("current_tags", [])
        
        if not content.strip():
            raise HTTPException(status_code=400, detail="Content is required")
        

        
        try:
            # Use LLM judge to generate tag suggestions using real OpenAI API
            result = await llm_judge.generate_tag_suggestions(content, current_tags)
            return result
            
        except Exception as e:
            print(f"LLM tag suggestions error: {e}")
            return {
                "success": False,
                "suggestions": [],
                "confidence_score": 0.0,
                "reasoning": f"Error generating tag suggestions: {str(e)}",
                "provider": "error"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tag suggestions: {str(e)}")

# Email Alert Management System
# =============================

# In-memory storage for email alerts
email_templates = {}
email_recipients = {}
email_settings = {
    "enabled": True,
    "real_time": True,
    "batch_frequency": 15,
    "max_emails_per_hour": 100,
    "include_record_details": True,
    "include_quality_scores": True,
    "include_llm_suggestions": True
}

# Email template models
class EmailTemplate(BaseModel):
    id: Optional[str] = None
    name: str
    subject: str
    body: str
    type: str  # "flagged", "under_review", "approved", "rejected"
    is_active: bool = True
    created_at: Optional[str] = None

class EmailRecipient(BaseModel):
    id: Optional[str] = None
    email: str
    name: str
    role: str
    alert_types: List[str]  # ["flagged", "under_review", "approved", "rejected"]
    is_active: bool = True
    created_at: Optional[str] = None

class AlertSettings(BaseModel):
    enabled: bool = True
    real_time: bool = True
    batch_frequency: int = 15
    max_emails_per_hour: int = 100
    include_record_details: bool = True
    include_quality_scores: bool = True
    include_llm_suggestions: bool = True

# Initialize sample email templates
def initialize_email_templates():
    global email_templates
    email_templates = {
        "1": {
            "id": "1",
            "name": "Flagged Record Alert",
            "subject": "🚨 Quality Issue Detected - Record #{record_id}",
            "body": """Hi {recipient_name},

A record has been flagged for quality review:

**Record Details:**
- ID: {record_id}
- Company: {company_name}
- Source: {source_connector}
- Quality Score: {quality_score}%

**Issues Found:**
{quality_issues}

**LLM Suggestions:**
{llm_suggestions}

Please review this record at your earliest convenience.

Best regards,
Indexing QA System""",
            "type": "flagged",
            "is_active": True,
            "created_at": "2024-01-15T10:00:00Z"
        },
        "2": {
            "id": "2",
            "name": "Medium Quality Records Notification",
            "subject": "📋 Record Medium Quality Records - #{record_id}",
            "body": """Hi {recipient_name},

A record is currently under review:

**Record Details:**
- ID: {record_id}
- Company: {company_name}
- Status: Medium Quality Records
- Reviewer: {reviewer_name}

**Review Notes:**
{review_notes}

You will be notified once the review is complete.

Best regards,
Indexing QA System""",
            "type": "under_review",
            "is_active": True,
            "created_at": "2024-01-15T10:00:00Z"
        }
    }

# Initialize sample email recipients
def initialize_email_recipients():
    global email_recipients
    email_recipients = {
        "1": {
            "id": "1",
            "email": "admin@company.com",
            "name": "System Administrator",
            "role": "Admin",
            "alert_types": ["flagged", "under_review", "approved", "rejected"],
            "is_active": True,
            "created_at": "2024-01-15T10:00:00Z"
        },
        "2": {
            "id": "2",
            "email": "qa-team@company.com",
            "name": "QA Team",
            "role": "QA Manager",
            "alert_types": ["flagged", "under_review"],
            "is_active": True,
            "created_at": "2024-01-15T10:00:00Z"
        }
    }

# Initialize email system
initialize_email_templates()
initialize_email_recipients()

# Email Template Endpoints
@app.get("/email/templates")
async def get_email_templates():
    """Get all email templates"""
    try:
        templates = list(email_templates.values())
        return {
            "success": True,
            "templates": templates,
            "total_count": len(templates)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")

@app.post("/email/templates")
async def create_email_template(template: EmailTemplate):
    """Create a new email template"""
    try:
        template_id = str(len(email_templates) + 1)
        template.id = template_id
        template.created_at = datetime.now().isoformat()
        
        email_templates[template_id] = template.dict()
        
        return {
            "success": True,
            "message": "Template created successfully",
            "template": email_templates[template_id]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")

@app.put("/email/templates")
async def update_email_template(template: EmailTemplate):
    """Update an existing email template"""
    try:
        if not template.id or template.id not in email_templates:
            raise HTTPException(status_code=404, detail="Template not found")
        
        email_templates[template.id] = template.dict()
        
        return {
            "success": True,
            "message": "Template updated successfully",
            "template": email_templates[template.id]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")

@app.delete("/email/templates/{template_id}")
async def delete_email_template(template_id: str):
    """Delete an email template"""
    try:
        if template_id not in email_templates:
            raise HTTPException(status_code=404, detail="Template not found")
        
        del email_templates[template_id]
        
        return {
            "success": True,
            "message": "Template deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")

# Email Recipients Endpoints
@app.get("/email/recipients")
async def get_email_recipients():
    """Get all email recipients"""
    try:
        recipients = list(email_recipients.values())
        return {
            "success": True,
            "recipients": recipients,
            "total_count": len(recipients)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recipients: {str(e)}")

@app.post("/email/recipients")
async def create_email_recipient(recipient: EmailRecipient):
    """Create a new email recipient"""
    try:
        recipient_id = str(len(email_recipients) + 1)
        recipient.id = recipient_id
        recipient.created_at = datetime.now().isoformat()
        
        email_recipients[recipient_id] = recipient.dict()
        
        return {
            "success": True,
            "message": "Recipient created successfully",
            "recipient": email_recipients[recipient_id]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create recipient: {str(e)}")

@app.put("/email/recipients")
async def update_email_recipient(recipient: EmailRecipient):
    """Update an existing email recipient"""
    try:
        if not recipient.id or recipient.id not in email_recipients:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        email_recipients[recipient.id] = recipient.dict()
        
        return {
            "success": True,
            "message": "Recipient updated successfully",
            "recipient": email_recipients[recipient.id]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update recipient: {str(e)}")

@app.delete("/email/recipients/{recipient_id}")
async def delete_email_recipient(recipient_id: str):
    """Delete an email recipient"""
    try:
        if recipient_id not in email_recipients:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        del email_recipients[recipient_id]
        
        return {
            "success": True,
            "message": "Recipient deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete recipient: {str(e)}")

# Email Settings Endpoints
@app.get("/email/settings")
async def get_email_settings():
    """Get email alert settings"""
    try:
        return {
            "success": True,
            "settings": email_settings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")

@app.put("/email/settings")
async def update_email_settings(settings: AlertSettings):
    """Update email alert settings"""
    try:
        global email_settings
        email_settings = settings.dict()
        
        return {
            "success": True,
            "message": "Settings updated successfully",
            "settings": email_settings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")

# Test Email Endpoint
@app.post("/email/test/{recipient_id}")
async def test_email(recipient_id: str):
    """Send a test email to a recipient"""
    try:
        if recipient_id not in email_recipients:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        recipient = email_recipients[recipient_id]
        
        # Simulate sending test email
        test_data = {
            "recipient_name": recipient["name"],
            "record_id": "TEST-001",
            "company_name": "Test Company",
            "source_connector": "SharePoint",
            "quality_score": 85,
            "quality_issues": "Sample quality issues for testing",
            "llm_suggestions": "Sample LLM suggestions for testing"
        }
        
        # In a real implementation, this would send an actual email
        print(f"TEST EMAIL SENT to {recipient['email']}:")
        print(f"Subject: Test Email from Indexing QA System")
        print(f"Body: This is a test email to verify email alert functionality.")
        print(f"Recipient: {recipient['name']} ({recipient['email']})")
        
        return {
            "success": True,
            "message": f"Test email sent successfully to {recipient['email']}",
            "recipient": recipient,
            "test_data": test_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test email: {str(e)}")

# Send Alert Email Function
def send_alert_email(record_data: Dict, alert_type: str, recipients: List[str] = None):
    """Send alert emails for flagged or under review records"""
    try:
        if not email_settings["enabled"]:
            return
        
        # Get template for alert type
        template = None
        for t in email_templates.values():
            if t["type"] == alert_type and t["is_active"]:
                template = t
                break
        
        if not template:
            print(f"No active template found for alert type: {alert_type}")
            return
        
        # Get recipients for this alert type
        if not recipients:
            recipients = []
            for r in email_recipients.values():
                if r["is_active"] and alert_type in r["alert_types"]:
                    recipients.append(r["email"])
        
        if not recipients:
            print(f"No recipients found for alert type: {alert_type}")
            return
        
        # Prepare email content
        subject = template["subject"]
        body = template["body"]
        
        # Replace placeholders with actual data
        replacements = {
            "{record_id}": record_data.get("record_id", "Unknown"),
            "{company_name}": record_data.get("company", "Unknown"),
            "{source_connector}": record_data.get("source_type", "Unknown"),
            "{quality_score}": str(record_data.get("quality_score", 0)),
            "{quality_issues}": record_data.get("quality_issues", "No issues found"),
            "{llm_suggestions}": record_data.get("llm_suggestions", "No suggestions available"),
            "{reviewer_name}": record_data.get("reviewer_name", "System"),
            "{review_notes}": record_data.get("review_notes", "No notes available")
        }
        
        for placeholder, value in replacements.items():
            subject = subject.replace(placeholder, value)
            body = body.replace(placeholder, value)
        
        # In a real implementation, this would send actual emails
        print(f"ALERT EMAIL SENT:")
        print(f"Type: {alert_type}")
        print(f"Subject: {subject}")
        print(f"Recipients: {recipients}")
        print(f"Body: {body[:200]}...")
        
        return True
    except Exception as e:
        print(f"Failed to send alert email: {str(e)}")
        return False

# Add these new endpoints after the existing endpoints

# ===============================
# IMPROVED PIPELINE ENDPOINTS
# ===============================

class RecordStatus(str, Enum):
    """Clear record status definitions"""
    APPROVED = "approved"
    FLAGGED = "flagged"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"

class ReviewAction(str, Enum):
    """Reviewer actions"""
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
    ESCALATE = "escalate"

class ReviewRequest(BaseModel):
    """Review request model"""
    action: ReviewAction
    reviewer_id: str
    comments: Optional[str] = None
    estimated_fix_time: Optional[int] = None

def make_quality_decision(quality_score: float, issues: List[Dict]) -> str:
    """Make binary APPROVED/FLAGGED decision based on quality"""
    # Get approval threshold from dynamic system
    approval_threshold = get_threshold_value("approval_quality_score_threshold") or 50.0
    
    critical_issues = [i for i in issues if i.get('severity') == 'critical']
    
    if float(quality_score) >= approval_threshold and not critical_issues:
        return RecordStatus.APPROVED
    else:
        return RecordStatus.FLAGGED

@app.get("/production/approved")
async def get_approved_records(
    page: int = 1,
    pageSize: int = 25,
    companies: Optional[str] = None,
    sourceConnectors: Optional[str] = None,
    tags: Optional[str] = None,
    searchQuery: Optional[str] = None
):
    """
    PRODUCTION DASHBOARD - Only approved, production-ready records
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get approval threshold from dynamic system
        approval_threshold = get_threshold_value("approval_quality_score_threshold") or 50.0
        
        # Base query for approved records only
        query = """
            SELECT id, record_id, title, content, tags, source_connector, company,
                   quality_score, created_at, content_metadata
            FROM processed_records 
            WHERE (status = 'approved' OR (status IS NULL AND CAST(quality_score AS REAL) >= ?))
        """
        params: list = [approval_threshold]
        
        # Add filters
        if companies:
            companies_list = companies.split(',')
            placeholders = ','.join(['?' for _ in companies_list])
            query += f" AND company IN ({placeholders})"
            params.extend(companies_list)
        
        if sourceConnectors:
            connectors_list = sourceConnectors.split(',')
            placeholders = ','.join(['?' for _ in connectors_list])
            query += f" AND source_connector IN ({placeholders})"
            params.extend(connectors_list)
        
        if searchQuery:
            query += " AND (title LIKE ? OR content LIKE ?)"
            params.extend([f'%{searchQuery}%', f'%{searchQuery}%'])
        
        # Add pagination
        offset = (page - 1) * pageSize
        query += f" ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([pageSize, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            records.append({
                'id': row[0],
                'recordId': row[1],
                'title': row[2],
                'content': row[3][:200] + '...' if len(row[3]) > 200 else row[3],
                'tags': json.loads(row[4]) if row[4] else [],
                'sourceConnector': row[5],
                'company': row[6],
                'qualityScore': row[7],
                'createdAt': row[8],
                'status': 'approved',
                'metadata': json.loads(row[9]) if row[9] else {}
            })
        
        # Get total count
        count_query = query.split('ORDER BY')[0].replace('SELECT id, record_id, title, content, tags, source_connector, company, quality_score, created_at, content_metadata', 'SELECT COUNT(*)')
        count_params = params[:-2]  # Remove the LIMIT and OFFSET parameters
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'records': records,
            'pagination': {
                'page': page,
                'pageSize': pageSize,
                'total': total,
                'totalPages': (total + pageSize - 1) // pageSize
            },
            'summary': {
                'totalApproved': total,
                'avgQualityScore': sum(r['qualityScore'] for r in records) / len(records) if records else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch approved records: {str(e)}")

@app.get("/review/queue")
async def get_review_queue(priority: Optional[str] = None, assigned_to: Optional[str] = None):
    """
    REVIEW QUEUE - Flagged records needing human review
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get approval threshold from dynamic system  
        approval_threshold = get_threshold_value("approval_quality_score_threshold") or 50.0
        
        # Get flagged records with issues
        query = """
            SELECT id, record_id, title, content, tags, source_connector, company,
                   quality_score, quality_checks, created_at, status, manual_review_status
            FROM processed_records 
            WHERE (status = 'flagged' OR (status IS NULL AND CAST(quality_score AS REAL) < ?))
        """
        params: list = [approval_threshold]
        
        if assigned_to:
            query += " AND manual_review_status LIKE ?"
            params.append(f'%{assigned_to}%')
        
        cursor.execute(query, params)
        
        rows = cursor.fetchall()
        
        review_items = []
        for row in rows:
            # Parse quality checks to extract issues
            quality_checks = json.loads(row[8]) if row[8] else []
            issues = []
            severity = 'medium'
            
            for check in quality_checks:
                if check.get('status') == 'fail':
                    issues.append({
                        'type': check.get('check_name', 'unknown'),
                        'description': check.get('failure_reason', 'Quality check failed'),
                        'autoFixable': check.get('check_name') in ['empty_tags', 'tag_count_validation', 'stopwords_detection']
                    })
            
            # Determine severity
            if row[7] < 50:  # quality_score
                severity = 'critical'
            elif row[7] < 70:
                severity = 'high'
            
            # Calculate priority (lower number = higher priority)
            priority_score = 1 if severity == 'critical' else (2 if severity == 'high' else 3)
            
            review_items.append({
                'id': row[0],
                'recordId': row[1],
                'title': row[2],
                'content': row[3][:300] + '...' if len(row[3]) > 300 else row[3],
                'tags': json.loads(row[4]) if row[4] else [],
                'sourceConnector': row[5],
                'company': row[6],
                'qualityScore': row[7],
                'severity': severity,
                'priority': priority_score,
                'issues': issues,
                'issueCount': len(issues),
                'createdAt': row[9],
                'status': 'flagged',
                'reviewStatus': row[11] or 'pending',
                'estimatedReviewTime': 5 + (5 if severity == 'critical' else 2),
                'autoFixSuggestions': _generate_auto_fix_suggestions(issues)
            })
        
        # Sort by priority (critical first) then by creation date
        review_items.sort(key=lambda x: (x['priority'], x['createdAt']))
        
        # Filter by priority if specified
        if priority:
            priority_map = {'critical': 1, 'high': 2, 'medium': 3}
            target_priority = priority_map.get(priority.lower(), 3)
            review_items = [item for item in review_items if item['priority'] == target_priority]
        
        conn.close()
        
        return {
            'reviewQueue': review_items,
            'summary': {
                'totalFlagged': len(review_items),
                'critical': len([item for item in review_items if item['severity'] == 'critical']),
                'high': len([item for item in review_items if item['severity'] == 'high']),
                'medium': len([item for item in review_items if item['severity'] == 'medium']),
                'estimatedTotalTime': sum(item['estimatedReviewTime'] for item in review_items)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch review queue: {str(e)}")

def _generate_auto_fix_suggestions(issues: List[Dict]) -> List[str]:
    """Generate auto-fix suggestions based on issues"""
    suggestions = []
    for issue in issues:
        if issue.get('autoFixable'):
            if 'tag' in issue['type']:
                suggestions.append("Add more specific, descriptive tags")
            elif 'spam' in issue['type']:
                suggestions.append("Remove test/spam content")
            elif 'duplicate' in issue['type']:
                suggestions.append("Check for duplicate content")
    return suggestions

@app.post("/review/process/{record_id}")
async def process_review(record_id: str, review: ReviewRequest):
    """
    Process human review decision for flagged record
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get the record
        cursor.execute("SELECT * FROM processed_records WHERE id = ? OR record_id = ?", (record_id, record_id))
        record = cursor.fetchone()
        
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Update record based on review decision
        new_status = None
        review_notes = {
            'reviewer_id': review.reviewer_id,
            'action': review.action,
            'comments': review.comments,
            'reviewed_at': datetime.now(UTC).isoformat(),
            'estimated_fix_time': review.estimated_fix_time
        }
        
        if review.action == ReviewAction.APPROVE:
            new_status = RecordStatus.APPROVED
        elif review.action == ReviewAction.REJECT:
            new_status = RecordStatus.REJECTED
        elif review.action == ReviewAction.REQUEST_CHANGES:
            new_status = RecordStatus.PENDING_REVIEW
        elif review.action == ReviewAction.ESCALATE:
            new_status = RecordStatus.PENDING_REVIEW
            review_notes['escalated'] = True
        
        # Update database
        cursor.execute("""
            UPDATE processed_records 
            SET status = ?, manual_review_status = ?, updated_at = ?
            WHERE id = ? OR record_id = ?
        """, (new_status, json.dumps(review_notes), datetime.now(UTC).isoformat(), record_id, record_id))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'recordId': record_id,
            'newStatus': new_status,
            'reviewAction': review.action,
            'message': f"Record {review.action.value}d by {review.reviewer_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process review: {str(e)}")

# ============================================================================
# REVIEW PIPELINE ENDPOINTS - Content Updates, Approve/Flag, Reprocess
# ============================================================================

class ContentUpdateRequest(BaseModel):
    content: str
    tags: List[str]
    user_id: str = "admin"
    reason: Optional[str] = "Content updated via UI"

class ReviewActionRequest(BaseModel):
    user_id: str = "admin"
    reason: Optional[str] = None

@app.put("/records/{record_id}/content")
async def update_record_content(record_id: str, request: ContentUpdateRequest):
    """Update record content and tags with audit trail"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current record
        cursor.execute("SELECT * FROM processed_records WHERE id = ? OR record_id = ?", (record_id, record_id))
        record = cursor.fetchone()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Get column names
        cursor.execute("PRAGMA table_info(processed_records)")
        columns = [col[1] for col in cursor.fetchall()]
        record_dict = dict(zip(columns, record))
        
        # Track changes for audit trail
        changes = {}
        if record_dict.get('document_text') != request.content:
            changes['content'] = {
                'old': record_dict.get('document_text', ''),
                'new': request.content
            }
        
        if record_dict.get('tags') != json.dumps(request.tags):
            old_tags = json.loads(record_dict.get('tags', '[]')) if record_dict.get('tags') else []
            changes['tags'] = {
                'old': old_tags,
                'new': request.tags
            }
        
        if not changes:
            return {"success": True, "message": "No changes detected", "record_id": record_id}
        
        # Create audit entry
        audit_entry = {
            "action": "content_update",
            "user_id": request.user_id,
            "reason": request.reason,
            "changes": changes,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        # Get existing audit log
        try:
            audit_log = json.loads(record_dict.get('manual_review_status', '[]')) if record_dict.get('manual_review_status') else []
        except:
            audit_log = []
        if not isinstance(audit_log, list):
            audit_log = [audit_log]
        audit_log.append(audit_entry)
        
        # Update record (using existing schema columns)
        cursor.execute("""
            UPDATE processed_records 
            SET document_text = ?, tags = ?, manual_review_status = ?
            WHERE id = ? OR record_id = ?
        """, (
            request.content, 
            json.dumps(request.tags), 
            json.dumps(audit_log), 
            record_id, 
            record_id
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Content updated successfully",
            "record_id": record_id,
            "changes": changes,
            "audit_trail": audit_entry
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update content: {str(e)}")

@app.post("/records/{record_id}/reprocess")
async def reprocess_record(record_id: str, request: ContentUpdateRequest):
    """Reprocess record through the full ingestion pipeline"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current record
        cursor.execute("SELECT * FROM processed_records WHERE id = ? OR record_id = ?", (record_id, record_id))
        record = cursor.fetchone()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Get column names
        cursor.execute("PRAGMA table_info(processed_records)")
        columns = [col[1] for col in cursor.fetchall()]
        record_dict = dict(zip(columns, record))
        
        # First update the content if changed
        content_changes = {}
        if record_dict.get('document_text') != request.content:
            content_changes['content'] = {
                'old': record_dict.get('document_text', ''),
                'new': request.content
            }
        
        if record_dict.get('tags') != json.dumps(request.tags):
            old_tags = json.loads(record_dict.get('tags', '[]')) if record_dict.get('tags') else []
            content_changes['tags'] = {
                'old': old_tags,
                'new': request.tags
            }
        
        # Create reprocess request for ingest endpoint
        # Map source connector to valid enum value
        original_connector = record_dict.get('source_connector', 'Custom')
        if not original_connector:
            valid_connector = "Custom"
        else:
            connector_lower = original_connector.lower().strip()
            if "sharepoint" in connector_lower:
                valid_connector = "SharePoint"
            elif "confluence" in connector_lower:
                valid_connector = "Confluence"
            elif "notion" in connector_lower:
                valid_connector = "Notion"
            elif "gdrive" in connector_lower or "google" in connector_lower or "drive" in connector_lower:
                valid_connector = "GDrive"
            elif "elasticsearch" in connector_lower or "elastic" in connector_lower:
                valid_connector = "Elasticsearch"
            elif connector_lower in ["unknown", "n/a", "null", ""]:
                valid_connector = "Unknown"
            else:
                valid_connector = "Custom"
        
        ingest_request = ContentIngestRequest(
            record_id=record_id,
            content=request.content,
            tags=request.tags,
            source_connector=valid_connector,
            content_metadata={}
        )
        
        # Call the ingest endpoint to reprocess
        ingest_result = await ingest_content(ingest_request)
        
        # Create comprehensive audit entry
        audit_entry = {
            "action": "reprocess",
            "user_id": request.user_id,
            "reason": request.reason,
            "content_changes": content_changes,
            "reprocess_result": {
                "success": ingest_result.get("success", False),
                "new_quality_score": ingest_result.get("quality_score"),
                "new_status": ingest_result.get("status"),
                "trace_id": ingest_result.get("trace_id")
            },
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        # Get existing audit log
        try:
            audit_log = json.loads(record_dict.get('manual_review_status', '[]')) if record_dict.get('manual_review_status') else []
        except:
            audit_log = []
        if not isinstance(audit_log, list):
            audit_log = [audit_log]
        audit_log.append(audit_entry)
        
        # Update the audit log in the reprocessed record
        cursor.execute("""
            UPDATE processed_records 
            SET manual_review_status = ?
            WHERE record_id = ?
        """, (json.dumps(audit_log), record_id))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Record reprocessed successfully",
            "record_id": record_id,
            "reprocess_result": ingest_result,
            "content_changes": content_changes,
            "audit_trail": audit_entry
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reprocess record: {str(e)}")

@app.post("/records/{record_id}/approve")
async def approve_record(record_id: str, request: ReviewActionRequest):
    """Manually approve a flagged record - moves to approved queue"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current record
        cursor.execute("SELECT * FROM processed_records WHERE id = ? OR record_id = ?", (record_id, record_id))
        record = cursor.fetchone()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Get column names
        cursor.execute("PRAGMA table_info(processed_records)")
        columns = [col[1] for col in cursor.fetchall()]
        record_dict = dict(zip(columns, record))
        
        old_status = record_dict.get('status', 'unknown')
        new_status = 'approved'
        
        # Create audit entry
        audit_entry = {
            "action": "manual_approve",
            "user_id": request.user_id,
            "reason": request.reason or "Manually approved by reviewer",
            "status_change": {
                "old": old_status,
                "new": new_status
            },
            "queue_movement": "moved_to_approved_queue",
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        # Get existing audit log
        try:
            audit_log = json.loads(record_dict.get('manual_review_status', '[]')) if record_dict.get('manual_review_status') else []
        except:
            audit_log = []
        if not isinstance(audit_log, list):
            audit_log = [audit_log]
        audit_log.append(audit_entry)
        
        # Update record status (using existing schema columns)
        cursor.execute("""
            UPDATE processed_records 
            SET status = ?, manual_review_status = ?
            WHERE id = ? OR record_id = ?
        """, (
            new_status,
            json.dumps(audit_log),
            record_id,
            record_id
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": f"Record approved by {request.user_id}",
            "record_id": record_id,
            "status_change": {"old": old_status, "new": new_status},
            "queue": "approved",
            "audit_trail": audit_entry
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve record: {str(e)}")

@app.post("/records/{record_id}/flag")
async def flag_record(record_id: str, request: ReviewActionRequest):
    """Manually flag an approved record - moves to review queue"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current record
        cursor.execute("SELECT * FROM processed_records WHERE id = ? OR record_id = ?", (record_id, record_id))
        record = cursor.fetchone()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Get column names
        cursor.execute("PRAGMA table_info(processed_records)")
        columns = [col[1] for col in cursor.fetchall()]
        record_dict = dict(zip(columns, record))
        
        old_status = record_dict.get('status', 'unknown')
        new_status = 'flagged'
        
        # Create audit entry
        audit_entry = {
            "action": "manual_flag",
            "user_id": request.user_id,
            "reason": request.reason or "Manually flagged by reviewer",
            "status_change": {
                "old": old_status,
                "new": new_status
            },
            "queue_movement": "moved_to_review_queue",
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        # Get existing audit log
        try:
            audit_log = json.loads(record_dict.get('manual_review_status', '[]')) if record_dict.get('manual_review_status') else []
        except:
            audit_log = []
        if not isinstance(audit_log, list):
            audit_log = [audit_log]
        audit_log.append(audit_entry)
        
        # Update record status (using existing schema columns)  
        cursor.execute("""
            UPDATE processed_records 
            SET status = ?, manual_review_status = ?
            WHERE id = ? OR record_id = ?
        """, (
            new_status,
            json.dumps(audit_log),
            record_id,
            record_id
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": f"Record flagged by {request.user_id}",
            "record_id": record_id,
            "status_change": {"old": old_status, "new": new_status},
            "queue": "review",
            "audit_trail": audit_entry
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to flag record: {str(e)}")

@app.get("/records/{record_id}/audit-trail")
async def get_audit_trail(record_id: str):
    """Get complete audit trail for a record"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get record with audit trail
        cursor.execute("SELECT manual_review_status FROM processed_records WHERE id = ? OR record_id = ?", (record_id, record_id))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Record not found")
        
        conn.close()
        
        # Parse audit trail
        try:
            audit_trail = json.loads(result[0]) if result[0] else []
        except:
            audit_trail = []
        
        if not isinstance(audit_trail, list):
            audit_trail = [audit_trail]
        
        # Sort by timestamp (newest first)
        audit_trail = sorted(audit_trail, key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return {
            "success": True,
            "record_id": record_id,
            "audit_trail": audit_trail,
            "total_actions": len(audit_trail)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audit trail: {str(e)}")

# ============================================================================
# END REVIEW PIPELINE ENDPOINTS
# ============================================================================

@app.get("/quality-control/dashboard")
async def get_quality_control_dashboard():
    """
    QUALITY CONTROL CENTER - Analytics and management overview
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get approval threshold from dynamic system
        approval_threshold = get_threshold_value("approval_quality_score_threshold") or 50.0
        
        # Status distribution
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN status = 'approved' OR (status IS NULL AND CAST(quality_score AS REAL) >= ?) THEN 'approved'
                    WHEN status = 'flagged' OR (status IS NULL AND CAST(quality_score AS REAL) < ?) THEN 'flagged'
                    WHEN status = 'rejected' THEN 'rejected'
                    ELSE 'pending'
                END as computed_status,
                COUNT(*) as count
            FROM processed_records
            GROUP BY computed_status
        """, (approval_threshold, approval_threshold))
        
        status_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Quality trends (last 7 days)
        cursor.execute("""
            SELECT 
                DATE(created_at) as date,
                AVG(quality_score) as avg_quality,
                COUNT(*) as total_records
            FROM processed_records 
            WHERE DATE(created_at) >= DATE('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        
        quality_trends = [
            {
                'date': row[0],
                'avgQuality': round(row[1], 1),
                'totalRecords': row[2]
            }
            for row in cursor.fetchall()
        ]
        
        # Top failure reasons
        cursor.execute("""
            SELECT quality_checks 
            FROM processed_records 
            WHERE quality_checks IS NOT NULL AND CAST(quality_score AS REAL) < ?
        """, (approval_threshold,))
        
        failure_reasons = defaultdict(int)
        for row in cursor.fetchall():
            try:
                checks = json.loads(row[0])
                for check in checks:
                    if check.get('status') == 'fail':
                        check_name = check.get('check_name', 'unknown')
                        failure_reasons[check_name] += 1
            except:
                continue
        
        top_failures = [
            {'reason': reason, 'count': count}
            for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # System performance
        total_records = sum(status_distribution.values())
        approval_rate = (status_distribution.get('approved', 0) / total_records * 100) if total_records > 0 else 0
        
        conn.close()
        
        return {
            'statusDistribution': status_distribution,
            'qualityTrends': quality_trends,
            'topFailureReasons': top_failures,
            'systemPerformance': {
                'totalRecords': total_records,
                'approvalRate': round(approval_rate, 1),
                'avgQualityScore': sum(trend['avgQuality'] * trend['totalRecords'] for trend in quality_trends) / sum(trend['totalRecords'] for trend in quality_trends) if quality_trends else 0,
                'recordsNeedingReview': status_distribution.get('flagged', 0)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch quality control dashboard: {str(e)}")

# Update the main ingest endpoint to use the new binary decision logic
def update_ingest_endpoint_for_binary_decision():
    """
    Update the main ingest endpoint to make binary APPROVED/FLAGGED decisions
    """
    # This would modify the existing /ingest endpoint to:
    # 1. Run quality checks
    # 2. Make binary decision (APPROVED >= 80 score + no critical issues, else FLAGGED)
    # 3. Route accordingly
    pass

# ===============================
# SIMPLE IMPROVED PIPELINE ENDPOINTS
# ===============================

@app.get("/production/approved-simple")
async def get_approved_records_endpoint(page: int = 1, pageSize: int = 25):
    """Production Dashboard - Only approved records (score >= config threshold)"""
    try:
        # Get approval threshold from dynamic system
        approval_threshold = get_threshold_value("approval_quality_score_threshold") or 50.0
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        offset = (page - 1) * pageSize
        
        cursor.execute("""
            SELECT id, record_id, content, tags, source_connector, 
                   quality_score, created_at, content_metadata, status
            FROM processed_records 
            WHERE (status = 'approved' OR (status IS NULL AND CAST(quality_score AS REAL) >= ?))
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """, (approval_threshold, pageSize, offset))
        
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            # Use actual status from database, fallback to 'approved' if null (for legacy records)
            actual_status = row[8] if row[8] is not None else 'approved'
            records.append({
                'id': row[0],
                'recordId': row[1],
                'content': row[2][:200] + '...' if len(row[2]) > 200 else row[2],
                'tags': json.loads(row[3]) if row[3] else [],
                'sourceConnector': row[4],
                'qualityScore': row[5],
                'createdAt': row[6],
                'status': actual_status
            })
        
        cursor.execute("SELECT COUNT(*) FROM processed_records WHERE (status = 'approved' OR (status IS NULL AND CAST(quality_score AS REAL) >= ?))", (approval_threshold,))
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'records': records,
            'pagination': {
                'page': page,
                'pageSize': pageSize,
                'total': total,
                'totalPages': (total + pageSize - 1) // pageSize
            },
            'summary': {
                'totalApproved': total,
                'avgQualityScore': sum(r['qualityScore'] for r in records) / len(records) if records else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/review/queue-simple")
async def get_review_queue_endpoint():
    """Review Queue - Flagged records needing review (score < config threshold)"""
    try:
        # Get approval threshold from dynamic system
        approval_threshold = get_threshold_value("approval_quality_score_threshold") or 50.0
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, record_id, content, tags, source_connector, 
                   quality_score, quality_checks, created_at
            FROM processed_records 
            WHERE (status = 'flagged' OR (status IS NULL AND CAST(quality_score AS REAL) < ?))
            ORDER BY quality_score ASC, created_at DESC
        """, (approval_threshold,))
        
        rows = cursor.fetchall()
        
        review_items = []
        for row in rows:
            quality_checks = json.loads(row[6]) if row[6] else []
            issues = []
            
            for check in quality_checks:
                if check.get('status') == 'fail':
                    issues.append({
                        'type': check.get('check_name', 'unknown'),
                        'description': check.get('failure_reason', 'Quality check failed')
                    })
            
            severity = 'critical' if row[5] < 50 else ('high' if row[5] < 70 else 'medium')
            
            review_items.append({
                'id': row[0],
                'recordId': row[1],
                'content': row[2][:300] + '...' if len(row[2]) > 300 else row[2],
                'tags': json.loads(row[3]) if row[3] else [],
                'sourceConnector': row[4],
                'qualityScore': row[5],
                'severity': severity,
                'issues': issues,
                'issueCount': len(issues),
                'createdAt': row[7],
                'status': 'flagged'
            })
        
        conn.close()
        
        summary = {
            'totalFlagged': len(review_items),
            'critical': len([item for item in review_items if item['severity'] == 'critical']),
            'high': len([item for item in review_items if item['severity'] == 'high']),
            'medium': len([item for item in review_items if item['severity'] == 'medium'])
        }
        
        return {
            'reviewQueue': review_items,
            'summary': summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/quality-control/dashboard-simple")
async def get_quality_control_dashboard_endpoint():
    """Quality Control Center - Analytics and management overview"""
    try:
        # Get approval threshold from dynamic system
        approval_threshold = get_threshold_value("approval_quality_score_threshold") or 50.0
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN CAST(quality_score AS REAL) >= ? THEN 'approved'
                    WHEN CAST(quality_score AS REAL) < ? THEN 'flagged'
                    ELSE 'unknown'
                END as status,
                COUNT(*) as count
            FROM processed_records
            GROUP BY status
        """, (approval_threshold, approval_threshold))
        
        status_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Quality trends (last 7 days)
        cursor.execute("""
            SELECT 
                DATE(created_at) as date,
                AVG(quality_score) as avg_quality,
                COUNT(*) as total_records
            FROM processed_records 
            WHERE DATE(created_at) >= DATE('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        
        quality_trends = [
            {
                'date': row[0],
                'avgQuality': round(row[1], 1),
                'totalRecords': row[2]
            }
            for row in cursor.fetchall()
        ]
        
        # Top failure reasons
        cursor.execute("""
            SELECT quality_checks 
            FROM processed_records 
            WHERE quality_checks IS NOT NULL AND CAST(quality_score AS REAL) < ?
        """, (approval_threshold,))
        
        failure_reasons = defaultdict(int)
        for row in cursor.fetchall():
            try:
                checks = json.loads(row[0])
                for check in checks:
                    if check.get('status') == 'fail':
                        check_name = check.get('check_name', 'unknown')
                        failure_reasons[check_name] += 1
            except:
                continue
        
        top_failures = [
            {'reason': reason, 'count': count}
            for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # System performance
        total_records = sum(status_distribution.values())
        approval_rate = (status_distribution.get('approved', 0) / total_records * 100) if total_records > 0 else 0
        
        conn.close()
        
        return {
            'statusDistribution': status_distribution,
            'qualityTrends': quality_trends,
            'topFailureReasons': top_failures,
            'systemPerformance': {
                'totalRecords': total_records,
                'approvalRate': round(approval_rate, 1),
                'avgQualityScore': sum(trend['avgQuality'] * trend['totalRecords'] for trend in quality_trends) / sum(trend['totalRecords'] for trend in quality_trends) if quality_trends else 0,
                'recordsNeedingReview': status_distribution.get('flagged', 0)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch quality control dashboard: {str(e)}")

@app.post("/production/override/{record_id}")
async def override_approved_record(record_id: str, payload: dict = Body(...)):
    """
    Manually override an approved record (e.g., flag for review).
    Payload: {"new_status": "flagged", "user_id": "reviewer123", "reason": "..."}
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Fetch the record
        cursor.execute("SELECT id, status, manual_review_status FROM processed_records WHERE id = ? OR record_id = ?", (record_id, record_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")
        db_id, old_status, manual_review_status = row
        
        # Prepare audit log
        audit_entry = {
            "action": "manual_override",
            "user_id": payload.get("user_id"),
            "old_status": old_status,
            "new_status": payload.get("new_status", "flagged"),
            "reason": payload.get("reason", "No reason provided"),
            "timestamp": datetime.now(UTC).isoformat()
        }
        # Append to manual_review_status JSON field
        try:
            audit_log = json.loads(manual_review_status) if manual_review_status else []
        except Exception:
            audit_log = []
        if not isinstance(audit_log, list):
            audit_log = [audit_log]
        audit_log.append(audit_entry)
        
        # Update record
        cursor.execute(
            """
            UPDATE processed_records
            SET status = ?, manual_review_status = ?
            WHERE id = ? OR record_id = ?
            """,
            (payload.get("new_status", "flagged"), json.dumps(audit_log), record_id, record_id)
        )
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "recordId": record_id,
            "newStatus": payload.get("new_status", "flagged"),
            "auditLog": audit_log[-1]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to override record: {str(e)}")

@app.get("/records/filters")
def get_records_filter_options_legacy():
    """Return real-time unique filter options for records page"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Companies
        cursor.execute("SELECT DISTINCT company FROM processed_records WHERE company IS NOT NULL AND company != ''")
        companies = [row[0] for row in cursor.fetchall()]
        # Connectors
        cursor.execute("SELECT DISTINCT source_connector FROM processed_records WHERE source_connector IS NOT NULL AND source_connector != ''")
        connectors = [row[0] for row in cursor.fetchall()]
        # Statuses
        cursor.execute("SELECT DISTINCT status FROM processed_records WHERE status IS NOT NULL AND status != ''")
        statuses = [row[0] for row in cursor.fetchall()]
        # Tags (flattened)
        cursor.execute("SELECT tags FROM processed_records WHERE tags IS NOT NULL AND tags != ''")
        tag_rows = cursor.fetchall()
        tag_set = set()
        for row in tag_rows:
            try:
                tags = json.loads(row[0]) if row[0].startswith('[') else row[0].split(',')
                tag_set.update([t.strip() for t in tags if t.strip()])
            except Exception:
                continue
        tags = sorted(tag_set)
        conn.close()
        return {
            "companies": companies,
            "connectors": connectors,
            "statuses": statuses,
            "tags": tags,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Enhanced Quality Engine Integration
@app.post("/enhanced/quality-check")
async def enhanced_quality_check(request: ContentIngestRequest):
    """
    Enhanced quality check using advanced NLP and semantic analysis
    """
    try:
        # Create chunk request for rules engine
        chunk_request = ChunkIngestRequest(
            record_id=request.record_id,
            document_text=request.content,
            tags=request.tags,
            source_connector=SourceConnector(request.source_connector),
            file_id=f"enhanced_{request.record_id}",
            created_at=datetime.now(UTC)
        )
        
        # Run enhanced quality checks
        if rules_engine:
            quality_results = rules_engine.check_chunk(chunk_request)
            
            # Calculate enhanced quality score
            total_score = 0.0
            total_weight = 0.0
            
            # Enhanced weights for different check types
            check_weights = {
                "semantic_relevance": 0.25,
                "domain_relevance": 0.20,
                "tag_specificity": 0.15,
                "context_coherence": 0.15,
                "empty_tags": 0.10,
                "tag_count_validation": 0.05,
                "advanced_stopwords": 0.05,
                "advanced_spam": 0.05,
            }
            
            for result in quality_results:
                weight = check_weights.get(result.check_name, 0.05)
                score = result.confidence_score
                
                # Apply severity penalties
                if result.severity == "critical":
                    score *= 0.5
                elif result.severity == "high":
                    score *= 0.8
                elif result.severity == "medium":
                    score *= 0.9
                
                total_score += score * weight
                total_weight += weight
            
            # Calculate final quality score
            final_score = (total_score / total_weight) * 100 if total_weight > 0 else 0
            final_score = min(100, max(0, final_score))
            
            # Determine quality level
            if final_score >= 80:
                quality_level = "high"
            elif final_score >= 60:
                quality_level = "medium"
            else:
                quality_level = "low"
            
            # Store the record
            record_data = {
                'record_id': request.record_id,
                'title': f"Enhanced Quality Check - {request.record_id}",
                'content': request.content,
                'tags': request.tags,
                'source_connector': request.source_connector,
                'company': request.content_metadata.get('company', 'Unknown') if request.content_metadata else 'Unknown',
                'quality_score': final_score,
                'quality_level': quality_level,
                'quality_checks': [result.dict() for result in quality_results],
                'content_metadata': request.content_metadata or {},
                'llm_suggestions': [],
                'llm_reasoning': f"Enhanced quality analysis completed with score: {final_score:.1f}",
                'status': 'processed',
                'manual_review_status': 'pending_review' if final_score < 70 else 'approved'
            }
            
            store_record(record_data)
            
            return {
                "status": "success",
                "message": "Enhanced quality check completed",
                "quality_score": final_score,
                "quality_level": quality_level,
                "quality_checks": [result.dict() for result in quality_results],
                "enhanced_features": {
                    "semantic_analysis": any(r.check_name == "semantic_relevance" for r in quality_results),
                    "domain_analysis": any(r.check_name == "domain_relevance" for r in quality_results),
                    "specificity_analysis": any(r.check_name == "tag_specificity" for r in quality_results),
                    "coherence_analysis": any(r.check_name == "context_coherence" for r in quality_results)
                },
                "processing_time_ms": sum(r.check_metadata.get('processing_time_ms', 0) for r in quality_results if r.check_metadata)
            }
        else:
            raise HTTPException(status_code=500, detail="Enhanced rules engine not available")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced quality check failed: {str(e)}")

@app.get("/enhanced/quality-metrics")
async def get_enhanced_quality_metrics():
    """
    Get enhanced quality engine performance metrics
    """
    try:
        if rules_engine:
            metrics = rules_engine.get_performance_metrics()
            return {
                "status": "success",
                "enhanced_metrics": metrics,
                "available_checks": [
                    "semantic_relevance",
                    "domain_relevance", 
                    "tag_specificity",
                    "context_coherence",
                    "empty_tags",
                    "tag_count_validation",
                    "text_quality",
                    "stopwords_detection",
                    "spam_pattern_detection",
                    "duplicate_content_detection",
                    "tag_text_relevance"
                ],
                "engine_status": "active"
            }
        else:
            return {
                "status": "error",
                "message": "Enhanced rules engine not available",
                "engine_status": "inactive"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get enhanced metrics: {str(e)}")

@app.post("/enhanced/batch-process")
async def enhanced_batch_process(records: List[ContentIngestRequest]):
    """
    Process multiple records with enhanced quality engine
    """
    try:
        results = []
        total_processing_time = 0
        
        for record in records:
            start_time = time.time()
            
            # Create chunk request
            chunk_request = ChunkIngestRequest(
                record_id=record.record_id,
                document_text=record.content,
                tags=record.tags,
                source_connector=SourceConnector(record.source_connector),
                file_id=f"batch_{record.record_id}",
                created_at=datetime.now(UTC)
            )
            
            # Process with enhanced engine
            if rules_engine:
                quality_results = rules_engine.check_chunk(chunk_request)
                
                # Calculate quality score (same logic as single check)
                total_score = 0.0
                total_weight = 0.0
                check_weights = {
                    "semantic_relevance": 0.25,
                    "domain_relevance": 0.20,
                    "tag_specificity": 0.15,
                    "context_coherence": 0.15,
                    "empty_tags": 0.10,
                    "tag_count_validation": 0.05,
                    "advanced_stopwords": 0.05,
                    "advanced_spam": 0.05,
                }
                
                for result in quality_results:
                    weight = check_weights.get(result.check_name, 0.05)
                    score = result.confidence_score
                    
                    if result.severity == "critical":
                        score *= 0.5
                    elif result.severity == "high":
                        score *= 0.8
                    elif result.severity == "medium":
                        score *= 0.9
                    
                    total_score += score * weight
                    total_weight += weight
                
                final_score = (total_score / total_weight) * 100 if total_weight > 0 else 0
                final_score = min(100, max(0, final_score))
                
                quality_level = "high" if final_score >= 80 else "medium" if final_score >= 60 else "low"
                
                # Store record
                record_data = {
                    'record_id': record.record_id,
                    'title': f"Batch Enhanced Check - {record.record_id}",
                    'content': record.content,
                    'tags': record.tags,
                    'source_connector': record.source_connector,
                    'company': record.content_metadata.get('company', 'Unknown') if record.content_metadata else 'Unknown',
                    'quality_score': final_score,
                    'quality_level': quality_level,
                    'quality_checks': [result.dict() for result in quality_results],
                    'content_metadata': record.content_metadata or {},
                    'llm_suggestions': [],
                    'llm_reasoning': f"Batch enhanced analysis - score: {final_score:.1f}",
                    'status': 'processed',
                    'manual_review_status': 'pending_review' if final_score < 70 else 'approved'
                }
                
                store_record(record_data)
                
                processing_time = (time.time() - start_time) * 1000
                total_processing_time += processing_time
                
                results.append({
                    "record_id": record.record_id,
                    "quality_score": final_score,
                    "quality_level": quality_level,
                    "processing_time_ms": processing_time,
                    "checks_passed": len([r for r in quality_results if r.status == FlagStatus.PASS]),
                    "checks_failed": len([r for r in quality_results if r.status == FlagStatus.FAIL])
                })
            else:
                results.append({
                    "record_id": record.record_id,
                    "error": "Enhanced rules engine not available"
                })
        
        return {
            "status": "success",
            "message": f"Batch processed {len(records)} records",
            "results": results,
            "total_processing_time_ms": total_processing_time,
            "avg_processing_time_ms": total_processing_time / len(records) if records else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

# ================================================================
# EXTERNAL API INGESTION ENDPOINTS
# ================================================================

class ExternalAPIConfig(BaseModel):
    """Configuration for external API ingestion"""
    api_url: str
    api_key: str
    headers: Dict[str, str] = {}
    batch_size: int = 1000
    rate_limit_per_second: int = 100
    max_concurrent_requests: int = 10
    poll_interval: int = 60
    enabled: bool = True

# Global ingestion manager
ingestion_configs = {}
ingestion_status = {}

@app.post("/external-api/configure")
async def configure_external_api(config: ExternalAPIConfig):
    """Configure external API for data ingestion"""
    try:
        config_id = f"api_{int(time.time())}"
        ingestion_configs[config_id] = config.dict()
        ingestion_status[config_id] = {
            "status": "configured",
            "created_at": datetime.now(UTC).isoformat(),
            "total_processed": 0,
            "last_run": None
        }
        
        return {
            "success": True,
            "config_id": config_id,
            "message": "External API configured successfully",
            "configuration": {
                "api_url": config.api_url,
                "batch_size": config.batch_size,
                "rate_limit": config.rate_limit_per_second,
                "poll_interval": config.poll_interval
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration failed: {str(e)}")

@app.post("/external-api/start/{config_id}")
async def start_external_ingestion(config_id: str):
    """Start continuous ingestion from configured external API"""
    try:
        if config_id not in ingestion_configs:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        config = ingestion_configs[config_id]
        
        # Update status
        ingestion_status[config_id].update({
            "status": "starting",
            "last_run": datetime.now(UTC).isoformat()
        })
        
        # In a real implementation, this would start a background task
        # For now, we'll simulate the start
        ingestion_status[config_id]["status"] = "running"
        
        return {
            "success": True,
            "message": f"Started ingestion from {config['api_url']}",
            "config_id": config_id,
            "status": "running"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start ingestion: {str(e)}")

@app.post("/external-api/stop/{config_id}")
async def stop_external_ingestion(config_id: str):
    """Stop continuous ingestion"""
    try:
        if config_id not in ingestion_status:
            raise HTTPException(status_code=404, detail="Ingestion not found")
        
        ingestion_status[config_id]["status"] = "stopped"
        
        return {
            "success": True,
            "message": "Ingestion stopped",
            "config_id": config_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop ingestion: {str(e)}")

@app.get("/external-api/status")
async def get_ingestion_status():
    """Get status of all external API ingestions"""
    return {
        "total_configurations": len(ingestion_configs),
        "running_ingestions": len([s for s in ingestion_status.values() if s["status"] == "running"]),
        "configurations": ingestion_status
    }

@app.post("/external-api/test-connection")
async def test_external_api_connection(config: ExternalAPIConfig):
    """Test connection to external API without saving configuration"""
    try:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    config.api_url,
                    headers=config.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Analyze response structure
                        record_count = 0
                        if isinstance(data, dict):
                            record_count = len(data.get('data', data.get('results', data.get('items', []))))
                        elif isinstance(data, list):
                            record_count = len(data)
                        
                        return {
                            "success": True,
                            "message": "Connection successful",
                            "response_status": response.status,
                            "estimated_records": record_count,
                            "api_response_type": type(data).__name__
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"API returned status {response.status}",
                            "response_status": response.status
                        }
                        
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "message": "Connection timeout",
                    "error": "API did not respond within 10 seconds"
                }
    except Exception as e:
        return {
            "success": False,
            "message": "Connection failed",
            "error": str(e)
        }

@app.post("/external-api/manual-fetch/{config_id}")
async def manual_fetch_from_api(config_id: str, params: Dict[str, Any] = Body(default={})):
    """Manually fetch and process data from configured external API"""
    try:
        if config_id not in ingestion_configs:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        config_data = ingestion_configs[config_id]
        
        # Fetch data
        async with aiohttp.ClientSession() as session:
            async with session.get(
                config_data["api_url"],
                headers=config_data["headers"],
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status != 200:
                    raise HTTPException(status_code=400, detail=f"API returned status {response.status}")
                
                data = await response.json()
                
                # Extract records
                records = []
                if isinstance(data, dict):
                    records = (
                        data.get('data', []) or 
                        data.get('results', []) or 
                        data.get('items', []) or
                        [data]
                    )
                elif isinstance(data, list):
                    records = data
                
                # Process records through ingestion pipeline
                processed_count = 0
                errors = []
                
                for record in records[:config_data["batch_size"]]:  # Limit to batch size
                    try:
                        # Transform external record
                        transformed = {
                            "record_id": str(record.get('id', f"manual_{int(time.time())}_{processed_count}")),
                            "content": record.get('content', record.get('text', record.get('body', ''))),
                            "tags": record.get('tags', ['external-api', 'manual-fetch']),
                            "source_connector": "external_api",
                            "content_metadata": {
                                "external_id": record.get('id'),
                                "api_source": config_data["api_url"],
                                "fetch_timestamp": datetime.now(UTC).isoformat()
                            }
                        }
                        
                        # Send through main ingestion endpoint
                        ingest_request = ContentIngestRequest(**transformed)
                        result = await ingest_content(ingest_request)
                        processed_count += 1
                        
                    except Exception as e:
                        errors.append({
                            "record_id": record.get('id', 'unknown'),
                            "error": str(e)
                        })
                
                # Update status
                ingestion_status[config_id]["total_processed"] += processed_count
                
                return {
                    "success": True,
                    "message": f"Manually processed {processed_count} records",
                    "processed_count": processed_count,
                    "error_count": len(errors),
                    "total_fetched": len(records),
                    "errors": errors[:5]  # First 5 errors
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manual fetch failed: {str(e)}")

# High-volume batch ingestion endpoint
@app.post("/external-api/bulk-ingest")
async def bulk_ingest_external_data(records: List[Dict[str, Any]]):
    """
    High-performance bulk ingestion endpoint for 250K+ records/day
    Optimized for external API data with minimal processing overhead
    """
    start_time = time.time()
    
    try:
        # Process in optimized batches
        batch_size = 500  # Optimal batch size for performance
        processed_count = 0
        error_count = 0
        batch_results = []
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            batch_start = time.time()
            
            batch_processed = 0
            batch_errors = 0
            
            for record in batch:
                try:
                    # Fast transformation
                    content = (
                        record.get('content') or 
                        record.get('text') or 
                        record.get('body') or 
                        str(record.get('title', ''))
                    )
                    
                    if len(content.strip()) < 10:
                        batch_errors += 1
                        continue
                    
                    # Minimal processing for high volume
                    record_data = {
                        "id": str(record.get('id', f"bulk_{int(time.time())}_{processed_count}")),
                        "record_id": str(record.get('id', f"bulk_{int(time.time())}_{processed_count}")),
                        "title": record.get('title', content[:100] + "..." if len(content) > 100 else content),
                        "content": content,
                        "tags": json.dumps(record.get('tags', ['external-api', 'bulk-import'])),
                        "source_connector": "external_api_bulk",
                        "quality_score": 75.0,  # Default score for bulk import
                        "status": "imported",
                        "created_at": datetime.now(UTC).isoformat(),
                        "processing_time_ms": 1.0,  # Minimal processing time
                        "trace_id": f"bulk-{int(time.time())}-{processed_count}",
                        "quality_checks": json.dumps([]),  # Skip quality checks for bulk
                        "content_metadata": json.dumps(record.get('metadata', {}))
                    }
                    
                    # Direct database insertion for performance
                    store_record(record_data)
                    batch_processed += 1
                    
                except Exception as e:
                    batch_errors += 1
                    error_count += 1
            
            processed_count += batch_processed
            
            batch_time = time.time() - batch_start
            batch_results.append({
                "batch_number": (i // batch_size) + 1,
                "processed": batch_processed,
                "errors": batch_errors,
                "processing_time_seconds": batch_time,
                "records_per_second": len(batch) / batch_time if batch_time > 0 else 0
            })
        
        total_time = time.time() - start_time
        
        return {
            "success": True,
            "message": f"Bulk ingestion completed",
            "summary": {
                "total_records": len(records),
                "processed_successfully": processed_count,
                "errors": error_count,
                "processing_time_seconds": total_time,
                "records_per_second": len(records) / total_time if total_time > 0 else 0,
                "daily_capacity": int((86400 / total_time) * len(records)) if total_time > 0 else 0
            },
            "batch_details": batch_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk ingestion failed: {str(e)}")

# LLM Invocation Settings Models
class LLMInvocationMode(str, Enum):
    BINARY = "binary"
    PERCENTAGE = "percentage"
    WEIGHTED = "weighted"
    RANGE = "range"  # NEW: Range-based triggering

class RuleWeight(BaseModel):
    """Individual rule weight configuration"""
    rule_name: str
    weight: float = 1.0
    description: str

class LLMInvocationSettings(BaseModel):
    """LLM invocation configuration"""
    mode: LLMInvocationMode = LLMInvocationMode.BINARY
    percentage_threshold: float = 85.0  # For percentage mode
    weighted_threshold: float = 0.8  # For weighted mode
    # NEW: Range-based triggering thresholds
    range_min_threshold: float = 70.0  # Lower bound - below this = auto-reject
    range_max_threshold: float = 80.0  # Upper bound - above this = auto-approve
    rule_weights: Dict[str, float] = {}
    created_by: str = "admin"
    updated_at: Optional[str] = None

class LLMInvocationDecision(BaseModel):
    """Decision result from LLM invocation logic"""
    should_invoke_llm: bool
    confidence: float
    reason: str
    mode_used: LLMInvocationMode
    threshold_used: Union[float, str]  # Can be float for percentage/weighted or string for range
    rules_summary: Dict[str, Any]

class LLMSimulationRequest(BaseModel):
    """Request for simulating LLM decision - uses dynamic Unified Config values"""
    mode: LLMInvocationMode
    sample_input: Dict[str, Any]
    # 🔧 REMOVED hardcoded values: threshold, rule_weights, range thresholds
    # Backend will get current dynamic values from Unified Config and LLM settings

class LLMSettingsHistory(BaseModel):
    """History record for LLM settings changes"""
    id: str
    changed_by: str
    old_mode: str
    new_mode: str
    old_threshold: float
    new_threshold: float
    timestamp: str
    reason: Optional[str]

# Global LLM invocation settings
llm_invocation_settings = LLMInvocationSettings()

def initialize_llm_invocation_settings():
    """Initialize LLM invocation settings from UnifiedConfigService - SINGLE SOURCE OF TRUTH"""
    global llm_invocation_settings
    
    try:
        from ..services.unified_config_service import get_unified_config_service
        config_service = get_unified_config_service()
        
        # Get values from UnifiedConfigService (single source of truth)
        percentage_threshold = config_service.get_threshold("llm_percentage_threshold") or 85.0
        weighted_threshold = config_service.get_threshold("llm_weighted_threshold") or 0.8
        range_min_threshold = config_service.get_threshold("llm_range_min_threshold") or 70.0
        range_max_threshold = config_service.get_threshold("llm_range_max_threshold") or 80.0
        
        print(f"🔄 Initializing LLM settings from UnifiedConfigService:")
        print(f"   percentage_threshold: {percentage_threshold}")
        print(f"   weighted_threshold: {weighted_threshold}")
        print(f"   range_min_threshold: {range_min_threshold}")
        print(f"   range_max_threshold: {range_max_threshold}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not load from UnifiedConfigService, using defaults: {e}")
        percentage_threshold = 85.0
        weighted_threshold = 0.8
        range_min_threshold = 70.0
        range_max_threshold = 80.0
    
    # Default rule weights (equal weight for all rules)
    default_weights = {
        "empty_tags": 1.0,
        "tag_count_validation": 1.0,
        "text_quality": 1.0,
        "stopwords_detection": 1.0,
        "spam_patterns": 1.0,
        "duplicate_content_detection": 1.0,
        "tag_text_relevance": 1.0,
        "semantic_relevance": 1.0,
        "domain_relevance": 1.0,
        "tag_specificity": 1.0,
        "context_coherence": 1.0
    }
    
    llm_invocation_settings = LLMInvocationSettings(
        mode=LLMInvocationMode.RANGE,  # Range mode for gray-zone triggering
        percentage_threshold=percentage_threshold,  # FROM UNIFIED CONFIG SERVICE
        weighted_threshold=weighted_threshold,      # FROM UNIFIED CONFIG SERVICE
        range_min_threshold=range_min_threshold,    # FROM UNIFIED CONFIG SERVICE
        range_max_threshold=range_max_threshold,    # FROM UNIFIED CONFIG SERVICE
        rule_weights=default_weights,
        created_by="system"
    )

def evaluate_llm_invocation_decision(quality_results: List[QualityCheckResult], settings: Optional[LLMInvocationSettings] = None) -> LLMInvocationDecision:
    """
    Evaluate whether LLM should be invoked based on current settings and rule results
    
    Args:
        quality_results: List of quality check results from rules engine
        settings: LLM invocation settings (optional, uses global if not provided)
    
    Returns:
        LLMInvocationDecision with decision and reasoning
    """
    global llm_invocation_settings
    
    if settings is None:
        settings = llm_invocation_settings
    
    total_rules = len(quality_results)
    passed_rules = sum(1 for result in quality_results if result.status == FlagStatus.PASS)
    
    rules_summary = {
        "total_rules": total_rules,
        "passed_rules": passed_rules,
        "failed_rules": total_rules - passed_rules,
        "pass_rate": (passed_rules / total_rules) * 100 if total_rules > 0 else 0,
        "rule_details": [
            {
                "name": result.check_name,
                "status": result.status.value,
                "confidence": result.confidence_score
            }
            for result in quality_results
        ]
    }
    
    if settings.mode == LLMInvocationMode.BINARY:
        # Binary mode: LLM runs only if ALL rules pass
        should_invoke = passed_rules == total_rules
        confidence = 1.0 if should_invoke else 0.0
        reason = f"Binary mode: {'All rules passed' if should_invoke else f'{total_rules - passed_rules} rules failed'}"
        
    elif settings.mode == LLMInvocationMode.PERCENTAGE:
        # Percentage mode: LLM runs if X% of rules pass
        pass_percentage = (passed_rules / total_rules) * 100 if total_rules > 0 else 0
        should_invoke = pass_percentage >= settings.percentage_threshold
        confidence = min(pass_percentage / settings.percentage_threshold, 1.0)
        reason = f"Percentage mode: {pass_percentage:.1f}% passed (threshold: {settings.percentage_threshold}%)"
        
    elif settings.mode == LLMInvocationMode.WEIGHTED:
        # Weighted mode: Calculate weighted score
        total_weight = 0.0
        passed_weight = 0.0
        
        for result in quality_results:
            rule_weight = settings.rule_weights.get(result.check_name, 1.0)
            total_weight += rule_weight
            if result.status == FlagStatus.PASS:
                passed_weight += rule_weight
        
        weighted_score = passed_weight / total_weight if total_weight > 0 else 0
        should_invoke = weighted_score >= settings.weighted_threshold
        confidence = min(weighted_score / settings.weighted_threshold, 1.0)
        reason = f"Weighted mode: {weighted_score:.3f} score (threshold: {settings.weighted_threshold})"
        
    elif settings.mode == LLMInvocationMode.RANGE:
        # Range mode: LLM runs only in the "gray zone" between min and max thresholds
        pass_percentage = (passed_rules / total_rules) * 100 if total_rules > 0 else 0
        
        if pass_percentage < settings.range_min_threshold:
            # Below minimum - auto-reject, no LLM needed
            should_invoke = False
            confidence = 1.0  # High confidence in rejection
            reason = f"Range mode: {pass_percentage:.1f}% < {settings.range_min_threshold}% (auto-reject)"
        elif pass_percentage > settings.range_max_threshold:
            # Above maximum - auto-approve, no LLM needed
            should_invoke = False
            confidence = 1.0  # High confidence in approval
            reason = f"Range mode: {pass_percentage:.1f}% > {settings.range_max_threshold}% (auto-approve)"
        else:
            # In gray zone - trigger LLM for analysis
            should_invoke = True
            # Confidence decreases as we get closer to the middle of the range
            range_width = settings.range_max_threshold - settings.range_min_threshold
            distance_from_min = pass_percentage - settings.range_min_threshold
            confidence = min(1.0, distance_from_min / (range_width / 2))  # Peak confidence in middle of range
            reason = f"Range mode: {pass_percentage:.1f}% in gray zone ({settings.range_min_threshold}%-{settings.range_max_threshold}%) - LLM needed"        
    else:
        # Fallback to binary mode
        should_invoke = passed_rules == total_rules
        confidence = 1.0 if should_invoke else 0.0
        reason = "Fallback to binary mode: unknown mode specified"
    
    # Determine the correct threshold value for the response
    if settings.mode == LLMInvocationMode.BINARY:
        threshold_used = 100.0  # 100% for binary mode (all rules must pass)
    elif settings.mode == LLMInvocationMode.PERCENTAGE:
        threshold_used = settings.percentage_threshold
    elif settings.mode == LLMInvocationMode.WEIGHTED:
        threshold_used = settings.weighted_threshold
    elif settings.mode == LLMInvocationMode.RANGE:
        threshold_used = f"{settings.range_min_threshold}-{settings.range_max_threshold}"
    else:
        threshold_used = 100.0  # Default for binary mode
    
    return LLMInvocationDecision(
        should_invoke_llm=should_invoke,
        confidence=confidence,
        reason=reason,
        mode_used=settings.mode,
        threshold_used=threshold_used,
        rules_summary=rules_summary
    )

def get_rule_weights_with_descriptions() -> List[RuleWeight]:
    """Get all available rules with their current weights and descriptions"""
    rule_descriptions = {
        "empty_tags": "Check for empty or missing tags",
        "tag_count_validation": "Validate tag count is within reasonable bounds", 
        "text_quality": "Validate text quality and length",
        "stopwords_detection": "Check for generic/meaningless tags",
        "spam_patterns": "Detect spam content patterns",
        "duplicate_content_detection": "Check for duplicate content",
        "tag_text_relevance": "Basic tag-text relevance check",
        "semantic_relevance": "Advanced semantic similarity analysis",
        "domain_relevance": "Domain-specific relevance check",
        "tag_specificity": "Analyze tag specificity vs generic terms",
        "context_coherence": "Check tag coherence and context consistency"
    }
    
    return [
        RuleWeight(
            rule_name=rule_name,
            weight=llm_invocation_settings.rule_weights.get(rule_name, 1.0),
            description=rule_descriptions.get(rule_name, f"Rule: {rule_name}")
        )
        for rule_name in rule_descriptions.keys()
    ]

def save_llm_settings_history(old_settings: LLMInvocationSettings, new_settings: LLMInvocationSettings, changed_by: str, reason: str = None):
    """Save LLM settings change to history"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        history_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC).isoformat()
        
        cursor.execute('''
            INSERT INTO llm_settings_history 
            (id, changed_by, old_mode, new_mode, old_threshold, new_threshold, timestamp, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            history_id, 
            changed_by, 
            old_settings.mode.value, 
            new_settings.mode.value,
            old_settings.percentage_threshold if old_settings.mode == LLMInvocationMode.PERCENTAGE else old_settings.weighted_threshold,
            new_settings.percentage_threshold if new_settings.mode == LLMInvocationMode.PERCENTAGE else new_settings.weighted_threshold,
            timestamp,
            reason
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Failed to save LLM settings history: {e}")
        return False

# Initialize LLM invocation settings
initialize_llm_invocation_settings()

# LLM Invocation Settings API Endpoints

@app.get("/settings/llm-mode")
async def get_llm_invocation_settings():
    """Get current LLM invocation settings"""
    try:
        global llm_invocation_settings
        return {
            "success": True,
            "settings": llm_invocation_settings,
            "rule_weights": get_rule_weights_with_descriptions()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get LLM settings: {str(e)}")

@app.post("/settings/llm-mode")
async def update_llm_invocation_mode(request: dict):
    """Update LLM invocation mode"""
    try:
        global llm_invocation_settings
        
        old_settings = llm_invocation_settings.model_copy()
        
        # Update mode
        mode = request.get("mode")
        if mode and mode in [m.value for m in LLMInvocationMode]:
            llm_invocation_settings.mode = LLMInvocationMode(mode)

        # Update range thresholds if provided
        if "range_min_threshold" in request:
            new_threshold = float(request["range_min_threshold"])
            llm_invocation_settings.range_min_threshold = new_threshold
            
            # Sync with dynamic threshold system
            if "llm_range_min_threshold" in dynamic_thresholds:
                dynamic_thresholds["llm_range_min_threshold"]["current_value"] = new_threshold
        
        if "range_max_threshold" in request:
            new_threshold = float(request["range_max_threshold"])
            llm_invocation_settings.range_max_threshold = new_threshold
            
            # Sync with dynamic threshold system
            if "llm_range_max_threshold" in dynamic_thresholds:
                dynamic_thresholds["llm_range_max_threshold"]["current_value"] = new_threshold        
        # Update user info
        user_id = request.get("user_id", "admin")
        reason = request.get("reason", "Mode change")
        llm_invocation_settings.created_by = user_id
        llm_invocation_settings.updated_at = datetime.now(UTC).isoformat()
        
        # Save to history
        save_llm_settings_history(old_settings, llm_invocation_settings, user_id, reason)
        
        return {
            "success": True,
            "message": f"LLM invocation mode updated to {llm_invocation_settings.mode.value}",
            "settings": llm_invocation_settings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update LLM mode: {str(e)}")

@app.patch("/settings/llm-thresholds")
async def update_llm_thresholds(request: dict):
    """Update LLM invocation thresholds and sync with UnifiedConfigService"""
    try:
        global llm_invocation_settings
        from ..services.unified_config_service import get_unified_config_service, ThresholdUpdate
        
        old_settings = llm_invocation_settings.model_copy()
        config_service = get_unified_config_service()
        
        # Update thresholds
        if "percentage_threshold" in request:
            new_threshold = float(request["percentage_threshold"])
            llm_invocation_settings.percentage_threshold = new_threshold
            
            # Sync with UnifiedConfigService
            threshold_update = ThresholdUpdate(
                name="llm_percentage_threshold",
                value=new_threshold,
                updated_by=request.get("user_id", "admin"),
                reason=f"LLM Settings: {request.get('reason', 'Threshold update')}"
            )
            config_service.update_threshold(threshold_update)
        
        if "weighted_threshold" in request:
            new_threshold = float(request["weighted_threshold"])
            llm_invocation_settings.weighted_threshold = new_threshold
            
            # Sync with UnifiedConfigService
            threshold_update = ThresholdUpdate(
                name="llm_weighted_threshold",
                value=new_threshold,
                updated_by=request.get("user_id", "admin"),
                reason=f"LLM Settings: {request.get('reason', 'Threshold update')}"
            )
            config_service.update_threshold(threshold_update)
        
        # Range mode threshold support
        if "range_min_threshold" in request:
            new_threshold = float(request["range_min_threshold"])
            llm_invocation_settings.range_min_threshold = new_threshold
            
            # Sync with UnifiedConfigService
            threshold_update = ThresholdUpdate(
                name="llm_range_min_threshold",
                value=new_threshold,
                updated_by=request.get("user_id", "admin"),
                reason=f"LLM Settings: {request.get('reason', 'Threshold update')}"
            )
            config_service.update_threshold(threshold_update)
        
        if "range_max_threshold" in request:
            new_threshold = float(request["range_max_threshold"])
            llm_invocation_settings.range_max_threshold = new_threshold
            
            # Sync with UnifiedConfigService
            threshold_update = ThresholdUpdate(
                name="llm_range_max_threshold",
                value=new_threshold,
                updated_by=request.get("user_id", "admin"),
                reason=f"LLM Settings: {request.get('reason', 'Threshold update')}"
            )
            config_service.update_threshold(threshold_update)
        
        if "rule_weights" in request:
            llm_invocation_settings.rule_weights.update(request["rule_weights"])
        
        # Update user info
        user_id = request.get("user_id", "admin")
        reason = request.get("reason", "Threshold update")
        llm_invocation_settings.created_by = user_id
        llm_invocation_settings.updated_at = datetime.now(UTC).isoformat()
        
        # Save to history
        save_llm_settings_history(old_settings, llm_invocation_settings, user_id, reason)
        
        # Notify rules engine to reload thresholds when LLM settings change  
        try:
            if 'rules_engine' in globals() and rules_engine is not None:
                rules_engine.reload_thresholds()
        except Exception as e:
            print(f"Warning: Failed to reload rules engine thresholds after LLM update: {e}")
        
        return {
            "success": True,
            "message": "LLM thresholds updated successfully and synchronized with UnifiedConfigService",
            "settings": llm_invocation_settings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update LLM thresholds: {str(e)}")

@app.get("/rules/weights")
async def get_rule_weights():
    """Get all available rules with their weights and descriptions"""
    try:
        return {
            "success": True,
            "rules": get_rule_weights_with_descriptions()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rule weights: {str(e)}")

@app.post("/simulate-llm-decision")
async def simulate_llm_decision(request: LLMSimulationRequest):
    """Simulate LLM invocation decision using current dynamic Unified Config values"""
    try:
        # 🔧 Get current dynamic LLM settings from Unified Config (no hardcoded values!)
        from ..services.unified_config_service import get_unified_config_service
        config_service = get_unified_config_service()
        
        # Use current DYNAMIC settings - exactly what actual ingestion uses
        global llm_invocation_settings
        current_settings = LLMInvocationSettings(
            mode=request.mode,
            # Get current dynamic thresholds from Unified Config
            percentage_threshold=config_service.get_threshold("llm_percentage_threshold") or llm_invocation_settings.percentage_threshold,
            weighted_threshold=config_service.get_threshold("llm_weighted_threshold") or llm_invocation_settings.weighted_threshold,
            range_min_threshold=config_service.get_threshold("llm_range_min_threshold") or llm_invocation_settings.range_min_threshold,
            range_max_threshold=config_service.get_threshold("llm_range_max_threshold") or llm_invocation_settings.range_max_threshold,
            rule_weights=llm_invocation_settings.rule_weights  # Use current dynamic rule weights
        )
        
        print(f"🎯 SIMULATION USING DYNAMIC CONFIG:")
        print(f"   Mode: {current_settings.mode}")
        print(f"   Percentage threshold: {current_settings.percentage_threshold}")
        print(f"   Weighted threshold: {current_settings.weighted_threshold}")
        print(f"   Range: {current_settings.range_min_threshold}-{current_settings.range_max_threshold}")
        
        # Simulate rules engine processing on sample input
        try:
            # Import rules engine and schema validator
            from app.services.rules_engine import RulesEngine
            from app.services.schema_validator import SchemaValidator
            from app.models.models import ChunkIngestRequest
            
            # Validate and create chunk request
            validator = SchemaValidator()
            validation_result = validator.validate_chunk(request.sample_input)
            
            if not validation_result.is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid sample input: {validation_result.errors}")
            
            chunk_request = ChunkIngestRequest(**validation_result.sanitized_data)
            
            # 🔧 FIX: Use the SAME global rules engine instance as actual ingestion to ensure consistent thresholds
            global rules_engine
            if not RULES_ENGINE_AVAILABLE or rules_engine is None:
                raise Exception("Rules engine not available for simulation")
            
            # Use the shared global rules engine to ensure simulation matches actual ingestion
            quality_results = rules_engine.check_chunk(chunk_request)
            
            # Log simulation results for debugging threshold consistency
            passed_rules = sum(1 for result in quality_results if result.status == FlagStatus.PASS)
            total_rules = len(quality_results)
            pass_rate = (passed_rules / total_rules * 100) if total_rules > 0 else 0
            
            print(f"🔍 SIMULATION DEBUG: Using shared rules engine - {passed_rules}/{total_rules} passed ({pass_rate:.1f}%)")
            
            # Evaluate LLM decision using current dynamic settings
            decision = evaluate_llm_invocation_decision(quality_results, current_settings)
            
            return {
                "success": True,
                "decision": decision,
                "simulation_settings": current_settings,
                "note": "Using current dynamic Unified Config values"
            }
            
        except Exception as sim_error:
            # Fallback simulation with mock data using current dynamic settings
            mock_quality_results = []
            for rule_name in current_settings.rule_weights.keys():
                # Create mock results (randomly pass/fail for demonstration)
                import random
                status = FlagStatus.PASS if random.random() > 0.3 else FlagStatus.FAIL
                mock_result = type('MockResult', (), {
                    'check_name': rule_name,
                    'status': status,
                    'confidence_score': random.uniform(0.5, 1.0)
                })()
                mock_quality_results.append(mock_result)
            
            decision = evaluate_llm_invocation_decision(mock_quality_results, current_settings)
            decision.rules_summary["simulation_note"] = f"Mock simulation used due to error: {str(sim_error)}"
            
            return {
                "success": True,
                "decision": decision,
                "simulation_settings": current_settings,
                "note": "Mock simulation used with dynamic config - actual rules engine processing failed"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to simulate LLM decision: {str(e)}")

@app.get("/settings/llm-thresholds/history")
async def get_llm_settings_history(limit: int = 20):
    """Get history of LLM settings changes"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, changed_by, old_mode, new_mode, old_threshold, new_threshold, timestamp, reason
            FROM llm_settings_history
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append(LLMSettingsHistory(
                id=row[0],
                changed_by=row[1],
                old_mode=row[2],
                new_mode=row[3],
                old_threshold=row[4],
                new_threshold=row[5],
                timestamp=row[6],
                reason=row[7]
            ))
        
        return {
            "success": True,
            "history": history,
            "total_count": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get LLM settings history: {str(e)}")

@app.post("/settings/llm-mode/reset")
async def reset_llm_settings(request: dict):
    """Reset LLM invocation settings to defaults"""
    try:
        global llm_invocation_settings
        
        old_settings = llm_invocation_settings.model_copy()
        user_id = request.get("user_id", "admin")
        
        # Reset to defaults
        initialize_llm_invocation_settings()
        llm_invocation_settings.created_by = user_id
        llm_invocation_settings.updated_at = datetime.now(UTC).isoformat()
        
        # Save to history
        save_llm_settings_history(old_settings, llm_invocation_settings, user_id, "Reset to defaults")
        
        return {
            "success": True,
            "message": "LLM invocation settings reset to defaults",
            "settings": llm_invocation_settings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset LLM settings: {str(e)}")

# ============================================================================
# UNIFIED SETTINGS ENDPOINTS  
# ============================================================================

@app.get("/api/unified-settings/configs")
async def get_unified_configurations(category: Optional[str] = None):
    """Get all unified configuration items integrated with dynamic thresholds"""
    try:
        global dynamic_thresholds
        
        # Convert dynamic thresholds to unified config format
        unified_configs = []
        for key, threshold_data in dynamic_thresholds.items():
            config = {
                "key": key,
                "value": threshold_data["current_value"],
                "data_type": "float" if isinstance(threshold_data["current_value"], (int, float)) else "string",
                "category": threshold_data.get("category", "general"),
                "description": threshold_data.get("description", f"Configuration for {key}"),
                "min_value": threshold_data.get("min_value"),
                "max_value": threshold_data.get("max_value"),
                "default_value": threshold_data.get("default_value"),
                "unit": threshold_data.get("unit", ""),
                "requires_restart": False,
                "validation_severity": "high" if key == "approval_quality_score_threshold" else "medium"
            }
            unified_configs.append(config)
        
        # Add LLM-specific configs
        llm_configs = [
            {
                "key": "llm_invocation_mode",
                "value": llm_invocation_settings.mode.value,
                "data_type": "string",
                "category": "llm",
                "description": "Mode for LLM invocation (binary, percentage, weighted, range)",
                "allowed_values": ["binary", "percentage", "weighted", "range"],
                "default_value": "binary",
                "requires_restart": False,
                "validation_severity": "medium"
            },
            {
                "key": "llm_percentage_threshold",
                "value": llm_invocation_settings.percentage_threshold,
                "data_type": "float",
                "category": "llm",
                "description": "Percentage threshold for LLM invocation",
                "min_value": 0.0,
                "max_value": 100.0,
                "default_value": 85.0,
                "unit": "percentage",
                "requires_restart": False,
                "validation_severity": "medium"
            }
        ]
        unified_configs.extend(llm_configs)
        
        # Filter by category if specified
        if category:
            unified_configs = [c for c in unified_configs if c["category"] == category]
        
        return {
            "success": True,
            "message": f"Retrieved {len(unified_configs)} configurations",
            "configs": unified_configs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get configurations: {str(e)}")

@app.put("/api/unified-settings/configs/{config_name}")
async def update_unified_configuration(config_name: str, request: dict):
    """Update a unified configuration value integrated with dynamic thresholds"""
    try:
        global dynamic_thresholds, llm_invocation_settings
        
        new_value = request.get("value")
        user_id = request.get("changed_by", "admin")
        reason = request.get("reason", "Updated via unified settings")
        
        # Handle dynamic threshold updates
        if config_name in dynamic_thresholds:
            result = update_threshold(config_name, float(new_value), user_id, reason)
            if result:
                return {
                    "success": True,
                    "message": f"Configuration '{config_name}' updated successfully",
                    "config": {
                        "key": config_name, 
                        "value": dynamic_thresholds[config_name]["current_value"]
                    }
                }
            else:
                raise HTTPException(status_code=400, detail=f"Failed to update threshold '{config_name}'")
        
        # Handle LLM-specific settings
        elif config_name == "llm_invocation_mode":
            old_settings = llm_invocation_settings.model_copy()
            llm_invocation_settings.mode = LLMInvocationMode(new_value)
            llm_invocation_settings.created_by = user_id
            llm_invocation_settings.updated_at = datetime.now(UTC).isoformat()
            save_llm_settings_history(old_settings, llm_invocation_settings, user_id, reason)
            
            return {
                "success": True,
                "message": f"LLM invocation mode updated to '{new_value}'",
                "config": {"key": config_name, "value": new_value}
            }
        
        elif config_name == "llm_percentage_threshold":
            old_settings = llm_invocation_settings.model_copy()
            llm_invocation_settings.percentage_threshold = float(new_value)
            llm_invocation_settings.created_by = user_id
            llm_invocation_settings.updated_at = datetime.now(UTC).isoformat()
            save_llm_settings_history(old_settings, llm_invocation_settings, user_id, reason)
            
            return {
                "success": True,
                "message": f"LLM percentage threshold updated to {new_value}%",
                "config": {"key": config_name, "value": new_value}
            }
        
        else:
            raise HTTPException(status_code=404, detail=f"Configuration '{config_name}' not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")

# ============================================================================
# END UNIFIED SETTINGS ENDPOINTS
# ============================================================================

# Add test endpoint before main app routes
@app.get("/test/quality-checks/{record_id}")
async def get_test_quality_checks(record_id: str):
    """Test endpoint to demonstrate comprehensive quality checks display"""
    
    # Sample comprehensive quality checks data
    sample_quality_checks = [
        {
            "check_name": "content_length_validation",
            "status": "PASS",
            "confidence_score": 0.95,
            "description": "Content length is within acceptable range (222 characters)",
            "suggestion": "",
            "autoFixable": False,
            "category": "content",
            "type": "content_length_validation",
            "severity": "low",
            "processing_time_ms": 45,
            "executed_at": "2024-12-15T14:20:15Z",
            "metadata": {
                "min_length": 100,
                "max_length": 50000,
                "actual_length": 222
            }
        },
        {
            "check_name": "pii_detection",
            "status": "PASS",
            "confidence_score": 0.88,
            "description": "No personally identifiable information detected",
            "suggestion": "",
            "autoFixable": False,
            "category": "compliance",
            "type": "pii_detection",
            "severity": "high",
            "processing_time_ms": 320,
            "executed_at": "2024-12-15T14:20:15Z",
            "metadata": {
                "patterns_checked": ["email", "phone", "ssn", "credit_card"],
                "matches_found": 0
            }
        },
        {
            "check_name": "semantic_relevance",
            "status": "FAIL",
            "confidence_score": 0.09,
            "description": "Low semantic relevance: 0.09 - tags don't semantically match content",
            "suggestion": "Review and update tags to better match the content semantics",
            "autoFixable": False,
            "category": "tagging",
            "type": "semantic_relevance",
            "severity": "medium",
            "processing_time_ms": 580,
            "executed_at": "2024-12-15T14:20:16Z",
            "failure_reason": "Semantic similarity between tags and content is below threshold",
            "metadata": {
                "similarity_threshold": 0.7,
                "actual_similarity": 0.09,
                "mismatched_tags": ["policy", "workflow"]
            }
        },
        {
            "check_name": "llm_semantic_validation",
            "status": "PASS",
            "confidence_score": 0.92,
            "description": "Content is semantically coherent and well-structured",
            "suggestion": "Consider adding more specific industry terminology",
            "autoFixable": False,
            "category": "llm",
            "type": "llm_semantic_validation",
            "severity": "low",
            "processing_time_ms": 1850,
            "executed_at": "2024-12-15T14:20:18Z",
            "metadata": {
                "coherence_score": 0.91,
                "relevance_score": 0.93,
                "completeness_score": 0.89,
                "llm_model": "gpt-4",
                "prompt_version": "v2.1"
            }
        },
        {
            "check_name": "duplicate_detection",
            "status": "PASS",
            "confidence_score": 0.82,
            "description": "No duplicate content detected",
            "suggestion": "",
            "autoFixable": False,
            "category": "content",
            "type": "duplicate_detection",
            "severity": "medium",
            "processing_time_ms": 580,
            "executed_at": "2024-12-15T14:20:17Z",
            "metadata": {
                "similarity_threshold": 0.85,
                "max_similarity_found": 0.23,
                "compared_documents": 1247
            }
        },
        {
            "check_name": "tag_count_validation",
            "status": "PASS",
            "confidence_score": 1.0,
            "description": "Tag count is within acceptable range (6 tags)",
            "suggestion": "",
            "autoFixable": True,
            "category": "tagging",
            "type": "tag_count_validation",
            "severity": "low",
            "processing_time_ms": 15,
            "executed_at": "2024-12-15T14:20:15Z",
            "metadata": {
                "min_tags": 2,
                "max_tags": 15,
                "actual_count": 6
            }
        },
        {
            "check_name": "domain_relevance",
            "status": "FAIL",
            "confidence_score": 0.17,
            "description": "Low domain relevance: 0.17 - tags don't match content domain",
            "suggestion": "Use domain-specific tags that better represent the business context",
            "autoFixable": False,
            "category": "tagging",
            "type": "domain_relevance",
            "severity": "medium",
            "processing_time_ms": 420,
            "executed_at": "2024-12-15T14:20:16Z",
            "failure_reason": "Tags don't align with the identified content domain (finance/policy)",
            "metadata": {
                "detected_domain": "finance_policy",
                "domain_confidence": 0.85,
                "suggested_tags": ["finance", "reimbursement", "expense_policy"]
            }
        },
        {
            "check_name": "spam_pattern_detection",
            "status": "PASS",
            "confidence_score": 0.98,
            "description": "No spam patterns detected",
            "suggestion": "",
            "autoFixable": False,
            "category": "content",
            "type": "spam_pattern_detection",
            "severity": "high",
            "processing_time_ms": 125,
            "executed_at": "2024-12-15T14:20:15Z",
            "metadata": {
                "patterns_checked": 15,
                "spam_indicators": 0,
                "quality_indicators": 8
            }
        }
    ]
    
    # Calculate summary statistics
    total_checks = len(sample_quality_checks)
    passed_checks = len([c for c in sample_quality_checks if c["status"] == "PASS"])
    failed_checks = total_checks - passed_checks
    avg_confidence = sum(c["confidence_score"] for c in sample_quality_checks) / total_checks
    total_processing_time = sum(c["processing_time_ms"] for c in sample_quality_checks)
    
    # Separate LLM and Rules Engine checks
    llm_checks = [c for c in sample_quality_checks if c["category"] == "llm"]
    rules_checks = [c for c in sample_quality_checks if c["category"] != "llm"]
    
    llm_confidence = sum(c["confidence_score"] for c in llm_checks) / len(llm_checks) if llm_checks else 0
    rules_confidence = sum(c["confidence_score"] for c in rules_checks) / len(rules_checks) if rules_checks else 0
    
    return {
        "record_id": record_id,
        "quality_checks": sample_quality_checks,
        "summary": {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "pass_rate": (passed_checks / total_checks) * 100,
            "avg_confidence": avg_confidence,
            "total_processing_time_ms": total_processing_time,
            "llm_confidence": llm_confidence,
            "rules_engine_confidence": rules_confidence
        },
        "categories": {
            "content": len([c for c in sample_quality_checks if c["category"] == "content"]),
            "tagging": len([c for c in sample_quality_checks if c["category"] == "tagging"]),
            "compliance": len([c for c in sample_quality_checks if c["category"] == "compliance"]),
            "llm": len([c for c in sample_quality_checks if c["category"] == "llm"])
        },
        "issues": [
            {
                "id": f"issue-{record_id}-{check['check_name']}",
                "type": check["check_name"],
                "severity": check["severity"],
                "description": check["description"],
                "suggestion": check["suggestion"],
                "autoFixable": check["autoFixable"],
                "category": check["category"],
                "confidence": check["confidence_score"]
            }
            for check in sample_quality_checks if check["status"] != "PASS"
        ]
    }


# Test endpoint for comprehensive record with quality checks
@app.get("/test/record/{record_id}")
async def get_test_record_with_quality_checks(record_id: str):
    """Test endpoint that returns a record with comprehensive quality checks"""
    
    # Get quality checks
    quality_data = await get_test_quality_checks(record_id)
    
    # Sample record data
    return {
        "id": record_id,
        "recordId": record_id,
        "companyId": "company-test",
        "companyName": "Test Company",
        "sourceConnectorName": "SharePoint",
        "sourceConnectorType": "sharepoint",
        "content": "To request a refund, employees must complete the reimbursement form and submit it to the finance department within 14 days of purchase. The form must include the original receipt, reason for the expense, and be approved by the department manager before processing.",
        "contentPreview": "To request a refund, employees must complete the reimbursement form and submit it to the finance department within 14 days...",
        "tags": ["reimbursement process", "finance policy", "employee expense", "receipt submission", "approval workflow", "refund request"],
        "status": "flagged" if quality_data["summary"]["failed_checks"] > 0 else "approved",
        "qualityScore": quality_data["summary"]["pass_rate"],
        "confidenceScore": quality_data["summary"]["avg_confidence"],
        "llm_confidence": quality_data["summary"]["llm_confidence"],
        "rules_engine_confidence": quality_data["summary"]["rules_engine_confidence"],
        "quality_checks": quality_data["quality_checks"],
        "issues": quality_data["issues"],
        "metadata": {
            "author": "HR Department",
            "department": "Human Resources",
            "documentType": "policy",
            "lastModified": "2024-12-15T14:18:30Z",
            "fileSize": 2847,
            "language": "en",
            "wordCount": 42,
            "sensitivity": "internal"
        },
        "createdAt": "2024-12-15T14:18:30Z",
        "updatedAt": "2024-12-15T14:20:18Z",
        "priority": "medium",
        "processingTimeMs": quality_data["summary"]["total_processing_time_ms"],
        "trace_id": f"trace-{record_id}",
        "llmSuggestions": [
            "Consider adding more specific metrics and KPIs to support strategic recommendations",
            "Include competitive benchmarking data for better market positioning",
            "Review and update tags to better match the content semantics"
        ],
        "llmReasoning": "The content is well-structured and provides clear procedural information for employee reimbursements. However, the tagging could be improved to better reflect the specific domain and context of the content."
    }

# =============================================================================
# DYNAMIC RULES & WEIGHTS MANAGEMENT API ENDPOINTS
# =============================================================================

class RuleUpdateRequest(BaseModel):
    """Request model for updating rule properties"""
    rule_name: str
    weight: Optional[float] = None
    enabled: Optional[bool] = None
    changed_by: str = "admin"
    reason: str = "Manual update"

class ThresholdUpdateRequestV2(BaseModel):
    """Enhanced request model for updating thresholds"""
    threshold_name: str
    new_value: float
    changed_by: str = "admin"
    reason: str = "Manual update"

class BulkRuleUpdateRequest(BaseModel):
    """Request model for bulk rule updates"""
    updates: List[RuleUpdateRequest]
    changed_by: str = "admin"
    reason: str = "Bulk update"

class BulkThresholdUpdateRequest(BaseModel):
    """Request model for bulk threshold updates"""
    updates: List[ThresholdUpdateRequestV2]
    changed_by: str = "admin"
    reason: str = "Bulk update"

@app.get("/dynamic-rules/rules")
async def get_all_dynamic_rules():
    """Get all quality rules with their current weights and settings"""
    try:
        if not rules_manager:
            raise HTTPException(status_code=503, detail="Dynamic Rules Manager not available")
        
        rules = rules_manager.get_all_rules()
        return {
            "success": True,
            "rules": [
                {
                    "name": rule.name,
                    "display_name": rule.display_name,
                    "description": rule.description,
                    "category": rule.category.value,
                    "severity": rule.severity.value,
                    "weight": rule.weight,
                    "enabled": rule.enabled,
                    "threshold_value": rule.threshold_value,
                    "auto_fixable": rule.auto_fixable,
                    "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
                }
                for rule in rules.values()
            ],
            "total_count": len(rules)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rules: {str(e)}")

@app.put("/dynamic-rules/rules/{rule_name}/weight")
async def update_rule_weight(rule_name: str, request: RuleUpdateRequest):
    """Update rule weight in real-time"""
    try:
        if not rules_manager:
            raise HTTPException(status_code=503, detail="Dynamic Rules Manager not available")
        
        if request.weight is None:
            raise HTTPException(status_code=400, detail="Weight value is required")
        
        success = rules_manager.update_rule_weight(
            rule_name=rule_name,
            new_weight=request.weight,
            changed_by=request.changed_by,
            reason=request.reason
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update rule weight")
        
        # Get updated rule
        rule = rules_manager.get_rule(rule_name)
        
        return {
            "success": True,
            "message": f"Rule weight updated: {rule_name} = {request.weight}",
            "rule": {
                "name": rule.name,
                "weight": rule.weight,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rule weight: {str(e)}")

@app.get("/dynamic-rules/thresholds")
async def get_all_dynamic_thresholds():
    """Get all quality thresholds with their current values"""
    try:
        if not rules_manager:
            raise HTTPException(status_code=503, detail="Dynamic Rules Manager not available")
        
        thresholds = rules_manager.get_all_thresholds()
        return {
            "success": True,
            "thresholds": [
                {
                    "name": threshold.name,
                    "display_name": threshold.display_name,
                    "current_value": threshold.current_value,
                    "default_value": threshold.default_value,
                    "min_value": threshold.min_value,
                    "max_value": threshold.max_value,
                    "description": threshold.description,
                    "category": threshold.category,
                    "unit": threshold.unit,
                    "affects_rules": threshold.affects_rules,
                    "updated_at": threshold.updated_at.isoformat() if threshold.updated_at else None
                }
                for threshold in thresholds.values()
            ],
            "total_count": len(thresholds)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get thresholds: {str(e)}")

@app.put("/dynamic-rules/thresholds/{threshold_name}")
async def update_dynamic_threshold(threshold_name: str, request: ThresholdUpdateRequestV2):
    """Update threshold value in real-time"""
    try:
        # Get dynamic rules manager directly instead of using global variable
        dynamic_manager = get_dynamic_rules_manager()
        
        success = dynamic_manager.update_threshold_value(
            threshold_name=threshold_name,
            new_value=request.new_value,
            changed_by=request.changed_by,
            reason=request.reason
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update threshold")
        
        # Get updated threshold
        threshold = rules_manager.get_threshold(threshold_name)
        
        return {
            "success": True,
            "message": f"Threshold updated: {threshold_name} = {request.new_value}",
            "threshold": {
                "name": threshold.name,
                "current_value": threshold.current_value,
                "updated_at": threshold.updated_at.isoformat() if threshold.updated_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update threshold: {str(e)}")

@app.post("/dynamic-rules/rules/bulk-update")
async def bulk_update_rules(request: BulkRuleUpdateRequest):
    """Update multiple rules at once"""
    try:
        if not rules_manager:
            raise HTTPException(status_code=503, detail="Dynamic Rules Manager not available")
        
        results = {}
        success_count = 0
        
        for update in request.updates:
            try:
                if update.weight is not None:
                    success = rules_manager.update_rule_weight(
                        rule_name=update.rule_name,
                        new_weight=update.weight,
                        changed_by=request.changed_by,
                        reason=request.reason
                    )
                    
                    if success:
                        success_count += 1
                        results[update.rule_name] = {
                            "success": True,
                            "weight": update.weight
                        }
                    else:
                        results[update.rule_name] = {
                            "success": False,
                            "error": "Failed to update weight"
                        }
                        
            except Exception as e:
                results[update.rule_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        return {
            "success": True,
            "message": f"Updated {success_count}/{len(request.updates)} rules",
            "results": results,
            "success_count": success_count,
            "total_count": len(request.updates)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk update rules: {str(e)}")

@app.get("/dynamic-rules/calculate-weighted-score")
async def calculate_weighted_score_endpoint(
    rule_results: str = None  # JSON string of rule results
):
    """Calculate weighted quality score based on current rule weights"""
    try:
        if not rules_manager:
            raise HTTPException(status_code=503, detail="Dynamic Rules Manager not available")
        
        if not rule_results:
            raise HTTPException(status_code=400, detail="Rule results are required")
        
        import json
        try:
            results = json.loads(rule_results)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in rule_results")
        
        weighted_score = rules_manager.calculate_weighted_score(results)
        
        return {
            "success": True,
            "weighted_score": weighted_score,
            "rule_count": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate weighted score: {str(e)}")

if __name__ == "__main__":
    print(f"""
🚀 Starting Enhanced Indexing QA Tool - Local Development Mode
============================================================
📡 Core Endpoints:
  🏠 Home:           http://127.0.0.1:8000/
  📋 API Docs:       http://127.0.0.1:8000/docs
  ❤️  Health Check:   http://127.0.0.1:8000/health
  📊 Statistics:     http://127.0.0.1:8000/stats
  🧪 Self Test:      http://127.0.0.1:8000/test

🔬 Analysis Endpoints:
  📥 Ingest Content: POST http://127.0.0.1:8000/ingest
  ⚡ Rules Check:   POST http://127.0.0.1:8000/rules/check
  🧠 LLM Analysis:  POST http://127.0.0.1:8000/llm/analyze

🎯 Enhanced Features:
  🔧 Custom LLM:    POST http://127.0.0.1:8000/llm/custom-analyze
  🛡️  Red Team:     POST http://127.0.0.1:8000/llm/redteam
  📊 Red Results:   GET  http://127.0.0.1:8000/redteam/results

✨ New Capabilities:
  • Custom LLM prompts with {{placeholders}}
  • Quality constraints with configurable weights
  • Red team testing scenarios
  • Advanced attack simulation
  • Constraint-based scoring

📝 Quick Test Commands:
  curl http://127.0.0.1:8000/health
  curl http://127.0.0.1:8000/test

⚠️  Note: Enhanced version with advanced features
   - Uses in-memory storage (data lost on restart)
   - {"Rules engine available" if RULES_ENGINE_AVAILABLE else "Rules engine NOT available (using mocks)"}
   - Custom LLM prompt support
   - Red team testing scenarios

🔗 Full Integration:
   1. Install all dependencies: pip install -r requirements.txt
   2. Configure LLM API keys in .env
   3. Use production API: uvicorn api:app --reload

🚀 Starting enhanced server...
""")
    
    # Start server with config settings - Fixed startup configuration
    uvicorn.run(
        app,
        host='127.0.0.1',
        port=8000,
        reload=False,  # Disabled reload to fix startup crashes
        log_level="info",
        access_log=True
    )