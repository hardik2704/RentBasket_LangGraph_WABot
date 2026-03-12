-- Revised Supabase Schema for RentBasket Discount Control Portal
-- Optimized for integration with existing bot integer IDs

-- 1. Categories
CREATE TABLE IF NOT EXISTS categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL, -- To match 'sofa', 'bed', etc.
  is_discount_eligible BOOLEAN DEFAULT true,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Products
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY, -- Using the integer IDs from data/products.py
  category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  is_active BOOLEAN DEFAULT true,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Base Prices
CREATE TABLE IF NOT EXISTS product_base_prices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
  duration_months INTEGER NOT NULL,
  base_price NUMERIC NOT NULL,
  currency_code TEXT DEFAULT 'INR',
  UNIQUE(product_id, duration_months)
);

-- 4. Discount Rules
CREATE TABLE IF NOT EXISTS discount_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_name TEXT NOT NULL,
  scope TEXT NOT NULL CHECK (scope IN ('global', 'category', 'product', 'combo', 'tenure')),
  target_category_id UUID REFERENCES categories(id) NULL,
  target_product_id INTEGER REFERENCES products(id) NULL,
  required_tenure_months INTEGER NULL,
  conditional_product_ids INTEGER[] NULL, -- For combos, using integers
  required_customer_segment TEXT NULL,
  discount_percent NUMERIC NOT NULL CHECK (discount_percent >= 0 AND discount_percent <= 100),
  starts_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ends_at TIMESTAMPTZ NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'disabled', 'pending_approval')) DEFAULT 'pending_approval',
  created_by_actor_id UUID NULL,
  created_by_actor_type TEXT NULL,
  approved_by_actor_id UUID NULL,
  reason TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Audit Logs
CREATE TABLE IF NOT EXISTS discount_audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  discount_rule_id UUID REFERENCES discount_rules(id) ON DELETE SET NULL,
  action_type TEXT NOT NULL,
  actor_id UUID,
  actor_type TEXT,
  actor_name_snapshot TEXT,
  before_payload_json JSONB,
  after_payload_json JSONB,
  change_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger function
CREATE OR REPLACE FUNCTION log_discount_rule_changes()
RETURNS TRIGGER AS $$
DECLARE
  v_action TEXT;
BEGIN
  IF TG_OP = 'INSERT' THEN
    v_action := 'CREATE';
    INSERT INTO discount_audit_logs (discount_rule_id, action_type, actor_type, after_payload_json, change_reason)
    VALUES (NEW.id, v_action, NEW.created_by_actor_type, row_to_json(NEW)::jsonb, NEW.reason);
  ELSIF TG_OP = 'UPDATE' THEN
    IF OLD.status = 'pending_approval' AND NEW.status = 'active' THEN v_action := 'APPROVE';
    ELSIF OLD.status = 'active' AND NEW.status = 'disabled' THEN v_action := 'DISABLE';
    ELSE v_action := 'UPDATE'; END IF;
    INSERT INTO discount_audit_logs (discount_rule_id, action_type, actor_type, before_payload_json, after_payload_json, change_reason)
    VALUES (NEW.id, v_action, NEW.created_by_actor_type, row_to_json(OLD)::jsonb, row_to_json(NEW)::jsonb, NEW.reason);
  ELSIF TG_OP = 'DELETE' THEN
    INSERT INTO discount_audit_logs (discount_rule_id, action_type, before_payload_json)
    VALUES (OLD.id, 'DELETE', row_to_json(OLD)::jsonb);
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_discount_rule_audit ON discount_rules;
CREATE TRIGGER trigger_discount_rule_audit
AFTER INSERT OR UPDATE OR DELETE ON discount_rules
FOR EACH ROW EXECUTE FUNCTION log_discount_rule_changes();

-- ==========================================
-- PRICING ENGINE (RPC FUNCTION)
-- ==========================================

CREATE OR REPLACE FUNCTION calculate_effective_price(
  p_product_id INTEGER,
  p_duration_months INTEGER,
  p_cart_items INTEGER[] DEFAULT NULL,
  p_customer_domain TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
  v_base_price NUMERIC;
  v_category_id UUID;
  v_product_name TEXT;
  v_is_eligible BOOLEAN;
  v_discount_percent NUMERIC := 0;
  v_discount_rule_id UUID := NULL;
  v_discount_source TEXT := 'none';
  v_final_price NUMERIC;
  v_display_text TEXT;
BEGIN
  -- 1. Get Base Price and Product Info
  SELECT bp.base_price, p.category_id, p.name, c.is_discount_eligible
  INTO v_base_price, v_category_id, v_product_name, v_is_eligible
  FROM products p
  JOIN product_base_prices bp ON p.id = bp.product_id
  JOIN categories c ON p.category_id = c.id
  WHERE p.id = p_product_id AND bp.duration_months = p_duration_months;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('error', 'Product or base price not found');
  -- Try to fallback to any price for this product if duration not found
  -- (Optionally, but strictly we follow duration)
  END IF;

  v_final_price := v_base_price;

  -- 2. If Category Ineligible
  IF NOT v_is_eligible THEN
    v_display_text := '₹' || round(v_base_price)::text || '/month for ' || p_duration_months::text || ' months';
    RETURN jsonb_build_object(
      'product_id', p_product_id,
      'product_name', v_product_name,
      'duration_months', p_duration_months,
      'base_price', v_base_price,
      'discount_percent', 0,
      'discount_source', 'ineligible',
      'final_price', round(v_base_price),
      'display_text', v_display_text,
      'pricing_status', 'active'
    );
  END IF;

  -- 3. Evaluate Hierarchy
  -- Combo Check
  IF p_cart_items IS NOT NULL AND array_length(p_cart_items, 1) > 0 THEN
      SELECT id, discount_percent, 'combo' INTO v_discount_rule_id, v_discount_percent, v_discount_source
      FROM discount_rules
      WHERE scope = 'combo' AND status = 'active'
        AND starts_at <= NOW() AND (ends_at IS NULL OR ends_at > NOW())
        AND conditional_product_ids <@ p_cart_items
      ORDER BY discount_percent DESC LIMIT 1;
  END IF;

  -- Tenure Check
  IF v_discount_rule_id IS NULL AND p_duration_months IS NOT NULL THEN
      SELECT id, discount_percent, 'tenure' INTO v_discount_rule_id, v_discount_percent, v_discount_source
      FROM discount_rules
      WHERE scope = 'tenure' AND status = 'active'
        AND starts_at <= NOW() AND (ends_at IS NULL OR ends_at > NOW())
        AND required_tenure_months = p_duration_months
      ORDER BY discount_percent DESC LIMIT 1;
  END IF;

  -- Product Check
  IF v_discount_rule_id IS NULL THEN
      SELECT id, discount_percent, 'product' INTO v_discount_rule_id, v_discount_percent, v_discount_source
      FROM discount_rules
      WHERE scope = 'product' AND target_product_id = p_product_id AND status = 'active'
        AND starts_at <= NOW() AND (ends_at IS NULL OR ends_at > NOW())
      ORDER BY discount_percent DESC LIMIT 1;
  END IF;

  -- Category Check
  IF v_discount_rule_id IS NULL THEN
      SELECT id, discount_percent, 'category' INTO v_discount_rule_id, v_discount_percent, v_discount_source
      FROM discount_rules
      WHERE scope = 'category' AND target_category_id = v_category_id AND status = 'active'
        AND starts_at <= NOW() AND (ends_at IS NULL OR ends_at > NOW())
      ORDER BY discount_percent DESC LIMIT 1;
  END IF;

  -- Global Check
  IF v_discount_rule_id IS NULL THEN
      SELECT id, discount_percent, 'global' INTO v_discount_rule_id, v_discount_percent, v_discount_source
      FROM discount_rules
      WHERE scope = 'global' AND status = 'active'
        AND starts_at <= NOW() AND (ends_at IS NULL OR ends_at > NOW())
      ORDER BY discount_percent DESC LIMIT 1;
  END IF;

  -- 4. Final Math
  IF v_discount_percent > 0 THEN
    v_final_price := v_base_price * (1 - (v_discount_percent / 100.0));
    v_display_text := '~₹' || round(v_base_price)::text || '~ ₹' || round(v_final_price)::text || '/month for ' || p_duration_months::text || ' months';
  ELSE
    v_display_text := '₹' || round(v_base_price)::text || '/month for ' || p_duration_months::text || ' months';
  END IF;

  RETURN jsonb_build_object(
    'product_id', p_product_id,
    'product_name', v_product_name,
    'duration_months', p_duration_months,
    'base_price', v_base_price,
    'discount_percent', v_discount_percent,
    'discount_source', v_discount_source,
    'final_price', round(v_final_price),
    'display_text', v_display_text,
    'pricing_status', 'active',
    'applied_rule_id', v_discount_rule_id
  );
END;
$$ LANGUAGE plpgsql;
