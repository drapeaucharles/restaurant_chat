#!/bin/bash

# Deploy improved chat service
echo "🚀 Deploying improved chat service..."

# Check current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "📍 Current branch: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" != "v3" ]; then
    echo "⚠️  Warning: Not on v3 branch. Current branch is $CURRENT_BRANCH"
    echo "Do you want to continue? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        echo "❌ Deployment cancelled"
        exit 1
    fi
fi

# Stage the new files
echo "📦 Staging new files..."
git add services/mia_chat_service_improved.py
git add config_improved.py
git add routes/chat_improved.py
git add test_improved_chat.py
git add deploy_improved_chat.sh

# Show what will be committed
echo "📝 Files to be committed:"
git status --porcelain | grep -E "^(A|M)" | head -20

# Commit changes
echo "💾 Committing changes..."
git commit -m "feat: Implement improved AI chat service with natural responses

- Add flexible system prompt for more natural conversations
- Implement structured context formatting for better AI understanding
- Include conversation history for context continuity
- Add dynamic temperature adjustment based on query type
- Implement response enhancement for completeness
- Create improved config with feature flags
- Add test scripts for validation
- Maintain backward compatibility with existing endpoints"

# Push to repository
echo "📤 Pushing to repository..."
git push origin v3

echo "✅ Code pushed to repository"
echo ""
echo "🔄 Railway will automatically deploy the changes"
echo ""
echo "📋 Next steps:"
echo "1. Monitor Railway deployment: https://railway.app/project/..."
echo "2. Test improved endpoint: /chat/improved"
echo "3. Run test script: python test_improved_chat.py"
echo "4. Compare responses: GET /chat/test-comparison?query=what+pasta+do+you+have"
echo ""
echo "🔧 To enable improved service globally:"
echo "   Set environment variable: USE_IMPROVED_CHAT=true"
echo "   Or update config.py to use config_improved.py"