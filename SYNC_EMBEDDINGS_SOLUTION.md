# 🚨 Embedding Sync Required

## Current Status
The admin@admin.com account is a regular restaurant account, not a system admin, so it can't sync other restaurants' embeddings.

## Restaurants Needing Sync:
1. **Bulla Gastrobar Tampa** (RestoBulla) - 61 items ⚠️ PRIORITY
2. **Lorenzo Papa** (RestoLorenzo) - 3 items
3. **La Brisa** (Labrisa) - 1 item
4. **Test** (Test) - 1 item

## Solutions:

### Option 1: Add System Admin Role (RECOMMENDED)
Update the database to give admin@admin.com system admin privileges:

```sql
UPDATE restaurants 
SET role = 'system_admin' 
WHERE restaurant_id = 'admin@admin.com';
```

Then run the sync script again.

### Option 2: Restaurant Owners Fix It Themselves
Each restaurant owner needs to:
1. Login to their account
2. Go to menu management
3. Make ANY small change (even add a space)
4. Save the menu
5. This will trigger embedding generation

### Option 3: Create Backend Admin Endpoint
Add a new endpoint that doesn't require individual restaurant ownership:

```python
@router.post("/admin/force-sync-all")
def force_sync_all(
    secret_key: str,
    db: Session = Depends(get_db)
):
    if secret_key != os.getenv("ADMIN_SECRET_KEY"):
        raise HTTPException(403, "Invalid secret")
    
    # Sync all restaurants
    # ... sync code ...
```

### Option 4: Direct Database Update
Since the embedding system is working correctly for new updates, you could:
1. Trigger a menu update programmatically for each restaurant
2. Or manually run the embedding creation in the database

## Immediate Action for Bulla (61 items)
Since Bulla is the most critical:

1. Contact Bulla restaurant owner
2. Have them login and save their menu
3. OR if you have their credentials, do it for them

## The Good News
- ✅ The embedding system IS working perfectly
- ✅ New restaurants automatically get embeddings
- ✅ Menu updates automatically refresh embeddings
- ✅ Smart hybrid RAG is routing queries correctly

This is just a one-time sync needed for restaurants created before the embedding system.