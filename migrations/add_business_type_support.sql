-- Migration to support multiple business types
-- This makes the system work for restaurants, legal services, and any other business

-- 1. Rename restaurants table to businesses (keeping backward compatibility)
ALTER TABLE restaurants RENAME TO businesses;

-- 2. Add business_type column if it doesn't exist
ALTER TABLE businesses 
ADD COLUMN IF NOT EXISTS business_type VARCHAR(50) DEFAULT 'restaurant';

-- 3. Create a more generic products table (rename from menu_items)
ALTER TABLE menu_items RENAME TO products;

-- 4. Add product_type to distinguish between different offerings
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS product_type VARCHAR(50) DEFAULT 'menu_item',
ADD COLUMN IF NOT EXISTS duration VARCHAR(100), -- For services like "2-3 weeks processing"
ADD COLUMN IF NOT EXISTS requirements JSONB, -- For visa requirements, documents needed, etc.
ADD COLUMN IF NOT EXISTS features JSONB; -- For what's included in the service

-- 5. Update column names to be more generic
ALTER TABLE products 
RENAME COLUMN restaurant_id TO business_id;

-- 6. Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_products_business_type ON products(business_id, product_type);
CREATE INDEX IF NOT EXISTS idx_businesses_type ON businesses(business_type);

-- 7. Update existing data to have proper business_type
UPDATE businesses SET business_type = 'restaurant' WHERE business_type IS NULL;

-- 8. Add business metadata
ALTER TABLE businesses
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Example metadata structure:
-- For restaurants: {"cuisine_type": "Italian", "hours": {...}, "delivery": true}
-- For legal services: {"specialties": ["visa", "company formation"], "languages": ["English", "Indonesian"]}

-- 9. Create view for backward compatibility
CREATE OR REPLACE VIEW restaurants AS 
SELECT * FROM businesses WHERE business_type = 'restaurant';

CREATE OR REPLACE VIEW menu_items AS 
SELECT * FROM products WHERE product_type = 'menu_item';

-- 10. Update foreign key constraints
ALTER TABLE products 
DROP CONSTRAINT IF EXISTS menu_items_restaurant_id_fkey,
ADD CONSTRAINT products_business_id_fkey 
FOREIGN KEY (business_id) REFERENCES businesses(restaurant_id);

-- 11. Example data for legal services
-- INSERT INTO businesses (restaurant_id, data, rag_mode, business_type, metadata) VALUES 
-- ('bali_business_consulting', 
--  '{"name": "Bali Business Consulting", "email": "info@balibusinessconsulting.com", "phone": "+62 812 3456 7890"}',
--  'memory_universal',
--  'legal_visa',
--  '{"specialties": ["visa", "company_formation", "property"], "languages": ["English", "Indonesian"], "experience_years": 13}'
-- );

-- Example legal service products:
-- INSERT INTO products (id, business_id, name, description, price, category, product_type, duration, requirements) VALUES
-- ('remote_worker_kitas', 'bali_business_consulting', 'Remote Worker KITAS', 'Work legally in Indonesia as a remote worker', 1500, 'Visa Services', 'service', '2-3 weeks', '{"documents": ["passport", "employment_letter", "bank_statement"]}'),
-- ('company_formation', 'bali_business_consulting', 'PT PMA Company Formation', 'Establish a foreign-owned company in Indonesia', 3000, 'Legal Services', 'service', '4-6 weeks', '{"documents": ["passport", "business_plan", "proof_of_funds"]}');