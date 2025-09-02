#!/usr/bin/env python3
"""
Run customer tests in smaller batches to avoid timeouts
"""

import subprocess
import time
import json
import os
import glob

def check_progress():
    """Check how many customers have been tested"""
    files = glob.glob("/tmp/customer_*.json")
    tested = set()
    for f in files:
        try:
            with open(f, 'r') as file:
                data = json.load(file)
                tested.add(data['customer']['name'])
        except:
            pass
    return len(tested), tested

def run_batch(batch_size=5):
    """Run a batch of tests"""
    print(f"Running batch of {batch_size} customers...")
    
    # The comprehensive test will automatically skip completed ones
    process = subprocess.Popen(
        ['python3', 'comprehensive_customer_test.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Monitor for completion of batch_size new customers
    start_count, _ = check_progress()
    start_time = time.time()
    
    while True:
        current_count, _ = check_progress()
        new_customers = current_count - start_count
        
        if new_customers >= batch_size:
            print(f"Completed {new_customers} new customers, stopping batch")
            process.terminate()
            break
            
        # Check if process is still running
        if process.poll() is not None:
            print("Process completed naturally")
            break
            
        # Timeout after 5 minutes per batch
        if time.time() - start_time > 300:
            print("Batch timeout reached")
            process.terminate()
            break
            
        time.sleep(5)
    
    # Wait for process to fully terminate
    process.wait()
    return current_count

def main():
    print("🚀 Running customer tests in batches")
    
    total_customers = 41
    batch_size = 5
    
    while True:
        count, tested = check_progress()
        print(f"\n📊 Progress: {count}/{total_customers} customers completed")
        
        if count >= total_customers:
            print("✅ All customers tested!")
            break
            
        # Run next batch
        new_count = run_batch(batch_size)
        
        if new_count == count:
            print("⚠️  No progress made in last batch, waiting 30s...")
            time.sleep(30)
    
    # Run the final report generation
    print("\n📈 Generating final report...")
    subprocess.run(['python3', 'comprehensive_customer_test.py'])

if __name__ == "__main__":
    main()