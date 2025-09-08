#!/usr/bin/env python3
"""Manually update bore URL in database for testing"""

import psycopg2
import sys

if len(sys.argv) != 2:
    print("Usage: python3 update_bore_url.py <new_bore_port>")
    print("Example: python3 update_bore_url.py 53103")
    sys.exit(1)

new_port = sys.argv[1]
new_url = f"bore.pub:{new_port}"

# Connect to MIA backend database
conn = psycopg2.connect(
    "postgresql://postgres:nHCCTrMQsLxQtOLLFtTHzgUSydCndqHV@ballast.proxy.rlwy.net:56305/railway"
)
cur = conn.cursor()

print(f"Updating miner bore URL to: {new_url}")

# Update the bore miner
cur.execute("""
    UPDATE miners 
    SET ip_address = %s,
        last_active = NOW()
    WHERE id = 29
""", (new_url,))

rows_updated = cur.rowcount
conn.commit()

print(f"Updated {rows_updated} miner(s)")

# Verify
cur.execute("SELECT id, name, ip_address FROM miners WHERE id = 29")
result = cur.fetchone()
if result:
    print(f"\nVerified: Miner {result[0]} ({result[1]}) now has IP: {result[2]}")

cur.close()
conn.close()

print("\nNOTE: This is a temporary fix. The real solution is:")
print("1. GPU miner restarts and gets new bore URL")
print("2. Miner sends heartbeat with public_url field")
print("3. Backend auto-updates the database")