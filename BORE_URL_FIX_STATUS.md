# Bore.pub URL Update Fix - Status Report

## Problem Identified
As you correctly identified, the bore.pub URL changes when the tunnel reconnects, but the database was not being updated.

## Solution Implemented
1. **Backend Fix (COMPLETED & DEPLOYED)**:
   - Modified `/heartbeat` endpoint to check for bore.pub URLs in `public_url` field
   - Automatically updates database when bore URL changes
   - Code is live on Railway

2. **How It Works**:
   ```python
   # In heartbeat endpoint:
   if public_url and public_url.startswith('http://bore.pub:'):
       new_ip = f"bore.pub:{bore_port}"
       if miner.ip_address != new_ip:
           miner.ip_address = new_ip  # Updates database
   ```

## Current Status
- ✅ Backend code updated and deployed
- ❌ GPU miner still has old bore URL (bore.pub:45413)
- ❌ Push architecture falling back to queue

## What Needs to Happen
The GPU miner needs to:
1. Restart (or bore tunnel needs to reconnect)
2. Get a new bore.pub URL (e.g., bore.pub:53103)
3. Send heartbeats with the new `public_url` field
4. Backend will automatically update the database

## Test Results
- Database shows: `bore.pub:45413` (old URL)
- Last heartbeat: 2025-09-08 06:19:25 UTC
- Push attempts fall back to queue because old URL is unreachable

## Next Steps
Once the GPU miner restarts:
- It will get a new bore URL
- Heartbeats will include the new URL
- Database will auto-update
- Push architecture will work again

The fix is ready and waiting for the miner to restart with a new bore URL.