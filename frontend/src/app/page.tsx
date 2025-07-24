'use client'

import { useState, useEffect } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import DashboardMetrics from '@/components/dashboard/DashboardMetrics'
import QualityRecordsTable from '@/components/table/QualityRecordsTable'
import RecordDetailModal from '@/components/modals/RecordDetailModal'
import { apiClient } from '@/app/api'
import { Upload, RefreshCw, AlertCircle, CheckCircle, FileText, Zap, Plus, Download, Filter, ChevronLeft, ChevronRight } from 'lucide-react'

export default function DashboardPage() {
  const [syncStatus, setSyncStatus] = useState<'idle' | 'uploading' | 'processing' | 'completed' | 'error'>('idle')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null)
  const [backendStatus, setBackendStatus] = useState<'online' | 'offline' | 'checking'>('checking')
  
  // Records state with pagination
  const [approvedRecords, setApprovedRecords] = useState<any[]>([])
  const [reviewQueue, setReviewQueue] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedRecord, setSelectedRecord] = useState<any | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Pagination state for approved records
  const [approvedPage, setApprovedPage] = useState(1)
  const [approvedPageSize, setApprovedPageSize] = useState(10)
  const [approvedPagination, setApprovedPagination] = useState({
    total: 0,
    totalPages: 0,
    page: 1,
    pageSize: 10
  })

  // Pagination state for review queue
  const [reviewPage, setReviewPage] = useState(1)
  const [reviewPageSize, setReviewPageSize] = useState(10)
  const [reviewPagination, setReviewPagination] = useState({
    total: 0,
    totalPages: 0,
    page: 1,
    pageSize: 10
  })

  useEffect(() => {
    checkBackendStatus()
    fetchApprovedRecords()
    fetchReviewQueue()
    const interval = setInterval(checkBackendStatus, 30000) // Check every 30 seconds
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    fetchApprovedRecords()
  }, [approvedPage, approvedPageSize])

  useEffect(() => {
    fetchReviewQueue()
  }, [reviewPage, reviewPageSize])

  const checkBackendStatus = async () => {
    try {
      await apiClient.getHealth()
      setBackendStatus('online')
    } catch (error) {
      setBackendStatus('offline')
    }
  }

  const fetchApprovedRecords = async () => {
    setLoading(true)
    try {
      const filters = { statuses: ['approved'] }
      const pagination = {
        page: approvedPage,
        pageSize: approvedPageSize,
        sortBy: 'createdAt',
        sortOrder: 'desc' as const
      }
      const response = await apiClient.getQualityRecords(filters, pagination)
      setApprovedRecords(response.data || [])
      setApprovedPagination(response.pagination || {
        total: 0,
        totalPages: 0,
        page: approvedPage,
        pageSize: approvedPageSize
      })
    } catch (err) {
      console.error('Error fetching approved records:', err)
      setApprovedRecords([])
    } finally {
      setLoading(false)
    }
  }

  const fetchReviewQueue = async () => {
    setLoading(true)
    try {
      const filters = { statuses: ['flagged', 'under_review'] }
      const pagination = {
        page: reviewPage,
        pageSize: reviewPageSize,
        sortBy: 'createdAt',
        sortOrder: 'desc' as const
      }
      const response = await apiClient.getQualityRecords(filters, pagination)
      setReviewQueue(response.data || [])
      setReviewPagination(response.pagination || {
        total: 0,
        totalPages: 0,
        page: reviewPage,
        pageSize: reviewPageSize
      })
    } catch (err) {
      console.error('Error fetching review queue:', err)
      setReviewQueue([])
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setSyncStatus('uploading')
    setUploadProgress(0)

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90))
      }, 200)

      const result = await apiClient.uploadFile(file)
      
      clearInterval(progressInterval)
      setUploadProgress(100)
      setSyncStatus('completed')
      setLastSyncTime(new Date().toLocaleString())
      
      // Refresh records after upload
      fetchApprovedRecords()
      fetchReviewQueue()
      
      setTimeout(() => setSyncStatus('idle'), 3000)
    } catch (error) {
      setSyncStatus('error')
      console.error('Upload failed:', error)
      setTimeout(() => setSyncStatus('idle'), 3000)
    }
  }

  const handleBatchSync = async () => {
    setSyncStatus('processing')
    try {
      // Example batch sync
      const sampleBatch = {
        chunks: [
          {
            record_id: `sync-${Date.now()}-1`,
            document_text: "Sample document from sync process",
            tags: ["sync", "automated"],
            source_connector: "SharePoint" as const,
            file_id: `file-${Date.now()}`
          }
        ],
        batch_metadata: {
          sync_type: "manual",
          initiated_by: "dashboard",
          timestamp: new Date().toISOString()
        }
      }
      
      await apiClient.syncBatch(sampleBatch)
      setSyncStatus('completed')
      setLastSyncTime(new Date().toLocaleString())
      
      // Refresh records after sync
      fetchApprovedRecords()
      fetchReviewQueue()
      
      setTimeout(() => setSyncStatus('idle'), 3000)
    } catch (error) {
      setSyncStatus('error')
      setTimeout(() => setSyncStatus('idle'), 3000)
    }
  }

  const handleRecordClick = (record: any) => {
    setSelectedRecord(record)
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedRecord(null)
  }

  const handleUpdateRecord = (updatedRecord: any) => {
    // Update the record in both lists if it exists
    setApprovedRecords(prevRecords => 
      prevRecords.map(record => 
        record.id === updatedRecord.id ? updatedRecord : record
      )
    )
    setReviewQueue(prevRecords => 
      prevRecords.map(record => 
        record.id === updatedRecord.id ? updatedRecord : record
      )
    )
    
    if (selectedRecord && selectedRecord.id === updatedRecord.id) {
      setSelectedRecord(updatedRecord)
    }
  }

  const handleRecordUpdated = () => {
    fetchApprovedRecords()
    fetchReviewQueue()
  }

  // Pagination component
  const PaginationControls = ({ 
    pagination, 
    onPageChange, 
    onPageSizeChange 
  }: { 
    pagination: any, 
    onPageChange: (page: number) => void,
    onPageSizeChange: (size: number) => void
  }) => (
    <div className="flex items-center justify-between mt-4 px-4 py-3 bg-gray-50 border-t border-gray-200">
      <div className="flex items-center space-x-2">
        <span className="text-sm text-gray-700">
          Page {pagination.page} of {pagination.totalPages} ({pagination.total} total)
        </span>
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={() => onPageChange(Math.max(1, pagination.page - 1))}
          disabled={pagination.page === 1}
          className="px-3 py-1 border border-gray-300 rounded-md bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-sm text-gray-600">
          {pagination.page}
        </span>
        <button
          onClick={() => onPageChange(Math.min(pagination.totalPages, pagination.page + 1))}
          disabled={pagination.page >= pagination.totalPages}
          className="px-3 py-1 border border-gray-300 rounded-md bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <select
          value={pagination.pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="border border-gray-300 rounded-md px-2 py-1 text-sm bg-white"
        >
          <option value={5}>5</option>
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
        </select>
      </div>
    </div>
  )

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Quality Control Dashboard</h1>
            <p className="mt-1 text-sm text-gray-500">
              Monitor content quality and manage records pipeline
            </p>
          </div>
          <div className="mt-4 sm:mt-0 flex items-center space-x-3">
            {/* Backend Status */}
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${
                backendStatus === 'online' ? 'bg-green-500' : 
                backendStatus === 'offline' ? 'bg-red-500' : 'bg-yellow-500'
              }`}></div>
              <span className="text-sm text-gray-600">
                Backend {backendStatus === 'checking' ? 'Checking...' : backendStatus}
              </span>
            </div>
            
            {/* Action Buttons */}
            <button
              onClick={() => {
                fetchApprovedRecords()
                fetchReviewQueue()
              }}
              disabled={loading}
              className="px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 mr-1 inline ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={() => console.log('Export all')}
              className="px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
            >
              <Download className="h-4 w-4 mr-1 inline" />
              Export All
            </button>
          </div>
        </div>

        {/* Dashboard Metrics */}
        <DashboardMetrics />

        {/* Sync Controls */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-medium text-gray-900 flex items-center">
                <Zap className="h-5 w-5 mr-2 text-blue-600" />
                Data Sync & Upload
              </h3>
              <p className="text-sm text-gray-500">
                Upload files or sync data batches for quality analysis
              </p>
            </div>
            {lastSyncTime && (
              <div className="text-sm text-gray-500">
                Last sync: {lastSyncTime}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* File Upload */}
            <div className="border border-gray-200 rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-2 flex items-center">
                <Upload className="h-4 w-4 mr-2" />
                File Upload
              </h4>
              <p className="text-sm text-gray-500 mb-3">
                Upload JSON files containing content chunks
              </p>
              
              <label className="block">
                <input
                  type="file"
                  accept=".json"
                  onChange={handleFileUpload}
                  disabled={syncStatus !== 'idle'}
                  className="block w-full text-sm text-gray-500
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-md file:border-0
                    file:text-sm file:font-medium
                    file:bg-blue-50 file:text-blue-700
                    hover:file:bg-blue-100
                    disabled:opacity-50"
                />
              </label>

              {syncStatus !== 'idle' && (
                <div className="mt-3">
                  <div className="flex items-center space-x-2">
                    {syncStatus === 'uploading' && <Upload className="h-4 w-4 text-blue-600 animate-pulse" />}
                    {syncStatus === 'completed' && <CheckCircle className="h-4 w-4 text-green-600" />}
                    {syncStatus === 'error' && <AlertCircle className="h-4 w-4 text-red-600" />}
                    <span className="text-sm">
                      {syncStatus === 'uploading' && `Uploading... ${uploadProgress}%`}
                      {syncStatus === 'completed' && 'Upload completed!'}
                      {syncStatus === 'error' && 'Upload failed'}
                    </span>
                  </div>
                  {syncStatus === 'uploading' && (
                    <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all"
                        style={{ width: `${uploadProgress}%` }}
                      ></div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Batch Sync */}
            <div className="border border-gray-200 rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-2 flex items-center">
                <RefreshCw className="h-4 w-4 mr-2" />
                Batch Sync
              </h4>
              <p className="text-sm text-gray-500 mb-3">
                Manually trigger a batch sync process
              </p>
              
              <button
                onClick={handleBatchSync}
                disabled={syncStatus !== 'idle' || backendStatus !== 'online'}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {syncStatus === 'processing' ? 'Syncing...' : 'Start Batch Sync'}
              </button>

              {syncStatus === 'processing' && (
                <div className="mt-3 flex items-center space-x-2">
                  <RefreshCw className="h-4 w-4 text-blue-600 animate-spin" />
                  <span className="text-sm text-blue-600">Processing batch...</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Review Queue Table */}
        <div className="mt-8">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">🚨 Review Queue ({reviewPagination.total})</h2>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-500">
                  {loading ? 'Loading...' : `${reviewQueue.length} of ${reviewPagination.total} flagged records`}
                </span>
              </div>
            </div>
            <QualityRecordsTable
              data={reviewQueue}
              loading={loading}
              onRecordClick={handleRecordClick}
              onRecordUpdated={handleRecordUpdated}
            />
            <PaginationControls
              pagination={reviewPagination}
              onPageChange={(page) => setReviewPage(page)}
              onPageSizeChange={(size) => {
                setReviewPageSize(size)
                setReviewPage(1)
              }}
            />
          </div>
        </div>

        {/* Approved Records Table */}
        <div className="mt-8">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">✅ Approved Records ({approvedPagination.total})</h2>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-500">
                  {loading ? 'Loading...' : `${approvedRecords.length} of ${approvedPagination.total} records`}
                </span>
              </div>
            </div>
            <QualityRecordsTable
              data={approvedRecords}
              loading={loading}
              onRecordClick={handleRecordClick}
              onRecordUpdated={handleRecordUpdated}
            />
            <PaginationControls
              pagination={approvedPagination}
              onPageChange={(page) => setApprovedPage(page)}
              onPageSizeChange={(size) => {
                setApprovedPageSize(size)
                setApprovedPage(1)
              }}
            />
          </div>
        </div>

        {/* Record Detail Modal */}
        <RecordDetailModal
          record={selectedRecord}
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          onUpdate={handleUpdateRecord}
          onRecordUpdated={handleRecordUpdated}
        />
      </div>
    </DashboardLayout>
  )
}
