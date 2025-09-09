#!/usr/bin/env python3
"""Monitor MIA GPU Miner health and logs"""
import time
import sys
import subprocess
from datetime import datetime
import requests

def check_bore_process():
    """Check if bore is running"""
    result = subprocess.run(['pgrep', '-f', 'bore'], capture_output=True, text=True)
    if result.stdout.strip():
        return True, f"PID: {result.stdout.strip()}"
    return False, "Not running"

def check_flask_health():
    """Check Flask server health"""
    try:
        response = requests.get("http://localhost:5000/health", timeout=2)
        if response.status_code == 200:
            return True, "Healthy"
        return False, f"Status: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused"
    except Exception as e:
        return False, str(e)

def check_vllm_health():
    """Check vLLM service"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            return True, "Healthy"
        return False, f"Status: {response.status_code}"
    except:
        return False, "Not accessible"

def tail_logs(lines=20):
    """Get last lines from miner log"""
    try:
        with open('/tmp/mia_miner.log', 'r') as f:
            all_lines = f.readlines()
            return all_lines[-lines:]
    except FileNotFoundError:
        return ["Log file not found"]
    except Exception as e:
        return [f"Error reading log: {e}"]

def monitor_loop():
    """Main monitoring loop"""
    print("🔍 MIA GPU Miner Monitor")
    print("=" * 60)
    
    while True:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
        
        # Check services
        bore_status, bore_info = check_bore_process()
        flask_status, flask_info = check_flask_health()
        vllm_status, vllm_info = check_vllm_health()
        
        print(f"Bore tunnel:  {'✅' if bore_status else '❌'} {bore_info}")
        print(f"Flask server: {'✅' if flask_status else '❌'} {flask_info}")
        print(f"vLLM service: {'✅' if vllm_status else '❌'} {vllm_info}")
        
        # Show recent logs if any errors
        if not all([bore_status, flask_status]):
            print("\nRecent logs:")
            logs = tail_logs(10)
            for line in logs:
                print(f"  {line.rstrip()}")
        
        print("-" * 60)
        
        try:
            time.sleep(30)  # Check every 30 seconds
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--logs':
        # Just show logs and exit
        print("Recent miner logs:")
        for line in tail_logs(50):
            print(line.rstrip())
    else:
        monitor_loop()