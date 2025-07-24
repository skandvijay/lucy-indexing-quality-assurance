'use client'

import React, { useState, useRef, useEffect } from 'react'
import { 
  X, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Clock, 
  User, 
  Calendar,
  FileText,
  Tag,
  Edit,
  Save,
  RotateCcw,
  ExternalLink,
  Copy,
  Download,
  Brain,
  Settings,
  MessageSquare,
  Zap,
  Shield,
  Lightbulb,
  BarChart3,
  GitBranch,
  Activity,
  Cpu,
  MemoryStick,
  Database,
  History,
  Server,
  Layers,
  ChevronRight,
  Info,
  Target,
  TrendingUp,
  Loader2,
  RefreshCw
} from 'lucide-react'
import { QualityRecord, QualityCheck } from '@/types'
import { apiClient } from '@/app/api'

// Utility functions
const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

// Clean Status Badge Component
const StatusBadge: React.FC<{ status: string; size?: 'sm' | 'md' }> = ({ status, size = 'md' }) => {
  const baseClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
  const statusConfig = {
    approved: 'bg-green-50 text-green-700 border-green-200',
    rejected: 'bg-red-50 text-red-700 border-red-200',
    flagged: 'bg-amber-50 text-amber-700 border-amber-200',
    under_review: 'bg-blue-50 text-blue-700 border-blue-200',
    PASS: 'bg-green-50 text-green-700 border-green-200',
    FAIL: 'bg-red-50 text-red-700 border-red-200',
    pass: 'bg-green-50 text-green-700 border-green-200',
    fail: 'bg-red-50 text-red-700 border-red-200',
    TRIGGERED: 'bg-purple-50 text-purple-700 border-purple-200',
    'NOT TRIGGERED': 'bg-gray-50 text-gray-700 border-gray-200',
    'not_triggered': 'bg-orange-50 text-orange-700 border-orange-200'
  }
  
  return (
    <span className={`inline-flex items-center rounded-full border font-medium ${baseClasses} ${statusConfig[status as keyof typeof statusConfig] || 'bg-gray-50 text-gray-700 border-gray-200'}`}>
      {status.replace('_', ' ').toUpperCase()}
    </span>
  )
}

// Metric Card Component
const MetricCard: React.FC<{ label: string; value: React.ReactNode; icon?: React.ReactNode; color?: string }> = ({ 
  label, 
  value, 
  icon, 
  color = 'gray' 
}) => (
  <div className="bg-white border border-gray-100 rounded-lg p-3 shadow-sm">
    <div className="flex items-center justify-between">
      <div className="flex-1">
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
        <div className={`text-xl font-bold text-${color}-900 mt-1`}>{value}</div>
      </div>
      {icon && <div className={`text-${color}-500 ml-2`}>{icon}</div>}
    </div>
  </div>
)

// Compact Rules Engine Component
const RulesEngineAnalysis: React.FC<{ record: QualityRecord }> = ({ record }) => {
  const qualityChecks = record.quality_checks || []
  const rulesChecks = qualityChecks.filter((check: QualityCheck) => 
    check.check_name !== 'llm_semantic_validation' && 
    check.check_name !== 'llm_invocation_decision'
  )
  const passedRules = rulesChecks.filter((check: QualityCheck) => 
    check.status?.toUpperCase() === 'PASS' || check.status?.toUpperCase() === 'PASSED'
  ).length
  const totalRules = rulesChecks.length
  const passRate = totalRules > 0 ? (passedRules / totalRules) * 100 : 0
  
  // Use backend rules engine confidence for consistency
  const overallConfidence = record.rules_engine_confidence || 0

  return (
    <div className="bg-white border border-gray-100 rounded-xl p-6">
      <div className="flex items-center space-x-3 mb-4">
        <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
          <Shield className="h-4 w-4 text-green-600" />
        </div>
        <div>
          <h4 className="font-semibold text-gray-900">Rules Engine Analysis</h4>
          <p className="text-sm text-gray-500">Automated quality validation checks</p>
        </div>
      </div>

      {/* Compact Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <div className="text-center">
          <div className="text-xl font-bold text-blue-600">{passedRules}/{totalRules}</div>
          <div className="text-xs text-gray-600">Rules Passed</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-green-600">{passRate.toFixed(0)}%</div>
          <div className="text-xs text-gray-600">Pass Rate</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-purple-600">{(overallConfidence * 100).toFixed(0)}%</div>
          <div className="text-xs text-gray-600">Avg Confidence</div>
        </div>
        <div className="text-center">
          <div className={`text-xl font-bold ${passedRules === totalRules ? 'text-green-600' : 'text-red-600'}`}>
            {passedRules === totalRules ? '✓' : '✗'}
          </div>
          <div className="text-xs text-gray-600">Status</div>
        </div>
      </div>

      {/* Compact Rules List */}
      {rulesChecks.length > 0 ? (
        <div className="space-y-2">
          {rulesChecks.map((check, index) => {
            const isPassed = check.status?.toUpperCase() === 'PASS' || check.status?.toUpperCase() === 'PASSED'
            return (
              <div key={index} className={`flex items-center justify-between p-2 rounded-lg ${isPassed ? 'bg-green-50' : 'bg-red-50'}`}>
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${isPassed ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className="text-sm font-medium text-gray-900">
                    {check.check_name?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Unknown Check'}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="flex items-center space-x-1">
                    <div className="w-8 bg-gray-200 rounded-full h-1.5">
                      <div 
                        className={`h-1.5 rounded-full ${
                          (check.confidence_score || 0) >= 0.8 ? 'bg-green-500' :
                          (check.confidence_score || 0) >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${((check.confidence_score || 0) * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-gray-700">{((check.confidence_score || 0) * 100).toFixed(0)}%</span>
                  </div>
                  <StatusBadge status={check.status || 'unknown'} size="sm" />
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="text-center py-4 text-gray-500">
          <Shield className="h-6 w-6 mx-auto mb-2 text-gray-300" />
          <p className="text-sm">No rules engine data available</p>
        </div>
      )}
    </div>
  )
}

// LLM Analysis Card Component with Real-time Settings Sync
// - Displays current system LLM configuration (not historical record settings)
// - Auto-refreshes every 5 seconds when modal is open
// - Updates immediately when modal opens or record changes
// - Manual refresh button available for immediate updates
// - Settings changes apply to new records only, not historical data
const LLMAnalysisCard: React.FC<{ record: QualityRecord; isModalOpen: boolean }> = ({ record, isModalOpen }) => {
  const [llmSettings, setLlmSettings] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())

    const loadLLMSettings = async () => {
      try {
        const settings = await apiClient.getLLMSettings()
      setLlmSettings(settings.settings || settings) // Handle both response formats
      setLastRefresh(new Date())
      } catch (error) {
        console.error('Failed to load LLM settings:', error)
      } finally {
        setLoading(false)
      }
    }

  // Load settings when modal opens, record changes, or on mount
  useEffect(() => {
    if (isModalOpen && record) {
    loadLLMSettings()
    }
  }, [isModalOpen, record?.id])

  // Real-time sync: refresh settings every 5 seconds when modal is open
  useEffect(() => {
    if (!isModalOpen) return

    const interval = setInterval(() => {
      loadLLMSettings()
    }, 5000) // Refresh every 5 seconds

    return () => clearInterval(interval)
  }, [isModalOpen])

  // Load LLM suggestions only when LLM was actually triggered
  useEffect(() => {
    if (!isModalOpen || loading || !record) return
    
    const loadLLMSuggestions = async () => {
      const llmCheck = (record.quality_checks || []).find((check: QualityCheck) => 
        check.check_name === 'llm_semantic_validation'
      )
      
      // Only proceed if LLM was actually triggered (not skipped)
      // Note: 'FAIL' status means LLM ran but found issues - we still want to show suggestions!
      if (llmCheck && llmCheck.status !== 'SKIPPED' && llmCheck.status !== undefined) {
        setLoadingSuggestions(true)
        console.log('🔍 LLM Check found:', llmCheck)
        console.log('📋 LLM Check metadata:', llmCheck.check_metadata)
        console.log('📝 Record llmSuggestions:', record.llmSuggestions)
        console.log('🎯 Record type:', typeof record)
        console.log('📊 Full record object:', record)
        
        try {
          // First, try to get LLM suggestions from the quality check metadata
          let llmSuggestions: string[] = []
          
          console.log('🔎 Searching for LLM suggestions...')
          console.log('🔎 record.llmSuggestions exists?', !!record.llmSuggestions)
          console.log('🔎 record.llmSuggestions value:', record.llmSuggestions)
          console.log('🔎 record.llmSuggestions length:', record.llmSuggestions?.length)
          
          // Check if record has top-level llmSuggestions
          if (record.llmSuggestions && record.llmSuggestions.length > 0) {
            console.log('✅ Using record.llmSuggestions:', record.llmSuggestions)
            llmSuggestions = record.llmSuggestions
          } else {
            console.log('❌ No top-level llmSuggestions, checking metadata...')
            
            // Try to extract from quality check metadata  
            if (llmCheck.check_metadata) {
              console.log('🔍 Parsing LLM check metadata...')
              try {
                const metadata = typeof llmCheck.check_metadata === 'string' 
                  ? JSON.parse(llmCheck.check_metadata) 
                  : llmCheck.check_metadata
                
                console.log('📋 Parsed metadata:', metadata)
                console.log('📋 metadata.llm_suggestions:', metadata.llm_suggestions)
                
                if (metadata && metadata.llm_suggestions && metadata.llm_suggestions.length > 0) {
                  console.log('✅ Found LLM suggestions in metadata:', metadata.llm_suggestions)
                  llmSuggestions = metadata.llm_suggestions
                } else {
                  console.log('❌ No llm_suggestions found in metadata')
                }
              } catch (parseError) {
                console.error('❌ Error parsing metadata:', parseError)
              }
            } else {
              console.log('❌ No check_metadata available')
            }
            
            // Additional fallback: check if LLM suggestions are elsewhere in the record
            if (llmSuggestions.length === 0) {
              console.log('🔍 Checking alternative locations...')
              
              // Check if it's in the quality checks directly
              const llmCheckWithSuggestions = (record.quality_checks || []).find((check: any) => 
                check.check_name === 'llm_semantic_validation' && 
                check.check_metadata_json && 
                JSON.stringify(check.check_metadata_json).includes('llm_suggestions')
              )
              
              if (llmCheckWithSuggestions) {
                console.log('🔍 Found LLM check with suggestions:', llmCheckWithSuggestions)
                try {
                  const metadataJson = typeof llmCheckWithSuggestions.check_metadata_json === 'string'
                    ? JSON.parse(llmCheckWithSuggestions.check_metadata_json)
                    : llmCheckWithSuggestions.check_metadata_json
                  
                  if (metadataJson && metadataJson.llm_suggestions) {
                    console.log('✅ Extracted suggestions from quality_checks:', metadataJson.llm_suggestions)
                    llmSuggestions = metadataJson.llm_suggestions
                  }
                } catch (e) {
                  console.error('❌ Error parsing quality check metadata:', e)
                }
              }
            }
          }
          
          if (llmSuggestions.length > 0) {
            console.log(`✅ Found ${llmSuggestions.length} LLM suggestions:`, llmSuggestions)
            setSuggestions(llmSuggestions)
          } else {
            console.log('⚠️ No LLM suggestions found, generating fallback suggestions')
            // Generate fallback suggestions only if no LLM suggestions found
            // Generate context-aware improvement suggestions
            const improvementSuggestions: string[] = []
            
            // Analyze quality score and provide specific suggestions
            if (record.qualityScore < 60) {
              improvementSuggestions.push("Content requires significant improvement for better quality score")
              improvementSuggestions.push("Review and enhance content structure and clarity")
            } else if (record.qualityScore < 80) {
              improvementSuggestions.push("Consider refining content for better clarity and completeness")
              improvementSuggestions.push("Review grammar, spelling, and formatting")
            }
            
            // Add suggestions based on issues
            if (record.issues && record.issues.length > 0) {
              improvementSuggestions.push(`Address ${record.issues.length} identified quality issue${record.issues.length > 1 ? 's' : ''}`)
              
              // Add specific suggestions based on issue types
              const issueTypes = [...new Set(record.issues.map(issue => issue.type))]
              issueTypes.forEach(type => {
                switch (type) {
                  case 'generic_tags':
                    improvementSuggestions.push("Replace generic tags with more specific, descriptive ones")
                    break
                  case 'content_quality':
                    improvementSuggestions.push("Improve content quality and relevance")
                    break
                  case 'missing_context':
                    improvementSuggestions.push("Add more context and background information")
                    break
                  case 'pii_detected':
                    improvementSuggestions.push("Remove or redact personal identifiable information")
                    break
                  default:
                    if (type) {
                      improvementSuggestions.push(`Address ${type.replace(/_/g, ' ')} concerns`)
                    }
                }
              })
            }
            
            // Add tag-related suggestions
            if (record.tags.length === 0) {
              improvementSuggestions.push("Add relevant tags to improve content discoverability")
            } else if (record.tags.length < 3) {
              improvementSuggestions.push("Consider adding more specific tags for better categorization")
            }
            
            // Try to get additional tag suggestions
            try {
              const response = await apiClient.getTagSuggestions(record.content, record.tags)
              if (response.success && response.suggestions.length > 0) {
                const tagSuggestions = response.suggestions.slice(0, 3).map((tag: string) => 
                  `Consider adding the tag "${tag}" for better categorization`
                )
                improvementSuggestions.push(...tagSuggestions)
              }
            } catch (tagError) {
              // Ignore tag suggestion errors
            }
            
            // Ensure we have at least some suggestions
            if (improvementSuggestions.length === 0) {
              if (record.qualityScore >= 90) {
                improvementSuggestions.push("Content quality is excellent - consider it as a template for future content")
                improvementSuggestions.push("Review tags periodically to ensure they remain relevant")
              } else {
                improvementSuggestions.push("Review content for potential improvements")
                improvementSuggestions.push("Ensure proper formatting and structure")
                improvementSuggestions.push("Add relevant tags for better discoverability")
              }
            }
            
            setSuggestions(improvementSuggestions)
          }
        } catch (error) {
          console.error('Failed to load LLM suggestions:', error)
          // Only provide fallback suggestions if LLM was actually triggered but failed
          setSuggestions([
            "LLM analysis was triggered but failed to generate suggestions",
            "Review content manually for potential improvements"
          ])
        } finally {
          setLoadingSuggestions(false)
        }
      } else {
        // LLM was not triggered - clear any suggestions and don't load fallbacks
        console.log('❌ LLM was not triggered - clearing suggestions')
        setSuggestions([])
        setLoadingSuggestions(false)
      }
    }
    
    if (!loading) {
      loadLLMSuggestions()
    }
  }, [record, loading, isModalOpen])

  const qualityChecks = record.quality_checks || []
  const rulesChecks = qualityChecks.filter((check: QualityCheck) => 
    check.check_name !== 'llm_semantic_validation' && 
    check.check_name !== 'llm_invocation_decision'
  )
  const passedRules = rulesChecks.filter((check: QualityCheck) => 
    check.status?.toUpperCase() === 'PASS' || check.status?.toUpperCase() === 'PASSED'
  ).length
  const totalRules = rulesChecks.length
  const passRate = totalRules > 0 ? (passedRules / totalRules) * 100 : 0

  const llmCheck = qualityChecks.find((check: QualityCheck) => 
    check.check_name === 'llm_semantic_validation'
  )
  const llmDecision = qualityChecks.find((check: QualityCheck) => 
    check.check_name === 'llm_invocation_decision'
  )

  const llmTriggered = llmCheck && llmCheck.status !== 'SKIPPED'
  const mode = llmSettings?.mode || 'binary'
  const threshold = llmSettings?.percentage_threshold || 85
  const weightedThreshold = llmSettings?.weighted_threshold || 0.8
  const rangeMin = llmSettings?.range_min_threshold || 70
  const rangeMax = llmSettings?.range_max_threshold || 90

  // Get approval threshold dynamically from settings API
  const [approvalThreshold, setApprovalThreshold] = useState(50) // Default fallback
  
  useEffect(() => {
    // Fetch dynamic approval threshold from backend
    const fetchApprovalThreshold = async () => {
      try {
        const response = await fetch('/api/settings') // This endpoint should provide current thresholds
        if (response.ok) {
          const settings = await response.json()
          setApprovalThreshold(settings.approval_quality_score_threshold || 50)
        }
      } catch (error) {
        console.warn('Could not fetch approval threshold, using default:', error)
        setApprovalThreshold(50) // Use fallback
      }
    }
    
    fetchApprovalThreshold()
  }, [])
  const qualityScore = record.qualityScore || 0
  // 🔧 BUG FIX: Use actual record status instead of calculated approval status
  // This ensures LLM analysis status is synchronized with overall record status
  const isRecordApproved = record.status === 'approved'
  const isRecordFlagged = record.status === 'flagged'

  // Dynamic LLM Analysis Status - FIXED: now synchronized with actual record status
  const getLLMAnalysisStatus = () => {
    if (!llmTriggered) {
      return {
        label: 'Not Triggered',
        description: 'LLM analysis was not needed based on current threshold settings',
        color: 'gray'
      }
    }
    
    // LLM was triggered - determine semantic quality status based on ACTUAL record status
    const hasImprovements = suggestions.length > 0
    
    if (isRecordApproved && !hasImprovements) {
      return {
        label: 'Excellent',
        description: 'Content approved with excellent semantic alignment',
        color: 'green'
      }
    } else if (isRecordApproved && hasImprovements) {
      return {
        label: 'Good',
        description: 'Content approved with optimization opportunities identified',
        color: 'blue'
      }
    } else if (isRecordFlagged && hasImprovements) {
      return {
        label: 'Needs Review',
        description: 'Content flagged with semantic improvement suggestions',
        color: 'orange'
      }
    } else if (isRecordFlagged) {
      return {
        label: 'Needs Review',
        description: 'Content flagged for review by the system',
        color: 'orange'
      }
    } else {
      return {
        label: 'Analysis Complete',
        description: 'LLM semantic analysis completed',
        color: 'purple'
      }
    }
  }

  const llmAnalysisStatus = getLLMAnalysisStatus()

  let triggerCondition = ''
  let triggerMet = false

  switch (mode) {
    case 'binary':
      triggerCondition = `All ${totalRules} rules must pass`
      triggerMet = passedRules === totalRules
      break
    case 'percentage':
      triggerCondition = `≥${threshold}% of rules must pass`
      triggerMet = passRate >= threshold
      break
    case 'weighted':
      triggerCondition = `Weighted score ≥${weightedThreshold}`
      triggerMet = false // Complex calculation
      break
    case 'range':
      triggerCondition = `${rangeMin}% ≤ pass rate ≤ ${rangeMax}% (gray zone)`
      triggerMet = passRate >= rangeMin && passRate <= rangeMax
      break
  }

  if (loading) {
  return (
      <div className="bg-white border border-gray-100 rounded-xl p-6">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
            <Brain className="h-4 w-4 text-blue-600 animate-pulse" />
        </div>
          <div>
            <h3 className="font-semibold text-gray-900">LLM Semantic Analysis</h3>
            <p className="text-sm text-gray-500">Loading analysis settings...</p>
        </div>
      </div>
    </div>
  )
}

  return (
    <div className="bg-white border border-gray-100 rounded-xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
    <div className="flex items-center space-x-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            llmTriggered ? 'bg-purple-100' : 'bg-gray-100'
          }`}>
            <Brain className={`h-4 w-4 ${llmTriggered ? 'text-purple-600' : 'text-gray-400'}`} />
      </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-semibold text-gray-900">LLM Semantic Analysis</h3>
              <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${
                loading ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                  loading 
                    ? 'bg-yellow-500 animate-spin' 
                    : 'bg-green-500 animate-pulse'
                }`}></span>
                {loading ? 'Refreshing...' : 'Current Settings'}
              </span>
      </div>
            <div className="flex items-center space-x-2 mt-1">
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                mode === 'binary' ? 'bg-blue-100 text-blue-700' :
                mode === 'percentage' ? 'bg-green-100 text-green-700' :
                mode === 'weighted' ? 'bg-purple-100 text-purple-700' :
                mode === 'range' ? 'bg-yellow-100 text-yellow-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {mode.charAt(0).toUpperCase() + mode.slice(1)} Mode
              </span>
              <span className="text-xs text-gray-500">
                {mode === 'binary' ? 'Strictest quality control' :
                 mode === 'percentage' ? 'Balanced approach' :
                 mode === 'weighted' ? 'Rule priority based' :
                 mode === 'range' ? 'Cost optimized' :
                 'Quality analysis'}
              </span>
              <span className="text-xs text-gray-400">
                • Updated {lastRefresh.toLocaleTimeString()} (auto-refresh: 5s)
        </span>
      </div>
    </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={loadLLMSettings}
            disabled={loading}
            className="p-1.5 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100 transition-colors disabled:opacity-50"
            title="Refresh LLM settings"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <StatusBadge status={llmTriggered ? 'TRIGGERED' : 'NOT TRIGGERED'} size="sm" />
        </div>
      </div>

      {/* Trigger Logic */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-gray-700">Dynamic Trigger Configuration</span>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">{passedRules}/{totalRules} rules</span>
            <span className="text-sm font-medium text-gray-900">{passRate.toFixed(1)}%</span>
          </div>
        </div>
        
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm font-medium text-gray-700">{triggerCondition}</p>
              <p className="text-xs text-gray-500 mt-1">
                {mode === 'binary' ? 'Zero tolerance - all rules must pass' :
                 mode === 'percentage' ? `Requires ${threshold}% minimum pass rate` :
                 mode === 'weighted' ? `Custom weights applied, threshold: ${weightedThreshold}` :
                 mode === 'range' ? `Gray zone: ${rangeMin}%-${rangeMax}% triggers LLM` :
                 'Standard trigger logic'}
              </p>
            </div>
            <div className={`w-3 h-3 rounded-full ${triggerMet ? 'bg-green-500' : 'bg-red-500'}`} />
          </div>
          
          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-300 ${
                triggerMet ? 'bg-green-500' : 'bg-red-500'
              }`}
              style={{ width: `${Math.min(passRate, 100)}%` }}
            />
          </div>
          
          {mode === 'percentage' && (
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0%</span>
              <span className="text-gray-700 font-medium">{threshold}% threshold</span>
              <span>100%</span>
        </div>
      )}
          
          {mode === 'range' && (
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0%</span>
              <span className="text-blue-700 font-medium">{rangeMin}%</span>
              <span className="text-purple-700 font-medium">{rangeMax}%</span>
              <span>100%</span>
            </div>
          )}
          
          {mode === 'weighted' && (
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0.0</span>
              <span className="text-gray-700 font-medium">{weightedThreshold} threshold</span>
              <span>1.0</span>
      </div>
          )}
        </div>
      </div>

      {/* Important Note */}
      <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start space-x-2">
          <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-800">
            <p className="font-medium">Real-time System Settings</p>
            <p className="text-xs text-blue-700 mt-1">
              The mode and thresholds shown above reflect the <span className="font-medium">current system configuration</span> and 
              update in real-time. Changes to these settings apply to new records only and do not affect historical records.
            </p>
          </div>
        </div>
      </div>

      {/* LLM Results */}
      {llmTriggered ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <MetricCard 
              label="LLM Confidence" 
              value={llmCheck?.confidence_score ? `${(llmCheck.confidence_score * 100).toFixed(0)}%` : 'N/A'}
              icon={<TrendingUp className="h-5 w-5" />}
              color="purple"
            />
            <MetricCard 
              label="Analysis Status" 
              value={<span className={`px-2 py-1 rounded-full text-xs font-medium ${
                llmAnalysisStatus.color === 'green' ? 'bg-green-100 text-green-800' :
                llmAnalysisStatus.color === 'blue' ? 'bg-blue-100 text-blue-800' :
                llmAnalysisStatus.color === 'orange' ? 'bg-orange-100 text-orange-800' :
                llmAnalysisStatus.color === 'gray' ? 'bg-gray-100 text-gray-800' :
                'bg-purple-100 text-purple-800'
              }`}>{llmAnalysisStatus.label}</span>}
              icon={<Target className="h-5 w-5" />}
              color="blue"
            />
          </div>
          
          {/* LLM Improvement Suggestions - Dynamic based on ACTUAL record status */}
          <div className={`border rounded-lg p-4 ${
            isRecordApproved ? 'bg-blue-50 border-blue-200' : 'bg-orange-50 border-orange-200'
          }`}>
            <h4 className={`font-medium mb-3 flex items-center ${
              isRecordApproved ? 'text-blue-900' : 'text-orange-900'
            }`}>
              <Lightbulb className="h-4 w-4 mr-2" />
              AI Semantic Analysis
              {loadingSuggestions && <Loader2 className="h-4 w-4 ml-2 animate-spin" />}
              <span className="ml-2 text-xs px-2 py-1 rounded-full bg-white bg-opacity-50">
                Quality: {qualityScore}% | Status: {isRecordApproved ? 'APPROVED' : 'FLAGGED'}
              </span>
            </h4>
            
            {/* Context explanation */}
            <div className={`mb-3 p-2 rounded text-xs ${
              isRecordApproved ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'
            }`}>
              {isRecordApproved ? (
                <span>✅ This content is <strong>approved</strong> by the system. AI analysis provides additional optimization insights.</span>
              ) : (
                <span>⚠️ This content is <strong>flagged for review</strong> by the system. AI analysis suggests specific improvements.</span>
              )}
            </div>
            
            {(() => {
              console.log('🎯 Current suggestions state:', suggestions, 'Loading:', loadingSuggestions, 'LLM Triggered:', llmTriggered)
              
              if (loadingSuggestions) {
                return <div className="text-sm text-purple-700">Loading suggestions...</div>
              } else if (suggestions.length > 0) {
                console.log('🎯 Displaying suggestions:', suggestions)
                return (
                  <div>
                    <p className={`text-sm mb-3 italic ${
                      isRecordApproved ? 'text-blue-600' : 'text-orange-600'
                    }`}>
                      {isRecordApproved ? 
                        '🎯 AI identified optimization opportunities to enhance semantic quality:' :
                        '🔧 AI suggests these improvements to meet approval criteria:'
                      }
                    </p>
                  <ul className="space-y-2">
                    {suggestions.map((suggestion, index) => (
                        <li key={index} className={`text-sm flex items-start ${
                          isRecordApproved ? 'text-blue-800' : 'text-orange-800'
                        }`}>
                          <span className={`mr-2 mt-1 ${
                            isRecordApproved ? 'text-blue-600' : 'text-orange-600'
                          }`}>•</span>
                        <span>{suggestion}</span>
                      </li>
                    ))}
                  </ul>
                  </div>
                )
              } else {
                console.log('❌ No suggestions to display')
                return <p className={`text-sm ${
                  isRecordApproved ? 'text-blue-700' : 'text-orange-700'
                }`}>
                  {!llmTriggered ? (
                    <span>ℹ️ AI analysis was not triggered based on current LLM threshold settings.</span>
                  ) : isRecordApproved ? (
                    <span>✅ Excellent! No semantic improvements needed - content meets high quality standards.</span>
                  ) : (
                    <span>📋 AI analysis completed. While suggestions weren't generated, manual review is recommended.</span>
                  )}
                </p>
              }
            })()}
          </div>
        </div>
      ) : (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
          <AlertTriangle className="h-6 w-6 text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-600">LLM analysis not triggered</p>
          <p className="text-xs text-gray-500 mt-1">
            {llmDecision?.failure_reason || 'Trigger conditions not met'}
          </p>
        </div>
      )}
    </div>
  )
}

// Quality Summary Component
const QualitySummary: React.FC<{ record: QualityRecord }> = ({ record }) => {
  const qualityChecks = record.quality_checks || []
  const rulesChecks = qualityChecks.filter((check: QualityCheck) => 
    check.check_name !== 'llm_semantic_validation' && 
    check.check_name !== 'llm_invocation_decision'
  )
  const passedRules = rulesChecks.filter((check: QualityCheck) => 
    check.status?.toUpperCase() === 'PASS' || check.status?.toUpperCase() === 'PASSED'
  ).length
  const totalRules = rulesChecks.length
  const issues = record.issues?.length || 0

  // Format LLM confidence - show "Not Triggered" if 0, else show percentage
  const formatLLMConfidence = () => {
    if (!record.llm_confidence || record.llm_confidence === 0) {
      return "Not Triggered"
    }
    return `${(record.llm_confidence * 100).toFixed(0)}%`
  }

  // Format Rules Engine confidence - use backend value for consistency
  const formatRulesConfidence = () => {
    if (!record.rules_engine_confidence || record.rules_engine_confidence === 0) {
      return "0%"
    }
    return `${(record.rules_engine_confidence * 100).toFixed(0)}%`
  }

  return (
    <div className="space-y-4">
      {/* Primary Metrics Row */}
      <div className="grid grid-cols-3 gap-4">
      <MetricCard 
        label="Quality Score" 
        value={`${record.qualityScore}%`}
        icon={<BarChart3 className="h-5 w-5" />}
        color="blue"
      />
      <MetricCard 
        label="Rules Passed" 
        value={`${passedRules}/${totalRules}`}
        icon={<CheckCircle className="h-5 w-5" />}
        color="green"
      />
      <MetricCard 
        label="Issues" 
        value={issues}
        icon={<AlertTriangle className="h-5 w-5" />}
        color="red"
      />
      </div>
      
      {/* Confidence Metrics Row */}
      <div className="grid grid-cols-3 gap-4">
        <MetricCard 
          label="Rules Confidence" 
          value={formatRulesConfidence()}
          icon={<Cpu className="h-5 w-5" />}
          color="orange"
        />
        <MetricCard 
          label="LLM Confidence" 
          value={formatLLMConfidence()}
          icon={<Brain className="h-5 w-5" />}
          color="purple"
        />
        <MetricCard 
          label="Combined Confidence" 
          value={`${(record.confidenceScore * 100).toFixed(0)}%`}
          icon={<Target className="h-5 w-5" />}
          color="indigo"
        />
      </div>
    </div>
  )
}

interface RecordDetailModalProps {
  record: QualityRecord | null
  isOpen: boolean
  onClose: () => void
  onUpdate?: (record: QualityRecord) => void
  onReprocess?: (recordId: string, content: string, tags: string[]) => void
  onRecordUpdated?: () => void
}

export default function RecordDetailModal({ 
  record, 
  isOpen, 
  onClose, 
  onUpdate,
  onReprocess,
  onRecordUpdated
}: RecordDetailModalProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'content' | 'quality' | 'pipeline' | 'audit' | 'review'>('overview')
  const [isEditing, setIsEditing] = useState(false)
  const [editedContent, setEditedContent] = useState('')
  const [editedTags, setEditedTags] = useState<string[]>([])
  const [reviewDecision, setReviewDecision] = useState<'approve' | 'reject' | 'revise' | ''>('')
  const [reviewComments, setReviewComments] = useState('')
  const [isSubmittingReview, setIsSubmittingReview] = useState(false)
  const [reviewSubmitted, setReviewSubmitted] = useState(false)
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [loadingTagSuggestions, setLoadingTagSuggestions] = useState(false)
  const [saving, setSaving] = useState(false)
  const [reprocessing, setReprocessing] = useState(false)
  const [approving, setApproving] = useState(false)
  const [flagging, setFlagging] = useState(false)
  const [auditTrail, setAuditTrail] = useState<any[]>([])
  const [loadingAuditTrail, setLoadingAuditTrail] = useState(false)

  // Initialize editing state when record changes
  React.useEffect(() => {
    if (record) {
      setEditedContent(record.content)
      setEditedTags([...record.tags])
      setReviewDecision('')
      setReviewComments('')
      setIsEditing(false)
      setReviewSubmitted(false)
      setReviewError(null)
      
      // Load audit trail for this record
      loadAuditTrail()
    }
  }, [record])

  // Load audit trail when modal opens
  React.useEffect(() => {
    if (isOpen && record) {
      loadAuditTrail()
    }
  }, [isOpen, record])

  if (!isOpen || !record) return null

  // Use internal record for display
  const displayRecord = record

  const handleSaveContent = async () => {
    try {
      setSaving(true)
      
      // Debug logging
      console.log('🔧 Saving content for record:', displayRecord.recordId || displayRecord.id)
      
      // Use recordId if available, fallback to id
      const recordIdentifier = displayRecord.recordId || displayRecord.id
      
      // Call the backend API to save content
      const result = await apiClient.updateRecordContent(
        recordIdentifier, 
        editedContent, 
        editedTags, 
        'current_user', 
        'Content updated via UI'
      )
      
      console.log('✅ Save result:', result)
      
      if (result.success) {
        // Update the local record state
      const updatedRecord = {
          ...displayRecord,
        content: editedContent,
        tags: editedTags,
        updatedAt: new Date().toISOString()
      }
      
        // Update parent state and refresh data
      onUpdate?.(updatedRecord)
        
        // Delay the refresh slightly to allow parent state update to take effect
        setTimeout(() => {
          onRecordUpdated?.()
        }, 100)
        
      setIsEditing(false)
        
        // Show success message
        console.log('Content saved successfully:', result.message)
        alert('Content saved successfully!')
      } else {
        console.error('Failed to save content:', result)
        alert('Failed to save content: ' + (result.message || 'Unknown error'))
      }
    } catch (error) {
      console.error('Error saving content:', error)
      alert('Error saving content: ' + (error instanceof Error ? error.message : String(error)))
    } finally {
      setSaving(false)
    }
  }

  const handleReprocess = async () => {
    try {
      setReprocessing(true)
      
      // Use recordId if available, fallback to id
      const recordIdentifier = displayRecord.recordId || displayRecord.id
      console.log('🔧 Reprocessing record:', recordIdentifier)
      console.log('🔧 Content:', editedContent)
      console.log('🔧 Tags:', editedTags)
      
      // Call the backend API to reprocess the record
      const result = await apiClient.reprocessRecord(
        recordIdentifier,
        editedContent,
        editedTags,
        'current_user',
        'Record reprocessed via UI with updated content'
      )
      
      console.log('✅ Reprocess result:', result)
      
      if (result.success) {
        // Update the local record state with new analysis results
        const updatedRecord = {
          ...displayRecord,
          content: editedContent,
          tags: editedTags,
          qualityScore: result.reprocess_result?.quality_score || displayRecord.qualityScore,
          status: result.reprocess_result?.status || displayRecord.status,
          updatedAt: new Date().toISOString()
        }
        
        onUpdate?.(updatedRecord)
        onRecordUpdated?.()
      setIsEditing(false)
        
        // Show success message
        console.log('Record reprocessed successfully:', result.message)
        alert('Record reprocessed successfully!')
        
        // Load updated audit trail
        loadAuditTrail()
      } else {
        console.error('Failed to reprocess record:', result)
        alert('Failed to reprocess record: ' + (result.message || 'Unknown error'))
      }
    } catch (error) {
      console.error('Error reprocessing:', error)
      
      // More detailed error logging
      if (error instanceof Error) {
        console.error('Error name:', error.name)
        console.error('Error message:', error.message)
        console.error('Error stack:', error.stack)
        alert('Error reprocessing: ' + error.message)
      } else {
        console.error('Unknown error type:', typeof error)
        console.error('Error details:', error)
        alert('Error reprocessing: ' + String(error))
      }
    } finally {
      setReprocessing(false)
    }
  }

  const handleSubmitReview = async () => {
    setIsSubmittingReview(true)
    setReviewError(null)
    try {
      await apiClient.submitFeedback({
        trace_id: displayRecord.trace_id || displayRecord.id,
        decision: reviewDecision,
        comments: reviewComments,
        reviewer_id: 'current_user',
        reviewed_at: new Date().toISOString(),
      })
      setReviewSubmitted(true)
      onRecordUpdated?.()
      setTimeout(() => {
        setReviewSubmitted(false)
        onClose()
      }, 1500)
    } catch (error) {
      setReviewError('Failed to submit review.')
    } finally {
      setIsSubmittingReview(false)
    }
  }

  const handleGetTagSuggestions = async () => {
    setLoadingTagSuggestions(true)
    try {
      const response = await apiClient.getTagSuggestions(editedContent, editedTags)
      if (response.success && response.suggestions.length > 0) {
        // Add new suggestions to existing tags
        const newTags = [...editedTags]
        response.suggestions.forEach((suggestion: string) => {
          if (!newTags.includes(suggestion)) {
            newTags.push(suggestion)
          }
        })
        setEditedTags(newTags)
      } else {
        alert('No new tag suggestions available.')
      }
    } catch (error) {
      console.error('Error getting tag suggestions:', error)
      alert('Failed to get tag suggestions. Please try again.')
    } finally {
      setLoadingTagSuggestions(false)
    }
  }

  const handleApprove = async () => {
    try {
      setApproving(true)
      
      // Use recordId if available, fallback to id
      const recordIdentifier = displayRecord.recordId || displayRecord.id
      
      const result = await apiClient.approveRecord(
        recordIdentifier,
        'current_user',
        'Manually approved via UI'
      )
      
      if (result.success) {
        // Update record status
        const updatedRecord = {
          ...displayRecord,
          status: 'approved' as const,
          updatedAt: new Date().toISOString()
        }
        
        onUpdate?.(updatedRecord)
        onRecordUpdated?.()
        
        console.log('Record approved successfully:', result.message)
        loadAuditTrail()
      } else {
        console.error('Failed to approve record:', result)
      }
    } catch (error) {
      console.error('Error approving record:', error)
    } finally {
      setApproving(false)
    }
  }

  const handleFlag = async () => {
    try {
      setFlagging(true)
      
      // Use recordId if available, fallback to id
      const recordIdentifier = displayRecord.recordId || displayRecord.id
      
      const result = await apiClient.flagRecord(
        recordIdentifier,
        'current_user',
        'Manually flagged via UI'
      )
      
      if (result.success) {
        // Update record status
        const updatedRecord = {
          ...displayRecord,
          status: 'flagged' as const,
          updatedAt: new Date().toISOString()
        }
        
        // Update parent state and refresh data
        onUpdate?.(updatedRecord)
        onRecordUpdated?.()
        
        console.log('Record flagged successfully:', result.message)
        loadAuditTrail()
      } else {
        console.error('Failed to flag record:', result)
      }
    } catch (error) {
      console.error('Error flagging record:', error)
    } finally {
      setFlagging(false)
    }
  }

  const loadAuditTrail = async () => {
    try {
      setLoadingAuditTrail(true)
      
      // Use recordId if available, fallback to id
      const recordIdentifier = displayRecord.recordId || displayRecord.id
      
      const result = await apiClient.getAuditTrail(recordIdentifier)
      
      if (result.success) {
        setAuditTrail(result.audit_trail || [])
      } else {
        console.error('Failed to load audit trail:', result)
        setAuditTrail([])
      }
    } catch (error) {
      console.error('Error loading audit trail:', error)
      setAuditTrail([])
    } finally {
      setLoadingAuditTrail(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved': return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'rejected': return <XCircle className="h-5 w-5 text-red-500" />
      case 'flagged': return <AlertTriangle className="h-5 w-5 text-amber-500" />
      case 'under_review': return <Clock className="h-5 w-5 text-blue-500" />
      default: return <Clock className="h-5 w-5 text-gray-500" />
    }
  }

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-100 px-8 py-6 flex items-center justify-between bg-gradient-to-r from-gray-50 to-white">
          <div className="flex items-center space-x-4">
            {getStatusIcon(displayRecord.status)}
            <div>
              <h2 className="text-xl font-semibold text-gray-900">{displayRecord.recordId}</h2>
              <p className="text-sm text-gray-500">{displayRecord.companyName} • {displayRecord.sourceConnectorName}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <StatusBadge status={displayRecord.status} />
          <button
            onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
              <X className="h-5 w-5 text-gray-400" />
          </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-100 px-8 bg-white">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'overview', label: 'Overview', icon: BarChart3 },
              { id: 'content', label: 'Content', icon: FileText },
              { id: 'quality', label: 'Quality Analysis', icon: Shield },
              { id: 'pipeline', label: 'Pipeline', icon: GitBranch },
              { id: 'audit', label: 'Audit Trail', icon: History },
              { id: 'review', label: 'Review', icon: MessageSquare }
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition-colors ${
                  activeTab === id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-200'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8 bg-gray-50">
          {activeTab === 'overview' && (
            <div className="space-y-8">
              {/* Quality Summary */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Quality Overview</h3>
                <QualitySummary record={record} />
                </div>

              {/* Basic Information */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white border border-gray-100 rounded-xl p-6">
                  <h4 className="font-semibold text-gray-900 mb-4">Record Information</h4>
                  <div className="space-y-3">
                    {[
                      { label: 'Record ID', value: record.recordId },
                      { label: 'Trace ID', value: record.trace_id || record.id || 'N/A' },
                      { label: 'Company', value: record.companyName },
                      { label: 'Source', value: record.sourceConnectorName },
                      { label: 'Priority', value: record.priority.toUpperCase() },
                      { label: 'Created', value: new Date(record.createdAt).toLocaleDateString() },
                      { label: 'Updated', value: new Date(record.updatedAt).toLocaleDateString() }
                    ].map(({ label, value }) => (
                      <div key={label} className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">{label}</span>
                        <span className="text-sm font-medium text-gray-900">{value}</span>
                    </div>
                    ))}
                </div>
              </div>

                <div className="bg-white border border-gray-100 rounded-xl p-6">
                  <h4 className="font-semibold text-gray-900 mb-4">Content Tags</h4>
                <div className="flex flex-wrap gap-2">
                  {(editedTags.length > 0 && editedTags.join(',') !== displayRecord.tags.join(',') 
                    ? editedTags 
                    : displayRecord.tags).map((tag, index) => (
                    <span 
                      key={index}
                        className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
                    >
                      {tag}
                    </span>
                  ))}
                  {((editedTags.length > 0 && editedTags.join(',') !== displayRecord.tags.join(',') 
                    ? editedTags 
                    : displayRecord.tags).length === 0) && (
                    <span className="text-sm text-gray-500 italic">No tags assigned</span>
                  )}
                  </div>
                </div>
              </div>

              {/* Metadata if available */}
              {record.metadata && Object.keys(record.metadata).length > 0 && (
                <div className="bg-white border border-gray-100 rounded-xl p-6">
                  <h4 className="font-semibold text-gray-900 mb-4">Additional Metadata</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(record.metadata).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-center">
                        <span className="text-sm text-gray-600 capitalize">
                          {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                        </span>
                        <span className="text-sm font-medium text-gray-900">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'content' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Document Content</h3>
                <div className="flex items-center space-x-3">
                  {isEditing ? (
                    <>
                      <button
                        onClick={() => {
                          setEditedContent(record.content)
                          setEditedTags([...record.tags])
                          setIsEditing(false)
                        }}
                        className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleSaveContent}
                        disabled={saving}
                        className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                      >
                        {saving ? 'Saving...' : 'Save Changes'}
                      </button>
                      <button
                        onClick={handleReprocess}
                        disabled={reprocessing}
                        className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                      >
                        {reprocessing ? 'Reprocessing...' : 'Save & Reprocess'}
                      </button>
                    </>
                  ) : (
                    <>
                    <button
                      onClick={() => setIsEditing(true)}
                        className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center space-x-2"
                      >
                        <Edit className="h-4 w-4" />
                        <span>Edit</span>
                      </button>
                      
                      {/* Review Action Buttons */}
                      <div className="flex space-x-2">
                        {record.status === 'flagged' && (
                          <button
                            onClick={handleApprove}
                            disabled={approving}
                            className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
                          >
                            <CheckCircle className="h-4 w-4" />
                            <span>{approving ? 'Approving...' : 'Approve'}</span>
                          </button>
                        )}
                        
                        {record.status === 'approved' && (
                          <button
                            onClick={handleFlag}
                            disabled={flagging}
                            className="px-4 py-2 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
                          >
                            <AlertTriangle className="h-4 w-4" />
                            <span>{flagging ? 'Flagging...' : 'Flag for Review'}</span>
                    </button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              </div>

              <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
                <div className="bg-gray-50 px-6 py-3 border-b border-gray-100 flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">Document Text</span>
                  <span className="text-xs text-gray-500">
                    {isEditing ? editedContent.length : record.content.length} characters
                  </span>
                </div>
                <div className="p-6">
                  {isEditing ? (
                    <textarea
                      value={editedContent}
                      onChange={(e) => setEditedContent(e.target.value)}
                      className="w-full h-64 p-4 border border-gray-200 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                      placeholder="Enter document content..."
                    />
                  ) : (
                    <div className="prose max-w-none">
                      <p className="text-gray-900 whitespace-pre-wrap leading-relaxed">
                      {record.content}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Tags Editor */}
              <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
                <div className="bg-gray-50 px-6 py-3 border-b border-gray-100">
                  <span className="text-sm font-medium text-gray-700">Content Tags</span>
                </div>
                <div className="p-6">
                  {isEditing ? (
                    <div className="space-y-4">
                      <div className="flex flex-wrap gap-2">
                        {editedTags.map((tag, index) => (
                          <div key={index} className="flex items-center bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm border border-blue-200">
                            {tag}
                            <button
                              onClick={() => setEditedTags(editedTags.filter((_, i) => i !== index))}
                              className="ml-2 text-blue-600 hover:text-blue-800"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                      <div className="flex space-x-2">
                        <input
                          type="text"
                          placeholder="Add new tag..."
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          onKeyPress={(e) => {
                            if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                              setEditedTags([...editedTags, e.currentTarget.value.trim()])
                              e.currentTarget.value = ''
                            }
                          }}
                        />
                        <button
                          onClick={handleGetTagSuggestions}
                          disabled={loadingTagSuggestions}
                          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center space-x-2 disabled:opacity-50"
                        >
                          {loadingTagSuggestions ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Lightbulb className="h-4 w-4" />
                          )}
                          <span>AI Suggest</span>
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {(editedTags.length > 0 && editedTags.join(',') !== displayRecord.tags.join(',') 
                        ? editedTags 
                        : displayRecord.tags).map((tag, index) => (
                        <span 
                          key={index}
                          className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
                        >
                          {tag}
                        </span>
                      ))}
                      {((editedTags.length > 0 && editedTags.join(',') !== displayRecord.tags.join(',') 
                        ? editedTags 
                        : displayRecord.tags).length === 0) && (
                        <span className="text-sm text-gray-500 italic">No tags assigned</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'quality' && (
            <div className="space-y-8">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-6">Quality Analysis</h3>
                
                {/* Rules Engine Analysis - FIRST */}
                <div className="mb-8">
                  <RulesEngineAnalysis record={record} />
                      </div>

                {/* LLM Analysis - SECOND */}
                <div className="mb-8">
                  <LLMAnalysisCard record={record} isModalOpen={isOpen} />
                          </div>
                          
                {/* Issues Analysis */}
                  {record.issues && record.issues.length > 0 && (
                  <div className="bg-white border border-gray-100 rounded-xl p-6">
                    <h4 className="font-semibold text-gray-900 mb-4 flex items-center">
                      <AlertTriangle className="h-5 w-5 mr-2 text-red-500" />
                      Quality Issues ({record.issues.length})
                    </h4>
                    <div className="space-y-3">
                      {record.issues.map((issue, index) => (
                        <div key={index} className="flex items-start space-x-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                          <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
                              <div className="flex-1">
                            <div className="flex items-start justify-between">
                              <div>
                                <p className="font-medium text-red-900">{issue.type?.replace(/_/g, ' ')}</p>
                                <p className="text-sm text-red-700 mt-1">{issue.description}</p>
                                {issue.suggestion && (
                                  <p className="text-sm text-red-600 mt-2">
                                    <span className="font-medium">💡 Suggestion:</span> {issue.suggestion}
                                  </p>
                                )}
                              </div>
                              <StatusBadge status={issue.severity || 'medium'} size="sm" />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* No Issues */}
                  {(!record.issues || record.issues.length === 0) && (
                  <div className="bg-white border border-gray-100 rounded-xl p-8 text-center">
                    <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
                    <h4 className="font-semibold text-gray-900 mb-2">No Quality Issues Detected</h4>
                    <p className="text-gray-600">All quality checks passed successfully</p>
                    </div>
                  )}
              </div>
            </div>
          )}

          {activeTab === 'pipeline' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">Processing Pipeline</h3>
              
              {/* Processing Pipeline */}
              <div className="bg-white border border-gray-100 rounded-xl p-6">
                <h4 className="font-semibold text-gray-900 mb-4 flex items-center">
                    <GitBranch className="h-5 w-5 mr-2" />
                  Processing Stages
                </h4>
                  <div className="space-y-4">
                  {((record as any).processing_pipeline || [
                    { stage: 'ingestion', status: 'completed', details: 'Content ingested successfully', timestamp: record.createdAt, processing_time_ms: 150 },
                    { stage: 'rules_validation', status: 'completed', details: 'Rules engine validation completed', timestamp: record.createdAt, processing_time_ms: 300 },
                    { 
                      stage: 'llm_analysis', 
                      status: (() => {
                        // Use the SAME logic as llmTriggered variable for perfect sync
                        const llmCheck = record.quality_checks?.find(q => q.check_name === 'llm_semantic_validation')
                        const wasTriggered = llmCheck && llmCheck.status !== 'SKIPPED'
                        
                        if (!wasTriggered) {
                          return 'not_triggered'
                        } else if (llmCheck.status === 'ERROR') {
                          return 'failed'  // Only technical errors are "failed"
                        } else if (llmCheck.status === 'FAIL' || llmCheck.status === 'PASS' || llmCheck.status === 'COMPLETED') {
                          return 'completed'  // Both FAIL and PASS mean LLM analysis completed successfully
                        } else {
                          return 'completed'  // Default to completed if triggered
                        }
                      })(), 
                      details: (() => {
                        const llmCheck = record.quality_checks?.find(q => q.check_name === 'llm_semantic_validation')
                        const llmDecision = record.quality_checks?.find(q => q.check_name === 'llm_invocation_decision')
                        const qualityScore = record.qualityScore || 0
                        const isRecordApproved = record.status === 'approved'
                        
                        // Use SAME logic as llmTriggered variable for perfect synchronization
                        const wasTriggered = llmCheck && llmCheck.status !== 'SKIPPED'
                        
                        // Calculate rule metrics for this pipeline context
                        const rulesChecks = (record.quality_checks || []).filter((check: any) => 
                          check.check_name !== 'llm_semantic_validation' && 
                          check.check_name !== 'llm_invocation_decision'
                        )
                        const passedRules = rulesChecks.filter((check: any) => 
                          check.status?.toUpperCase() === 'PASS' || check.status?.toUpperCase() === 'PASSED'
                        ).length
                        const totalRules = rulesChecks.length
                        const passRate = totalRules > 0 ? (passedRules / totalRules) * 100 : 0
                        
                        if (!wasTriggered) {
                          // LLM NOT TRIGGERED - Handle all cases with detailed reasoning
                          
                          // First, check if there's a specific decision reason
                          if (llmDecision && llmDecision.failure_reason) {
                            const reason = llmDecision.failure_reason
                            
                            // Parse different LLM invocation modes for user-friendly messages
                            if (reason.includes('Range mode') && reason.includes('auto-approve')) {
                              return `LLM not triggered - excellent quality (${passRate.toFixed(1)}% > 89%) saves analysis cost`
                            } else if (reason.includes('Range mode') && reason.includes('auto-reject')) {
                              return `LLM not triggered - quality below minimum (${passRate.toFixed(1)}% < 70%)`
                            } else if (reason.includes('Binary mode') && reason.includes('failed')) {
                              return `LLM not triggered - binary mode needs all rules to pass (${passedRules}/${totalRules} passed)`
                            } else if (reason.includes('Percentage mode') && reason.includes('below')) {
                              return `LLM not triggered - pass rate ${passRate.toFixed(1)}% below threshold`
                            } else if (reason.includes('Weighted mode') && reason.includes('below')) {
                              return `LLM not triggered - weighted score below threshold`
                        } else {
                              return `LLM not triggered - ${reason}`
                            }
                          }
                          
                          // Fallback: If no decision reason, check if there are any errors
                          if (llmCheck && llmCheck.status === 'ERROR') {
                            return `LLM not triggered - service error: ${llmCheck.failure_reason || 'technical failure'}`
                          }
                          
                          // Final fallback: Generic message with current metrics
                          return `LLM not triggered - threshold conditions not met (${passedRules}/${totalRules} rules passed, ${passRate.toFixed(1)}%)`
                          
                        } else {
                          // LLM WAS TRIGGERED - Handle completion cases
                          
                          if (llmCheck.status === 'ERROR') {
                            return `LLM analysis failed - technical error: ${llmCheck.failure_reason || 'service unavailable'}`
                          } else if (llmCheck.status === 'FAIL' || llmCheck.status === 'PASS') {
                            // Dynamic message based on approval status
                            if (isRecordApproved) {
                              return 'LLM semantic analysis completed - content approved with insights'
                            } else {
                              return 'LLM semantic analysis completed - improvement suggestions provided'
                            }
                          } else {
                            // Any other status when triggered means completed
                            return 'LLM semantic analysis completed successfully'
                          }
                        }
                      })(), 
                      timestamp: record.updatedAt, 
                      processing_time_ms: (() => {
                        const llmCheck = record.quality_checks?.find(q => q.check_name === 'llm_semantic_validation')
                        return (llmCheck && llmCheck.status !== 'SKIPPED' && llmCheck.status !== undefined) ? 2000 : 0
                      })()
                    },
                    { stage: 'quality_scoring', status: 'completed', details: 'Quality score calculation', timestamp: record.updatedAt, processing_time_ms: 50 }
                  ]).map((stage: any, index: number) => (
                      <div key={index} className="flex items-start space-x-4">
                        <div className="flex-shrink-0">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                            stage.status === 'completed' ? 'bg-green-100 text-green-600' :
                            stage.status === 'failed' ? 'bg-red-100 text-red-600' :
                            stage.status === 'skipped' ? 'bg-gray-100 text-gray-600' :
                            stage.status === 'not_triggered' ? 'bg-orange-100 text-orange-600' :
                            'bg-yellow-100 text-yellow-600'
                          }`}>
                            {stage.status === 'completed' ? (
                              <CheckCircle className="h-5 w-5" />
                            ) : stage.status === 'failed' ? (
                              <XCircle className="h-5 w-5" />
                            ) : stage.status === 'skipped' ? (
                              <Clock className="h-5 w-5" />
                            ) : stage.status === 'not_triggered' ? (
                              <AlertTriangle className="h-5 w-5" />
                            ) : (
                              <Clock className="h-5 w-5" />
                            )}
                          </div>
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm font-medium text-gray-900 capitalize">
                              {stage.stage.replace('_', ' ')}
                            </h4>
                            <span className="text-xs text-gray-500">
                              {stage.status === 'not_triggered' ? 'Not triggered' : formatDuration(stage.processing_time_ms)}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 mt-1">{stage.details}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            {new Date(stage.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Performance Metrics */}
              <div className="bg-white border border-gray-100 rounded-xl p-6">
                <h4 className="font-semibold text-gray-900 mb-4 flex items-center">
                    <Activity className="h-5 w-5 mr-2" />
                    Performance Metrics
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <MetricCard 
                    label="Processing Time" 
                    value="2.5s"
                    icon={<Clock className="h-5 w-5" />}
                    color="blue"
                  />
                  <MetricCard 
                    label="Memory Usage" 
                    value="45MB"
                    icon={<MemoryStick className="h-5 w-5" />}
                    color="green"
                  />
                  <MetricCard 
                    label="Storage Size" 
                    value={formatBytes(record.content.length * 2)}
                    icon={<Database className="h-5 w-5" />}
                    color="purple"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'audit' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Audit Trail</h3>
                <button
                  onClick={loadAuditTrail}
                  disabled={loadingAuditTrail}
                  className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 transition-colors disabled:opacity-50"
                >
                  {loadingAuditTrail ? 'Loading...' : 'Refresh'}
                </button>
                </div>
              
              <div className="bg-white border border-gray-100 rounded-xl p-6">
                {loadingAuditTrail ? (
                  <div className="text-center py-8 text-gray-500">
                    <div className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
                    <p>Loading audit trail...</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {auditTrail.length > 0 ? auditTrail.map((event: any, index: number) => (
                      <div key={index} className="flex items-start space-x-4 pb-4 border-b border-gray-100 last:border-b-0">
                        <div className={`w-3 h-3 rounded-full mt-2 ${
                          event.action === 'manual_approve' ? 'bg-green-500' :
                          event.action === 'manual_flag' ? 'bg-amber-500' :
                          event.action === 'content_update' ? 'bg-blue-500' :
                          event.action === 'reprocess' ? 'bg-purple-500' :
                          'bg-gray-400'
                        }`} />
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-gray-900 capitalize">
                              {event.action.replace(/_/g, ' ')}
                            </span>
                            <span className="text-sm text-gray-500">
                              {new Date(event.timestamp).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 mt-1">{event.reason}</p>
                          
                          {/* Show specific details based on action type */}
                          {event.action === 'content_update' && event.changes && (
                            <div className="mt-2 p-2 bg-blue-50 rounded text-xs">
                              <p className="font-medium text-blue-900">Content Changes:</p>
                              {event.changes.content && (
                                <p className="text-blue-700">Content updated</p>
                              )}
                              {event.changes.tags && (
                                <p className="text-blue-700">
                                  Tags: {event.changes.tags.old.join(', ')} → {event.changes.tags.new.join(', ')}
                                </p>
                              )}
                        </div>
                          )}
                          
                          {event.action === 'reprocess' && event.reprocess_result && (
                            <div className="mt-2 p-2 bg-purple-50 rounded text-xs">
                              <p className="font-medium text-purple-900">Reprocess Result:</p>
                              <p className="text-purple-700">
                                Quality Score: {event.reprocess_result.new_quality_score}% | 
                                Status: {event.reprocess_result.new_status}
                              </p>
                      </div>
                          )}
                          
                          {(event.action === 'manual_approve' || event.action === 'manual_flag') && event.status_change && (
                            <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
                              <p className="font-medium text-gray-900">Status Change:</p>
                              <p className="text-gray-700">
                                {event.status_change.old} → {event.status_change.new}
                              </p>
                </div>
                          )}
                          
                          <p className="text-xs text-gray-500 mt-1">by {event.user_id}</p>
                </div>
                        </div>
                    )) : (
                      <div className="text-center py-8 text-gray-500">
                        <History className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                        <p>No audit events recorded</p>
                        <p className="text-xs mt-1">Actions like content updates, approvals, and flags will appear here</p>
                        </div>
                    )}
                  </div>
                )}
                  </div>
                </div>
          )}

          {activeTab === 'review' && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-900">Manual Review Actions</h3>
              
              <div className="bg-white border border-gray-100 rounded-xl p-6">
                <h4 className="font-semibold text-gray-900 mb-4">Status Actions</h4>
                <p className="text-sm text-gray-600 mb-6">
                  Use these actions to manually change the record's status and move it between approval queues.
                </p>
                
                <div className="flex space-x-4">
                  {record.status === 'flagged' && (
                    <button
                      onClick={handleApprove}
                      disabled={approving}
                      className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
                    >
                      <CheckCircle className="h-5 w-5" />
                      <span>{approving ? 'Approving...' : 'Approve Record'}</span>
                    </button>
                  )}
                  
                  {record.status === 'approved' && (
                    <button
                      onClick={handleFlag}
                      disabled={flagging}
                      className="px-6 py-3 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
                    >
                      <AlertTriangle className="h-5 w-5" />
                      <span>{flagging ? 'Flagging...' : 'Flag for Review'}</span>
                    </button>
                  )}
                  
                  {(record.status !== 'approved' && record.status !== 'flagged') && (
                    <div className="flex space-x-3">
                      <button
                        onClick={handleApprove}
                        disabled={approving}
                        className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
                      >
                        <CheckCircle className="h-5 w-5" />
                        <span>{approving ? 'Approving...' : 'Approve'}</span>
                      </button>
                      <button
                        onClick={handleFlag}
                        disabled={flagging}
                        className="px-6 py-3 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
                      >
                        <AlertTriangle className="h-5 w-5" />
                        <span>{flagging ? 'Flagging...' : 'Flag'}</span>
                      </button>
                            </div>
                          )}
                        </div>
                
                <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-start space-x-2">
                    <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-blue-800">
                      <p className="font-medium">Action Effects:</p>
                      <ul className="text-xs text-blue-700 mt-1 space-y-1">
                        <li>• <strong>Approve:</strong> Moves record to approved queue, available for final processing</li>
                        <li>• <strong>Flag:</strong> Moves record to review queue for manual inspection</li>
                        <li>• All actions create audit trail entries with timestamps and user information</li>
                  </ul>
                </div>
            </div>
                </div>
              </div>

              {/* Legacy Review System */}
              <div className="bg-white border border-gray-100 rounded-xl p-6">
                <h4 className="font-semibold text-gray-900 mb-4">Detailed Feedback (Optional)</h4>
                <p className="text-sm text-gray-600 mb-4">
                  Provide additional feedback comments for this record.
                </p>
              
              {reviewSubmitted ? (
                <div className="text-center py-8">
                    <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
                    <p className="text-green-800">Feedback submitted successfully</p>
                </div>
              ) : (
                  <div className="space-y-4">
                    <textarea
                      value={reviewComments}
                      onChange={(e) => setReviewComments(e.target.value)}
                      placeholder="Optional: Provide detailed feedback about this record..."
                      className="w-full h-24 p-4 border border-gray-200 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    
                    <div className="flex justify-end">
                    <button
                        onClick={async () => {
                          if (!reviewComments.trim()) {
                            alert('Please enter some feedback comments first.');
                            return;
                          }
                          setIsSubmittingReview(true);
                          try {
                            await apiClient.submitFeedback({
                              trace_id: record.trace_id || record.id,
                              decision: 'comment',
                              comments: reviewComments,
                              reviewer_id: 'current_user',
                              reviewed_at: new Date().toISOString(),
                            });
                            setReviewSubmitted(true);
                            setTimeout(() => setReviewSubmitted(false), 2000);
                          } catch (error) {
                            setReviewError('Failed to submit feedback');
                          } finally {
                            setIsSubmittingReview(false);
                          }
                        }}
                        disabled={!reviewComments.trim() || isSubmittingReview}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {isSubmittingReview ? 'Submitting...' : 'Submit Feedback'}
                    </button>
                  </div>

                  {reviewError && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <p className="text-sm text-red-800">{reviewError}</p>
                    </div>
                  )}
                </div>
              )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-100 px-8 py-4 flex items-center justify-between bg-white">
          <div className="flex items-center space-x-6 text-sm text-gray-500">
            <span className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              <span>ID: {record.recordId}</span>
            </span>
            <span className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-purple-500" />
              <span>Trace: {record.trace_id || record.id || 'N/A'}</span>
            </span>
            <span>Quality: {record.qualityScore}%</span>
            <span>Issues: {record.issues?.length || 0}</span>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => copyToClipboard(record.trace_id || record.id || '')}
              className="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center space-x-2"
            >
              <Copy className="h-4 w-4" />
              <span>Copy Trace ID</span>
            </button>
            <button
              onClick={() => copyToClipboard(JSON.stringify(record, null, 2))}
              className="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center space-x-2"
            >
              <Copy className="h-4 w-4" />
              <span>Copy JSON</span>
            </button>
            <button
              onClick={() => {
                const blob = new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `record-${record.recordId}.json`
                a.click()
                URL.revokeObjectURL(url)
              }}
              className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
            >
              <Download className="h-4 w-4" />
              <span>Export</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
} 