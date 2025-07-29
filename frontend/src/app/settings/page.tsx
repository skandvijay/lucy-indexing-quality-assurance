'use client'

import React from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import { Settings as SettingsIcon } from 'lucide-react'
import UnifiedSettingsManager from './UnifiedSettingsManager'

export default function SettingsPage() {
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
              Unified configuration management - all settings in one place following SOLID principles
            </p>
          </div>
        </div>

        {/* Single Unified Settings Manager - No Redundant Components */}
        <div className="bg-white rounded-lg shadow-sm">
          <UnifiedSettingsManager />
        </div>
      </div>
    </DashboardLayout>
  )
} 