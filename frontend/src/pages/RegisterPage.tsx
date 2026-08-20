import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'

import type { RegisterInput } from '@/api/types'
import { useAuth } from '@/auth/useAuth'
import { useDomainConfig } from '@/hooks/queries'
import { Alert, Button } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { classes, humanise } from '@/lib/format'
import { skillLabel } from '@/lib/domain'
import { AuthCard } from './authShared'

type SelfServiceRole = RegisterInput['role']

const ROLE_CHOICES: { value: SelfServiceRole; description: string }[] = [
  { value: 'REPORTER', description: 'Report elevator incidents in your building.' },
  { value: 'CONTRACTOR', description: 'Take elevator jobs, start work and resolve them.' },
]

export function RegisterPage() {
  const { user, register } = useAuth()
  const navigate = useNavigate()
  const { data: config } = useDomainConfig()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<SelfServiceRole>('REPORTER')
  const [skills, setSkills] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (user) return <Navigate to="/tickets" replace />

  function toggleSkill(skill: string) {
    setSkills((current) =>
      current.includes(skill)
        ? current.filter((value) => value !== skill)
        : [...current, skill],
    )
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await register({
        name: name.trim(),
        email: email.trim(),
        password,
        role,
        skills: role === 'CONTRACTOR' ? skills : [],
      })
      void navigate('/tickets', { replace: true })
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthCard
      title="Create an account"
        subtitle="Sign up to report elevator incidents or to take jobs in the field."
      footer={
        <p className="text-sm text-muted">
          Already registered?{' '}
          <Link to="/login" className="font-medium text-brand-600 hover:underline">
            Sign in
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && <Alert>{error}</Alert>}

        <div>
          <label className="label" htmlFor="name">
            Full name
          </label>
          <input
            id="name"
            className="input"
            required
            minLength={2}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Ahmed Ben Salah"
          />
        </div>

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
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="At least 8 characters"
          />
        </div>

        <fieldset>
          <legend className="label">I am signing up to</legend>
          <div className="grid gap-2">
            {ROLE_CHOICES.map((choice) => (
              <label
                key={choice.value}
                className={classes(
                  'flex cursor-pointer gap-3 rounded-lg border p-3 transition',
                  role === choice.value
                    ? 'border-brand-500 bg-brand-50'
                    : 'border-line hover:bg-canvas',
                )}
              >
                <input
                  type="radio"
                  name="role"
                  className="mt-1 accent-brand-600"
                  checked={role === choice.value}
                  onChange={() => setRole(choice.value)}
                />
                <span>
                  <span className="block text-sm font-medium text-ink">
                    {choice.value === 'CONTRACTOR'
                      ? (config?.worker_label ?? humanise(choice.value))
                      : humanise(choice.value)}
                  </span>
                  <span className="block text-xs text-muted">{choice.description}</span>
                </span>
              </label>
            ))}
          </div>
          <p className="mt-2 text-xs text-muted">
            Dispatcher and administrator accounts are created by an administrator.
          </p>
        </fieldset>

        {role === 'CONTRACTOR' && config && (
          <fieldset>
            <legend className="label">Skills</legend>
            <div className="flex flex-wrap gap-1.5">
              {config.skill_vocabulary.map((skill) => (
                <button
                  key={skill}
                  type="button"
                  onClick={() => toggleSkill(skill)}
                  aria-pressed={skills.includes(skill)}
                  className={classes(
                    'rounded-md px-2.5 py-1 text-xs font-medium ring-1 ring-inset transition',
                    skills.includes(skill)
                      ? 'bg-brand-600 text-white ring-brand-600'
                      : 'bg-canvas text-muted ring-line hover:text-ink',
                  )}
                >
                  {skillLabel(config, skill)}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-muted">
              Skills feed the dispatcher's recommendations; they never block an
              assignment.
            </p>
          </fieldset>
        )}

        <Button type="submit" loading={isSubmitting} className="w-full">
          Create account
        </Button>
      </form>
    </AuthCard>
  )
}
