"""
Database migration script to add WhatsApp fields to Restaurant table.
This script adds the whatsapp_number and whatsapp_session_id columns.
Re-runnable and safe for production use.
"""

import sqlite3
import os
import sys


def migrate_sqlite_database(db_path):
    """Add WhatsApp fields to existing Restaurant table in SQLite"""
    
    if not os.path.exists(db_path):
        print(f"⚠️ Database file {db_path} not found")
        return False
    
    print(f"🔍 Found SQLite database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if restaurants table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='restaurants'")
        if not cursor.fetchone():
            print(f"ℹ️ No restaurants table found in {db_path}, skipping")
            conn.close()
            return True
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(restaurants)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"📋 Existing columns: {columns}")
        
        # Track changes made
        changes_made = []
        
        # Add whatsapp_number column if it doesn't exist
        if 'whatsapp_number' not in columns:
            try:
                cursor.execute("ALTER TABLE restaurants ADD COLUMN whatsapp_number TEXT")
                changes_made.append("whatsapp_number")
                print("✅ Added whatsapp_number column")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print("ℹ️ whatsapp_number column already exists (detected via error)")
                else:
                    print(f"❌ Error adding whatsapp_number column: {e}")
                    conn.close()
                    return False
        else:
            print("ℹ️ whatsapp_number column already exists")
        
        # Add whatsapp_session_id column if it doesn't exist
        if 'whatsapp_session_id' not in columns:
            try:
                cursor.execute("ALTER TABLE restaurants ADD COLUMN whatsapp_session_id TEXT")
                changes_made.append("whatsapp_session_id")
                print("✅ Added whatsapp_session_id column")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print("ℹ️ whatsapp_session_id column already exists (detected via error)")
                else:
                    print(f"❌ Error adding whatsapp_session_id column: {e}")
                    conn.close()
                    return False
        else:
            print("ℹ️ whatsapp_session_id column already exists")
        
        # Commit changes if any were made
        if changes_made:
            conn.commit()
            print(f"💾 Committed changes: {', '.join(changes_made)}")
        else:
            print("💾 No changes needed - database already up to date")
        
        conn.close()
        print(f"✅ Database migration completed successfully for {db_path}!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ SQLite error for {db_path}: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error for {db_path}: {str(e)}")
        return False


def migrate_postgresql():
    """Provide PostgreSQL migration instructions and attempt if psycopg2 is available"""
    
    print(f"\n🐘 PostgreSQL Migration:")
    
    # Try to connect to PostgreSQL if psycopg2 is available
    try:
        import psycopg2
        from dotenv import load_dotenv
        
        load_dotenv()
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            print("ℹ️ No DATABASE_URL found in environment")
            print_postgresql_instructions()
            return False
        
        print(f"🔗 Attempting to connect to PostgreSQL...")
        
        try:
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            
            # Check if restaurants table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'restaurants'
                );
            """)
            
            if not cursor.fetchone()[0]:
                print("ℹ️ No restaurants table found in PostgreSQL database")
                conn.close()
                return True
            
            # Check existing columns
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'restaurants';
            """)
            
            columns = [row[0] for row in cursor.fetchall()]
            print(f"📋 Existing PostgreSQL columns: {columns}")
            
            changes_made = []
            
            # Add whatsapp_number column if it doesn't exist
            if 'whatsapp_number' not in columns:
                try:
                    cursor.execute("ALTER TABLE restaurants ADD COLUMN whatsapp_number VARCHAR")
                    changes_made.append("whatsapp_number")
                    print("✅ Added whatsapp_number column to PostgreSQL")
                except psycopg2.Error as e:
                    if "already exists" in str(e):
                        print("ℹ️ whatsapp_number column already exists in PostgreSQL")
                    else:
                        print(f"❌ Error adding whatsapp_number to PostgreSQL: {e}")
                        conn.rollback()
                        conn.close()
                        return False
            else:
                print("ℹ️ whatsapp_number column already exists in PostgreSQL")
            
            # Add whatsapp_session_id column if it doesn't exist
            if 'whatsapp_session_id' not in columns:
                try:
                    cursor.execute("ALTER TABLE restaurants ADD COLUMN whatsapp_session_id VARCHAR")
                    changes_made.append("whatsapp_session_id")
                    print("✅ Added whatsapp_session_id column to PostgreSQL")
                except psycopg2.Error as e:
                    if "already exists" in str(e):
                        print("ℹ️ whatsapp_session_id column already exists in PostgreSQL")
                    else:
                        print(f"❌ Error adding whatsapp_session_id to PostgreSQL: {e}")
                        conn.rollback()
                        conn.close()
                        return False
            else:
                print("ℹ️ whatsapp_session_id column already exists in PostgreSQL")
            
            # Commit changes if any were made
            if changes_made:
                conn.commit()
                print(f"💾 Committed PostgreSQL changes: {', '.join(changes_made)}")
            else:
                print("💾 No changes needed - PostgreSQL database already up to date")
            
            conn.close()
            print("✅ PostgreSQL migration completed successfully!")
            return True
            
        except psycopg2.Error as e:
            print(f"❌ PostgreSQL connection/query error: {e}")
            print_postgresql_instructions()
            return False
        except Exception as e:
            print(f"❌ Unexpected PostgreSQL error: {e}")
            print_postgresql_instructions()
            return False
            
    except ImportError:
        print("ℹ️ psycopg2 not available, providing manual instructions")
        print_postgresql_instructions()
        return False


def print_postgresql_instructions():
    """Print manual PostgreSQL migration instructions"""
    print("\n📋 Manual PostgreSQL Migration Instructions:")
    print("   Connect to your PostgreSQL database and run:")
    print("   ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS whatsapp_number VARCHAR;")
    print("   ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS whatsapp_session_id VARCHAR;")


def migrate_all_databases():
    """Migrate all found database files and PostgreSQL if available"""
    
    print("🚀 Starting WhatsApp Database Migration")
    print("=" * 50)
    
    # SQLite databases
    db_files = [
        "test_api.db",
        "test_api_message_saves.db", 
        "test_whatsapp.db"
    ]
    
    sqlite_success_count = 0
    
    print("\n📁 SQLite Database Migration:")
    for db_file in db_files:
        if migrate_sqlite_database(db_file):
            sqlite_success_count += 1
    
    # PostgreSQL migration
    postgresql_success = migrate_postgresql()
    
    # Summary
    print(f"\n📊 Migration Summary:")
    print(f"   SQLite databases processed: {len(db_files)}")
    print(f"   SQLite databases successful: {sqlite_success_count}")
    print(f"   PostgreSQL migration: {'✅ Success' if postgresql_success else '⚠️ Manual required'}")
    
    if sqlite_success_count == len(db_files) and postgresql_success:
        print("\n🎉 All database migrations completed successfully!")
        return True
    elif sqlite_success_count == len(db_files):
        print("\n✅ SQLite migrations completed. PostgreSQL may require manual migration.")
        return True
    else:
        print("\n❌ Some migrations failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    try:
        success = migrate_all_databases()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during migration: {e}")
        sys.exit(1)

