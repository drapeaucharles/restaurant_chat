#!/usr/bin/env python3
"""
Revert all businesses back to full_menu approach
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def revert_all_to_full_menu():
    """Revert all businesses to use full_menu mode"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Update all businesses
        result = conn.execute(text("""
            UPDATE businesses 
            SET rag_mode = 'full_menu'
        """))
        
        business_count = result.rowcount
        conn.commit()
        
        print(f"✅ Updated {business_count} businesses to use full_menu mode")
        
        # Also update restaurants table
        try:
            result = conn.execute(text("""
                UPDATE restaurants 
                SET rag_mode = 'full_menu'
            """))
            
            restaurant_count = result.rowcount
            conn.commit()
            
            if restaurant_count > 0:
                print(f"✅ Also updated {restaurant_count} restaurants in legacy table")
        except Exception as e:
            print(f"ℹ️ No legacy restaurants table: {e}")
        
        # Verify
        print("\nVerification - All businesses now using full_menu:")
        print("=" * 60)
        
        result = conn.execute(text("""
            SELECT business_id, business_type, rag_mode 
            FROM businesses 
            ORDER BY business_type, business_id
        """))
        
        for biz in result.fetchall():
            status = "✅" if biz[2] == 'full_menu' else "❌"
            print(f"{status} {biz[0]:<30} Type: {biz[1]:<15} Mode: {biz[2]}")

if __name__ == "__main__":
    print("Reverting all businesses to full_menu mode")
    print("This prepares for the new architecture: full catalog + AI queries for details")
    print()
    
    try:
        revert_all_to_full_menu()
        print("\n✅ All businesses successfully reverted to full_menu mode!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()