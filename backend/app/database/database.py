"""
Database configuration and connection management for Indexing QA Observability Tool
Optimized for Azure SQL Database with connection pooling and failover support
"""

import logging
from typing import Generator, Optional, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import DisconnectionError, OperationalError
import time

from ..models.models import Base
from ..core.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()

# Global engine and session factory
engine: Optional[Any] = None
SessionLocal: Optional[Any] = None


def create_database_engine():
    """Create SQLAlchemy engine optimized for Azure SQL Database"""
    global engine
    
    if engine is not None:
        return engine
    
    # Connection string configuration
    database_url = settings.database_url
    
    # Azure SQL specific connection parameters
    connect_args = {}
    if "azure" in database_url.lower() or "database.windows.net" in database_url:
        connect_args = {
            "driver": "ODBC Driver 17 for SQL Server",
            "autocommit": False,
            "timeout": 30,
            "login_timeout": 30,
        }
    
    # Create engine with connection pooling
    execution_options = {}
    
    # Set isolation level based on database type
    if "sqlite" in database_url.lower():
        # SQLite only supports SERIALIZABLE, READ_UNCOMMITTED, or AUTOCOMMIT
        execution_options["isolation_level"] = "SERIALIZABLE"
    else:
        # For Azure SQL and other databases
        execution_options["isolation_level"] = "READ_COMMITTED"
    
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=10,  # Number of connections to maintain
        max_overflow=20,  # Additional connections when pool is full
        pool_pre_ping=True,  # Validate connections before use
        pool_recycle=3600,  # Recycle connections every hour
        echo=False,  # Set to True for SQL debugging
        connect_args=connect_args,
        execution_options=execution_options
    )
    
    # Add connection event listeners for monitoring
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set database-specific connection options"""
        if engine and "sqlite" in str(engine.url):
            # SQLite optimizations for development
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
    
    @event.listens_for(engine, "checkout")
    def ping_connection(dbapi_connection, connection_record, connection_proxy):
        """Ensure connection is alive on checkout"""
        connection_record.info['pid'] = time.time()
    
    logger.info(f"Database engine created for: {mask_connection_string(database_url)}")
    return engine


def create_session_factory():
    """Create session factory"""
    global SessionLocal
    
    if SessionLocal is not None:
        return SessionLocal
    
    engine = create_database_engine()
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False
    )
    
    return SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI
    Provides automatic session management with error handling
    """
    if SessionLocal is None:
        create_session_factory()
    
    if SessionLocal is None:
        raise RuntimeError("Failed to create database session factory")
    
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database sessions outside of FastAPI"""
    if SessionLocal is None:
        create_session_factory()
    
    if SessionLocal is None:
        raise RuntimeError("Failed to create database session factory")
    
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database context error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create all database tables"""
    try:
        engine = create_database_engine()
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully")
        
        # Initialize default threshold configurations
        with get_db_context() as db:
            _initialize_default_thresholds(db)
            
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def _initialize_default_thresholds(db: Session):
    """Initialize default threshold configurations"""
    from ..models.models import ThresholdConfiguration
    
    default_thresholds = [
        {
            "check_name": "empty_tags",
            "threshold_value": 1.0,
            "confidence_cutoff": 0.9,
        },
        {
            "check_name": "tag_count_validation", 
            "threshold_value": float(settings.max_tag_count),
            "confidence_cutoff": 0.8,
        },
        {
            "check_name": "stopwords_detection",
            "threshold_value": settings.stopword_threshold,
            "confidence_cutoff": 0.7,
        },
        {
            "check_name": "spam_pattern_detection",
            "threshold_value": settings.spam_threshold,
            "confidence_cutoff": 0.8,
        },
        {
            "check_name": "duplicate_content_detection",
            "threshold_value": 0.9,
            "confidence_cutoff": 0.9,
        },
        {
            "check_name": "tag_text_relevance",
            "threshold_value": 0.3,
            "confidence_cutoff": 0.6,
        },
        {
            "check_name": "llm_semantic_validation",
            "threshold_value": settings.llm_confidence_threshold,
            "confidence_cutoff": 0.7,
        }
    ]
    
    for threshold_config in default_thresholds:
        # Check if threshold already exists
        existing = db.query(ThresholdConfiguration).filter(
            ThresholdConfiguration.check_name == threshold_config["check_name"]
        ).first()
        
        if not existing:
            new_threshold = ThresholdConfiguration(
                check_name=threshold_config["check_name"],
                threshold_value=threshold_config["threshold_value"],
                confidence_cutoff=threshold_config["confidence_cutoff"],
                updated_by="system_init",
                reason="Initial default configuration"
            )
            db.add(new_threshold)
    
    try:
        db.commit()
        logger.info("Default threshold configurations initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize default thresholds: {e}")
        db.rollback()


def check_database_health() -> Dict[str, Any]:
    """Comprehensive database health check"""
    health_status: Dict[str, Any] = {
        "status": "unknown",
        "connection": False,
        "tables_exist": False,
        "query_performance": None,
        "error": None
    }
    
    try:
        engine = create_database_engine()
        
        # Test basic connection
        start_time = time.time()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            health_status["connection"] = True
            
            # Test query performance
            query_time = (time.time() - start_time) * 1000
            health_status["query_performance"] = f"{query_time:.2f}ms"
            
            # Check if tables exist
            if "sqlite" in str(engine.url):
                table_check = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            else:
                table_check = conn.execute(text("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES"))
            
            tables = [row[0] for row in table_check.fetchall()]
            expected_tables = ["chunk_records", "quality_check_records", "review_records"]
            health_status["tables_exist"] = all(table in tables for table in expected_tables)
            health_status["table_count"] = len(tables)
            
        health_status["status"] = "healthy"
        
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        logger.error(f"Database health check failed: {e}")
    
    return health_status


def get_database_metrics() -> Dict[str, Any]:
    """Get database performance and usage metrics"""
    metrics: Dict[str, Any] = {
        "connection_pool_size": 0,
        "checked_out_connections": 0,
        "overflow_connections": 0,
        "invalid_connections": 0
    }
    
    try:
        engine = create_database_engine()
        
        if hasattr(engine.pool, 'size'):
            metrics["connection_pool_size"] = engine.pool.size()
        if hasattr(engine.pool, 'checkedout'):
            metrics["checked_out_connections"] = engine.pool.checkedout()
        if hasattr(engine.pool, 'overflow'):
            metrics["overflow_connections"] = engine.pool.overflow()
        if hasattr(engine.pool, 'invalidated'):
            metrics["invalid_connections"] = engine.pool.invalidated()
            
    except Exception as e:
        logger.error(f"Failed to get database metrics: {e}")
        metrics["error"] = str(e)
    
    return metrics


def cleanup_old_records(days_to_keep: int = 90):
    """Clean up old records based on retention policy"""
    from datetime import datetime, timedelta, timezone
    from ..models.models import ChunkRecord, DeadLetterRecord, AlertRecord
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    
    try:
        with get_db_context() as db:
            # Clean up old dead letter records
            deleted_dead_letters = db.query(DeadLetterRecord).filter(
                DeadLetterRecord.failed_at < cutoff_date,
                DeadLetterRecord.resolved == True
            ).delete()
            
            # Clean up old alert records
            deleted_alerts = db.query(AlertRecord).filter(
                AlertRecord.sent_at < cutoff_date
            ).delete()
            
            # Optionally clean up old chunk records (be careful with this)
            # deleted_chunks = db.query(ChunkRecord).filter(
            #     ChunkRecord.processed_at < cutoff_date
            # ).delete()
            
            logger.info(f"Cleanup completed: {deleted_dead_letters} dead letters, {deleted_alerts} alerts removed")
            
    except Exception as e:
        logger.error(f"Database cleanup failed: {e}")
        raise


def execute_raw_query(query: str, params: Optional[Dict[str, Any]] = None) -> list:
    """Execute raw SQL query - use with caution"""
    try:
        engine = create_database_engine()
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return [dict(row) for row in result.fetchall()]
    except Exception as e:
        logger.error(f"Raw query execution failed: {e}")
        raise


def mask_connection_string(connection_string: str) -> str:
    """Mask sensitive parts of connection string for logging"""
    import re
    
    # Mask password in connection string
    masked = re.sub(r'(:)([^@/:]+)(@)', r'\1***\3', connection_string)
    
    # Mask API keys
    masked = re.sub(r'(key=)([^;]+)', r'\1***', masked)
    
    return masked


# Database migration utilities
def get_current_schema_version() -> str:
    """Get current database schema version"""
    try:
        with get_db_context() as db:
            result = db.execute(text("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"))
            row = result.fetchone()
            return row[0] if row else "unknown"
    except Exception:
        return "unknown"


def backup_database(backup_path: Optional[str] = None):
    """Create database backup (SQLite only for dev)"""
    if "sqlite" in str(create_database_engine().url):
        import shutil
        import os
        from datetime import datetime, timezone
        
        db_path = str(create_database_engine().url).replace("sqlite:///", "")
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_indexing_qa_{timestamp}.db"
        
        try:
            shutil.copy2(db_path, backup_path)
            logger.info(f"Database backed up to: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            raise
    else:
        logger.warning("Database backup only supported for SQLite in development")


# Connection testing utilities
def test_connection_with_retry(max_retries: int = 3, delay: float = 1.0) -> bool:
    """Test database connection with retry logic"""
    for attempt in range(max_retries):
        try:
            engine = create_database_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info(f"Database connection successful on attempt {attempt + 1}")
                return True
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                logger.error("All database connection attempts failed")
                return False
    
    return False 