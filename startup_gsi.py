#!/usr/bin/env python3
"""
GSI Bali Agency Auto-Startup Script
Ensures GSI agency is created automatically when Railway starts
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_and_create_gsi():
    """Check if GSI exists, create if needed"""
    try:
        from config import MIA_VISA_ENABLED
        
        if not MIA_VISA_ENABLED:
            logger.info("MIA_VISA_ENABLED=False - skipping GSI auto-creation")
            return False
        
        logger.info("🚀 Checking GSI Bali Agency status...")
        
        # Try to import database components
        try:
            from database import SessionLocal
            from models.visa_models import Business
        except ImportError as e:
            logger.warning(f"Database components not available: {e}")
            return False
        
        # Check if GSI already exists
        try:
            db = SessionLocal()
            existing_gsi = db.query(Business).filter(
                Business.business_id == 'gsi_bali_agency'
            ).first()
            
            if existing_gsi:
                logger.info("✅ GSI Bali Agency already exists - ready to serve")
                return True
            else:
                logger.info("🔧 GSI Bali Agency not found - creating now...")
                
                # Import and run GSI creation
                from create_gsi_agency import create_gsi_agency
                result = create_gsi_agency()
                
                if result.get("status") == "success":
                    logger.info("✅ GSI Bali Agency created successfully!")
                    return True
                else:
                    logger.error(f"❌ Failed to create GSI: {result.get('error')}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Database error: {e}")
            return False
        finally:
            try:
                db.close()
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        return False


def run_migrations():
    """Run database migrations if needed"""
    try:
        from config import MIA_VISA_ENABLED
        
        if not MIA_VISA_ENABLED:
            return True
            
        logger.info("🔧 Running database migrations...")
        
        # Import and run migrations
        from migrations.run_migrations import run_all_migrations
        success = run_all_migrations()
        
        if success:
            logger.info("✅ Database migrations completed")
            return True
        else:
            logger.error("❌ Database migrations failed")
            return False
            
    except ImportError:
        logger.warning("Migration module not available - skipping")
        return True
    except Exception as e:
        logger.error(f"❌ Migration error: {e}")
        return False


def startup_gsi():
    """Main startup function for GSI"""
    logger.info("🚀 GSI BALI AGENCY - AUTO STARTUP")
    logger.info("=" * 50)
    
    try:
        # Step 1: Run migrations
        if not run_migrations():
            logger.error("❌ Migrations failed - GSI startup aborted")
            return False
        
        # Step 2: Check/create GSI
        if not check_and_create_gsi():
            logger.error("❌ GSI creation failed - startup incomplete")
            return False
        
        logger.info("🎉 GSI BALI AGENCY STARTUP COMPLETE!")
        logger.info("✅ Ready to handle visa inquiries")
        return True
        
    except Exception as e:
        logger.error(f"❌ GSI startup failed: {e}")
        return False


if __name__ == "__main__":
    success = startup_gsi()
    sys.exit(0 if success else 1)
