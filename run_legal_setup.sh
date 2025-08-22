#!/bin/bash

# Run legal business setup on Railway
echo "Setting up legal business on Railway..."
echo "======================================"

# First run the migration
echo -e "\n1. Running migration..."
python3 migrate_to_universal.py

# Then setup the legal business
echo -e "\n2. Setting up legal business..."
python3 setup_legal_business.py

# Generate embeddings using OpenAI
echo -e "\n3. Generating embeddings..."
python3 update_embeddings_openai.py

echo -e "\nSetup complete!"