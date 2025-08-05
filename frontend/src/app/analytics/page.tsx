'use client'

import React, { useState, useEffect } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { 
  LineChart, 
  Line, 
  AreaChart, 
  Area,
  BarChart, 
  Bar, 
  PieChart, 
  Pie, 
  Cell,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  ComposedChart,
  Scatter,
  ScatterChart
} from 'recharts'
import { 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  PieChart as PieChartIcon, 
  Activity,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Zap,
  Target,
  Users,
  Database,
  RefreshCw,
  Filter,
  Calendar,
  Building,
  GitBranch,
  Tag,
  FileText,
  Download,
  Eye,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  ChevronDown,
  X
} from 'lucide-react'
import { apiClient } from '@/app/api'

interface AdvancedAnalyticsData {
  qualityTrendData: Array<{
    date: string
    avgQualityScore: number
    approved: number
    flagged: number
    totalRecords: number
  }>
  companyBreakdown: Array<{
    company: string
    approved: number
    flagged: number
    avgQuality: number
    totalRecords: number
    cost: number
  }>
  connectorBreakdown: Array<{
    connector: string
    approved: number
    flagged: number
    avgQuality: number
    totalRecords: number
    reliability: number
  }>
  tagAnalytics: Array<{
    tag: string
    frequency: number
    avgQuality: number
    relevancyScore: number
    usage: 'high' | 'medium' | 'low'
  }>
  qualityDistribution: Array<{
    range: string
    count: number
    percentage: number
  }>
  topIssues: Array<{
    issue: string
    count: number
    severity: 'critical' | 'high' | 'medium' | 'low'
    affectedCompanies: number
  }>
  fileTypeData?: Array<{
    fileType: string
    count: number
    avgQuality: number
    issues: number
    successRate: number
    color: string
  }>
}

export default function AdvancedAnalyticsPage() {
  // State management
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([])
  const [selectedConnectors, setSelectedConnectors] = useState<string[]>([])
  const [selectedFileTypes, setSelectedFileTypes] = useState<string[]>([])
  const [selectedView, setSelectedView] = useState<'overview' | 'companies' | 'connectors' | 'tags' | 'quality' | 'filetypes'>('overview')
  const [analyticsData, setAnalyticsData] = useState<AdvancedAnalyticsData | null>(null)
  const [filterOptions, setFilterOptions] = useState<{
    companies: Array<{value: string, label: string, count: number}>
    connectors: Array<{value: string, label: string, count: number}>
    fileTypes: Array<{value: string, label: string, count: number}>
  }>({ companies: [], connectors: [], fileTypes: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Modern Apple-inspired color palette
  const colors = {
    primary: '#007AFF',
    success: '#34C759', 
    warning: '#FF9500',
    danger: '#FF3B30',
    secondary: '#8E8E93',
    background: '#F2F2F7',
    surface: '#FFFFFF',
    surfaceSecondary: '#F9F9FB',
    text: '#1D1D1F',
    textSecondary: '#86868B',
    border: '#E5E5EA',
    accent: '#5856D6'
  }

  const fetchFilterOptions = async () => {
    try {
      const options = await apiClient.getFilterOptions()
      setFilterOptions({
        companies: options.companies || [],
        connectors: options.connectors || [],
        fileTypes: options.fileTypes || []
      })
    } catch (err) {
      console.error('Error fetching filter options:', err)
    }
  }

  const fetchAdvancedAnalytics = async () => {
    try {
      setLoading(true)
      setError(null)

      // Define file type extraction function first
      const extractFileTypeFromMetadata = (contentMetadata: string, sourceConnector: string = '') => {
        try {
          if (contentMetadata) {
            const metadata = typeof contentMetadata === 'string' ? JSON.parse(contentMetadata) : contentMetadata
            
            // Check for direct file_type field
            if (metadata.file_type) {
              return metadata.file_type.toLowerCase()
            }
            
            // Extract from filename or file path
            const filename = metadata.filename || metadata.file_name || metadata.title || ''
            if (filename.includes('.')) {
              const ext = filename.split('.').pop()?.toLowerCase() || ''
              const fileTypeMap: { [key: string]: string } = {
                'pdf': 'PDF Document',
                'docx': 'Microsoft Word',
                'doc': 'Microsoft Word',
                'pptx': 'Microsoft PowerPoint',
                'ppt': 'Microsoft PowerPoint',
                'xlsx': 'Microsoft Excel',
                'xls': 'Microsoft Excel',
                'txt': 'Text Document',
                'html': 'Web Content',
                'htm': 'Web Content',
                'csv': 'CSV Data',
                'json': 'JSON Data',
                'xml': 'XML Document'
              }
              return fileTypeMap[ext] || 'Unknown Type'
            }
            
            // Check for document type indicators
            const docType = metadata.document_type || metadata.content_type || ''
            if (docType) {
              if (docType.toLowerCase().includes('pdf')) return 'PDF Document'
              if (docType.toLowerCase().includes('word') || docType.toLowerCase().includes('docx')) return 'Microsoft Word'
              if (docType.toLowerCase().includes('excel') || docType.toLowerCase().includes('xlsx')) return 'Microsoft Excel'
              if (docType.toLowerCase().includes('powerpoint') || docType.toLowerCase().includes('pptx')) return 'Microsoft PowerPoint'
            }
          }
          
          // Infer from source connector
          const sourceMapping: { [key: string]: string } = {
            'sharepoint': 'Microsoft Word',
            'confluence': 'Web Content',
            'notion': 'Web Content',
            'jira': 'Web Content',
            'gdrive': 'Microsoft Word'
          }
          
          return sourceMapping[sourceConnector.toLowerCase()] || 'Unknown Type'
          
        } catch (error) {
          return 'Unknown Type'
        }
      }

      // Get backend analytics data (includes fileTypeData)
      const analyticsResponse = await apiClient.getDashboardAnalytics()

      // Get analytics data and records with proper filtering (no fileTypes in backend API)
      const recordsResponse = await apiClient.getQualityRecords(
        {
          companies: selectedCompanies.length > 0 ? selectedCompanies : undefined,
          sourceConnectors: selectedConnectors.length > 0 ? selectedConnectors : undefined
        },
        { page: 1, pageSize: 1000, sortBy: 'createdAt', sortOrder: 'desc' }
      )

      // Process the data for advanced analytics
      let records = recordsResponse.data || []

      // Apply client-side file type filtering if specific file types are selected
      if (selectedFileTypes.length > 0) {
        records = records.filter((record: any) => {
          const fileType = extractFileTypeFromMetadata(
            JSON.stringify(record.metadata || {}), 
            record.sourceConnectorName || record.sourceConnectorType || ''
          )
          return selectedFileTypes.includes(fileType)
        })
      }

      // Calculate filtered file type data
      const fileTypeStats: { [key: string]: { count: number, totalQuality: number, issues: number, successCount: number } } = {}
      
      records.forEach((record: any) => {
        const fileType = extractFileTypeFromMetadata(
          JSON.stringify(record.metadata || {}), 
          record.sourceConnectorName || record.sourceConnectorType || ''
        )
        
        if (!fileTypeStats[fileType]) {
          fileTypeStats[fileType] = { count: 0, totalQuality: 0, issues: 0, successCount: 0 }
        }
        
        fileTypeStats[fileType].count++
        fileTypeStats[fileType].totalQuality += record.qualityScore || 0
        
        if (record.status === 'flagged' || record.status === 'under_review') {
          fileTypeStats[fileType].issues++
        }
        
        if (record.status === 'approved') {
          fileTypeStats[fileType].successCount++
        }
      })

      // Convert to file type data format with Apple colors
      const appleColors = [
        '#007AFF', '#34C759', '#FF9500', '#FF3B30', 
        '#5856D6', '#FF2D92', '#64D2FF', '#32D74B'
      ]
      
      const filteredFileTypeData = Object.entries(fileTypeStats).map(([fileType, stats], index) => ({
        fileType,
        count: stats.count,
        avgQuality: stats.count > 0 ? Math.round((stats.totalQuality / stats.count) * 10) / 10 : 0,
        issues: stats.issues,
        successRate: stats.count > 0 ? Math.round((stats.successCount / stats.count) * 1000) / 10 : 0,
        color: appleColors[index % appleColors.length]
      })).sort((a, b) => b.count - a.count)
      
      // Generate quality trend data with real data processing
      const trendData = []
      const today = new Date()
      const daysCount = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
      
      for (let i = daysCount - 1; i >= 0; i--) {
        const date = new Date(today)
        date.setDate(date.getDate() - i)
        const dateStr = date.toISOString().split('T')[0]
        
        const dayRecords = records.filter((record: any) => {
          const recordDate = new Date(record.createdAt).toISOString().split('T')[0]
          return recordDate === dateStr
        })
        
        const totalRecords = dayRecords.length
        const approved = dayRecords.filter((r: any) => r.status === 'approved').length
        const flagged = dayRecords.filter((r: any) => r.status === 'flagged' || r.status === 'under_review').length
        const avgQuality = totalRecords > 0 
          ? dayRecords.reduce((sum: number, r: any) => sum + (r.qualityScore || 0), 0) / totalRecords
          : 0

        trendData.push({
          date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          avgQualityScore: Math.round(avgQuality * 10) / 10,
          approved,
          flagged,
          totalRecords
        })
      }

      // Company breakdown analysis with proper quality calculation
      const companyStats = new Map<string, any>()
      records.forEach((record: any) => {
        const company = record.companyName || record.company || 'Unknown'
        if (!companyStats.has(company)) {
          companyStats.set(company, {
            approved: 0, flagged: 0, totalQuality: 0, count: 0, cost: 0
          })
        }
        const stats = companyStats.get(company)
        stats.count++
        stats.totalQuality += record.qualityScore || 0
        stats.cost += 0.05 // Mock cost calculation
        if (record.status === 'approved') stats.approved++
        else stats.flagged++
      })

      const companyBreakdown = Array.from(companyStats.entries()).map(([company, stats]) => ({
        company,
        approved: stats.approved,
        flagged: stats.flagged,
        avgQuality: stats.count > 0 ? Math.round((stats.totalQuality / stats.count) * 10) / 10 : 0,
        totalRecords: stats.count,
        cost: Math.round(stats.cost * 100) / 100
      })).sort((a, b) => b.totalRecords - a.totalRecords)

      // Connector breakdown analysis with proper quality calculation
      const connectorStats = new Map<string, any>()
      records.forEach((record: any) => {
        const connector = record.sourceConnectorName || record.sourceConnector || 'Unknown'
        if (!connectorStats.has(connector)) {
          connectorStats.set(connector, {
            approved: 0, flagged: 0, totalQuality: 0, count: 0
          })
        }
        const stats = connectorStats.get(connector)
        stats.count++
        stats.totalQuality += record.qualityScore || 0
        if (record.status === 'approved') stats.approved++
        else stats.flagged++
      })

      const connectorBreakdown = Array.from(connectorStats.entries()).map(([connector, stats]) => ({
        connector,
        approved: stats.approved,
        flagged: stats.flagged,
        avgQuality: stats.count > 0 ? Math.round((stats.totalQuality / stats.count) * 10) / 10 : 0,
        totalRecords: stats.count,
        reliability: stats.count > 0 ? Math.round((stats.approved / stats.count) * 100) : 0
      })).sort((a, b) => b.totalRecords - a.totalRecords)

      // Tag analytics with proper calculation
      const tagStats = new Map<string, any>()
      records.forEach((record: any) => {
        const tags = record.tags || []
        tags.forEach((tag: string) => {
          if (!tagStats.has(tag)) {
            tagStats.set(tag, { count: 0, totalQuality: 0, records: [] })
          }
          const stats = tagStats.get(tag)
          stats.count++
          stats.totalQuality += record.qualityScore || 0
          stats.records.push(record.qualityScore || 0)
        })
      })

      const tagAnalytics = Array.from(tagStats.entries()).map(([tag, stats]) => {
        const avgQuality = stats.count > 0 ? stats.totalQuality / stats.count : 0
        const frequency = stats.count
        // Calculate relevancy score based on consistency and usage
        const variance = stats.count > 0 
          ? stats.records.reduce((acc: number, score: number) => acc + Math.pow(score - avgQuality, 2), 0) / stats.count
          : 0
        const relevancyScore = Math.max(0, 100 - variance) // Lower variance = higher relevancy
        
        return {
          tag,
          frequency,
          avgQuality: Math.round(avgQuality * 10) / 10,
          relevancyScore: Math.round(relevancyScore),
          usage: frequency > 10 ? 'high' : frequency > 5 ? 'medium' : 'low' as 'high' | 'medium' | 'low'
        }
      }).sort((a, b) => b.frequency - a.frequency).slice(0, 20)

      // Quality distribution
      const qualityRanges = [
        { range: '90-100', min: 90, max: 100 },
        { range: '80-89', min: 80, max: 89 },
        { range: '70-79', min: 70, max: 79 },
        { range: '60-69', min: 60, max: 69 },
        { range: '50-59', min: 50, max: 59 },
        { range: '0-49', min: 0, max: 49 }
      ]

      const qualityDistribution = qualityRanges.map(range => {
        const count = records.filter((r: any) => 
          (r.qualityScore || 0) >= range.min && (r.qualityScore || 0) <= range.max
        ).length
        return {
          range: range.range,
          count,
          percentage: records.length > 0 ? Math.round((count / records.length) * 100 * 10) / 10 : 0
        }
      })

      // Top issues analysis
      const issueMap = new Map<string, any>()
      records.forEach((record: any) => {
        const issues = record.issues || []
        issues.forEach((issue: any) => {
          const key = issue.type || 'Unknown Issue'
          if (!issueMap.has(key)) {
            issueMap.set(key, { count: 0, companies: new Set(), severity: issue.severity || 'medium' })
          }
          const stats = issueMap.get(key)
          stats.count++
          stats.companies.add(record.companyName || record.company || 'Unknown')
        })
      })

      const topIssues = Array.from(issueMap.entries()).map(([issue, stats]) => ({
        issue,
        count: stats.count,
        severity: stats.severity,
        affectedCompanies: stats.companies.size
      })).sort((a, b) => b.count - a.count).slice(0, 10)

      setAnalyticsData({
        qualityTrendData: trendData,
        companyBreakdown,
        connectorBreakdown,
        tagAnalytics,
        qualityDistribution,
        topIssues,
        fileTypeData: filteredFileTypeData
      })

    } catch (err) {
      console.error('Error fetching advanced analytics:', err)
      setError('Failed to load analytics data')
      // Set fallback data
      setAnalyticsData({
        qualityTrendData: [],
        companyBreakdown: [],
        connectorBreakdown: [],
        tagAnalytics: [],
        qualityDistribution: [],
        topIssues: [],
        fileTypeData: []
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchFilterOptions()
  }, [])

  useEffect(() => {
    fetchAdvancedAnalytics()
  }, [timeRange, selectedCompanies, selectedConnectors, selectedFileTypes])

  // Modern metric card component
  const MetricCard = ({ 
    title, 
    value, 
    change, 
    changeType = 'neutral',
    icon: Icon, 
    color = 'primary',
    subtitle = ''
  }: {
    title: string;
    value: string | number;
    change?: number;
    changeType?: 'positive' | 'negative' | 'neutral';
    icon: any;
    color?: 'primary' | 'success' | 'warning' | 'danger' | 'secondary' | 'accent';
    subtitle?: string;
  }) => {
    const colorMap: Record<string, string> = {
      primary: colors.primary,
      success: colors.success,
      warning: colors.warning,
      danger: colors.danger,
      secondary: colors.secondary,
      accent: colors.accent
    }

    const TrendIcon = changeType === 'positive' ? ArrowUpRight : 
                     changeType === 'negative' ? ArrowDownRight : Minus

    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 hover:shadow-md transition-all duration-200">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-4">
              <div 
                className="w-12 h-12 rounded-xl flex items-center justify-center"
                style={{ backgroundColor: (colorMap[color] || colors.primary) + '15' }}
              >
                <Icon className="w-6 h-6" style={{ color: colorMap[color] || colors.primary }} />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500 tracking-wide uppercase">{title}</p>
                {subtitle && <p className="text-xs text-gray-400">{subtitle}</p>}
              </div>
            </div>
            <div className="flex items-end gap-3">
              <p className="text-3xl font-bold text-gray-900 tracking-tight">{value}</p>
              {change !== undefined && (
                <div className={`flex items-center gap-1 px-2 py-1 rounded-lg text-sm font-medium ${
                  changeType === 'positive' ? 'bg-green-50 text-green-700' :
                  changeType === 'negative' ? 'bg-red-50 text-red-700' :
                  'bg-gray-50 text-gray-700'
                }`}>
                  <TrendIcon className="w-4 h-4" />
                  {Math.abs(change)}%
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Professional Multi-Select Filter Component
  const MultiSelectFilter = ({ 
    label, 
    icon: Icon, 
    value, 
    onChange, 
    options, 
    placeholder = "Select..." 
  }: {
    label: string;
    icon: any;
    value: string[];
    onChange: (value: string[]) => void;
    options: Array<{value: string, label: string, count: number}>;
    placeholder?: string;
  }) => {
    const [isOpen, setIsOpen] = useState(false)

    const handleToggle = (optionValue: string) => {
      if (value.includes(optionValue)) {
        onChange(value.filter(v => v !== optionValue))
      } else {
        onChange([...value, optionValue])
      }
    }

    const selectedItems = options.filter(opt => value.includes(opt.value))
    const displayText = selectedItems.length === 0 
      ? placeholder 
      : selectedItems.length === 1 
        ? selectedItems[0].label
        : `${selectedItems.length} selected`

    return (
      <div className="relative">
        <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
          <Icon className="w-4 h-4 text-gray-500" />
          {label}
        </label>
        <div className="relative">
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-left text-sm font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors hover:border-gray-300 flex items-center justify-between min-w-[180px]"
          >
            <span className={value.length === 0 ? 'text-gray-500' : 'text-gray-900'}>
              {displayText}
            </span>
            <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
          </button>
          
          {isOpen && (
            <div className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-xl shadow-lg max-h-60 overflow-auto">
              {options.length === 0 ? (
                <div className="px-4 py-3 text-sm text-gray-500">No options available</div>
              ) : (
                options.map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={value.includes(option.value)}
                      onChange={() => handleToggle(option.value)}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-900 flex-1">{option.label}</span>
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                      {option.count}
                    </span>
                  </label>
                ))
              )}
            </div>
          )}
        </div>

        {/* Selected items display */}
        {selectedItems.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {selectedItems.map((item) => (
              <span
                key={item.value}
                className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-full"
              >
                {item.label}
                <button
                  onClick={() => onChange(value.filter(v => v !== item.value))}
                  className="ml-1 hover:text-blue-900"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>
    )
  }

  // Modern chart container
  const ChartContainer = ({ title, children, className = '', action }: any) => (
    <div className={`bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden ${className}`}>
      <div className="px-8 py-6 border-b border-gray-100 bg-gray-50/50">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-semibold text-gray-900 tracking-tight">{title}</h3>
          {action && action}
        </div>
      </div>
      <div className="p-8">
        {children}
      </div>
    </div>
  )

  // Modern table component
  const DataTable = ({ title, headers, data, className = '' }: any) => (
    <div className={`bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden ${className}`}>
      <div className="px-8 py-6 border-b border-gray-100 bg-gray-50/50">
        <h3 className="text-xl font-semibold text-gray-900 tracking-tight">{title}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              {headers.map((header: any, index: number) => (
                <th key={index} className="px-8 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {data}
          </tbody>
        </table>
      </div>
    </div>
  )

  if (loading) {
    return (
      <DashboardLayout>
        <div className="min-h-screen bg-gray-50/50 p-8">
          <div className="max-w-7xl mx-auto">
            <div className="animate-pulse space-y-8">
              <div className="h-12 bg-gray-200 rounded-xl w-1/3"></div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-40 bg-gray-200 rounded-2xl"></div>
                ))}
              </div>
              <div className="h-96 bg-gray-200 rounded-2xl"></div>
            </div>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  const calculateTotals = () => {
    if (!analyticsData) return { total: 0, approved: 0, flagged: 0, avgQuality: 0 }
    
    const approved = analyticsData.companyBreakdown.reduce((sum, item) => sum + item.approved, 0)
    const flagged = analyticsData.companyBreakdown.reduce((sum, item) => sum + item.flagged, 0)
    const total = approved + flagged
    const totalQuality = analyticsData.companyBreakdown.reduce((sum, item) => sum + (item.avgQuality * item.totalRecords), 0)
    const avgQuality = total > 0 ? totalQuality / total : 0

    return { total, approved, flagged, avgQuality: Math.round(avgQuality * 10) / 10 }
  }

  const totals = calculateTotals()

  return (
    <DashboardLayout>
      <div className="min-h-screen bg-gray-50/30">
        <div className="max-w-7xl mx-auto px-8 py-8 space-y-8">
          {/* Modern Header */}
          <div className="flex flex-col space-y-6">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h1 className="text-4xl font-bold text-gray-900 tracking-tight">Analytics Dashboard</h1>
                <p className="text-lg text-gray-600 mt-2">Comprehensive insights into quality patterns and performance metrics</p>
              </div>
              
              <button 
                onClick={fetchAdvancedAnalytics}
                className="flex items-center gap-3 px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors font-medium shadow-sm w-fit"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh Data
              </button>
            </div>
            
            {/* Professional Filters */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <div className="flex items-center gap-3 mb-6">
                <Filter className="w-5 h-5 text-gray-600" />
                <h3 className="text-lg font-semibold text-gray-900">Filters & Settings</h3>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Time Range Filter */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-gray-500" />
                    Time Period
                  </label>
                  <select 
                    value={timeRange} 
                    onChange={(e) => setTimeRange(e.target.value as any)}
                    className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  >
                    <option value="7d">Last 7 days</option>
                    <option value="30d">Last 30 days</option>
                    <option value="90d">Last 90 days</option>
                  </select>
                </div>

                {/* Company Filter */}
                <MultiSelectFilter
                  label="Companies"
                  icon={Building}
                  value={selectedCompanies}
                  onChange={setSelectedCompanies}
                  options={filterOptions.companies}
                  placeholder="All Companies"
                />

                {/* Connector Filter */}
                <MultiSelectFilter
                  label="Connectors"
                  icon={GitBranch}
                  value={selectedConnectors}
                  onChange={setSelectedConnectors}
                  options={filterOptions.connectors}
                  placeholder="All Connectors"
                />

                {/* File Type Filter */}
                <MultiSelectFilter
                  label="File Types"
                  icon={FileText}
                  value={selectedFileTypes}
                  onChange={setSelectedFileTypes}
                  options={filterOptions.fileTypes}
                  placeholder="All File Types"
                />
              </div>
            </div>
          </div>

          {/* Modern Navigation */}
          <div className="flex flex-wrap gap-2 p-2 bg-gray-100 rounded-2xl w-fit">
            {[
              { key: 'overview', label: 'Overview', icon: Activity },
              { key: 'companies', label: 'Companies', icon: Building },
              { key: 'connectors', label: 'Connectors', icon: GitBranch },
              { key: 'tags', label: 'Tags', icon: Tag },
              { key: 'quality', label: 'Quality', icon: Target },
              { key: 'filetypes', label: 'File Types', icon: FileText }
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setSelectedView(key as any)}
                className={`flex items-center gap-3 px-6 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                  selectedView === key 
                    ? 'bg-white text-blue-600 shadow-sm scale-105' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <MetricCard 
              title="Total Records" 
              value={totals.total.toLocaleString()}
              subtitle="All processed records"
              change={12}
              changeType="positive"
              icon={Database}
              color="primary"
            />
            <MetricCard 
              title="Approved Records" 
              value={totals.approved.toLocaleString()}
              subtitle="Quality approved"
              change={8}
              changeType="positive"
              icon={CheckCircle}
              color="success"
            />
            <MetricCard 
              title="Flagged Records" 
              value={totals.flagged.toLocaleString()}
              subtitle="Requiring review"
              change={-3}
              changeType="negative"
              icon={AlertTriangle}
              color="warning"
            />
            <MetricCard 
              title="Average Quality" 
              value={`${totals.avgQuality}%`}
              subtitle="Overall score"
              change={5}
              changeType="positive"
              icon={Target}
              color="accent"
            />
          </div>

          {/* Dynamic Content Based on Selected View */}
          {selectedView === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <ChartContainer title="Quality Trends Over Time">
                <ResponsiveContainer width="100%" height={350}>
                  <AreaChart data={analyticsData?.qualityTrendData || []}>
                    <defs>
                      <linearGradient id="qualityGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={colors.primary} stopOpacity={0.3}/>
                        <stop offset="95%" stopColor={colors.primary} stopOpacity={0.05}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#666' }} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#666' }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: 'none', 
                        borderRadius: '12px', 
                        boxShadow: '0 4px 20px rgba(0,0,0,0.1)' 
                      }} 
                    />
                    <Area 
                      type="monotone" 
                      dataKey="avgQualityScore" 
                      stroke={colors.primary} 
                      strokeWidth={3}
                      fill="url(#qualityGradient)"
                      name="Quality Score"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </ChartContainer>

              <ChartContainer title="Status Distribution">
                <ResponsiveContainer width="100%" height={350}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Approved', value: totals.approved, fill: colors.success },
                        { name: 'Flagged', value: totals.flagged, fill: colors.warning }
                      ]}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={120}
                      paddingAngle={5}
                      dataKey="value"
                      label={({ name, percent }) => `${name}: ${percent ? (percent * 100).toFixed(1) : 0}%`}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: 'none', 
                        borderRadius: '12px', 
                        boxShadow: '0 4px 20px rgba(0,0,0,0.1)' 
                      }} 
                    />
                  </PieChart>
                </ResponsiveContainer>
              </ChartContainer>
            </div>
          )}

          {selectedView === 'companies' && (
            <div className="space-y-8">
              <ChartContainer title="Company Performance: Approved vs Flagged">
                <ResponsiveContainer width="100%" height={450}>
                  <BarChart data={analyticsData?.companyBreakdown?.slice(0, 10) || []} margin={{ bottom: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis 
                      dataKey="company" 
                      angle={-45} 
                      textAnchor="end" 
                      height={80} 
                      axisLine={false} 
                      tickLine={false}
                      tick={{ fontSize: 12, fill: '#666' }}
                    />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#666' }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: 'none', 
                        borderRadius: '12px', 
                        boxShadow: '0 4px 20px rgba(0,0,0,0.1)' 
                      }} 
                    />
                    <Legend />
                    <Bar dataKey="approved" fill={colors.success} name="Approved" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="flagged" fill={colors.warning} name="Flagged" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartContainer>

              <DataTable
                title="Company Performance Details"
                headers={['Company', 'Total Records', 'Approved', 'Flagged', 'Avg Quality', 'Approval Rate']}
                data={analyticsData?.companyBreakdown?.map((company) => (
                  <tr key={company.company} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-8 py-6 text-sm font-semibold text-gray-900">{company.company}</td>
                    <td className="px-8 py-6 text-sm text-gray-600">{company.totalRecords.toLocaleString()}</td>
                    <td className="px-8 py-6 text-sm font-medium text-green-600">{company.approved.toLocaleString()}</td>
                    <td className="px-8 py-6 text-sm font-medium text-orange-600">{company.flagged.toLocaleString()}</td>
                    <td className="px-8 py-6 text-sm text-gray-900 font-medium">{company.avgQuality}%</td>
                    <td className="px-8 py-6">
                      <div className="flex items-center gap-3">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${company.totalRecords > 0 ? Math.round((company.approved / company.totalRecords) * 100) : 0}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-gray-900">
                          {company.totalRecords > 0 ? Math.round((company.approved / company.totalRecords) * 100) : 0}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              />
            </div>
          )}

          {selectedView === 'connectors' && (
            <div className="space-y-8">
              <ChartContainer title="Connector Reliability & Performance">
                <ResponsiveContainer width="100%" height={450}>
                  <ComposedChart data={analyticsData?.connectorBreakdown || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="connector" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#666' }} />
                    <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#666' }} />
                    <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#666' }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: 'none', 
                        borderRadius: '12px', 
                        boxShadow: '0 4px 20px rgba(0,0,0,0.1)' 
                      }} 
                    />
                    <Legend />
                    <Bar yAxisId="left" dataKey="approved" fill={colors.success} name="Approved" radius={[4, 4, 0, 0]} />
                    <Bar yAxisId="left" dataKey="flagged" fill={colors.warning} name="Flagged" radius={[4, 4, 0, 0]} />
                    <Line yAxisId="right" type="monotone" dataKey="reliability" stroke={colors.accent} strokeWidth={3} name="Reliability %" />
                  </ComposedChart>
                </ResponsiveContainer>
              </ChartContainer>

              <DataTable
                title="Connector Performance Metrics"
                headers={['Connector', 'Total Records', 'Reliability', 'Avg Quality', 'Status']}
                data={analyticsData?.connectorBreakdown?.map((connector) => (
                  <tr key={connector.connector} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-8 py-6 text-sm font-semibold text-gray-900">{connector.connector}</td>
                    <td className="px-8 py-6 text-sm text-gray-600">{connector.totalRecords.toLocaleString()}</td>
                    <td className="px-8 py-6 text-sm font-medium text-gray-900">{connector.reliability}%</td>
                    <td className="px-8 py-6 text-sm font-medium text-gray-900">{connector.avgQuality}%</td>
                    <td className="px-8 py-6">
                      <span className={`inline-flex px-3 py-1.5 text-xs font-semibold rounded-full ${
                        connector.reliability >= 80 ? 'bg-green-100 text-green-800' :
                        connector.reliability >= 60 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {connector.reliability >= 80 ? 'Excellent' : 
                         connector.reliability >= 60 ? 'Good' : 'Needs Improvement'}
                      </span>
                    </td>
                  </tr>
                ))}
              />
            </div>
          )}

          {selectedView === 'tags' && (
            <div className="space-y-8">
              <ChartContainer title="Tag Relevancy Analysis">
                <div className="mb-6">
                  <p className="text-sm text-gray-600">
                    Frequency vs Quality correlation analysis. Higher relevancy scores indicate more consistent quality across usage patterns.
                  </p>
                </div>
                <ResponsiveContainer width="100%" height={450}>
                  <ScatterChart data={analyticsData?.tagAnalytics || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis 
                      dataKey="frequency" 
                      name="Frequency" 
                      axisLine={false} 
                      tickLine={false}
                      tick={{ fontSize: 12, fill: '#666' }}
                    />
                    <YAxis 
                      dataKey="avgQuality" 
                      name="Avg Quality" 
                      axisLine={false} 
                      tickLine={false}
                      tick={{ fontSize: 12, fill: '#666' }}
                    />
                    <Tooltip 
                      cursor={{ strokeDasharray: '3 3' }}
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: 'none', 
                        borderRadius: '12px', 
                        boxShadow: '0 4px 20px rgba(0,0,0,0.1)' 
                      }}
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="bg-white p-4 border border-gray-200 rounded-xl shadow-lg">
                              <p className="font-semibold text-gray-900 mb-2">{data.tag}</p>
                              <div className="space-y-1 text-sm">
                                <p>Frequency: <span className="font-medium">{data.frequency}</span></p>
                                <p>Avg Quality: <span className="font-medium">{data.avgQuality}%</span></p>
                                <p>Relevancy: <span className="font-medium">{data.relevancyScore}%</span></p>
                              </div>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Scatter dataKey="avgQuality" fill={colors.primary} />
                  </ScatterChart>
                </ResponsiveContainer>
              </ChartContainer>

              <DataTable
                title="Tag Performance Rankings"
                headers={['Rank', 'Tag', 'Frequency', 'Avg Quality', 'Relevancy Score', 'Usage Level']}
                data={analyticsData?.tagAnalytics?.map((tag, index) => (
                  <tr key={tag.tag} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-8 py-6 text-sm font-semibold text-gray-900">#{index + 1}</td>
                    <td className="px-8 py-6 text-sm font-semibold text-gray-900">{tag.tag}</td>
                    <td className="px-8 py-6 text-sm text-gray-600">{tag.frequency.toLocaleString()}</td>
                    <td className="px-8 py-6 text-sm font-medium text-gray-900">{tag.avgQuality}%</td>
                    <td className="px-8 py-6 text-sm font-medium text-gray-900">{tag.relevancyScore}%</td>
                    <td className="px-8 py-6">
                      <span className={`inline-flex px-3 py-1.5 text-xs font-semibold rounded-full ${
                        tag.usage === 'high' ? 'bg-green-100 text-green-800' :
                        tag.usage === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {tag.usage.charAt(0).toUpperCase() + tag.usage.slice(1)}
                      </span>
                    </td>
                  </tr>
                ))}
              />
            </div>
          )}

          {selectedView === 'quality' && (
            <div className="space-y-8">
              <ChartContainer title="Quality Score Distribution">
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={analyticsData?.qualityDistribution || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="range" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#666' }} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#666' }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: 'none', 
                        borderRadius: '12px', 
                        boxShadow: '0 4px 20px rgba(0,0,0,0.1)' 
                      }} 
                    />
                    <Bar dataKey="count" fill={colors.primary} radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartContainer>

              <DataTable
                title="Top Quality Issues"
                headers={['Rank', 'Issue', 'Count', 'Severity', 'Affected Companies']}
                data={analyticsData?.topIssues?.map((issue, index) => (
                  <tr key={issue.issue} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-8 py-6 text-sm font-semibold text-gray-900">#{index + 1}</td>
                    <td className="px-8 py-6 text-sm font-semibold text-gray-900">{issue.issue}</td>
                    <td className="px-8 py-6 text-sm text-gray-600">{issue.count.toLocaleString()}</td>
                    <td className="px-8 py-6">
                      <span className={`inline-flex px-3 py-1.5 text-xs font-semibold rounded-full ${
                        issue.severity === 'critical' ? 'bg-red-100 text-red-800' :
                        issue.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                        issue.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {issue.severity.charAt(0).toUpperCase() + issue.severity.slice(1)}
                      </span>
                    </td>
                    <td className="px-8 py-6 text-sm text-gray-600">{issue.affectedCompanies}</td>
                  </tr>
                ))}
              />
            </div>
          )}

          {selectedView === 'filetypes' && (
            <div className="space-y-8">
              {/* Enterprise File Type Insights */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Modern Donut Chart */}
                <div className="lg:col-span-2">
                  <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-8">
                    <div className="flex items-center justify-between mb-8">
                      <div>
                        <h3 className="text-2xl font-bold text-gray-900 mb-2">File Type Distribution</h3>
                        <p className="text-gray-600">Document format breakdown across your knowledge base</p>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        Total: {analyticsData?.fileTypeData?.reduce((sum, item) => sum + item.count, 0) || 0} documents
                      </div>
                    </div>

                    <div className="relative">
                      <ResponsiveContainer width="100%" height={350}>
                        <PieChart>
                          <Pie
                            data={analyticsData?.fileTypeData || []}
                            cx="50%"
                            cy="50%"
                            innerRadius={70}
                            outerRadius={140}
                            paddingAngle={4}
                            dataKey="count"
                          >
                            {(analyticsData?.fileTypeData || []).map((entry, index) => {
                              const appleColors = [
                                '#007AFF', // Blue
                                '#34C759', // Green  
                                '#FF9500', // Orange
                                '#FF3B30', // Red
                                '#5856D6', // Purple
                                '#FF2D92', // Pink
                                '#64D2FF', // Light Blue
                                '#32D74B'  // Light Green
                              ];
                              return (
                                <Cell 
                                  key={`cell-${index}`} 
                                  fill={appleColors[index % appleColors.length]}
                                  stroke="white"
                                  strokeWidth={3}
                                />
                              )
                            })}
                          </Pie>
                          <Tooltip 
                            contentStyle={{ 
                              backgroundColor: 'rgba(255, 255, 255, 0.98)', 
                              border: 'none', 
                              borderRadius: '16px', 
                              boxShadow: '0 20px 40px rgba(0,0,0,0.15)',
                              backdropFilter: 'blur(20px)'
                            }}
                            content={({ active, payload }) => {
                              if (active && payload && payload.length) {
                                const data = payload[0].payload;
                                const total = analyticsData?.fileTypeData?.reduce((sum, item) => sum + item.count, 0) || 1;
                                const percentage = ((data.count / total) * 100).toFixed(1);
                                return (
                                  <div className="bg-white/95 backdrop-blur-xl p-4 border border-gray-100 rounded-2xl shadow-xl">
                                    <div className="flex items-center gap-3 mb-3">
                                      <div 
                                        className="w-4 h-4 rounded-full"
                                        style={{ backgroundColor: payload[0].fill }}
                                      ></div>
                                      <p className="font-semibold text-gray-900">{data.fileType}</p>
                                    </div>
                                    <div className="space-y-2 text-sm">
                                      <div className="flex justify-between items-center">
                                        <span className="text-gray-600">Documents:</span>
                                        <span className="font-semibold">{data.count.toLocaleString()}</span>
                                      </div>
                                      <div className="flex justify-between items-center">
                                        <span className="text-gray-600">Percentage:</span>
                                        <span className="font-semibold">{percentage}%</span>
                                      </div>
                                      <div className="flex justify-between items-center">
                                        <span className="text-gray-600">Avg Quality:</span>
                                        <span className="font-semibold">{data.avgQuality}%</span>
                                      </div>
                                      <div className="flex justify-between items-center">
                                        <span className="text-gray-600">Success Rate:</span>
                                        <span className={`font-semibold ${
                                          data.successRate >= 90 ? 'text-green-600' :
                                          data.successRate >= 80 ? 'text-yellow-600' :
                                          'text-red-600'
                                        }`}>{data.successRate}%</span>
                                      </div>
                                    </div>
                                  </div>
                                );
                              }
                              return null;
                            }}
                          />
                        </PieChart>
                      </ResponsiveContainer>

                      {/* Center Label */}
                      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <div className="text-center">
                          <div className="text-3xl font-bold text-gray-900">
                            {analyticsData?.fileTypeData?.length || 0}
                          </div>
                          <div className="text-sm text-gray-500 font-medium">File Types</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Modern Legend & Insights */}
                <div className="space-y-6">
                  {/* Custom Legend */}
                  <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-6">
                    <h4 className="text-lg font-bold text-gray-900 mb-4">File Types</h4>
                    <div className="space-y-4">
                      {(analyticsData?.fileTypeData || []).map((item, index) => {
                        const appleColors = [
                          '#007AFF', '#34C759', '#FF9500', '#FF3B30', 
                          '#5856D6', '#FF2D92', '#64D2FF', '#32D74B'
                        ];
                        const total = analyticsData?.fileTypeData?.reduce((sum, i) => sum + i.count, 0) || 1;
                        const percentage = ((item.count / total) * 100).toFixed(1);
                        
                        return (
                          <div key={item.fileType} className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div 
                                className="w-4 h-4 rounded-full shadow-sm"
                                style={{ backgroundColor: appleColors[index % appleColors.length] }}
                              ></div>
                              <div>
                                <div className="font-semibold text-gray-900 text-sm">{item.fileType}</div>
                                <div className="text-xs text-gray-500">{item.count.toLocaleString()} documents</div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="font-bold text-gray-900 text-sm">{percentage}%</div>
                              <div className="text-xs text-gray-500">{item.avgQuality}% quality</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Quality Insights */}
                  <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-3xl border border-blue-100 p-6">
                    <h4 className="text-lg font-bold text-gray-900 mb-4">Quality Insights</h4>
                    <div className="space-y-3">
                                             {(() => {
                         const fileTypes = analyticsData?.fileTypeData || [];
                         if (fileTypes.length === 0) return null;
                         
                         const bestType = fileTypes.reduce((best, current) => 
                           current.avgQuality > best.avgQuality ? current : best);
                         const worstType = fileTypes.reduce((worst, current) => 
                           current.avgQuality < worst.avgQuality ? current : worst);
                         
                         return (
                           <>
                             {bestType && (
                              <div className="flex items-center gap-3 p-3 bg-white/60 rounded-xl">
                                <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                                  <CheckCircle className="w-4 h-4 text-green-600" />
                                </div>
                                <div>
                                  <div className="text-sm font-semibold text-gray-900">Best Performing</div>
                                  <div className="text-xs text-gray-600">{bestType.fileType} - {bestType.avgQuality}% avg quality</div>
                                </div>
                              </div>
                            )}
                            {worstType && (
                              <div className="flex items-center gap-3 p-3 bg-white/60 rounded-xl">
                                <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center">
                                  <AlertTriangle className="w-4 h-4 text-orange-600" />
                                </div>
                                <div>
                                  <div className="text-sm font-semibold text-gray-900">Needs Attention</div>
                                  <div className="text-xs text-gray-600">{worstType.fileType} - {worstType.avgQuality}% avg quality</div>
                                </div>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </div>
                </div>
              </div>

              {/* Enhanced Performance Table */}
              <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="px-8 py-6 border-b border-gray-100">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xl font-bold text-gray-900">File Type Performance Analytics</h3>
                      <p className="text-gray-600 mt-1">Detailed quality metrics and processing insights</p>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Database className="w-4 h-4" />
                      Enterprise Analytics
                    </div>
                  </div>
                </div>
                
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50/50">
                      <tr>
                        <th className="px-8 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">File Type</th>
                        <th className="px-8 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Volume</th>
                        <th className="px-8 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Quality Score</th>
                        <th className="px-8 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Success Rate</th>
                        <th className="px-8 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Issues</th>
                        <th className="px-8 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Health</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {(analyticsData?.fileTypeData || []).map((fileType, index) => {
                        const appleColors = [
                          '#007AFF', '#34C759', '#FF9500', '#FF3B30', 
                          '#5856D6', '#FF2D92', '#64D2FF', '#32D74B'
                        ];
                        const total = analyticsData?.fileTypeData?.reduce((sum, item) => sum + item.count, 0) || 1;
                        const percentage = ((fileType.count / total) * 100).toFixed(1);
                        
                        return (
                          <tr key={fileType.fileType} className="hover:bg-gray-50/30 transition-all duration-200">
                            <td className="px-8 py-6">
                              <div className="flex items-center gap-4">
                                <div 
                                  className="w-6 h-6 rounded-lg shadow-sm flex items-center justify-center"
                                  style={{ backgroundColor: `${appleColors[index % appleColors.length]}15` }}
                                >
                                  <div 
                                    className="w-3 h-3 rounded-full"
                                    style={{ backgroundColor: appleColors[index % appleColors.length] }}
                                  ></div>
                                </div>
                                <div>
                                  <div className="font-bold text-gray-900">{fileType.fileType}</div>
                                  <div className="text-sm text-gray-500">{percentage}% of total</div>
                                </div>
                              </div>
                            </td>
                            <td className="px-8 py-6">
                              <div className="flex items-center gap-3">
                                <div className="text-xl font-bold text-gray-900">{fileType.count.toLocaleString()}</div>
                                <div className="text-sm text-gray-500">documents</div>
                              </div>
                            </td>
                            <td className="px-8 py-6">
                              <div className="flex items-center gap-3">
                                <div className="text-lg font-bold text-gray-900">{fileType.avgQuality}%</div>
                                <div className={`w-12 h-2 rounded-full ${
                                  fileType.avgQuality >= 80 ? 'bg-green-200' :
                                  fileType.avgQuality >= 60 ? 'bg-yellow-200' : 'bg-red-200'
                                }`}>
                                  <div 
                                    className={`h-2 rounded-full ${
                                      fileType.avgQuality >= 80 ? 'bg-green-500' :
                                      fileType.avgQuality >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                                    }`}
                                    style={{ width: `${fileType.avgQuality}%` }}
                                  ></div>
                                </div>
                              </div>
                            </td>
                            <td className="px-8 py-6">
                              <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold ${
                                fileType.successRate >= 90 ? 'bg-green-100 text-green-800' :
                                fileType.successRate >= 80 ? 'bg-yellow-100 text-yellow-800' :
                                'bg-red-100 text-red-800'
                              }`}>
                                {fileType.successRate >= 90 ? <CheckCircle className="w-4 h-4" /> :
                                 fileType.successRate >= 80 ? <Clock className="w-4 h-4" /> :
                                 <XCircle className="w-4 h-4" />}
                                {fileType.successRate}%
                              </div>
                            </td>
                            <td className="px-8 py-6">
                              <div className="flex items-center gap-2">
                                <span className="text-lg font-bold text-gray-900">{fileType.issues}</span>
                                <span className="text-sm text-gray-500">issues</span>
                              </div>
                            </td>
                            <td className="px-8 py-6">
                              <div className={`flex items-center gap-2 ${
                                fileType.successRate >= 90 && fileType.avgQuality >= 80 ? 'text-green-600' :
                                fileType.successRate >= 80 && fileType.avgQuality >= 60 ? 'text-yellow-600' :
                                'text-red-600'
                              }`}>
                                {fileType.successRate >= 90 && fileType.avgQuality >= 80 ? (
                                  <>
                                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                                    <span className="text-sm font-semibold">Excellent</span>
                                  </>
                                ) : fileType.successRate >= 80 && fileType.avgQuality >= 60 ? (
                                  <>
                                    <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                                    <span className="text-sm font-semibold">Good</span>
                                  </>
                                ) : (
                                  <>
                                    <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                                    <span className="text-sm font-semibold">Needs Work</span>
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-2xl p-6">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-red-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-red-900 mb-2">Analytics Error</h3>
                  <p className="text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
} 