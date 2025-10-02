#!/usr/bin/env python3
"""
Verify GSI Bali Agency Deployment Readiness
Checks all components without requiring database dependencies
"""

import os
import json
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and report status"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} - NOT FOUND")
        return False

def check_directory_exists(dirpath, description):
    """Check if a directory exists and report status"""
    if os.path.exists(dirpath) and os.path.isdir(dirpath):
        print(f"✅ {description}: {dirpath}")
        return True
    else:
        print(f"❌ {description}: {dirpath} - NOT FOUND")
        return False

def verify_visa_models():
    """Verify visa models are implemented"""
    print("\n🧪 Verifying Visa Models...")
    
    checks = [
        ("models/visa_models.py", "Visa Models"),
        ("services/visa/v1/__init__.py", "Visa Services Init"),
        ("services/visa/v1/tools.py", "Visa Tools"),
        ("services/visa/v1/flows.py", "Visa Flows"),
        ("services/visa/v1/profile_tools.py", "Profile Tools"),
        ("services/visa/v1/policy_tools.py", "Policy Tools"),
        ("services/visa/v1/catalog_tools.py", "Catalog Tools"),
        ("services/visa/v1/rules_engine.py", "Rules Engine"),
        ("services/visa/v1/application_tools.py", "Application Tools"),
        ("services/visa/v1/payment_tools.py", "Payment Tools")
    ]
    
    passed = 0
    for filepath, description in checks:
        if check_file_exists(filepath, description):
            passed += 1
    
    print(f"📊 Visa Models: {passed}/{len(checks)} files present")
    return passed == len(checks)

def verify_api_routes():
    """Verify API routes are implemented"""
    print("\n🧪 Verifying API Routes...")
    
    checks = [
        ("routes/visa.py", "Visa Routes"),
        ("services/visa_chat_service.py", "Visa Chat Service")
    ]
    
    passed = 0
    for filepath, description in checks:
        if check_file_exists(filepath, description):
            passed += 1
    
    print(f"📊 API Routes: {passed}/{len(checks)} files present")
    return passed == len(checks)

def verify_database_components():
    """Verify database components are ready"""
    print("\n🧪 Verifying Database Components...")
    
    checks = [
        ("migrations/001_add_visa_tables.sql", "Migration SQL"),
        ("migrations/run_migrations.py", "Migration Runner"),
        ("create_gsi_agency.py", "GSI Agency Creator"),
        ("seeds/visa_seed_data.py", "Visa Seed Data")
    ]
    
    passed = 0
    for filepath, description in checks:
        if check_file_exists(filepath, description):
            passed += 1
    
    print(f"📊 Database Components: {passed}/{len(checks)} files present")
    return passed == len(checks)

def verify_main_app_integration():
    """Verify main app has visa integration"""
    print("\n🧪 Verifying Main App Integration...")
    
    try:
        with open('main.py', 'r') as f:
            main_content = f.read()
        
        checks = [
            ('MIA_VISA_ENABLED' in main_content, "Feature flag import"),
            ('from routes import visa' in main_content, "Visa routes import"),
            ('app.include_router(visa.router)' in main_content, "Visa router inclusion")
        ]
        
        passed = 0
        for check, description in checks:
            if check:
                print(f"✅ {description}")
                passed += 1
            else:
                print(f"❌ {description}")
        
        print(f"📊 Main App Integration: {passed}/{len(checks)} checks passed")
        return passed == len(checks)
        
    except Exception as e:
        print(f"❌ Error checking main.py: {e}")
        return False

def verify_config_integration():
    """Verify config has visa feature flag"""
    print("\n🧪 Verifying Config Integration...")
    
    try:
        with open('config.py', 'r') as f:
            config_content = f.read()
        
        if 'MIA_VISA_ENABLED' in config_content:
            print("✅ MIA_VISA_ENABLED feature flag present in config")
            return True
        else:
            print("❌ MIA_VISA_ENABLED feature flag missing from config")
            return False
            
    except Exception as e:
        print(f"❌ Error checking config.py: {e}")
        return False

def verify_documentation():
    """Verify documentation is complete"""
    print("\n🧪 Verifying Documentation...")
    
    checks = [
        ("README_VISA.md", "Visa README"),
        ("GSI_DEPLOYMENT_GUIDE.md", "GSI Deployment Guide"),
        ("docs/VISA_AGENCY_SETUP.md", "Setup Guide"),
        ("docs/VISA_API_EXAMPLES.md", "API Examples")
    ]
    
    passed = 0
    for filepath, description in checks:
        if check_file_exists(filepath, description):
            passed += 1
    
    print(f"📊 Documentation: {passed}/{len(checks)} files present")
    return passed == len(checks)

def main():
    """Run all deployment readiness checks"""
    print("🚀 GSI BALI AGENCY - DEPLOYMENT READINESS CHECK")
    print("=" * 60)
    
    checks = [
        ("Visa Models", verify_visa_models),
        ("API Routes", verify_api_routes),
        ("Database Components", verify_database_components),
        ("Main App Integration", verify_main_app_integration),
        ("Config Integration", verify_config_integration),
        ("Documentation", verify_documentation)
    ]
    
    passed_categories = 0
    total_categories = len(checks)
    
    for category_name, check_func in checks:
        if check_func():
            passed_categories += 1
        else:
            print(f"\n❌ {category_name} verification failed")
    
    print("\n" + "=" * 60)
    print(f"📊 DEPLOYMENT READINESS: {passed_categories}/{total_categories} categories passed")
    
    if passed_categories == total_categories:
        print("\n🎉 GSI BALI AGENCY IS READY FOR DEPLOYMENT!")
        print("\n✅ All components verified and ready")
        print("\n🚀 DEPLOYMENT INSTRUCTIONS:")
        print("=" * 40)
        print("1. Ensure production environment has required dependencies:")
        print("   - SQLAlchemy")
        print("   - FastAPI") 
        print("   - PostgreSQL database")
        print("   - All requirements from requirements.txt")
        print()
        print("2. Set environment variable:")
        print("   export MIA_VISA_ENABLED=true")
        print()
        print("3. Run database migrations:")
        print("   python3 migrations/run_migrations.py")
        print()
        print("4. Create GSI Bali Agency:")
        print("   python3 create_gsi_agency.py")
        print()
        print("5. Start the application:")
        print("   python3 main.py")
        print()
        print("6. Test GSI deployment:")
        print("   curl -X POST http://localhost:8000/visa/health")
        print("   curl -X POST http://localhost:8000/visa/chat \\")
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"message": "I want to visit Bali", "client_id": "test", "restaurant_id": "gsi_bali_agency"}\'')
        print()
        print("🎯 GSI Bali Agency will be live and ready to handle visa inquiries!")
        return True
    else:
        print(f"\n⚠️ {total_categories - passed_categories} categories failed verification")
        print("Please check the failed components before deployment")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
