'use client'

import React, { useState, useEffect } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Clock, 
  Zap,
  RefreshCw,
  Play,
  Filter,
  Search,
  Download,
  MoreVertical,
  Eye,
  Edit,
  Trash2,
  Settings,
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  Users,
  Database,
  Bell,
  Shield,
  AlertCircle,
  Info,
  Wrench,
  Sparkles
} from 'lucide-react'
import { QualityIssue } from '@/types'
import { apiClient } from '@/app/api';

interface IssueWithRecord {
  id: string
  type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  suggestion?: string
  autoFixable: boolean
  category: 'content' | 'tags' | 'metadata' | 'compliance' | 'llm'
  confidence?: number
  record: {
    id: string
    recordId: string
    companyName: string
    status: string
    priority: string
    createdAt: string
  }
}

export default function IssuesPage() {
  const [reviewQueue, setReviewQueue] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null)
  const [selectedIssues, setSelectedIssues] = useState<string[]>([])
  const [filters, setFilters] = useState({
    severity: 'all',
    category: 'all',
    autoFixable: 'all',
    company: 'all'
  })
  const [searchQuery, setSearchQuery] = useState('')
  const [autoFixing, setAutoFixing] = useState<string[]>([])
  const [issues, setIssues] = useState<QualityIssue[]>([])

  const fetchIssues = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Use the correct issues endpoint
      const response = await apiClient.getIssues()
      
      // Extract issues array from the response object
      const issuesArray = response?.issues || []
      setIssues(issuesArray)
    } catch (err) {
      console.error('Failed to fetch issues:', err)
      setError('Failed to load issues')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setLoading(true);
    fetchIssues();
  }, []);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchIssues, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleAutoFix = async (issueId: string) => {
    try {
      setAutoFixing(prev => [...prev, issueId])
      
      const response = await apiClient.autoFixIssue(issueId) as any
      
      if (response?.success) {
        // Refresh issues to get updated data
        await fetchIssues()
        
        // Also refresh records to show updated status
        // Note: This would need to be passed down from parent or use a global state management
        // For now, we'll just refresh the issues
        
        // Show success notification
        // You can implement a toast notification system here
        console.log('Auto-fix applied successfully:', response.message)
      }
    } catch (err) {
      console.error('Auto-fix failed:', err)
      // Show error notification
    } finally {
      setAutoFixing(prev => prev.filter(id => id !== issueId))
    }
  }

  const handleBulkAutoFix = async () => {
    const autoFixableIssues = selectedIssues.filter(issueId => {
      const issue = issues.find(i => i.id === issueId)
      return issue?.autoFixable
    })

    if (autoFixableIssues.length === 0) {
      alert('No auto-fixable issues selected')
      return
    }

    try {
      setAutoFixing(autoFixableIssues)
      
      // Apply auto-fix to all selected issues
      const promises = autoFixableIssues.map(issueId => apiClient.autoFixIssue(issueId))
      await Promise.all(promises)
      
      // Refresh issues
      await fetchIssues()
      
      // Also refresh records to show updated status
      // Note: This would need to be passed down from parent or use a global state management
      // For now, we'll just refresh the issues
      
      setSelectedIssues([])
      
      console.log(`Auto-fix applied to ${autoFixableIssues.length} issues`)
    } catch (err) {
      console.error('Bulk auto-fix failed:', err)
    } finally {
      setAutoFixing([])
    }
  }

  const filteredIssues = issues.filter(issue => {
    // Search filter
    if (searchQuery && !issue.description.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false
    }
    
    // Severity filter
    if (filters.severity !== 'all' && issue.severity !== filters.severity) {
      return false
    }
    
    // Category filter
    if (filters.category !== 'all' && issue.category !== filters.category) {
      return false
    }
    
    // Auto-fixable filter
    if (filters.autoFixable !== 'all') {
      const isAutoFixable = filters.autoFixable === 'true'
      if (issue.autoFixable !== isAutoFixable) {
        return false
      }
    }
    
    // Company filter
    if (filters.company !== 'all' && issue.record.companyName !== filters.company) {
      return false
    }
    
    return true
  })

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800'
      case 'high': return 'bg-orange-100 text-orange-800'
      case 'medium': return 'bg-yellow-100 text-yellow-800'
      case 'low': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'content': return <Edit className="h-4 w-4" />
      case 'tags': return <Target className="h-4 w-4" />
      case 'metadata': return <Database className="h-4 w-4" />
      case 'compliance': return <Shield className="h-4 w-4" />
      default: return <AlertCircle className="h-4 w-4" />
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center space-x-2">
            <RefreshCw className="h-5 w-5 animate-spin text-blue-600" />
            <span className="text-gray-600">Loading issues...</span>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Failed to load issues</h3>
            <p className="text-gray-600 mb-4">{error}</p>
            <button
              onClick={fetchIssues}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Try Again
            </button>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Quality Issues</h1>
            <p className="mt-1 text-sm text-gray-500">
              Monitor and resolve quality issues across all content sources
            </p>
          </div>
          <div className="mt-4 sm:mt-0 flex items-center space-x-3">
            <button
              onClick={fetchIssues}
              className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 flex items-center space-x-2"
            >
              <RefreshCw className="h-4 w-4" />
              <span>Refresh</span>
            </button>
            {selectedIssues.length > 0 && (
              <button
                onClick={handleBulkAutoFix}
                disabled={autoFixing.length > 0}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
              >
                <Sparkles className="h-4 w-4" />
                <span>Auto-fix Selected ({selectedIssues.length})</span>
              </button>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search issues..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Severity</label>
              <select
                value={filters.severity}
                onChange={(e) => setFilters(prev => ({ ...prev, severity: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select
                value={filters.category}
                onChange={(e) => setFilters(prev => ({ ...prev, category: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">All Categories</option>
                <option value="content">Content</option>
                <option value="tags">Tags</option>
                <option value="metadata">Metadata</option>
                <option value="compliance">Compliance</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Auto-fixable</label>
              <select
                value={filters.autoFixable}
                onChange={(e) => setFilters(prev => ({ ...prev, autoFixable: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">All Issues</option>
                <option value="true">Auto-fixable</option>
                <option value="false">Manual Only</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
              <select
                value={filters.company}
                onChange={(e) => setFilters(prev => ({ ...prev, company: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">All Companies</option>
                {Array.from(new Set(issues.map(issue => issue.record.companyName))).map(company => (
                  <option key={company} value={company}>{company}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Issues List */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">
                Issues ({filteredIssues.length})
              </h3>
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <span>{issues.filter(i => i.autoFixable).length} auto-fixable</span>
                <span>•</span>
                <span>{issues.filter(i => i.severity === 'critical').length} critical</span>
              </div>
            </div>
          </div>
          
          <div className="divide-y divide-gray-200">
            {filteredIssues.length === 0 ? (
              <div className="px-6 py-12 text-center">
                <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No issues found</h3>
                <p className="text-gray-500">All quality checks are passing!</p>
              </div>
            ) : (
              filteredIssues.map((issue) => (
                <div key={issue.id} className="px-6 py-4 hover:bg-gray-50">
                  <div className="flex items-start space-x-4">
                    <div className="flex-shrink-0">
                      <input
                        type="checkbox"
                        checked={selectedIssues.includes(issue.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedIssues(prev => [...prev, issue.id])
                          } else {
                            setSelectedIssues(prev => prev.filter(id => id !== issue.id))
                          }
                        }}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          {getCategoryIcon(issue.category)}
                          <div>
                            <h4 className="text-sm font-medium text-gray-900">
                              {issue.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </h4>
                            <p className="text-sm text-gray-500">{issue.description}</p>
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(issue.severity)}`}>
                            {issue.severity.toUpperCase()}
                          </span>
                          
                          {issue.autoFixable && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              <Sparkles className="h-3 w-3 mr-1" />
                              Auto-fixable
                            </span>
                          )}
                        </div>
                      </div>
                      
                      <div className="mt-2 flex items-center justify-between">
                        <div className="flex items-center space-x-4 text-sm text-gray-500">
                          <span>Company: {issue.record.companyName}</span>
                          <span>Record: {issue.record.recordId}</span>
                          <span>Created: {new Date(issue.record.createdAt).toLocaleDateString()}</span>
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          {issue.suggestion && (
                            <span className="text-sm text-blue-600">{issue.suggestion}</span>
                          )}
                          
                          {issue.autoFixable && (
                            <button
                              onClick={() => handleAutoFix(issue.id)}
                              disabled={autoFixing.includes(issue.id)}
                              className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 disabled:opacity-50 flex items-center space-x-1"
                            >
                              {autoFixing.includes(issue.id) ? (
                                <RefreshCw className="h-3 w-3 animate-spin" />
                              ) : (
                                <Sparkles className="h-3 w-3" />
                              )}
                              <span>Auto-fix</span>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
} 