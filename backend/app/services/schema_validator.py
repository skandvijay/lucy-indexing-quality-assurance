"""
Schema Validator for Indexing QA Observability Tool
Validates input data structure and format before processing
Ensures data integrity and prevents invalid records from entering the pipeline
"""

import re
import json
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ValidationError
from ..models.models import ChunkIngestRequest, QualityCheckResult, FlagStatus
from ..core.config import get_settings


class SchemaValidationError(Exception):
    """Custom exception for schema validation errors"""
    pass


class ValidationSeverity(str, Enum):
    """Severity levels for validation errors"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SchemaValidationResult(BaseModel):
    """Result of schema validation"""
    is_valid: bool
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    sanitized_data: Optional[Dict[str, Any]] = None
    validation_time_ms: float = 0.0


class SchemaValidator:
    """
    Comprehensive schema validation for chunk ingestion
    Validates data structure, format, and business rules before processing
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._init_validation_rules()
    
    def _init_validation_rules(self):
        """Initialize validation rules and patterns"""
        self.validation_rules = {
            'record_id': {
                'required': True,
                'type': str,
                'min_length': 1,
                'max_length': 256,
                'pattern': r'^[a-zA-Z0-9_-]+$',
                'description': 'Record ID must be alphanumeric with underscores/hyphens'
            },
            'document_text': {
                'required': True,
                'type': str,
                'min_length': 10,
                'max_length': 100000,
                'description': 'Document text must be between 10-100000 characters'
            },
            'tags': {
                'required': True,
                'type': list,
                'min_items': 1,
                'max_items': 50,
                'item_type': str,
                'item_min_length': 1,
                'item_max_length': 100,
                'description': 'Tags must be 1-50 non-empty strings, each 1-100 characters'
            },
            'source_connector': {
                'required': True,
                'type': str,
                'min_length': 1,
                'max_length': 50,
                'allowed_values': [
                    'SharePoint', 'Confluence', 'Notion', 'GDrive', 
                    'Elasticsearch', 'Custom', 'Unknown'
                ],
                'description': 'Source connector must be a valid connector type'
            },
            'file_id': {
                'required': True,
                'type': str,
                'min_length': 1,
                'max_length': 256,
                'description': 'File ID must be 1-256 characters'
            },
            'created_at': {
                'required': False,
                'type': datetime,
                'description': 'Created at timestamp (optional, auto-generated if missing)'
            },
            'content_metadata': {
                'required': False,
                'type': dict,
                'description': 'Optional metadata dictionary'
            }
        }
        
        # Dangerous patterns to detect
        self.dangerous_patterns = [
            {
                'pattern': r'<script[^>]*>.*?</script>',
                'name': 'script_injection',
                'severity': ValidationSeverity.CRITICAL,
                'description': 'Potential script injection detected'
            },
            {
                'pattern': r'javascript:',
                'name': 'javascript_url',
                'severity': ValidationSeverity.HIGH,
                'description': 'JavaScript URL detected'
            },
            {
                'pattern': r'(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\s+',
                'name': 'sql_injection',
                'severity': ValidationSeverity.HIGH,
                'description': 'Potential SQL injection detected'
            },
            {
                'pattern': r'(\.\./|\.\.\\)',
                'name': 'path_traversal',
                'severity': ValidationSeverity.MEDIUM,
                'description': 'Path traversal pattern detected'
            }
        ]
    
    def validate_chunk(self, data: Dict[str, Any]) -> SchemaValidationResult:
        """
        Validate a chunk data structure
        
        Args:
            data: Raw input data dictionary
            
        Returns:
            SchemaValidationResult with validation status and details
        """
        start_time = time.time()
        errors = []
        warnings = []
        sanitized_data = {}
        
        try:
            # 1. Basic structure validation
            structure_errors = self._validate_structure(data)
            errors.extend(structure_errors)
            
            # 2. Field-by-field validation
            field_errors, field_warnings, sanitized_fields = self._validate_fields(data)
            errors.extend(field_errors)
            warnings.extend(field_warnings)
            sanitized_data.update(sanitized_fields)
            
            # 3. Security validation
            security_errors = self._validate_security(data)
            errors.extend(security_errors)
            
            # 4. Business rules validation
            business_errors, business_warnings = self._validate_business_rules(data)
            errors.extend(business_errors)
            warnings.extend(business_warnings)
            
            # 5. Pydantic model validation (if basic validation passes)
            if not errors:
                pydantic_errors = self._validate_pydantic_model(sanitized_data)
                errors.extend(pydantic_errors)
            
            validation_time = (time.time() - start_time) * 1000
            
            return SchemaValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                sanitized_data=sanitized_data if len(errors) == 0 else None,
                validation_time_ms=validation_time
            )
            
        except Exception as e:
            validation_time = (time.time() - start_time) * 1000
            return SchemaValidationResult(
                is_valid=False,
                errors=[{
                    'field': 'validation_system',
                    'code': 'VALIDATION_ERROR',
                    'message': f'Schema validation system error: {str(e)}',
                    'severity': ValidationSeverity.CRITICAL
                }],
                validation_time_ms=validation_time
            )
    
    def _validate_structure(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate basic data structure"""
        errors = []
        
        if not isinstance(data, dict):
            errors.append({
                'field': 'root',
                'code': 'INVALID_TYPE',
                'message': 'Input must be a dictionary/object',
                'severity': ValidationSeverity.CRITICAL
            })
            return errors
        
        # Check for required fields
        required_fields = [field for field, rules in self.validation_rules.items() 
                          if rules.get('required', False)]
        
        for field in required_fields:
            if field not in data:
                errors.append({
                    'field': field,
                    'code': 'MISSING_FIELD',
                    'message': f'Required field "{field}" is missing',
                    'severity': ValidationSeverity.CRITICAL
                })
            elif data[field] is None:
                errors.append({
                    'field': field,
                    'code': 'NULL_VALUE',
                    'message': f'Required field "{field}" cannot be null',
                    'severity': ValidationSeverity.CRITICAL
                })
        
        return errors
    
    def _validate_fields(self, data: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """Validate individual fields"""
        errors = []
        warnings = []
        sanitized_data = {}
        
        for field_name, field_value in data.items():
            if field_name not in self.validation_rules:
                warnings.append({
                    'field': field_name,
                    'code': 'UNKNOWN_FIELD',
                    'message': f'Unknown field "{field_name}" will be ignored',
                    'severity': ValidationSeverity.LOW
                })
                continue
            
            rules = self.validation_rules[field_name]
            field_errors, sanitized_value = self._validate_field(field_name, field_value, rules)
            errors.extend(field_errors)
            
            if not field_errors and sanitized_value is not None:
                sanitized_data[field_name] = sanitized_value
        
        return errors, warnings, sanitized_data
    
    def _validate_field(self, field_name: str, value: Any, rules: Dict[str, Any]) -> tuple[List[Dict[str, Any]], Any]:
        """Validate a single field"""
        errors = []
        sanitized_value = value
        
        # Type validation
        expected_type = rules.get('type')
        if expected_type and not isinstance(value, expected_type):
            errors.append({
                'field': field_name,
                'code': 'INVALID_TYPE',
                'message': f'Field "{field_name}" must be of type {expected_type.__name__}',
                'severity': ValidationSeverity.HIGH
            })
            return errors, None
        
        # String validations
        if isinstance(value, str):
            # Length validation
            if 'min_length' in rules and len(value) < rules['min_length']:
                errors.append({
                    'field': field_name,
                    'code': 'TOO_SHORT',
                    'message': f'Field "{field_name}" must be at least {rules["min_length"]} characters',
                    'severity': ValidationSeverity.HIGH
                })
            
            if 'max_length' in rules and len(value) > rules['max_length']:
                errors.append({
                    'field': field_name,
                    'code': 'TOO_LONG',
                    'message': f'Field "{field_name}" must be at most {rules["max_length"]} characters',
                    'severity': ValidationSeverity.HIGH
                })
            
            # Pattern validation
            if 'pattern' in rules:
                pattern = rules['pattern']
                if not re.match(pattern, value):
                    errors.append({
                        'field': field_name,
                        'code': 'INVALID_PATTERN',
                        'message': f'Field "{field_name}" format is invalid. {rules.get("description", "")}',
                        'severity': ValidationSeverity.HIGH
                    })
            
            # Allowed values validation
            if 'allowed_values' in rules and value not in rules['allowed_values']:
                errors.append({
                    'field': field_name,
                    'code': 'INVALID_VALUE',
                    'message': f'Field "{field_name}" must be one of: {", ".join(rules["allowed_values"])}',
                    'severity': ValidationSeverity.MEDIUM
                })
            
            # Sanitize string (trim whitespace)
            sanitized_value = value.strip()
        
        # List validations
        elif isinstance(value, list):
            if 'min_items' in rules and len(value) < rules['min_items']:
                errors.append({
                    'field': field_name,
                    'code': 'TOO_FEW_ITEMS',
                    'message': f'Field "{field_name}" must have at least {rules["min_items"]} items',
                    'severity': ValidationSeverity.HIGH
                })
            
            if 'max_items' in rules and len(value) > rules['max_items']:
                errors.append({
                    'field': field_name,
                    'code': 'TOO_MANY_ITEMS',
                    'message': f'Field "{field_name}" must have at most {rules["max_items"]} items',
                    'severity': ValidationSeverity.HIGH
                })
            
            # Validate list items
            if 'item_type' in rules:
                sanitized_items = []
                for i, item in enumerate(value):
                    if not isinstance(item, rules['item_type']):
                        errors.append({
                            'field': f'{field_name}[{i}]',
                            'code': 'INVALID_ITEM_TYPE',
                            'message': f'Item {i} in "{field_name}" must be of type {rules["item_type"].__name__}',
                            'severity': ValidationSeverity.HIGH
                        })
                        continue
                    
                    # String item validations
                    if isinstance(item, str):
                        if 'item_min_length' in rules and len(item) < rules['item_min_length']:
                            errors.append({
                                'field': f'{field_name}[{i}]',
                                'code': 'ITEM_TOO_SHORT',
                                'message': f'Item {i} in "{field_name}" must be at least {rules["item_min_length"]} characters',
                                'severity': ValidationSeverity.HIGH
                            })
                            continue
                        
                        if 'item_max_length' in rules and len(item) > rules['item_max_length']:
                            errors.append({
                                'field': f'{field_name}[{i}]',
                                'code': 'ITEM_TOO_LONG',
                                'message': f'Item {i} in "{field_name}" must be at most {rules["item_max_length"]} characters',
                                'severity': ValidationSeverity.HIGH
                            })
                            continue
                        
                        # Sanitize item
                        sanitized_items.append(item.strip())
                    else:
                        sanitized_items.append(item)
                
                if not errors:
                    sanitized_value = sanitized_items
        
        return errors, sanitized_value
    
    def _validate_security(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate for security threats"""
        errors = []
        
        # Check text fields for dangerous patterns
        text_fields = ['document_text', 'tags', 'record_id', 'file_id']
        
        for field_name in text_fields:
            if field_name not in data:
                continue
                
            field_value = data[field_name]
            
            # Handle both strings and lists
            text_values = []
            if isinstance(field_value, str):
                text_values = [field_value]
            elif isinstance(field_value, list):
                text_values = [str(item) for item in field_value if item is not None]
            
            for text_value in text_values:
                for pattern_info in self.dangerous_patterns:
                    if re.search(pattern_info['pattern'], text_value, re.IGNORECASE):
                        errors.append({
                            'field': field_name,
                            'code': 'SECURITY_THREAT',
                            'message': f'Security threat detected in "{field_name}": {pattern_info["description"]}',
                            'severity': pattern_info['severity'],
                            'threat_type': pattern_info['name']
                        })
        
        return errors
    
    def _validate_business_rules(self, data: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate business-specific rules"""
        errors = []
        warnings = []
        
        # Check for duplicate tags
        if 'tags' in data and isinstance(data['tags'], list):
            tags = data['tags']
            if len(tags) != len(set(tags)):
                warnings.append({
                    'field': 'tags',
                    'code': 'DUPLICATE_TAGS',
                    'message': 'Duplicate tags detected and will be removed',
                    'severity': ValidationSeverity.LOW
                })
        
        # Check for reasonable timestamp
        if 'created_at' in data and data['created_at']:
            created_at = data['created_at']
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except ValueError:
                    errors.append({
                        'field': 'created_at',
                        'code': 'INVALID_TIMESTAMP',
                        'message': 'Invalid timestamp format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)',
                        'severity': ValidationSeverity.HIGH
                    })
                    return errors, warnings
            
            # Check if timestamp is reasonable (not too far in future/past)
            now = datetime.now(timezone.utc)
            if created_at > now:
                warnings.append({
                    'field': 'created_at',
                    'code': 'FUTURE_TIMESTAMP',
                    'message': 'Timestamp is in the future',
                    'severity': ValidationSeverity.LOW
                })
            elif (now - created_at).days > 365:
                warnings.append({
                    'field': 'created_at',
                    'code': 'OLD_TIMESTAMP',
                    'message': 'Timestamp is more than 1 year old',
                    'severity': ValidationSeverity.LOW
                })
        
        # Check document text quality
        if 'document_text' in data:
            text = data['document_text']
            if isinstance(text, str):
                # Check for mostly non-printable characters
                printable_chars = sum(1 for c in text if c.isprintable())
                if printable_chars < len(text) * 0.8:
                    errors.append({
                        'field': 'document_text',
                        'code': 'INVALID_ENCODING',
                        'message': 'Document text contains too many non-printable characters',
                        'severity': ValidationSeverity.HIGH
                    })
                
                # Check for extremely repetitive content
                if len(set(text.split())) < len(text.split()) * 0.1:
                    warnings.append({
                        'field': 'document_text',
                        'code': 'REPETITIVE_CONTENT',
                        'message': 'Document text appears highly repetitive',
                        'severity': ValidationSeverity.MEDIUM
                    })
        
        return errors, warnings
    
    def _validate_pydantic_model(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Final validation using Pydantic model"""
        errors = []
        
        try:
            # Try to create ChunkIngestRequest model
            ChunkIngestRequest(**data)
        except ValidationError as e:
            for error in e.errors():
                field_path = '.'.join(str(x) for x in error['loc'])
                errors.append({
                    'field': field_path,
                    'code': 'PYDANTIC_VALIDATION',
                    'message': f'Pydantic validation failed: {error["msg"]}',
                    'severity': ValidationSeverity.HIGH
                })
        except Exception as e:
            errors.append({
                'field': 'model_validation',
                'code': 'MODEL_ERROR',
                'message': f'Model validation error: {str(e)}',
                'severity': ValidationSeverity.CRITICAL
            })
        
        return errors
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            'total_rules': len(self.validation_rules),
            'security_patterns': len(self.dangerous_patterns),
            'supported_fields': list(self.validation_rules.keys()),
            'version': '1.0.0'
        } 