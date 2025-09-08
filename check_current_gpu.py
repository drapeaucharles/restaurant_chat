#!/usr/bin/env python3
"""Check current GPU status"""

import requests
import psycopg2

print("1. Checking GPU metrics from API...")
response = requests.get("https://mia-backend-production.up.railway.app/metrics/gpus")
gpu_data = response.json()

print(f"   Total GPUs: {gpu_data['total_gpus']}")
print(f"   Available: {gpu_data['available_gpus']}")

for gpu in gpu_data['gpus']:
    print(f"\n   GPU ID: {gpu['id']}")
    print(f"   Name: {gpu['name']}")
    print(f"   Last heartbeat: {gpu['last_heartbeat']}")

print("\n2. Checking database directly...")
conn = psycopg2.connect(
    "postgresql://postgres:nHCCTrMQsLxQtOLLFtTHzgUSydCndqHV@ballast.proxy.rlwy.net:56305/railway"
)
cur = conn.cursor()

cur.execute("""
    SELECT id, name, ip_address, last_active
    FROM miners
    WHERE last_active > NOW() - INTERVAL '10 minutes'
    ORDER BY last_active DESC
""")

miners = cur.fetchall()
for miner in miners:
    print(f"\n   Miner {miner[0]}: {miner[1]}")
    print(f"   IP: {miner[2]}")
    print(f"   Last active: {miner[3]}")

cur.close()
conn.close()