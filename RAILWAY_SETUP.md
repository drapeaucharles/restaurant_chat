# Railway Auto-Deployment Setup for GSI Bali Agency

## 🚀 **Auto-Execution on Railway Restart**

**YES** - The GSI Bali Agency will **automatically execute** when Railway restarts, provided the environment variable is set.

### ✅ **What Happens on Railway Restart**

1. **App Starts** - `main.py` loads with FastAPI
2. **Feature Flag Check** - Checks `MIA_VISA_ENABLED` environment variable
3. **Auto-Startup** - If enabled, runs GSI creation in background thread
4. **Routes Active** - Visa endpoints become available immediately
5. **GSI Ready** - Agency is created and ready to handle requests

---

## 🔧 **Railway Environment Setup**

### **Required Environment Variable**

Set this in your Railway project dashboard:

```bash
MIA_VISA_ENABLED=true
```

### **How to Set in Railway Dashboard**

1. Go to your Railway project
2. Click on **"Variables"** tab
3. Add new variable:
   - **Name**: `MIA_VISA_ENABLED`
   - **Value**: `true`
4. Click **"Add"**
5. Deploy/restart your service

---

## 🔄 **Auto-Startup Flow**

When Railway restarts your app:

```
Railway Start
    ↓
main.py loads
    ↓
MIA_VISA_ENABLED=true detected
    ↓
Visa routes enabled ✅
    ↓
Background thread starts
    ↓
Database migrations run
    ↓
GSI Bali Agency created
    ↓
Ready to serve visa requests 🎉
```

### **Startup Logs You'll See**

```
✅ Visa agency routes enabled
🚀 GSI Bali Agency auto-startup initiated...
🔧 Running database migrations...
✅ Database migrations completed
🔧 GSI Bali Agency not found - creating now...
✅ GSI Bali Agency created successfully!
🎉 GSI BALI AGENCY STARTUP COMPLETE!
✅ Ready to handle visa inquiries
```

---

## 🛡️ **Safety Features**

### **Non-Blocking Startup**
- GSI creation runs in **background thread**
- App starts immediately, GSI initializes in parallel
- No delay to existing restaurant functionality

### **Idempotent Creation**
- Checks if GSI already exists before creating
- Safe to run multiple times
- No duplicate agencies created

### **Graceful Failure**
- If GSI creation fails, app continues running
- Restaurant functionality unaffected
- Error logged but doesn't crash app

### **Feature Flag Control**
- Set `MIA_VISA_ENABLED=false` to disable
- Instant rollback capability
- Restaurant system continues normally

---

## 🧪 **Testing Auto-Startup**

### **Method 1: Railway Dashboard**
1. Set `MIA_VISA_ENABLED=true`
2. Restart your Railway service
3. Check logs for startup messages
4. Test: `curl https://your-app.railway.app/visa/health`

### **Method 2: Manual Trigger**
```bash
# In Railway console or local environment
python3 startup_gsi.py
```

### **Method 3: API Test**
```bash
curl -X POST https://your-app.railway.app/visa/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to visit Bali",
    "client_id": "test-123",
    "restaurant_id": "gsi_bali_agency"
  }'
```

---

## 📊 **Verification Checklist**

After Railway restart, verify:

- [ ] `MIA_VISA_ENABLED=true` set in Railway variables
- [ ] App starts successfully (check Railway logs)
- [ ] Visa routes enabled message appears
- [ ] GSI auto-startup initiated message appears
- [ ] GSI creation completed message appears
- [ ] `/visa/health` endpoint returns `{"status": "available"}`
- [ ] `/visa/chat` endpoint accepts requests
- [ ] Restaurant functionality still works normally

---

## 🔧 **Troubleshooting**

### **If GSI Doesn't Auto-Create**

1. **Check Environment Variable**
   ```bash
   # In Railway console
   echo $MIA_VISA_ENABLED
   # Should return: true
   ```

2. **Check Railway Logs**
   - Look for "GSI auto-startup initiated" message
   - Check for any error messages

3. **Manual Creation**
   ```bash
   # In Railway console
   python3 create_gsi_agency.py --force
   ```

4. **Database Issues**
   ```bash
   # Run migrations manually
   python3 migrations/run_migrations.py --force
   ```

### **If Feature Flag Not Working**

1. Verify variable name is exactly: `MIA_VISA_ENABLED`
2. Verify value is exactly: `true` (lowercase)
3. Restart Railway service after setting variable
4. Check Railway logs for feature flag detection

---

## 🎯 **Expected Behavior**

### **✅ When MIA_VISA_ENABLED=true**
- Visa routes automatically enabled
- GSI agency automatically created
- Both restaurant and visa systems active
- Auto-startup on every Railway restart

### **✅ When MIA_VISA_ENABLED=false (or unset)**
- Visa routes disabled
- No GSI creation attempted
- Only restaurant system active
- Normal restaurant behavior

---

## 🚀 **Ready for Production**

**Answer: YES** - GSI Bali Agency will **automatically execute** when Railway restarts.

**Requirements:**
1. Set `MIA_VISA_ENABLED=true` in Railway environment variables
2. Deploy the current codebase to Railway
3. Railway will handle the rest automatically

**Result:** GSI Bali Agency will be live and ready to handle visa inquiries immediately after Railway restart! 🎉
