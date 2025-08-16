# 🗑️ Delete Dummy Restaurants Guide

## Restaurants to Delete:
1. **Test** - Dummy restaurant with placeholder menu
2. **Labrisa** - La Brisa with dummy menu item  
3. **RestoLorenzo** - Lorenzo Papa with corrupted menu data

## Option 1: Using Admin API (Once Deployed)

```bash
# 1. Login as admin
TOKEN=$(curl -X POST https://restaurantchat-production.up.railway.app/restaurant/login \
  -H "Content-Type: application/json" \
  -d '{"restaurant_id":"admin@admin.com","password":"Lol007321lol!"}' \
  -s | jq -r '.access_token')

# 2. Delete each restaurant
curl -X DELETE https://restaurantchat-production.up.railway.app/admin/restaurant/Test \
  -H "Authorization: Bearer $TOKEN"

curl -X DELETE https://restaurantchat-production.up.railway.app/admin/restaurant/Labrisa \
  -H "Authorization: Bearer $TOKEN"

curl -X DELETE https://restaurantchat-production.up.railway.app/admin/restaurant/RestoLorenzo \
  -H "Authorization: Bearer $TOKEN"
```

## Option 2: Direct Database Deletion

If you have database access, run these SQL commands:

```sql
-- Delete embeddings first (foreign key constraint)
DELETE FROM menu_embeddings 
WHERE restaurant_id IN ('Test', 'Labrisa', 'RestoLorenzo');

-- Delete chat messages
DELETE FROM chat_messages 
WHERE restaurant_id IN ('Test', 'Labrisa', 'RestoLorenzo');

-- Delete clients
DELETE FROM clients 
WHERE restaurant_id IN ('Test', 'Labrisa', 'RestoLorenzo');

-- Finally delete restaurants
DELETE FROM restaurants 
WHERE restaurant_id IN ('Test', 'Labrisa', 'RestoLorenzo');
```

## Option 3: Restaurant Self-Deletion

Each restaurant can delete itself if you have their credentials:

```bash
# Login as the restaurant
TOKEN=$(curl -X POST https://restaurantchat-production.up.railway.app/restaurant/login \
  -H "Content-Type: application/json" \
  -d '{"restaurant_id":"RESTAURANT_ID","password":"THEIR_PASSWORD"}' \
  -s | jq -r '.access_token')

# Delete self
curl -X DELETE https://restaurantchat-production.up.railway.app/restaurant/delete \
  -H "Authorization: Bearer $TOKEN"
```

## Current Status:
- ✅ Admin account is now hidden from restaurant list
- ✅ Admin can still login and manage restaurants
- ⏳ Admin delete endpoint is deployed, waiting for it to be ready

## Final Clean State:
After deletion, only these restaurants will remain:
1. **bella_vista_restaurant** - Bella Vista Gourmet (50 items)
2. **RestoBulla** - Bulla Gastrobar Tampa (61 items)
3. **admin@admin.com** - System Admin (hidden from list)