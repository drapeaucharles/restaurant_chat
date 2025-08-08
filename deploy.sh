#!/bin/bash

# Git deployment script
# This script commits and pushes changes to the repository

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment process...${NC}"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

# Check for changes
if [[ -z $(git status -s) ]]; then
    echo "No changes to commit"
    exit 0
fi

# Show status
echo "Current git status:"
git status -s

# Add all changes
echo -e "\n${GREEN}Adding all changes...${NC}"
git add .

# Create commit message
COMMIT_MSG="Update: $(date '+%Y-%m-%d %H:%M:%S')"
if [ ! -z "$1" ]; then
    COMMIT_MSG="$1"
fi

# Commit changes
echo -e "\n${GREEN}Committing with message: $COMMIT_MSG${NC}"
git commit -m "$COMMIT_MSG"

# Push to origin
echo -e "\n${GREEN}Pushing to remote repository...${NC}"
git push

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Deployment successful!${NC}"
else
    echo -e "\n${RED}❌ Push failed!${NC}"
    exit 1
fi