#!/usr/bin/env python3
"""
Test script to verify LLM invocation modes work correctly
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_binary_mode():
    """Test binary mode - LLM should only trigger if ALL rules pass"""
    print("🔍 Testing BINARY MODE...")
    
    # Set to binary mode
    response = requests.post(f"{BASE_URL}/settings/llm-mode", json={
        "mode": "binary",
        "reason": "Testing binary mode"
    })
    print(f"✅ Set to binary mode: {response.status_code}")
    
    # Test 1: Content with some failed rules (should NOT trigger LLM)
    print("\n📝 Test 1: Content with failed rules (should NOT trigger LLM)")
    response = requests.post(f"{BASE_URL}/ingest", json={
        "record_id": "test_binary_fail",
        "content": "This is a test document with some quality issues that should not trigger LLM in binary mode.",
        "tags": ["Test", "Document"],
        "source_connector": "Custom",
        "content_metadata": {"title": "Binary Test Fail"}
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Quality Score: {result.get('quality_score')}")
        print(f"   Status: {result.get('status')}")
        print(f"   LLM Confidence: {result.get('llm_confidence')}")
        
        # Check if LLM was triggered (should be 0 or "Not Triggered")
        llm_confidence = result.get('llm_confidence')
        if llm_confidence == 0 or llm_confidence == "Not Triggered":
            print("   ✅ CORRECT: LLM was NOT triggered")
        else:
            print(f"   ❌ ERROR: LLM was triggered with confidence {llm_confidence}")
    else:
        print(f"   ❌ Request failed: {response.status_code}")
    
    # Test 2: Content with all rules passing (should trigger LLM)
    print("\n📝 Test 2: Content with all rules passing (should trigger LLM)")
    response = requests.post(f"{BASE_URL}/ingest", json={
        "record_id": "test_binary_pass",
        "content": "This is a comprehensive document about artificial intelligence and machine learning applications in modern business environments. It covers various algorithms, their implementation strategies, and practical use cases for enterprise organizations.",
        "tags": ["Artificial Intelligence", "Machine Learning", "Business Applications", "Enterprise Technology"],
        "source_connector": "Custom",
        "content_metadata": {"title": "Binary Test Pass"}
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Quality Score: {result.get('quality_score')}")
        print(f"   Status: {result.get('status')}")
        print(f"   LLM Confidence: {result.get('llm_confidence')}")
        
        # Check if LLM was triggered
        llm_confidence = result.get('llm_confidence')
        if llm_confidence and llm_confidence != 0 and llm_confidence != "Not Triggered":
            print("   ✅ CORRECT: LLM was triggered")
        else:
            print(f"   ❌ ERROR: LLM was NOT triggered (confidence: {llm_confidence})")
    else:
        print(f"   ❌ Request failed: {response.status_code}")

def test_percentage_mode():
    """Test percentage mode - LLM triggers if X% of rules pass"""
    print("\n🔍 Testing PERCENTAGE MODE...")
    
    # Set to percentage mode with 80% threshold
    response = requests.post(f"{BASE_URL}/settings/llm-mode", json={
        "mode": "percentage",
        "percentage_threshold": 80.0,
        "reason": "Testing percentage mode"
    })
    print(f"✅ Set to percentage mode (80% threshold): {response.status_code}")
    
    # Test 1: Content with 70% pass rate (should NOT trigger LLM)
    print("\n📝 Test 1: Content with 70% pass rate (should NOT trigger LLM)")
    response = requests.post(f"{BASE_URL}/ingest", json={
        "record_id": "test_percentage_70",
        "content": "This document has some quality issues but is mostly acceptable.",
        "tags": ["Document", "Quality", "Issues"],
        "source_connector": "Custom",
        "content_metadata": {"title": "Percentage Test 70%"}
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Quality Score: {result.get('quality_score')}")
        print(f"   LLM Confidence: {result.get('llm_confidence')}")
        
        llm_confidence = result.get('llm_confidence')
        if llm_confidence == 0 or llm_confidence == "Not Triggered":
            print("   ✅ CORRECT: LLM was NOT triggered")
        else:
            print(f"   ❌ ERROR: LLM was triggered with confidence {llm_confidence}")
    else:
        print(f"   ❌ Request failed: {response.status_code}")

def test_weighted_mode():
    """Test weighted mode - LLM triggers based on weighted score"""
    print("\n🔍 Testing WEIGHTED MODE...")
    
    # Set to weighted mode with 0.7 threshold
    response = requests.post(f"{BASE_URL}/settings/llm-mode", json={
        "mode": "weighted",
        "weighted_threshold": 0.7,
        "reason": "Testing weighted mode"
    })
    print(f"✅ Set to weighted mode (0.7 threshold): {response.status_code}")
    
    # Test weighted mode
    response = requests.post(f"{BASE_URL}/ingest", json={
        "record_id": "test_weighted",
        "content": "This is a test document for weighted mode evaluation.",
        "tags": ["Test", "Weighted", "Evaluation"],
        "source_connector": "Custom",
        "content_metadata": {"title": "Weighted Test"}
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Quality Score: {result.get('quality_score')}")
        print(f"   LLM Confidence: {result.get('llm_confidence')}")
        print(f"   Rules Engine Confidence: {result.get('rules_engine_confidence')}")
    else:
        print(f"   ❌ Request failed: {response.status_code}")

def test_range_mode():
    """Test range mode - LLM triggers only in gray zone"""
    print("\n🔍 Testing RANGE MODE...")
    
    # Set to range mode with 60-80% gray zone
    response = requests.post(f"{BASE_URL}/settings/llm-mode", json={
        "mode": "range",
        "range_min_threshold": 60.0,
        "range_max_threshold": 80.0,
        "reason": "Testing range mode"
    })
    print(f"✅ Set to range mode (60-80% gray zone): {response.status_code}")
    
    # Test range mode
    response = requests.post(f"{BASE_URL}/ingest", json={
        "record_id": "test_range",
        "content": "This is a test document for range mode evaluation.",
        "tags": ["Test", "Range", "Evaluation"],
        "source_connector": "Custom",
        "content_metadata": {"title": "Range Test"}
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Quality Score: {result.get('quality_score')}")
        print(f"   LLM Confidence: {result.get('llm_confidence')}")
        print(f"   Rules Engine Confidence: {result.get('rules_engine_confidence')}")
    else:
        print(f"   ❌ Request failed: {response.status_code}")

def test_threshold_synchronization():
    """Test that thresholds are synchronized between frontend and backend"""
    print("\n🔍 Testing THRESHOLD SYNCHRONIZATION...")
    
    # Get current settings
    response = requests.get(f"{BASE_URL}/settings/llm-mode")
    if response.status_code == 200:
        settings = response.json()['settings']
        print(f"   Current mode: {settings['mode']}")
        print(f"   Percentage threshold: {settings['percentage_threshold']}")
        print(f"   Weighted threshold: {settings['weighted_threshold']}")
        print(f"   Range min: {settings['range_min_threshold']}")
        print(f"   Range max: {settings['range_max_threshold']}")
    
    # Get dynamic thresholds
    response = requests.get(f"{BASE_URL}/thresholds")
    if response.status_code == 200:
        thresholds = response.json()['thresholds']
        print(f"   Dynamic thresholds count: {len(thresholds)}")
        
        # Check for LLM-related thresholds
        llm_thresholds = [t for t in thresholds if 'llm' in t['name'].lower()]
        print(f"   LLM-related thresholds: {[t['name'] for t in llm_thresholds]}")

def main():
    """Run all tests"""
    print("🚀 Starting LLM Invocation Mode Tests")
    print("=" * 50)
    
    try:
        test_binary_mode()
        test_percentage_mode()
        test_weighted_mode()
        test_range_mode()
        test_threshold_synchronization()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    main() 