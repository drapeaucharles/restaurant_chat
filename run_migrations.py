#!/usr/bin/env python3
"""
Run database migrations
"""
import sys
from migrations.add_pgvector import upgrade, downgrade

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        print("Rolling back pgvector migration...")
        downgrade()
    else:
        print("Running pgvector migration...")
        upgrade()

if __name__ == "__main__":
    main()