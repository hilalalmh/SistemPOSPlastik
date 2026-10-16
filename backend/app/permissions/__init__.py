"""Permission catalog and default role mappings (production.md Bagian 3 & 16)."""

PRODUCT_READ = "product.read"
PRODUCT_UPDATE = "product.update"
PRICE_READ = "price.read"
PRICE_UPDATE = "price.update"

INVENTORY_READ = "inventory.read"
INVENTORY_ADJUST = "inventory.adjust"
STOCKCOUNT_CREATE = "stockcount.create"
STOCKCOUNT_READ = "stockcount.read"
STOCKCOUNT_COUNT = "stockcount.count"
STOCKCOUNT_CONFIRM = "stockcount.confirm"

SALE_CREATE = "sale.create"
SALE_READ = "sale.read"
SALE_UPDATE_PRICE = "sale.update_price"
SALE_DISCOUNT = "sale.discount"
SALE_VOID = "sale.void"

SESSION_OPEN = "session.open"
SESSION_READ = "session.read"
SESSION_CLOSE = "session.close"
SESSION_CASHMOVE = "session.cashmove"

PURCHASE_READ = "purchase.read"
PURCHASE_UPDATE = "purchase.update"
PURCHASE_RECEIVE = "purchase.receive"

RETURN_CREATE = "return.create"
RETURN_READ = "return.read"
RETURN_CONFIRM = "return.confirm"

SUPPLIER_READ = "supplier.read"
SUPPLIER_UPDATE = "supplier.update"

CUSTOMER_READ = "customer.read"
CUSTOMER_UPDATE = "customer.update"

EXPENSE_READ = "expense.read"
EXPENSE_UPDATE = "expense.update"

REPORT_DASHBOARD = "report.dashboard"
REPORT_SALES = "report.sales"
REPORT_STOCK = "report.stock"
REPORT_PROFIT = "report.profit"
REPORT_PURCHASE = "report.purchase"
REPORT_EXPENSE = "report.expense"

USER_READ = "user.read"
USER_CREATE = "user.create"
USER_UPDATE = "user.update"
ROLE_READ = "role.read"
ROLE_UPDATE = "role.update"

SETTINGS_UPDATE = "settings.update"
AUDIT_READ = "audit.read"

ALL_PERMISSIONS: dict[str, str] = {
    PRODUCT_READ: "Melihat produk dan varian",
    PRODUCT_UPDATE: "Menambah/mengubah produk dan varian",
    PRICE_READ: "Melihat harga",
    PRICE_UPDATE: "Mengubah harga jual",
    INVENTORY_READ: "Melihat stok dan pergerakan",
    INVENTORY_ADJUST: "Menyesuaikan stok",
    STOCKCOUNT_CREATE: "Membuat stok opname",
    STOCKCOUNT_READ: "Melihat stok opname",
    STOCKCOUNT_COUNT: "Mengisi hitungan fisik",
    STOCKCOUNT_CONFIRM: "Mengonfirmasi stok opname",
    SALE_CREATE: "Membuat transaksi penjualan",
    SALE_READ: "Melihat transaksi penjualan",
    SALE_UPDATE_PRICE: "Mengubah harga pada transaksi",
    SALE_DISCOUNT: "Memberi diskon pada transaksi",
    SALE_VOID: "Membatalkan (void) transaksi",
    SESSION_OPEN: "Membuka shift kasir",
    SESSION_READ: "Melihat shift kasir",
    SESSION_CLOSE: "Menutup shift kasir",
    SESSION_CASHMOVE: "Mencatat kas masuk/keluar",
    PURCHASE_READ: "Melihat pembelian",
    PURCHASE_UPDATE: "Membuat/mengubah pembelian",
    PURCHASE_RECEIVE: "Menerima barang pembelian",
    RETURN_CREATE: "Membuat retur",
    RETURN_READ: "Melihat retur",
    RETURN_CONFIRM: "Mengonfirmasi retur",
    SUPPLIER_READ: "Melihat supplier",
    SUPPLIER_UPDATE: "Menambah/mengubah supplier",
    CUSTOMER_READ: "Melihat pelanggan",
    CUSTOMER_UPDATE: "Menambah/mengubah pelanggan",
    EXPENSE_READ: "Melihat pengeluaran",
    EXPENSE_UPDATE: "Mencatat pengeluaran",
    REPORT_DASHBOARD: "Melihat dashboard",
    REPORT_SALES: "Melihat laporan penjualan",
    REPORT_STOCK: "Melihat laporan stok",
    REPORT_PROFIT: "Melihat laporan laba kotor",
    REPORT_PURCHASE: "Melihat laporan pembelian",
    REPORT_EXPENSE: "Melihat laporan pengeluaran",
    USER_READ: "Melihat pengguna",
    USER_CREATE: "Menambah pengguna",
    USER_UPDATE: "Mengubah pengguna",
    ROLE_READ: "Melihat role",
    ROLE_UPDATE: "Mengubah role dan permission",
    SETTINGS_UPDATE: "Mengubah pengaturan toko",
    AUDIT_READ: "Melihat audit log",
}

OWNER_PERMISSIONS = list(ALL_PERMISSIONS.keys())

ADMIN_PERMISSIONS = [
    PRODUCT_READ,
    PRODUCT_UPDATE,
    PRICE_READ,
    PRICE_UPDATE,
    INVENTORY_READ,
    INVENTORY_ADJUST,
    STOCKCOUNT_CREATE,
    STOCKCOUNT_READ,
    STOCKCOUNT_COUNT,
    STOCKCOUNT_CONFIRM,
    SALE_CREATE,
    SALE_READ,
    SALE_UPDATE_PRICE,
    SALE_DISCOUNT,
    SALE_VOID,
    SESSION_OPEN,
    SESSION_READ,
    SESSION_CLOSE,
    SESSION_CASHMOVE,
    PURCHASE_READ,
    PURCHASE_UPDATE,
    PURCHASE_RECEIVE,
    RETURN_CREATE,
    RETURN_READ,
    RETURN_CONFIRM,
    SUPPLIER_READ,
    SUPPLIER_UPDATE,
    CUSTOMER_READ,
    CUSTOMER_UPDATE,
    EXPENSE_READ,
    EXPENSE_UPDATE,
    REPORT_DASHBOARD,
    REPORT_SALES,
    REPORT_STOCK,
    REPORT_PURCHASE,
    REPORT_EXPENSE,
    USER_READ,
    USER_UPDATE,
    ROLE_READ,
    AUDIT_READ,
]

CASHIER_PERMISSIONS = [
    PRODUCT_READ,
    PRICE_READ,
    INVENTORY_READ,
    SALE_CREATE,
    SALE_READ,
    SALE_DISCOUNT,
    SESSION_OPEN,
    SESSION_READ,
    SESSION_CLOSE,
    SESSION_CASHMOVE,
    CUSTOMER_READ,
    REPORT_DASHBOARD,
]

WAREHOUSE_PERMISSIONS = [
    PRODUCT_READ,
    PRODUCT_UPDATE,
    PRICE_READ,
    INVENTORY_READ,
    INVENTORY_ADJUST,
    STOCKCOUNT_CREATE,
    STOCKCOUNT_READ,
    STOCKCOUNT_COUNT,
    STOCKCOUNT_CONFIRM,
    PURCHASE_READ,
    PURCHASE_RECEIVE,
    SUPPLIER_READ,
    REPORT_STOCK,
]

DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "owner": OWNER_PERMISSIONS,
    "admin": ADMIN_PERMISSIONS,
    "cashier": CASHIER_PERMISSIONS,
    "warehouse": WAREHOUSE_PERMISSIONS,
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "owner": "Pemilik toko dengan akses penuh",
    "admin": "Administrator operasional",
    "cashier": "Kasir",
    "warehouse": "Petugas gudang",
}
