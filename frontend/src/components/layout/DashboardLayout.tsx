'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  Home,
  BarChart3,
  Settings,
  Bell,
  Search,
  Menu,
  X,
  Database,
  FileText,
  AlertTriangle,
  User,
  LogOut,
  RefreshCw,
  Download,
  Terminal,
  Server,
  Archive
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavigationItem {
  label: string
  href: string
  icon: React.ComponentType<any>
  badge?: number
  children?: NavigationItem[]
}

interface DashboardLayoutProps {
  children: React.ReactNode
}

const navigation: NavigationItem[] = [
  {
    label: 'Dashboard',
    href: '/',
    icon: Home,
  },
  {
    label: 'Quality Records',
    href: '/records',
    icon: FileText,
    // badge: 127,
  },
  {
    label: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
  },
  {
    label: 'Issues',
    href: '/issues',
    icon: AlertTriangle,
    // badge: 23,
  },
  {
    label: 'Dead Letters',
    href: '/dead-letters',
    icon: Database,
  },
  {
    label: 'Settings',
    href: '/settings',
    icon: Settings,
  },
  {
    label: 'API Testing',
    href: '/api-test',
    icon: Terminal,
  },
  {
    label: 'Backend Tests',
    href: '/backend-test',
    icon: Server,
  },
]

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [notifications, setNotifications] = useState(3)
  const [isOnline, setIsOnline] = useState<boolean | null>(null) // null = loading
  const [mounted, setMounted] = useState(false)
  const pathname = usePathname()

  // Ensure component is mounted before rendering client-side content
  useEffect(() => {
    setMounted(true)
  }, [])

  // Check backend connection status
  useEffect(() => {
    if (!mounted) return

    const checkConnection = async () => {
      try {
        const response = await fetch('/api/health')
        setIsOnline(response.ok)
      } catch {
        setIsOnline(false)
      }
    }

    checkConnection()
    const interval = setInterval(checkConnection, 30000) // Check every 30s

    return () => clearInterval(interval)
  }, [mounted])

  const isActiveRoute = (href: string) => {
    if (href === '/') {
      return pathname === '/'
    }
    return pathname.startsWith(href)
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-50 bg-gray-600 bg-opacity-75 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar - Desktop */}
      <div className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0">
        <div className="flex flex-col flex-grow bg-white border-r border-gray-200 pt-5 pb-4 overflow-y-auto">
          {/* Logo */}
          <div className="flex items-center flex-shrink-0 px-4">
          <div className="h-8 w-8 rounded-lg flex items-center justify-center overflow-hidden">
            <img 
              src="/lucy.png"
              alt="Indexing QA Logo" 
              className="h-8 w-8 object-contain"
            />
          </div>
          <span className="ml-3 text-xl font-bold text-gray-900">Indexing QA</span>
        </div>

          {/* Connection Status - Only render when mounted */}
          {mounted && (
            <div className="px-4 py-3 mt-5 border-b border-gray-200">
              <div className={cn(
                "flex items-center space-x-2 text-xs",
                isOnline === null ? "text-gray-500" : isOnline ? "text-green-600" : "text-red-600"
              )}>
                <div className={cn(
                  "h-2 w-2 rounded-full",
                  isOnline === null ? "bg-gray-400" : isOnline ? "bg-green-500" : "bg-red-500"
                )} />
                <span className="font-medium">
                  {isOnline === null ? 'Checking...' : isOnline ? 'Backend Connected' : 'Backend Offline'}
                </span>
              </div>
            </div>
          )}

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1">
            {navigation.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors",
                  isActiveRoute(item.href)
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-700 hover:bg-gray-50 hover:text-gray-900"
                )}
                onClick={() => setSidebarOpen(false)}
              >
                <item.icon className={cn(
                  "mr-3 h-5 w-5 flex-shrink-0",
                  isActiveRoute(item.href) ? "text-blue-500" : "text-gray-400 group-hover:text-gray-500"
                )} />
                <span className="flex-1">{item.label}</span>
                {item.badge && (
                  <span className={cn(
                    "ml-3 inline-block py-0.5 px-2 text-xs rounded-full font-medium",
                    isActiveRoute(item.href)
                      ? "bg-blue-100 text-blue-600"
                      : "bg-gray-100 text-gray-600 group-hover:bg-gray-200"
                  )}>
                    {item.badge}
                  </span>
                )}
              </Link>
            ))}
          </nav>

          {/* User Menu */}
          <div className="flex-shrink-0 border-t border-gray-200 p-4">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="h-8 w-8 bg-gray-300 rounded-full flex items-center justify-center">
                  <User className="h-5 w-5 text-gray-600" />
                </div>
              </div>
              <div className="ml-3 flex-1">
                <p className="text-sm font-medium text-gray-700">Admin User</p>
                <p className="text-xs text-gray-500">admin@indexingqa.com</p>
              </div>
              <button className="ml-3 flex-shrink-0 p-1 rounded-md text-gray-400 hover:text-gray-500">
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Sidebar */}
      <div className={cn(
        "fixed inset-y-0 left-0 z-50 w-64 bg-white transform transition-transform duration-300 ease-in-out lg:hidden",
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex h-16 items-center justify-between px-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 rounded-lg flex items-center justify-center overflow-hidden">
              <img 
                src="frontend/public/lucy.png" 
                alt="Indexing QA Logo" 
                className="h-8 w-8 object-contain"
              />
            </div>
            <span className="text-xl font-bold text-gray-900">Indexing QA</span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-1 rounded-md hover:bg-gray-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

          {/* Mobile Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors",
                  isActiveRoute(item.href)
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-700 hover:bg-gray-50 hover:text-gray-900"
                )}
                onClick={() => setSidebarOpen(false)}
              >
                <item.icon className={cn(
                  "mr-3 h-5 w-5 flex-shrink-0",
                  isActiveRoute(item.href) ? "text-blue-500" : "text-gray-400 group-hover:text-gray-500"
                )} />
                <span className="flex-1">{item.label}</span>
                {item.badge && (
                  <span className={cn(
                    "ml-3 inline-block py-0.5 px-2 text-xs rounded-full font-medium",
                    isActiveRoute(item.href)
                      ? "bg-blue-100 text-blue-600"
                      : "bg-gray-100 text-gray-600 group-hover:bg-gray-200"
                  )}>
                    {item.badge}
                  </span>
                )}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      {/* Main content area */}
      <div className="flex-1 lg:ml-64">
        {/* Top bar */}
        <div className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-40">
          <div className="px-4 sm:px-6 lg:px-8">
            <div className="flex h-16 items-center justify-between">
              {/* Mobile menu button */}
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
              >
                <Menu className="h-5 w-5" />
              </button>

              {/* Search bar */}
              <div className="hidden sm:block flex-1 max-w-md ml-4 lg:ml-0">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search records..."
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Right side actions */}
              <div className="flex items-center space-x-4">
                <button className="p-2 text-gray-400 hover:text-gray-500 rounded-md hover:bg-gray-100">
                  <RefreshCw className="h-5 w-5" />
                </button>
                <button className="relative p-2 text-gray-400 hover:text-gray-500 rounded-md hover:bg-gray-100">
                  <Bell className="h-5 w-5" />
                  {notifications > 0 && (
                    <span className="absolute top-0 right-0 h-4 w-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                      {notifications}
                    </span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Page content - Fully flexible and scrollable */}
        <main className="flex-1">
          <div className="py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
} 