#!/usr/bin/env python3
"""
Update all restaurants to use optimized_with_memory RAG mode
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
import models

def update_restaurants():
    db = SessionLocal()
    try:
        # Update all restaurants to use optimized_with_memory
        result = db.query(models.Restaurant).update({'rag_mode': 'optimized_with_memory'})
        db.commit()
        print(f'✅ Updated {result} restaurants to use optimized_with_memory mode')
        
        # Verify by showing a few examples
        print("\nVerification - Sample restaurants:")
        sample = db.query(models.Restaurant).limit(5).all()
        for r in sample:
            name = r.data.get('name', 'Unknown') if r.data else 'Unknown'
            print(f'  - {name} (ID: {r.restaurant_id}): rag_mode = {r.rag_mode}')
            
        # Count by mode
        print("\nRAG mode distribution:")
        from sqlalchemy import func
        mode_counts = db.query(
            models.Restaurant.rag_mode, 
            func.count(models.Restaurant.restaurant_id)
        ).group_by(models.Restaurant.rag_mode).all()
        
        for mode, count in mode_counts:
            print(f'  - {mode}: {count} restaurants')
            
    except Exception as e:
        print(f'❌ Error: {e}')
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_restaurants()