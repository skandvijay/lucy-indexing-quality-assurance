'use client';

import React, { useState, useEffect } from 'react';

interface Threshold {
  name: string;
  current_value: number;
  default_value: number;
  min_value: number;
  max_value: number;
  description: string;
  category: string;
  unit: string;
}

interface ThresholdHistory {
  threshold_name: string;
  old_value: number;
  new_value: number;
  changed_by: string;
  reason?: string;
  timestamp: string;
}

interface ThresholdUpdateRequest {
  threshold_name: string;
  new_value: number;
  reason?: string;
  user_id?: string;
}

export default function ThresholdsPage() {
  const [thresholds, setThresholds] = useState<Threshold[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [editingThreshold, setEditingThreshold] = useState<string | null>(null);
  const [newValues, setNewValues] = useState<Record<string, number>>({});
  const [updateReason, setUpdateReason] = useState('');
  const [history, setHistory] = useState<ThresholdHistory[]>([]);
  const [showHistory, setShowHistory] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const categories = ['all', 'quality', 'llm', 'rules', 'cost'];

  useEffect(() => {
    fetchThresholds();
  }, []);

  const fetchThresholds = async () => {
    try {
      const response = await fetch('/api/thresholds');
      if (response.ok) {
        const data = await response.json();
        setThresholds(data.thresholds);
      } else {
        setMessage({ type: 'error', text: 'Failed to fetch thresholds' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Error connecting to server' });
    } finally {
      setLoading(false);
    }
  };

  const updateThreshold = async (thresholdName: string, newValue: number) => {
    try {
      const updateData: ThresholdUpdateRequest = {
        threshold_name: thresholdName,
        new_value: newValue,
        reason: updateReason || 'Updated via UI',
        user_id: 'admin'
      };

      const response = await fetch(`/api/thresholds/${thresholdName}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData)
      });

      if (response.ok) {
        const result = await response.json();
        setMessage({ type: 'success', text: result.message });
        setEditingThreshold(null);
        setNewValues({});
        setUpdateReason('');
        fetchThresholds(); // Refresh the list
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || 'Failed to update threshold' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Error updating threshold' });
    }
  };

  const resetThreshold = async (thresholdName: string) => {
    try {
      const response = await fetch(`/api/thresholds/${thresholdName}/reset?user_id=admin`);
      if (response.ok) {
        const result = await response.json();
        setMessage({ type: 'success', text: result.message });
        fetchThresholds(); // Refresh the list
      } else {
        setMessage({ type: 'error', text: 'Failed to reset threshold' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Error resetting threshold' });
    }
  };

  const fetchHistory = async (thresholdName: string) => {
    try {
      const response = await fetch(`/api/thresholds/${thresholdName}/history`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data.history);
        setShowHistory(thresholdName);
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Error fetching history' });
    }
  };

  const filteredThresholds = thresholds.filter(threshold => 
    selectedCategory === 'all' || threshold.category === selectedCategory
  );

  const getCategoryColor = (category: string) => {
    const colors = {
      quality: 'bg-blue-100 text-blue-800',
      llm: 'bg-green-100 text-green-800',
      rules: 'bg-purple-100 text-purple-800',
      cost: 'bg-orange-100 text-orange-800'
    };
    return colors[category as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  const getValueColor = (threshold: Threshold) => {
    const ratio = (threshold.current_value - threshold.min_value) / (threshold.max_value - threshold.min_value);
    if (ratio < 0.3) return 'text-red-600';
    if (ratio < 0.7) return 'text-yellow-600';
    return 'text-green-600';
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p>Loading thresholds...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Dynamic Threshold Management</h1>
        <p className="text-gray-600">
          Update quality control thresholds in real-time without restarting the server
        </p>
      </div>

      {message && (
        <div className={`mb-4 p-4 rounded-lg border ${
          message.type === 'success' 
            ? 'border-green-200 bg-green-50 text-green-800' 
            : 'border-red-200 bg-red-50 text-red-800'
        }`}>
          {message.text}
        </div>
      )}

      <div className="mb-6 flex gap-4 items-center">
        <label htmlFor="category" className="font-medium">Filter by Category:</label>
        <select 
          id="category"
          value={selectedCategory} 
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-2 w-48"
        >
          {categories.map(category => (
            <option key={category} value={category}>
              {category.charAt(0).toUpperCase() + category.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-6">
        {filteredThresholds.map(threshold => (
          <div key={threshold.name} className="border border-gray-200 rounded-lg p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold">{threshold.name.replace(/_/g, ' ')}</h3>
                <p className="text-sm text-gray-600 mt-1">{threshold.description}</p>
              </div>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(threshold.category)}`}>
                {threshold.category}
              </span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="font-medium">Current Value</label>
                  <span className={`font-semibold ${getValueColor(threshold)}`}>
                    {threshold.current_value} {threshold.unit}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ 
                      width: `${((threshold.current_value - threshold.min_value) / (threshold.max_value - threshold.min_value)) * 100}%` 
                    }}
                  ></div>
                </div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Min: {threshold.min_value}</span>
                  <span>Max: {threshold.max_value}</span>
                </div>
              </div>

              <div className="space-y-2">
                {editingThreshold === threshold.name ? (
                  <div className="space-y-2">
                    <div>
                      <label htmlFor={`new-value-${threshold.name}`} className="block text-sm font-medium mb-1">
                        New Value
                      </label>
                      <input
                        id={`new-value-${threshold.name}`}
                        type="number"
                        min={threshold.min_value}
                        max={threshold.max_value}
                        step="0.1"
                        value={newValues[threshold.name] || ''}
                        onChange={(e) => setNewValues({
                          ...newValues,
                          [threshold.name]: parseFloat(e.target.value)
                        })}
                        className="w-full border border-gray-300 rounded-md px-3 py-2"
                      />
                    </div>
                    <div>
                      <label htmlFor="reason" className="block text-sm font-medium mb-1">
                        Reason (optional)
                      </label>
                      <input
                        id="reason"
                        type="text"
                        placeholder="Why are you changing this threshold?"
                        value={updateReason}
                        onChange={(e) => setUpdateReason(e.target.value)}
                        className="w-full border border-gray-300 rounded-md px-3 py-2"
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => updateThreshold(threshold.name, newValues[threshold.name])}
                        disabled={!newValues[threshold.name] || newValues[threshold.name] < threshold.min_value || newValues[threshold.name] > threshold.max_value}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Update
                      </button>
                      <button
                        onClick={() => {
                          setEditingThreshold(null);
                          setNewValues({});
                          setUpdateReason('');
                        }}
                        className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <button
                      onClick={() => setEditingThreshold(threshold.name)}
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => resetThreshold(threshold.name)}
                      className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                    >
                      Reset to Default
                    </button>
                    <button
                      onClick={() => fetchHistory(threshold.name)}
                      className="px-4 py-2 text-gray-600 hover:text-gray-800"
                    >
                      History
                    </button>
                  </div>
                )}
              </div>
            </div>

            {showHistory === threshold.name && history.length > 0 && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                <h4 className="font-semibold mb-2">Change History</h4>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {history.map((change, index) => (
                    <div key={index} className="text-sm">
                      <div className="flex justify-between">
                        <span>{new Date(change.timestamp).toLocaleString()}</span>
                        <span className="font-mono">
                          {change.old_value} → {change.new_value}
                        </span>
                      </div>
                      <div className="text-gray-600">
                        by {change.changed_by}
                        {change.reason && ` - ${change.reason}`}
                      </div>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => setShowHistory(null)}
                  className="mt-2 text-sm text-gray-600 hover:text-gray-800"
                >
                  Hide History
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {filteredThresholds.length === 0 && (
        <div className="border border-gray-200 rounded-lg p-8 text-center">
          <p className="text-gray-500">No thresholds found for the selected category.</p>
        </div>
      )}
    </div>
  );
} 