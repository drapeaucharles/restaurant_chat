# Legal Business Setup Guide

## Overview
This guide explains how to set up the legal/visa consulting business functionality.

## Prerequisites
- PostgreSQL database with existing restaurant data
- Railway deployment or local environment
- OpenAI API key (for embeddings) or text search fallback

## Setup Steps

### 1. Deploy Updated Code
Push the latest code to Railway which includes:
- Universal business models
- Text search fallback service
- Fixed parameter names in memory service

### 2. Run Setup Script on Railway
SSH into Railway or use Railway CLI:
```bash
./run_legal_setup.sh
```

This script will:
1. Run migration to create businesses/products tables
2. Set up legal business with services
3. Generate embeddings (if OpenAI key available)

### 3. Test the Deployment

#### Check if business exists:
```bash
curl https://your-app.railway.app/debug/business/bali-legal-consulting/products
```

#### Test search functionality:
```bash
./test_legal_complete.sh https://your-app.railway.app
```

#### Test chat:
```bash
./test_legal_chat_api.sh https://your-app.railway.app
```

## Architecture

### Database Changes
- `restaurants` → `businesses` table (with views for compatibility)
- `menu_items` → `products` table (with views for compatibility)
- Added `business_type` field to support different business types

### Service Updates
- `embedding_service_universal.py` - Works with any business type
- `text_search_service.py` - Fallback when ML not available
- `rag_chat_memory_universal.py` - Universal chat with memory

### Text Search Fallback
When ML libraries are not available on Railway:
1. Embedding service automatically falls back to text search
2. Text search uses SQL pattern matching
3. Optimized for visa/legal terms like "KITAS", "retirement", etc.

## Troubleshooting

### Issue: "ML libraries not available"
**Solution**: This is expected on Railway. Text search fallback will handle queries.

### Issue: Generic responses instead of specific services
**Cause**: Parameter name mismatch or missing products
**Solution**: 
1. Check products exist: `/debug/business/bali-legal-consulting/products`
2. Test search directly: `/debug/search`
3. Ensure using business_id="bali-legal-consulting"

### Issue: "Business not found"
**Solution**: Run setup script to create the business and products

## Testing Legal Business Chat

Example queries that should return specific service information:
- "I need a Remote Worker KITAS visa" → Should mention $1500 service
- "How much does retirement visa cost?" → Should mention $1200 service
- "I want to set up a company in Bali" → Should mention PT PMA $3500
- "What services do you offer?" → Should list available services

## Environment Variables

Optional for better embeddings:
```
OPENAI_API_KEY=your-key-here
```

Without this, system uses text search which works well for most queries.