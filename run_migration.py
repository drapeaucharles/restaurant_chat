"""
Run the business_type migration manually
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from migrations.add_business_type import add_business_type_column
import logging

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    print("Running business_type migration...")
    try:
        add_business_type_column()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {str(e)}")