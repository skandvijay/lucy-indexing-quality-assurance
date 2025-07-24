'use client'

import React, { useState, useEffect } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { 
  Server, 
  CheckCircle, 
  XCircle, 
  Clock, 
  Zap, 
  Brain, 
  Shield, 
  Database, 
  Mail, 
  TestTube, 
  TrendingUp, 
  Activity, 
  AlertCircle, 
  FileCode, 
  Upload, 
  Eye, 
  Target, 
  MessageSquare, 
  Building, 
  Plug, 
  Bell, 
  Download, 
  Play,
  RefreshCw,
  Settings,
  AlertTriangle,
  FileText,
  Cpu,
  Rocket,
  Wrench,
  Bug,
  BarChart3,
  Plus
} from 'lucide-react'
import { apiClient } from '@/app/api'

interface TestResult {
  name: string
  status: 'success' | 'error'
  result?: any
  error?: string
  duration: number
  timestamp: string
}

export default function BackendTestPage() {
  const [backendStatus, setBackendStatus] = useState<'online' | 'offline' | 'checking'>('checking')
  const [testResults, setTestResults] = useState<TestResult[]>([])
  const [isTesting, setIsTesting] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  useEffect(() => {
    checkBackendStatus()
  }, [])

  const checkBackendStatus = async () => {
    setBackendStatus('checking')
    try {
      await apiClient.health()
      setBackendStatus('online')
    } catch (error) {
      setBackendStatus('offline')
    }
  }

  const runBackendTest = async (testName: string, testFunction: () => Promise<any>) => {
    setIsTesting(true)
    const startTime = Date.now()
    
    try {
      const result = await testFunction()
      const endTime = Date.now()
      
      setTestResults(prev => [{
        name: testName,
        status: 'success',
        result,
        duration: endTime - startTime,
        timestamp: new Date().toISOString()
      }, ...prev.slice(0, 19)]) // Keep last 20 results
    } catch (error) {
      const endTime = Date.now()
      setTestResults(prev => [{
        name: testName,
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
        duration: endTime - startTime,
        timestamp: new Date().toISOString()
      }, ...prev.slice(0, 19)])
    } finally {
      setIsTesting(false)
    }
  }

  // ================================
  // WORKING ENDPOINT TESTS (✅ Verified)
  // ================================
  
  // Core System Tests
  const testHealth = () => runBackendTest('Health Check', () => apiClient.getHealth())
  const testStats = () => runBackendTest('System Stats', () => apiClient.getStats())
  const testSelfTest = () => runBackendTest('Self Test', () => apiClient.selfTest())

  // Data Retrieval Tests
  const testRecords = () => runBackendTest('Get Records', () => apiClient.getRecords())
  const testAnalytics = () => runBackendTest('Dashboard Analytics', () => apiClient.getDashboardAnalytics())
  const testIssues = () => runBackendTest('Get Issues', () => apiClient.getIssues())
  const testDeadLetters = () => runBackendTest('Get Dead Letters', () => apiClient.getDeadLetters())
  const testCompanies = () => runBackendTest('Get Companies', () => apiClient.getCompanies())
  const testConnectors = () => runBackendTest('Get Connectors', () => apiClient.getConnectors())

  // Analysis Tests
  const testContentIngestion = async () => {
    const testContent = {
      record_id: "test-001",
      content: "This is a comprehensive guide about machine learning algorithms and their applications in data science. The document covers various topics including supervised learning, unsupervised learning, and deep learning techniques.",
      tags: ["machine learning", "algorithms", "data science", "AI"],
      source_connector: "SharePoint",
      content_metadata: {
        author: "Test User",
        department: "Engineering"
      }
    }
    
    await runBackendTest('Content Ingestion', () => apiClient.ingestContent(testContent))
  }

  const testRulesCheck = async () => {
    const testRules = {
      document_text: "API documentation for user authentication service. Handles login, registration, password reset, and session management.",
      tags: ["api", "authentication", "security", "documentation"],
      source_connector: "SharePoint"
    }
    
    await runBackendTest('Rules Check', () => apiClient.checkRules(testRules))
  }

  const testLLMAnalysis = async () => {
    const testLLM = {
      content: "Marketing strategy for Q1 2024 focusing on digital transformation initiatives and customer acquisition.",
      tags: ["marketing", "strategy", "digital-transformation"],
      context: {
        source: "strategy-docs",
        department: "Marketing"
      }
    }
    
    await runBackendTest('LLM Analysis', () => apiClient.analyzeLLM(testLLM))
  }

  const testRedTeam = async () => {
    const testRedTeam = {
      scenario_id: "generic_tags",
      content: "Test content with generic tags",
      tags: ["generic", "document", "test"],
      test_objectives: ["Detect generic tags", "Flag low-quality content"],
      expected_issues: ["generic_tags", "low_quality"]
    }
    
    await runBackendTest('Red Team Analysis', () => apiClient.redTeamAnalysis(testRedTeam))
  }

  // ================================
  // COMMENTED OUT - TESTS FOR NON-EXISTENT ENDPOINTS
  // ================================
  
  /*
  // These tests call endpoints that don't exist in the backend
  // Commenting them out to avoid 404 errors and confusion
  
  const testRequestLogs = () => runBackendTest('Get Request Logs', () => apiClient.getRequestLogs())
  const testRequestAnalytics = () => runBackendTest('Request Analytics', () => apiClient.getRequestAnalytics())
  const testEvaluationMetrics = () => runBackendTest('Evaluation Metrics', () => apiClient.getEvaluationMetrics())
  const testRedTeamResults = () => runBackendTest('Red Team Results', () => apiClient.getRedTeamResults())
  const testAlertEmails = () => runBackendTest('Alert Emails', () => apiClient.getAlertEmails())
  const testAlertTemplate = () => runBackendTest('Alert Template', () => apiClient.getAlertTemplate())
  const testAddAlertEmail = () => runBackendTest('Add Alert Email', () => apiClient.addAlertEmail('test@example.com'))
  const testExportRecords = () => runBackendTest('Export Records', () => apiClient.exportRecords('json'))
  
  const testChainOfThought = async () => {
    const testCOT = {
      content: "AI implementation plan for customer support automation using NLP and machine learning.",
      tags: ["ai", "nlp", "automation", "customer-support"],
      custom_prompt: "Analyze this plan step by step for feasibility and implementation challenges.",
      constraints: [],
      quality_weights: {}
    }
    
    await runBackendTest('Chain of Thought Analysis', () => apiClient.chainOfThoughtAnalysis(testCOT))
  }
  */

  const testCategories = [
    {
      id: 'core',
      name: 'Core System',
      icon: Server,
      color: 'text-blue-600',
      tests: [
        { name: 'Health Check', icon: CheckCircle, test: testHealth },
        { name: 'System Stats', icon: BarChart3, test: testStats },
        { name: 'Self Test', icon: TestTube, test: testSelfTest }
      ]
    },
    {
      id: 'essential',
      name: 'Essential Data',
      icon: Database,
      color: 'text-green-600',
      tests: [
        { name: 'Get Records', icon: FileText, test: testRecords },
        { name: 'Dashboard Analytics', icon: TrendingUp, test: testAnalytics },
        { name: 'Get Issues', icon: AlertCircle, test: testIssues },
        { name: 'Get Companies', icon: Building, test: testCompanies },
        { name: 'Get Connectors', icon: Plug, test: testConnectors }
      ]
    },
    {
      id: 'quality',
      name: 'Quality Processing',
      icon: Cpu,
      color: 'text-purple-600',
      tests: [
        { name: 'Content Ingestion', icon: Upload, test: testContentIngestion },
        { name: 'Rules Check', icon: Shield, test: testRulesCheck },
        { name: 'LLM Analysis', icon: Brain, test: testLLMAnalysis }
      ]
    }
  ]

  const filteredCategories = selectedCategory === 'all' 
    ? testCategories 
    : testCategories.filter(cat => cat.id === selectedCategory)

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Backend Testing Interface</h1>
              <p className="mt-1 text-sm text-gray-600">
                Test all backend endpoints and functionality with real data
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={checkBackendStatus}
                className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  backendStatus === 'online' ? 'bg-green-100 text-green-700' :
                  backendStatus === 'offline' ? 'bg-red-100 text-red-700' :
                  'bg-yellow-100 text-yellow-700'
                }`}
              >
                <div className={`w-2 h-2 rounded-full mr-2 ${
                  backendStatus === 'online' ? 'bg-green-500' :
                  backendStatus === 'offline' ? 'bg-red-500' :
                  'bg-yellow-500'
                }`} />
                {backendStatus}
                <RefreshCw className="h-4 w-4 ml-2" />
              </button>
              
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">All Categories</option>
                {testCategories.map(category => (
                  <option key={category.id} value={category.id}>{category.name}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Test Categories */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {filteredCategories.map(category => (
            <div key={category.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center mb-4">
                <category.icon className={`h-6 w-6 ${category.color} mr-3`} />
                <h3 className="text-lg font-semibold text-gray-900">{category.name}</h3>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {category.tests.map((test, index) => (
                  <button
                    key={index}
                    onClick={test.test}
                    disabled={isTesting || backendStatus !== 'online'}
                    className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <test.icon className="h-4 w-4 text-gray-600 mr-2" />
                    <span className="text-sm font-medium text-gray-900">{test.name}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Test Results */}
        {testResults.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Test Results</h3>
              <button
                onClick={() => setTestResults([])}
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                Clear Results
              </button>
            </div>
            
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {testResults.map((result, index) => (
                <div
                  key={index}
                  className={`flex items-center justify-between p-3 rounded-lg border ${
                    result.status === 'success' 
                      ? 'bg-green-50 border-green-200' 
                      : 'bg-red-50 border-red-200'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    {result.status === 'success' ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-600" />
                    )}
                    <div>
                      <span className="font-medium text-gray-900">{result.name}</span>
                      {result.error && (
                        <p className="text-sm text-red-600 mt-1">{result.error}</p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4 text-sm text-gray-600">
                    <div className="flex items-center space-x-1">
                      <Clock className="h-3 w-3" />
                      <span>{result.duration}ms</span>
                    </div>
                    <span>•</span>
                    <span>{new Date(result.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <button
              onClick={() => {
                testHealth()
                testStats()
                testRecords()
              }}
              disabled={isTesting || backendStatus !== 'online'}
              className="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              <Server className="h-6 w-6 text-blue-600 mb-2" />
              <span className="text-sm font-medium">System Check</span>
            </button>
            
            <button
              onClick={() => {
                testContentIngestion()
                testRulesCheck()
                testLLMAnalysis()
              }}
              disabled={isTesting || backendStatus !== 'online'}
              className="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              <Cpu className="h-6 w-6 text-purple-600 mb-2" />
              <span className="text-sm font-medium">Processing Test</span>
            </button>
            
            <button
              onClick={() => {
                testAnalytics()
                testIssues()
                // testRequestAnalytics() // This test is commented out
              }}
              disabled={isTesting || backendStatus !== 'online'}
              className="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              <BarChart3 className="h-6 w-6 text-green-600 mb-2" />
              <span className="text-sm font-medium">Analytics Test</span>
            </button>
            
            <button
              onClick={() => {
                // testAlertEmails() // This test is commented out
                // testAlertTemplate() // This test is commented out
                // testTestAlert() // This test is commented out
              }}
              disabled={isTesting || backendStatus !== 'online'}
              className="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              <Mail className="h-6 w-6 text-orange-600 mb-2" />
              <span className="text-sm font-medium">Alert Test</span>
            </button>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
} 