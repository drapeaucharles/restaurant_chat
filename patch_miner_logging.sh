#!/bin/bash
# Patch script to improve heartbeat error logging in existing miner

echo "🔧 Patching MIA miner for better heartbeat error logging..."

# Find the miner script
MINER_FILE="/data/qwen-awq-miner/mia_miner_heartbeat.py"

if [ ! -f "$MINER_FILE" ]; then
    echo "❌ Miner file not found at $MINER_FILE"
    echo "Looking for alternative locations..."
    
    # Try to find it
    FOUND=$(find /data -name "mia_miner_heartbeat.py" -type f 2>/dev/null | head -1)
    if [ -n "$FOUND" ]; then
        MINER_FILE="$FOUND"
        echo "✅ Found at: $MINER_FILE"
    else
        echo "❌ Could not find miner file"
        exit 1
    fi
fi

# Backup original
cp "$MINER_FILE" "${MINER_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

# Create improved heartbeat function
cat > /tmp/improved_heartbeat.py << 'EOF'
    async def send_heartbeat(self):
        """Send heartbeat to backend with improved error logging"""
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    # Check if bore needs restart (non-blocking)
                    self.restart_bore_if_needed()
                    
                    if not self.is_processing and self.public_url:
                        data = {
                            "miner_id": self.miner_id,
                            "status": "available",
                            "timestamp": datetime.utcnow().isoformat(),
                            "port": int(self.bore_port) if self.bore_port else 80,
                            "public_url": self.public_url
                        }
                        
                        async with session.post(
                            f"{self.backend_url}/heartbeat",
                            json=data,
                            headers={"Authorization": f"Bearer {self.miner_key}"},
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            if response.status == 200:
                                logger.debug("❤️ Heartbeat sent successfully")
                                # Reset bore failures on successful heartbeat
                                if self.bore_failures > 0 and self.bore_failures < self.max_bore_failures:
                                    self.bore_failures = max(0, self.bore_failures - 1)
                            else:
                                # Log the actual error response
                                error_text = await response.text()
                                logger.warning(f"Heartbeat failed: {response.status} - {error_text}")
                    
                    await asyncio.sleep(self.heartbeat_interval)
                    
                except asyncio.TimeoutError:
                    logger.error("Heartbeat error: Timeout while sending heartbeat to backend")
                    self.bore_failures += 1
                except aiohttp.ClientError as e:
                    logger.error(f"Heartbeat error: Network error - {type(e).__name__}: {str(e)}")
                    self.bore_failures += 1
                except Exception as e:
                    logger.error(f"Heartbeat error: {type(e).__name__}: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Check if bore tunnel might be down
                    if "bore" in str(e).lower() or "connection" in str(e).lower():
                        self.bore_failures += 1
                    
                    await asyncio.sleep(5)
EOF

# Also improve the restart_bore_if_needed function
cat > /tmp/improved_restart_bore.py << 'EOF'
    def restart_bore_if_needed(self):
        """Check and restart bore if needed with better logging"""
        current_time = time.time()
        
        # Only check periodically
        if current_time - self.last_bore_check < self.bore_check_interval:
            return
            
        self.last_bore_check = current_time
        
        # Check if bore process is alive
        if self.bore_process and self.bore_process.poll() is not None:
            exit_code = self.bore_process.poll()
            logger.error(f"Bore process died with exit code: {exit_code}")
            self.bore_failures = self.max_bore_failures  # Force restart
        
        # Check bore health by testing Flask endpoint
        if not self.check_bore_health():
            self.bore_failures += 1
            logger.warning(f"Bore tunnel unhealthy (failures: {self.bore_failures}/{self.max_bore_failures})")
            
            # Log more details about the failure
            if self.bore_process:
                logger.info(f"Bore process state: {'running' if self.bore_process.poll() is None else 'dead'}")
            logger.info(f"Public URL: {self.public_url}")
            logger.info(f"Bore port: {self.bore_port}")
            
            # Restart if we've hit the failure threshold
            if self.bore_failures >= self.max_bore_failures:
                logger.info("🔄 Restarting bore tunnel due to repeated failures...")
                self.bore_failures = 0  # Reset counter
                
                # Restart bore
                if self.start_bore():
                    logger.info("✅ Bore tunnel restarted successfully")
                else:
                    logger.error("❌ Failed to restart bore tunnel")
                    # Wait a bit before trying again
                    time.sleep(10)
EOF

# Apply the patches
echo "📝 Applying patches..."

# Create a Python script to do the replacement
cat > /tmp/apply_patch.py << 'EOF'
import sys
import re

# Read the original file
with open(sys.argv[1], 'r') as f:
    content = f.read()

# Read the patches
with open('/tmp/improved_heartbeat.py', 'r') as f:
    new_heartbeat = f.read()

with open('/tmp/improved_restart_bore.py', 'r') as f:
    new_restart = f.read()

# Replace send_heartbeat method
pattern1 = r'async def send_heartbeat\(self\):.*?(?=\n    def|\n    async def|\nclass|\Z)'
content = re.sub(pattern1, new_heartbeat.strip() + '\n', content, flags=re.DOTALL)

# Replace restart_bore_if_needed method
pattern2 = r'def restart_bore_if_needed\(self\):.*?(?=\n    def|\n    async def|\nclass|\Z)'
content = re.sub(pattern2, new_restart.strip() + '\n', content, flags=re.DOTALL)

# Write the patched file
with open(sys.argv[1], 'w') as f:
    f.write(content)

print("✅ Patches applied successfully")
EOF

python3 /tmp/apply_patch.py "$MINER_FILE"

# Restart the miner service if it's running
echo "🔄 Restarting miner service..."
if systemctl is-active --quiet mia-gpu-miner; then
    sudo systemctl restart mia-gpu-miner
    echo "✅ Miner service restarted"
else
    echo "ℹ️ Miner service not running, you'll need to start it manually"
fi

# Clean up temp files
rm -f /tmp/improved_heartbeat.py /tmp/improved_restart_bore.py /tmp/apply_patch.py

echo "✅ Patching complete!"
echo ""
echo "The miner now has:"
echo "- Detailed heartbeat error logging"
echo "- Better bore process monitoring"
echo "- More informative failure messages"
echo ""
echo "Monitor logs with:"
echo "  tail -f /data/qwen-awq-miner/miner_heartbeat.log"
echo "  sudo journalctl -u mia-gpu-miner -f"