/** Customer domain types for API payloads and responses. */

export interface CustomerCreatePayload {
  company_name: string;
  business_number: string;
  billing_address: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  credit_limit: string;
}

export interface CustomerResponse {
  id: string;
  tenant_id: string;
  company_name: string;
  normalized_business_number: string;
  billing_address: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  credit_limit: string;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface CustomerSummary {
  id: string;
  company_name: string;
  normalized_business_number: string;
  contact_phone: string;
  status: string;
}

export interface CustomerListResponse {
  items: CustomerSummary[];
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

export interface CustomerUpdatePayload {
  company_name?: string;
  business_number?: string;
  billing_address?: string;
  contact_name?: string;
  contact_phone?: string;
  contact_email?: string;
  credit_limit?: string;
  status?: string;
  version: number;
}
