'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Heart, Mail, Lock, Eye, EyeOff, Loader2 } from 'lucide-react'
import { useStore } from '@/lib/store'
import { authAPI } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const { setToken, setUser } = useStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      // Call the real login API
      const response = await authAPI.login({ email, password })
      const { access_token } = response.data
      
      // Store the JWT token
      setToken(access_token)
      
      // Fetch user profile
      try {
        const userResponse = await authAPI.getMe()
        setUser(userResponse.data)
      } catch (userErr) {
        // If getting user fails, still proceed with login
        console.warn('Failed to fetch user profile:', userErr)
        setUser({
          id: 0,
          email: email,
          full_name: email.split('@')[0],
          language: 'en',
        })
      }
      
      router.push('/dashboard')
    } catch (err: any) {
      console.error('Login error:', err)
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials and try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDemoLogin = () => {
    setToken('demo-token')
    setUser({
      id: 1,
      email: 'demo@claricare.ai',
      full_name: 'Demo User',
      language: 'en',
    })
    router.push('/dashboard')
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center shadow-glow">
              <Heart className="w-7 h-7 text-white" />
            </div>
            <div className="text-left">
              <h1 className="font-display font-bold text-xl text-surface-900">NidanMitra</h1>
              <p className="text-xs text-surface-500">AI Health Companion</p>
            </div>
          </Link>
        </div>

        <div className="card p-8">
          <h2 className="text-2xl font-display font-semibold text-surface-900 text-center mb-2">
            Welcome Back
          </h2>
          <p className="text-surface-500 text-center mb-8">
            Sign in to continue your health journey
          </p>

          {error && (
            <div className="mb-4 p-3 bg-emergency-light text-emergency rounded-lg text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-surface-700 mb-2">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="input-field pl-10"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-surface-700 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input-field pl-10 pr-10"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-600"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-surface-200" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-surface-500">or</span>
            </div>
          </div>

          <button
            onClick={handleDemoLogin}
            className="btn-secondary w-full"
          >
            Continue as Demo User
          </button>

          <p className="text-center text-sm text-surface-500 mt-6">
            Don't have an account?{' '}
            <Link href="/auth/register" className="text-primary-600 hover:text-primary-700 font-medium">
              Sign up
            </Link>
          </p>
        </div>

        <p className="text-center text-xs text-surface-400 mt-6">
          By signing in, you agree to our Terms of Service and Privacy Policy
        </p>
      </motion.div>
    </div>
  )
}

