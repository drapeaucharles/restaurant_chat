#!/usr/bin/env python3
"""Check miner info directly in database"""

import psycopg2
import json

# Connect to MIA backend database
conn = psycopg2.connect(
    "postgresql://postgres:nHCCTrMQsLxQtOLLFtTHzgUSydCndqHV@ballast.proxy.rlwy.net:56305/railway"
)
cur = conn.cursor()

print("Checking miners in database...")
cur.execute("""
    SELECT id, name, ip_address, gpu_name, last_active, auth_key
    FROM miners
    WHERE last_active > NOW() - INTERVAL '10 minutes'
    ORDER BY last_active DESC
    LIMIT 5
""")

miners = cur.fetchall()
print(f"\nFound {len(miners)} active miners:")

for miner in miners:
    print(f"\nMiner ID: {miner[0]}")
    print(f"  Name: {miner[1]}")
    print(f"  IP Address: {miner[2]}")
    print(f"  GPU: {miner[3]}")
    print(f"  Last Active: {miner[4]}")
    print(f"  Auth Key: {miner[5][:10]}...")

cur.close()
conn.close()