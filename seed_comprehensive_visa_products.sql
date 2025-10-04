-- Comprehensive Visa Products for GSI Bali Agency
-- This includes all major Indonesia visa types with detailed information

-- Get GSI business ID
\set gsi_business_id '6becb7a9-f82f-4b3a-857e-28108460ee20'

-- Create catalog for GSI (if not exists)
INSERT INTO catalogs (id, business_id, created_at)
VALUES (
    gen_random_uuid(),
    :'gsi_business_id',
    now()
) ON CONFLICT DO NOTHING;

-- Get the catalog ID
DO $$
DECLARE
    catalog_uuid UUID;
BEGIN
    SELECT id INTO catalog_uuid FROM catalogs WHERE business_id = '6becb7a9-f82f-4b3a-857e-28108460ee20';
    
    -- Clear existing visa products to avoid duplicates
    DELETE FROM visa_products WHERE catalog_id = catalog_uuid;
    
    -- Insert comprehensive visa products
    INSERT INTO visa_products (id, catalog_id, product_code, name, category, entry_type, first_stay_days, extendable_to_days, convertible, sponsor_needed, gov_fee_idr, processing_sla_days, notes)
    VALUES 
        -- TOURIST VISAS
        (gen_random_uuid(), catalog_uuid, 'B211A', 'Visit Visa (Tourist)', 'Tourist', 'Single', 30, 60, false, false, 500000, 7, '30-day tourist visa, extendable once to 60 days total'),
        (gen_random_uuid(), catalog_uuid, 'B211B', 'Business Visit Visa', 'Business', 'Single', 60, null, false, true, 1000000, 10, '60-day business visit visa, requires sponsor'),
        (gen_random_uuid(), catalog_uuid, 'VOA', 'Visa on Arrival', 'Tourist', 'Single', 30, 30, false, false, 500000, 0, 'Available at major airports, extendable once'),
        
        -- E-KIT (Electronic Visa)
        (gen_random_uuid(), catalog_uuid, 'E-KIT', 'Electronic Visa (E-KIT)', 'Tourist', 'Single', 30, 60, false, false, 500000, 3, 'Online application, faster processing'),
        
        -- LONG-TERM VISAS
        (gen_random_uuid(), catalog_uuid, 'B213', 'KITAS (Stay Permit)', 'Residence', 'Multiple', 365, null, true, true, 5000000, 21, '1-year renewable stay permit, requires sponsor'),
        (gen_random_uuid(), catalog_uuid, 'VITAS', 'Investment Visa', 'Investment', 'Multiple', 365, null, true, false, 7500000, 30, 'For foreign investors, convertible to KITAS'),
        (gen_random_uuid(), catalog_uuid, 'IMTA', 'Work Permit', 'Work', 'Multiple', 365, null, false, true, 6000000, 21, 'Foreign worker employment permit'),
        
        -- SPECIAL PURPOSE VISAS
        (gen_random_uuid(), catalog_uuid, 'B211C', 'Social/Cultural Visa', 'Social', 'Single', 60, 180, false, true, 1000000, 10, 'For social, cultural, or educational purposes'),
        (gen_random_uuid(), catalog_uuid, 'B211D', 'Journalist Visa', 'Media', 'Single', 30, null, false, true, 1000000, 10, 'For journalists and media professionals'),
        (gen_random_uuid(), catalog_uuid, 'B211E', 'Transit Visa', 'Transit', 'Single', 7, null, false, false, 250000, 3, 'For transit through Indonesia'),
        
        -- RETIREMENT & SECOND HOME
        (gen_random_uuid(), catalog_uuid, 'RETIREMENT', 'Retirement Visa', 'Retirement', 'Multiple', 365, null, true, false, 4000000, 21, 'For retirees 55+, renewable annually'),
        (gen_random_uuid(), catalog_uuid, 'SECOND_HOME', 'Second Home Visa', 'Residence', 'Multiple', 365, null, true, false, 10000000, 30, 'For wealthy individuals, 5-10 year validity'),
        
        -- STUDENT & EDUCATION
        (gen_random_uuid(), catalog_uuid, 'STUDENT', 'Student Visa', 'Education', 'Multiple', 365, null, true, true, 3000000, 14, 'For students enrolled in Indonesian institutions'),
        (gen_random_uuid(), catalog_uuid, 'RESEARCH', 'Research Visa', 'Education', 'Single', 180, 365, false, true, 2000000, 14, 'For academic research purposes'),
        
        -- MEDICAL & HUMANITARIAN
        (gen_random_uuid(), catalog_uuid, 'MEDICAL', 'Medical Visa', 'Medical', 'Single', 60, 180, false, true, 1000000, 7, 'For medical treatment in Indonesia'),
        (gen_random_uuid(), catalog_uuid, 'HUMANITARIAN', 'Humanitarian Visa', 'Humanitarian', 'Single', 30, 90, false, true, 500000, 5, 'For humanitarian missions and aid work'),
        
        -- DIPLOMATIC & OFFICIAL
        (gen_random_uuid(), catalog_uuid, 'DIPLOMATIC', 'Diplomatic Visa', 'Diplomatic', 'Multiple', 365, null, true, false, 0, 7, 'For diplomatic personnel and officials'),
        (gen_random_uuid(), catalog_uuid, 'OFFICIAL', 'Official Visa', 'Official', 'Multiple', 90, 365, true, false, 0, 7, 'For government officials and representatives')
    ON CONFLICT DO NOTHING;

    -- Create detailed visa requirements for each product
    INSERT INTO visa_requirements (id, visa_product_id, key, value, mandatory)
    SELECT 
        gen_random_uuid(),
        vp.id,
        'passport',
        'Valid passport with minimum 6 months validity and 2 blank pages',
        true
    FROM visa_products vp 
    WHERE vp.catalog_id = catalog_uuid
    ON CONFLICT DO NOTHING;

    INSERT INTO visa_requirements (id, visa_product_id, key, value, mandatory)
    SELECT 
        gen_random_uuid(),
        vp.id,
        'photos',
        '2 passport-sized photos (4x6cm, white background)',
        true
    FROM visa_products vp 
    WHERE vp.catalog_id = catalog_uuid
    ON CONFLICT DO NOTHING;

    -- Add specific requirements for different visa types
    INSERT INTO visa_requirements (id, visa_product_id, key, value, mandatory)
    SELECT 
        gen_random_uuid(),
        vp.id,
        'financial_proof',
        'Bank statement showing minimum $2000 USD balance',
        true
    FROM visa_products vp 
    WHERE vp.catalog_id = catalog_uuid
    AND vp.category IN ('Tourist', 'Business', 'Social')
    ON CONFLICT DO NOTHING;

    INSERT INTO visa_requirements (id, visa_product_id, key, value, mandatory)
    SELECT 
        gen_random_uuid(),
        vp.id,
        'sponsor_letter',
        'Sponsor letter from Indonesian citizen or company',
        true
    FROM visa_products vp 
    WHERE vp.catalog_id = catalog_uuid
    AND vp.sponsor_needed = true
    ON CONFLICT DO NOTHING;

    INSERT INTO visa_requirements (id, visa_product_id, key, value, mandatory)
    SELECT 
        gen_random_uuid(),
        vp.id,
        'employment_contract',
        'Employment contract or job offer letter',
        true
    FROM visa_products vp 
    WHERE vp.catalog_id = catalog_uuid
    AND vp.product_code = 'IMTA'
    ON CONFLICT DO NOTHING;

    INSERT INTO visa_requirements (id, visa_product_id, key, value, mandatory)
    SELECT 
        gen_random_uuid(),
        vp.id,
        'investment_proof',
        'Proof of investment minimum $1,000,000 USD',
        true
    FROM visa_products vp 
    WHERE vp.catalog_id = catalog_uuid
    AND vp.product_code = 'VITAS'
    ON CONFLICT DO NOTHING;

    INSERT INTO visa_requirements (id, visa_product_id, key, value, mandatory)
    SELECT 
        gen_random_uuid(),
        vp.id,
        'age_requirement',
        'Minimum age 55 years for retirement visa',
        true
    FROM visa_products vp 
    WHERE vp.catalog_id = catalog_uuid
    AND vp.product_code = 'RETIREMENT'
    ON CONFLICT DO NOTHING;

    INSERT INTO visa_requirements (id, visa_product_id, key, value, mandatory)
    SELECT 
        gen_random_uuid(),
        vp.id,
        'enrollment_letter',
        'Letter of enrollment from Indonesian educational institution',
        true
    FROM visa_products vp 
    WHERE vp.catalog_id = catalog_uuid
    AND vp.product_code IN ('STUDENT', 'RESEARCH')
    ON CONFLICT DO NOTHING;

END $$;

-- Verify the data was created
SELECT 'Visa Products Created' as status, COUNT(*) as count FROM visa_products WHERE catalog_id = (SELECT id FROM catalogs WHERE business_id = '6becb7a9-f82f-4b3a-857e-28108460ee20')
UNION ALL
SELECT 'Visa Requirements Created', COUNT(*) FROM visa_requirements WHERE visa_product_id IN (SELECT id FROM visa_products WHERE catalog_id = (SELECT id FROM catalogs WHERE business_id = '6becb7a9-f82f-4b3a-857e-28108460ee20'));

-- Show all visa products
SELECT 
    vp.product_code,
    vp.name,
    vp.category,
    vp.first_stay_days,
    vp.extendable_to_days,
    vp.gov_fee_idr,
    vp.processing_sla_days,
    vp.sponsor_needed,
    vp.convertible
FROM visa_products vp
JOIN catalogs c ON vp.catalog_id = c.id
WHERE c.business_id = '6becb7a9-f82f-4b3a-857e-28108460ee20'
ORDER BY vp.category, vp.product_code;
