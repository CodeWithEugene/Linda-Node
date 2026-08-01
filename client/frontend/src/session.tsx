import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react'
import { api, post, User } from './api'

export type Session = {
  user: User | null
  loading: boolean
  connectionError: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const SessionContext = createContext<Session | null>(null)

export const useSession = (): Session => {
  const value = useContext(SessionContext)
  if (!value) throw new Error('Session context missing')
  return value
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  useEffect(() => {
    api<User>('/api/me')
      .then(setUser)
      .catch((error) => {
        const message = error instanceof Error ? error.message : 'The Linda API could not be reached.'
        if (!message.includes('Sign in is required') && !message.includes('Request failed (401)')) setConnectionError(message)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo<Session>(
    () => ({
      user,
      loading,
      connectionError,
      login: async (email, password) => setUser(await post<User>('/api/auth/login', { email, password })),
      logout: async () => {
        await post<void>('/api/auth/logout')
        setUser(null)
      },
    }),
    [user, loading, connectionError],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}
