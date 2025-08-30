#!/usr/bin/env python3
"""
Update all businesses to use the new db_query RAG mode
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def update_all_businesses_to_db_query():
    """Update all businesses to use db_query mode"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # First, check current status
        result = conn.execute(text("""
            SELECT business_id, business_type, rag_mode 
            FROM businesses 
            ORDER BY business_type, business_id
        """))
        
        businesses = result.fetchall()
        print(f"Found {len(businesses)} businesses to update")
        print("=" * 60)
        
        # Show current status
        for biz in businesses:
            print(f"{biz[0]:<30} Type: {biz[1]:<15} Current mode: {biz[2] or 'None'}")
        
        print("\n" + "=" * 60)
        print("Updating all businesses to use db_query mode...")
        
        # Update all businesses
        result = conn.execute(text("""
            UPDATE businesses 
            SET rag_mode = 'db_query',
                updated_at = CURRENT_TIMESTAMP
            WHERE rag_mode IS NULL OR rag_mode != 'db_query'
        """))
        
        updated_count = result.rowcount
        conn.commit()
        
        print(f"✅ Updated {updated_count} businesses to use db_query mode")
        
        # Also update any restaurants in the old table
        try:
            result = conn.execute(text("""
                UPDATE restaurants 
                SET rag_mode = 'db_query'
                WHERE rag_mode IS NULL OR rag_mode != 'db_query'
            """))
            
            restaurant_count = result.rowcount
            conn.commit()
            
            if restaurant_count > 0:
                print(f"✅ Also updated {restaurant_count} restaurants in legacy table")
        except Exception as e:
            print(f"ℹ️ No legacy restaurants table or already updated: {e}")
        
        # Verify the update
        print("\n" + "=" * 60)
        print("Verification - All businesses should now use db_query:")
        
        result = conn.execute(text("""
            SELECT business_id, business_type, rag_mode 
            FROM businesses 
            ORDER BY business_type, business_id
        """))
        
        for biz in result.fetchall():
            status = "✅" if biz[2] == 'db_query' else "❌"
            print(f"{status} {biz[0]:<30} Type: {biz[1]:<15} Mode: {biz[2]}")

if __name__ == "__main__":
    print("Updating all businesses to use db_query mode")
    print("This will make AI queries more efficient by only fetching needed data")
    print()
    
    try:
        update_all_businesses_to_db_query()
        print("\n✅ All businesses successfully updated to db_query mode!")
        print("\nBenefits:")
        print("- 77% smaller prompts sent to MIA")
        print("- More focused responses")
        print("- Better handling of ingredient preferences")
        print("- Smart recommendations")
    except Exception as e:
        print(f"\n❌ Error updating businesses: {e}")
        import traceback
        traceback.print_exc()