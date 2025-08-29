#!/usr/bin/env python3
"""
Cleanup script to remove all GREETING references from services
"""
import os
import re

def cleanup_file(filepath):
    """Remove GREETING references from a file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Pattern 1: if query_type == QueryType.GREETING:
    pattern1 = r'(\s*)if\s+query_type\s*==\s*QueryType\.GREETING\s*:(.*?)(?=\n\s*(?:if|elif|else|def|class|$))'
    matches = list(re.finditer(pattern1, content, re.DOTALL))
    for match in reversed(matches):  # Process in reverse to maintain positions
        indent = match.group(1)
        replacement = f'{indent}# Removed GREETING special case - let AI handle naturally\n{indent}if False:  # was query_type == QueryType.GREETING\n{indent}    pass'
        content = content[:match.start()] + replacement + content[match.end():]
        changes.append(f"Removed GREETING condition at line {content[:match.start()].count(chr(10)) + 1}")
    
    # Pattern 2: query_type != QueryType.GREETING
    pattern2 = r'query_type\s*!=\s*QueryType\.GREETING'
    content = re.sub(pattern2, 'True  # was query_type != QueryType.GREETING', content)
    if pattern2 in original_content:
        changes.append("Replaced query_type != QueryType.GREETING with True")
    
    # Pattern 3: not in [QueryType.GREETING]
    pattern3 = r'not\s+in\s+\[QueryType\.GREETING\]'
    content = re.sub(pattern3, 'True  # was not in [QueryType.GREETING]', content)
    if pattern3 in original_content:
        changes.append("Replaced not in [QueryType.GREETING] with True")
    
    # Pattern 4: QueryType.GREETING in enums/lists
    pattern4 = r'QueryType\.GREETING\s*[,:]'
    if re.search(pattern4, content):
        changes.append("WARNING: Found QueryType.GREETING in enum/list - manual fix needed")
    
    # Pattern 5: return QueryType.GREETING
    pattern5 = r'return\s+QueryType\.GREETING'
    content = re.sub(pattern5, 'return QueryType.OTHER  # was QueryType.GREETING', content)
    if pattern5 in original_content:
        changes.append("Replaced return QueryType.GREETING with QueryType.OTHER")
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True, changes
    return False, []

def main():
    """Clean up all service files"""
    services_dir = "/home/charles-drapeau/Documents/Project/MIA_project/Restaurant/BackEnd/services"
    
    # Files with GREETING references found
    files_to_clean = [
        "rag_chat_memory_fixed.py",
        "rag_chat_memory_v2.py", 
        "rag_chat_memory_v3.py",
        "rag_chat_memory_v4.py",
        "rag_chat_memory_v5.py",
        "rag_chat_memory_v6.py",
        "rag_chat_enhanced_v3_debug.py",
        "rag_chat_service.py",
        "rag_chat_enhanced_v3_lazy.py",
        "rag_chat_optimized.py",
        "mia_chat_service_enhanced.py",
        "rag_chat_memory_universal.py",
        "rag_chat_enhanced_v3_fixed.py",
        "rag_chat_enhanced.py",
        "rag_chat_memory_best.py",
        "rag_chat_enhanced_v3.py",
        "rag_chat_service_improved.py",
        "mia_chat_service_enhanced_simple.py",
        "rag_chat_optimized_with_memory.py"
    ]
    
    total_changes = 0
    for filename in files_to_clean:
        filepath = os.path.join(services_dir, filename)
        if os.path.exists(filepath):
            changed, changes = cleanup_file(filepath)
            if changed:
                print(f"\n✅ {filename}:")
                for change in changes:
                    print(f"   - {change}")
                total_changes += 1
            else:
                print(f"❌ {filename}: No changes needed")
        else:
            print(f"⚠️  {filename}: File not found")
    
    print(f"\n🎯 Total files modified: {total_changes}")
    print("\nIMPORTANT: Review the changes and test before committing!")

if __name__ == "__main__":
    main()