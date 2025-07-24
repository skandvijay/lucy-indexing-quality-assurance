'use client'

import React, { useState, useEffect } from 'react'
import { 
  Play, 
  Code, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Copy,
  Download,
  RefreshCw,
  Zap,
  Database,
  Settings,
  ExternalLink,
  Upload,
  FileText,
  Brain,
  Clock,
  Filter,
  Shield,
  Target,
  Edit3,
  Save,
  RotateCcw
} from 'lucide-react'

interface ApiTestResult {
  status: number
  statusText: string
  data: any
  headers: Record<string, string>
  duration: number
  timestamp: string
  rulesEngineResults?: any[]
  llmJudgeResults?: any
}

interface TestEndpoint {
  id: string
  name: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  path: string
  description: string
  samplePayload?: any
  category: 'system' | 'ingestion' | 'analysis' | 'management' | 'advanced'
}

interface LLMConstraint {
  id: string
  name: string
  description: string
  enabled: boolean
  weight: number
  rule: string
}

interface RedTeamScenario {
  id: string
  name: string
  description: string
  content: string
  tags: string[]
  expectedIssues: string[]
}

const testEndpoints: TestEndpoint[] = [
  // ================================
  // CONTENT INGESTION (✅ Working & Clear)
  // ================================
  {
    id: 'ingest',
    name: '✅ Content Ingestion (Main)',
    method: 'POST',
    path: '/ingest',
    description: 'PRIMARY ENDPOINT: Submit content for complete quality analysis with rules engine and LLM judge',
    category: 'ingestion',
    samplePayload: {
      record_id: 'main_001',
      content: 'This comprehensive guide covers machine learning deployment strategies, including containerization, monitoring frameworks, A/B testing protocols, and production rollout procedures for enterprise applications.',
      tags: ['machine-learning', 'deployment', 'enterprise', 'containerization', 'monitoring'],
      source_connector: 'Confluence',
      content_metadata: {
        author: 'ML Engineering Team',
        department: 'Engineering',
        document_type: 'technical-guide',
        file_size: 4096,
        language: 'en',
        created_at: new Date().toISOString()
      }
    }
  },

  // ================================
  // REMOVED CONFUSING ENDPOINTS
  // ================================
  // The following endpoints were removed to eliminate confusion:
  // - /ingest/batch (hardcoded scores, no real analysis)
  // - /ingest/sharepoint (format-specific, different logic)
  // - /ingest/elasticsearch (format-specific, different logic)  
  // - /ingest/file (inconsistent processing)
  //
  // ✅ SOLUTION: Use /ingest for single records
  // ✅ FUTURE: Use /ingest/bulk for multiple records (any format)

  /*
  // DEPRECATED ENDPOINTS - Commented out to reduce confusion
  {
    id: 'ingest-batch',
    name: '⚠️ Batch Content Ingestion (DEPRECATED)',
    method: 'POST',
    path: '/ingest/batch',
    description: 'DEPRECATED: Uses hardcoded scores instead of real analysis. Use /ingest for proper processing.',
    category: 'deprecated'
  },
  {
    id: 'ingest-sharepoint',
    name: '⚠️ SharePoint Data Ingestion (DEPRECATED)',
    method: 'POST',
    path: '/ingest/sharepoint',
    description: 'DEPRECATED: Format-specific endpoint with different logic. Use /ingest for consistent processing.',
    category: 'deprecated'
  },
  */

  // ================================
  // ANALYSIS ENDPOINTS (✅ Working)
  // ================================
  {
    id: 'rules-check',
    name: 'Rules Engine Only',
    method: 'POST',
    path: '/rules/check',
    description: 'Test content against rules engine only (fast, cheap checks)',
    category: 'analysis',
    samplePayload: {
      document_text: 'Sample document for testing quality rules and validation checks',
      tags: ['generic', 'test', 'document'],
      source_connector: 'SharePoint'
    }
  },
  {
    id: 'llm-analyze',
    name: 'LLM Analysis',
    method: 'POST',
    path: '/llm/analyze',
    description: 'Submit content for LLM-based quality analysis',
    category: 'analysis',
    samplePayload: {
      content: 'Enterprise software development requires careful consideration of scalability, maintainability, and security. This document outlines best practices for implementing robust applications.',
      tags: ['software', 'enterprise', 'development', 'best-practices'],
      context: {
        source: 'confluence',
        author: 'Technical Team',
        department: 'Engineering'
      }
    }
  },
  {
    id: 'llm-redteam',
    name: 'Red Team Analysis',
    method: 'POST',
    path: '/llm/redteam',
    description: 'Submit content for adversarial red team testing',
    category: 'analysis',
    samplePayload: {
      scenario_id: 'generic_tags',
      content: 'Test content with potentially problematic elements',
      tags: ['generic', 'test'],
      test_objectives: ['Detect quality issues', 'Test system robustness'],
      expected_issues: ['generic_tags', 'low_quality']
    }
  },

  // ================================
  // DATA RETRIEVAL (✅ Working)
  // ================================
  {
    id: 'records',
    name: 'Quality Records',
    method: 'GET',
    path: '/records',
    description: 'Retrieve quality records with filtering and pagination',
    category: 'management'
  },
  {
    id: 'issues',
    name: 'System Issues',
    method: 'GET',
    path: '/issues',
    description: 'Get current system issues and problems',
    category: 'management'
  },
  {
    id: 'dead-letters',
    name: 'Dead Letters',
    method: 'GET',
    path: '/dead-letters',
    description: 'Get failed processing records for review',
    category: 'management'
  },
  {
    id: 'companies',
    name: 'Companies List',
    method: 'GET',
    path: '/companies',
    description: 'List all companies in the system',
    category: 'management'
  },
  {
    id: 'connectors',
    name: 'Source Connectors',
    method: 'GET',
    path: '/connectors',
    description: 'List available source connectors',
    category: 'management'
  },

  // ================================
  // ADVANCED FEATURES (✅ Working)
  // ================================
  {
    id: 'thresholds',
    name: 'Dynamic Thresholds',
    method: 'GET',
    path: '/thresholds',
    description: 'Get all configurable quality thresholds',
    category: 'advanced'
  },
  {
    id: 'request-logs',
    name: 'Request Logs',
    method: 'GET',
    path: '/request-logs',
    description: 'Get system request logs and analytics',
    category: 'advanced'
  },
  {
    id: 'llm-settings',
    name: 'LLM Settings',
    method: 'GET',
    path: '/settings/llm-mode',
    description: 'Get LLM invocation settings and configuration',
    category: 'advanced'
  },

  // ================================
  // EXTERNAL API ENDPOINTS (✅ Working)
  // ================================
  {
    id: 'external-api-bulk',
    name: 'External API Bulk Ingestion',
    method: 'POST',
    path: '/external-api/bulk-ingest',
    description: 'High-performance bulk ingestion for external API data (250K+ records/day)',
    category: 'ingestion',
    samplePayload: [
      {
        id: 'bulk_001',
        title: 'External API Record 1',
        content: 'Sample content from external API for bulk processing',
        tags: ['external-api', 'bulk', 'test'],
        metadata: {
          source: 'external_api',
          timestamp: new Date().toISOString()
        }
      }
    ]
  }

  // ================================
  // COMMENTED OUT - ENDPOINTS WITHOUT BACKEND IMPLEMENTATION
  // ================================
  
  /*
  // These endpoints were found in frontend but don't have backend implementations
  // Commenting them out to avoid confusion and 404 errors
  
  {
    id: 'chain-of-thought',
    name: 'Chain of Thought Analysis',
    method: 'POST',
    path: '/llm/chain-of-thought',
    description: 'MOCK: Advanced reasoning analysis (backend not implemented)',
    category: 'analysis'
  },
  {
    id: 'self-consistency',
    name: 'Self Consistency Analysis', 
    method: 'POST',
    path: '/llm/self-consistency',
    description: 'MOCK: Self-consistency validation (backend not implemented)',
    category: 'analysis'
  },
  {
    id: 'export-records',
    name: 'Export Records',
    method: 'GET',
    path: '/export/records',
    description: 'MOCK: Export records (basic implementation only)',
    category: 'management'
  },
  {
    id: 'import-records',
    name: 'Import Records',
    method: 'POST',
    path: '/import/records',
    description: 'MOCK: Import records (basic implementation only)',
    category: 'management'
  },
  {
    id: 'tag-suggestions',
    name: 'LLM Tag Suggestions',
    method: 'POST', 
    path: '/llm/tag-suggestions',
    description: 'MOCK: AI-powered tag suggestions (backend not fully implemented)',
    category: 'analysis'
  },
  {
    id: 'improvement-suggestions',
    name: 'LLM Improvement Suggestions',
    method: 'POST',
    path: '/llm/improvement-suggestions', 
    description: 'MOCK: Content improvement suggestions (backend not implemented)',
    category: 'analysis'
  },
  {
    id: 'redteam-results',
    name: 'Red Team Results',
    method: 'GET',
    path: '/redteam/results',
    description: 'MOCK: Red team test results (partial implementation)',
    category: 'advanced'
  },
  {
    id: 'evaluation-metrics',
    name: 'Evaluation Metrics',
    method: 'GET',
    path: '/evaluation/metrics',
    description: 'MOCK: System evaluation metrics (basic implementation)',
    category: 'advanced'
  },
  {
    id: 'alert-emails',
    name: 'Alert Email Management',
    method: 'GET',
    path: '/alerts/emails',
    description: 'MOCK: Email alert configuration (basic implementation)',
    category: 'management'
  }
  */
]

const defaultLLMPrompt = `You are an expert content quality analyst. Analyze the provided content and tags for quality, relevance, and usefulness.

Content: {{content}}
Tags: {{tags}}
Source: {{source}}
Context: {{context}}

Please evaluate:
1. Content Quality (clarity, depth, usefulness)
2. Tag Relevance (how well tags match content)
3. Information Completeness
4. Technical Accuracy (if applicable)
5. Business Value

Provide a quality score (0-100) and specific improvement suggestions.`

const defaultConstraints: LLMConstraint[] = [
  {
    id: 'tag_relevance',
    name: 'Tag Relevance',
    description: 'Tags must be highly relevant to content',
    enabled: true,
    weight: 0.3,
    rule: 'At least 80% of tags should directly relate to content topics'
  },
  {
    id: 'content_depth',
    name: 'Content Depth',
    description: 'Content should be substantial and informative',
    enabled: true,
    weight: 0.25,
    rule: 'Content should be at least 100 words and provide actionable information'
  },
  {
    id: 'no_generic_tags',
    name: 'No Generic Tags',
    description: 'Avoid overly generic or meaningless tags',
    enabled: true,
    weight: 0.2,
    rule: 'Generic tags like "document", "file", "content" should be avoided'
  },
  {
    id: 'technical_accuracy',
    name: 'Technical Accuracy',
    description: 'Technical content should be accurate and current',
    enabled: false,
    weight: 0.15,
    rule: 'Technical information should be verifiable and up-to-date'
  },
  {
    id: 'business_value',
    name: 'Business Value',
    description: 'Content should provide clear business or educational value',
    enabled: true,
    weight: 0.1,
    rule: 'Content should help users achieve specific goals or learn something valuable'
  }
]

const redTeamScenarios: RedTeamScenario[] = [
  {
    id: 'generic_tags_attack',
    name: 'Generic Tags Attack',
    description: 'Test with extremely generic and meaningless tags',
    content: 'This document contains important information about our company processes and procedures.',
    tags: ['document', 'important', 'information', 'company', 'general', 'misc', 'data', 'content'],
    expectedIssues: ['Generic tags detected', 'Low tag specificity', 'Minimal content value']
  },
  {
    id: 'tag_content_mismatch',
    name: 'Tag-Content Mismatch',
    description: 'Content and tags are completely unrelated',
    content: 'Recipe for chocolate chip cookies: Mix flour, sugar, butter, eggs, and chocolate chips. Bake at 350°F for 12 minutes.',
    tags: ['machine-learning', 'artificial-intelligence', 'enterprise-software', 'database-optimization'],
    expectedIssues: ['Tag-content mismatch', 'Irrelevant tags', 'Content categorization error']
  },
  {
    id: 'minimal_content',
    name: 'Minimal Content Test',
    description: 'Very short, low-value content with specific tags',
    content: 'Good.',
    tags: ['excellent-documentation', 'comprehensive-guide', 'best-practices', 'detailed-analysis'],
    expectedIssues: ['Insufficient content length', 'Over-tagging', 'Content-tag imbalance']
  },
  {
    id: 'spam_content',
    name: 'Spam Content Detection',
    description: 'Test content that looks like spam or placeholder text',
    content: 'Lorem ipsum dolor sit amet test test test document document document placeholder content sample text example.',
    tags: ['lorem-ipsum', 'test', 'placeholder', 'sample'],
    expectedIssues: ['Spam content detected', 'Placeholder text', 'Low content quality']
  },
  {
    id: 'over_tagging',
    name: 'Over-tagging Attack',
    description: 'Excessive number of tags for simple content',
    content: 'Meeting scheduled for Tuesday.',
    tags: ['meeting', 'schedule', 'tuesday', 'calendar', 'appointment', 'business', 'work', 'office', 'corporate', 'planning', 'organization', 'time-management', 'productivity', 'team', 'collaboration'],
    expectedIssues: ['Excessive tagging', 'Tag spam', 'Poor tag-to-content ratio']
  },
  {
    id: 'duplicate_content',
    name: 'Duplicate Content Test',
    description: 'Repetitive content with different tags',
    content: 'This is a test. This is a test. This is a test. This is a test. This is a test.',
    tags: ['testing', 'quality-assurance', 'validation'],
    expectedIssues: ['Duplicate content', 'Repetitive text', 'Low content diversity']
  }
]

const samplePayloads = {
  minimal: {
    record_id: 'test_minimal',
    content: 'Short test content',
    tags: ['test'],
    source_connector: 'api_test'
  },
  complex: {
    record_id: 'test_complex',
    content: `This is a comprehensive technical documentation about implementing machine learning pipelines in production environments. 
    
Key topics covered:
- Data preprocessing and validation
- Model training and hyperparameter tuning
- Deployment strategies (blue-green, canary)
- Monitoring and alerting systems
- A/B testing frameworks
- Performance optimization techniques

The document includes code examples, architecture diagrams, and best practices derived from real-world implementations across multiple Fortune 500 companies.`,
    tags: ['machine-learning', 'mlops', 'production', 'deployment', 'monitoring', 'optimization', 'enterprise'],
    source_connector: 'confluence',
    metadata: {
      author: 'ML Engineering Team',
      department: 'Data Science',
      document_type: 'technical-documentation',
      file_size: 15680,
      language: 'en',
      created_at: new Date().toISOString(),
      last_modified: new Date().toISOString(),
      tags_auto_generated: false,
      review_status: 'pending'
    }
  },
  problematic: {
    record_id: 'test_problematic',
    content: 'test test test document document document generic content generic content',
    tags: ['generic', 'document', 'test', 'content', 'misc', 'general'],
    source_connector: 'sharepoint',
    metadata: {
      author: '',
      department: 'unknown'
    }
  }
}

export default function ApiTestInterface() {
  const [selectedEndpoint, setSelectedEndpoint] = useState<TestEndpoint>(testEndpoints[0])
  const [customPayload, setCustomPayload] = useState('')
  const [customHeaders, setCustomHeaders] = useState('{"Content-Type": "application/json"}')
  const [apiBaseUrl, setApiBaseUrl] = useState(process.env.NEXT_PUBLIC_API_URL || '/api')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<ApiTestResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [testHistory, setTestHistory] = useState<ApiTestResult[]>([])
  
  // LLM Judge customization
  const [llmPrompt, setLlmPrompt] = useState(defaultLLMPrompt)
  const [constraints, setConstraints] = useState<LLMConstraint[]>(defaultConstraints)
  const [selectedRedTeamScenario, setSelectedRedTeamScenario] = useState<RedTeamScenario | null>(null)
  const [showLlmConfig, setShowLlmConfig] = useState(false)
  const [showRedTeam, setShowRedTeam] = useState(false)

  useEffect(() => {
    if (selectedEndpoint.samplePayload) {
      setCustomPayload(JSON.stringify(selectedEndpoint.samplePayload, null, 2))
    } else {
      setCustomPayload('')
    }
  }, [selectedEndpoint])

  const executeTest = async () => {
    setIsLoading(true)
    setError(null)
    setResult(null)

    const startTime = performance.now()
    
    try {
      const url = `${apiBaseUrl}${selectedEndpoint.path}`
      let headers: Record<string, string> = {}
      
      try {
        headers = JSON.parse(customHeaders || '{}')
      } catch {
        headers = { 'Content-Type': 'application/json' }
      }

      const config: RequestInit = {
        method: selectedEndpoint.method,
        headers,
        mode: 'cors'
      }

      if (['POST', 'PUT'].includes(selectedEndpoint.method) && customPayload) {
        let payload = customPayload
        
        // For LLM endpoints, inject custom configuration
        if (selectedEndpoint.id === 'llm-judge') {
          try {
            const payloadObj = JSON.parse(payload)
            payloadObj.custom_prompt = llmPrompt
            payloadObj.constraints = constraints.filter(c => c.enabled)
            payloadObj.quality_weights = constraints.reduce((acc, c) => {
              if (c.enabled) acc[c.id] = c.weight
              return acc
            }, {} as Record<string, number>)
            payload = JSON.stringify(payloadObj, null, 2)
          } catch {
            // Keep original payload if parsing fails
          }
        }
        
        config.body = payload
      }

      const response = await fetch(url, config)
      const endTime = performance.now()
      
      const responseHeaders: Record<string, string> = {}
      response.headers.forEach((value, key) => {
        responseHeaders[key] = value
      })

      let responseData
      const contentType = response.headers.get('content-type')
      
      try {
        if (contentType?.includes('application/json')) {
          responseData = await response.json()
        } else {
          responseData = await response.text()
        }
      } catch {
        responseData = 'Unable to parse response'
      }

      const testResult: ApiTestResult = {
        status: response.status,
        statusText: response.statusText,
        data: responseData,
        headers: responseHeaders,
        duration: endTime - startTime,
        timestamp: new Date().toISOString()
      }

      // Parse rules engine and LLM results if present
      if (responseData && typeof responseData === 'object') {
        if (responseData.rules_engine_results) {
          testResult.rulesEngineResults = responseData.rules_engine_results
        }
        if (responseData.llm_judge_results) {
          testResult.llmJudgeResults = responseData.llm_judge_results
        }
      }

      setResult(testResult)
      setTestHistory(prev => [testResult, ...prev.slice(0, 9)]) // Keep last 10 results

      // If this was an ingest operation and it was successful, trigger a refresh
      if (response.ok && (selectedEndpoint.id === 'ingest' || selectedEndpoint.id === 'ingest/batch')) {
        // Dispatch a custom event to notify other components to refresh
        window.dispatchEvent(new CustomEvent('records-updated'));
      }

    } catch (err: any) {
      const errorMessage = err.message || 'Request failed'
      setError(errorMessage)
      console.error('API Test Error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const loadSamplePayload = (type: keyof typeof samplePayloads) => {
    setCustomPayload(JSON.stringify(samplePayloads[type], null, 2))
  }

  const loadRedTeamScenario = (scenario: RedTeamScenario) => {
    const payload = {
      record_id: `redteam_${scenario.id}`,
      content: scenario.content,
      tags: scenario.tags,
      source_connector: 'api_test',
      redteam_scenario: scenario.id,
      expected_issues: scenario.expectedIssues
    }
    setCustomPayload(JSON.stringify(payload, null, 2))
    setSelectedRedTeamScenario(scenario)
  }

  const updateConstraint = (id: string, updates: Partial<LLMConstraint>) => {
    setConstraints(prev => prev.map(c => 
      c.id === id ? { ...c, ...updates } : c
    ))
  }

  const resetLlmConfig = () => {
    setLlmPrompt(defaultLLMPrompt)
    setConstraints(defaultConstraints)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const downloadResponse = () => {
    if (!result) return
    
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `api-test-${selectedEndpoint.id}-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const getStatusIcon = (status: number) => {
    if (status >= 200 && status < 300) return <CheckCircle className="h-5 w-5 text-green-500" />
    if (status >= 400 && status < 500) return <AlertCircle className="h-5 w-5 text-yellow-500" />
    if (status >= 500) return <XCircle className="h-5 w-5 text-red-500" />
    return <AlertCircle className="h-5 w-5 text-gray-500" />
  }

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'system': return <Database className="h-4 w-4" />
      case 'ingestion': return <Upload className="h-4 w-4" />
      case 'analysis': return <Brain className="h-4 w-4" />
      case 'management': return <Settings className="h-4 w-4" />
      case 'advanced': return <Target className="h-4 w-4" />
      default: return <FileText className="h-4 w-4" />
    }
  }

  const filteredEndpoints = selectedCategory === 'all' 
    ? testEndpoints 
    : testEndpoints.filter(ep => ep.category === selectedCategory)

  const renderRulesEngineResults = (results: any[]) => {
    if (!results || results.length === 0) return null

    return (
      <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h4 className="text-sm font-semibold text-blue-900 mb-3 flex items-center">
          <Zap className="h-4 w-4 mr-2" />
          Rules Engine Results ({results.length} checks)
        </h4>
        <div className="space-y-2">
          {results.map((result, idx) => (
            <div key={idx} className={`p-3 rounded border ${
              result.status === 'PASS' 
                ? 'bg-green-50 border-green-200 text-green-800' 
                : 'bg-red-50 border-red-200 text-red-800'
            }`}>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{result.check_name}</span>
                <span className={`text-xs px-2 py-1 rounded ${
                  result.status === 'PASS' ? 'bg-green-100' : 'bg-red-100'
                }`}>
                  {result.status}
                </span>
              </div>
              {result.failure_reason && (
                <p className="text-xs mt-1 opacity-80">{result.failure_reason}</p>
              )}
              <div className="text-xs mt-1 opacity-70">
                Confidence: {(result.confidence_score * 100).toFixed(1)}%
                {result.metadata?.processing_time_ms && 
                  ` • ${result.metadata.processing_time_ms.toFixed(1)}ms`
                }
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  const renderLLMJudgeResults = (results: any) => {
    if (!results) return null

    return (
      <div className="mt-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
        <h4 className="text-sm font-semibold text-purple-900 mb-3 flex items-center">
          <Brain className="h-4 w-4 mr-2" />
          LLM Judge Analysis
        </h4>
        <div className="space-y-3">
          {results.quality_score && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-purple-800">Quality Score:</span>
              <div className="flex items-center space-x-2">
                <div className="w-20 bg-purple-200 rounded-full h-2">
                  <div 
                    className="bg-purple-600 h-2 rounded-full" 
                    style={{ width: `${results.quality_score}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-purple-900">
                  {results.quality_score}%
                </span>
              </div>
            </div>
          )}
          {results.reasoning && (
            <div>
              <span className="text-sm font-medium text-purple-800">Reasoning:</span>
              <p className="text-sm text-purple-700 mt-1">{results.reasoning}</p>
            </div>
          )}
          {results.suggested_improvements && (
            <div>
              <span className="text-sm font-medium text-purple-800">Suggestions:</span>
              <ul className="text-sm text-purple-700 mt-1 space-y-1">
                {results.suggested_improvements.map((suggestion: string, idx: number) => (
                  <li key={idx} className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>{suggestion}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">API Testing Interface</h3>
            <p className="mt-1 text-sm text-gray-600">
              Test API endpoints with custom LLM prompts, constraints, and red-team scenarios
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Categories</option>
              <option value="system">System</option>
              <option value="ingestion">Ingestion</option>
              <option value="analysis">Analysis</option>
              <option value="advanced">Advanced</option>
              <option value="management">Management</option>
            </select>
            <button
              onClick={() => setShowLlmConfig(!showLlmConfig)}
              className={`px-3 py-2 text-sm rounded-md border transition-colors ${
                showLlmConfig 
                  ? 'bg-purple-50 border-purple-200 text-purple-700' 
                  : 'bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100'
              }`}
            >
              <Brain className="h-4 w-4 mr-2 inline" />
              LLM Config
            </button>
            <button
              onClick={() => setShowRedTeam(!showRedTeam)}
              className={`px-3 py-2 text-sm rounded-md border transition-colors ${
                showRedTeam 
                  ? 'bg-red-50 border-red-200 text-red-700' 
                  : 'bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100'
              }`}
            >
              <Shield className="h-4 w-4 mr-2 inline" />
              Red Team
            </button>
          </div>
        </div>

        {/* LLM Configuration Panel */}
        {showLlmConfig && (
          <div className="mb-6 p-4 bg-purple-50 border border-purple-200 rounded-lg">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-md font-semibold text-purple-900">LLM Judge Configuration</h4>
              <button
                onClick={resetLlmConfig}
                className="px-3 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
              >
                <RotateCcw className="h-3 w-3 mr-1 inline" />
                Reset to Default
              </button>
            </div>
            
            <div className="space-y-4">
              {/* Custom Prompt */}
              <div>
                <label className="block text-sm font-medium text-purple-800 mb-2">
                  Custom LLM Prompt
                  <span className="text-purple-600 text-xs ml-2">
                    Use {`{{content}}, {{tags}}, {{source}}, {{context}}`} as placeholders
                  </span>
                </label>
                <textarea
                  value={llmPrompt}
                  onChange={(e) => setLlmPrompt(e.target.value)}
                  rows={8}
                  className="w-full px-3 py-2 border border-purple-300 rounded-md text-gray-900 text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  placeholder="Enter your custom LLM prompt..."
                />
              </div>

              {/* Quality Constraints */}
              <div>
                <label className="block text-sm font-medium text-purple-800 mb-3">
                  Quality Constraints & Weights
                </label>
                <div className="space-y-3">
                  {constraints.map((constraint) => (
                    <div key={constraint.id} className="flex items-center space-x-4 p-3 bg-white border border-purple-200 rounded">
                      <input
                        type="checkbox"
                        checked={constraint.enabled}
                        onChange={(e) => updateConstraint(constraint.id, { enabled: e.target.checked })}
                        className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                      />
                      <div className="flex-1">
                        <div className="text-sm font-medium text-gray-900">{constraint.name}</div>
                        <div className="text-xs text-gray-600">{constraint.description}</div>
                        <div className="text-xs text-purple-700 mt-1">{constraint.rule}</div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs text-gray-600">Weight:</span>
                        <input
                          type="number"
                          value={constraint.weight}
                          onChange={(e) => updateConstraint(constraint.id, { weight: parseFloat(e.target.value) || 0 })}
                          min="0"
                          max="1"
                          step="0.05"
                          className="w-16 px-2 py-1 text-xs border border-gray-300 rounded focus:ring-purple-500 focus:border-purple-500"
                          disabled={!constraint.enabled}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Red Team Panel */}
        {showRedTeam && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <h4 className="text-md font-semibold text-red-900 mb-4">Red Team Testing Scenarios</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {redTeamScenarios.map((scenario) => (
                <button
                  key={scenario.id}
                  onClick={() => loadRedTeamScenario(scenario)}
                  className={`text-left p-3 border rounded-md transition-colors ${
                    selectedRedTeamScenario?.id === scenario.id
                      ? 'border-red-500 bg-red-100 text-red-900'
                      : 'border-red-200 text-red-800 hover:bg-red-100'
                  }`}
                >
                  <div className="font-medium text-sm">{scenario.name}</div>
                  <div className="text-xs mt-1 opacity-80">{scenario.description}</div>
                  <div className="text-xs mt-2">
                    <span className="font-medium">Expected Issues:</span>
                    <div className="mt-1 space-y-1">
                      {scenario.expectedIssues.map((issue, idx) => (
                        <div key={idx} className="flex items-start">
                          <span className="mr-1">•</span>
                          <span>{issue}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Configuration */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Panel - Endpoint Selection */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">API Base URL</label>
              <input
                type="text"
                value={apiBaseUrl}
                onChange={(e) => setApiBaseUrl(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder={process.env.NEXT_PUBLIC_API_URL || '/api'}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Endpoint</label>
              <div className="space-y-2">
                {filteredEndpoints.map((endpoint) => (
                  <button
                    key={endpoint.id}
                    onClick={() => setSelectedEndpoint(endpoint)}
                    className={`w-full text-left p-3 border rounded-md transition-colors ${
                      selectedEndpoint.id === endpoint.id
                        ? 'border-blue-500 bg-blue-50 text-blue-900'
                        : 'border-gray-200 text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        {getCategoryIcon(endpoint.category)}
                        <span className="font-medium">{endpoint.name}</span>
                        <span className={`px-2 py-1 text-xs rounded font-medium ${
                          endpoint.method === 'GET' ? 'bg-green-100 text-green-800' :
                          endpoint.method === 'POST' ? 'bg-blue-100 text-blue-800' :
                          endpoint.method === 'PUT' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {endpoint.method}
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{endpoint.description}</p>
                    <p className="text-xs text-gray-500 mt-1 font-mono">{endpoint.path}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Right Panel - Request Configuration */}
          <div className="space-y-4">
            {/* Sample Payloads */}
            {selectedEndpoint.method === 'POST' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Quick Samples</label>
                <div className="flex space-x-2">
                  <button
                    onClick={() => loadSamplePayload('minimal')}
                    className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                  >
                    Minimal
                  </button>
                  <button
                    onClick={() => loadSamplePayload('complex')}
                    className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                  >
                    Complex
                  </button>
                  <button
                    onClick={() => loadSamplePayload('problematic')}
                    className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                  >
                    Problematic
                  </button>
                </div>
              </div>
            )}

            {/* Headers */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Headers (JSON)</label>
              <textarea
                value={customHeaders}
                onChange={(e) => setCustomHeaders(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder='{"Content-Type": "application/json"}'
              />
            </div>

            {/* Payload */}
            {['POST', 'PUT'].includes(selectedEndpoint.method) && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Request Payload (JSON)</label>
                <textarea
                  value={customPayload}
                  onChange={(e) => setCustomPayload(e.target.value)}
                  rows={12}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter JSON payload..."
                />
              </div>
            )}

            {/* Execute Button */}
            <button
              onClick={executeTest}
              disabled={isLoading}
              className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Testing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Execute Test
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      {(result || error) && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-lg font-semibold text-gray-900">Test Results</h4>
            {result && (
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => copyToClipboard(JSON.stringify(result, null, 2))}
                  className="p-2 text-gray-500 hover:text-gray-700 rounded"
                  title="Copy response"
                >
                  <Copy className="h-4 w-4" />
                </button>
                <button
                  onClick={downloadResponse}
                  className="p-2 text-gray-500 hover:text-gray-700 rounded"
                  title="Download response"
                >
                  <Download className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>

          {error ? (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center space-x-2">
                <XCircle className="h-5 w-5 text-red-500" />
                <span className="text-sm font-medium text-red-800">Request Failed</span>
              </div>
              <p className="text-sm text-red-700 mt-2">{error}</p>
            </div>
          ) : result ? (
            <div className="space-y-4">
              {/* Status and Timing */}
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  {getStatusIcon(result.status)}
                  <span className="text-sm font-medium text-gray-900">
                    {result.status} {result.statusText}
                  </span>
                </div>
                <div className="flex items-center space-x-4 text-sm text-gray-600">
                  <span className="flex items-center">
                    <Clock className="h-4 w-4 mr-1" />
                    {formatDuration(result.duration)}
                  </span>
                  <span>{new Date(result.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>

              {/* Red Team Analysis */}
              {selectedRedTeamScenario && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <h5 className="text-sm font-semibold text-red-900 mb-2 flex items-center">
                    <Shield className="h-4 w-4 mr-2" />
                    Red Team Analysis: {selectedRedTeamScenario.name}
                  </h5>
                  <div className="text-sm text-red-800">
                    <p className="mb-2"><strong>Expected Issues:</strong></p>
                    <ul className="space-y-1">
                      {selectedRedTeamScenario.expectedIssues.map((issue, idx) => (
                        <li key={idx} className="flex items-start">
                          <span className="mr-2">•</span>
                          <span>{issue}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Rules Engine Results */}
              {result.rulesEngineResults && renderRulesEngineResults(result.rulesEngineResults)}

              {/* LLM Judge Results */}
              {result.llmJudgeResults && renderLLMJudgeResults(result.llmJudgeResults)}

              {/* Raw Response */}
              <div>
                <h5 className="text-sm font-medium text-gray-900 mb-2">Response Data</h5>
                <pre className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-800 overflow-auto max-h-96">
                  {JSON.stringify(result.data, null, 2)}
                </pre>
              </div>

              {/* Headers */}
              {Object.keys(result.headers).length > 0 && (
                <div>
                  <h5 className="text-sm font-medium text-gray-900 mb-2">Response Headers</h5>
                  <pre className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-800 overflow-auto">
                    {JSON.stringify(result.headers, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}

      {/* Test History */}
      {testHistory.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">Recent Tests</h4>
          <div className="space-y-2">
            {testHistory.map((test, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded border">
                <div className="flex items-center space-x-3">
                  {getStatusIcon(test.status)}
                  <span className="text-sm font-medium text-gray-900">
                    {testEndpoints.find(ep => test.data?.endpoint === ep.id)?.name || 'Unknown'}
                  </span>
                  <span className="text-xs text-gray-500">
                    {new Date(test.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <span>{test.status}</span>
                  <span>•</span>
                  <span>{formatDuration(test.duration)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
} 