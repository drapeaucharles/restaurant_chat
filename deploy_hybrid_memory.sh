#!/bin/bash

echo "🚀 Deploying Hybrid Smart + Memory RAG Mode"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ DATABASE_URL not set. Please set it first:${NC}"
    echo "   export DATABASE_URL='your-database-url'"
    exit 1
fi

echo -e "${YELLOW}📋 Step 1: Running database migration${NC}"
echo "Adding rag_mode column and updating all restaurants..."

# Run the SQL migration
psql $DATABASE_URL < UPDATE_ALL_TO_HYBRID_MEMORY.sql

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database updated successfully!${NC}"
else
    echo -e "${RED}❌ Database update failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}📋 Step 2: Deploy to Railway${NC}"
echo "The following changes will be deployed:"
echo "- New hybrid_smart_memory RAG mode (auto-routing + conversation memory)"
echo "- Restaurant-specific AI mode selection in owner dashboard"
echo "- 5 RAG modes available for selection"
echo "- All restaurants set to hybrid_smart_memory"

echo ""
echo -e "${GREEN}✨ Deployment preparation complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Commit and push the changes:"
echo "   git add ."
echo "   git commit -m 'Add hybrid smart + memory RAG mode'"
echo "   git push"
echo ""
echo "2. Railway will automatically deploy the changes"
echo ""
echo "3. All restaurants will now have:"
echo "   - Smart cost optimization (auto-routing)"
echo "   - Full conversation memory (last 10 messages)"
echo "   - Natural follow-up questions"
echo "   - ~50% cost savings vs always enhanced"

echo ""
echo -e "${YELLOW}📊 New RAG Modes Available:${NC}"
echo "1. hybrid_smart_memory ⭐ - Auto-routing + memory (NEW DEFAULT)"
echo "2. hybrid_smart - Auto-routing, no memory"
echo "3. optimized - Fast/cheap, no memory"
echo "4. enhanced_v2 - High quality, no memory"
echo "5. enhanced_v3 - High quality + memory"

echo ""
echo -e "${GREEN}🎉 Ready to push!${NC}"