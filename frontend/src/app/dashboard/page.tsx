'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  MessageCircle,
  FileText,
  Pill,
  Activity,
  ArrowRight,
  Clock,
  TrendingUp,
  Calendar,
  Sun,
  CheckCircle,
  AlertCircle,
  Sparkles,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { AppLayout } from '@/components/Layout/AppLayout'
import { useStore } from '@/lib/store'
import { dashboardAPI, medicationsAPI, symptomsAPI } from '@/lib/api'

interface DashboardStats {
  overview: {
    active_medications: number
    recent_symptoms: number
    medical_reports: number
    recent_conversations: number
  }
  symptom_trend: string
  medication_adherence?: number
  last_report_date?: string
}

interface HealthSummary {
  summary: string
  overview: DashboardStats['overview']
  medications: any[]
  recent_symptoms: any[]
  reports: any[]
  generated_at: string
  disclaimer: string
}

export default function DashboardPage() {
  const { t } = useTranslation()
  const { user } = useStore()
  
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [healthSummary, setHealthSummary] = useState<HealthSummary | null>(null)
  const [isLoadingStats, setIsLoadingStats] = useState(true)
  const [isLoadingSummary, setIsLoadingSummary] = useState(false)
  const [medications, setMedications] = useState<any[]>([])
  const [symptoms, setSymptoms] = useState<any[]>([])
  
  const greeting = getGreeting()
  const today = new Date().toLocaleDateString('en-US', { 
    weekday: 'long', 
    month: 'long', 
    day: 'numeric' 
  })

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    setIsLoadingStats(true)
    try {
      const [statsRes, medsRes, symptomsRes] = await Promise.all([
        dashboardAPI.getStats(),
        medicationsAPI.getAll(true),
        symptomsAPI.getAll(7),
      ])
      setStats(statsRes.data)
      setMedications(medsRes.data.slice(0, 5))
      setSymptoms(symptomsRes.data.slice(0, 3))
    } catch (err) {
      console.error('Failed to load dashboard:', err)
    } finally {
      setIsLoadingStats(false)
    }
  }

  const loadHealthSummary = async () => {
    setIsLoadingSummary(true)
    try {
      const response = await dashboardAPI.getHealthSummary(30)
      setHealthSummary(response.data)
    } catch (err) {
      console.error('Failed to load health summary:', err)
    } finally {
      setIsLoadingSummary(false)
    }
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving': return '📈'
      case 'worsening': return '📉'
      case 'stable': return '➡️'
      default: return '❓'
    }
  }

  return (
    <AppLayout>
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center gap-3 mb-2">
            <Sun className="w-6 h-6 text-accent-500" />
            <span className="text-surface-500">{today}</span>
          </div>
          <h1 className="text-3xl font-display font-bold text-surface-900">
            {greeting}, {user?.full_name || 'there'}! 👋
          </h1>
          <p className="text-surface-600 mt-1">
            Here's your health overview for today
          </p>
        </motion.div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            {
              icon: Pill,
              label: 'Active Medications',
              value: isLoadingStats ? '-' : String(stats?.overview.active_medications || 0),
              subtext: 'being tracked',
              color: 'primary',
            },
            {
              icon: Activity,
              label: 'Symptoms (30d)',
              value: isLoadingStats ? '-' : String(stats?.overview.recent_symptoms || 0),
              subtext: stats?.symptom_trend ? `Trend: ${getTrendIcon(stats.symptom_trend)} ${stats.symptom_trend}` : 'logged recently',
              color: 'accent',
            },
            {
              icon: FileText,
              label: 'Medical Reports',
              value: isLoadingStats ? '-' : String(stats?.overview.medical_reports || 0),
              subtext: 'uploaded',
              color: 'primary',
            },
            {
              icon: MessageCircle,
              label: 'AI Conversations',
              value: isLoadingStats ? '-' : String(stats?.overview.recent_conversations || 0),
              subtext: 'this month',
              color: 'accent',
            },
          ].map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="card p-5"
            >
              <div className="flex items-start justify-between">
                <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${
                  stat.color === 'primary' ? 'bg-primary-100' : 'bg-accent-100'
                }`}>
                  <stat.icon className={`w-5 h-5 ${
                    stat.color === 'primary' ? 'text-primary-600' : 'text-accent-600'
                  }`} />
                </div>
              </div>
              <div className="mt-4">
                <p className="text-2xl font-display font-bold text-surface-900">
                  {stat.value}
                </p>
                <p className="text-sm text-surface-500">{stat.subtext}</p>
              </div>
            </motion.div>
          ))}
        </div>

        {/* AI Health Summary Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mb-6 card"
        >
          <div className="p-4 border-b border-surface-100 flex items-center justify-between">
            <h2 className="font-display font-semibold text-surface-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary-600" />
              AI Health Summary
            </h2>
            <button
              onClick={loadHealthSummary}
              disabled={isLoadingSummary}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              {isLoadingSummary ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              {healthSummary ? 'Refresh' : 'Generate Summary'}
            </button>
          </div>
          
          <div className="p-4">
            {isLoadingSummary ? (
              <div className="flex flex-col items-center justify-center py-8">
                <Sparkles className="w-10 h-10 text-primary-600 animate-pulse mb-3" />
                <p className="text-surface-600">Analyzing your health data...</p>
                <p className="text-sm text-surface-400">This may take a moment</p>
              </div>
            ) : healthSummary ? (
              <div className="prose prose-sm max-w-none prose-p:my-2 prose-ul:my-2 prose-li:my-0.5 prose-headings:my-2 prose-headings:font-semibold">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {healthSummary.summary}
                </ReactMarkdown>
                <div className="mt-4 p-3 bg-surface-50 rounded-lg text-xs text-surface-500">
                  {healthSummary.disclaimer}
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <Sparkles className="w-10 h-10 mx-auto text-surface-300 mb-3" />
                <p className="text-surface-600 mb-2">Get a personalized AI health summary</p>
                <p className="text-sm text-surface-400">
                  Click "Generate Summary" to analyze your medications, symptoms, and reports
                </p>
              </div>
            )}
          </div>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Active Medications */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="lg:col-span-2 card"
          >
            <div className="p-4 border-b border-surface-100 flex items-center justify-between">
              <h2 className="font-display font-semibold text-surface-900 flex items-center gap-2">
                <Pill className="w-5 h-5 text-primary-600" />
                {t('dashboard.medications')}
              </h2>
              <Link href="/medications" className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1">
                View all <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
            
            <div className="divide-y divide-surface-100">
              {medications.length === 0 ? (
                <div className="p-8 text-center">
                  <Pill className="w-10 h-10 mx-auto text-surface-300 mb-3" />
                  <p className="text-surface-500">No medications tracked yet</p>
                  <Link href="/medications" className="text-sm text-primary-600 hover:text-primary-700 mt-2 inline-block">
                    Add your first medication →
                  </Link>
                </div>
              ) : (
                medications.map((med, index) => (
                  <div key={med.id} className="p-4 flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-primary-50 flex items-center justify-center">
                      <Pill className="w-5 h-5 text-primary-600" />
                    </div>
                    <div className="flex-1">
                      <span className="font-medium text-surface-900">
                        {med.name}
                      </span>
                      <span className="text-sm ml-2 text-surface-600">
                        {med.dosage}
                      </span>
                      <p className="text-xs text-surface-500 mt-0.5">
                        {med.frequency} • {med.purpose || 'Purpose not specified'}
                      </p>
                    </div>
                    <Link 
                      href={`/medications`}
                      className="text-sm text-primary-600 hover:text-primary-700"
                    >
                      Details
                    </Link>
                  </div>
                ))
              )}
            </div>
          </motion.div>

          {/* Quick Actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="card p-4"
          >
            <h2 className="font-display font-semibold text-surface-900 mb-4">
              {t('dashboard.quickActions')}
            </h2>
            
            <div className="space-y-2">
              {[
                { icon: MessageCircle, label: 'Ask AI a Question', href: '/chat', color: 'primary' },
                { icon: FileText, label: 'Upload a Report', href: '/reports', color: 'accent' },
                { icon: Activity, label: 'Log a Symptom', href: '/symptoms', color: 'primary' },
                { icon: Calendar, label: 'View Medications', href: '/medications', color: 'accent' },
              ].map((action) => (
                <Link
                  key={action.label}
                  href={action.href}
                  className="flex items-center gap-3 p-3 rounded-xl hover:bg-surface-50 transition-colors group"
                >
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    action.color === 'primary' ? 'bg-primary-100' : 'bg-accent-100'
                  }`}>
                    <action.icon className={`w-5 h-5 ${
                      action.color === 'primary' ? 'text-primary-600' : 'text-accent-600'
                    }`} />
                  </div>
                  <span className="flex-1 font-medium text-surface-700 group-hover:text-surface-900">
                    {action.label}
                  </span>
                  <ArrowRight className="w-5 h-5 text-surface-400 group-hover:text-surface-600 transition-colors" />
                </Link>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Recent Symptoms */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="mt-6 card"
        >
          <div className="p-4 border-b border-surface-100 flex items-center justify-between">
            <h2 className="font-display font-semibold text-surface-900 flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary-600" />
              {t('dashboard.symptoms')}
            </h2>
            <Link href="/symptoms" className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1">
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          
          <div className="p-4">
            <div className="flex gap-4 overflow-x-auto pb-2">
              {symptoms.length === 0 ? (
                <div className="flex-1 text-center py-4">
                  <Activity className="w-8 h-8 mx-auto text-surface-300 mb-2" />
                  <p className="text-surface-500 text-sm">No symptoms logged recently</p>
                </div>
              ) : (
                symptoms.map((entry) => (
                  <div
                    key={entry.id}
                    className="flex-shrink-0 w-48 p-4 rounded-xl bg-surface-50 border border-surface-200"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-surface-900">{entry.symptom}</span>
                      <span className={`text-sm font-bold ${
                        entry.severity <= 3 ? 'text-success' :
                        entry.severity <= 6 ? 'text-warning' : 'text-emergency'
                      }`}>
                        {entry.severity}/10
                      </span>
                    </div>
                    <span className="text-xs text-surface-500">
                      {new Date(entry.recorded_at).toLocaleDateString()}
                    </span>
                  </div>
                ))
              )}
              
              <Link
                href="/symptoms"
                className="flex-shrink-0 w-48 p-4 rounded-xl border-2 border-dashed border-surface-200 flex items-center justify-center gap-2 text-surface-500 hover:text-surface-700 hover:border-surface-300 transition-colors"
              >
                <Activity className="w-5 h-5" />
                Log Symptom
              </Link>
            </div>
          </div>
        </motion.div>

        {/* Health Tip */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="mt-6 card p-6 bg-gradient-to-r from-primary-50 to-accent-50"
        >
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-white shadow-soft flex items-center justify-center flex-shrink-0">
              <TrendingUp className="w-6 h-6 text-primary-600" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-surface-900 mb-1">
                Daily Health Tip
              </h3>
              <p className="text-surface-600">
                Staying hydrated helps your body absorb medications more effectively. 
                Aim for 8 glasses of water throughout the day, especially when taking pills.
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </AppLayout>
  )
}

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}
