'use client'

import React, { useState } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { 
  Sliders, 
  Settings as SettingsIcon, 
  Zap, 
  Mail, 
  Database,
  AlertTriangle
} from 'lucide-react'

// Import all settings components
import ThresholdsTab from './thresholds/ThresholdsTab'
import UnifiedSettingsManager from './UnifiedSettingsManager'
import LLMInvocationSettings from './thresholds/LLMInvocationSettings'
// import EmailAlertsTab from './alerts/EmailAlertsTab'  // Commented out - file is empty

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('unified')

  const tabs = [
    {
      id: 'unified',
      label: 'Unified Config',
      icon: Database,
      description: 'Central configuration management'
    },
    {
      id: 'thresholds',
      label: 'Dynamic Thresholds',
      icon: Sliders,
      description: 'Quality control thresholds'
    },
    {
      id: 'llm-legacy',
      label: 'LLM Invocation Legacy',
      icon: Zap,
      description: 'LLM invocation settings'
    },
    {
      id: 'alerts',
      label: 'Email Alerts',
      icon: Mail,
      description: 'Alert configurations'
    },
    {
      id: 'advanced',
      label: 'Advanced',
      icon: AlertTriangle,
      description: 'Advanced system configuration'
    }
  ]

  const renderTabContent = () => {
    switch (activeTab) {
      case 'unified':
        return <UnifiedSettingsManager />
      case 'thresholds':
        return <ThresholdsTab />
      case 'llm-legacy':
        return <LLMInvocationSettings />
      case 'alerts':
        // return <EmailAlertsTab />  // Commented out - component not implemented
        return <div className="p-6 text-center text-gray-500">Email alerts configuration coming soon...</div>
      default:
        return <UnifiedSettingsManager />
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center">
              <SettingsIcon className="h-8 w-8 mr-3 text-blue-600" />
              Settings
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              Configure system settings, thresholds, and integrations
            </p>
          </div>
        </div>

        <div className="flex gap-6">
          {/* Sidebar Navigation */}
          <div className="w-64 bg-white rounded-lg shadow-sm">
            <nav className="p-4 space-y-2">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-start px-3 py-3 text-sm font-medium rounded-md transition-colors ${
                    activeTab === tab.id
                      ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <tab.icon className={`h-5 w-5 mr-3 flex-shrink-0 mt-0.5 ${
                    activeTab === tab.id ? 'text-blue-500' : 'text-gray-400'
                  }`} />
                  <div className="text-left">
                    <div className="font-medium">{tab.label}</div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {tab.description}
                    </div>
              </div>
                </button>
              ))}
            </nav>
          </div>

          {/* Main Content */}
          <div className="flex-1 bg-white rounded-lg shadow-sm">
            <div className="p-6">
              {/* Tab Header */}
              <div className="mb-6 border-b border-gray-200 pb-4">
                <div className="flex items-center">
                  {(() => {
                    const currentTab = tabs.find(tab => tab.id === activeTab)
                    const Icon = currentTab?.icon || Database
                    return (
                      <>
                        <Icon className="h-6 w-6 mr-3 text-blue-600" />
                        <div>
                          <h2 className="text-xl font-semibold text-gray-900">
                            {currentTab?.label}
                          </h2>
                          <p className="text-sm text-gray-500">
                            {currentTab?.description}
                          </p>
                        </div>
                      </>
                    )
                  })()}
                </div>
              </div>

              {/* Tab Content */}
              <div className="relative">
                {renderTabContent()}
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
} 