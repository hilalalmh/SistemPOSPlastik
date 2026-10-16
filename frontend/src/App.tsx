import { useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import Layout from './components/Layout'
import { setUnauthorizedHandler } from './lib/api'
import CashierPage from './pages/CashierPage'
import DashboardPage from './pages/DashboardPage'
import ExpensesPage from './pages/ExpensesPage'
import InventoryPage from './pages/InventoryPage'
import LabelPrintPage from './pages/LabelPrintPage'
import LoginPage from './pages/LoginPage'
import ProductsPage from './pages/ProductsPage'
import PurchasesPage from './pages/PurchasesPage'
import ReportsPage from './pages/ReportsPage'
import ReturnsPage from './pages/ReturnsPage'
import SalesPage from './pages/SalesPage'
import StockCountsPage from './pages/StockCountsPage'
import { useAuth } from './store/auth'

function Protected({ children }: { children: React.ReactNode }) {
  const status = useAuth((state) => state.status)
  const location = useLocation()

  if (status === 'loading') {
    return (
      <div className="flex h-full items-center justify-center text-slate-500">
        Memuat aplikasi…
      </div>
    )
  }
  if (status === 'anon') {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return <>{children}</>
}

export default function App() {
  const bootstrap = useAuth((state) => state.bootstrap)
  const logout = useAuth((state) => state.logout)

  useEffect(() => {
    setUnauthorizedHandler(() => {
      void logout()
    })
    void bootstrap()
  }, [bootstrap, logout])

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/kasir" element={<CashierPage />} />
        <Route path="/penjualan" element={<SalesPage />} />
        <Route path="/retur" element={<ReturnsPage />} />
        <Route path="/produk" element={<ProductsPage />} />
        <Route path="/pembelian" element={<PurchasesPage />} />
        <Route path="/inventori" element={<InventoryPage />} />
        <Route path="/pengeluaran" element={<ExpensesPage />} />
        <Route path="/stok-opname" element={<StockCountsPage />} />
        <Route path="/label-barcode" element={<LabelPrintPage />} />
        <Route path="/laporan" element={<ReportsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
