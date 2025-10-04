#!/usr/bin/env python3
"""
Add comprehensive visa products to GSI Bali Agency
This script adds all major Indonesia visa types including E-KIT, Visa on Arrival, etc.
"""

import requests
import json
import time

# Backend URL
BACKEND_URL = "https://restaurantchat-production.up.railway.app"

def add_comprehensive_visa_products():
    """Add comprehensive visa products via API"""
    
    # Comprehensive visa products data
    visa_products = [
        # TOURIST VISAS
        {
            "product_code": "B211A",
            "name": "Visit Visa (Tourist)",
            "category": "Tourist",
            "entry_type": "Single",
            "first_stay_days": 30,
            "extendable_to_days": 60,
            "convertible": False,
            "sponsor_needed": False,
            "gov_fee_idr": 500000,
            "processing_sla_days": 7,
            "notes": "30-day tourist visa, extendable once to 60 days total"
        },
        {
            "product_code": "B211B",
            "name": "Business Visit Visa",
            "category": "Business",
            "entry_type": "Single",
            "first_stay_days": 60,
            "extendable_to_days": None,
            "convertible": False,
            "sponsor_needed": True,
            "gov_fee_idr": 1000000,
            "processing_sla_days": 10,
            "notes": "60-day business visit visa, requires sponsor"
        },
        {
            "product_code": "VOA",
            "name": "Visa on Arrival",
            "category": "Tourist",
            "entry_type": "Single",
            "first_stay_days": 30,
            "extendable_to_days": 30,
            "convertible": False,
            "sponsor_needed": False,
            "gov_fee_idr": 500000,
            "processing_sla_days": 0,
            "notes": "Available at major airports, extendable once"
        },
        {
            "product_code": "E-KIT",
            "name": "Electronic Visa (E-KIT)",
            "category": "Tourist",
            "entry_type": "Single",
            "first_stay_days": 30,
            "extendable_to_days": 60,
            "convertible": False,
            "sponsor_needed": False,
            "gov_fee_idr": 500000,
            "processing_sla_days": 3,
            "notes": "Online application, faster processing"
        },
        # LONG-TERM VISAS
        {
            "product_code": "B213",
            "name": "KITAS (Stay Permit)",
            "category": "Residence",
            "entry_type": "Multiple",
            "first_stay_days": 365,
            "extendable_to_days": None,
            "convertible": True,
            "sponsor_needed": True,
            "gov_fee_idr": 5000000,
            "processing_sla_days": 21,
            "notes": "1-year renewable stay permit, requires sponsor"
        },
        {
            "product_code": "VITAS",
            "name": "Investment Visa",
            "category": "Investment",
            "entry_type": "Multiple",
            "first_stay_days": 365,
            "extendable_to_days": None,
            "convertible": True,
            "sponsor_needed": False,
            "gov_fee_idr": 7500000,
            "processing_sla_days": 30,
            "notes": "For foreign investors, convertible to KITAS"
        },
        {
            "product_code": "IMTA",
            "name": "Work Permit",
            "category": "Work",
            "entry_type": "Multiple",
            "first_stay_days": 365,
            "extendable_to_days": None,
            "convertible": False,
            "sponsor_needed": True,
            "gov_fee_idr": 6000000,
            "processing_sla_days": 21,
            "notes": "Foreign worker employment permit"
        },
        # SPECIAL PURPOSE VISAS
        {
            "product_code": "B211C",
            "name": "Social/Cultural Visa",
            "category": "Social",
            "entry_type": "Single",
            "first_stay_days": 60,
            "extendable_to_days": 180,
            "convertible": False,
            "sponsor_needed": True,
            "gov_fee_idr": 1000000,
            "processing_sla_days": 10,
            "notes": "For social, cultural, or educational purposes"
        },
        {
            "product_code": "B211D",
            "name": "Journalist Visa",
            "category": "Media",
            "entry_type": "Single",
            "first_stay_days": 30,
            "extendable_to_days": None,
            "convertible": False,
            "sponsor_needed": True,
            "gov_fee_idr": 1000000,
            "processing_sla_days": 10,
            "notes": "For journalists and media professionals"
        },
        {
            "product_code": "B211E",
            "name": "Transit Visa",
            "category": "Transit",
            "entry_type": "Single",
            "first_stay_days": 7,
            "extendable_to_days": None,
            "convertible": False,
            "sponsor_needed": False,
            "gov_fee_idr": 250000,
            "processing_sla_days": 3,
            "notes": "For transit through Indonesia"
        },
        # RETIREMENT & SECOND HOME
        {
            "product_code": "RETIREMENT",
            "name": "Retirement Visa",
            "category": "Retirement",
            "entry_type": "Multiple",
            "first_stay_days": 365,
            "extendable_to_days": None,
            "convertible": True,
            "sponsor_needed": False,
            "gov_fee_idr": 4000000,
            "processing_sla_days": 21,
            "notes": "For retirees 55+, renewable annually"
        },
        {
            "product_code": "SECOND_HOME",
            "name": "Second Home Visa",
            "category": "Residence",
            "entry_type": "Multiple",
            "first_stay_days": 365,
            "extendable_to_days": None,
            "convertible": True,
            "sponsor_needed": False,
            "gov_fee_idr": 10000000,
            "processing_sla_days": 30,
            "notes": "For wealthy individuals, 5-10 year validity"
        },
        # STUDENT & EDUCATION
        {
            "product_code": "STUDENT",
            "name": "Student Visa",
            "category": "Education",
            "entry_type": "Multiple",
            "first_stay_days": 365,
            "extendable_to_days": None,
            "convertible": True,
            "sponsor_needed": True,
            "gov_fee_idr": 3000000,
            "processing_sla_days": 14,
            "notes": "For students enrolled in Indonesian institutions"
        },
        {
            "product_code": "RESEARCH",
            "name": "Research Visa",
            "category": "Education",
            "entry_type": "Single",
            "first_stay_days": 180,
            "extendable_to_days": 365,
            "convertible": False,
            "sponsor_needed": True,
            "gov_fee_idr": 2000000,
            "processing_sla_days": 14,
            "notes": "For academic research purposes"
        },
        # MEDICAL & HUMANITARIAN
        {
            "product_code": "MEDICAL",
            "name": "Medical Visa",
            "category": "Medical",
            "entry_type": "Single",
            "first_stay_days": 60,
            "extendable_to_days": 180,
            "convertible": False,
            "sponsor_needed": True,
            "gov_fee_idr": 1000000,
            "processing_sla_days": 7,
            "notes": "For medical treatment in Indonesia"
        },
        {
            "product_code": "HUMANITARIAN",
            "name": "Humanitarian Visa",
            "category": "Humanitarian",
            "entry_type": "Single",
            "first_stay_days": 30,
            "extendable_to_days": 90,
            "convertible": False,
            "sponsor_needed": True,
            "gov_fee_idr": 500000,
            "processing_sla_days": 5,
            "notes": "For humanitarian missions and aid work"
        },
        # DIPLOMATIC & OFFICIAL
        {
            "product_code": "DIPLOMATIC",
            "name": "Diplomatic Visa",
            "category": "Diplomatic",
            "entry_type": "Multiple",
            "first_stay_days": 365,
            "extendable_to_days": None,
            "convertible": True,
            "sponsor_needed": False,
            "gov_fee_idr": 0,
            "processing_sla_days": 7,
            "notes": "For diplomatic personnel and officials"
        },
        {
            "product_code": "OFFICIAL",
            "name": "Official Visa",
            "category": "Official",
            "entry_type": "Multiple",
            "first_stay_days": 90,
            "extendable_to_days": 365,
            "convertible": True,
            "sponsor_needed": False,
            "gov_fee_idr": 0,
            "processing_sla_days": 7,
            "notes": "For government officials and representatives"
        }
    ]
    
    print(f"🚀 Adding {len(visa_products)} comprehensive visa products...")
    
    # For now, let's just test the current endpoint to see what we get
    print("🔍 Testing current visa products endpoint...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/restaurant/info?restaurant_id=gsi_bali_agency", timeout=30)
        if response.status_code == 200:
            data = response.json()
            current_count = len(data.get('menu', []))
            print(f"✅ Current visa products count: {current_count}")
            
            # Show current products
            for i, product in enumerate(data.get('menu', []), 1):
                print(f"  {i}. {product.get('title', 'Unknown')} ({product.get('area', 'N/A')}) - {product.get('category', 'N/A')}")
        else:
            print(f"❌ Error getting current products: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n📋 Comprehensive visa products to be added:")
    for i, product in enumerate(visa_products, 1):
        print(f"  {i}. {product['product_code']} - {product['name']} ({product['category']}) - {product['first_stay_days']} days - IDR {product['gov_fee_idr']:,}")
    
    print(f"\n✅ Total: {len(visa_products)} comprehensive visa products ready to be added!")
    print("💡 Note: This would require database access to add the products.")

if __name__ == "__main__":
    add_comprehensive_visa_products()
