'use client'

import React from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import ApiTestInterface from '@/components/api/ApiTestInterface'

export default function ApiTestPage() {
  return (
    <DashboardLayout>
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">API Test Interface</h1>
          <p className="text-gray-600 mt-2">
            Test all backend API endpoints and verify functionality
          </p>
        </div>
        <ApiTestInterface />
      </div>
    </DashboardLayout>
  )
} 