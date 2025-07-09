"""
Menu Validation Logger
Tracks when AI attempts to recommend non-existent menu items
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any

class MenuValidationLogger:
    """Logger for tracking AI menu item invention attempts"""
    
    def __init__(self, log_file: str = "logs/menu_validation_errors.json"):
        self.log_file = log_file
        self.ensure_log_dir()
    
    def ensure_log_dir(self):
        """Ensure the log directory exists"""
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    def log_invalid_items(
        self,
        restaurant_id: str,
        client_id: str,
        user_message: str,
        invalid_items: List[str],
        valid_items: List[str],
        ai_response: Dict[str, Any]
    ):
        """Log when AI tries to recommend non-existent menu items"""
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "restaurant_id": restaurant_id,
            "client_id": client_id,
            "user_message": user_message,
            "invalid_items": invalid_items,
            "valid_items": valid_items,
            "ai_response_excerpt": {
                "recommended_items": ai_response.get("recommended_items", []),
                "custom_message": ai_response.get("custom_message", "")
            },
            "severity": "CRITICAL"
        }
        
        # Read existing logs
        logs = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    logs = json.load(f)
            except (json.JSONDecodeError, IOError):
                logs = []
        
        # Append new log
        logs.append(log_entry)
        
        # Keep only last 1000 entries to prevent file from growing too large
        if len(logs) > 1000:
            logs = logs[-1000:]
        
        # Write back
        try:
            with open(self.log_file, 'w') as f:
                json.dump(logs, f, indent=2)
        except IOError as e:
            print(f"Failed to write validation log: {e}")
    
    def get_recent_errors(self, restaurant_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent validation errors, optionally filtered by restaurant"""
        if not os.path.exists(self.log_file):
            return []
        
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
        
        # Filter by restaurant if specified
        if restaurant_id:
            logs = [log for log in logs if log.get("restaurant_id") == restaurant_id]
        
        # Return most recent entries
        return logs[-limit:]
    
    def get_error_statistics(self, restaurant_id: str = None) -> Dict[str, Any]:
        """Get statistics about menu validation errors"""
        logs = self.get_recent_errors(restaurant_id, limit=None)
        
        if not logs:
            return {
                "total_errors": 0,
                "unique_invalid_items": [],
                "most_common_invalid": [],
                "error_rate_last_24h": 0
            }
        
        # Collect all invalid items
        all_invalid = []
        for log in logs:
            all_invalid.extend(log.get("invalid_items", []))
        
        # Count occurrences
        item_counts = {}
        for item in all_invalid:
            item_counts[item] = item_counts.get(item, 0) + 1
        
        # Sort by frequency
        most_common = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Count errors in last 24 hours
        now = datetime.utcnow()
        errors_24h = sum(
            1 for log in logs
            if (now - datetime.fromisoformat(log["timestamp"])).total_seconds() < 86400
        )
        
        return {
            "total_errors": len(logs),
            "unique_invalid_items": list(item_counts.keys()),
            "most_common_invalid": [{"item": item, "count": count} for item, count in most_common],
            "error_rate_last_24h": errors_24h
        }

# Global logger instance
menu_validation_logger = MenuValidationLogger()