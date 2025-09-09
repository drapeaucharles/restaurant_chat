#!/bin/bash
# Setup script for improved MIA GPU miner

echo "🚀 Setting up MIA GPU Miner..."

# Make miner script executable
chmod +x mia_gpu_miner_improved.py

# Install bore if not already installed
if ! command -v bore &> /dev/null; then
    echo "📦 Installing bore..."
    # Download and install bore
    wget https://github.com/ekzhang/bore/releases/download/v0.5.0/bore-v0.5.0-x86_64-unknown-linux-musl.tar.gz
    tar -xf bore-v0.5.0-x86_64-unknown-linux-musl.tar.gz
    sudo mv bore /usr/local/bin/
    rm bore-v0.5.0-x86_64-unknown-linux-musl.tar.gz
fi

# Option 1: Run directly
echo "To run the miner directly:"
echo "  python3 mia_gpu_miner_improved.py [MINER_ID]"
echo ""

# Option 2: Install as systemd service (requires sudo)
echo "To install as a systemd service (auto-restart on failure):"
echo "  1. Edit mia-gpu-miner.service and replace \$USER with your username"
echo "  2. sudo cp mia-gpu-miner.service /etc/systemd/system/"
echo "  3. sudo systemctl daemon-reload"
echo "  4. sudo systemctl enable mia-gpu-miner"
echo "  5. sudo systemctl start mia-gpu-miner"
echo ""
echo "To check logs:"
echo "  - Direct run: tail -f /tmp/mia_miner.log"
echo "  - Systemd: sudo journalctl -u mia-gpu-miner -f"