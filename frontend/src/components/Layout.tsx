import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../store/auth'
import ErrorBoundary from './ErrorBoundary'
import { Button } from './ui'

const navItems = [
  { to: '/', label: 'Dashboard', permission: 'report.dashboard' },
  { to: '/kasir', label: 'Kasir', permission: 'sale.create' },
  { to: '/penjualan', label: 'Penjualan', permission: 'sale.read' },
  { to: '/retur', label: 'Retur', permission: 'return.read' },
  { to: '/produk', label: 'Produk', permission: 'product.read' },
  { to: '/pembelian', label: 'Pembelian', permission: 'purchase.read' },
  { to: '/inventori', label: 'Inventori', permission: 'inventory.read' },
  { to: '/pengeluaran', label: 'Pengeluaran', permission: 'expense.read' },
  { to: '/stok-opname', label: 'Stok Opname', permission: 'stockcount.read' },
  { to: '/label-barcode', label: 'Label Barcode', permission: 'product.read' },
  { to: '/laporan', label: 'Laporan', permission: 'report.sales' },
]

export default function Layout() {
  const user = useAuth((state) => state.user)
  const hasPermission = useAuth((state) => state.hasPermission)
  const logout = useAuth((state) => state.logout)
  const navigate = useNavigate()
  const location = useLocation()

  const items = navItems.filter((item) => hasPermission(item.permission))

  return (
    <div className="flex h-full">
      <aside className="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-4 py-4">
          <div className="text-base font-bold text-emerald-700">POS Plastik</div>
          <div className="truncate text-xs text-slate-400">{user?.name}</div>
          <div className="text-xs uppercase tracking-wide text-slate-400">{user?.role}</div>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-2">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-700'
                    : 'text-slate-600 hover:bg-slate-100'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-100 p-3">
          <Button
            variant="secondary"
            className="w-full"
            onClick={async () => {
              await logout()
              navigate('/login')
            }}
          >
            Keluar
          </Button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <ErrorBoundary key={location.pathname}>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  )
}
