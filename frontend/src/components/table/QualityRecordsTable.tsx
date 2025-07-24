'use client';

import React, { useState } from 'react';
import { PaginatedResponse, QualityRecord } from '@/types';
import { apiClient } from '@/app/api';
import { 
  Eye,
  AlertTriangle,
  CheckCircle,
  Clock,
  Flag
} from 'lucide-react';

interface QualityRecordsTableProps {
  data: any[];
  loading: boolean;
  onRecordClick: (record: any) => void;
  onOverride?: (record: any) => void;
  onBulkAction?: (action: string, recordIds: string[]) => void;
  onSort?: (sortBy: string, sortOrder: 'asc' | 'desc') => void;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  selectedRecords?: string[];
  onSelectionChange?: (recordIds: string[]) => void;
  onRecordUpdated?: () => void;
}

export default function QualityRecordsTable({
  data,
  loading,
  onRecordClick,
  onOverride,
  onBulkAction = () => {},
  onSort = () => {},
  onPageChange = () => {},
  onPageSizeChange = () => {},
  selectedRecords = [],
  onSelectionChange = () => {},
  onRecordUpdated = () => {},
}: QualityRecordsTableProps) {
  // Add state for button loading states
  const [approvingRecord, setApprovingRecord] = useState<string | null>(null);
  const [flaggingRecord, setFlaggingRecord] = useState<string | null>(null);

  // Direct API handlers for approve/flag actions
  const handleApproveRecord = async (record: any) => {
    try {
      const recordIdentifier = record.recordId || record.id;
      setApprovingRecord(recordIdentifier);
      
      const result = await apiClient.approveRecord(
        recordIdentifier,
        'current_user',
        'Approved via table action'
      );
      
      if (result.success) {
        console.log('Record approved successfully:', result.message);
        onRecordUpdated();
      } else {
        console.error('Failed to approve record:', result);
      }
    } catch (error) {
      console.error('Error approving record:', error);
    } finally {
      setApprovingRecord(null);
    }
  };

  const handleFlagRecord = async (record: any) => {
    try {
      const recordIdentifier = record.recordId || record.id;
      setFlaggingRecord(recordIdentifier);
      
      const result = await apiClient.flagRecord(
        recordIdentifier,
        'current_user',
        'Flagged via table action'
      );
      
      if (result.success) {
        console.log('Record flagged successfully:', result.message);
        onRecordUpdated();
      } else {
        console.error('Failed to flag record:', result);
      }
    } catch (error) {
      console.error('Error flagging record:', error);
    } finally {
      setFlaggingRecord(null);
    }
  };

  const getStatusColor = (status: QualityRecord['status']) => {
    switch (status) {
      case 'approved':
        return 'bg-green-100 text-green-800';
      case 'flagged':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'under_review':
        return 'bg-blue-100 text-blue-800';
      case 'rejected':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: QualityRecord['status']) => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="w-4 h-4" />;
      case 'flagged':
        return <AlertTriangle className="w-4 h-4" />;
      case 'pending':
        return <Clock className="w-4 h-4" />;
      case 'under_review':
        return <Flag className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const getStatusText = (status: QualityRecord['status']) => {
    switch (status) {
      case 'approved':
        return 'Approved';
      case 'flagged':
        return 'Flagged';
      case 'pending':
        return 'Pending';
      case 'under_review':
        return 'Under Review';
      case 'rejected':
        return 'Rejected';
      default:
        return status;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const handleSelectAll = () => {
    if (selectedRecords.length === data.length) {
      onSelectionChange([]);
    } else {
      onSelectionChange(data.map(record => record.id));
    }
  };

  const handleSelectRecord = (recordId: string) => {
    const newSelection = selectedRecords.includes(recordId)
      ? selectedRecords.filter(id => id !== recordId)
      : [...selectedRecords, recordId];
    onSelectionChange(newSelection);
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg">
        <div className="px-6 py-4">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Ensure data is an array
  const records = Array.isArray(data) ? data : [];

  return (
    <div className="bg-white rounded-lg overflow-hidden">
      {/* Bulk actions */}
      {selectedRecords.length > 0 && (
        <div className="px-6 py-3 bg-blue-50 border-b border-blue-200">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-blue-700">
              {selectedRecords.length} records selected
            </span>
            <div className="flex space-x-2">
              <button
                onClick={() => onBulkAction('approve', selectedRecords)}
                className="px-3 py-1 text-xs font-medium bg-green-100 text-green-700 rounded hover:bg-green-200"
              >
                Approve
              </button>
              <button
                onClick={() => onBulkAction('flag', selectedRecords)}
                className="px-3 py-1 text-xs font-medium bg-red-100 text-red-700 rounded hover:bg-red-200"
              >
                Flag
              </button>
              <button
                onClick={() => onBulkAction('review', selectedRecords)}
                className="px-3 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
              >
                Review
              </button>
            </div>
          </div>
        </div>
      )}

      {records.length === 0 ? (
        <div className="text-center py-12">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No records found</h3>
          <p className="mt-1 text-sm text-gray-500">
            No quality records match your current filters.
          </p>
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
                  Record ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Company
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tags
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Quality Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Issues
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
                  className="hover:bg-gray-100 cursor-pointer group"
                  onClick={e => {
                    // Prevent row click if an action button was clicked
                    if ((e.target as HTMLElement).closest('button')) return;
                    onRecordClick(record);
                  }}
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-600">
                    {record.trace_id ? (
                      <span className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {record.trace_id.substring(0, 8)}...
                      </span>
                    ) : (
                      <span className="text-gray-400">N/A</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {record.recordId}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      {getStatusIcon(record.status)}
                      <span className={`ml-2 inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(record.status)}`}>
                        {getStatusText(record.status)}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {record.companyName || 'Unknown'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-wrap gap-1">
                      {record.tags && record.tags.map((tag: string, idx: number) => (
                        <span key={idx} className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div className="flex items-center">
                      <span className={`font-semibold ${
                        record.qualityScore >= 80 ? 'text-green-600' : 
                        record.qualityScore >= 60 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {record.qualityScore?.toFixed(1) || 'N/A'}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {record.issues && record.issues.length > 0 ? (
                      <div className="space-y-1">
                        {record.issues.slice(0, 2).map((issue: any, idx: number) => (
                          <div key={idx} className="text-xs text-red-600">
                            {issue.type}: {issue.description}
                          </div>
                        ))}
                        {record.issues.length > 2 && (
                          <div className="text-xs text-gray-500">
                            +{record.issues.length - 2} more issues
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className="text-green-600 text-xs">No issues</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <button 
                        onClick={e => { e.stopPropagation(); onRecordClick(record); }}
                        className="text-blue-600 hover:text-blue-900 flex items-center"
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        View
                      </button>
                      
                      {/* Consistent approve/flag buttons with loading states */}
                      {record.status === 'approved' && (
                        <button 
                          onClick={e => { e.stopPropagation(); handleFlagRecord(record); }} 
                          disabled={flaggingRecord === (record.recordId || record.id)}
                          className="text-amber-600 hover:text-amber-900 flex items-center disabled:opacity-50"
                        >
                          <Flag className="w-4 h-4 mr-1" />
                          {flaggingRecord === (record.recordId || record.id) ? 'Flagging...' : 'Flag'}
                        </button>
                      )}
                      
                      {record.status === 'flagged' && (
                        <button
                          onClick={e => { e.stopPropagation(); handleApproveRecord(record); }}
                          disabled={approvingRecord === (record.recordId || record.id)}
                          className="text-green-600 hover:text-green-900 flex items-center disabled:opacity-50"
                        >
                          <CheckCircle className="w-4 h-4 mr-1" />
                          {approvingRecord === (record.recordId || record.id) ? 'Approving...' : 'Approve'}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
} 