// Core Data Types
export interface QualityRecord {
  id: string
  recordId: string
  companyId: string
  companyName: string
  sourceConnectorName: string
  sourceConnectorType: string
  content: string
  contentPreview: string
  tags: string[]
  status: 'pending' | 'approved' | 'flagged' | 'under_review' | 'rejected'
  qualityScore: number
  confidenceScore: number
  llm_confidence?: number
  rules_engine_confidence?: number
  issues: QualityIssue[]
  metadata: Record<string, any>
  createdAt: string
  updatedAt: string
  priority: 'low' | 'medium' | 'high' | 'critical'
  reviewedAt?: string
  reviewedBy?: string
  llmSuggestions?: string[]
  llmReasoning?: string
  trace_id?: string
  processingTimeMs?: number
  quality_checks?: QualityCheck[]; // Add this line for backend compatibility
}

export interface QualityIssue {
  id: string
  type: 'generic_tags' | 'content_quality' | 'missing_context' | 'pii_detected' | 'duplicate_content' | 'spam_detected' | 'stopwords_detection' | 'tag_validation' | 'llm_semantic_validation' | 'text_quality' | 'spam_pattern_detection' | 'duplicate_content_detection' | 'tag_text_relevance' | 'empty_tags' | 'tag_count_validation' | 'semantic_relevance' | 'domain_relevance' | 'context_coherence' | 'tag_specificity'
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  suggestion?: string
  autoFixable: boolean
  category: 'content' | 'tags' | 'metadata' | 'compliance' | 'llm'
  confidence?: number
  record: QualityRecord  // Full record associated with this issue
  
  // Additional fields for detailed quality check information
  reasoning?: string  // LLM reasoning for the decision
  issues?: Array<{tag: string; problem: string}>  // List of specific issues found
  llm_assessment?: string  // LLM's overall assessment
  llm_reasoning?: string  // LLM's detailed reasoning
  issues_found?: number  // Number of issues found
  processing_time_ms?: number  // Processing time for this check
}

export interface RecordMetadata {
  author?: string
  department?: string
  documentType?: string
  lastModified?: string
  fileSize?: number
  language?: string
  wordCount?: number
  readingLevel?: string
  sensitivity?: 'public' | 'internal' | 'confidential' | 'restricted'
}

// Dashboard Metrics
export interface DashboardMetrics {
  totalRecords: number
  todaysRecords: number
  avgQualityScore: number
  qualityTrend: number // percentage change
  issuesCount: number
  criticalIssues: number
  activeSources: number
  companiesCount: number
  processingRate: number // records per hour
  systemHealth: 'healthy' | 'warning' | 'critical'
  costMetrics: {
    dailyCost: number
    monthlyBudget: number
    budgetUsed: number
  }
}

export interface QualityTrend {
  date: string
  qualityScore: number
  recordsProcessed: number
  issuesFound: number
}

export interface SourceMetrics {
  connectorId: string
  connectorName: string
  recordsProcessed: number
  avgQualityScore: number
  issuesCount: number
  lastSync: string
  healthStatus: 'healthy' | 'warning' | 'error' | 'disconnected'
}

// Filtering and Pagination
export interface DashboardFilters {
  companies: string[] // company IDs
  sourceConnectors: string[] // connector IDs  
  statuses: QualityRecord['status'][]
  priorities: QualityRecord['priority'][]
  issueTypes: QualityIssue['type'][]
  qualityScoreRange: [number, number]
  dateRange: {
    from: string
    to: string
  }
  searchQuery: string
  tags: string[]
  departments: string[]
  authors: string[]
}

export interface PaginationParams {
  page: number
  pageSize: number
  sortBy?: keyof QualityRecord
  sortOrder: 'asc' | 'desc'
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: {
    page: number
    pageSize: number
    total: number
    totalPages: number
    hasNext: boolean
    hasPrev: boolean
  }
  filters: DashboardFilters
  appliedFiltersCount: number
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean
  data: T
  message?: string
  error?: string
  timestamp: string
}

export interface HealthResponse {
  status: 'healthy' | 'warning' | 'critical'
  services: {
    database: 'up' | 'down'
    llm: 'up' | 'down' | 'degraded'
    storage: 'up' | 'down'
  }
  version: string
  uptime: number
}

// Review and Actions
export interface ReviewDecision {
  recordId: string
  decision: 'approve' | 'reject' | 'needs_revision'
  comments: string
  tags?: string[] // updated tags if revision
  priority?: QualityRecord['priority']
  assignTo?: string
  timestamp: string
}

export interface BulkAction {
  type: 'approve' | 'reject' | 'assign' | 'tag' | 'export'
  recordIds: string[]
  parameters?: Record<string, any>
  reason?: string
}

export interface ReviewWorkflow {
  id: string
  recordId: string
  currentStage: 'quality_check' | 'human_review' | 'final_approval' | 'completed'
  assignedTo?: string
  history: ReviewHistoryEntry[]
  slaDeadline?: string
  escalated: boolean
}

export interface ReviewHistoryEntry {
  id: string
  action: string
  performedBy: string
  timestamp: string
  comments?: string
  fromStage?: string
  toStage?: string
  metadata?: Record<string, any>
}

export interface ExportRequest {
  format: 'csv' | 'excel' | 'json' | 'pdf'
  filters: Partial<DashboardFilters>
  columns: string[]
  includeMetadata: boolean
  dateRange?: {
    from: string
    to: string
  }
}

export interface Report {
  id: string
  title: string
  type: 'quality_summary' | 'compliance' | 'performance' | 'cost_analysis'
  schedule: 'once' | 'daily' | 'weekly' | 'monthly'
  recipients: string[]
  lastGenerated?: string
  nextGeneration?: string
  isActive: boolean
}

export interface QualityInsights {
  topIssueTypes: Array<{
    type: QualityIssue['type']
    count: number
    trend: number
  }>
  qualityBySource: Array<{
    sourceId: string
    sourceName: string
    avgQuality: number
    trend: number
  }>
  qualityByCompany: Array<{
    companyId: string
    companyName: string
    avgQuality: number
    recordsCount: number
  }>
  tagsAnalysis: Array<{
    tag: string
    frequency: number
    avgQuality: number
    isImproving: boolean
  }>
  recommendations: Array<{
    type: 'threshold_adjustment' | 'connector_optimization' | 'tag_standardization'
    priority: 'low' | 'medium' | 'high'
    description: string
    impact: string
    actionRequired: string
  }>
}

// UI Components
export interface TableColumn {
  id: string
  label: string
  sortable: boolean
  filterable: boolean
  width?: number
  minWidth?: number
  sticky?: boolean
  type: 'text' | 'number' | 'date' | 'status' | 'tags' | 'actions'
}

export interface FilterConfig {
  type: 'select' | 'multiselect' | 'range' | 'date' | 'search' | 'tags'
  label: string
  placeholder?: string
  options?: Array<{ label: string; value: string }>
  min?: number
  max?: number
  multiple?: boolean
}

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  timestamp: string
  read: boolean
  actionUrl?: string
  actionLabel?: string
  priority: 'low' | 'normal' | 'high'
  category: 'system' | 'quality' | 'review' | 'compliance'
}

export interface ApiError {
  code: string
  message: string
  details?: Record<string, any>
  timestamp: string
  requestId?: string
}

export interface ValidationError {
  field: string
  message: string
  code: string
} 

// Add a minimal QualityCheck type if not present
export interface QualityCheck {
  check_name?: string;
  type?: string;
  status?: string;
  confidence_score?: number;
  confidence?: number;
  description?: string;
  suggestion?: string;
  category?: string;
  [key: string]: any;
} 