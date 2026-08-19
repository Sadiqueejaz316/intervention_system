import { createContext } from 'react'

import type { RegisterInput, User } from '@/api/types'

export interface AuthState {
  user: User | null
  /** True until the stored token has been checked against the API. */
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (input: RegisterInput) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthState | null>(null)
