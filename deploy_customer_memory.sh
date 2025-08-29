#!/bin/bash
# Deploy Customer Memory System

echo "🧠 Deploying Customer Memory System"
echo "==================================="
echo ""

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Run this from the Restaurant/BackEnd directory"
    exit 1
fi

# Pull latest changes
echo "📥 Pulling latest code..."
git pull

# Install any new dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt 2>/dev/null || true

# Run the migration
echo ""
echo "🗄️  Creating customer_profiles table..."
python3 migrations/add_customer_profiles.py

# Test the customer memory service
echo ""
echo "🧪 Testing customer memory extraction..."
python3 << EOF
from services.customer_memory_service import CustomerMemoryService

# Test extraction
tests = [
    "My name is Charles",
    "I'm vegetarian and allergic to nuts", 
    "I don't like spicy food",
    "I am Sarah and I love extra spicy dishes"
]

for test in tests:
    info = CustomerMemoryService.extract_customer_info(test)
    print(f"Message: '{test}'")
    print(f"Extracted: {info}")
    print()
EOF

echo ""
echo "✅ Customer Memory System Deployed!"
echo ""
echo "The AI will now remember:"
echo "- Customer names (My name is X)"
echo "- Dietary restrictions (I'm vegetarian/vegan/halal)"
echo "- Allergies (I'm allergic to X)"
echo "- Preferences (I like/don't like X)"
echo ""
echo "⚠️  Remember to restart your service:"
echo "   systemctl restart restaurant-backend"
echo "   OR"
echo "   pm2 restart restaurant-backend"