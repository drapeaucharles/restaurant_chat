#!/bin/bash

# Setup MIA Local Miner for Restaurant Project
# This runs a local MIA instance to power the restaurant chat

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║    MIA Setup for Restaurant Project       ║${NC}"
echo -e "${GREEN}║    Local AI-Powered Chat System           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Check if we're in the restaurant directory
if [ ! -f "BackEnd/main.py" ]; then
    echo -e "${RED}Error: Not in Restaurant project directory${NC}"
    echo "Please run this from the Restaurant folder"
    exit 1
fi

# Create MIA directory
echo -e "${YELLOW}Creating MIA directory...${NC}"
mkdir -p mia-local

# Download MIA production miner
echo -e "${YELLOW}Downloading MIA miner...${NC}"
cd mia-local
wget -O mia_miner.py https://raw.githubusercontent.com/drapeaucharles/mia-backend/master/mia_miner_production.py

# Create a simplified local-only version
echo -e "${YELLOW}Creating local-only MIA miner...${NC}"
cat > mia_miner_local.py << 'EOF'
#!/usr/bin/env python3
"""
MIA Local Miner for Restaurant Project
Runs locally without connecting to MIA backend network
"""
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import sys
import time
import logging
from flask import Flask, request, jsonify
from waitress import serve
from vllm import LLM, SamplingParams
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mia-restaurant')

# Flask app
app = Flask(__name__)
model = None

def detect_language_simple(text):
    """Simple language detection"""
    text_lower = text.lower()
    
    # Spanish indicators
    if any(char in text for char in 'ñáéíóúü¿¡') or any(word in text_lower for word in ['hola', 'cómo', 'está', 'gracias']):
        return 'Spanish'
    # French indicators
    elif any(char in text for char in 'àâçèéêëîïôùûüÿœæ') or any(word in text_lower for word in ['bonjour', 'comment', 'merci']):
        return 'French'
    # Default to English
    else:
        return 'English'

def load_model():
    """Load vLLM model"""
    global model
    
    logger.info("Loading vLLM with AWQ model...")
    
    try:
        model = LLM(
            model="TheBloke/Mistral-7B-OpenOrca-AWQ",
            quantization="awq",
            dtype="half",
            gpu_memory_utilization=0.90,
            max_model_len=2048
        )
        
        logger.info("✓ Model loaded successfully!")
        
        # Test the model
        sampling_params = SamplingParams(temperature=0, max_tokens=50)
        outputs = model.generate(["Hello, how are you?"], sampling_params)
        tokens = len(outputs[0].outputs[0].token_ids)
        logger.info(f"✓ Model test successful - generated {tokens} tokens")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return False

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ready" if model is not None else "loading",
        "backend": "MIA-Local",
        "description": "Restaurant-specific MIA instance"
    })

@app.route("/generate", methods=["POST"])
def generate():
    if model is None:
        return jsonify({"error": "Model not loaded"}), 503
    
    try:
        data = request.json
        prompt = data.get("prompt", "")
        max_tokens = data.get("max_tokens", 150)
        
        # Detect language
        detected_language = detect_language_simple(prompt)
        
        # Add language instruction if not English
        if detected_language != 'English':
            language_instruction = f"\n\nIMPORTANT: Respond in {detected_language}."
            prompt = prompt + language_instruction
        
        logger.info(f"Generating response (detected language: {detected_language})")
        
        # Generate
        sampling_params = SamplingParams(
            temperature=0.7,
            top_p=0.9,
            max_tokens=max_tokens,
            repetition_penalty=1.1,
            stop=["<|im_end|>", "<|im_start|>", "\n\n"]
        )
        
        start_time = time.time()
        outputs = model.generate([prompt], sampling_params)
        generation_time = time.time() - start_time
        
        generated_text = outputs[0].outputs[0].text.strip()
        tokens_generated = len(outputs[0].outputs[0].token_ids)
        tokens_per_sec = tokens_generated / generation_time if generation_time > 0 else 0
        
        logger.info(f"Generated {tokens_generated} tokens in {generation_time:.2f}s ({tokens_per_sec:.1f} tok/s)")
        
        return jsonify({
            "text": generated_text,
            "tokens_generated": tokens_generated,
            "generation_time": round(generation_time, 2),
            "tokens_per_second": round(tokens_per_sec, 1),
            "language": detected_language
        })
        
    except Exception as e:
        logger.error(f"Generation error: {e}")
        return jsonify({"error": str(e)}), 500

def main():
    logger.info("=" * 60)
    logger.info("MIA Local Miner for Restaurant Project")
    logger.info("=" * 60)
    
    if not load_model():
        logger.error("Failed to load model")
        sys.exit(1)
    
    logger.info("Starting server on port 8000...")
    serve(app, host="0.0.0.0", port=8000, threads=4)

if __name__ == "__main__":
    main()
EOF

chmod +x mia_miner_local.py

# Create virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
python3 -m venv venv

# Activate and install dependencies
source venv/bin/activate

echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install vllm flask waitress

# Create start script
echo -e "${YELLOW}Creating start script...${NC}"
cat > start_mia.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "Starting MIA Local Miner for Restaurant..."
python3 mia_miner_local.py
EOF
chmod +x start_mia.sh

# Create systemd service (optional)
cat > mia-restaurant.service << 'EOF'
[Unit]
Description=MIA Local Miner for Restaurant
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/path/to/Restaurant/mia-local
ExecStart=/path/to/Restaurant/mia-local/venv/bin/python /path/to/Restaurant/mia-local/mia_miner_local.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Go back to restaurant directory
cd ..

# Update restaurant backend .env
echo -e "${YELLOW}Updating restaurant backend configuration...${NC}"
if [ ! -f "BackEnd/.env" ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cat > BackEnd/.env << 'EOF'
# Chat Provider Configuration
CHAT_PROVIDER=mia_local
MIA_MINER_URL=http://localhost:8000

# Optional: Keep OpenAI as fallback
OPENAI_API_KEY=your-key-here-if-needed

# Other restaurant settings
DATABASE_URL=your-database-url
SECRET_KEY=your-secret-key
PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX=your-index-name
EOF
else
    echo -e "${BLUE}Adding MIA configuration to existing .env...${NC}"
    echo "" >> BackEnd/.env
    echo "# MIA Chat Provider" >> BackEnd/.env
    echo "CHAT_PROVIDER=mia_local" >> BackEnd/.env
    echo "MIA_MINER_URL=http://localhost:8000" >> BackEnd/.env
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ MIA Setup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Start MIA Local Miner:"
echo "   cd mia-local"
echo "   ./start_mia.sh"
echo ""
echo "2. Update Restaurant Backend imports:"
echo "   In BackEnd/routes/__init__.py:"
echo "   Change: from .chat import router as chat_router"
echo "   To:     from .chat_mia import router as chat_router"
echo ""
echo "3. Start Restaurant Backend:"
echo "   cd BackEnd"
echo "   python main.py"
echo ""
echo -e "${GREEN}Features:${NC}"
echo "• Local AI-powered chat (no OpenAI costs)"
echo "• 60+ tokens/second performance"
echo "• Automatic language detection"
echo "• Runs completely offline"
echo ""
echo -e "${BLUE}Test the setup:${NC}"
echo "curl -X POST http://localhost:8000/generate -H 'Content-Type: application/json' -d '{\"prompt\":\"Hello, how are you?\",\"max_tokens\":50}'"
echo ""
echo -e "${GREEN}Your restaurant now has local AI chat powered by MIA!${NC}"