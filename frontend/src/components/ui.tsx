import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>
      {children}
    </div>
  )
}

export function CardHeader({ title, actions }: { title: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
      <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
      {actions}
    </div>
  )
}

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'

const variantClasses: Record<ButtonVariant, string> = {
  primary: 'bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-emerald-300',
  secondary: 'bg-slate-100 text-slate-700 hover:bg-slate-200 disabled:opacity-50',
  danger: 'bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300',
  ghost: 'bg-transparent text-slate-600 hover:bg-slate-100',
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition disabled:cursor-not-allowed ${variantClasses[variant]} ${className}`}
      {...props}
    />
  )
}

export function Input({ className = '', ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 ${className}`}
      {...props}
    />
  )
}

export function Label({ children }: { children: ReactNode }) {
  return <label className="mb-1 block text-xs font-medium text-slate-600">{children}</label>
}

export function Spinner({ className = '' }: { className?: string }) {
  return (
    <div
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-emerald-600 ${className}`}
    />
  )
}

export function EmptyState({ message }: { message: string }) {
  return <div className="px-4 py-10 text-center text-sm text-slate-400">{message}</div>
}

export function ErrorText({ children }: { children: ReactNode }) {
  if (!children) return null
  return (
    <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
      {children}
    </div>
  )
}
