"use client"

import React, { useState, useEffect } from 'react';
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
} from 'lucide-react';
import { apiClient } from '@/app/api';

interface DeadLetterRecord {
  id: string;
  trace_id: string;
  raw_input?: Record<string, any>;
  error_message: string;
  error_type: string;
  source_connector: string;
  created_at?: string;
  failed_at?: string;
  retry_count: number;
  last_retry_at?: string;
  resolved_at?: string;
  resolved?: boolean;
}

interface DeadLetterStats {
  total_count: number;
  unresolved_count: number;
  resolved_count: number;
  error_types: Record<string, number>;
  source_connectors: Record<string, number>;
  recent_trend: Array<{ hour: string; count: number }>;
  analysis_period_hours: number;
}

interface DeadLettersProps {
  className?: string;
}

const DeadLetters: React.FC<DeadLettersProps> = ({ className }) => {
  const [records, setRecords] = useState<DeadLetterRecord[]>([]);
  const [stats, setStats] = useState<DeadLetterStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedRecord, setSelectedRecord] = useState<DeadLetterRecord | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [filters, setFilters] = useState({
    error_type: '',
    source_connector: '',
    hours_back: 24
  });

  // Fetch dead letters
  const fetchDeadLetters = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getDeadLetters({
        skip: 0,
        limit: 50,
        hours_back: filters.hours_back,
        error_type: filters.error_type || undefined,
        source_connector: filters.source_connector || undefined
      });
      setRecords(data || []);
    } catch (error) {
      console.error('Error fetching dead letters:', error);
      setRecords([]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch statistics
  const fetchStats = async () => {
    try {
      const data = await apiClient.getDeadLettersStats(filters.hours_back);
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
      // Set default stats if the endpoint is not available
      setStats({
        total_count: records.length,
        unresolved_count: records.filter(r => !(r.resolved_at || r.resolved)).length,
        resolved_count: records.filter(r => r.resolved_at || r.resolved).length,
        error_types: {},
        source_connectors: {},
        recent_trend: [],
        analysis_period_hours: filters.hours_back
      });
    }
  };

  // Retry a dead letter
  const retryDeadLetter = async (id: string) => {
    try {
      await apiClient.retryDeadLetter(id);
      alert('Dead letter retry initiated');
      fetchDeadLetters();
      fetchStats();
    } catch (error) {
      console.error('Error retrying dead letter:', error);
      alert('Failed to retry dead letter');
    }
  };

  // Resolve a dead letter
  const resolveDeadLetter = async (id: string) => {
    try {
      await apiClient.resolveDeadLetter(id);
      alert('Dead letter marked as resolved');
      fetchDeadLetters();
      fetchStats();
    } catch (error) {
      console.error('Error resolving dead letter:', error);
      alert('Failed to resolve dead letter');
    }
  };

  // Delete a dead letter
  const deleteDeadLetter = async (id: string) => {
    try {
      await apiClient.deleteDeadLetter(id);
      alert('Dead letter deleted');
      fetchDeadLetters();
      fetchStats();
    } catch (error) {
      console.error('Error deleting dead letter:', error);
      alert('Failed to delete dead letter');
    }
  };

  // View details of a dead letter
  const viewDetails = (record: DeadLetterRecord) => {
    setSelectedRecord(record);
    setShowDetailModal(true);
  };

  // Format date
  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  // Get error type color - only schema validation errors now
  const getErrorTypeColor = (errorType: string) => {
    switch (errorType) {
      case 'schema_validation_error':
        return 'bg-red-100 text-red-800';
      case 'SCHEMA_VALIDATION_ERROR':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Get source connector color
  const getSourceConnectorColor = (connector: string) => {
    const colors = {
      'SharePoint': 'bg-blue-100 text-blue-800',
      'Confluence': 'bg-green-100 text-green-800',
      'Notion': 'bg-purple-100 text-purple-800',
      'GDrive': 'bg-yellow-100 text-yellow-800',
      'Elasticsearch': 'bg-orange-100 text-orange-800',
      'Custom': 'bg-gray-100 text-gray-800',
      'Unknown': 'bg-red-100 text-red-800'
    };
    return colors[connector as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  useEffect(() => {
    fetchDeadLetters();
    fetchStats();
  }, [filters]);

  return (
    <div className={`p-6 space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Dead Letters</h2>
        <button 
          onClick={() => {
            fetchDeadLetters();
            fetchStats();
          }}
          className="flex items-center px-4 py-2 bg-white border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Database className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Total Records</dt>
                    <dd className="text-lg font-medium text-gray-900">{stats.total_count}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <AlertCircle className="h-6 w-6 text-red-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Unresolved</dt>
                    <dd className="text-lg font-medium text-red-600">{stats.unresolved_count}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <CheckCircle className="h-6 w-6 text-green-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Resolved</dt>
                    <dd className="text-lg font-medium text-green-600">{stats.resolved_count}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <TrendingUp className="h-6 w-6 text-blue-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Recent Trend</dt>
                    <dd className="text-lg font-medium text-blue-600">
                      {stats.recent_trend.length > 0 ? 
                        stats.recent_trend[stats.recent_trend.length - 1].count : 0}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex items-center mb-4">
            <Filter className="h-5 w-5 text-gray-400 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">Filters</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Error Type</label>
              <select
                value={filters.error_type}
                onChange={(e) => setFilters(prev => ({ ...prev, error_type: e.target.value }))}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              >
                <option value="">All error types</option>
                {stats && Object.keys(stats.error_types).map(type => (
                  <option key={type} value={type}>
                    {type} ({stats.error_types[type]})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Source Connector</label>
              <select
                value={filters.source_connector}
                onChange={(e) => setFilters(prev => ({ ...prev, source_connector: e.target.value }))}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              >
                <option value="">All connectors</option>
                {stats && Object.keys(stats.source_connectors).map(connector => (
                  <option key={connector} value={connector}>
                    {connector} ({stats.source_connectors[connector]})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Time Range</label>
              <select
                value={filters.hours_back}
                onChange={(e) => setFilters(prev => ({ ...prev, hours_back: parseInt(e.target.value) }))}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              >
                <option value={1}>Last 1 hour</option>
                <option value={6}>Last 6 hours</option>
                <option value={24}>Last 24 hours</option>
                <option value={168}>Last 7 days</option>
                <option value={720}>Last 30 days</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Dead Letter Records Table */}
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
                      Trace ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Error Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Source
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Retries
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {records.map((record) => (
                    <tr 
                      key={record.id} 
                      className="hover:bg-gray-50 cursor-pointer transition-colors"
                      onClick={() => viewDetails(record)}
                    >
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
                         {formatDate(record.created_at || record.failed_at)}
                       </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
                          {record.retry_count}
                        </span>
                      </td>
                                             <td className="px-6 py-4 whitespace-nowrap">
                         {record.resolved_at || record.resolved ? (
                           <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                             Resolved
                           </span>
                         ) : (
                           <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                             Unresolved
                           </span>
                         )}
                       </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div className="flex space-x-2" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => viewDetails(record)}
                            className="text-blue-600 hover:text-blue-900"
                            title="View Details"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          
                                                     {!(record.resolved_at || record.resolved) && (
                            <>
                              <button
                                onClick={() => retryDeadLetter(record.id)}
                                className="text-green-600 hover:text-green-900"
                                title="Retry"
                              >
                                <RefreshCw className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => resolveDeadLetter(record.id)}
                                className="text-yellow-600 hover:text-yellow-900"
                                title="Mark as Resolved"
                              >
                                <CheckCircle className="w-4 h-4" />
                              </button>
                            </>
                          )}
                          
                          <button
                            onClick={() => deleteDeadLetter(record.id)}
                            className="text-red-600 hover:text-red-900"
                            title="Delete"
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

      {/* Modal for viewing record details */}
      {showModal && selectedRecord && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium text-gray-900">Dead Letter Details</h3>
                <button
                  onClick={() => setShowModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ×
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Trace ID</label>
                  <input
                    type="text"
                    value={selectedRecord.trace_id}
                    readOnly
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-sm"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Error Message</label>
                  <textarea
                    value={selectedRecord.error_message}
                    readOnly
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-sm"
                  />
                </div>
                
                                 <div>
                   <label className="block text-sm font-medium text-gray-700 mb-1">Raw Input</label>
                   <textarea
                     value={selectedRecord.raw_input ? JSON.stringify(selectedRecord.raw_input, null, 2) : 'No raw input data available'}
                     readOnly
                     rows={10}
                     className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-sm font-mono"
                   />
                 </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Detailed Record Modal */}
      {showDetailModal && selectedRecord && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium text-gray-900">Dead Letter Record Details</h3>
                <button
                  onClick={() => setShowDetailModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>
            
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Basic Information */}
                <div className="space-y-4">
                  <h4 className="text-md font-semibold text-gray-900 border-b pb-2">Basic Information</h4>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Record ID</label>
                    <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded font-mono">{selectedRecord.id}</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Trace ID</label>
                    <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded font-mono">{selectedRecord.trace_id}</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Error Type</label>
                    <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getErrorTypeColor(selectedRecord.error_type)}`}>
                      {selectedRecord.error_type}
                    </span>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Source Connector</label>
                    <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getSourceConnectorColor(selectedRecord.source_connector)}`}>
                      {selectedRecord.source_connector}
                    </span>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Created At</label>
                    <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{formatDate(selectedRecord.created_at || selectedRecord.failed_at)}</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Retry Count</label>
                    <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{selectedRecord.retry_count}</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                    {selectedRecord.resolved_at || selectedRecord.resolved ? (
                      <span className="inline-flex px-3 py-1 text-sm font-semibold rounded-full bg-green-100 text-green-800">
                        Resolved
                      </span>
                    ) : (
                      <span className="inline-flex px-3 py-1 text-sm font-semibold rounded-full bg-red-100 text-red-800">
                        Unresolved
                      </span>
                    )}
                  </div>
                </div>
                
                {/* Error Details */}
                <div className="space-y-4">
                  <h4 className="text-md font-semibold text-gray-900 border-b pb-2">Error Details</h4>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Error Message</label>
                    <textarea
                      value={selectedRecord.error_message}
                      readOnly
                      rows={4}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-sm"
                    />
                  </div>
                  
                  {selectedRecord.last_retry_at && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Last Retry At</label>
                      <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{formatDate(selectedRecord.last_retry_at)}</p>
                    </div>
                  )}
                  
                  {selectedRecord.resolved_at && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Resolved At</label>
                      <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{formatDate(selectedRecord.resolved_at)}</p>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Raw Input Data */}
              <div className="mt-6">
                <h4 className="text-md font-semibold text-gray-900 border-b pb-2 mb-4">Raw Input Data</h4>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <pre className="text-sm text-gray-900 whitespace-pre-wrap font-mono overflow-x-auto">
                    {selectedRecord.raw_input ? JSON.stringify(selectedRecord.raw_input, null, 2) : 'No raw input data available'}
                  </pre>
                </div>
              </div>
              
              {/* Actions */}
              <div className="mt-6 flex justify-end space-x-3">
                {!(selectedRecord.resolved_at || selectedRecord.resolved) && (
                  <>
                    <button
                      onClick={() => {
                        retryDeadLetter(selectedRecord.id);
                        setShowDetailModal(false);
                      }}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Retry
                    </button>
                    
                    <button
                      onClick={() => {
                        resolveDeadLetter(selectedRecord.id);
                        setShowDetailModal(false);
                      }}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                    >
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Resolve
                    </button>
                  </>
                )}
                
                <button
                  onClick={() => {
                    deleteDeadLetter(selectedRecord.id);
                    setShowDetailModal(false);
                  }}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete
                </button>
                
                <button
                  onClick={() => setShowDetailModal(false)}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DeadLetters; 