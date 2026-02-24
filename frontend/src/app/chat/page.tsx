'use client'

import { motion } from 'framer-motion'
import { AppLayout } from '@/components/Layout/AppLayout'
import { ChatInterface } from '@/components/Chat/ChatInterface'

export default function ChatPage() {
  return (
    <AppLayout>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="h-screen flex flex-col"
      >
        {/* Header */}
        <div className="p-4 border-b border-surface-200 bg-white/80 backdrop-blur-sm">
          <h1 className="text-xl font-display font-semibold text-surface-900">
            Chat with NidanMitra AI
          </h1>
          <p className="text-sm text-surface-500">
            Ask questions about your health, medications, or medical reports
          </p>
        </div>

        {/* Chat Interface */}
        <div className="flex-1 overflow-hidden">
          <ChatInterface />
        </div>
      </motion.div>
    </AppLayout>
  )
}

