"""
Direct database fix for business_type column
"""
import psycopg2
from psycopg2 import sql

DATABASE_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

def fix_business_type_column():
    conn = None
    cur = None
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # First, check what tables exist
        print("\nChecking database structure...")
        cur.execute("""
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%restaurant%'
            ORDER BY table_name
        """)
        
        tables = cur.fetchall()
        print(f"\nFound {len(tables)} restaurant-related objects:")
        for table_name, table_type in tables:
            print(f"  - {table_name} ({table_type})")
        
        # Check ALL tables to find where restaurant data is stored
        print("\nChecking ALL tables in database...")
        cur.execute("""
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        all_tables = cur.fetchall()
        print(f"\nAll base tables:")
        for table_name, table_type in all_tables:
            print(f"  - {table_name}")
        
        # Get the view definition to find the base table
        if any(t[1] == 'VIEW' for t in tables if t[0] == 'restaurants'):
            print("\n'restaurants' is a VIEW. Getting definition...")
            cur.execute("""
                SELECT definition 
                FROM pg_views 
                WHERE viewname = 'restaurants'
            """)
            view_def = cur.fetchone()
            if view_def:
                print(f"\nView definition:\n{view_def[0]}")
        
        # Find the actual base table
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND (table_name LIKE '%restaurant%' OR table_name LIKE '%business%' OR table_name = 'users' OR table_name = 'accounts')
        """)
        
        base_tables = cur.fetchall()
        
        if not base_tables:
            print("\nERROR: No base restaurant table found!")
            return
        
        # For each base table, check and add business_type column
        for (table_name,) in base_tables:
            print(f"\nChecking table: {table_name}")
            
            # Check if column exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s 
                AND column_name = 'business_type'
            """, (table_name,))
            
            if cur.fetchone():
                print(f"  - business_type column already exists in {table_name}")
            else:
                print(f"  - Adding business_type column to {table_name}...")
                try:
                    cur.execute(sql.SQL("""
                        ALTER TABLE {} 
                        ADD COLUMN business_type VARCHAR DEFAULT 'restaurant'
                    """).format(sql.Identifier(table_name)))
                    conn.commit()
                    print(f"  ✅ Successfully added business_type column to {table_name}")
                except Exception as e:
                    conn.rollback()
                    print(f"  ❌ Error adding column: {e}")
        
        # If restaurants is a view, we might need to recreate it
        cur.execute("""
            SELECT viewname, definition 
            FROM pg_views 
            WHERE schemaname = 'public' 
            AND viewname = 'restaurants'
        """)
        
        view_result = cur.fetchone()
        if view_result:
            view_name, view_def = view_result
            print(f"\n⚠️  Note: 'restaurants' is a VIEW, not a table")
            print("The view might need to be recreated to include business_type column")
            print(f"View definition: {view_def[:200]}...")
        
        print("\n✅ Database fix completed!")
        
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
    fix_business_type_column()