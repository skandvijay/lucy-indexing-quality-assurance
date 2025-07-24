'use client'

import React, { useState, useEffect } from 'react'
import { 
  AlertCircle, 
  RefreshCw, 
  CheckCircle, 
  Trash2, 
  Eye,
  Database,
  TrendingUp,
  Filter,
  X
} from 'lucide-react'
import { apiClient } from '@/app/api'

interface DeadLetterRecord {
  id: string
  trace_id: string
  raw_input?: Record<string, any>
  error_message: string
  error_type: string
  source_connector: string
  created_at?: string
  failed_at?: string
  retry_count: number
  last_retry_at?: string
  resolved_at?: string
  resolved?: boolean
}

interface DeadLetterStats {
  total_count: number
  unresolved_count: number
  resolved_count: number
  error_types: Record<string, number>
  source_connectors: Record<string, number>
  recent_trend: Array<{ hour: string; count: number }>
  analysis_period_hours: number
}

interface DeadLettersProps {
  className?: string
}

const DeadLetters: React.FC<DeadLettersProps> = ({ className }) => {
  const [records, setRecords] = useState<DeadLetterRecord[]>([])
  const [stats, setStats] = useState<DeadLetterStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedRecord, setSelectedRecord] = useState<DeadLetterRecord | null>(null)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [filters, setFilters] = useState({
    error_type: '',
    source_connector: '',
    hours_back: 24
  })

  // Fetch dead letters
  const fetchDeadLetters = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getDeadLetters({
        skip: 0,
        limit: 50,
        hours_back: filters.hours_back,
        error_type: filters.error_type || undefined,
        source_connector: filters.source_connector || undefined
      })
      setRecords(data || [])
    } catch (error) {
      console.error('Error fetching dead letters:', error)
      setRecords([])
    } finally {
      setLoading(false)
    }
  }

  // Fetch statistics with fallback
  const fetchStats = async () => {
    try {
      const data = await apiClient.getDeadLettersStats(filters.hours_back)
      setStats(data)
    } catch (error) {
      console.error('Error fetching stats:', error)
      // Set default stats if the endpoint is not available
      setStats({
        total_count: records.length,
        unresolved_count: records.filter(r => !(r.resolved_at || r.resolved)).length,
        resolved_count: records.filter(r => r.resolved_at || r.resolved).length,
        error_types: {},
        source_connectors: {},
        recent_trend: [],
        analysis_period_hours: filters.hours_back
      })
    }
  }

  // Retry a dead letter
  const retryDeadLetter = async (id: string) => {
    try {
      await apiClient.retryDeadLetter(id)
      alert('Dead letter retry initiated')
      fetchDeadLetters()
      fetchStats()
    } catch (error) {
      console.error('Error retrying dead letter:', error)
      alert('Failed to retry dead letter')
    }
  }

  // Resolve a dead letter
  const resolveDeadLetter = async (id: string) => {
    try {
      await apiClient.resolveDeadLetter(id)
      alert('Dead letter marked as resolved')
      fetchDeadLetters()
      fetchStats()
    } catch (error) {
      console.error('Error resolving dead letter:', error)
      alert('Failed to resolve dead letter')
    }
  }

  // Delete a dead letter
  const deleteDeadLetter = async (id: string) => {
    try {
      await apiClient.deleteDeadLetter(id)
      alert('Dead letter deleted')
      fetchDeadLetters()
      fetchStats()
    } catch (error) {
      console.error('Error deleting dead letter:', error)
      alert('Failed to delete dead letter')
    }
  }

  // View details of a dead letter
  const viewDetails = (record: DeadLetterRecord) => {
    setSelectedRecord(record)
    setShowDetailModal(true)
  }

  // Format date
  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  // Get error type color - only schema validation errors now
  const getErrorTypeColor = (errorType: string) => {
    switch (errorType) {
      case 'schema_validation_error':
        return 'bg-red-100 text-red-800'
      case 'SCHEMA_VALIDATION_ERROR':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  useEffect(() => {
    fetchDeadLetters()
    fetchStats()
  }, [filters])

  return (
    <div className={`p-6 space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center">
          <Database className="h-6 w-6 mr-2 text-blue-600" />
          Dead Letters
        </h2>
        <button 
          onClick={() => {
            fetchDeadLetters()
            fetchStats()
          }}
          className="flex items-center px-4 py-2 bg-white border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-6 rounded-lg shadow border">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <AlertCircle className="h-8 w-8 text-red-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Dead Letters</dt>
                  <dd className="text-lg font-medium text-gray-900">{stats.total_count}</dd>
                </dl>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow border">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <TrendingUp className="h-8 w-8 text-yellow-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Unresolved</dt>
                  <dd className="text-lg font-medium text-gray-900">{stats.unresolved_count}</dd>
                </dl>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow border">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <CheckCircle className="h-8 w-8 text-green-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Resolved</dt>
                  <dd className="text-lg font-medium text-gray-900">{stats.resolved_count}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow border">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Error Type</label>
            <select
              value={filters.error_type}
              onChange={(e) => setFilters(prev => ({ ...prev, error_type: e.target.value }))}
              className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Types</option>
              <option value="SCHEMA_VALIDATION_ERROR">Schema Validation</option>
              <option value="PROCESSING_ERROR">Processing Error</option>
              <option value="TIMEOUT_ERROR">Timeout Error</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Source Connector</label>
            <select
              value={filters.source_connector}
              onChange={(e) => setFilters(prev => ({ ...prev, source_connector: e.target.value }))}
              className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Sources</option>
              <option value="SharePoint">SharePoint</option>
              <option value="Confluence">Confluence</option>
              <option value="Notion">Notion</option>
              <option value="GDrive">GDrive</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Time Range (hours)</label>
            <select
              value={filters.hours_back}
              onChange={(e) => setFilters(prev => ({ ...prev, hours_back: parseInt(e.target.value) }))}
              className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
            >
              <option value={1}>Last Hour</option>
              <option value={24}>Last 24 Hours</option>
              <option value={168}>Last Week</option>
              <option value={720}>Last Month</option>
            </select>
          </div>
        </div>
      </div>

      {/* Dead Letters Table */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Dead Letter Records</h3>
          
          {loading ? (
            <div className="flex justify-center items-center h-32">
              <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : records.length === 0 ? (
            <div className="text-center py-8">
              <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No dead letters found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Error
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Source
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Retries
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {records.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex flex-col">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getErrorTypeColor(record.error_type)}`}>
                            {record.error_type}
                          </span>
                          <span className="text-sm text-gray-500 mt-1 truncate max-w-xs">
                            {record.error_message}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {record.source_connector}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {record.retry_count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(record.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex space-x-2">
                          <button
                            onClick={() => viewDetails(record)}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => retryDeadLetter(record.id)}
                            className="text-green-600 hover:text-green-900"
                          >
                            <RefreshCw className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => resolveDeadLetter(record.id)}
                            className="text-yellow-600 hover:text-yellow-900"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => deleteDeadLetter(record.id)}
                            className="text-red-600 hover:text-red-900"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Detail Modal */}
      {showDetailModal && selectedRecord && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-md bg-white">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">Dead Letter Details</h3>
              <button
                onClick={() => setShowDetailModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Trace ID</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedRecord.trace_id}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Error Message</label>
                <p className="mt-1 text-sm text-gray-900">{selectedRecord.error_message}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Raw Input</label>
                <pre className="mt-1 text-xs text-gray-900 bg-gray-100 p-3 rounded overflow-auto max-h-64">
                  {JSON.stringify(selectedRecord.raw_input || {}, null, 2)}
                </pre>
              </div>
            </div>
            
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowDetailModal(false)}
                className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DeadLetters 