#!/usr/bin/env python3
"""Find NoneType subscript error in Restaurant backend"""

import re

# Read the file
with open('services/mia_chat_service_full_menu_with_tools_fixed.py', 'r') as f:
    content = f.read()
    
# Find all lines with subscript operations
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    # Look for patterns that might cause NoneType subscript
    if '[' in line and ']' in line:
        # Check for .get() which is safe, vs direct access
        if not '.get(' in line:
            # This could be problematic if the object is None
            print(f"Line {i}: {line.strip()}")
            
            # Check for common problematic patterns
            if 'profile[' in line or 'data[' in line or 'result[' in line:
                print(f"  ⚠️  Potential NoneType issue!")
                
print("\nChecking for None checks before subscript access...")
# Find patterns where we access something without checking None first
pattern = r'(\w+)\[.+\]'
for i, line in enumerate(lines, 1):
    matches = re.findall(pattern, line)
    for var in matches:
        # Check if this variable is checked for None in previous lines
        check_start = max(0, i - 10)
        check_lines = lines[check_start:i]
        has_none_check = any(f'{var} is None' in l or f'not {var}' in l or f'if {var}:' in l for l in check_lines)
        
        if not has_none_check and var not in ['self', 'models', 'os', 'json', 'logger']:
            print(f"Line {i}: {line.strip()}")
            print(f"  ⚠️  Variable '{var}' accessed without None check")