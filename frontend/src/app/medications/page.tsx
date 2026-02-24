'use client'

import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { AppLayout } from '@/components/Layout/AppLayout'
import { MedicationTracker } from '@/components/Medications/MedicationTracker'

export default function MedicationsPage() {
  const { t } = useTranslation()

  return (
    <AppLayout>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="p-6 lg:p-8 max-w-5xl mx-auto"
      >
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-display font-semibold text-surface-900">
            {t('meds.title')}
          </h1>
          <p className="text-surface-500 mt-1">
            Track your medications, set reminders, and never miss a dose
          </p>
        </div>

        {/* Medication Tracker */}
        <MedicationTracker />
      </motion.div>
    </AppLayout>
  )
}

