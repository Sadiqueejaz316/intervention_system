import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import { readToken, setUnauthorizedHandler, writeToken } from '@/api/client'
import { auth } from '@/api/endpoints'
import type { RegisterInput, User } from '@/api/types'
import { AuthContext } from './context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(readToken() !== null)

  const logout = useCallback(() => {
    writeToken(null)
    setUser(null)
    // Another account must never see the previous one's cached tickets.
    queryClient.clear()
  }, [queryClient])

  // A token can expire while the tab sits open; any 401 ends the session.
  useEffect(() => {
    setUnauthorizedHandler(logout)
  }, [logout])

  // A stored token only means "was valid once", so confirm it on start-up.
  useEffect(() => {
    if (readToken() === null) return

    let cancelled = false
    auth
      .me()
      .then((profile) => {
        if (!cancelled) setUser(profile)
      })
      .catch(() => {
        if (!cancelled) writeToken(null)
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await auth.login(email, password)
      writeToken(access_token)

      try {
        setUser(await auth.me())
      } catch (error) {
        writeToken(null)
        throw error
      }

      queryClient.clear()
    },
    [queryClient],
  )

  const register = useCallback(
    async (input: RegisterInput) => {
      await auth.register(input)
      await login(input.email, input.password)
    },
    [login],
  )

  const value = useMemo(
    () => ({ user, isLoading, login, register, logout }),
    [user, isLoading, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
