export type RuleScope = 'global' | 'category' | 'product' | 'combo' | 'tenure';
export type RuleStatus = 'active' | 'disabled' | 'pending_approval';

export interface Category {
  id: string;
  name: string;
  slug: string;
  is_discount_eligible: boolean;
  updated_at: string;
}

export interface Product {
  id: number;
  name: string;
  category_id: string;
  is_active: boolean;
  updated_at: string;
}

export interface ProductBasePrice {
  id: string;
  product_id: number;
  duration_months: number;
  base_price: number;
  currency_code: string;
}

export interface DiscountRule {
  id: string;
  rule_name: string;
  scope: string;
  target_category_id?: string | null;
  target_product_id?: number | null;
  required_tenure_months?: number | null;
  conditional_product_ids?: number[] | null;
  required_customer_segment?: string | null;
  discount_percent: number;
  starts_at: string;
  ends_at?: string | null;
  status: string;
  created_by_actor_id?: string | null;
  created_by_actor_type?: string | null;
  approved_by_actor_id?: string | null;
  reason?: string | null;
  updated_at: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  discount_rule_id: string;
  action_type: string;
  actor_id?: string | null;
  actor_type?: string | null;
  actor_name_snapshot?: string | null;
  before_payload_json?: any;
  after_payload_json?: any;
  change_reason?: string | null;
  created_at: string;
}

export interface PricingPreview {
  product_id: number;
  product_name: string;
  duration_months: number;
  base_price: number;
  discount_percent: number;
  discount_source: string;
  final_price: number;
  display_text: string;
  pricing_status: string;
  applied_rule_id?: string;
}

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  public: {
    Tables: {
      categories: {
        Row: Category
        Insert: Partial<Category>
        Update: Partial<Category>
      }
      products: {
        Row: Product
        Insert: Partial<Product>
        Update: Partial<Product>
      }
      product_base_prices: {
        Row: ProductBasePrice
        Insert: Partial<ProductBasePrice>
        Update: Partial<ProductBasePrice>
      }
      discount_rules: {
        Row: DiscountRule
        Insert: Partial<DiscountRule>
        Update: Partial<DiscountRule>
      }
      discount_audit_logs: {
        Row: AuditLog
        Insert: Partial<AuditLog>
        Update: Partial<AuditLog>
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      calculate_effective_price: {
        Args: {
          p_product_id: number
          p_duration: number
          p_cart_items?: Json
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
  }
}
