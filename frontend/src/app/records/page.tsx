'use client'

import React, { useState, useEffect } from 'react';
import { useDashboardContext } from '@/lib/DashboardContext';
import { apiClient } from '@/app/api';
import QualityRecordsTable from '@/components/table/QualityRecordsTable';
import DashboardLayout from '@/components/layout/DashboardLayout';
import RecordDetailModal from '@/components/modals/RecordDetailModal';
import AdvancedFilters from '@/components/filters/AdvancedFilters';
import { DashboardFilters, PaginationParams } from '@/types';

export default function RecordsPage() {
  const { state, actions } = useDashboardContext();
  const { filters } = state;
  const { setFilters } = actions;
  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [pagination, setPagination] = useState({
    total: 0,
    totalPages: 0,
    page: 1,
    pageSize: 25,
    hasNext: false,
    hasPrev: false
  });
  const [overrideModal, setOverrideModal] = useState<{ open: boolean, record: any } | null>(null);
  const [overrideReason, setOverrideReason] = useState('');
  const [isOverriding, setIsOverriding] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<any | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  // Approve flagged record
  const [isApproving, setIsApproving] = useState(false);
  const [approveModal, setApproveModal] = useState<{ open: boolean, record: any } | null>(null);
  const [approveError, setApproveError] = useState('');

  useEffect(() => {
    fetchAllRecords();
  }, [page, pageSize, filters]);

  const fetchAllRecords = async () => {
    setLoading(true);
    try {
      // Use getQualityRecords to fetch with filters and pagination
      const paginationParams: PaginationParams = {
        page,
        pageSize,
        sortBy: 'createdAt',
        sortOrder: 'desc',
      };
      const response = await apiClient.getQualityRecords(filters, paginationParams);
      let all = response.data || [];
      setRecords(all);
      
      // Update pagination metadata
      setPagination(response.pagination || {
        total: 0,
        totalPages: 0,
        page,
        pageSize,
        hasNext: false,
        hasPrev: false
      });
    } catch (err) {
      console.error('Error fetching records:', err);
      setRecords([]);
      setPagination({
        total: 0,
        totalPages: 0,
        page,
        pageSize,
        hasNext: false,
        hasPrev: false
      });
    } finally {
      setLoading(false);
    }
  };

  const handleFiltersChange = (newFilters: Partial<DashboardFilters>) => {
    setFilters(newFilters);
    setPage(1); // Reset to first page on filter change
  };

  const handleFiltersReset = () => {
    setFilters({});
    setPage(1);
  };

  const handleOverride = (record: any) => {
    setOverrideModal({ open: true, record });
    setOverrideReason('');
  };

  const handleOverrideSubmit = async () => {
    if (!overrideModal?.record || !overrideReason.trim()) return;
    
    setIsOverriding(true);
    try {
      await apiClient.overrideApprovedRecord(
        overrideModal.record.id, 
        'user-123', // Replace with actual user ID
        overrideReason
      );
      
      // Refresh records after override
      await fetchAllRecords();
      setOverrideModal(null);
      setOverrideReason('');
    } catch (error) {
      console.error('Error overriding record:', error);
      alert('Failed to override record. Please try again.');
    } finally {
      setIsOverriding(false);
    }
  };

  const handleRecordClick = (record: any) => {
    setSelectedRecord(record);
    setIsDetailOpen(true);
  };

  const handleDetailClose = () => {
    setIsDetailOpen(false);
    setSelectedRecord(null);
  };

  // Approve flagged record with confirmation dialog
  const handleBulkAction = async (action: string, recordIds: string[]) => {
    if (action === 'approve' && recordIds.length > 0) {
      const record = records.find(r => r.id === recordIds[0]);
      setApproveModal({ open: true, record });
    }
  };
  const handleApproveConfirm = async () => {
    if (!approveModal?.record) return;
    setIsApproving(true);
    setApproveError('');
    try {
      await apiClient.approveFlaggedRecord(approveModal.record.id, 'user-123');
      await fetchAllRecords();
      setApproveModal(null);
    } catch (err) {
      setApproveError('Failed to approve record.');
    } finally {
      setIsApproving(false);
    }
  };
  const handleApproveCancel = () => {
    setApproveModal(null);
    setApproveError('');
  };

  // Map all non-approved statuses to 'flagged' for display
  const mappedRecords = records.map(r => ({
    ...r,
    status: r.status === 'approved' ? 'approved' : 'flagged'
  }));

  return (
    <DashboardLayout>
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Advanced Filters */}
        <AdvancedFilters
          filters={filters}
          onFiltersChange={setFilters}
          onReset={() => setFilters({})}
        />
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 mt-4">
          <h1 className="text-2xl font-bold text-gray-900">Quality Records</h1>
        </div>
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <QualityRecordsTable
            data={mappedRecords}
            loading={loading || isApproving}
            onRecordClick={handleRecordClick}
            onRecordUpdated={fetchAllRecords}
            selectedRecords={[]}
            onSelectionChange={() => {}}
          />
        </div>
        
        {/* Override Modal */}
        {overrideModal?.open && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
              <h3 className="text-lg font-semibold mb-4">Flag Record for Review</h3>
              <p className="text-sm text-gray-600 mb-4">
                Record: <strong>{overrideModal.record?.recordId}</strong>
              </p>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reason for Flagging
                </label>
                <textarea
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  rows={3}
                  placeholder="Enter reason for flagging this record for review..."
                />
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setOverrideModal(null)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  disabled={isOverriding}
                >
                  Cancel
                </button>
                <button
                  onClick={handleOverrideSubmit}
                  disabled={!overrideReason.trim() || isOverriding}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
                >
                  {isOverriding ? 'Flagging...' : 'Flag for Review'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Approve Modal */}
        {approveModal?.open && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
              <h3 className="text-lg font-semibold mb-4">Approve Record</h3>
              <p className="text-sm text-gray-600 mb-4">
                Are you sure you want to approve record <strong>{approveModal.record?.recordId}</strong>?
              </p>
              {approveError && <div className="text-red-600 text-sm mb-2">{approveError}</div>}
              <div className="flex justify-end space-x-3">
                <button
                  onClick={handleApproveCancel}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  disabled={isApproving}
                >
                  Cancel
                </button>
                <button
                  onClick={handleApproveConfirm}
                  disabled={isApproving}
                  className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50"
                >
                  {isApproving ? 'Approving...' : 'Approve'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Record Detail Modal */}
        <RecordDetailModal
          record={selectedRecord}
          isOpen={isDetailOpen}
          onClose={handleDetailClose}
          onRecordUpdated={fetchAllRecords}
        />

        {/* Pagination */}
        <div className="flex items-center justify-between mt-6 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-700">
              Showing {records.length} of {pagination.total} records 
              (Page {pagination.page} of {pagination.totalPages})
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1 || loading}
              className="px-3 py-1 border border-gray-300 rounded-md bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
            >
              <span>Previous</span>
            </button>
            
            <div className="flex items-center space-x-1">
              {pagination.totalPages > 1 && (
                <>
                  {page > 2 && (
                    <>
                      <button
                        onClick={() => setPage(1)}
                        className="px-2 py-1 text-sm border border-gray-300 rounded bg-white hover:bg-gray-50"
                      >
                        1
                      </button>
                      {page > 3 && <span className="text-gray-500">...</span>}
                    </>
                  )}
                  
                  {page > 1 && (
                    <button
                      onClick={() => setPage(page - 1)}
                      className="px-2 py-1 text-sm border border-gray-300 rounded bg-white hover:bg-gray-50"
                    >
                      {page - 1}
                    </button>
                  )}
                  
                  <span className="px-2 py-1 text-sm bg-blue-600 text-white rounded">
                    {page}
                  </span>
                  
                  {page < pagination.totalPages && (
                    <button
                      onClick={() => setPage(page + 1)}
                      className="px-2 py-1 text-sm border border-gray-300 rounded bg-white hover:bg-gray-50"
                    >
                      {page + 1}
                    </button>
                  )}
                  
                  {page < pagination.totalPages - 1 && (
                    <>
                      {page < pagination.totalPages - 2 && <span className="text-gray-500">...</span>}
                      <button
                        onClick={() => setPage(pagination.totalPages)}
                        className="px-2 py-1 text-sm border border-gray-300 rounded bg-white hover:bg-gray-50"
                      >
                        {pagination.totalPages}
                      </button>
                    </>
                  )}
                </>
              )}
            </div>
            
            <button
              onClick={() => setPage(Math.min(pagination.totalPages, page + 1))}
              disabled={page >= pagination.totalPages || loading}
              className="px-3 py-1 border border-gray-300 rounded-md bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
            >
              <span>Next</span>
            </button>
            
            <select
              value={pageSize}
              onChange={e => {
                setPageSize(Number(e.target.value))
                setPage(1) // Reset to first page when changing page size
              }}
              className="ml-4 border border-gray-300 rounded-md px-2 py-1 text-sm bg-white"
            >
              <option value={10}>10 per page</option>
              <option value={25}>25 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
} 