'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  User,
  Globe,
  Eye,
  Volume2,
  Shield,
  Bell,
  Moon,
  LogOut,
  ChevronRight,
  Check,
  HelpCircle,
  RotateCcw,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { AppLayout } from '@/components/Layout/AppLayout'
import { useStore } from '@/lib/store'
import { cn } from '@/lib/utils'

const TUTORIAL_STORAGE_KEYS = [
  'nidanmitra-medications-tutorial',
  'nidanmitra-symptoms-tutorial',
  'nidanmitra-reports-tutorial',
]

export default function SettingsPage() {
  const { t, i18n } = useTranslation()
  const { user, language, setLanguage, largeFontMode, setLargeFontMode, logout } = useStore()
  const [notifications, setNotifications] = useState(true)

  const handleLanguageChange = (lang: string) => {
    setLanguage(lang)
    i18n.changeLanguage(lang)
  }

  return (
    <AppLayout>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="p-6 lg:p-8 max-w-3xl mx-auto"
      >
        <div className="mb-8">
          <h1 className="text-2xl font-display font-semibold text-surface-900">
            {t('nav.settings')}
          </h1>
          <p className="text-surface-500 mt-1">
            Customize your NidanMitra experience
          </p>
        </div>

        <div className="space-y-6">
          {/* Profile Section */}
          <div className="card">
            <div className="p-4 border-b border-surface-100">
              <h2 className="font-medium text-surface-900 flex items-center gap-2">
                <User className="w-5 h-5 text-primary-600" />
                Profile
              </h2>
            </div>
            <div className="p-4">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-2xl bg-primary-100 flex items-center justify-center">
                  <User className="w-8 h-8 text-primary-600" />
                </div>
                <div>
                  <h3 className="font-medium text-surface-900">
                    {user?.full_name || 'Guest User'}
                  </h3>
                  <p className="text-sm text-surface-500">
                    {user?.email || 'Sign in to sync your data'}
                  </p>
                </div>
              </div>
              
              {!user && (
                <button className="btn-primary w-full mt-4">
                  Sign In / Create Account
                </button>
              )}
            </div>
          </div>

          {/* Language Section */}
          <div className="card">
            <div className="p-4 border-b border-surface-100">
              <h2 className="font-medium text-surface-900 flex items-center gap-2">
                <Globe className="w-5 h-5 text-primary-600" />
                Language
              </h2>
            </div>
            <div className="p-4">
              <div className="grid grid-cols-2 gap-2">
                {[
                  { code: 'en', name: 'English' },
                  { code: 'ne', name: 'नेपाली' },
                ].map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => handleLanguageChange(lang.code)}
                    className={cn(
                      'p-3 rounded-xl border-2 text-center transition-all',
                      language === lang.code
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-surface-200 hover:border-surface-300 text-surface-600'
                    )}
                  >
                    <span className="font-medium">{lang.name}</span>
                    {language === lang.code && (
                      <Check className="w-4 h-4 mx-auto mt-1 text-primary-600" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Accessibility Section */}
          <div className="card">
            <div className="p-4 border-b border-surface-100">
              <h2 className="font-medium text-surface-900 flex items-center gap-2">
                <Eye className="w-5 h-5 text-primary-600" />
                Accessibility
              </h2>
            </div>
            <div className="divide-y divide-surface-100">
              <ToggleSetting
                icon={Eye}
                title={t('a11y.largeFont')}
                description="Increase text size for better readability"
                enabled={largeFontMode}
                onToggle={() => setLargeFontMode(!largeFontMode)}
              />
              <ToggleSetting
                icon={Volume2}
                title="Audio Explanations"
                description="Read explanations aloud (coming soon)"
                enabled={false}
                onToggle={() => {}}
                disabled
              />
              <ToggleSetting
                icon={Moon}
                title="Dark Mode"
                description="Reduce eye strain in low light (coming soon)"
                enabled={false}
                onToggle={() => {}}
                disabled
              />
            </div>
          </div>

          {/* Notifications Section */}
          <div className="card">
            <div className="p-4 border-b border-surface-100">
              <h2 className="font-medium text-surface-900 flex items-center gap-2">
                <Bell className="w-5 h-5 text-primary-600" />
                Notifications
              </h2>
            </div>
            <div className="divide-y divide-surface-100">
              <ToggleSetting
                icon={Bell}
                title="Medication Reminders"
                description="Get notified when it's time to take your medication"
                enabled={notifications}
                onToggle={() => setNotifications(!notifications)}
              />
            </div>
          </div>

          {/* Tutorials Section */}
          <div className="card">
            <div className="p-4 border-b border-surface-100">
              <h2 className="font-medium text-surface-900 flex items-center gap-2">
                <HelpCircle className="w-5 h-5 text-primary-600" />
                Help & Tutorials
              </h2>
            </div>
            <div className="divide-y divide-surface-100">
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-surface-900">Page Tutorials</h3>
                    <p className="text-sm text-surface-500 mt-0.5">
                      Reset tutorials to see them again when visiting pages
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      TUTORIAL_STORAGE_KEYS.forEach(key => {
                        localStorage.removeItem(key)
                      })
                      alert('Tutorials reset! Visit each page to see them again.')
                    }}
                    className="btn-secondary flex items-center gap-2"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Reset All
                  </button>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    onClick={() => {
                      localStorage.removeItem('nidanmitra-medications-tutorial')
                      alert('Medications tutorial reset!')
                    }}
                    className="px-3 py-1.5 text-sm bg-surface-100 hover:bg-surface-200 rounded-lg transition-colors"
                  >
                    Medications
                  </button>
                  <button
                    onClick={() => {
                      localStorage.removeItem('nidanmitra-symptoms-tutorial')
                      alert('Symptoms tutorial reset!')
                    }}
                    className="px-3 py-1.5 text-sm bg-surface-100 hover:bg-surface-200 rounded-lg transition-colors"
                  >
                    Symptoms
                  </button>
                  <button
                    onClick={() => {
                      localStorage.removeItem('nidanmitra-reports-tutorial')
                      alert('Reports tutorial reset!')
                    }}
                    className="px-3 py-1.5 text-sm bg-surface-100 hover:bg-surface-200 rounded-lg transition-colors"
                  >
                    Reports
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Privacy Section */}
          <div className="card">
            <div className="p-4 border-b border-surface-100">
              <h2 className="font-medium text-surface-900 flex items-center gap-2">
                <Shield className="w-5 h-5 text-primary-600" />
                Privacy & Security
              </h2>
            </div>
            <div className="divide-y divide-surface-100">
              <LinkSetting
                title="Privacy Policy"
                description="How we handle your data"
              />
              <LinkSetting
                title="Terms of Service"
                description="Our terms and conditions"
              />
              <LinkSetting
                title="Delete My Data"
                description="Permanently remove all your data"
                danger
              />
            </div>
          </div>

          {/* Sign Out */}
          {user && (
            <button
              onClick={logout}
              className="w-full card p-4 flex items-center justify-center gap-2 text-emergency hover:bg-emergency-light transition-colors"
            >
              <LogOut className="w-5 h-5" />
              Sign Out
            </button>
          )}

          {/* App Info */}
          <div className="text-center py-4">
            <p className="text-sm text-surface-400">
              NidanMitra AI v1.0.0
            </p>
            <p className="text-xs text-surface-400 mt-1">
              Educational health information only
            </p>
          </div>
        </div>
      </motion.div>
    </AppLayout>
  )
}

function ToggleSetting({
  icon: Icon,
  title,
  description,
  enabled,
  onToggle,
  disabled = false,
}: {
  icon: any
  title: string
  description: string
  enabled: boolean
  onToggle: () => void
  disabled?: boolean
}) {
  return (
    <div className={cn(
      'p-4 flex items-center gap-4',
      disabled && 'opacity-50'
    )}>
      <div className="w-10 h-10 rounded-lg bg-surface-100 flex items-center justify-center">
        <Icon className="w-5 h-5 text-surface-600" />
      </div>
      <div className="flex-1">
        <h3 className="font-medium text-surface-900">{title}</h3>
        <p className="text-sm text-surface-500">{description}</p>
      </div>
      <button
        onClick={onToggle}
        disabled={disabled}
        className={cn(
          'w-12 h-7 rounded-full transition-colors relative',
          enabled ? 'bg-primary-600' : 'bg-surface-300',
          disabled && 'cursor-not-allowed'
        )}
      >
        <div className={cn(
          'w-5 h-5 rounded-full bg-white shadow-sm absolute top-1 transition-transform',
          enabled ? 'translate-x-6' : 'translate-x-1'
        )} />
      </button>
    </div>
  )
}

function LinkSetting({
  title,
  description,
  danger = false,
}: {
  title: string
  description: string
  danger?: boolean
}) {
  return (
    <button className="w-full p-4 flex items-center gap-4 hover:bg-surface-50 transition-colors text-left">
      <div className="flex-1">
        <h3 className={cn(
          'font-medium',
          danger ? 'text-emergency' : 'text-surface-900'
        )}>
          {title}
        </h3>
        <p className="text-sm text-surface-500">{description}</p>
      </div>
      <ChevronRight className={cn(
        'w-5 h-5',
        danger ? 'text-emergency' : 'text-surface-400'
      )} />
    </button>
  )
}

