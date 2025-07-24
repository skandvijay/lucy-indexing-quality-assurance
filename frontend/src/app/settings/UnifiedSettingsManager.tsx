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
  const [activeTab, setActiveTab] = useState('thresholds')
  const [thresholds, setThresholds] = useState<Threshold[]>([])
  const [llmSettings, setLLMSettings] = useState<LLMSettings>({
    mode: 'percentage',
    percentage_threshold: 85,
    weighted_threshold: 0.8,
    range_min_threshold: 70,
    range_max_threshold: 80,
    rule_weights: {}
  })
  const [configs, setConfigs] = useState<ConfigItem[]>([])
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['quality']))
  const [loading, setLoading] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')
  const [simulationInput, setSimulationInput] = useState('')
  const [simulationResult, setSimulationResult] = useState<any>(null)
  const [ruleWeights, setRuleWeights] = useState<any[]>([])

  // Load initial data
  useEffect(() => {
    Promise.all([
      loadThresholds(),
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
          threshold: llmSettings.mode === 'percentage' ? llmSettings.percentage_threshold : llmSettings.weighted_threshold,
          sample_input: input,
          rule_weights: llmSettings.rule_weights
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
    switch (category.toLowerCase()) {
      case 'quality': return Shield
      case 'llm': return Zap
      case 'cost': return Target
      case 'rules': return Database
      default: return Settings
    }
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
            <TabsList className="grid w-full grid-cols-3 mb-6">
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
                  {Object.entries(groupedThresholds).map(([category, categoryThresholds]) => {
                    const IconComponent = getCategoryIcon(category)
                    const isExpanded = expandedCategories.has(category)
                    
                    return (
                      <div key={category} className="border rounded-lg">
                        <button
                          onClick={() => toggleCategory(category)}
                          className="w-full p-4 text-left bg-gray-50 hover:bg-gray-100 rounded-t-lg flex items-center justify-between"
                        >
                          <div className="flex items-center gap-3">
                            <IconComponent className="h-5 w-5 text-blue-600" />
                            <span className="font-semibold capitalize">{category} Settings</span>
                            <Badge variant="outline">{categoryThresholds.length} thresholds</Badge>
                          </div>
                          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                        </button>
                        
                        {isExpanded && (
                          <div className="p-4 space-y-4 bg-white">
                            {categoryThresholds.map((threshold) => (
                              <div key={threshold.name} className="p-4 border rounded-lg bg-gray-50">
                                <div className="flex items-center justify-between mb-3">
                                  <div>
                                    <Label className="font-medium">{threshold.name.replace(/_/g, ' ').toUpperCase()}</Label>
                                    <p className="text-sm text-gray-600 mt-1">{threshold.description}</p>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-sm text-gray-500">
                                      Current: {threshold.current_value} {threshold.unit}
                                    </span>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      onClick={() => resetThreshold(threshold.name)}
                                      className="p-2"
                                    >
                                      <RotateCcw className="h-3 w-3" />
                                    </Button>
                                  </div>
                                </div>
                                
                                <div className="space-y-3">
                                  <Slider
                                    value={[threshold.current_value]}
                                    onValueChange={([value]) => updateThresholdValue(threshold.name, value)}
                                    min={threshold.min_value}
                                    max={threshold.max_value}
                                    step={threshold.unit === 'percentage' ? 1 : 0.1}
                                    className="w-full"
                                  />
                                  <div className="flex justify-between text-xs text-gray-500">
                                    <span>Min: {threshold.min_value}</span>
                                    <span>Default: {threshold.default_value}</span>
                                    <span>Max: {threshold.max_value}</span>
                                  </div>
                                  <Input
                                    type="number"
                                    value={threshold.current_value}
                                    onChange={(e) => updateThresholdValue(threshold.name, parseFloat(e.target.value) || 0)}
                                    min={threshold.min_value}
                                    max={threshold.max_value}
                                    step={threshold.unit === 'percentage' ? 1 : 0.1}
                                    className="w-32"
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
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
                          Threshold: {llmSettings.mode === 'percentage' 
                            ? `${llmSettings.percentage_threshold}%` 
                            : llmSettings.weighted_threshold
                          }
                        </span>
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
                              <Badge className={simulationResult.should_invoke_llm ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                                {simulationResult.should_invoke_llm ? '✅ YES' : '❌ NO'}
                              </Badge>
                            </div>
                            
                            <div>
                              <span className="font-medium">Confidence: </span>
                              <span>{Math.round(simulationResult.confidence * 100)}%</span>
                            </div>
                            
                            <div>
                              <span className="font-medium">Reasoning: </span>
                              <p className="text-gray-700 mt-1">{simulationResult.reason}</p>
                            </div>

                            {simulationResult.rules_summary && (
                              <div>
                                <span className="font-medium">Rules Summary:</span>
                                <pre className="mt-2 p-3 bg-gray-50 rounded text-sm overflow-auto">
                                  {JSON.stringify(simulationResult.rules_summary, null, 2)}
                                </pre>
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