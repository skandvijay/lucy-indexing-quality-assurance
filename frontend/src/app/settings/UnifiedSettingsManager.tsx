'use client'

import React, { useState, useEffect } from 'react'
import { 
  Save, 
  RotateCcw, 
  Settings, 
  ChevronDown, 
  ChevronRight,
  Database,
  Zap,
  Shield,
  BarChart3,
  Mail,
  Sliders,
  Target,
  Play,
  AlertTriangle,
  CheckCircle,
  Info,
  Clock,
  TrendingUp
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { Slider } from '@/components/ui/slider'
import { Badge } from '@/components/ui/badge'

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

interface LLMSettings {
  mode: string
  percentage_threshold: number
  weighted_threshold: number
  range_min_threshold: number
  range_max_threshold: number
  rule_weights: Record<string, number>
}

interface Rule {
  name: string
  display_name: string
  description: string
  category: string
  severity: string
  weight: number
  enabled: boolean
  threshold_value?: number
  auto_fixable: boolean
  updated_at?: string
}

interface DynamicThreshold {
  name: string
  display_name: string
  current_value: number
  default_value: number
  min_value: number
  max_value: number
  description: string
  category: string
  unit: string
  affects_rules: string[]
  updated_at?: string
}

interface ConfigItem {
  name: string
  value: any
  type: string
  description: string
  category: string
  default_value: any
}

const API_BASE = 'http://127.0.0.1:8000'

const LLM_MODES = {
  binary: {
    title: 'Binary Mode',
    description: 'Simple pass/fail based on all rules passing',
    info: 'Strict mode: LLM is triggered only when ALL quality rules pass. Most conservative approach.',
    color: 'bg-red-100 text-red-800',
    icon: Shield
  },
  percentage: {
    title: 'Percentage Mode', 
    description: 'LLM triggered based on percentage of rules passing',
    info: 'Balanced mode: LLM is triggered when a certain percentage of rules pass. Good for most use cases.',
    color: 'bg-yellow-100 text-yellow-800',
    icon: BarChart3
  },
  weighted: {
    title: 'Weighted Mode',
    description: 'Advanced scoring with custom rule weights',
    info: 'Flexible mode: Each rule has a custom weight. LLM triggered based on weighted score. Most customizable.',
    color: 'bg-green-100 text-green-800',
    icon: Sliders
  },
  range: {
    title: 'Range Mode',
    description: 'LLM triggered only in gray zone between thresholds',
    info: 'Smart mode: Below min threshold = auto-reject, above max threshold = auto-approve, in between = LLM analysis. Perfect for cost optimization.',
    color: 'bg-blue-100 text-blue-800',
    icon: Target
  }
}

export default function UnifiedSettingsManager() {
  const [activeTab, setActiveTab] = useState('rules')
  const [thresholds, setThresholds] = useState<Threshold[]>([])
  const [dynamicRules, setDynamicRules] = useState<Rule[]>([])
  const [dynamicThresholds, setDynamicThresholds] = useState<DynamicThreshold[]>([])
  const [llmSettings, setLLMSettings] = useState<LLMSettings>({
    mode: 'percentage',
    percentage_threshold: 85,
    weighted_threshold: 0.8,
    range_min_threshold: 70,
    range_max_threshold: 80,
    rule_weights: {}
  })
  const [configs, setConfigs] = useState<ConfigItem[]>([])
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['content_quality', 'tag_validation']))
  const [loading, setLoading] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')
  const [simulationInput, setSimulationInput] = useState('')
  const [simulationResult, setSimulationResult] = useState<any>(null)
  const [ruleWeights, setRuleWeights] = useState<any[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [searchTerm, setSearchTerm] = useState('')

  // Load initial data
  useEffect(() => {
    Promise.all([
      loadThresholds(),
      loadDynamicRules(),
      loadDynamicThresholds(),
      loadLLMSettings(), 
      loadConfigs(),
      loadRuleWeights()
    ])
  }, [])

  const loadThresholds = async () => {
    try {
      const response = await fetch(`${API_BASE}/thresholds`)
      const data = await response.json()
      if (data.success) {
        setThresholds(data.thresholds || [])
      }
    } catch (error) {
      console.error('Failed to load thresholds:', error)
    }
  }

  const loadDynamicRules = async () => {
    try {
      const response = await fetch(`${API_BASE}/dynamic-rules/rules`)
      const data = await response.json()
      if (data.success) {
        setDynamicRules(data.rules || [])
      }
    } catch (error) {
      console.error('Failed to load dynamic rules:', error)
    }
  }

  const loadDynamicThresholds = async () => {
    try {
      // Load ALL thresholds from UnifiedConfigService (22 thresholds) instead of just Dynamic Rules (11)
      const response = await fetch(`${API_BASE}/thresholds`)
      const data = await response.json()
      if (data.success) {
        // Convert UnifiedConfigService format to DynamicThreshold format for UI compatibility
        const unifiedThresholds = Object.values(data.thresholds || {}).map((threshold: any) => ({
          name: threshold.name,
          display_name: threshold.display_name,
          current_value: threshold.current_value,
          default_value: threshold.default_value,
          min_value: threshold.min_value,
          max_value: threshold.max_value,
          description: threshold.description,
          category: threshold.category || 'general',
          unit: threshold.unit || 'value',
          affects_rules: threshold.affects_rules || [],
          updated_at: threshold.updated_at
        }))
        
        console.log(`🎯 Loaded ${unifiedThresholds.length} thresholds from UnifiedConfigService`)
        setDynamicThresholds(unifiedThresholds)
      }
    } catch (error) {
      console.error('Failed to load unified thresholds:', error)
      // Fallback to dynamic rules if UnifiedConfigService fails
      try {
        const fallbackResponse = await fetch(`${API_BASE}/dynamic-rules/thresholds`)
        const fallbackData = await fallbackResponse.json()
        if (fallbackData.success) {
          setDynamicThresholds(fallbackData.thresholds || [])
        }
      } catch (fallbackError) {
        console.error('Failed to load fallback thresholds:', fallbackError)
      }
    }
  }

  const loadLLMSettings = async () => {
    try {
      const response = await fetch(`${API_BASE}/settings/llm-mode`)
      const data = await response.json()
      if (data.success) {
        // Merge API response with current state to prevent undefined values
        setLLMSettings(prev => ({
          ...prev,
          ...data.settings,
          // Ensure range thresholds are always defined
          range_min_threshold: data.settings.range_min_threshold ?? prev.range_min_threshold,
          range_max_threshold: data.settings.range_max_threshold ?? prev.range_max_threshold
        }))
      }
    } catch (error) {
      console.error('Failed to load LLM settings:', error)
    }
  }

  const loadConfigs = async () => {
    try {
      const response = await fetch(`${API_BASE}/unified-settings/configs`)
      const data = await response.json()
      if (data.success) {
        setConfigs(data.configs || [])
      }
    } catch (error) {
      console.error('Failed to load configs:', error)
    }
  }

  const loadRuleWeights = async () => {
    try {
      const response = await fetch(`${API_BASE}/rules/weights`)
      const data = await response.json()
      if (data.success) {
        setRuleWeights(data.rule_weights || [])
      }
    } catch (error) {
      console.error('Failed to load rule weights:', error)
    }
  }

  const saveThresholds = async () => {
    setLoading(true)
    try {
      const updates = thresholds.map(t => ({
        threshold_name: t.name,
        new_value: t.current_value,
        reason: 'Updated via Unified Settings Manager',
        user_id: 'admin'
      }))

      const response = await fetch(`${API_BASE}/thresholds/bulk-update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })

      const result = await response.json()
      if (result.success) {
        setSaveMessage('✅ Thresholds saved successfully!')
        setTimeout(() => setSaveMessage(''), 3000)
        await loadThresholds() // Reload to get latest values
      }
    } catch (error) {
      setSaveMessage('❌ Failed to save thresholds')
      setTimeout(() => setSaveMessage(''), 3000)
    } finally {
      setLoading(false)
    }
  }

  const saveLLMSettings = async () => {
    setLoading(true)
    try {
      // First update the mode
      const modeResponse = await fetch(`${API_BASE}/settings/llm-mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: llmSettings.mode,
          user_id: 'admin',
          reason: 'Updated via Unified Settings Manager'
        })
      })

      // Then update the thresholds
      const thresholdPayload: any = {
        user_id: 'admin',
        reason: 'Updated via Unified Settings Manager'
      }

      if (llmSettings.mode === 'percentage') {
        thresholdPayload.percentage_threshold = llmSettings.percentage_threshold
      } else if (llmSettings.mode === 'weighted') {
        thresholdPayload.weighted_threshold = llmSettings.weighted_threshold
        thresholdPayload.rule_weights = llmSettings.rule_weights
      } else if (llmSettings.mode === 'range') {
        thresholdPayload.range_min_threshold = llmSettings.range_min_threshold
        thresholdPayload.range_max_threshold = llmSettings.range_max_threshold
      }

      const thresholdResponse = await fetch(`${API_BASE}/settings/llm-thresholds`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(thresholdPayload)
      })

      const modeResult = await modeResponse.json()
      const thresholdResult = await thresholdResponse.json()
      
      if (modeResult.success && thresholdResult.success) {
        setSaveMessage('✅ LLM settings saved successfully!')
        setTimeout(() => setSaveMessage(''), 3000)
        await loadLLMSettings() // Reload to get latest values
      } else {
        setSaveMessage('❌ Failed to save some LLM settings')
        setTimeout(() => setSaveMessage(''), 3000)
      }
    } catch (error) {
      setSaveMessage('❌ Failed to save LLM settings')
      setTimeout(() => setSaveMessage(''), 3000)
    } finally {
      setLoading(false)
    }
  }

  const simulateLLMDecision = async () => {
    if (!simulationInput.trim()) return

    setLoading(true)
    try {
      const input = JSON.parse(simulationInput)
      const response = await fetch(`${API_BASE}/simulate-llm-decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: llmSettings.mode,
          // 🔧 REMOVED hardcoded threshold - backend will get current dynamic values from Unified Config
          sample_input: input
          // 🔧 REMOVED rule_weights - backend will get current dynamic values
        })
      })

      const result = await response.json()
      setSimulationResult(result)
    } catch (error) {
      setSimulationResult({
        error: 'Invalid JSON input or simulation failed',
        details: error instanceof Error ? error.message : 'Unknown error'
      })
    } finally {
      setLoading(false)
    }
  }

  const resetThreshold = async (thresholdName: string) => {
    try {
      const response = await fetch(`${API_BASE}/thresholds/${thresholdName}/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'admin' })
      })

      if (response.ok) {
        await loadThresholds()
        setSaveMessage(`✅ Reset ${thresholdName} to default`)
        setTimeout(() => setSaveMessage(''), 3000)
      }
    } catch (error) {
      console.error('Failed to reset threshold:', error)
    }
  }

  const updateThresholdValue = (name: string, value: number) => {
    setThresholds(prev => prev.map(t => t.name === name ? { ...t, current_value: value } : t))
  }

  const updateLLMMode = (mode: string) => {
    setLLMSettings(prev => ({ ...prev, mode }))
  }

  const updateLLMThreshold = (value: number) => {
    if (llmSettings.mode === 'percentage') {
      setLLMSettings(prev => ({ ...prev, percentage_threshold: value }))
    } else {
      setLLMSettings(prev => ({ ...prev, weighted_threshold: value }))
    }
  }

  const updateRuleWeight = (ruleName: string, weight: number) => {
    setLLMSettings(prev => ({
      ...prev,
      rule_weights: { ...prev.rule_weights, [ruleName]: weight }
    }))
  }

  const updateDynamicRuleWeight = async (ruleName: string, newWeight: number) => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/dynamic-rules/rules/${ruleName}/weight`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rule_name: ruleName,
          weight: newWeight,
          changed_by: 'admin',
          reason: 'Updated via Unified Settings'
        })
      })

      const result = await response.json()
      if (result.success) {
        setSaveMessage(`✅ Rule weight updated: ${ruleName} = ${newWeight}`)
        setTimeout(() => setSaveMessage(''), 3000)
        await loadDynamicRules()
      } else {
        setSaveMessage(`❌ Failed to update rule weight`)
        setTimeout(() => setSaveMessage(''), 3000)
      }
    } catch (error) {
      setSaveMessage('❌ Failed to update rule weight')
      setTimeout(() => setSaveMessage(''), 3000)
    } finally {
      setLoading(false)
    }
  }

  const updateDynamicThreshold = async (thresholdName: string, newValue: number) => {
    setLoading(true)
    try {
      // Use UnifiedConfigService API for threshold updates (follows SOLID principles)
      const response = await fetch(`${API_BASE}/thresholds/${thresholdName}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          threshold_name: thresholdName,
          new_value: newValue,
          user_id: 'admin',
          reason: 'Updated via Unified Settings Manager'
        })
      })

      const result = await response.json()
      if (result.success) {
        setSaveMessage(`✅ Threshold updated: ${thresholdName} = ${newValue}`)
        setTimeout(() => setSaveMessage(''), 3000)
        await loadDynamicThresholds() // Reload all thresholds from UnifiedConfigService
      } else {
        setSaveMessage(`❌ Failed to update threshold: ${result.detail || 'Unknown error'}`)
        setTimeout(() => setSaveMessage(''), 3000)
      }
    } catch (error) {
      setSaveMessage('❌ Failed to update threshold')
      setTimeout(() => setSaveMessage(''), 3000)
    } finally {
      setLoading(false)
    }
  }

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev)
      if (newSet.has(category)) {
        newSet.delete(category)
      } else {
        newSet.add(category)
      }
      return newSet
    })
  }

  const groupedThresholds = thresholds.reduce((acc, threshold) => {
    const category = threshold.category || 'other'
    if (!acc[category]) acc[category] = []
    acc[category].push(threshold)
    return acc
  }, {} as Record<string, Threshold[]>)

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'quality': return BarChart3
      case 'llm': return Zap
      case 'rules': return Shield
      case 'content': return Database
      case 'tags': return Target
      case 'cost': return TrendingUp
      default: return Settings
    }
  }

  const categorizeAndSortThresholds = (thresholds: DynamicThreshold[]) => {
    // Define category order and priority
    const categoryOrder = ['quality', 'llm', 'rules', 'content', 'tags', 'cost', 'general']
    
    // Enhanced categorization mapping
    const categoryMapping: Record<string, string> = {
      'approval_quality_score_threshold': 'quality',
      'quality_pass_rate_threshold': 'quality', 
      'quality_confidence_threshold': 'quality',
      'llm_percentage_threshold': 'llm',
      'llm_weighted_threshold': 'llm',
      'llm_range_min_threshold': 'llm',
      'llm_range_max_threshold': 'llm',
      'llm_confidence_threshold': 'llm',
      'spam_threshold': 'rules',
      'stopword_threshold': 'rules',
      'semantic_relevance_threshold': 'rules',
      'domain_relevance_threshold': 'rules',
      'tag_specificity_threshold': 'rules',
      'tag_text_relevance_threshold': 'rules',
      'context_coherence_threshold': 'rules',
      'language_consistency_threshold': 'rules',
      'min_tag_count': 'tags',
      'max_tag_count': 'tags',
      'min_content_length': 'content',
      'max_content_length': 'content',
      'cost_budget_daily_limit': 'cost',
      'cost_alert_threshold_percentage': 'cost'
    }

    // Apply enhanced categorization
    const enhancedThresholds = thresholds.map(threshold => ({
      ...threshold,
      category: categoryMapping[threshold.name] || threshold.category || 'general'
    }))

    // Group by category
    const grouped = enhancedThresholds.reduce((acc, threshold) => {
      const category = threshold.category
      if (!acc[category]) acc[category] = []
      acc[category].push(threshold)
      return acc
    }, {} as Record<string, DynamicThreshold[]>)

    // Sort within each category by priority
    Object.keys(grouped).forEach(category => {
      grouped[category].sort((a, b) => {
        // Priority order within categories
        const priorityOrder = [
          'approval_quality_score_threshold', // Most important
          'quality_pass_rate_threshold',
          'quality_confidence_threshold',
          'llm_percentage_threshold',
          'llm_weighted_threshold', 
          'llm_range_min_threshold',
          'llm_range_max_threshold',
          'semantic_relevance_threshold',
          'domain_relevance_threshold',
          'tag_text_relevance_threshold',
          'tag_specificity_threshold',
          'context_coherence_threshold'
        ]
        
        const aIndex = priorityOrder.indexOf(a.name)
        const bIndex = priorityOrder.indexOf(b.name)
        
        if (aIndex !== -1 && bIndex !== -1) {
          return aIndex - bIndex
        } else if (aIndex !== -1) {
          return -1
        } else if (bIndex !== -1) {
          return 1
        } else {
          return a.display_name.localeCompare(b.display_name)
        }
      })
    })

    // Return categories in defined order
    const orderedResult: Record<string, DynamicThreshold[]> = {}
    categoryOrder.forEach(category => {
      if (grouped[category]) {
        orderedResult[category] = grouped[category]
      }
    })

    return orderedResult
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                <Settings className="h-8 w-8 text-blue-600" />
                Unified Configuration Management
              </h1>
              <p className="text-gray-600 mt-2">
                Enterprise-grade settings management with real-time updates and comprehensive controls
              </p>
            </div>
            {saveMessage && (
              <div className="flex items-center gap-2 bg-green-50 text-green-700 px-4 py-2 rounded-lg border border-green-200">
                <CheckCircle className="h-4 w-4" />
                {saveMessage}
              </div>
            )}
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-4 mb-6">
              <TabsTrigger value="rules" className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Rule Weights
              </TabsTrigger>
              <TabsTrigger value="thresholds" className="flex items-center gap-2">
                <Sliders className="h-4 w-4" />
                Dynamic Thresholds
              </TabsTrigger>
              <TabsTrigger value="llm" className="flex items-center gap-2">
                <Zap className="h-4 w-4" />
                LLM Invocation Settings
              </TabsTrigger>
              <TabsTrigger value="simulation" className="flex items-center gap-2">
                <Play className="h-4 w-4" />
                LLM Decision Simulation
              </TabsTrigger>
            </TabsList>

            <TabsContent value="rules" className="space-y-6">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Settings className="h-5 w-5 text-blue-600" />
                  <h3 className="font-semibold text-blue-900">Rule Weights Configuration</h3>
                </div>
                <p className="text-blue-800 text-sm">
                  Adjust the importance of each quality rule in the overall score calculation. 
                  Higher weights make rules more impactful. Changes take effect immediately across the entire system.
                </p>
              </div>

              {/* Search and Filter */}
              <div className="flex gap-4 items-center bg-white p-4 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2">
                  <label className="font-medium">Category:</label>
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">All Categories</option>
                    <option value="content_quality">Content Quality</option>
                    <option value="tag_validation">Tag Validation</option>
                    <option value="semantic_analysis">Semantic Analysis</option>
                    <option value="spam_detection">Spam Detection</option>
                    <option value="duplicate_detection">Duplicate Detection</option>
                    <option value="domain_specific">Domain Specific</option>
                  </select>
                </div>
                <input
                  type="text"
                  placeholder="Search rules..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 flex-1"
                />
              </div>

                             {/* Rules by Category */}
               {Object.entries(
                 dynamicRules
                   .filter(rule => 
                     (selectedCategory === 'all' || rule.category === selectedCategory) &&
                     (rule.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                      rule.description.toLowerCase().includes(searchTerm.toLowerCase()))
                   )
                   .reduce((acc, rule) => {
                     const category = rule.category || 'other'
                     if (!acc[category]) acc[category] = []
                     acc[category].push(rule)
                     return acc
                   }, {} as Record<string, Rule[]>)
               ).map(([category, categoryRules]) => {
                  const isExpanded = expandedCategories.has(category)
                  const Icon = getCategoryIcon(category)
                  
                  return (
                    <Card key={category} className="overflow-hidden">
                      <CardHeader 
                        className="cursor-pointer hover:bg-gray-50 transition-colors"
                        onClick={() => toggleCategory(category)}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Icon className="h-5 w-5 text-gray-600" />
                            <div>
                              <CardTitle className="text-lg capitalize">
                                {category.replace('_', ' ')} Rules
                              </CardTitle>
                              <CardDescription>
                                {categoryRules.length} rules in this category
                              </CardDescription>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge className="bg-blue-100 text-blue-800">
                              {categoryRules.length} rules
                            </Badge>
                            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                          </div>
                        </div>
                      </CardHeader>

                      {isExpanded && (
                        <CardContent className="space-y-4">
                          {categoryRules.map((rule) => (
                            <div key={rule.name} className="p-4 border rounded-lg bg-gray-50">
                              <div className="flex items-start justify-between mb-3">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <h4 className="font-medium text-gray-900">{rule.display_name}</h4>
                                    <Badge className={
                                      rule.severity === 'critical' ? 'bg-red-500 text-white' :
                                      rule.severity === 'high' ? 'bg-orange-500 text-white' :
                                      rule.severity === 'medium' ? 'bg-yellow-500 text-white' :
                                      'bg-green-500 text-white'
                                    }>
                                      {rule.severity}
                                    </Badge>
                                    {rule.auto_fixable && (
                                      <Badge variant="outline" className="text-green-600 border-green-600">
                                        Auto-fixable
                                      </Badge>
                                    )}
                                  </div>
                                  <p className="text-sm text-gray-600 mb-2">{rule.description}</p>
                                  {rule.updated_at && (
                                    <p className="text-xs text-gray-500">
                                      Last updated: {new Date(rule.updated_at).toLocaleString()}
                                    </p>
                                  )}
                                </div>
                                
                                <div className="flex items-center gap-2 ml-4">
                                  <span className="text-sm font-medium text-gray-700">
                                    Weight: {rule.weight.toFixed(1)}
                                  </span>
                                </div>
                              </div>
                              
                              <div className="space-y-3">
                                <div>
                                  <Label className="text-sm text-gray-700">
                                    Weight (0.0 - 5.0): {rule.weight.toFixed(1)}
                                  </Label>
                                                                     <Slider
                                     value={[rule.weight]}
                                     onValueChange={(values) => {
                                       const value = values[0]
                                       // Update local state immediately for responsive UI
                                       const updatedRules = dynamicRules.map(r => 
                                         r.name === rule.name ? { ...r, weight: value } : r
                                       )
                                       setDynamicRules(updatedRules)
                                       
                                       // Debounced update to API
                                       clearTimeout((window as any)[`rule_${rule.name}_timeout`])
                                       ;(window as any)[`rule_${rule.name}_timeout`] = setTimeout(() => {
                                         updateDynamicRuleWeight(rule.name, value)
                                       }, 500)
                                     }}
                                     min={0}
                                     max={5}
                                     step={0.1}
                                     className="w-full mt-2"
                                   />
                                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                                    <span>Disabled (0.0)</span>
                                    <span>Normal (1.0)</span>
                                    <span>High Impact (5.0)</span>
                                  </div>
                                </div>
                                
                                <div className="flex gap-2">
                                  <Input
                                    type="number"
                                    value={rule.weight}
                                    onChange={(e) => {
                                      const value = parseFloat(e.target.value) || 0
                                      const updatedRules = dynamicRules.map(r => 
                                        r.name === rule.name ? { ...r, weight: value } : r
                                      )
                                      setDynamicRules(updatedRules)
                                    }}
                                    onBlur={(e) => {
                                      const value = parseFloat(e.target.value) || 0
                                      updateDynamicRuleWeight(rule.name, Math.max(0, Math.min(5, value)))
                                    }}
                                    min={0}
                                    max={5}
                                    step={0.1}
                                    className="w-24"
                                  />
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => updateDynamicRuleWeight(rule.name, 1.0)}
                                    className="flex items-center gap-1"
                                  >
                                    <RotateCcw className="h-3 w-3" />
                                    Reset
                                  </Button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </CardContent>
                      )}
                    </Card>
                  )
                })}
            </TabsContent>

            <TabsContent value="thresholds" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Sliders className="h-5 w-5" />
                    Dynamic Threshold Management
                  </CardTitle>
                  <CardDescription>
                    Configure real-time quality thresholds with instant updates. Changes take effect immediately.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {Object.entries(
                    categorizeAndSortThresholds(
                      dynamicThresholds.filter(threshold => 
                        (selectedCategory === 'all' || threshold.category === selectedCategory) &&
                        (threshold.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         threshold.description.toLowerCase().includes(searchTerm.toLowerCase()))
                      )
                    )
                  ).map(([category, categoryThresholds]) => {
                    const Icon = getCategoryIcon(category)
                    const isExpanded = expandedCategories.has(category)
                    
                    return (
                      <Card key={category} className="border-l-4 border-l-blue-500">
                        <CardHeader 
                          className="cursor-pointer hover:bg-gray-50 transition-colors"
                          onClick={() => toggleCategory(category)}
                        >
                          <CardTitle className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <Icon className="h-5 w-5" />
                              <span className="capitalize">{category} Thresholds</span>
                              <Badge variant="secondary">{categoryThresholds.length}</Badge>
                            </div>
                            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                          </CardTitle>
                        </CardHeader>
                        {isExpanded && (
                          <CardContent className="space-y-4">
                            {categoryThresholds.map((threshold) => (
                              <div key={threshold.name} className="border rounded-lg p-4 bg-gray-50/50">
                                <div className="flex items-center justify-between mb-2">
                                  <div>
                                    <Label className="font-medium">{threshold.display_name}</Label>
                                    <p className="text-sm text-gray-600 mt-1">{threshold.description}</p>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-sm font-mono bg-white px-2 py-1 rounded border">
                                      {threshold.current_value} {threshold.unit}
                                    </span>
                                  </div>
                                </div>
                                <div className="flex items-center gap-4">
                                  <Slider
                                    value={[threshold.current_value]}
                                    onValueChange={(value) => {
                                      updateDynamicThreshold(threshold.name, value[0])
                                    }}
                                    min={threshold.min_value}
                                    max={threshold.max_value}
                                    step={threshold.unit === 'percentage' ? 1 : 0.1}
                                    className="flex-1"
                                  />
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => updateDynamicThreshold(threshold.name, threshold.default_value)}
                                    className="flex items-center gap-1"
                                  >
                                    <RotateCcw className="h-3 w-3" />
                                    Reset
                                  </Button>
                                </div>
                                <div className="flex justify-between text-xs text-gray-500 mt-2">
                                  <span>Min: {threshold.min_value}</span>
                                  <span>Default: {threshold.default_value}</span>
                                  <span>Max: {threshold.max_value}</span>
                                </div>
                              </div>
                            ))}
                          </CardContent>
                        )}
                      </Card>
                    )
                  })}
                  
                  <div className="pt-4 border-t">
                    <Button 
                      onClick={saveThresholds} 
                      disabled={loading}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2"
                    >
                      <Save className="h-4 w-4 mr-2" />
                      {loading ? 'Saving...' : 'Save All Thresholds'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="llm" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="h-5 w-5" />
                    LLM Invocation Configuration
                  </CardTitle>
                  <CardDescription>
                    Configure when and how the LLM judge is invoked based on quality rule results
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div>
                    <Label className="text-base font-medium">LLM Invocation Mode</Label>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
                      {Object.entries(LLM_MODES).map(([mode, config]) => {
                        const IconComponent = config.icon
                        const isSelected = llmSettings.mode === mode
                        
                        return (
                          <button
                            key={mode}
                            onClick={() => updateLLMMode(mode)}
                            className={`p-4 border-2 rounded-lg text-left transition-all ${
                              isSelected 
                                ? 'border-blue-500 bg-blue-50' 
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            <div className="flex items-center gap-3 mb-2">
                              <IconComponent className="h-5 w-5 text-blue-600" />
                              <span className="font-semibold">{config.title}</span>
                              {isSelected && <CheckCircle className="h-4 w-4 text-green-600" />}
                            </div>
                            <p className="text-sm text-gray-600 mb-3">{config.description}</p>
                            <div className={`text-xs px-2 py-1 rounded ${config.color}`}>
                              {config.info}
                            </div>
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  {llmSettings.mode === 'percentage' && (
                    <div className="p-4 border rounded-lg bg-yellow-50">
                      <Label className="font-medium">Percentage Threshold</Label>
                      <p className="text-sm text-gray-600 mb-3">
                        LLM will be invoked when this percentage of quality rules pass
                      </p>
                      <div className="space-y-3">
                        <Slider
                          value={[llmSettings.percentage_threshold]}
                          onValueChange={([value]) => updateLLMThreshold(value)}
                          min={0}
                          max={100}
                          step={5}
                          className="w-full"
                        />
                        <div className="flex items-center gap-4">
                          <Input
                            type="number"
                            value={llmSettings.percentage_threshold}
                            onChange={(e) => updateLLMThreshold(parseInt(e.target.value) || 0)}
                            min={0}
                            max={100}
                            className="w-24"
                          />
                          <span className="text-sm text-gray-500">% of rules must pass</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {llmSettings.mode === 'weighted' && (
                    <div className="space-y-4">
                      <div className="p-4 border rounded-lg bg-green-50">
                        <Label className="font-medium">Weighted Threshold</Label>
                        <p className="text-sm text-gray-600 mb-3">
                          LLM will be invoked when the weighted score exceeds this threshold
                        </p>
                        <div className="space-y-3">
                          <Slider
                            value={[llmSettings.weighted_threshold]}
                            onValueChange={([value]) => updateLLMThreshold(value)}
                            min={0}
                            max={1}
                            step={0.1}
                            className="w-full"
                          />
                          <Input
                            type="number"
                            value={llmSettings.weighted_threshold}
                            onChange={(e) => updateLLMThreshold(parseFloat(e.target.value) || 0)}
                            min={0}
                            max={1}
                            step={0.1}
                            className="w-24"
                          />
                        </div>
                      </div>

                      <div className="p-4 border rounded-lg">
                        <Label className="font-medium mb-3 block">Rule Weights</Label>
                        <div className="space-y-3">
                          {ruleWeights.map((rule) => (
                            <div key={rule.rule_name} className="flex items-center justify-between">
                              <div>
                                <span className="font-medium">{rule.rule_name.replace(/_/g, ' ')}</span>
                                <p className="text-sm text-gray-600">{rule.description}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <Slider
                                  value={[llmSettings.rule_weights[rule.rule_name] || rule.weight]}
                                  onValueChange={([value]) => updateRuleWeight(rule.rule_name, value)}
                                  min={0}
                                  max={5}
                                  step={0.1}
                                  className="w-32"
                                />
                                <Input
                                  type="number"
                                  value={llmSettings.rule_weights[rule.rule_name] || rule.weight}
                                  onChange={(e) => updateRuleWeight(rule.rule_name, parseFloat(e.target.value) || 0)}
                                  min={0}
                                  max={5}
                                  step={0.1}
                                  className="w-20"
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {llmSettings.mode === 'range' && (
                    <div className="p-4 border rounded-lg bg-blue-50">
                      <Label className="font-medium">Range Mode Thresholds</Label>
                      <p className="text-sm text-gray-600 mb-4">
                        Configure the "gray zone" where LLM analysis is triggered
                      </p>
                      
                      <div className="space-y-4">
                        {/* Minimum Threshold */}
                        <div>
                          <Label className="text-sm font-medium text-gray-700">
                            Minimum Threshold (Auto-Reject Below)
                          </Label>
                          <p className="text-xs text-gray-500 mb-2">
                            Content with quality below this will be auto-rejected without LLM analysis
                          </p>
                          <div className="space-y-2">
                            <Slider
                              value={[llmSettings.range_min_threshold ?? 70]}
                              onValueChange={([value]) => setLLMSettings(prev => ({ ...prev, range_min_threshold: value }))}
                              min={0}
                              max={100}
                              step={1}
                              className="w-full"
                            />
                            <div className="flex items-center gap-4">
                              <Input
                                type="number"
                                value={llmSettings.range_min_threshold ?? 70}
                                onChange={(e) => setLLMSettings(prev => ({ ...prev, range_min_threshold: parseInt(e.target.value) || 0 }))}
                                min={0}
                                max={100}
                                className="w-24"
                              />
                              <span className="text-sm text-gray-500">% (auto-reject below)</span>
                            </div>
                          </div>
                        </div>

                        {/* Maximum Threshold */}
                        <div>
                          <Label className="text-sm font-medium text-gray-700">
                            Maximum Threshold (Auto-Approve Above)
                          </Label>
                          <p className="text-xs text-gray-500 mb-2">
                            Content with quality above this will be auto-approved without LLM analysis
                          </p>
                          <div className="space-y-2">
                            <Slider
                              value={[llmSettings.range_max_threshold ?? 80]}
                              onValueChange={([value]) => setLLMSettings(prev => ({ ...prev, range_max_threshold: value }))}
                              min={0}
                              max={100}
                              step={1}
                              className="w-full"
                            />
                            <div className="flex items-center gap-4">
                              <Input
                                type="number"
                                value={llmSettings.range_max_threshold ?? 80}
                                onChange={(e) => setLLMSettings(prev => ({ ...prev, range_max_threshold: parseInt(e.target.value) || 0 }))}
                                min={0}
                                max={100}
                                className="w-24"
                              />
                              <span className="text-sm text-gray-500">% (auto-approve above)</span>
                            </div>
                          </div>
                        </div>

                        {/* Gray Zone Visualization */}
                        <div className="mt-4 p-3 bg-gray-50 rounded border">
                          <Label className="text-sm font-medium text-gray-700 mb-2 block">
                            Current Gray Zone (LLM Triggered)
                          </Label>
                          <div className="text-center">
                            <span className="text-lg font-semibold text-blue-600">
                              {llmSettings.range_min_threshold ?? 70}% - {llmSettings.range_max_threshold ?? 80}%
                            </span>
                            <p className="text-xs text-gray-500 mt-1">
                              LLM analysis will only run for content scoring within this range
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="pt-4 border-t">
                    <Button 
                      onClick={saveLLMSettings} 
                      disabled={loading}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2"
                    >
                      <Save className="h-4 w-4 mr-2" />
                      {loading ? 'Saving...' : 'Save LLM Settings'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="simulation" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Play className="h-5 w-5" />
                    LLM Decision Simulation
                  </CardTitle>
                  <CardDescription>
                    Test how your LLM settings will behave with sample content
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div>
                    <Label className="font-medium">Current Configuration</Label>
                    <div className="mt-2 p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-4">
                        <Badge className={LLM_MODES[llmSettings.mode as keyof typeof LLM_MODES]?.color}>
                          {LLM_MODES[llmSettings.mode as keyof typeof LLM_MODES]?.title}
                        </Badge>
                        <span className="text-sm">
                          🔧 Using Dynamic Unified Config Values
                        </span>
                      </div>
                      <div className="text-xs text-gray-600 mt-2">
                        Simulation automatically uses current threshold values from your Unified Config settings - no hardcoded values!
                      </div>
                    </div>
                  </div>

                  <div>
                    <Label className="font-medium">Sample JSON Input</Label>
                    <Textarea
                      value={simulationInput}
                      onChange={(e) => setSimulationInput(e.target.value)}
                      placeholder={`{
  "record_id": "test-123",
  "document_text": "Your sample content here...",
  "tags": ["tag1", "tag2"],
  "source_connector": "SharePoint"
}`}
                      className="h-40 mt-2 font-mono text-sm"
                    />
                  </div>

                  <Button 
                    onClick={simulateLLMDecision} 
                    disabled={loading || !simulationInput.trim()}
                    className="bg-green-600 hover:bg-green-700 text-white"
                  >
                    <Play className="h-4 w-4 mr-2" />
                    {loading ? 'Simulating...' : 'Simulate LLM Decision'}
                  </Button>

                  {simulationResult && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          {simulationResult.error ? (
                            <AlertTriangle className="h-5 w-5 text-red-600" />
                          ) : (
                            <CheckCircle className="h-5 w-5 text-green-600" />
                          )}
                          Simulation Results
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        {simulationResult.error ? (
                          <div className="text-red-600">
                            <p className="font-medium">Error:</p>
                            <p>{simulationResult.error}</p>
                            {simulationResult.details && <p className="text-sm mt-1">{simulationResult.details}</p>}
                          </div>
                        ) : (
                          <div className="space-y-4">
                            <div className="flex items-center gap-3">
                              <span className="font-medium">LLM Will Trigger:</span>
                              <Badge className={simulationResult.decision?.should_invoke_llm ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                                {simulationResult.decision?.should_invoke_llm ? '✅ YES' : '❌ NO'}
                              </Badge>
                            </div>
                            
                            <div>
                              <span className="font-medium">Confidence: </span>
                              <span>{Math.round((simulationResult.decision?.confidence || 0) * 100)}%</span>
                            </div>
                            
                            <div>
                              <span className="font-medium">Reasoning: </span>
                              <p className="text-gray-700 mt-1">{simulationResult.decision?.reason || 'No reasoning provided'}</p>
                            </div>

                            <div>
                              <span className="font-medium">Threshold Used: </span>
                              <span className="font-mono bg-gray-100 px-2 py-1 rounded">{simulationResult.decision?.threshold_used}</span>
                            </div>

                            {simulationResult.decision?.rules_summary && (
                              <div>
                                <span className="font-medium">Rules Summary: </span>
                                <div className="mt-2 p-3 bg-gray-50 rounded">
                                  <div className="grid grid-cols-3 gap-4 text-sm">
                                    <div>Total Rules: {simulationResult.decision.rules_summary.total_rules}</div>
                                    <div className="text-green-600">Passed: {simulationResult.decision.rules_summary.passed_rules}</div>
                                    <div className="text-red-600">Failed: {simulationResult.decision.rules_summary.failed_rules}</div>
                                  </div>
                                  <div className="mt-2">
                                    <span className="font-medium">Pass Rate: </span>
                                    <span>{Math.round(simulationResult.decision.rules_summary.pass_rate || 0)}%</span>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
} 