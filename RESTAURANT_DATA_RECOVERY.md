# 🚨 Restaurant Data Recovery Guide

## What Happened
During the visa vertical implementation, the `restaurants` table was accidentally dropped/recreated, causing loss of existing restaurant data.

## ❌ What NOT to Do
- Don't create hardcoded fake restaurants
- Don't auto-generate sample data
- Don't assume what restaurants existed

## ✅ Proper Solutions

### Option 1: Database Backup Recovery
If you have database backups:
```sql
-- Restore from backup (if available)
-- Contact Railway support for backup restoration
```

### Option 2: Manual Recreation via API
Create restaurants through the proper API endpoints:

```bash
# Example: Create a restaurant via API
curl -X POST "https://your-api.railway.app/restaurants" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "your_restaurant_name",
    "password": "secure_password",
    "data": {
      "name": "Your Restaurant Name",
      "description": "Restaurant description",
      "menu": [...],
      "location": {...}
    }
  }'
```

### Option 3: Frontend Creation
Use the admin panel to create restaurants:
1. Go to `/admin/restaurants`
2. Click "Add Restaurant"
3. Fill in real restaurant details
4. Upload actual menu data

### Option 4: Migration Script (If you know the original data)
If you remember the original restaurants, create a proper migration:

```python
# migrations/restore_known_restaurants.py
def restore_known_restaurants():
    # Only if you know the actual restaurant data
    restaurants = [
        {
            "restaurant_id": "actual_restaurant_id",
            "password": "actual_password",
            "data": {...}  # Real data
        }
    ]
    # Insert real data
```

## Current State
- ✅ Admin users exist (`admin`, `admin@admin.com`)
- ✅ GSI Bali Agency exists (visa vertical)
- ❌ Original restaurant data lost
- ✅ System ready for new restaurant creation

## Next Steps
1. **Identify what restaurants actually existed** (check logs, backups, or ask users)
2. **Recreate restaurants with real data** via API or frontend
3. **Don't use auto-generated fake data**

## Prevention
- Set up regular database backups
- Test migrations on staging first
- Use feature flags for major changes
- Keep migration rollback scripts ready
