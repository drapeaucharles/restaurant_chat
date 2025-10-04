-- Seed GSI Bali Agency with visa data
-- Create catalog, policy pack, and visa products

-- Variables (replace with actual GSI business ID)
\set gsi_business_id '6becb7a9-f82f-4b3a-857e-28108460ee20'

-- Create catalog for Indonesia (IDN)
INSERT INTO catalogs (id, business_id, jurisdiction, name, description, is_active)
VALUES (
    gen_random_uuid(),
    :'gsi_business_id',
    'IDN',
    'Indonesia Visa Catalog',
    'Complete visa and permit catalog for Indonesia',
    true
) ON CONFLICT DO NOTHING;

-- Get the catalog ID for reference
\set catalog_id (SELECT id FROM catalogs WHERE business_id = :'gsi_business_id' AND jurisdiction = 'IDN')

-- Create policy pack for Indonesia
INSERT INTO policy_packs (id, business_id, jurisdiction, name, version, data_json_from_pdf, is_active)
VALUES (
    gen_random_uuid(),
    :'gsi_business_id',
    'IDN',
    'Indonesia Immigration Policy 2024',
    '1.0',
    '{
        "visa_types": {
            "B211A": {"name": "Visit Visa", "duration": 30, "extendable": true},
            "B211B": {"name": "Business Visit", "duration": 60, "extendable": false},
            "B213": {"name": "Stay Permit (KITAS)", "duration": 365, "renewable": true}
        },
        "requirements": {
            "passport": {"validity_months": 6, "blank_pages": 2},
            "photos": {"count": 2, "size": "4x6cm", "background": "white"},
            "financial": {"min_balance_usd": 2000}
        },
        "processing_times": {
            "standard": "7-14 days",
            "express": "3-5 days"
        }
    }',
    true
) ON CONFLICT DO NOTHING;

-- Create visa products
INSERT INTO visa_products (id, catalog_id, product_code, name, category, entry_type, first_stay_days, extendable_to_days, convertible, sponsor_needed, gov_fee_idr, processing_sla_days, notes)
VALUES 
    -- Tourist Visas
    (gen_random_uuid(), (SELECT id FROM catalogs WHERE business_id = :'gsi_business_id'), 'B211A', 'Visit Visa (Tourist)', 'Tourist', 'Single', 30, 60, false, false, 500000, 7, '30-day tourist visa, extendable once'),
    (gen_random_uuid(), (SELECT id FROM catalogs WHERE business_id = :'gsi_business_id'), 'B211B', 'Business Visit Visa', 'Business', 'Single', 60, null, false, true, 1000000, 10, '60-day business visit visa'),
    
    -- Long-term Permits  
    (gen_random_uuid(), (SELECT id FROM catalogs WHERE business_id = :'gsi_business_id'), 'B213', 'KITAS (Stay Permit)', 'Residence', 'Multiple', 365, null, true, true, 5000000, 21, '1-year renewable stay permit'),
    
    -- Investment & Work
    (gen_random_uuid(), (SELECT id FROM catalogs WHERE business_id = :'gsi_business_id'), 'VITAS', 'Investment Visa', 'Investment', 'Multiple', 365, null, true, false, 7500000, 30, 'For foreign investors'),
    (gen_random_uuid(), (SELECT id FROM catalogs WHERE business_id = :'gsi_business_id'), 'IMTA', 'Work Permit', 'Work', 'Multiple', 365, null, false, true, 6000000, 21, 'Foreign worker employment permit')
ON CONFLICT DO NOTHING;

-- Create basic visa requirements
INSERT INTO visa_requirements (id, visa_product_id, requirement_type, description, is_mandatory, document_format, notes)
SELECT 
    gen_random_uuid(),
    vp.id,
    'passport',
    'Valid passport with minimum 6 months validity',
    true,
    'original',
    'Must have at least 2 blank pages'
FROM visa_products vp 
WHERE vp.catalog_id = (SELECT id FROM catalogs WHERE business_id = :'gsi_business_id')
ON CONFLICT DO NOTHING;

INSERT INTO visa_requirements (id, visa_product_id, requirement_type, description, is_mandatory, document_format, notes)
SELECT 
    gen_random_uuid(),
    vp.id,
    'photo',
    '2 passport-sized photos (4x6cm, white background)',
    true,
    'physical',
    'Recent photos taken within last 6 months'
FROM visa_products vp 
WHERE vp.catalog_id = (SELECT id FROM catalogs WHERE business_id = :'gsi_business_id')
ON CONFLICT DO NOTHING;

-- Verify the data was created
SELECT 'Catalogs' as table_name, COUNT(*) as count FROM catalogs WHERE business_id = :'gsi_business_id'
UNION ALL
SELECT 'Policy Packs', COUNT(*) FROM policy_packs WHERE business_id = :'gsi_business_id'
UNION ALL  
SELECT 'Visa Products', COUNT(*) FROM visa_products WHERE catalog_id = (SELECT id FROM catalogs WHERE business_id = :'gsi_business_id')
UNION ALL
SELECT 'Visa Requirements', COUNT(*) FROM visa_requirements WHERE visa_product_id IN (SELECT id FROM visa_products WHERE catalog_id = (SELECT id FROM catalogs WHERE business_id = :'gsi_business_id'));
