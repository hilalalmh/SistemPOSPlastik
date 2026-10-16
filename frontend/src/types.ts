export interface CurrentUser {
  id: string
  name: string
  role: string
  permissions: string[]
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: CurrentUser
}

export interface CashMovement {
  id: string
  type: string
  amount: string
  reason?: string | null
  created_at: string
}

export interface CashSession {
  id: string
  location_id: string
  cashier_id: string
  opened_at: string
  closed_at?: string | null
  opening_cash: string
  expected_cash?: string | null
  counted_cash?: string | null
  difference?: string | null
  status: string
  notes?: string | null
  movements?: CashMovement[]
  sales_count?: number
  sales_total?: string
}

export interface CatalogUnit {
  unit_id: string
  unit_name: string
  symbol?: string
  conversion_factor: string
  unit_price?: string | null
  min_qty?: string | null
}

export interface CatalogItem {
  variant_id: string
  product_name: string
  sku: string
  barcode?: string | null
  attributes: Record<string, string>
  base_unit_id: string
  base_unit_name: string
  stock_base: string
  price_from?: string | null
  units: CatalogUnit[]
}

export interface QuoteLine {
  variant_id: string
  name: string
  sku: string
  unit_id: string
  unit_name: string
  conversion_factor: string
  quantity: string
  base_quantity: string
  unit_price: string
  min_qty: string
  max_qty?: string | null
  discount_amount: string
  line_total: string
  stock_base: string
  stock_sufficient: boolean
  price_overridden: boolean
}

export interface QuoteResponse {
  items: QuoteLine[]
  subtotal: string
  discount_total: string
  tax_total: string
  total: string
}

export interface Payment {
  method: string
  amount: string
  status: string
  reference_no?: string | null
}

export interface SaleItem {
  variant_id: string
  name_snapshot: string
  sku_snapshot: string
  unit_name_snapshot: string
  conversion_factor: string
  quantity: string
  base_quantity: string
  unit_price: string
  discount_amount: string
  line_total: string
  cost_unit: string
  cost_total: string
}

export interface Sale {
  id: string
  number: string
  status: string
  cashier_id: string
  cash_session_id: string
  customer_id?: string | null
  subtotal: string
  discount_total: string
  tax_total: string
  total: string
  paid_total: string
  change_total: string
  cost_total: string
  notes?: string | null
  sold_at: string
  voided_at?: string | null
  void_reason?: string | null
  items: SaleItem[]
  payments: Payment[]
}

export interface DashboardData {
  date: string
  sales_count: number
  gross_revenue: string
  return_total?: string
  net_revenue: string
  net_after_return?: string
  discount_total: string
  payment_breakdown: { method: string; amount: string; count: number }[]
  low_stock_count: number
}

export interface TopProduct {
  variant_id: string
  product_name?: string | null
  sku?: string | null
  quantity_sold: string
  revenue: string
}

export interface SalesTrendRow {
  period: string
  sales_count: number
  gross_revenue: string
  return_total?: string
  net_revenue: string
  net_after_return?: string
  cost_total: string
  gross_profit: string
}

export interface SalesTrendReport {
  from_date: string
  to_date: string
  rows: SalesTrendRow[]
  totals: SalesTrendRow
}

export interface Movement {
  id: string
  variant_id: string
  location_id: string
  type: string
  quantity: string
  unit_cost?: string | null
  balance_after?: string | null
  reason?: string | null
  product_name?: string | null
  created_at: string
}

export interface Paginated<T> {
  data: T[]
  page: number
  page_size: number
  total: number
}

export interface Category {
  id: string
  name: string
}

export interface Unit {
  id: string
  name: string
  symbol: string
  allows_fraction: boolean
}

export interface VariantSummary {
  id: string
  product_id: string
  sku: string
  barcode?: string | null
  attribute_size?: string | null
  attribute_color?: string | null
  base_unit_id: string
  min_stock?: string | null
  is_active: boolean
  product_name?: string | null
}

export interface Product {
  id: string
  name: string
  category_id?: string | null
  brand?: string | null
  is_active: boolean
  variants?: VariantSummary[]
}

export interface Supplier {
  id: string
  name: string
  contact_name?: string | null
  phone?: string | null
  email?: string | null
  address?: string | null
  is_active: boolean
}

export interface PurchaseItem {
  id: string
  variant_id: string
  unit_id: string
  conversion_factor: string
  quantity: string
  received_quantity: string
  base_quantity?: string | null
  unit_cost: string
  discount_amount: string
  line_total: string
  remaining_quantity: string
  base_unit_cost: string
  product_name?: string | null
  sku?: string | null
}

export interface PurchaseReceiptItem {
  id: string
  purchase_item_id: string
  base_quantity: string
  unit_cost: string
}

export interface PurchaseReceipt {
  id: string
  number: string
  received_by: string
  received_at: string
  notes?: string | null
  items: PurchaseReceiptItem[]
}

export interface Purchase {
  id: string
  number: string
  supplier_id: string
  supplier_name?: string | null
  location_id: string
  status: string
  subtotal: string
  discount_total: string
  additional_cost: string
  total: string
  invoice_no?: string | null
  notes?: string | null
  created_by: string
  received_by?: string | null
  created_at: string
  ordered_at?: string | null
  received_at?: string | null
  items: PurchaseItem[]
  receipts: PurchaseReceipt[]
}

export interface StockCountListItem {
  id: string
  number: string
  status: string
  created_at: string
  confirmed_at?: string | null
}

export interface StockCountItem {
  id: string
  variant_id: string
  system_quantity: string
  counted_quantity?: string | null
  difference?: string | null
  unit_id: string
  unit_name?: string | null
  notes?: string | null
  sku?: string | null
  product_name?: string | null
}

export interface StockCount {
  id: string
  number: string
  location_id: string
  status: string
  created_by: string
  confirmed_by?: string | null
  confirmed_at?: string | null
  notes?: string | null
  created_at: string
  items: StockCountItem[]
}

export interface ExpenseCategory {
  id: string
  name: string
  is_active: boolean
}

export interface Expense {
  id: string
  category_id?: string | null
  category_name?: string | null
  expense_date: string
  amount: string
  payment_method: string
  description?: string | null
  attachment_url?: string | null
  user_id: string
  cancelled_at?: string | null
  cancelled_by?: string | null
  created_at: string
}

export interface ExpenseReport {
  from_date: string
  to_date: string
  total: string
  count: number
  by_category: { category_id: string | null; category_name: string; total: string; count: number }[]
}

export interface LabelData {
  variant_id: string
  product_name: string
  sku: string
  barcode?: string | null
  code: string
  has_barcode: boolean
  attributes: Record<string, string>
  barcode_svg: string
  copies: number
}

export interface LabelPreview {
  template: string
  total: number
  labels: LabelData[]
}

export interface ReturnItem {
  id: string
  sale_item_id?: string | null
  variant_id: string
  unit_id: string
  conversion_factor: string
  quantity: string
  base_quantity: string
  condition: string
  refund_amount: string
  product_name?: string | null
  sku?: string | null
}

export interface SaleReturn {
  id: string
  number: string
  sale_id?: string | null
  purchase_id?: string | null
  type: string
  status: string
  reason: string
  refund_method?: string | null
  refund_amount: string
  created_by: string
  approved_by?: string | null
  created_at: string
  items: ReturnItem[]
}

export interface ReturnableItem {
  id: string
  sale_item_id: string
  variant_id: string
  unit_id: string
  conversion_factor: string
  quantity: string
  base_quantity: string
  returned_quantity: string
  remaining_quantity: string
  condition: string
  refund_amount: string
  product_name?: string | null
  sku?: string | null
}

export interface ReturnableSale {
  sale_id: string
  number: string
  sold_at: string
  status: string
  customer_id?: string | null
  items: ReturnableItem[]
}
