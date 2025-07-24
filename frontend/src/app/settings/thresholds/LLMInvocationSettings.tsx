'use client'

import React, { useState, useEffect } from 'react'
import { 
  Settings, 
  Play, 
  History, 
  RotateCcw, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  ChevronDown,
  ChevronRight,
  Zap,
  Target,
  BarChart3
} from 'lucide-react'
import { apiClient } from '@/app/api'

interface LLMInvocationSettings {
  mode: 'binary' | 'percentage' | 'weighted' | 'range'
  percentage_threshold: number
  weighted_threshold: number
  range_min_threshold: number
  range_max_threshold: number
  rule_weights: Record<string, number>
  created_by: string
  updated_at?: string
}

interface RuleWeight {
  rule_name: string
  weight: number
  description: string
}

interface LLMDecision {
  should_invoke_llm: boolean
  confidence: number
  reason: string
  mode_used: string
  threshold_used: number
  rules_summary: {
    total_rules: number
    passed_rules: number
    failed_rules: number
    pass_rate: number
    rule_details: Array<{
      name: string
      status: string
      confidence: number
    }>
  }
}

interface LLMSettingsHistory {
  id: string
  changed_by: string
  old_mode: string
  new_mode: string
  old_threshold: number
  new_threshold: number
  timestamp: string
  reason?: string
}

export default function LLMInvocationSettings() {
  const [settings, setSettings] = useState<LLMInvocationSettings | null>(null)
  const [ruleWeights, setRuleWeights] = useState<RuleWeight[]>([])
  const [history, setHistory] = useState<LLMSettingsHistory[]>([])
  const [loading, setLoading] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [simulationInput, setSimulationInput] = useState(`{
  "record_id": "test-sample-123",
  "document_text": "This is a comprehensive document about artificial intelligence and machine learning applications in modern business environments. It covers various aspects of AI implementation, including natural language processing, computer vision, and predictive analytics.",
  "tags": ["artificial-intelligence", "machine-learning", "business-applications", "technology"],
  "source_connector": "SharePoint",
  "quality_checks": [
    {"check_name": "content_quality_check", "status": "pass", "confidence_score": 0.92},
    {"check_name": "tag_validation", "status": "pass", "confidence_score": 0.88},
    {"check_name": "pii_detection", "status": "pass", "confidence_score": 0.95},
    {"check_name": "format_validation", "status": "fail", "confidence_score": 0.65}
  ]
}`)
  const [simulationResult, setSimulationResult] = useState<LLMDecision | null>(null)
  const [simulationLoading, setSimulationLoading] = useState(false)
  const [status, setStatus] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)

  useEffect(() => {
    loadSettings()
    loadHistory()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getLLMSettings()
      if (response.success) {
        setSettings(response.settings)
        setRuleWeights(response.rule_weights)
      } else {
        setStatus({ type: 'error', message: 'Failed to load LLM settings' })
      }
    } catch (error) {
      setStatus({ type: 'error', message: 'Error loading LLM settings' })
    } finally {
      setLoading(false)
    }
  }

  const loadHistory = async () => {
    try {
      const response = await apiClient.getLLMSettingsHistory()
      if (response.success) {
        setHistory(response.history)
      }
    } catch (error) {
      console.error('Failed to load history:', error)
    }
  }

  const updateMode = async (mode: string, reason: string = '') => {
    try {
      setLoading(true)
      const response = await apiClient.updateLLMMode(mode, 'admin', reason)

      if (response.success) {
        const data = response
        setSettings(data.settings)
        setStatus({ type: 'success', message: data.message })
        await loadHistory()
      } else {
        setStatus({ type: 'error', message: 'Failed to update mode' })
      }
    } catch (error) {
      setStatus({ type: 'error', message: 'Error updating mode' })
    } finally {
      setLoading(false)
    }
  }

  const updateThresholds = async (updates: any, reason: string = '') => {
    try {
      setLoading(true)
      const response = await apiClient.updateLLMThresholds(updates, 'admin', reason)

      if (response.success) {
        const data = response
        setSettings(data.settings)
        setStatus({ type: 'success', message: data.message })
        await loadHistory()
      } else {
        setStatus({ type: 'error', message: 'Failed to update thresholds' })
      }
    } catch (error) {
      setStatus({ type: 'error', message: 'Error updating thresholds' })
    } finally {
      setLoading(false)
    }
  }

  const simulateDecision = async () => {
    if (!simulationInput.trim() || !settings) return

    try {
      setSimulationLoading(true)
      setSimulationResult(null)
      
      const sampleInput = JSON.parse(simulationInput)
      const threshold = settings.mode === 'percentage' 
        ? settings.percentage_threshold 
        : settings.mode === 'range'
        ? settings.range_min_threshold  // For display purposes, we'll use min threshold
        : settings.weighted_threshold

      // Try backend simulation first
      try {
        const response = await apiClient.simulateLLMDecision(settings.mode, threshold, sampleInput, settings.rule_weights)

        if (response.success) {
          const data = response.data
          setSimulationResult(data.decision)
          return
        }
      } catch (backendError) {
        console.log('Backend simulation not available, using local simulation')
      }

      // Fallback to local simulation logic
      const qualityChecks = sampleInput.quality_checks || []
      const totalRules = qualityChecks.length
      const passedRules = qualityChecks.filter((check: any) => 
        check.status === 'pass' || check.status === 'passed'
      ).length
      const passRate = totalRules > 0 ? (passedRules / totalRules) * 100 : 0

      let shouldInvokeLLM = false
      let reason = ''
      let confidence = 0.85

      switch (settings.mode) {
        case 'binary':
          shouldInvokeLLM = passedRules === totalRules
          reason = shouldInvokeLLM 
            ? 'All rules passed - LLM triggered for binary mode'
            : `Only ${passedRules}/${totalRules} rules passed - LLM not triggered in binary mode`
          break

        case 'percentage':
          shouldInvokeLLM = passRate >= threshold
          reason = shouldInvokeLLM
            ? `${passRate.toFixed(1)}% pass rate exceeds ${threshold}% threshold - LLM triggered`
            : `${passRate.toFixed(1)}% pass rate below ${threshold}% threshold - LLM not triggered`
          break

        case 'weighted':
          // Simple weighted calculation for demo
          const weightedScore = qualityChecks.reduce((sum: number, check: any) => {
            const weight = ruleWeights.find(rw => rw.rule_name === check.check_name)?.weight || 1.0
            const passed = check.status === 'pass' ? 1 : 0
            return sum + (passed * weight)
          }, 0) / qualityChecks.length

          shouldInvokeLLM = weightedScore >= threshold
          reason = shouldInvokeLLM
            ? `Weighted score ${weightedScore.toFixed(2)} exceeds ${threshold} threshold - LLM triggered`
            : `Weighted score ${weightedScore.toFixed(2)} below ${threshold} threshold - LLM not triggered`
          break

        case 'range':
          const minThreshold = settings.range_min_threshold
          const maxThreshold = settings.range_max_threshold
          
          if (passRate < minThreshold) {
            shouldInvokeLLM = false
            reason = `${passRate.toFixed(1)}% pass rate below ${minThreshold}% min threshold - Auto-rejected (no LLM cost)`
          } else if (passRate > maxThreshold) {
            shouldInvokeLLM = false
            reason = `${passRate.toFixed(1)}% pass rate above ${maxThreshold}% max threshold - Auto-approved (no LLM cost)`
          } else {
            shouldInvokeLLM = true
            reason = `${passRate.toFixed(1)}% pass rate in gray zone (${minThreshold}%-${maxThreshold}%) - LLM triggered for analysis`
          }
          break
      }

      const mockResult: LLMDecision = {
        should_invoke_llm: shouldInvokeLLM,
        confidence: confidence,
        reason: reason,
        mode_used: settings.mode,
        threshold_used: threshold,
        rules_summary: {
          total_rules: totalRules,
          passed_rules: passedRules,
          failed_rules: totalRules - passedRules,
          pass_rate: passRate,
          rule_details: qualityChecks.map((check: any) => ({
            name: check.check_name,
            status: check.status,
            confidence: check.confidence_score || 0.8
          }))
        }
      }

      setSimulationResult(mockResult)

    } catch (error) {
      setStatus({ type: 'error', message: 'Invalid JSON or simulation error' })
    } finally {
      setSimulationLoading(false)
    }
  }

  const resetSettings = async () => {
    if (!confirm('Reset all LLM invocation settings to defaults?')) return

    try {
      setLoading(true)
      const response = await apiClient.resetLLMSettings()

      if (response.success) {
        const data = response
        setSettings(data.settings)
        setStatus({ type: 'success', message: data.message })
        await loadHistory()
      } else {
        setStatus({ type: 'error', message: 'Failed to reset settings' })
      }
    } catch (error) {
      setStatus({ type: 'error', message: 'Error resetting settings' })
    } finally {
      setLoading(false)
    }
  }

  const getModeIcon = (mode: string) => {
    switch (mode) {
      case 'binary': return <Target className="h-4 w-4" />
      case 'percentage': return <BarChart3 className="h-4 w-4" />
      case 'weighted': return <Zap className="h-4 w-4" />
      default: return <Settings className="h-4 w-4" />
    }
  }

  const getModeDescription = (mode: string) => {
    switch (mode) {
      case 'binary': return 'LLM runs only if ALL rules pass (strictest)'
      case 'percentage': return 'LLM runs if X% of rules pass (balanced)'
      case 'weighted': return 'LLM runs based on weighted rule scores (most flexible)'
      case 'range': return 'LLM runs if pass rate falls in gray zone (cost optimized)'
      default: return 'Unknown mode'
    }
  }

  if (loading && !settings) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-medium text-gray-900">LLM Invocation Settings</h2>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center space-x-2"
          >
            <History className="h-4 w-4" />
            <span>View History</span>
          </button>
          <button
            onClick={resetSettings}
            disabled={loading}
            className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50 flex items-center space-x-2"
          >
            <RotateCcw className="h-4 w-4" />
            <span>Reset to Defaults</span>
          </button>
        </div>
      </div>

      {/* Status Message */}
      {status && (
        <div className={`p-4 rounded-md flex items-center space-x-2 ${
          status.type === 'success' 
            ? 'bg-green-50 text-green-800 border border-green-200'
            : status.type === 'error'
            ? 'bg-red-50 text-red-800 border border-red-200'
            : 'bg-blue-50 text-blue-800 border border-blue-200'
        }`}>
          {status.type === 'success' && <CheckCircle className="h-5 w-5" />}
          {status.type === 'error' && <XCircle className="h-5 w-5" />}
          {status.type === 'info' && <Info className="h-5 w-5" />}
          <span>{status.message}</span>
        </div>
      )}

      {settings && (
        <>
          {/* Mode Selector */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-md font-medium text-gray-900 mb-4">1. LLM Trigger Mode</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {['binary', 'percentage', 'weighted', 'range'].map((mode) => (
                <div
                  key={mode}
                  className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                    settings.mode === mode
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => updateMode(mode)}
                >
                  <div className="flex items-center space-x-3 mb-2">
                    {getModeIcon(mode)}
                    <span className="font-medium capitalize">{mode}</span>
                    {settings.mode === mode && (
                      <CheckCircle className="h-5 w-5 text-blue-600" />
                    )}
                  </div>
                  <p className="text-sm text-gray-600">{getModeDescription(mode)}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Threshold Sliders */}
          {settings.mode !== 'binary' && (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h3 className="text-md font-medium text-gray-900 mb-4">
                2. Threshold Settings
              </h3>

              {settings.mode === 'percentage' && (
                <div className="space-y-4">
                  <label className="block text-sm font-medium text-gray-700">
                    Minimum percentage of rules that must pass
                  </label>
                  <div className="flex items-center space-x-4">
                    <input
                      type="range"
                      min="50"
                      max="100"
                      step="5"
                      value={settings.percentage_threshold}
                      onChange={(e) => updateThresholds({
                        percentage_threshold: parseFloat(e.target.value)
                      })}
                      className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <span className="font-medium text-gray-900 min-w-12">
                      {settings.percentage_threshold}%
                    </span>
                  </div>
                  <p className="text-sm text-gray-600">
                    LLM will trigger if {settings.percentage_threshold}% or more rules pass
                  </p>
                </div>
              )}

              {settings.mode === 'weighted' && (
                <div className="space-y-6">
                  <div className="space-y-4">
                    <label className="block text-sm font-medium text-gray-700">
                      Global weighted threshold (0-1 scale)
                    </label>
                    <div className="flex items-center space-x-4">
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={settings.weighted_threshold}
                        onChange={(e) => updateThresholds({
                          weighted_threshold: parseFloat(e.target.value)
                        })}
                        className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                      />
                      <span className="font-medium text-gray-900 min-w-12">
                        {settings.weighted_threshold.toFixed(2)}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h4 className="font-medium text-gray-900">Rule Weights</h4>
                    <div className="space-y-3 max-h-80 overflow-y-auto">
                      {ruleWeights.map((rule) => (
                        <div key={rule.rule_name} className="flex items-center space-x-4 p-3 bg-gray-50 rounded-md">
                          <div className="flex-1">
                            <div className="font-medium text-sm">{rule.rule_name}</div>
                            <div className="text-xs text-gray-600">{rule.description}</div>
                          </div>
                          <input
                            type="range"
                            min="0"
                            max="3"
                            step="0.1"
                            value={rule.weight}
                            onChange={(e) => updateThresholds({
                              rule_weights: {
                                ...settings.rule_weights,
                                [rule.rule_name]: parseFloat(e.target.value)
                              }
                            })}
                            className="w-24 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                          />
                          <span className="font-medium text-gray-900 min-w-12 text-center">
                            {rule.weight.toFixed(1)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {settings.mode === 'range' && (
                <div className="space-y-6">
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                    <h4 className="font-medium text-yellow-800 mb-2">Range Mode (Gray Zone)</h4>
                    <p className="text-sm text-yellow-700">
                      Records with pass rates below min threshold are auto-rejected, above max threshold are auto-approved. 
                      Only records in the "gray zone" between thresholds trigger LLM analysis for cost optimization.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <label className="block text-sm font-medium text-gray-700">
                        Min Threshold (Auto-reject below this)
                      </label>
                      <div className="flex items-center space-x-4">
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="5"
                          value={settings.range_min_threshold}
                          onChange={(e) => updateThresholds({
                            range_min_threshold: parseFloat(e.target.value)
                          })}
                          className="flex-1 h-2 bg-red-200 rounded-lg appearance-none cursor-pointer"
                        />
                        <span className="font-medium text-gray-900 min-w-12">
                          {settings.range_min_threshold}%
                        </span>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <label className="block text-sm font-medium text-gray-700">
                        Max Threshold (Auto-approve above this)
                      </label>
                      <div className="flex items-center space-x-4">
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="5"
                          value={settings.range_max_threshold}
                          onChange={(e) => updateThresholds({
                            range_max_threshold: parseFloat(e.target.value)
                          })}
                          className="flex-1 h-2 bg-green-200 rounded-lg appearance-none cursor-pointer"
                        />
                        <span className="font-medium text-gray-900 min-w-12">
                          {settings.range_max_threshold}%
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h5 className="font-medium text-blue-800 mb-2">Current Configuration:</h5>
                    <div className="text-sm text-blue-700 space-y-1">
                      <p>• Pass rate &lt; {settings.range_min_threshold}% → <span className="font-bold text-red-600">Auto-reject</span> (no LLM cost)</p>
                      <p>• Pass rate {settings.range_min_threshold}% - {settings.range_max_threshold}% → <span className="font-bold text-purple-600">LLM analysis</span> (gray zone)</p>
                      <p>• Pass rate &gt; {settings.range_max_threshold}% → <span className="font-bold text-green-600">Auto-approve</span> (no LLM cost)</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Test Simulation */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-md font-medium text-gray-900 mb-4">3. Test Simulation</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Sample Chunk JSON
                </label>
                <textarea
                  value={simulationInput}
                  onChange={(e) => setSimulationInput(e.target.value)}
                  placeholder={`{
  "record_id": "test-123",
  "document_text": "This is a sample document about machine learning and AI...",
  "tags": ["machine-learning", "artificial-intelligence", "technology"],
  "source_connector": "Custom"
}`}
                  className="w-full h-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                />
              </div>

              <button
                onClick={simulateDecision}
                disabled={simulationLoading || !simulationInput.trim()}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center space-x-2"
              >
                <Play className="h-4 w-4" />
                <span>{simulationLoading ? 'Simulating...' : 'Simulate Decision'}</span>
              </button>

              {simulationResult && (
                <div className={`p-4 rounded-md border-2 ${
                  simulationResult.should_invoke_llm
                    ? 'border-green-200 bg-green-50'
                    : 'border-red-200 bg-red-50'
                }`}>
                  <div className="flex items-center space-x-2 mb-2">
                    {simulationResult.should_invoke_llm ? (
                      <CheckCircle className="h-6 w-6 text-green-600" />
                    ) : (
                      <XCircle className="h-6 w-6 text-red-600" />
                    )}
                    <span className="font-medium text-lg">
                      LLM Will {simulationResult.should_invoke_llm ? 'Trigger ✅' : 'Not Trigger ❌'}
                    </span>
                  </div>
                  
                  <div className="space-y-2 text-sm">
                    <p><strong>Reason:</strong> {simulationResult.reason}</p>
                    <p><strong>Confidence:</strong> {simulationResult.confidence.toFixed(2)}</p>
                    <p><strong>Pass Rate:</strong> {simulationResult.rules_summary.pass_rate.toFixed(1)}% 
                       ({simulationResult.rules_summary.passed_rules}/{simulationResult.rules_summary.total_rules} rules passed)</p>
                  </div>

                  <details className="mt-3">
                    <summary className="cursor-pointer font-medium text-gray-700">View Rule Details</summary>
                    <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                      {simulationResult.rules_summary.rule_details.map((rule, idx) => (
                        <div key={idx} className="flex justify-between items-center p-2 bg-white rounded text-xs">
                          <span>{rule.name}</span>
                          <span className={`px-2 py-1 rounded ${
                            rule.status === 'pass' 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {rule.status} ({rule.confidence.toFixed(2)})
                          </span>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              )}
            </div>
          </div>

          {/* History Section */}
          {showHistory && (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-md font-medium text-gray-900">4. Settings History</h3>
                <button
                  onClick={() => setShowHistory(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <ChevronDown className="h-5 w-5" />
                </button>
              </div>

              {history.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Changed By
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Mode Change
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Threshold
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Timestamp
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Reason
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {history.map((entry) => (
                        <tr key={entry.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {entry.changed_by}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <span className="text-red-600">{entry.old_mode}</span>
                            <span className="mx-2">→</span>
                            <span className="text-green-600">{entry.new_mode}</span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <span className="text-red-600">{entry.old_threshold}</span>
                            <span className="mx-2">→</span>
                            <span className="text-green-600">{entry.new_threshold}</span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {new Date(entry.timestamp).toLocaleString()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {entry.reason || 'No reason provided'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">No history available</p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
} 