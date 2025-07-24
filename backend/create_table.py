#!/usr/bin/env python3
import sqlite3

# Create the missing processed_records table
conn = sqlite3.connect('indexing_qa.db')
cursor = conn.cursor()

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
        issues TEXT
    )
''')

# Also create other required tables
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
        source_connector TEXT
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

conn.commit()
conn.close()

print("Database tables created successfully!") 