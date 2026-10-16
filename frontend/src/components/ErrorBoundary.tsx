import { Component, type ErrorInfo, type ReactNode } from 'react'

import { Button, Card } from './ui'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Terjadi kesalahan saat menampilkan halaman:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="p-6">
          <Card className="mx-auto max-w-lg p-6 text-center">
            <h2 className="text-base font-semibold text-slate-800">Terjadi kesalahan</h2>
            <p className="mt-1 text-sm text-slate-500">
              Halaman ini gagal dimuat. Silakan coba muat ulang.
            </p>
            <p className="mt-2 break-words rounded-lg bg-slate-50 px-3 py-2 text-xs text-red-600">
              {this.state.error.message}
            </p>
            <Button className="mt-4" onClick={() => this.setState({ error: null })}>
              Coba lagi
            </Button>
          </Card>
        </div>
      )
    }
    return this.props.children
  }
}
