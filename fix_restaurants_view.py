"""
Fix restaurants view to include business_type column
"""
import psycopg2
from psycopg2 import sql

DATABASE_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

def fix_restaurants_view():
    conn = None
    cur = None
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Drop the old view
        print("Dropping old restaurants view...")
        cur.execute("DROP VIEW IF EXISTS restaurants CASCADE")
        
        # Create the new view with business_type column
        print("Creating new restaurants view with business_type...")
        cur.execute("""
            CREATE VIEW restaurants AS
            SELECT 
                business_id AS restaurant_id,
                password,
                role,
                data,
                whatsapp_number,
                whatsapp_session_id,
                restaurant_category,
                rag_mode,
                business_type
            FROM businesses
        """)
        
        conn.commit()
        print("✅ Successfully recreated restaurants view with business_type column!")
        
        # Verify the view
        print("\nVerifying new view structure...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'restaurants'
            ORDER BY ordinal_position
        """)
        
        columns = cur.fetchall()
        print("\nColumns in restaurants view:")
        for (col,) in columns:
            print(f"  - {col}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_restaurants_view()