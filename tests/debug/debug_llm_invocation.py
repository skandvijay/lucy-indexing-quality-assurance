#!/usr/bin/env python3
"""
Debug script to test LLM invocation logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from run_local import evaluate_llm_invocation_decision, LLMInvocationSettings, LLMInvocationMode, QualityCheckResult, FlagStatus

def test_binary_mode_logic():
    """Test binary mode logic directly"""
    print("🔍 Testing Binary Mode Logic Directly")
    print("=" * 50)
    
    # Create test quality results with some failures
    quality_results = [
        QualityCheckResult(
            check_name="empty_tags",
            status=FlagStatus.PASS,
            confidence_score=0.9,
            failure_reason=None
        ),
        QualityCheckResult(
            check_name="tag_count_validation", 
            status=FlagStatus.PASS,
            confidence_score=0.8,
            failure_reason=None
        ),
        QualityCheckResult(
            check_name="text_quality",
            status=FlagStatus.PASS,
            confidence_score=0.7,
            failure_reason=None
        ),
        QualityCheckResult(
            check_name="stopwords_detection",
            status=FlagStatus.FAIL,  # This should fail
            confidence_score=0.3,
            failure_reason="Generic tags detected"
        ),
        QualityCheckResult(
            check_name="spam_patterns",
            status=FlagStatus.FAIL,  # This should fail
            confidence_score=0.2,
            failure_reason="Spam patterns detected"
        ),
        QualityCheckResult(
            check_name="semantic_relevance",
            status=FlagStatus.PASS,
            confidence_score=0.6,
            failure_reason=None
        )
    ]
    
    # Create binary mode settings
    settings = LLMInvocationSettings(
        mode=LLMInvocationMode.BINARY,
        percentage_threshold=85.0,
        weighted_threshold=0.8,
        range_min_threshold=70.0,
        range_max_threshold=80.0,
        rule_weights={},
        created_by="debug",
        updated_at=None
    )
    
    print(f"Settings mode: {settings.mode}")
    print(f"Total rules: {len(quality_results)}")
    
    # Count passed and failed rules
    passed_rules = sum(1 for result in quality_results if result.status == FlagStatus.PASS)
    failed_rules = sum(1 for result in quality_results if result.status == FlagStatus.FAIL)
    
    print(f"Passed rules: {passed_rules}")
    print(f"Failed rules: {failed_rules}")
    
    # Test the logic manually
    should_invoke_manual = passed_rules == len(quality_results)
    print(f"Manual calculation - should_invoke: {should_invoke_manual}")
    
    # Test the function
    decision = evaluate_llm_invocation_decision(quality_results, settings)
    
    print(f"\nFunction result:")
    print(f"  should_invoke_llm: {decision.should_invoke_llm}")
    print(f"  confidence: {decision.confidence}")
    print(f"  reason: {decision.reason}")
    print(f"  mode_used: {decision.mode_used}")
    print(f"  threshold_used: {decision.threshold_used}")
    
    # Check if the result is correct
    if decision.should_invoke_llm == should_invoke_manual:
        print("✅ Result is CORRECT!")
    else:
        print("❌ Result is WRONG!")
        print(f"Expected: {should_invoke_manual}, Got: {decision.should_invoke_llm}")
    
    return decision

def test_binary_mode_all_pass():
    """Test binary mode with all rules passing"""
    print("\n🔍 Testing Binary Mode - All Rules Pass")
    print("=" * 50)
    
    # Create test quality results with all passing
    quality_results = [
        QualityCheckResult(
            check_name="empty_tags",
            status=FlagStatus.PASS,
            confidence_score=0.9,
            failure_reason=None
        ),
        QualityCheckResult(
            check_name="tag_count_validation", 
            status=FlagStatus.PASS,
            confidence_score=0.8,
            failure_reason=None
        ),
        QualityCheckResult(
            check_name="text_quality",
            status=FlagStatus.PASS,
            confidence_score=0.7,
            failure_reason=None
        )
    ]
    
    # Create binary mode settings
    settings = LLMInvocationSettings(
        mode=LLMInvocationMode.BINARY,
        percentage_threshold=85.0,
        weighted_threshold=0.8,
        range_min_threshold=70.0,
        range_max_threshold=80.0,
        rule_weights={},
        created_by="debug",
        updated_at=None
    )
    
    print(f"Settings mode: {settings.mode}")
    print(f"Total rules: {len(quality_results)}")
    
    # Count passed and failed rules
    passed_rules = sum(1 for result in quality_results if result.status == FlagStatus.PASS)
    failed_rules = sum(1 for result in quality_results if result.status == FlagStatus.FAIL)
    
    print(f"Passed rules: {passed_rules}")
    print(f"Failed rules: {failed_rules}")
    
    # Test the logic manually
    should_invoke_manual = passed_rules == len(quality_results)
    print(f"Manual calculation - should_invoke: {should_invoke_manual}")
    
    # Test the function
    decision = evaluate_llm_invocation_decision(quality_results, settings)
    
    print(f"\nFunction result:")
    print(f"  should_invoke_llm: {decision.should_invoke_llm}")
    print(f"  confidence: {decision.confidence}")
    print(f"  reason: {decision.reason}")
    print(f"  mode_used: {decision.mode_used}")
    print(f"  threshold_used: {decision.threshold_used}")
    
    # Check if the result is correct
    if decision.should_invoke_llm == should_invoke_manual:
        print("✅ Result is CORRECT!")
    else:
        print("❌ Result is WRONG!")
        print(f"Expected: {should_invoke_manual}, Got: {decision.should_invoke_llm}")
    
    return decision

if __name__ == "__main__":
    print("🚀 Starting LLM Invocation Debug Tests")
    print("=" * 60)
    
    # Test 1: Some rules fail (should NOT invoke LLM)
    decision1 = test_binary_mode_logic()
    
    # Test 2: All rules pass (should invoke LLM)
    decision2 = test_binary_mode_all_pass()
    
    print("\n" + "=" * 60)
    print("✅ Debug tests completed!") 