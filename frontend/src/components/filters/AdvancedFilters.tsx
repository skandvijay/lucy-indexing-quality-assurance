'use client'

import React, { useState, useEffect, useRef } from 'react'
import { 
  Filter, 
  X, 
  ChevronDown, 
  Calendar, 
  Search,
  Building,
  Database,
  AlertTriangle,
  Tag,
  User,
  Briefcase,
  RotateCcw
} from 'lucide-react'
import { DashboardFilters } from '@/types'
import { cn, countAppliedFilters, formatDate } from '@/lib/utils'
import { apiClient } from '@/app/api'

interface FilterOption {
  value: string
  label: string
  count?: number
  icon?: React.ComponentType<any>
}

interface AdvancedFiltersProps {
  filters: Partial<DashboardFilters>
  onFiltersChange: (filters: Partial<DashboardFilters>) => void
  onReset: () => void
  className?: string
}

interface MultiSelectProps {
  options: FilterOption[]
  selected: string[]
  onChange: (values: string[]) => void
  placeholder: string
  icon?: React.ComponentType<any>
  loading?: boolean
}

function MultiSelect({ options, selected, onChange, placeholder, icon: Icon, loading }: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const filteredOptions = options.filter(option =>
    typeof option?.label === 'string' &&
    option.label.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const toggleOption = (value: string) => {
    const newSelected = selected.includes(value)
      ? selected.filter(v => v !== value)
      : [...selected, value]
    onChange(newSelected)
  }

  const selectedLabels = selected.map(value => 
    options.find(opt => opt.value === value)?.label || value
  )

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "relative w-full rounded-md border border-gray-300 bg-white pl-3 pr-10 py-2 text-left shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 sm:text-sm",
          selected.length > 0 && "border-blue-300 bg-blue-50"
        )}
      >
        <div className="flex items-center">
          {Icon && <Icon className="h-4 w-4 text-gray-400 mr-2" />}
          <span className="block truncate">
            {selected.length === 0 
              ? placeholder
              : selected.length === 1
              ? selectedLabels[0]
              : `${selected.length} selected`
            }
          </span>
        </div>
        <span className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
          <ChevronDown className="h-4 w-4 text-gray-400" />
        </span>
      </button>

      {isOpen && (
        <div className="absolute z-10 mt-1 w-full bg-white shadow-lg max-h-60 rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 overflow-auto focus:outline-none sm:text-sm">
          {/* Search input */}
          <div className="sticky top-0 bg-white px-3 py-2 border-b border-gray-200">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search options..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {loading ? (
            <div className="px-3 py-2 text-sm text-gray-500">Loading...</div>
          ) : filteredOptions.length === 0 ? (
            <div className="px-3 py-2 text-sm text-gray-500">No options found</div>
          ) : (
            filteredOptions.map((option) => (
              <label
                key={option.value}
                className="flex items-center px-3 py-2 hover:bg-gray-100 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(option.value)}
                  onChange={() => toggleOption(option.value)}
                  className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <div className="ml-3 flex items-center justify-between w-full">
                  <div className="flex items-center">
                    {option.icon && <option.icon className="h-4 w-4 text-gray-400 mr-2" />}
                    <span className="text-sm text-gray-900">{option.label}</span>
                  </div>
                  {option.count !== undefined && (
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                      {option.count}
                    </span>
                  )}
                </div>
              </label>
            ))
          )}
        </div>
      )}
    </div>
  )
}

interface DateRangePickerProps {
  value: { from?: string; to?: string }
  onChange: (range: { from?: string; to?: string }) => void
}

function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const formatDateRange = () => {
    if (!value.from && !value.to) return 'Select date range'
    if (value.from && !value.to) return `From ${formatDate(value.from)}`
    if (!value.from && value.to) return `To ${formatDate(value.to)}`
    return `${formatDate(value.from!)} - ${formatDate(value.to!)}`
  }

  const presets = [
    { label: 'Today', getValue: () => {
      const today = new Date().toISOString().split('T')[0]
      return { from: today, to: today }
    }},
    { label: 'Yesterday', getValue: () => {
      const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      return { from: yesterday, to: yesterday }
    }},
    { label: 'Last 7 days', getValue: () => {
      const today = new Date().toISOString().split('T')[0]
      const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      return { from: weekAgo, to: today }
    }},
    { label: 'Last 30 days', getValue: () => {
      const today = new Date().toISOString().split('T')[0]
      const monthAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      return { from: monthAgo, to: today }
    }},
    { label: 'This month', getValue: () => {
      const now = new Date()
      const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0]
      const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0]
      return { from: firstDay, to: lastDay }
    }}
  ]

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "relative w-full rounded-md border border-gray-300 bg-white pl-3 pr-10 py-2 text-left shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 sm:text-sm",
          (value.from || value.to) && "border-blue-300 bg-blue-50"
        )}
      >
        <div className="flex items-center">
          <Calendar className="h-4 w-4 text-gray-400 mr-2" />
          <span className="block truncate text-sm">{formatDateRange()}</span>
        </div>
        <span className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
          <ChevronDown className="h-4 w-4 text-gray-400" />
        </span>
      </button>

      {isOpen && (
        <div className="absolute z-10 mt-1 w-80 bg-white shadow-lg rounded-md py-2 ring-1 ring-black ring-opacity-5">
          <div className="px-3 py-2 border-b border-gray-200">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Quick Presets</h4>
            <div className="grid grid-cols-2 gap-2">
              {presets.map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => {
                    onChange(preset.getValue())
                    setIsOpen(false)
                  }}
                  className="text-left px-2 py-1 text-xs bg-gray-50 hover:bg-gray-100 rounded"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>
          
          <div className="px-3 py-2">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Custom Range</h4>
            <div className="space-y-2">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">From</label>
                <input
                  type="date"
                  value={value.from || ''}
                  onChange={(e) => onChange({ ...value, from: e.target.value })}
                  className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">To</label>
                <input
                  type="date"
                  value={value.to || ''}
                  onChange={(e) => onChange({ ...value, to: e.target.value })}
                  className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function AdvancedFilters({ filters, onFiltersChange, onReset, className }: AdvancedFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [loading, setLoading] = useState({ companies: false, connectors: false })
  const [filterOptions, setFilterOptions] = useState<{
    companies: Array<{ value: string; label: string }>
    connectors: Array<{ value: string; label: string }>
    statuses: Array<{ value: string; label: string }>
    priorities: Array<{ value: string; label: string; count: number }>
    issueTypes: Array<{ value: string; label: string; count: number }>
    tags: Array<{ value: string; label: string }>
  }>({
    companies: [],
    connectors: [],
    statuses: [],
    priorities: [],
    issueTypes: [],
    tags: []
  })

  useEffect(() => {
    const fetchFilterOptions = async () => {
      try {
        setLoading({ companies: true, connectors: true })
        
        // Fetch all filter options from the new API method
        const options = await apiClient.getFilterOptions();
        setFilterOptions({
          companies: (options.companies || []).map((c: any) => ({ 
            value: c.value || c.label || c, 
            label: c.label || c.value || c 
          })),
          connectors: (options.connectors || []).map((c: any) => ({ 
            value: c.value || c.label || c, 
            label: c.label || c.value || c 
          })),
          statuses: (options.statuses || []).map((s: any) => ({ 
            value: s.value || s.label || s, 
            label: s.label || s.value || s 
          })),
          priorities: (options.priorities || []).map((p: any) => ({ 
            value: p.value || p.label || p, 
            label: p.label || p.value || p,
            count: p.count || 0
          })),
          issueTypes: (options.issue_types || []).map((i: any) => ({ 
            value: i.value || i.label || i, 
            label: i.label || i.value || i,
            count: i.count || 0
          })),
          tags: (options.tags || []).map((t: any) => ({ 
            value: t.value || t.label || t, 
            label: t.label || t.value || t 
          })),
        });
      } catch (error) {
        console.error('Failed to fetch filter options:', error)
        // Set fallback data with correct structure
        setFilterOptions({
          companies: [
            { value: 'Unknown Company', label: 'Unknown Company' }
          ],
          connectors: [
            { value: 'SharePoint', label: 'SharePoint' },
            { value: 'Confluence', label: 'Confluence' },
            { value: 'Notion', label: 'Notion' },
            { value: 'GDrive', label: 'Google Drive' }
          ],
          statuses: [
            { value: 'pending', label: 'Pending' },
            { value: 'approved', label: 'Approved' },
            { value: 'flagged', label: 'Flagged' },
            { value: 'rejected', label: 'Rejected' },
            { value: 'under_review', label: 'Under Review' }
          ],
          priorities: [
            { value: 'low', label: 'Low', count: 0 },
            { value: 'medium', label: 'Medium', count: 0 },
            { value: 'high', label: 'High', count: 0 },
            { value: 'critical', label: 'Critical', count: 0 }
          ],
          issueTypes: [
            { value: 'generic_tags', label: 'Generic Tags', count: 0 },
            { value: 'content_quality', label: 'Content Quality', count: 0 },
            { value: 'missing_context', label: 'Missing Context', count: 0 }
          ],
          tags: []
        })
      } finally {
        setLoading({ companies: false, connectors: false })
      }
    }

    fetchFilterOptions()
  }, [])

  const appliedFiltersCount = countAppliedFilters(filters)

  const statusOptions: FilterOption[] = filterOptions.statuses.map(status => ({
    value: status.value,
    label: status.label,
    count: (status as any).count
  }))

  const priorityOptions: FilterOption[] = filterOptions.priorities.map(priority => ({
    value: priority.value,
    label: priority.label,
    count: priority.count
  }))

  const issueTypeOptions: FilterOption[] = filterOptions.issueTypes.map(issueType => ({
    value: issueType.value,
    label: issueType.label,
    count: issueType.count
  }))

  const companyOptions: FilterOption[] = filterOptions.companies.map(company => ({
    value: company.value,
    label: company.label,
    icon: Building,
    count: (company as any).count
  }))

  const connectorOptions: FilterOption[] = filterOptions.connectors.map(connector => ({
    value: connector.value,
    label: connector.label,
    icon: Database,
    count: (connector as any).count
  }))

  const updateFilters = (key: keyof DashboardFilters, value: any) => {
    onFiltersChange({ ...filters, [key]: value })
  }

  return (
    <div className={cn("bg-white rounded-lg shadow-sm border border-gray-200 p-4", className)}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <Filter className="h-5 w-5 text-gray-400" />
          <h3 className="text-lg font-medium text-gray-900">Filters</h3>
          {appliedFiltersCount > 0 && (
            <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
              {appliedFiltersCount} applied
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={onReset}
            disabled={appliedFiltersCount === 0}
            className="flex items-center space-x-1 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RotateCcw className="h-4 w-4" />
            <span>Reset</span>
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center space-x-1 px-3 py-1.5 text-sm text-blue-600 hover:text-blue-700"
          >
            <span>{isExpanded ? 'Collapse' : 'Expand'}</span>
            <ChevronDown className={cn("h-4 w-4 transition-transform", isExpanded && "rotate-180")} />
          </button>
        </div>
      </div>

      {/* Search input */}
      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search records by content, author, or metadata..."
            value={filters.searchQuery || ''}
            onChange={(e) => updateFilters('searchQuery', e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>

      {/* Main filters */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <MultiSelect
          options={companyOptions}
          selected={filters.companies || []}
          onChange={(values) => updateFilters('companies', values)}
          placeholder="All Companies"
          icon={Building}
          loading={loading.companies}
        />

        <MultiSelect
          options={connectorOptions}
          selected={filters.sourceConnectors || []}
          onChange={(values) => updateFilters('sourceConnectors', values)}
          placeholder="All Sources"
          icon={Database}
          loading={loading.connectors}
        />

        <MultiSelect
          options={statusOptions}
          selected={filters.statuses || []}
          onChange={(values) => updateFilters('statuses', values)}
          placeholder="All Statuses"
          icon={AlertTriangle}
        />

        <DateRangePicker
          value={filters.dateRange || {}}
          onChange={(range) => updateFilters('dateRange', range)}
        />
      </div>

      {/* Expanded filters */}
      {isExpanded && (
        <div className="space-y-4 border-t border-gray-200 pt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <MultiSelect
              options={priorityOptions}
              selected={filters.priorities || []}
              onChange={(values) => updateFilters('priorities', values)}
              placeholder="All Priorities"
              icon={AlertTriangle}
            />

            <MultiSelect
              options={issueTypeOptions}
              selected={filters.issueTypes || []}
              onChange={(values) => updateFilters('issueTypes', values)}
              placeholder="All Issue Types"
              icon={Tag}
            />

            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">Quality Score Range</label>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  min="0"
                  max="100"
                  placeholder="Min"
                  value={filters.qualityScoreRange?.[0] || ''}
                  onChange={(e) => {
                    const min = Number(e.target.value) || 0
                    const max = filters.qualityScoreRange?.[1] || 100
                    updateFilters('qualityScoreRange', [min, max])
                  }}
                  className="w-20 px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
                <span className="text-gray-500">-</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  placeholder="Max"
                  value={filters.qualityScoreRange?.[1] || ''}
                  onChange={(e) => {
                    const max = Number(e.target.value) || 100
                    const min = filters.qualityScoreRange?.[0] || 0
                    updateFilters('qualityScoreRange', [min, max])
                  }}
                  className="w-20 px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Additional text filters */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Authors</label>
              <input
                type="text"
                placeholder="Filter by author names (comma separated)"
                value={filters.authors?.join(', ') || ''}
                onChange={(e) => {
                  const authors = e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                  updateFilters('authors', authors)
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Departments</label>
              <input
                type="text"
                placeholder="Filter by departments (comma separated)"
                value={filters.departments?.join(', ') || ''}
                onChange={(e) => {
                  const departments = e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                  updateFilters('departments', departments)
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tags</label>
              <input
                type="text"
                placeholder="Filter by tags (comma separated)"
                value={filters.tags?.join(', ') || ''}
                onChange={(e) => {
                  const tags = e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                  updateFilters('tags', tags)
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>
      )}

      {/* Applied filters summary */}
      {appliedFiltersCount > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex flex-wrap gap-2">
            {filters.searchQuery && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Search: "{filters.searchQuery}"
                <button
                  onClick={() => updateFilters('searchQuery', '')}
                  className="ml-1.5 h-3 w-3 text-blue-400 hover:text-blue-600"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            )}
            {filters.companies?.map(companyId => {
              const company = filterOptions.companies.find(c => c.value === companyId)
              return (
                <span key={companyId} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  Company: {company?.label || companyId}
                  <button
                    onClick={() => updateFilters('companies', filters.companies?.filter(id => id !== companyId))}
                    className="ml-1.5 h-3 w-3 text-green-400 hover:text-green-600"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              )
            })}
            {(filters.qualityScoreRange && (filters.qualityScoreRange[0] > 0 || filters.qualityScoreRange[1] < 100)) && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                Quality: {filters.qualityScoreRange[0]}-{filters.qualityScoreRange[1]}%
                <button
                  onClick={() => updateFilters('qualityScoreRange', undefined)}
                  className="ml-1.5 h-3 w-3 text-purple-400 hover:text-purple-600"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
} 