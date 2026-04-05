export type SupplierInvoiceStatus = "open" | "paid" | "voided";

export interface SupplierInvoiceLine {
  id: string;
  line_number: number;
  product_id: string | null;
  product_code_snapshot: string | null;
  product_name: string | null;
  description: string;
  quantity: string;
  unit_price: string;
  subtotal_amount: string;
  tax_type: number;
  tax_rate: string;
  tax_amount: string;
  total_amount: string;
  created_at: string;
}

export interface SupplierInvoice {
  id: string;
  supplier_id: string;
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  currency_code: string;
  subtotal_amount: string;
  tax_amount: string;
  total_amount: string;
  status: SupplierInvoiceStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
  lines: SupplierInvoiceLine[];
}

export interface SupplierInvoiceListItem {
  id: string;
  supplier_id: string;
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  currency_code: string;
  total_amount: string;
  status: SupplierInvoiceStatus;
  created_at: string;
  updated_at: string;
  line_count: number;
}

export interface SupplierInvoiceListResponse {
  items: SupplierInvoiceListItem[];
  total: number;
  page: number;
  page_size: number;
}