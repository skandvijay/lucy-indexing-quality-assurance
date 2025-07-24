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
  X,
  Calendar,
  Server,
  FileText,
  Activity
} from 'lucide-react'
import { apiClient } from '@/app/api'
import DashboardLayout from '@/components/layout/DashboardLayout'

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

const StatusBadge: React.FC<{ status: string; size?: 'sm' | 'md' }> = ({ status, size = 'md' }) => {
  const baseClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
  const statusConfig = {
    resolved: 'bg-green-50 text-green-700 border-green-200',
    unresolved: 'bg-red-50 text-red-700 border-red-200',
    retrying: 'bg-amber-50 text-amber-700 border-amber-200',
    failed: 'bg-red-50 text-red-700 border-red-200'
  }
  
  return (
    <span className={`inline-flex items-center rounded-full border font-medium ${baseClasses} ${statusConfig[status as keyof typeof statusConfig] || 'bg-gray-50 text-gray-700 border-gray-200'}`}>
      {status.toUpperCase()}
    </span>
  )
}

const MetricCard: React.FC<{ label: string; value: React.ReactNode; icon?: React.ReactNode; color?: string }> = ({ 
  label, 
  value, 
  icon, 
  color = 'gray' 
}) => (
  <div className="bg-white border border-gray-100 rounded-xl p-4">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-gray-600 font-medium">{label}</p>
        <div className={`text-2xl font-semibold text-${color}-900 mt-1`}>{value}</div>
      </div>
      {icon && <div className={`text-${color}-500`}>{icon}</div>}
    </div>
  </div>
)

const DeadLetterDetailModal: React.FC<{
  record: DeadLetterRecord | null
  isOpen: boolean
  onClose: () => void
  onRetry: (id: string) => void
  onResolve: (id: string) => void
  onDelete: (id: string) => void
}> = ({ record, isOpen, onClose, onRetry, onResolve, onDelete }) => {
  if (!isOpen || !record) return null

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-100 px-8 py-6 flex items-center justify-between bg-gradient-to-r from-gray-50 to-white">
          <div className="flex items-center space-x-4">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Dead Letter Record</h2>
              <p className="text-sm text-gray-500">Trace ID: {record.trace_id}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <StatusBadge status={record.resolved ? 'resolved' : 'unresolved'} />
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
              <X className="h-5 w-5 text-gray-400" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8 bg-gray-50">
          <div className="space-y-8">
            {/* Summary Cards */}
            <div className="grid grid-cols-3 gap-4">
              <MetricCard 
                label="Error Type" 
                value={record.error_type}
                icon={<AlertCircle className="h-5 w-5" />}
                color="red"
              />
              <MetricCard 
                label="Source Connector" 
                value={record.source_connector}
                icon={<Server className="h-5 w-5" />}
                color="blue"
              />
              <MetricCard 
                label="Retry Count" 
                value={record.retry_count}
                icon={<RefreshCw className="h-5 w-5" />}
                color="amber"
              />
            </div>

            {/* Details */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white border border-gray-100 rounded-xl p-6">
                <h4 className="font-semibold text-gray-900 mb-4">Record Information</h4>
                <div className="space-y-3">
                  {[
                    { label: 'Record ID', value: record.id },
                    { label: 'Trace ID', value: record.trace_id },
                    { label: 'Failed At', value: formatDate(record.failed_at || record.created_at) },
                    { label: 'Last Retry', value: formatDate(record.last_retry_at) },
                    { label: 'Resolved At', value: formatDate(record.resolved_at) }
                  ].map(({ label, value }) => (
                    <div key={label} className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">{label}</span>
                      <span className="text-sm font-medium text-gray-900 font-mono">{value}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white border border-gray-100 rounded-xl p-6">
                <h4 className="font-semibold text-gray-900 mb-4">Error Details</h4>
                <div className="space-y-3">
                  <div>
                    <span className="text-sm text-gray-600">Error Message</span>
                    <div className="mt-1 p-3 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-800">{record.error_message}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Raw Input Data */}
            <div className="bg-white border border-gray-100 rounded-xl p-6">
              <h4 className="font-semibold text-gray-900 mb-4">Raw Input Data</h4>
              <div className="bg-gray-50 p-4 rounded-lg">
                <pre className="text-sm text-gray-900 whitespace-pre-wrap font-mono overflow-x-auto max-h-64">
                  {record.raw_input ? JSON.stringify(record.raw_input, null, 2) : 'No raw input data available'}
                </pre>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="border-t border-gray-100 px-8 py-4 flex items-center justify-between bg-white">
          <div className="flex items-center space-x-6 text-sm text-gray-500">
            <span className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span>Failed: {formatDate(record.failed_at)}</span>
            </span>
            <span>Retries: {record.retry_count}</span>
          </div>
          <div className="flex items-center space-x-3">
            {!record.resolved && (
              <>
                <button
                  onClick={() => onRetry(record.id)}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  <span>Retry</span>
                </button>
                <button
                  onClick={() => onResolve(record.id)}
                  className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center space-x-2"
                >
                  <CheckCircle className="h-4 w-4" />
                  <span>Resolve</span>
                </button>
              </>
            )}
            <button
              onClick={() => onDelete(record.id)}
              className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center space-x-2"
            >
              <Trash2 className="h-4 w-4" />
              <span>Delete</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function DeadLettersPage() {
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
  const [filterOptions, setFilterOptions] = useState<{
    error_types: Array<{value: string, label: string, count: number}>
    source_connectors: Array<{value: string, label: string, count: number}>
    time_periods: Array<{value: number, label: string}>
  }>({
    error_types: [],
    source_connectors: [],
    time_periods: []
  })
  const [filtersLoading, setFiltersLoading] = useState(true)

  // Fetch filter options
  const fetchFilterOptions = async () => {
    try {
      setFiltersLoading(true)
      const options = await apiClient.getDeadLettersFilterOptions()
      setFilterOptions(options)
    } catch (error) {
      console.error('Error fetching filter options:', error)
    } finally {
      setFiltersLoading(false)
    }
  }

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
      setRecords(Array.isArray(data) ? data : [])
    } catch (error) {
      console.error('Error fetching dead letters:', error)
      setRecords([])
    } finally {
      setLoading(false)
    }
  }

  // Fetch statistics
  const fetchStats = async () => {
    try {
      const data = await apiClient.getDeadLettersStats(filters.hours_back)
      setStats(data)
    } catch (error) {
      console.error('Error fetching stats:', error)
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

  // Action handlers
  const handleRetry = async (id: string) => {
    try {
      await apiClient.retryDeadLetter(id)
      fetchDeadLetters()
      fetchStats()
      setShowDetailModal(false)
    } catch (error) {
      console.error('Error retrying dead letter:', error)
    }
  }

  const handleResolve = async (id: string) => {
    try {
      await apiClient.resolveDeadLetter(id)
      fetchDeadLetters()
      fetchStats()
      setShowDetailModal(false)
    } catch (error) {
      console.error('Error resolving dead letter:', error)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await apiClient.deleteDeadLetter(id)
      fetchDeadLetters()
      fetchStats()
      setShowDetailModal(false)
    } catch (error) {
      console.error('Error deleting dead letter:', error)
    }
  }

  const viewDetails = (record: DeadLetterRecord) => {
    setSelectedRecord(record)
    setShowDetailModal(true)
  }

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString()
  }

  const getErrorTypeColor = (errorType: string) => {
    const colors = {
      'schema_validation_error': 'bg-red-100 text-red-800',
      'SCHEMA_VALIDATION_ERROR': 'bg-red-100 text-red-800'
    }
    return colors[errorType as keyof typeof colors] || 'bg-gray-100 text-gray-800'
  }

  const getSourceConnectorColor = (connector: string) => {
    const colors = {
      'SharePoint': 'bg-blue-100 text-blue-800',
      'Confluence': 'bg-green-100 text-green-800',
      'Notion': 'bg-purple-100 text-purple-800',
      'GDrive': 'bg-yellow-100 text-yellow-800',
      'Elasticsearch': 'bg-orange-100 text-orange-800'
    }
    return colors[connector as keyof typeof colors] || 'bg-gray-100 text-gray-800'
  }

  useEffect(() => {
    fetchDeadLetters()
    fetchStats()
    fetchFilterOptions()
  }, [filters])

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dead Letters</h1>
            <p className="text-gray-600 mt-1">Schema validation failures requiring attention</p>
            <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <span className="font-medium">Note:</span> Dead Letters now only capture schema validation errors. 
                General processing errors are logged separately and do not appear here.
              </p>
            </div>
          </div>
          <button 
            onClick={() => {
              fetchDeadLetters()
              fetchStats()
              fetchFilterOptions()
            }}
            className="flex items-center px-4 py-2 bg-white border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </button>
        </div>

        {/* Statistics Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <MetricCard 
              label="Total Records" 
              value={stats.total_count}
              icon={<Database className="h-5 w-5" />}
              color="blue"
            />
            <MetricCard 
              label="Unresolved" 
              value={stats.unresolved_count || records.filter(r => !r.resolved).length}
              icon={<AlertCircle className="h-5 w-5" />}
              color="red"
            />
            <MetricCard 
              label="Resolved" 
              value={stats.resolved_count || records.filter(r => r.resolved).length}
              icon={<CheckCircle className="h-5 w-5" />}
              color="green"
            />
            <MetricCard 
              label="Success Rate" 
              value={`${stats.total_count > 0 ? Math.round(((stats.resolved_count || 0) / stats.total_count) * 100) : 0}%`}
              icon={<TrendingUp className="h-5 w-5" />}
              color="purple"
            />
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-xl border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
            <div className="flex items-center space-x-2">
              {filtersLoading && <RefreshCw className="h-4 w-4 animate-spin text-gray-400" />}
              <button
                onClick={fetchFilterOptions}
                className="p-1 hover:bg-gray-100 rounded-full transition-colors"
                title="Refresh filter options"
              >
                <RefreshCw className="h-4 w-4 text-gray-400" />
              </button>
              <Filter className="h-5 w-5 text-gray-400" />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Error Type</label>
              <select
                value={filters.error_type}
                onChange={(e) => setFilters({...filters, error_type: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={filtersLoading}
              >
                <option value="">All Types</option>
                {filterOptions.error_types.map((errorType) => (
                  <option key={errorType.value} value={errorType.value}>
                    {errorType.label} ({errorType.count})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Source Connector</label>
              <select
                value={filters.source_connector}
                onChange={(e) => setFilters({...filters, source_connector: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={filtersLoading}
              >
                <option value="">All Sources</option>
                {filterOptions.source_connectors.map((connector) => (
                  <option key={connector.value} value={connector.value}>
                    {connector.label} ({connector.count})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Time Period</label>
              <select
                value={filters.hours_back}
                onChange={(e) => setFilters({...filters, hours_back: parseInt(e.target.value)})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={filtersLoading}
              >
                {filterOptions.time_periods.map((period) => (
                  <option key={period.value} value={period.value}>
                    {period.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Records Table */}
        <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900">Dead Letter Records</h3>
          </div>
          
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
              <span className="ml-2 text-gray-600">Loading records...</span>
            </div>
          ) : records.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900">No Dead Letters</h3>
              <p className="text-gray-600">All records are processing successfully!</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trace ID</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Error Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Failed At</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Retries</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {records.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => viewDetails(record)}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                        {record.trace_id.substring(0, 8)}...
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getErrorTypeColor(record.error_type)}`}>
                          {record.error_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getSourceConnectorColor(record.source_connector)}`}>
                          {record.source_connector}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatDate(record.failed_at || record.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
                          {record.retry_count}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <StatusBadge status={record.resolved ? 'resolved' : 'unresolved'} size="sm" />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            viewDetails(record)
                          }}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Detail Modal */}
        <DeadLetterDetailModal
          record={selectedRecord}
          isOpen={showDetailModal}
          onClose={() => setShowDetailModal(false)}
          onRetry={handleRetry}
          onResolve={handleResolve}
          onDelete={handleDelete}
        />
      </div>
    </DashboardLayout>
  )
} 