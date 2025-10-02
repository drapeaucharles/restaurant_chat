# 🚀 Deploy GSI Bali Agency - Instructions

Since we can't install SQLAlchemy locally, here are the exact steps to deploy GSI in your Railway environment:

## 📋 **Method 1: Railway Console (Recommended)**

1. **Open Railway Console**
   - Go to Railway Dashboard → Your Project
   - Click **"Console"** or **"Terminal"**

2. **Run the deployment script**
   ```bash
   python3 deploy_gsi_railway.py
   ```

3. **Expected output:**
   ```
   🚀 DEPLOYING GSI BALI AGENCY
   ✅ Database connection successful
   🔧 Running visa migrations...
   ✅ Migrations completed
   🏢 Creating GSI Bali Agency...
   ✅ GSI business created
   📋 Creating policy pack...
   ✅ Policy pack created
   📦 Creating visa catalog...
   ✅ Created catalog with 3 products
   🎉 GSI BALI AGENCY DEPLOYMENT COMPLETE!
   ```

## 📋 **Method 2: Manual SQL (If script fails)**

If the script doesn't work, run these SQL commands directly in Railway console:

```bash
# Connect to database
python3 -c "
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Create business
    conn.execute(text('''
        INSERT INTO businesses (business_id, type, name, password, role, data)
        VALUES (
            ''gsi_bali_agency'',
            ''visa_agency'',
            ''GSI Bali Agency'',
            ''gsi2025'',
            ''owner'',
            ''{\"description\": \"Professional visa services in Bali\", \"location\": {\"address\": \"Seminyak, Bali\"}}''
        ) ON CONFLICT (business_id) DO NOTHING;
    '''))
    
    print('✅ GSI Bali Agency created')
    conn.commit()
"
```

## 📋 **Method 3: API Test (Verify it works)**

After deployment, test the GSI agency:

```bash
# Health check
curl -X POST /visa/health

# Chat test
curl -X POST /visa/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to visit Bali for vacation",
    "client_id": "test-123",
    "restaurant_id": "gsi_bali_agency"
  }'
```

## 🎯 **What Gets Created**

- **Business**: `gsi_bali_agency` (visa agency type)
- **Products**: A1 (Free), B1 (500K IDR), C1 (1M IDR)
- **Policy**: Indonesia rules with tourist visa support
- **Catalog**: Complete visa product catalog

## ✅ **Verification**

After deployment, GSI will be ready to:
- Handle visa inquiries via `/visa/chat`
- Provide visa recommendations (A1, B1, C1)
- Process applications and document uploads
- Support KITAS consultation framework

---

## 🚀 **Quick Deploy Command**

**Run this in Railway Console:**
```bash
python3 deploy_gsi_railway.py
```

That's it! GSI Bali Agency will be live and ready to handle visa inquiries! 🎉
