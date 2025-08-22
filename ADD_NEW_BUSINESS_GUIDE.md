# Guide: Adding New Businesses

## Quick Start - Add a New Business

### 1. Create SQL file for your business
Create a file like `setup_[business_name].sql`:

```sql
-- Example: setup_salon_business.sql

-- 1. Insert the business
INSERT INTO businesses (
    business_id, password, role, data, 
    business_type, metadata, rag_mode
) VALUES (
    'glamour-beauty-salon',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGH9pyp2HJa', -- 'password123'
    'owner',
    '{
        "name": "Glamour Beauty Salon",
        "email": "info@glamourbeauty.com",
        "phone": "+62 812 9876 5432",
        "address": "Jl. Seminyak No. 123, Bali",
        "description": "Premium beauty salon with expert stylists"
    }'::jsonb,
    'salon',
    '{
        "theme_color": "#e91e63",
        "specialties": ["hair", "nails", "facial", "massage"],
        "languages": ["English", "Indonesian"]
    }'::jsonb,
    'memory_universal'  -- Uses universal service for non-restaurants
);

-- 2. Insert products/services
INSERT INTO products (id, business_id, name, description, price, category, product_type, tags, available) VALUES
('glamour-beauty-salon_haircut', 'glamour-beauty-salon', 'Haircut & Style', 'Professional haircut with wash and style', 35, 'hair_services', 'service', '["haircut", "style", "wash", "treatment"]'::jsonb, true),
('glamour-beauty-salon_manicure', 'glamour-beauty-salon', 'Manicure', 'Full manicure with polish', 25, 'nail_services', 'service', '["nails", "manicure", "polish", "beauty"]'::jsonb, true),
('glamour-beauty-salon_facial', 'glamour-beauty-salon', 'Deep Cleansing Facial', '60-minute deep cleansing facial treatment', 50, 'facial_services', 'service', '["facial", "skincare", "cleansing", "treatment"]'::jsonb, true);
```

### 2. Run the SQL on Railway
```bash
PGPASSWORD=pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh psql -h shortline.proxy.rlwy.net -p 31808 -U postgres -d railway -f setup_salon_business.sql
```

### 3. Generate Embeddings (Optional but Recommended)

#### Option A: Use OpenAI (if API key is set)
```bash
python3 update_embeddings_openai.py
```

#### Option B: Text search works automatically!
No action needed - the system will use SQL pattern matching

## Frontend Integration

### 1. The business will automatically appear in:
- Business listing endpoint: `/businesses`
- Business details: `/businesses/{business_id}`
- Chat endpoint: `/chat` (with restaurant_id = business_id)

### 2. For your existing restaurant frontend:

#### Simple Integration - Direct Link
```html
<!-- Add a business selector -->
<select id="businessSelector" onchange="switchBusiness(this.value)">
    <option value="warung-makan-padang">Warung Makan Padang</option>
    <option value="bali-legal-consulting">Bali Legal Services</option>
    <option value="glamour-beauty-salon">Glamour Beauty Salon</option>
</select>

<script>
function switchBusiness(businessId) {
    // Update your chat to use the selected business
    currentBusinessId = businessId;
    // Clear chat history
    clearChat();
    // Show welcome message for new business
    showWelcomeMessage(businessId);
}
</script>
```

#### Advanced Integration - Dynamic Loading
```javascript
// Load available businesses
async function loadBusinesses() {
    const response = await fetch('https://your-api.railway.app/businesses');
    const data = await response.json();
    
    // Populate dropdown or grid
    data.businesses.forEach(business => {
        addBusinessOption(business);
    });
}

// When sending chat message
async function sendChatMessage(message) {
    const response = await fetch('https://your-api.railway.app/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            restaurant_id: currentBusinessId,  // Works for any business
            message: message,
            client_id: clientUUID
        })
    });
}
```

### 3. Business-Specific Themes
Each business can have custom theme in metadata:

```javascript
// Get business details with theme
const business = await fetch(`/businesses/${businessId}`).then(r => r.json());

// Apply theme
document.body.style.setProperty('--primary-color', business.theme.primary_color);
if (business.theme.logo_url) {
    document.getElementById('logo').src = business.theme.logo_url;
}
```

## Adding Business Types

### Currently Supported Types:
- `restaurant` - Food service
- `legal_visa` - Legal and visa services
- `salon` - Beauty services
- `hotel` - Accommodation
- `repair` - Device repair services

### To Add a New Type:
1. Use it in the `business_type` field when creating business
2. The universal memory service will adapt automatically
3. Add type-specific keywords in `rag_chat_memory_universal.py` for better context

## Testing Your New Business

### 1. Check it exists:
```bash
curl https://your-api.railway.app/debug/business/your-business-id/products
```

### 2. Test chat:
```bash
curl -X POST https://your-api.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "your-business-id",
    "message": "What services do you offer?",
    "client_id": "123e4567-e89b-12d3-a456-426614174000"
  }'
```

### 3. Test search:
```bash
curl -X POST https://your-api.railway.app/debug/search \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "your-business-id",
    "query": "your service name"
  }'
```

## Embedding Strategies

### For Production at Scale:

1. **OpenAI API** (Recommended)
   - Set `OPENAI_API_KEY` in Railway
   - Automatic embedding generation
   - High quality, works immediately

2. **Text Search** (Current Default)
   - No setup needed
   - Works well for <1000 products per business
   - Optimized for common business terms

3. **Local Generation** (For Cost Saving)
   - Generate embeddings on your GPU
   - Upload to database
   - Best for bulk operations

## Example: Complete Hotel Setup

```sql
-- Hotel with full services
INSERT INTO businesses (business_id, password, role, data, business_type, metadata, rag_mode) VALUES (
    'paradise-beach-hotel',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGH9pyp2HJa',
    'owner',
    '{"name": "Paradise Beach Hotel", "email": "info@paradisebeach.com", "phone": "+62 361 123456", "address": "Beachfront, Seminyak", "description": "Luxury beachfront hotel with stunning ocean views", "website": "https://paradisebeach.com"}'::jsonb,
    'hotel',
    '{"stars": 5, "amenities": ["pool", "spa", "restaurant", "bar", "gym"], "theme_color": "#ff6b6b", "languages": ["English", "Indonesian", "Japanese", "Chinese"]}'::jsonb,
    'memory_universal'
);

-- Room types
INSERT INTO products (id, business_id, name, description, price, category, product_type, features, tags, available) VALUES
('paradise-beach-hotel_deluxe_ocean', 'paradise-beach-hotel', 'Deluxe Ocean View', 'Spacious room with ocean view, king bed, balcony', 200, 'rooms', 'accommodation', '["Ocean view", "King bed", "Balcony", "Mini bar", "Free WiFi", "Breakfast included"]'::jsonb, '["room", "ocean view", "deluxe", "balcony"]'::jsonb, true),
('paradise-beach-hotel_suite', 'paradise-beach-hotel', 'Beach Suite', 'Luxury suite with living area and direct beach access', 400, 'rooms', 'accommodation', '["Beach access", "Living room", "Kitchen", "2 bedrooms", "Private pool"]'::jsonb, '["suite", "beach", "luxury", "private pool"]'::jsonb, true);

-- Hotel services
INSERT INTO products (id, business_id, name, description, price, category, product_type, tags, available) VALUES
('paradise-beach-hotel_spa', 'paradise-beach-hotel', 'Spa Package', 'Full day spa package with massage and treatments', 150, 'services', 'service', '["spa", "massage", "relaxation", "wellness"]'::jsonb, true),
('paradise-beach-hotel_airport_transfer', 'paradise-beach-hotel', 'Airport Transfer', 'Private car transfer to/from airport', 35, 'services', 'service', '["transfer", "airport", "transport", "pickup"]'::jsonb, true);
```

That's it! Your multi-business system is ready to scale.