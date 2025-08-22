#!/usr/bin/env python3
"""
Script to set up a legal/visa consulting business in the system
Example: Bali Business Consulting
"""
import json
from datetime import datetime
from sqlalchemy import text
from database import SessionLocal
from services.legal_visa_data_loader import LEGAL_VISA_SERVICES, get_legal_visa_metadata

def setup_legal_business():
    """Set up a legal/visa consulting business"""
    db = SessionLocal()
    
    try:
        # 1. Create the business
        business_id = "bali-legal-consulting"
        business_data = {
            "name": "Bali Business Consulting",
            "email": "info@balibusinessconsulting.com",
            "phone": "+62 812 3456 7890",
            "address": "Jl. Sunset Road No. 88, Seminyak, Bali",
            "website": "https://balibusinessconsulting.com",
            "description": "Your trusted partner for visa and legal services in Indonesia. 13+ years of experience."
        }
        
        # Check if business exists
        check_query = text("SELECT 1 FROM businesses WHERE business_id = :id")
        exists = db.execute(check_query, {"id": business_id}).fetchone()
        
        if not exists:
            # Use the migration-compatible table name
            insert_business = text("""
                INSERT INTO businesses (
                    business_id, password, role, data, 
                    business_type, metadata, rag_mode
                ) VALUES (
                    :id, :password, :role, :data::jsonb, 
                    :type, :metadata::jsonb, :rag_mode
                )
            """)
            
            db.execute(insert_business, {
                "id": business_id,
                "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGH9pyp2HJa",  # bcrypt hash of 'password123'
                "role": "owner",
                "data": json.dumps(business_data),
                "type": "legal_visa",
                "metadata": json.dumps(get_legal_visa_metadata()),
                "rag_mode": "memory_universal"
            })
            print(f"✅ Created business: {business_id}")
        else:
            print(f"ℹ️  Business already exists: {business_id}")
        
        # 2. Add all services as products
        
        # Clear existing products for this business
        delete_query = text("DELETE FROM products WHERE business_id = :id")
        db.execute(delete_query, {"id": business_id})
        
        # Insert all services
        insert_product = text("""
            INSERT INTO products (
                id, business_id, name, description, price, 
                category, product_type, duration, requirements, 
                features, tags, available
            ) VALUES (
                :id, :business_id, :name, :description, :price,
                :category, :product_type, :duration, :requirements::jsonb,
                :features::jsonb, :tags::jsonb, true
            )
        """)
        
        total_products = 0
        
        # Add visa services
        for service in LEGAL_VISA_SERVICES["visa_services"]:
            db.execute(insert_product, {
                "id": f"{business_id}_{service['id']}",
                "business_id": business_id,
                "name": service["name"],
                "description": service["description"],
                "price": service["price"],
                "category": service["category"],
                "product_type": service["product_type"],
                "duration": service.get("duration"),
                "requirements": json.dumps(service.get("requirements", {})),
                "features": json.dumps(service.get("features", [])),
                "tags": json.dumps(service.get("tags", []))
            })
            total_products += 1
        
        # Add legal services
        for service in LEGAL_VISA_SERVICES["legal_services"]:
            db.execute(insert_product, {
                "id": f"{business_id}_{service['id']}",
                "business_id": business_id,
                "name": service["name"],
                "description": service["description"],
                "price": service["price"],
                "category": service["category"],
                "product_type": service["product_type"],
                "duration": service.get("duration"),
                "requirements": json.dumps(service.get("requirements", {})),
                "features": json.dumps(service.get("features", [])),
                "tags": json.dumps(service.get("tags", []))
            })
            total_products += 1
        
        # Add consultation services
        for service in LEGAL_VISA_SERVICES["consultation_services"]:
            db.execute(insert_product, {
                "id": f"{business_id}_{service['id']}",
                "business_id": business_id,
                "name": service["name"],
                "description": service["description"],
                "price": service["price"],
                "category": service["category"],
                "product_type": service["product_type"],
                "duration": service.get("duration"),
                "requirements": json.dumps(service.get("requirements", {})),
                "features": json.dumps(service.get("features", [])),
                "tags": json.dumps(service.get("tags", []))
            })
            total_products += 1
        
        print(f"✅ Added {total_products} services")
        
        # 3. Generate embeddings for all services
        try:
            from services.embedding_service_universal import universal_embedding_service
            universal_embedding_service.update_product_embeddings(db, business_id, "legal_visa")
            print("✅ Generated embeddings for all services")
        except Exception as e:
            print(f"⚠️  Could not generate embeddings: {e}")
        
        # Commit all changes
        db.commit()
        
        print("\n🎉 Legal/Visa business setup complete!")
        print(f"Business ID: {business_id}")
        print(f"Login: {business_id}")
        print(f"Password: password123")
        print(f"Services: {total_products}")
        print("\nYou can now:")
        print("1. Login to the admin panel")
        print("2. Test the chat with visa/legal queries")
        print("3. Connect WhatsApp for customer support")
        
    except Exception as e:
        print(f"❌ Error setting up business: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    setup_legal_business()