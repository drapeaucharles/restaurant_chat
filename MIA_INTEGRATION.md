# MIA Integration for Restaurant Project

This guide explains how to use the MIA backend to power the restaurant chat system instead of OpenAI.

## Overview

The restaurant project can now use MIA (your custom AI backend) instead of OpenAI for chat responses. This provides:
- **Cost Savings**: No OpenAI API costs
- **Performance**: 60+ tokens/second with local GPU
- **Privacy**: All data stays on your infrastructure
- **Language Support**: Automatic language detection (English, Spanish, French, etc.)

## Architecture

```
Restaurant Frontend
       ↓
Restaurant Backend (FastAPI)
       ↓
MIA Chat Service (instead of OpenAI)
       ↓
MIA Local Miner (vLLM + Mistral-7B)
```

## Quick Setup

### 1. Run the Setup Script

From the Restaurant directory:

```bash
cd /home/charles-drapeau/Documents/Project/Restaurant
bash setup-mia-for-restaurant.sh
```

This will:
- Download and configure MIA miner
- Create a local-only version optimized for restaurant use
- Set up Python virtual environment
- Configure the restaurant backend to use MIA

### 2. Start MIA Local Miner

```bash
cd mia-local
./start_mia.sh
```

The miner will:
- Load the Mistral-7B-OpenOrca model
- Start a server on port 8000
- Be ready to handle chat requests

### 3. Update Restaurant Backend

In `BackEnd/routes/__init__.py`, change:
```python
from .chat import router as chat_router
```
To:
```python
from .chat_mia import router as chat_router
```

### 4. Configure Environment

Make sure `BackEnd/.env` has:
```env
CHAT_PROVIDER=mia_local
MIA_MINER_URL=http://localhost:8000
```

### 5. Start Restaurant Backend

```bash
cd BackEnd
python main.py
```

## Configuration Options

### Chat Providers

Set `CHAT_PROVIDER` in `.env`:

- `mia_local` - Use local MIA miner (recommended)
- `mia` - Use MIA distributed backend
- `openai` - Use OpenAI (fallback)

### Performance Tuning

```env
MIA_MAX_TOKENS=150         # Max response length
MIA_TIMEOUT=30             # Request timeout
MIA_RETRY_ATTEMPTS=2       # Retry failed requests
```

## Testing

### Test MIA Directly

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Hello, I am looking for vegetarian options","max_tokens":100}'
```

### Test Through Restaurant API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "test-restaurant",
    "client_id": "test-client",
    "message": "What vegetarian dishes do you have?"
  }'
```

### Check Current Provider

```bash
curl http://localhost:8000/chat/provider
```

## Features

### Language Detection

MIA automatically detects and responds in the user's language:
- English: "Hello, how are you?" → English response
- Spanish: "Hola, ¿cómo estás?" → Spanish response
- French: "Bonjour, comment allez-vous?" → French response

### Context Awareness

The system maintains conversation context:
- Recent chat history (60 minutes)
- Restaurant menu and information
- Customer preferences

### Caching

Common queries are cached for faster responses:
- Opening hours
- Contact information
- WiFi/parking details

## Troubleshooting

### MIA Not Starting

```bash
# Check CUDA availability
nvidia-smi

# Check Python version (needs 3.8+)
python3 --version

# Check logs
tail -f mia-local/mia.log
```

### Slow Responses

- Ensure GPU has 8GB+ VRAM
- Check GPU utilization during inference
- Reduce `max_tokens` if needed

### Language Detection Issues

The miner uses pattern matching for language detection. If issues persist:
1. Check the detected language in logs
2. Adjust detection patterns in `mia_miner_local.py`

## System Requirements

- **GPU**: NVIDIA GPU with 8GB+ VRAM
- **CUDA**: 11.8 or higher
- **Python**: 3.8+
- **Storage**: 20GB for model
- **RAM**: 16GB+ recommended

## Cost Comparison

| Provider | Cost | Speed | Privacy |
|----------|------|-------|---------|
| OpenAI GPT-4 | ~$0.03/1K tokens | 20-30 tok/s | Cloud |
| MIA Local | $0 (your GPU) | 60+ tok/s | Local |

## Advanced Configuration

### Run as System Service

```bash
# Copy and edit the service file
sudo cp mia-local/mia-restaurant.service /etc/systemd/system/
sudo systemctl enable mia-restaurant
sudo systemctl start mia-restaurant
```

### Use Multiple GPUs

Modify `gpu_memory_utilization` in `mia_miner_local.py`:
```python
model = LLM(
    model="TheBloke/Mistral-7B-OpenOrca-AWQ",
    tensor_parallel_size=2,  # Use 2 GPUs
    gpu_memory_utilization=0.85
)
```

### Custom System Prompts

Edit the system prompt in `mia_chat_service.py` to customize behavior for your restaurant.

## Monitoring

### Check MIA Status
```bash
curl http://localhost:8000/health
```

### View Logs
```bash
# MIA logs
tail -f mia-local/mia.log

# Restaurant backend logs
tail -f BackEnd/app.log
```

### Performance Metrics
The system logs tokens/second for each request to help monitor performance.

## Rollback to OpenAI

If needed, you can quickly switch back to OpenAI:

1. Update `.env`:
   ```env
   CHAT_PROVIDER=openai
   OPENAI_API_KEY=your-key-here
   ```

2. Restart the restaurant backend

The system will automatically use OpenAI instead of MIA.

## Support

For issues:
1. Check MIA miner logs
2. Verify GPU/CUDA setup
3. Ensure all dependencies are installed
4. Check restaurant backend logs

The integration is designed to be seamless - the restaurant frontend doesn't need any changes!