import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'

import { nextRoute } from '@/auth/nextRoute'
import { useAuth } from '@/auth/useAuth'
import { Alert, Button } from '@/components/ui'
import { DEV_ACCOUNTS } from '@/lib/devAccounts'
import { errorMessage } from '@/lib/errors'
import { AuthCard } from './authShared'

export function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const destination = nextRoute(location.search)

  if (user) return <Navigate to={destination} replace />

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await login(email.trim(), password)
      void navigate(destination, { replace: true })
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setIsSubmitting(false)
    }
  }

  function fillDevAccount(devEmail: string, devPassword: string) {
    setEmail(devEmail)
    setPassword(devPassword)
    setError(null)
  }

  return (
    <AuthCard
      title="Sign in"
      subtitle="Report an issue, dispatch a job, or pick up your next intervention."
      footer={
        <p className="text-sm text-muted">
          No account yet?{' '}
          <Link to="/register" className="font-medium text-brand-600 hover:underline">
            Create one
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && <Alert>{error}</Alert>}

        <div>
          <label className="label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            className="input"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label className="label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            className="input"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••"
          />
        </div>

        <Button type="submit" loading={isSubmitting} className="w-full">
          Sign in
        </Button>
      </form>

      {import.meta.env.DEV && (
        <div className="mt-6 border-t border-line pt-4">
          <p className="text-xs font-medium text-muted">
            Development accounts (seeded by <code>python -m scripts.seed</code>)
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {DEV_ACCOUNTS.map((account) => (
              <button
                key={account.email}
                type="button"
                onClick={() => fillDevAccount(account.email, account.password)}
                className="rounded-md bg-canvas px-2 py-1 text-xs font-medium text-muted ring-1 ring-inset ring-line transition hover:text-ink"
              >
                {account.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </AuthCard>
  )
}
