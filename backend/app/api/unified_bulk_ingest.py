"""
Unified Bulk + Streaming Ingestion API
Processes multiple records through the same robust pipeline as single /ingest endpoint
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, UTC
from typing import List, Dict, Any, AsyncGenerator, Optional, Union, Callable
from fastapi import HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import logging

from ..models.models import ChunkIngestRequest
# ContentIngestRequest is defined in api.py, will be passed as parameter

logger = logging.getLogger(__name__)

class UnifiedBulkProcessor:
    """
    Unified processor that routes all bulk ingestion through the existing /ingest pipeline
    Ensures consistent quality analysis, LLM processing, and error handling
    """
    
    def __init__(self, ingest_function: Callable = None):
        self.processing_stats = {
            "total_processed": 0,
            "total_errors": 0,
            "start_time": time.time()
        }
        self.ingest_function = ingest_function
    
    def set_ingest_function(self, ingest_function: Callable):
        """Set the ingest function to avoid circular imports"""
        self.ingest_function = ingest_function
    
    async def process_single_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single record through the existing /ingest pipeline
        Normalizes different input formats to the standard ContentIngestRequest
        """
        try:
            if not self.ingest_function:
                raise Exception("Ingest function not set - call set_ingest_function() first")
                
            # Normalize field names from various input formats
            normalized_data = self._normalize_record_fields(record_data)
            
            # Create request data for the existing pipeline
            # ContentIngestRequest will be created in the calling function
            content_request = {
                "record_id": normalized_data["record_id"],
                "content": normalized_data["content"],
                "tags": normalized_data["tags"],
                "source_connector": normalized_data["source_connector"],
                "content_metadata": normalized_data.get("content_metadata", {})
            }
            
            # Use the existing robust /ingest pipeline
            result = await self.ingest_function(content_request)
            
            self.processing_stats["total_processed"] += 1
            return {
                "status": "success",
                "record_id": normalized_data["record_id"],
                "result": result
            }
            
        except Exception as e:
            self.processing_stats["total_errors"] += 1
            return {
                "status": "error",
                "record_id": record_data.get("record_id", "unknown"),
                "error": str(e),
                "original_data": record_data
            }
    
    def _normalize_record_fields(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize various input formats to standard ContentIngestRequest format
        Handles: SharePoint, Elasticsearch, external APIs, file uploads, etc.
        """
        # Extract content from various possible field names
        content = (
            record_data.get("content") or
            record_data.get("document_text") or  # ChunkIngestRequest format
            record_data.get("text") or
            record_data.get("body") or
            record_data.get("description") or
            record_data.get("combined_data") or  # Elasticsearch format
            record_data.get("parser_data") or
            str(record_data.get("title", ""))
        )
        
        # Extract tags from various formats
        tags = []
        possible_tag_fields = ["tags", "categories", "labels", "keywords"]
        for field in possible_tag_fields:
            if field in record_data and record_data[field]:
                field_value = record_data[field]
                if isinstance(field_value, list):
                    tags.extend([str(tag) for tag in field_value])
                elif isinstance(field_value, str):
                    tags.extend([tag.strip() for tag in field_value.split(",")])
        
        # Default tags if none found
        if not tags:
            tags = ["bulk-import", "auto-generated"]
        
        # Extract or generate record ID
        record_id = (
            record_data.get("record_id") or
            record_data.get("id") or
            record_data.get("external_id") or
            f"bulk-{int(time.time())}-{abs(hash(content[:100])) % 10000}"
        )
        
        # Determine source connector
        source_connector = (
            record_data.get("source_connector") or
            record_data.get("source_type") or
            "Custom"
        )
        
        # Validate source connector format
        valid_connectors = ["SharePoint", "Confluence", "Notion", "GDrive", "Elasticsearch", "Custom", "Unknown"]
        if source_connector not in valid_connectors:
            source_connector = "Custom"
        
        # Extract metadata
        content_metadata = record_data.get("content_metadata", {})
        if not content_metadata:
            # Build metadata from available fields
            content_metadata = {
                "author": record_data.get("author", ""),
                "created_date": record_data.get("created_at", ""),
                "source_url": record_data.get("source_url", ""),
                "company": record_data.get("company", ""),
                "bulk_import": True,
                "original_format": list(record_data.keys())  # Track original fields
            }
        
        return {
            "record_id": str(record_id),
            "content": content,
            "tags": tags,
            "source_connector": source_connector,
            "content_metadata": content_metadata
        }
    
    async def process_batch_stream(
        self, 
        records: List[Dict[str, Any]], 
        batch_size: int = 10,
        concurrent_limit: int = 5
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process records in streaming batches with concurrency control
        Yields real-time progress updates
        """
        total_records = len(records)
        processed_count = 0
        
        # Process in batches to manage memory and provide streaming updates
        for i in range(0, total_records, batch_size):
            batch = records[i:i + batch_size]
            batch_start_time = time.time()
            
            # Process batch with concurrency control
            semaphore = asyncio.Semaphore(concurrent_limit)
            
            async def process_with_semaphore(record):
                async with semaphore:
                    return await self.process_single_record(record)
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(
                *[process_with_semaphore(record) for record in batch],
                return_exceptions=True
            )
            
            # Handle any exceptions in results
            processed_results = []
            for result in batch_results:
                if isinstance(result, Exception):
                    processed_results.append({
                        "status": "error",
                        "error": str(result),
                        "record_id": "unknown"
                    })
                else:
                    processed_results.append(result)
            
            processed_count += len(batch)
            batch_time = time.time() - batch_start_time
            
            # Yield streaming update
            yield {
                "batch_number": (i // batch_size) + 1,
                "total_batches": (total_records + batch_size - 1) // batch_size,
                "processed_in_batch": len(batch),
                "total_processed": processed_count,
                "total_records": total_records,
                "progress_percentage": round((processed_count / total_records) * 100, 2),
                "batch_processing_time_ms": round(batch_time * 1000, 2),
                "estimated_time_remaining_seconds": round(
                    (batch_time * ((total_records - processed_count) / len(batch))) if processed_count < total_records else 0, 
                    2
                ),
                "batch_results": processed_results,
                "processing_stats": {
                    "total_processed": self.processing_stats["total_processed"],
                    "total_errors": self.processing_stats["total_errors"],
                    "success_rate": round(
                        (self.processing_stats["total_processed"] / 
                         (self.processing_stats["total_processed"] + self.processing_stats["total_errors"])) * 100, 2
                    ) if (self.processing_stats["total_processed"] + self.processing_stats["total_errors"]) > 0 else 0
                }
            }

# Global processor instance - will be initialized after importing ingest function
bulk_processor = UnifiedBulkProcessor()

async def extract_records_from_upload(file: UploadFile) -> List[Dict[str, Any]]:
    """
    Extract records from uploaded files (JSON, JSONL, CSV)
    Supports multiple formats and automatically detects structure
    """
    try:
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # Detect file format and parse accordingly
        if file.filename.endswith('.json'):
            data = json.loads(file_content)
            
            # Handle different JSON structures
            if isinstance(data, list):
                return data  # Array of records
            elif isinstance(data, dict):
                # Check for common bulk formats
                if "hits" in data and isinstance(data["hits"], list):
                    return data["hits"]  # Elasticsearch format
                elif "answers" in data and isinstance(data["answers"], list):
                    return data["answers"]  # SharePoint format
                elif "chunks" in data and isinstance(data["chunks"], list):
                    return data["chunks"]  # Batch format
                else:
                    return [data]  # Single record
        
        elif file.filename.endswith('.jsonl'):
            # JSON Lines format - one JSON object per line
            records = []
            for line in file_content.strip().split('\n'):
                if line.strip():
                    records.append(json.loads(line.strip()))
            return records
        
        else:
            raise ValueError(f"Unsupported file format: {file.filename}")
            
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File processing failed: {str(e)}")

def create_streaming_response(async_generator) -> StreamingResponse:
    """
    Create a streaming HTTP response for real-time progress updates
    """
    async def generate():
        async for chunk in async_generator:
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    ) 