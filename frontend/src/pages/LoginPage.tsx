import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button, Card, Input, Label, Spinner } from '../components/ui'
import { RequestError } from '../lib/api'
import { useAuth } from '../store/auth'

export default function LoginPage() {
  const login = useAuth((state) => state.login)
  const status = useAuth((state) => state.status)
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (status === 'authed') {
    navigate('/', { replace: true })
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username.trim(), password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof RequestError ? err.message : 'Gagal masuk. Coba lagi.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-full items-center justify-center bg-slate-100 p-4">
      <Card className="w-full max-w-sm">
        <form onSubmit={onSubmit} className="space-y-4 p-6">
          <div className="text-center">
            <div className="text-xl font-bold text-emerald-700">POS Plastik</div>
            <div className="text-sm text-slate-500">Masuk untuk melanjutkan</div>
          </div>
          <div>
            <Label>Username</Label>
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div>
            <Label>Password</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && (
            <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
          )}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading && <Spinner className="border-white/40 border-t-white" />}
            Masuk
          </Button>
        </form>
      </Card>
    </div>
  )
}
