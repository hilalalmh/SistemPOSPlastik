import { create } from 'zustand'

import {
  apiRequest,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from '../lib/api'
import type { CurrentUser, LoginResponse } from '../types'

interface AuthState {
  user: CurrentUser | null
  status: 'loading' | 'authed' | 'anon'
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  bootstrap: () => Promise<void>
  hasPermission: (code: string) => boolean
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  status: 'loading',

  login: async (username, password) => {
    const data = await apiRequest<LoginResponse>('/auth/login', {
      method: 'POST',
      body: { username, password },
      auth: false,
    })
    setAccessToken(data.access_token)
    setRefreshToken(data.refresh_token)
    set({ user: data.user, status: 'authed' })
  },

  logout: async () => {
    try {
      await apiRequest('/auth/logout', { method: 'POST' })
    } catch {
      // ignore network errors on logout
    }
    setAccessToken(null)
    setRefreshToken(null)
    set({ user: null, status: 'anon' })
  },

  bootstrap: async () => {
    if (!getRefreshToken()) {
      set({ status: 'anon' })
      return
    }
    try {
      const data = await apiRequest<LoginResponse>('/auth/refresh', {
        method: 'POST',
        body: { refresh_token: getRefreshToken() },
        auth: false,
      })
      setAccessToken(data.access_token)
      setRefreshToken(data.refresh_token)
      set({ user: data.user, status: 'authed' })
    } catch {
      setAccessToken(null)
      setRefreshToken(null)
      set({ user: null, status: 'anon' })
    }
  },

  hasPermission: (code) => get().user?.permissions.includes(code) ?? false,
}))
