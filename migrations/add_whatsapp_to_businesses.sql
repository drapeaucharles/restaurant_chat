-- Add WhatsApp fields to businesses table

-- Add whatsapp_number column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='businesses' AND column_name='whatsapp_number'
    ) THEN
        ALTER TABLE businesses ADD COLUMN whatsapp_number VARCHAR(50);
    END IF;
END $$;

-- Add whatsapp_session_id column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='businesses' AND column_name='whatsapp_session_id'
    ) THEN
        ALTER TABLE businesses ADD COLUMN whatsapp_session_id VARCHAR(255);
    END IF;
END $$;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_businesses_whatsapp_session ON businesses(whatsapp_session_id);
CREATE INDEX IF NOT EXISTS idx_businesses_whatsapp_number ON businesses(whatsapp_number);

-- Update legal business example with WhatsApp
UPDATE businesses 
SET whatsapp_number = '+62 361 123456'
WHERE business_id = 'bali-legal-consulting';

-- Show the updated schema
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'businesses'
ORDER BY ordinal_position;