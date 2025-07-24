'use client'

import React, { useState, useEffect } from 'react'
import { 
  Save, 
  RotateCcw, 
  Filter, 
  Search, 
  History, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info
} from 'lucide-react'

interface Threshold {
  name: string
  current_value: number
  default_value: number
  min_value: number
  max_value: number
  description: string
  category: string
  unit: string
}

interface ThresholdHistory {
  threshold_name: string
  old_value: number
  new_value: number
  changed_by: string
  reason?: string
  timestamp: string
}

export default function ThresholdsTab() {
  const [thresholds, setThresholds] = useState<Threshold[]>([])
  const [filteredThresholds, setFilteredThresholds] = useState<Threshold[]>([])
  const [history, setHistory] = useState<ThresholdHistory[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [editingThreshold, setEditingThreshold] = useState<string | null>(null)
  const [editValue, setEditValue] = useState<number>(0)
  const [editReason, setEditReason] = useState('')
  const [status, setStatus] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)

  const categories = [
    { id: 'all', name: 'All Categories' },
    { id: 'quality', name: 'Quality Control' },
    { id: 'llm', name: 'LLM Validation' },
    { id: 'rules', name: 'Rules Engine' },
    { id: 'performance', name: 'Performance' }
  ]

  useEffect(() => {
    loadThresholds()
    loadHistory()
  }, [])

  useEffect(() => {
    filterThresholds()
  }, [thresholds, searchTerm, categoryFilter])

  const loadThresholds = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/thresholds')
      if (response.ok) {
        const data = await response.json()
        setThresholds(data.thresholds || [])
      } else {
        console.error('Failed to load thresholds')
        setStatus({ type: 'error', message: 'Failed to load thresholds' })
      }
    } catch (error) {
      console.error('Error loading thresholds:', error)
      setStatus({ type: 'error', message: 'Error loading thresholds' })
    } finally {
      setLoading(false)
    }
  }

  const loadHistory = async () => {
    try {
      // Load history for all thresholds
      const allHistory: ThresholdHistory[] = []
      for (const threshold of thresholds) {
        const response = await fetch(`/api/thresholds/${threshold.name}/history`)
        if (response.ok) {
          const data = await response.json()
          allHistory.push(...(data.history || []))
        }
      }
      setHistory(allHistory)
    } catch (error) {
      console.error('Error loading history:', error)
    }
  }

  const filterThresholds = () => {
    let filtered = thresholds

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(t => 
        t.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        t.description.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    // Apply category filter
    if (categoryFilter !== 'all') {
      filtered = filtered.filter(t => t.category === categoryFilter)
    }

    setFilteredThresholds(filtered)
  }

  const updateThreshold = async (name: string, value: number, reason: string) => {
    try {
      setLoading(true)
      const response = await fetch(`/api/thresholds/${name}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          threshold_name: name,
          new_value: value,
          reason: reason,
          user_id: 'admin'
        })
      })

      if (response.ok) {
        setStatus({ type: 'success', message: 'Threshold updated successfully!' })
        setEditingThreshold(null)
        setEditValue(0)
        setEditReason('')
        await loadThresholds()
        await loadHistory()
      } else {
        const errorData = await response.json()
        setStatus({ type: 'error', message: errorData.detail || 'Failed to update threshold' })
      }
    } catch (error) {
      setStatus({ type: 'error', message: 'Error updating threshold' })
    } finally {
      setLoading(false)
    }
  }

  const resetThresholds = async () => {
    try {
      setLoading(true)
      // Reset each threshold individually
      for (const threshold of thresholds) {
        const response = await fetch(`/api/thresholds/${threshold.name}/reset`, {
          method: 'POST'
        })
        if (!response.ok) {
          throw new Error(`Failed to reset ${threshold.name}`)
        }
      }
      
      setStatus({ type: 'success', message: 'Thresholds reset to defaults!' })
      await loadThresholds()
      await loadHistory()
    } catch (error) {
      setStatus({ type: 'error', message: 'Error resetting thresholds' })
    } finally {
      setLoading(false)
    }
  }

  const startEditing = (threshold: Threshold) => {
    setEditingThreshold(threshold.name)
    setEditValue(threshold.current_value)
    setEditReason('')
  }

  const cancelEditing = () => {
    setEditingThreshold(null)
    setEditValue(0)
    setEditReason('')
  }

  const getStatusIcon = (threshold: Threshold) => {
    if (threshold.current_value >= threshold.max_value * 0.8) return <CheckCircle className="h-4 w-4 text-green-500" />
    if (threshold.current_value <= threshold.min_value * 1.2) return <XCircle className="h-4 w-4 text-red-500" />
    return <Info className="h-4 w-4 text-yellow-500" />
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-medium text-gray-900">Dynamic Threshold Management</h2>
        <button
          onClick={resetThresholds}
          disabled={loading}
          className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50 flex items-center space-x-2"
        >
          <RotateCcw className="h-4 w-4" />
          <span>Reset to Defaults</span>
        </button>
      </div>

      {status && (
        <div className={`p-4 rounded-md ${
          status.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' :
          status.type === 'error' ? 'bg-red-50 text-red-800 border border-red-200' :
          'bg-blue-50 text-blue-800 border border-blue-200'
        }`}>
          {status.message}
        </div>
      )}

      {/* Search and Filter Controls */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
          <input
            type="text"
            placeholder="Search thresholds..."
            value={searchTerm || ''}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center space-x-2">
          <Filter className="h-4 w-4 text-gray-400" />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {categories.map(category => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Thresholds List */}
      {loading ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading thresholds...</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredThresholds.map((threshold) => (
            <div key={threshold.name} className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(threshold)}
                  <h3 className="font-medium text-gray-900">{threshold.name}</h3>
                  <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
                    {threshold.category}
                  </span>
                </div>
                <button
                  onClick={() => startEditing(threshold)}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Edit
                </button>
              </div>

              <p className="text-gray-600 text-sm mb-3">{threshold.description}</p>

              {editingThreshold === threshold.name ? (
                <div className="space-y-3 p-3 bg-gray-50 rounded">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Current Value
                      </label>
                      <input
                        type="number"
                        min={threshold.min_value}
                        max={threshold.max_value}
                        step="0.1"
                        value={isNaN(editValue) ? '' : editValue}
                        onChange={(e) => {
                          const value = parseFloat(e.target.value)
                          setEditValue(isNaN(value) ? 0 : value)
                        }}
                        className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Range: {threshold.min_value} - {threshold.max_value} {threshold.unit}
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Reason for Change
                      </label>
                      <input
                        type="text"
                        placeholder="Reason for change..."
                        value={editReason || ''}
                        onChange={(e) => setEditReason(e.target.value)}
                        className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => updateThreshold(threshold.name, editValue, editReason)}
                      disabled={loading}
                      className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 flex items-center space-x-1"
                    >
                      <Save className="h-3 w-3" />
                      <span>Save</span>
                    </button>
                    <button
                      onClick={cancelEditing}
                      className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Current Value:</span>
                    <span className="font-medium">{threshold.current_value} {threshold.unit}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Default Value:</span>
                    <span className="text-gray-500">{threshold.default_value} {threshold.unit}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{
                        width: `${((threshold.current_value - threshold.min_value) / (threshold.max_value - threshold.min_value)) * 100}%`
                      }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* History Section */}
      {history.length > 0 && (
        <div className="mt-8">
          <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center space-x-2">
            <History className="h-5 w-5" />
            <span>Recent Changes</span>
          </h3>
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Threshold
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Old Value
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      New Value
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Changed By
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Reason
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {history.slice(0, 10).map((entry, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {entry.threshold_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {entry.old_value}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {entry.new_value}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {entry.changed_by}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {entry.reason || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(entry.timestamp).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
} 