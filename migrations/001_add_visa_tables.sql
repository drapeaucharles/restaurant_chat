-- Migration: Add Visa Agency Tables
-- This migration is additive and does not modify existing restaurant tables
-- All new tables are namespaced for visa functionality

-- Add business type to existing restaurants table (non-breaking)
ALTER TABLE restaurants 
  ADD COLUMN IF NOT EXISTS type VARCHAR(64) DEFAULT 'restaurant';

-- Create businesses table (extended business model)
CREATE TABLE IF NOT EXISTS businesses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id VARCHAR UNIQUE NOT NULL,
  type VARCHAR(64) NOT NULL DEFAULT 'restaurant',
  name VARCHAR NOT NULL,
  password VARCHAR NOT NULL,
  role VARCHAR DEFAULT 'owner',
  data JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create index on business_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_businesses_business_id ON businesses(business_id);
CREATE INDEX IF NOT EXISTS idx_businesses_type ON businesses(type);

-- Policy/country criteria (rules DSL lives here)
CREATE TABLE IF NOT EXISTS policy_packs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  jurisdiction VARCHAR(16) NOT NULL,      -- e.g., IDN
  version VARCHAR(32) NOT NULL,           -- e.g., 2025-09
  data_json JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (business_id, jurisdiction, version)
);

-- Create indexes for policy packs
CREATE INDEX IF NOT EXISTS idx_policy_packs_business_id ON policy_packs(business_id);
CREATE INDEX IF NOT EXISTS idx_policy_packs_jurisdiction ON policy_packs(jurisdiction);

-- Catalog of products (visa types)
CREATE TABLE IF NOT EXISTS catalogs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Create index on business_id for catalogs
CREATE INDEX IF NOT EXISTS idx_catalogs_business_id ON catalogs(business_id);

-- Visa products table
CREATE TABLE IF NOT EXISTS visa_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  catalog_id UUID NOT NULL REFERENCES catalogs(id) ON DELETE CASCADE,
  product_code VARCHAR(32) NOT NULL,      -- A1, B1, C1, C10, C11, E28A...
  name TEXT NOT NULL,
  category VARCHAR(64) NOT NULL,          -- tourism | business_event | investment | gov | crew
  entry_type VARCHAR(32) NOT NULL,        -- single | multiple
  first_stay_days INT NOT NULL,
  extendable_to_days INT,
  convertible BOOLEAN DEFAULT FALSE,
  sponsor_needed BOOLEAN DEFAULT FALSE,
  gov_fee_idr BIGINT DEFAULT 0,
  processing_sla_days INT,
  notes TEXT,
  UNIQUE (catalog_id, product_code)
);

-- Create indexes for visa products
CREATE INDEX IF NOT EXISTS idx_visa_products_catalog_id ON visa_products(catalog_id);
CREATE INDEX IF NOT EXISTS idx_visa_products_product_code ON visa_products(product_code);
CREATE INDEX IF NOT EXISTS idx_visa_products_category ON visa_products(category);

-- Visa requirements table
CREATE TABLE IF NOT EXISTS visa_requirements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  visa_product_id UUID NOT NULL REFERENCES visa_products(id) ON DELETE CASCADE,
  key VARCHAR(64) NOT NULL,               -- passport_validity, return_ticket, bank_statement_usd, photo_spec...
  value TEXT NOT NULL,                    -- '>=6 months', '>=USD 2000 (3 months)'
  mandatory BOOLEAN DEFAULT TRUE
);

-- Create indexes for visa requirements
CREATE INDEX IF NOT EXISTS idx_visa_requirements_product_id ON visa_requirements(visa_product_id);
CREATE INDEX IF NOT EXISTS idx_visa_requirements_key ON visa_requirements(key);

-- Visa eligibility table
CREATE TABLE IF NOT EXISTS visa_eligibilities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  visa_product_id UUID NOT NULL REFERENCES visa_products(id) ON DELETE CASCADE,
  country_whitelist TEXT                  -- JSON array of ISO2 or '*' (store as text)
);

-- Create index for visa eligibilities
CREATE INDEX IF NOT EXISTS idx_visa_eligibilities_product_id ON visa_eligibilities(visa_product_id);

-- Visa leads table
CREATE TABLE IF NOT EXISTS visa_leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  client_name TEXT, 
  client_email TEXT, 
  client_whatsapp TEXT,
  profile_json JSONB DEFAULT '{}'::jsonb,          -- nationality_iso2, purpose, stay_days...
  recommendation_json JSONB,
  status VARCHAR(32) DEFAULT 'new',                -- new|qualified|won|lost
  created_at TIMESTAMPTZ DEFAULT now(), 
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create indexes for visa leads
CREATE INDEX IF NOT EXISTS idx_visa_leads_business_id ON visa_leads(business_id);
CREATE INDEX IF NOT EXISTS idx_visa_leads_status ON visa_leads(status);
CREATE INDEX IF NOT EXISTS idx_visa_leads_created_at ON visa_leads(created_at);

-- Visa applications table
CREATE TABLE IF NOT EXISTS visa_applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  visa_lead_id UUID NOT NULL REFERENCES visa_leads(id) ON DELETE CASCADE,
  visa_product_id UUID NOT NULL REFERENCES visa_products(id),
  checklist_json JSONB DEFAULT '[]'::jsonb,        -- [{key, uploaded, verified, comment}]
  payments_json JSONB DEFAULT '[]'::jsonb,         -- [{amount_idr, type, paid, txid}]
  status VARCHAR(32) DEFAULT 'draft',              -- draft|docs_pending|submitted|granted|rejected|refunded
  created_at TIMESTAMPTZ DEFAULT now(), 
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create indexes for visa applications
CREATE INDEX IF NOT EXISTS idx_visa_applications_lead_id ON visa_applications(visa_lead_id);
CREATE INDEX IF NOT EXISTS idx_visa_applications_product_id ON visa_applications(visa_product_id);
CREATE INDEX IF NOT EXISTS idx_visa_applications_status ON visa_applications(status);

-- Restaurant extensions table (for backward compatibility)
CREATE TABLE IF NOT EXISTS restaurant_extensions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_id VARCHAR REFERENCES restaurants(restaurant_id) UNIQUE,
  business_type VARCHAR DEFAULT 'restaurant',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Create index for restaurant extensions
CREATE INDEX IF NOT EXISTS idx_restaurant_extensions_restaurant_id ON restaurant_extensions(restaurant_id);

-- Add comments for documentation
COMMENT ON TABLE businesses IS 'Extended business table supporting multiple business types including restaurants and visa agencies';
COMMENT ON TABLE policy_packs IS 'Policy and country criteria with rules DSL for visa eligibility';
COMMENT ON TABLE catalogs IS 'Catalog of visa products for each business';
COMMENT ON TABLE visa_products IS 'Individual visa products with codes, fees, and processing times';
COMMENT ON TABLE visa_requirements IS 'Requirements for each visa product';
COMMENT ON TABLE visa_eligibilities IS 'Eligibility criteria defining which countries can apply for each visa';
COMMENT ON TABLE visa_leads IS 'Potential customers who have inquired about visa services';
COMMENT ON TABLE visa_applications IS 'Formal visa applications with document checklist and payment tracking';
COMMENT ON TABLE restaurant_extensions IS 'Backward compatibility extension for existing restaurants';
