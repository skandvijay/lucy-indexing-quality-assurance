// API client for connecting to the Indexing QA backend

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export interface ChunkIngestRequest {
  record_id: string;
  document_text: string;
  tags: string[];
  source_connector: 'SharePoint' | 'Confluence' | 'Notion' | 'GDrive';
  file_id: string;
  created_at?: string;
}

export interface QualityCheckResult {
  check_name: string;
  status: 'pass' | 'fail' | 'pending_review';
  confidence_score: number;
  failure_reason?: string;
  check_metadata?: Record<string, any>;
  
  // Additional fields for detailed quality check information
  type?: string;  // e.g., "stopwords detection", "tag validation", "llm_semantic_validation"
  severity?: string;  // e.g., "low", "medium", "high", "critical"
  description?: string;  // Detailed description of the check
  suggestion?: string;  // Suggested fix or improvement
  autoFixable?: boolean;  // Whether this issue can be auto-fixed
  category?: string;  // e.g., "tags", "content", "metadata", "llm"
  reasoning?: string;  // LLM reasoning for the decision
  issues?: Array<{tag: string; problem: string}>;  // List of specific issues found
  llm_assessment?: string;  // LLM's overall assessment
  llm_reasoning?: string;  // LLM's detailed reasoning
  issues_found?: number;  // Number of issues found
  processing_time_ms?: number;  // Processing time for this check
}

export interface ChunkAnalysisResponse {
  trace_id: string;
  record_id: string;
  overall_status: 'pass' | 'fail' | 'pending_review';
  quality_checks: QualityCheckResult[];
  processing_time_ms: number;
  created_at: string;
}

export interface SystemStats {
  total_processed: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_processing_time_ms: number;
  total_chunks: number;
  llm_requests: number;
  llm_cost_usd: number;
}

export interface ChunkRecord {
  id: string;
  trace_id: string;
  record_id: string;
  recordId: string;
  source_connector: string;
  sourceConnectorName: string;
  sourceConnectorType: string;
  content: string;
  contentPreview: string;
  tags: string[];
  overall_status: 'pass' | 'fail' | 'pending_review';
  status: 'pending' | 'approved' | 'flagged' | 'under_review' | 'rejected';
  qualityScore: number;
  confidenceScore: number;
  companyId: string;
  companyName: string;
  issues: any[];
  metadata: Record<string, any>;
  created_at: string;
  createdAt: string;
  updatedAt: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  processed_at: string;
  llmSuggestions: string[];  // Add LLM suggestions field
  quality_checks: QualityCheckResult[];
}

export interface RecordsResponse {
  data: ChunkRecord[];
  pagination: {
    page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
  };
}

export interface AnalyticsData {
  qualityTrendData: Array<{
    date: string
    processed: number
    avg_quality: number
  }>
  sourcePerformanceData: Array<{
    source: string
    processed: number
    avg_quality: number
  }>
  issueBreakdownData: Array<{
    name: string
    value: number
    color: string
  }>
  companyMetricsData: Array<{
    company: string
    records: number | null
    avgQuality: number | null
    issues: number | null
    cost: number | null
  }>
  topFailureReasons: Array<{
    reason: string
    count: number
    percentage: number
  }>
  today: {
    total_processed: number | null
    avg_quality_score: number | null
    total_issues: number | null
  }
}

class APIClient {
  private baseURL: string;

  constructor() {
    this.baseURL = API_BASE_URL;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('🌐 API Error:', response.status, errorText);
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }
      
      const result = await response.json();
      return result;
    } catch (error) {
      console.error('🌐 Request failed:', error);
      throw error;
    }
  }

  // Approve a flagged record
  async approveFlaggedRecord(recordId: string, userId: string) {
    return this.request(`/records/approve/${recordId}`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    });
  }

  // Quality Records Methods
  async getQualityRecords(filters: any, pagination: any): Promise<any> {
    try {
      const queryParams = new URLSearchParams();
      
      // Add pagination params
      if (pagination.page !== undefined) queryParams.append('page', pagination.page.toString());
      if (pagination.pageSize !== undefined) queryParams.append('pageSize', pagination.pageSize.toString());
      if (pagination.sortBy) queryParams.append('sortBy', pagination.sortBy);
      if (pagination.sortOrder) queryParams.append('sortOrder', pagination.sortOrder);
      
      // Add filter params - PROPERLY MAP ARRAYS
      if (filters.companies && filters.companies.length > 0) {
        queryParams.append('companies', filters.companies.join(','));
      }
      if (filters.sourceConnectors && filters.sourceConnectors.length > 0) {
        queryParams.append('sourceConnectors', filters.sourceConnectors.join(','));
      }
      if (filters.statuses && filters.statuses.length > 0) {
        queryParams.append('statuses', filters.statuses.join(','));
      }
      if (filters.priorities && filters.priorities.length > 0) {
        queryParams.append('priorities', filters.priorities.join(','));
      }
      if (filters.issueTypes && filters.issueTypes.length > 0) {
        queryParams.append('issueTypes', filters.issueTypes.join(','));
      }
      if (filters.tags && filters.tags.length > 0) {
        queryParams.append('tags', filters.tags.join(','));
      }
      if (filters.departments && filters.departments.length > 0) {
        queryParams.append('departments', filters.departments.join(','));
      }
      if (filters.authors && filters.authors.length > 0) {
        queryParams.append('authors', filters.authors.join(','));
      }
      if (filters.searchQuery) {
        queryParams.append('searchQuery', filters.searchQuery);
      }
      if (filters.qualityScoreRange && filters.qualityScoreRange.length === 2) {
        queryParams.append('qualityScoreRange', `${filters.qualityScoreRange[0]},${filters.qualityScoreRange[1]}`);
      }
      if (filters.dateRange) {
        if (filters.dateRange.from) queryParams.append('startDate', filters.dateRange.from);
        if (filters.dateRange.to) queryParams.append('endDate', filters.dateRange.to);
      }
      
      const endpoint = `/records${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      console.log('🔍 Filter request URL:', endpoint);
      console.log('🔍 Applied filters:', filters);
      
      const response = await this.request(endpoint) as any;
      
      console.log('🏠 Backend /records (with filters) response:', response);
      if (response.data && response.data.length > 0) {
        console.log('🎯 First filtered record structure:', response.data[0]);
        console.log('📝 LLM suggestions in first filtered record:', response.data[0].llmSuggestions);
      }
      
      return response;
      
    } catch (error) {
      console.warn('Records endpoint not available, using fallback data');
      // Return empty data structure that matches expected format
      return {
        data: [],
        pagination: {
          page: pagination.page || 1,
          page_size: pagination.pageSize || 20,
          total_count: 0,
          total_pages: 0
        }
      };
    }
  }

  async overrideApprovedRecord(recordId: string, userId: string, reason: string): Promise<any> {
    return this.request(`/records/${recordId}/override`, {
      method: 'POST',
      body: JSON.stringify({ 
        user_id: userId,
        reason: reason 
      }),
    });
  }

  async getFilterOptions(): Promise<any> {
    try {
      // Try the real filter options endpoint first
      return await this.request('/records/filter-options');
    } catch (error) {
      console.warn('Records filter options endpoint not available, using fallback data');
      return {
        companies: ['Default Company'],
        connectors: ['SharePoint', 'Confluence', 'Notion', 'GDrive'],
        tags: ['important', 'review', 'policy', 'documentation'],
        statuses: ['approved', 'flagged', 'pending', 'under_review', 'rejected'],
        priorities: ['low', 'medium', 'high', 'critical']
      };
    }
  }

  async getDeadLettersFilterOptions(): Promise<any> {
    try {
      return await this.request('/dead-letters/filter-options');
    } catch (error) {
      console.warn('Dead letters filter options endpoint not available, using fallback data');
      return {
        error_types: [
          { value: 'SCHEMA_VALIDATION_ERROR', label: 'Schema Validation', count: 0 },
          { value: 'PROCESSING_ERROR', label: 'Processing Error', count: 0 },
          { value: 'TIMEOUT_ERROR', label: 'Timeout', count: 0 },
          { value: 'LLM_ERROR', label: 'LLM Error', count: 0 },
          { value: 'CONNECTION_ERROR', label: 'Connection Error', count: 0 }
        ],
        source_connectors: [
          { value: 'SharePoint', label: 'SharePoint', count: 0 },
          { value: 'Confluence', label: 'Confluence', count: 0 },
          { value: 'Notion', label: 'Notion', count: 0 },
          { value: 'GDrive', label: 'Google Drive', count: 0 },
          { value: 'Elasticsearch', label: 'Elasticsearch', count: 0 }
        ],
        time_periods: [
          { value: 1, label: 'Last Hour' },
          { value: 6, label: 'Last 6 Hours' },
          { value: 24, label: 'Last 24 Hours' },
          { value: 168, label: 'Last Week' },
          { value: 720, label: 'Last Month' }
        ]
      };
    }
  }

  // Analytics and Dashboard Methods
  async getDashboardAnalytics(): Promise<any> {
    return this.request('/analytics/dashboard');
  }

  async getAnalyticsData(timeRange: string = '7d'): Promise<any> {
    return this.request(`/analytics/dashboard?time_range=${timeRange}`);
  }

  // Backend Testing Methods
  async getHealth(): Promise<any> {
    try {
      return await this.request('/health');
    } catch (error) {
      console.warn('Health endpoint not available');
      return {
        status: 'offline',
        message: 'Backend server needs restart to load new endpoints',
        timestamp: new Date().toISOString()
      };
    }
  }

  async health(): Promise<any> {
    return this.getHealth();
  }

  async selfTest(): Promise<any> {
    return this.request('/test');
  }

  async getStats(): Promise<SystemStats> {
    return this.request('/stats');
  }

  // ================================
  // COMMENTED OUT - METHODS FOR NON-EXISTENT ENDPOINTS
  // ================================
  
  /*
  // These methods call endpoints that don't exist in the backend
  // Keeping them commented for reference but removing from active use
  
  async getRequestLogs(params?: {
    page?: number;
    page_size?: number;
    success_only?: boolean;
    endpoint?: string;
  }): Promise<any> {
    const queryParams = new URLSearchParams();
    if (params?.page !== undefined) queryParams.append('page', params.page.toString());
    if (params?.page_size !== undefined) queryParams.append('page_size', params.page_size.toString());
    if (params?.success_only !== undefined) queryParams.append('success_only', params.success_only.toString());
    if (params?.endpoint) queryParams.append('endpoint', params.endpoint);
    
    const endpoint = `/request-logs${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    return this.request(endpoint);
  }

  async getRequestAnalytics(): Promise<any> {
    return this.request('/analytics/requests');
  }

  async getEvaluationMetrics(): Promise<any> {
    return this.request('/evaluation/metrics');
  }

  async getRedTeamResults(): Promise<any> {
    return this.request('/redteam/results');
  }

  async getAlertEmails(): Promise<any> {
    return this.request('/alerts/emails');
  }

  async getAlertTemplate(): Promise<any> {
    return this.request('/alerts/template');
  }

  async addAlertEmail(email: string, type: string = 'to'): Promise<any> {
    const params = new URLSearchParams({ email, typ: type });
    return this.request(`/alerts/emails?${params.toString()}`, { method: 'POST' });
  }

  async testAlert(): Promise<any> {
    return this.request('/alerts/test', { method: 'POST' });
  }

  async exportRecords(format: string = 'json'): Promise<any> {
    return this.request(`/export/records?format=${format}`);
  }

  async chainOfThoughtAnalysis(request: any): Promise<any> {
    return this.request('/llm/chain-of-thought', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async selfConsistencyAnalysis(request: any): Promise<any> {
    return this.request('/llm/self-consistency', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }
  */

  // Content Processing Methods
  async ingestContent(content: any): Promise<any> {
    return this.request('/ingest', {
      method: 'POST',
      body: JSON.stringify(content),
    });
  }

  async checkRules(rulesData: any): Promise<any> {
    return this.request('/rules/check', {
      method: 'POST',
      body: JSON.stringify(rulesData),
    });
  }

  async analyzeLLM(llmData: any): Promise<any> {
    return this.request('/llm/analyze', {
      method: 'POST',
      body: JSON.stringify(llmData),
    });
  }

  async redTeamAnalysis(redTeamData: any): Promise<any> {
    return this.request('/red-team/analyze', {
      method: 'POST',
      body: JSON.stringify(redTeamData),
    });
  }

  async chainOfThoughtAnalysis(cotData: any): Promise<any> {
    return this.request('/llm/chain-of-thought', {
      method: 'POST',
      body: JSON.stringify(cotData),
    });
  }

  // Alert and Email Methods
  async getAlertEmails(): Promise<any> {
    return this.request('/alerts/emails');
  }

  async getAlertTemplate(): Promise<any> {
    return this.request('/alerts/template');
  }

  async addAlertEmail(email: string): Promise<any> {
    return this.request('/alerts/emails', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  }

  async testAlert(): Promise<any> {
    return this.request('/alerts/test', {
      method: 'POST',
    });
  }

  // Review Pipeline Methods
  async updateRecordContent(recordId: string, content: string, tags: string[], userId: string = 'admin', reason?: string): Promise<any> {
    return this.request(`/records/${encodeURIComponent(recordId)}/content`, {
      method: 'PUT',
      body: JSON.stringify({
        content,
        tags,
        user_id: userId,
        reason: reason || 'Content updated via UI'
      }),
    });
  }

  async reprocessRecord(recordId: string, content: string, tags: string[], userId: string = 'admin', reason?: string): Promise<any> {
    return this.request(`/records/${encodeURIComponent(recordId)}/reprocess`, {
      method: 'POST',
      body: JSON.stringify({
        content,
        tags,
        user_id: userId,
        reason: reason || 'Record reprocessed via UI'
      }),
    });
  }

  async approveRecord(recordId: string, userId: string = 'admin', reason?: string): Promise<any> {
    return this.request(`/records/${encodeURIComponent(recordId)}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        reason: reason || 'Approved via UI'
      }),
    });
  }

  async flagRecord(recordId: string, userId: string = 'admin', reason?: string): Promise<any> {
    return this.request(`/records/${encodeURIComponent(recordId)}/flag`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        reason: reason || 'Flagged via UI'
      }),
    });
  }

  async getAuditTrail(recordId: string): Promise<any> {
    return this.request(`/records/${encodeURIComponent(recordId)}/audit-trail`, {
      method: 'GET',
    });
  }

  // Company and Connector Methods
  async getCompanies(): Promise<any> {
    return this.request('/companies');
  }

  async getConnectors(): Promise<any> {
    return this.request('/connectors');
  }

  async getIssues(): Promise<any> {
    return this.request('/issues');
  }

  // Export Methods
  async exportRecords(format: string = 'json'): Promise<any> {
    return this.request(`/export/records?format=${format}`);
  }

  // Dead Letters Methods (already exist but may need updates)
  async getDeadLettersStats(hoursBack: number = 24): Promise<any> {
    return this.request(`/dead-letters/stats?hours_back=${hoursBack}`);
  }

  // LLM Settings Methods
  async getLLMSettings(): Promise<any> {
    try {
      const response = await this.request<{success: boolean, settings: any}>('/settings/llm-mode');
      // Return in the format expected by LLMInvocationSettings component
      return {
        success: true,
        settings: response.settings || { 
          mode: 'binary', 
          percentage_threshold: 85, 
          weighted_threshold: 0.8,
          range_min_threshold: 70,
          range_max_threshold: 90,
          rule_weights: {},
          created_by: 'system',
          updated_at: new Date().toISOString()
        },
        rule_weights: [
          { rule_name: 'content_quality_check', weight: 1.0, description: 'Validates content quality and relevance' },
          { rule_name: 'tag_validation', weight: 0.8, description: 'Ensures proper tag assignment' },
          { rule_name: 'pii_detection', weight: 1.2, description: 'Detects personally identifiable information' },
          { rule_name: 'format_validation', weight: 0.6, description: 'Validates document format and structure' }
        ]
      };
    } catch (error) {
      // Fallback to default settings if endpoint not available
      return {
        success: true,
        settings: { 
          mode: 'binary', 
          percentage_threshold: 85, 
          weighted_threshold: 0.8,
          range_min_threshold: 70,
          range_max_threshold: 90,
          rule_weights: {
            'content_quality_check': 1.0,
            'tag_validation': 0.8,
            'pii_detection': 1.2,
            'format_validation': 0.6
          },
          created_by: 'system',
          updated_at: new Date().toISOString()
        },
        rule_weights: [
          { rule_name: 'content_quality_check', weight: 1.0, description: 'Validates content quality and relevance' },
          { rule_name: 'tag_validation', weight: 0.8, description: 'Ensures proper tag assignment' },
          { rule_name: 'pii_detection', weight: 1.2, description: 'Detects personally identifiable information' },
          { rule_name: 'format_validation', weight: 0.6, description: 'Validates document format and structure' }
        ]
      };
    }
  }

  async getLLMSettingsHistory(): Promise<any> {
    try {
      const response = await this.request('/settings/llm-thresholds/history') as any;
      return { success: true, history: response.history || [] };
    } catch (error) {
      // Fallback with empty history
      return { success: true, history: [] };
    }
  }

  async updateLLMMode(mode: string, userId: string, reason?: string): Promise<any> {
    try {
      const response = await this.request('/settings/llm-mode', {
        method: 'POST',
        body: JSON.stringify({ mode, user_id: userId, reason }),
      }) as any;
      return { success: true, settings: response.settings, message: 'LLM mode updated successfully' };
    } catch (error) {
      return { success: false, message: 'Failed to update LLM mode' };
    }
  }

  async updateLLMThresholds(updates: any, userId: string, reason?: string): Promise<any> {
    try {
      const response = await this.request('/settings/llm-thresholds', {
        method: 'PATCH',
        body: JSON.stringify({ ...updates, user_id: userId, reason }),
      }) as any;
      return { success: true, settings: response.settings, message: 'LLM thresholds updated successfully' };
    } catch (error) {
      return { success: false, message: 'Failed to update LLM thresholds' };
    }
  }

  async simulateLLMDecision(mode: string, threshold: number, sampleInput: any, ruleWeights: any): Promise<any> {
    try {
      const response = await this.request('/simulate-llm-decision', {
        method: 'POST',
        body: JSON.stringify({
          mode,
          threshold,
          sample_input: sampleInput,
          rule_weights: ruleWeights
        }),
      }) as any;
      return { success: true, data: { decision: response } };
    } catch (error) {
      return { success: false, message: 'Simulation failed' };
    }
  }

  async resetLLMSettings(): Promise<any> {
    try {
      const response = await this.request('/settings/llm-reset', {
        method: 'POST',
      }) as any;
      return { success: true, settings: response.settings, message: 'LLM settings reset to defaults' };
    } catch (error) {
      return { success: false, message: 'Failed to reset LLM settings' };
    }
  }

  async updateLLMSettings(settings: any): Promise<any> {
    return this.request('/llm/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  }

  // Feedback Methods
  async submitFeedback(feedback: {
    trace_id: string;
    decision: string;
    comments: string;
    reviewer_id: string;
    reviewed_at: string;
  }): Promise<any> {
    return this.request('/feedback', {
      method: 'POST',
      body: JSON.stringify(feedback),
    });
  }

  // Essential Record Management Methods
  async getRecords(): Promise<RecordsResponse> {
    const response = await this.request('/records') as any;
    console.log('🏠 Backend /records response:', response);
    if (response.data && response.data.length > 0) {
      console.log('🎯 First record structure:', response.data[0]);
      console.log('📝 LLM suggestions in first record:', response.data[0].llmSuggestions);
    }
    return response;
  }

  async ingestChunk(chunk: ChunkIngestRequest): Promise<ChunkAnalysisResponse> {
    return this.request('/ingest', {
      method: 'POST',
      body: JSON.stringify(chunk),
    });
  }

  // Dead Letters Management
  async getDeadLetters(params?: {
    skip?: number;
    limit?: number;
    hours_back?: number;
    error_type?: string;
    source_connector?: string;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.hours_back !== undefined) queryParams.append('hours_back', params.hours_back.toString());
    if (params?.error_type) queryParams.append('error_type', params.error_type);
    if (params?.source_connector) queryParams.append('source_connector', params.source_connector);
    
    const endpoint = `/dead-letters${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    const response = await this.request<{dead_letters: any[]}>(endpoint);
    return response.dead_letters || [];
  }

  async retryDeadLetter(letterId: string): Promise<any> {
    return this.request(`/dead-letters/${letterId}/retry`, { method: 'POST' });
  }

  async resolveDeadLetter(letterId: string): Promise<any> {
    return this.request(`/dead-letters/${letterId}/resolve`, { method: 'POST' });
  }

  async deleteDeadLetter(letterId: string): Promise<any> {
    return this.request(`/dead-letters/${letterId}`, { method: 'DELETE' });
  }

  // File Upload and Batch Processing
  async uploadFile(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${this.baseURL}/ingest/unified-upload`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    // Handle streaming response by reading the final result
    const text = await response.text();
    
    // Extract the last complete JSON from streaming data
    const lines = text.trim().split('\n');
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i].trim();
      if (line.startsWith('data: ')) {
        try {
          return JSON.parse(line.substring(6));
        } catch (e) {
          continue;
        }
      }
    }
    
    // Fallback: try to parse entire response as JSON
    try {
      return JSON.parse(text);
    } catch (e) {
      return { success: true, message: 'Upload completed' };
    }
  }

  async syncBatch(batch: {
    chunks: ChunkIngestRequest[];
    batch_metadata?: Record<string, any>;
  }): Promise<any> {
    return this.request('/ingest/unified-demo', {
      method: 'POST',
      body: JSON.stringify(batch.chunks),
    });
  }

  // Tag Suggestions
  async getTagSuggestions(content: string, currentTags: string[] = []): Promise<{
    success: boolean;
    suggestions: string[];
    confidence_score: number;
    reasoning: string;
  }> {
    return this.request('/llm/tag-suggestions', {
      method: 'POST',
      body: JSON.stringify({
        content,
        current_tags: currentTags
      }),
    });
  }

  // LLM Improvement Suggestions
  async getLLMSuggestions(params: {
    content: string;
    tags: string[];
    quality_score: number;
    issues: any[];
  }): Promise<{
    success: boolean;
    suggestions: string[];
    confidence_score: number;
    reasoning: string;
  }> {
    return this.request('/llm/improvement-suggestions', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  // Metrics endpoint
  async getMetrics(): Promise<any> {
    return this.request('/metrics');
  }

  // Auto-fix issues
  async autoFixIssue(issueId: string) {
    return this.request(`/issues/${issueId}/auto-fix`, {
      method: 'POST',
    });
  }
}

export const apiClient = new APIClient(); 