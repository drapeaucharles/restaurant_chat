#!/bin/bash
# One-liner installation script for MIA GPU Miner
# Usage: curl -sSL https://raw.githubusercontent.com/drapeaucharles/restaurant_chat/main/install_miner_oneliner.sh | bash
# Note: This file needs to be committed and pushed to the main branch first!

set -e

INSTALL_DIR="/home/$USER/mia-miner"
BORE_VERSION="v0.5.0"
MIA_BACKEND_URL="https://mia-backend-production.up.railway.app"

echo "🚀 Installing MIA GPU Miner..."

# Create installation directory
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# First, register with MIA backend to get a miner ID
echo "📝 Registering with MIA backend..."
REGISTRATION_RESPONSE=$(curl -s -X POST "${MIA_BACKEND_URL}/register_miner" \
  -H "Content-Type: application/json" \
  -d '{"type": "gpu", "capabilities": ["llm", "chat"]}')

MINER_ID=$(echo "$REGISTRATION_RESPONSE" | grep -o '"miner_id":[^,]*' | cut -d'"' -f4)

if [ -z "$MINER_ID" ]; then
    echo "❌ Failed to register miner. Response: $REGISTRATION_RESPONSE"
    exit 1
fi

echo "✅ Registered as Miner ID: $MINER_ID"

# Download the improved miner script
echo "📥 Downloading miner script..."
cat > mia_gpu_miner.py << 'EOF'
#!/usr/bin/env python3
"""
Improved MIA GPU Miner with better logging and auto-restart
"""
import os
import sys
import time
import json
import requests
import subprocess
import logging
import signal
import threading
from datetime import datetime
from typing import Optional, Dict, Any

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/mia_miner.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

class MIAGPUMiner:
    def __init__(self):
        self.miner_id = os.getenv('MINER_ID', '1')
        self.mia_backend_url = "https://mia-backend-production.up.railway.app"
        self.bore_port = 5000  # Flask/miner API port
        self.vllm_port = 8000  # vLLM service port
        self.public_url = None
        self.bore_process = None
        self.flask_process = None
        self.running = True
        self.heartbeat_failures = 0
        self.max_heartbeat_failures = 3
        self.bore_failures = 0
        self.max_bore_failures = 3
        self.last_successful_heartbeat = time.time()
        self.heartbeat_interval = 30  # seconds
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info("Received shutdown signal, cleaning up...")
        self.running = False
        self.cleanup()
        sys.exit(0)

    def start_bore(self) -> bool:
        """Start bore tunnel with better error handling"""
        try:
            # Kill any existing bore process
            subprocess.run(['pkill', '-f', 'bore'], capture_output=True)
            time.sleep(1)
            
            logger.info(f"Starting bore tunnel on port {self.bore_port}...")
            self.bore_process = subprocess.Popen(
                ['bore', 'local', str(self.bore_port), '--to', 'bore.pub'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Wait for bore to start and capture the public URL
            start_time = time.time()
            while time.time() - start_time < 10:
                if self.bore_process.poll() is not None:
                    logger.error("Bore process died unexpectedly")
                    return False
                    
                line = self.bore_process.stdout.readline()
                if line:
                    logger.info(f"Bore: {line.strip()}")
                    if 'listening on' in line.lower():
                        # Extract public URL from bore output
                        parts = line.split()
                        for part in parts:
                            if 'bore.pub' in part:
                                self.public_url = part.strip()
                                if not self.public_url.startswith('http'):
                                    self.public_url = f"http://{self.public_url}"
                                logger.info(f"✅ Bore tunnel established: {self.public_url}")
                                return True
                time.sleep(0.1)
            
            logger.error("Timeout waiting for bore to establish tunnel")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start bore: {e}")
            return False

    def start_flask_server(self) -> bool:
        """Start Flask server for handling jobs"""
        try:
            logger.info(f"Starting Flask server on port {self.bore_port}...")
            
            # Create a simple Flask app inline
            flask_code = f'''
import sys
import json
import time
import logging
import subprocess
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({{"status": "healthy", "miner_id": "{self.miner_id}"}})

@app.route('/process', methods=['POST'])
def process():
    try:
        logger.info("Received job request")
        data = request.json
        
        # Log job details
        logger.info(f"Job ID: {{data.get('job_id')}}")
        logger.info(f"Message length: {{len(data.get('message', ''))}}")
        logger.info(f"Has tools: {{'tools' in data}}")
        
        # Forward to vLLM
        import requests
        vllm_url = "http://localhost:{self.vllm_port}/v1/chat/completions"
        
        # Prepare vLLM request
        vllm_data = {{
            "messages": [{{"role": "user", "content": data['message']}}],
            "max_tokens": data.get('max_tokens', 150),
            "temperature": 0.7
        }}
        
        if 'tools' in data:
            vllm_data['tools'] = data['tools']
        
        logger.info(f"Forwarding to vLLM at {{vllm_url}}")
        response = requests.post(vllm_url, json=vllm_data, timeout=60)
        
        if response.status_code != 200:
            logger.error(f"vLLM error: {{response.status_code}} - {{response.text}}")
            return jsonify({{"status": "error", "error": f"vLLM error: {{response.status_code}}"}}), 500
        
        result = response.json()
        logger.info("Job completed successfully")
        
        # Extract the response
        return jsonify({{
            "status": "completed",
            "response": result['choices'][0]['message']['content'] if result.get('choices') else "Error processing"
        }})
        
    except Exception as e:
        logger.error(f"Error processing job: {{e}}", exc_info=True)
        return jsonify({{"status": "error", "error": str(e)}}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port={self.bore_port}, debug=False)
'''
            
            # Write Flask app to temp file
            flask_file = '/tmp/mia_flask_server.py'
            with open(flask_file, 'w') as f:
                f.write(flask_code)
            
            # Start Flask server
            self.flask_process = subprocess.Popen(
                [sys.executable, flask_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Wait for Flask to start
            time.sleep(2)
            if self.flask_process.poll() is not None:
                logger.error("Flask process died unexpectedly")
                return False
            
            # Test Flask health
            try:
                response = requests.get(f"http://localhost:{self.bore_port}/health", timeout=5)
                if response.status_code == 200:
                    logger.info("✅ Flask server is running")
                    return True
            except:
                pass
            
            logger.error("Flask server failed to start properly")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start Flask server: {e}")
            return False

    def send_heartbeat(self) -> bool:
        """Send heartbeat to MIA backend with detailed logging"""
        try:
            heartbeat_data = {
                "miner_id": self.miner_id,
                "status": "available",
                "timestamp": datetime.now().isoformat()
            }
            
            # Include public URL if available
            if self.public_url:
                heartbeat_data["public_url"] = self.public_url
                logger.debug(f"Sending heartbeat with URL: {self.public_url}")
            
            response = requests.post(
                f"{self.mia_backend_url}/heartbeat",
                json=heartbeat_data,
                timeout=10
            )
            
            if response.status_code == 200:
                self.heartbeat_failures = 0
                self.last_successful_heartbeat = time.time()
                logger.debug(f"✅ Heartbeat successful: {response.text}")
                return True
            else:
                logger.warning(f"Heartbeat failed with status {response.status_code}: {response.text}")
                self.heartbeat_failures += 1
                return False
                
        except requests.exceptions.Timeout:
            logger.error("Heartbeat timeout - MIA backend not responding")
            self.heartbeat_failures += 1
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Heartbeat connection error: {str(e)}")
            self.heartbeat_failures += 1
            return False
        except Exception as e:
            logger.error(f"Unexpected heartbeat error: {type(e).__name__}: {str(e)}")
            self.heartbeat_failures += 1
            return False

    def check_bore_health(self) -> bool:
        """Check if bore tunnel is still working"""
        if self.bore_process is None or self.bore_process.poll() is not None:
            logger.error("Bore process is not running")
            return False
        
        # Also check if we can reach our Flask server through localhost
        try:
            response = requests.get(f"http://localhost:{self.bore_port}/health", timeout=2)
            return response.status_code == 200
        except:
            return False

    def restart_services(self):
        """Restart bore and Flask services"""
        logger.warning("Restarting services due to failures...")
        
        # Stop existing services
        if self.bore_process:
            self.bore_process.terminate()
            time.sleep(1)
            if self.bore_process.poll() is None:
                self.bore_process.kill()
        
        if self.flask_process:
            self.flask_process.terminate()
            time.sleep(1)
            if self.flask_process.poll() is None:
                self.flask_process.kill()
        
        time.sleep(2)
        
        # Start services again
        if self.start_bore():
            time.sleep(2)
            if self.start_flask_server():
                logger.info("✅ Services restarted successfully")
                self.heartbeat_failures = 0
                self.bore_failures = 0
                return True
        
        logger.error("Failed to restart services")
        return False

    def heartbeat_loop(self):
        """Main heartbeat loop with auto-restart logic"""
        while self.running:
            try:
                # Check if heartbeat failures exceeded threshold
                if self.heartbeat_failures >= self.max_heartbeat_failures:
                    logger.warning(f"Heartbeat failures ({self.heartbeat_failures}) exceeded threshold")
                    
                    # First check bore health
                    if not self.check_bore_health():
                        logger.error("Bore tunnel appears to be down")
                        self.restart_services()
                    else:
                        # Bore is fine, might be network issue
                        logger.warning("Bore is healthy but heartbeats failing - possible network issue")
                
                # Send heartbeat
                self.send_heartbeat()
                
                # Log status every 5 heartbeats
                if hasattr(self, '_heartbeat_count'):
                    self._heartbeat_count += 1
                else:
                    self._heartbeat_count = 1
                    
                if self._heartbeat_count % 5 == 0:
                    uptime = time.time() - self.last_successful_heartbeat
                    logger.info(f"Status - Failures: {self.heartbeat_failures}, Uptime: {uptime:.1f}s")
                
                # Sleep until next heartbeat
                time.sleep(self.heartbeat_interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}", exc_info=True)
                time.sleep(5)

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up miner resources...")
        
        if self.bore_process:
            self.bore_process.terminate()
        if self.flask_process:
            self.flask_process.terminate()
        
        # Send final heartbeat to notify unavailability
        try:
            requests.post(
                f"{self.mia_backend_url}/heartbeat",
                json={"miner_id": self.miner_id, "status": "offline"},
                timeout=5
            )
        except:
            pass

    def run(self):
        """Main run method"""
        logger.info(f"Starting MIA GPU Miner ID: {self.miner_id}")
        
        # Start services
        if not self.start_bore():
            logger.error("Failed to start bore tunnel")
            return
        
        time.sleep(2)
        
        if not self.start_flask_server():
            logger.error("Failed to start Flask server")
            return
        
        # Start heartbeat loop
        logger.info("Starting heartbeat loop...")
        self.heartbeat_loop()

if __name__ == "__main__":
    # Set miner ID from command line or environment
    if len(sys.argv) > 1:
        os.environ['MINER_ID'] = sys.argv[1]
    
    miner = MIAGPUMiner()
    try:
        miner.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        miner.cleanup()
EOF

chmod +x mia_gpu_miner.py

# Install bore if not already installed
if ! command -v bore &> /dev/null; then
    echo "📦 Installing bore..."
    cd /tmp
    wget -q https://github.com/ekzhang/bore/releases/download/${BORE_VERSION}/bore-${BORE_VERSION}-x86_64-unknown-linux-musl.tar.gz
    tar -xf bore-${BORE_VERSION}-x86_64-unknown-linux-musl.tar.gz
    sudo mv bore /usr/local/bin/
    rm bore-${BORE_VERSION}-x86_64-unknown-linux-musl.tar.gz
    cd "$INSTALL_DIR"
fi

# Check for Python dependencies
echo "📦 Checking Python dependencies..."
pip3 install --quiet flask requests

# Create systemd service
echo "🔧 Creating systemd service..."
sudo tee /etc/systemd/system/mia-gpu-miner.service > /dev/null << EOF
[Unit]
Description=MIA GPU Miner Service (ID: $MINER_ID)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment="MINER_ID=$MINER_ID"
ExecStart=/usr/bin/python3 $INSTALL_DIR/mia_gpu_miner.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Restart conditions
RestartPreventExitStatus=0
StartLimitIntervalSec=60
StartLimitBurst=5

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start the service
echo "🚀 Starting miner service..."
sudo systemctl daemon-reload
sudo systemctl enable mia-gpu-miner
sudo systemctl start mia-gpu-miner

echo "✅ MIA GPU Miner installed and started!"
echo "   Miner ID: $MINER_ID"
echo ""
echo "Useful commands:"
echo "  Check status:  sudo systemctl status mia-gpu-miner"
echo "  View logs:     sudo journalctl -u mia-gpu-miner -f"
echo "  Restart:       sudo systemctl restart mia-gpu-miner"
echo "  Stop:          sudo systemctl stop mia-gpu-miner"
echo ""
echo "Log file: /tmp/mia_miner.log"