#!/bin/bash
# Update restaurant backend to use direct vLLM OpenAI API

echo "Updating restaurant backend for direct OpenAI API..."

# Update .env to point to vLLM server
cat >> .env << EOF

# Direct vLLM OpenAI API (not MIA backend)
MIA_OPENAI_URL=http://localhost:8000/v1
ENABLE_OPENAI_TOOLS=true
EOF

echo "✓ Updated .env"
echo ""
echo "Next steps:"
echo "1. Update restaurant in database to use rag_mode='openai_tools'"
echo "2. Restart restaurant backend"
echo ""
echo "The flow will be:"
echo "Restaurant Backend → vLLM OpenAI API (localhost:8000) → Direct response"
echo "(No job queue, no MIA backend needed for chat)"