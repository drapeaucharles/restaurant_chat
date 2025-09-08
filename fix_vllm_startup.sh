#!/bin/bash
# Fix vLLM startup issues

echo "=== Fixing vLLM Startup ==="

# First, check vLLM version
echo "1. Checking vLLM version..."
cd /data/qwen-awq-miner
source .venv/bin/activate
python -c "import vllm; print(f'vLLM version: {vllm.__version__}')"

# Kill existing processes
echo -e "\n2. Stopping existing processes..."
pkill -f vllm
pkill -f mia_miner
pkill bore
sleep 3

# Try with different settings
echo -e "\n3. Testing vLLM with legacy engine..."

# Option 1: Force legacy engine with environment variable
export VLLM_USE_V1=0
export VLLM_USE_LEGACY=1

# Option 2: Try with minimal settings
echo "Starting vLLM with minimal settings..."
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct-AWQ \
    --quantization awq \
    --dtype half \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.85 \
    --enforce-eager \
    --host 0.0.0.0 \
    --port 8000 &

VLLM_PID=$!
echo "vLLM PID: $VLLM_PID"

# Wait and check if it started
sleep 10
if ps -p $VLLM_PID > /dev/null; then
    echo "✅ vLLM started successfully!"
    
    # Test the API
    curl -s http://localhost:8000/v1/models
    
    echo -e "\n\nTo start the miner:"
    echo "cd /data/qwen-awq-miner"
    echo "source .venv/bin/activate" 
    echo "python3 mia_miner_heartbeat.py"
else
    echo "❌ vLLM failed to start"
    echo "Checking last 50 lines of error..."
    tail -50 vllm.log
fi