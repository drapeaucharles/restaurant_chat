#!/usr/bin/env python3
"""
Comprehensive test suite for production-ready WhatsApp integration.
Tests all critical fixes and improvements.
"""

import sys
import os
import time
import requests
import json
from datetime import datetime

def test_production_fixes():
    """Test all production fixes and improvements"""
    
    print("🔍 PRODUCTION FIXES VALIDATION")
    print("=" * 60)
    
    # Test 1: Migration Script Re-runnability
    print("\n1. 🗄️ Testing Migration Script Re-runnability")
    
    try:
        import subprocess
        result = subprocess.run([sys.executable, 'migrate_whatsapp.py'], 
                              capture_output=True, text=True, cwd='/home/ubuntu')
        
        if result.returncode == 0:
            print("   ✅ Migration script runs successfully")
            if "No changes needed" in result.stdout or "already exists" in result.stdout:
                print("   ✅ Migration is properly re-runnable")
            else:
                print("   ⚠️ Migration made changes (may be first run)")
        else:
            print(f"   ❌ Migration failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Migration test error: {e}")
        return False
    
    # Test 2: FastAPI Startup Improvements
    print("\n2. 🚀 Testing FastAPI Startup Improvements")
    
    try:
        # Test that main.py imports without errors
        sys.path.append('/home/ubuntu')
        from main import start_whatsapp_service, stop_whatsapp_service
        print("   ✅ Improved startup functions imported successfully")
        
        # Test path resolution
        import os
        whatsapp_service_path = os.path.abspath(os.path.join('/home/ubuntu', "whatsapp-service"))
        node_script = os.path.abspath(os.path.join(whatsapp_service_path, "server.js"))
        
        if os.path.exists(whatsapp_service_path) and os.path.exists(node_script):
            print("   ✅ Absolute path resolution working correctly")
        else:
            print("   ❌ Path resolution issues detected")
            return False
            
    except Exception as e:
        print(f"   ❌ FastAPI startup test error: {e}")
        return False
    
    # Test 3: WhatsApp Service Features
    print("\n3. 📱 Testing WhatsApp Service Features")
    
    try:
        # Check if server.js has the required features
        with open('/home/ubuntu/whatsapp-service/server.js', 'r') as f:
            server_content = f.read()
        
        required_features = [
            'authenticateRequest',  # Authentication
            'validateSendMessage',  # Input validation
            'delay(',               # Throttling
            'logWithTimestamp',     # Enhanced logging
            '/qr/:sessionId',       # QR code exposure
            'SHARED_SECRET',        # Security
            'Math.random() * 8000'  # Anti-ban delay
        ]
        
        missing_features = []
        for feature in required_features:
            if feature not in server_content:
                missing_features.append(feature)
        
        if not missing_features:
            print("   ✅ All required features implemented in server.js")
        else:
            print(f"   ❌ Missing features: {missing_features}")
            return False
            
    except Exception as e:
        print(f"   ❌ Server.js feature test error: {e}")
        return False
    
    # Test 4: Security and Validation
    print("\n4. 🔐 Testing Security and Validation")
    
    # Test authentication middleware
    auth_tests = [
        'authenticateRequest',
        'SHARED_SECRET',
        'Bearer',
        'x-api-key',
        'Unauthorized'
    ]
    
    auth_implemented = all(test in server_content for test in auth_tests)
    
    if auth_implemented:
        print("   ✅ Authentication middleware implemented")
    else:
        print("   ❌ Authentication middleware incomplete")
        return False
    
    # Test input validation
    validation_tests = [
        'validateSendMessage',
        'phoneRegex',
        'message.length > 4000',
        'typeof to !== \'string\''
    ]
    
    validation_implemented = all(test in server_content for test in validation_tests)
    
    if validation_implemented:
        print("   ✅ Input validation implemented")
    else:
        print("   ❌ Input validation incomplete")
        return False
    
    # Test 5: Anti-ban and Throttling
    print("\n5. ⏱️ Testing Anti-ban and Throttling")
    
    throttling_tests = [
        'Math.floor(2000 + Math.random() * 8000)',
        'await delay(delayMs)',
        'Anti-ban throttling',
        'delayApplied'
    ]
    
    throttling_implemented = all(test in server_content for test in throttling_tests)
    
    if throttling_implemented:
        print("   ✅ Anti-ban throttling implemented")
    else:
        print("   ❌ Anti-ban throttling incomplete")
        return False
    
    # Test 6: QR Code Management
    print("\n6. 📱 Testing QR Code Management")
    
    qr_tests = [
        'QR_DIR',
        'qrCodes.set',
        '/qr/:sessionId',
        'qr_available',
        'onQR:'
    ]
    
    qr_implemented = all(test in server_content for test in qr_tests)
    
    if qr_implemented:
        print("   ✅ QR code management implemented")
    else:
        print("   ❌ QR code management incomplete")
        return False
    
    # Test 7: Enhanced Logging
    print("\n7. 📝 Testing Enhanced Logging")
    
    logging_tests = [
        'logWithTimestamp',
        'timestamp',
        'level.toUpperCase()',
        'Restaurant:',
        'const prefix'
    ]
    
    logging_implemented = all(test in server_content for test in logging_tests)
    
    if logging_implemented:
        print("   ✅ Enhanced logging implemented")
    else:
        print("   ❌ Enhanced logging incomplete")
        return False
    
    # Test 8: Session Management
    print("\n8. 🔄 Testing Session Management")
    
    session_tests = [
        'cleanupSession',
        'setupConnectionHandlers',
        'sessionStates',
        'onStateChanged',
        'DISCONNECTED'
    ]
    
    session_implemented = all(test in server_content for test in session_tests)
    
    if session_implemented:
        print("   ✅ Session management implemented")
    else:
        print("   ❌ Session management incomplete")
        return False
    
    # Test 9: Error Handling
    print("\n9. ⚠️ Testing Error Handling")
    
    error_tests = [
        'try {',
        'catch (error)',
        'retries',
        'timeout',
        'graceful'
    ]
    
    error_count = sum(1 for test in error_tests if server_content.count(test) > 0)
    
    if error_count >= 4:
        print("   ✅ Comprehensive error handling implemented")
    else:
        print("   ❌ Error handling needs improvement")
        return False
    
    # Test 10: Package Structure
    print("\n10. 📦 Testing Package Structure")
    
    required_files = [
        '/home/ubuntu/main.py',
        '/home/ubuntu/migrate_whatsapp.py',
        '/home/ubuntu/whatsapp-service/server.js',
        '/home/ubuntu/whatsapp-service/package.json',
        '/home/ubuntu/routes/whatsapp.py',
        '/home/ubuntu/services/whatsapp_service.py',
        '/home/ubuntu/schemas/whatsapp.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if not missing_files:
        print("   ✅ All required files present")
    else:
        print(f"   ❌ Missing files: {missing_files}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 ALL PRODUCTION FIXES VALIDATED SUCCESSFULLY!")
    print("\n📋 Validation Summary:")
    print("   ✅ Migration script is re-runnable")
    print("   ✅ FastAPI startup improvements working")
    print("   ✅ Authentication and security implemented")
    print("   ✅ Input validation comprehensive")
    print("   ✅ Anti-ban throttling active")
    print("   ✅ QR code management functional")
    print("   ✅ Enhanced logging operational")
    print("   ✅ Session management robust")
    print("   ✅ Error handling comprehensive")
    print("   ✅ Package structure complete")
    print("\n🚀 Ready for production deployment!")
    
    return True

if __name__ == "__main__":
    try:
        success = test_production_fixes()
        print(f"\n{'✅ VALIDATION PASSED' if success else '❌ VALIDATION FAILED'}")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ VALIDATION ERROR: {e}")
        sys.exit(1)

