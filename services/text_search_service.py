"""
Text-based search service for when embeddings are not available
Uses SQL pattern matching for product search
"""
import logging
from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class TextSearchService:
    """Fallback text search when ML is not available"""
    
    def search_products(self, db: Session, business_id: str, query: str, 
                       limit: int = 5) -> List[Dict]:
        """Search products using text matching"""
        try:
            query_lower = query.lower()
            
            # Extract key terms from query
            search_terms = []
            
            # Visa-related terms
            visa_terms = ['visa', 'kitas', 'permit', 'immigration', 'stay']
            for term in visa_terms:
                if term in query_lower:
                    search_terms.append(term)
            
            # Work-related terms
            if any(word in query_lower for word in ['work', 'remote', 'digital nomad', 'employment']):
                search_terms.extend(['remote', 'work'])
            
            # Retirement terms
            if any(word in query_lower for word in ['retire', 'retirement', 'senior']):
                search_terms.append('retirement')
            
            # Company terms
            if any(word in query_lower for word in ['company', 'business', 'pt pma', 'incorporation']):
                search_terms.extend(['company', 'pma'])
            
            # Property terms
            if any(word in query_lower for word in ['property', 'land', 'real estate']):
                search_terms.append('property')
            
            # Build search query
            sql = text("""
                SELECT DISTINCT
                    p.id, p.name, p.description, p.price, p.category,
                    p.product_type, p.duration, p.requirements::text, 
                    p.features::text, p.tags::text,
                    -- Calculate relevance score
                    CASE 
                        WHEN LOWER(p.name) LIKE '%' || :exact_query || '%' THEN 100
                        WHEN LOWER(p.description) LIKE '%' || :exact_query || '%' THEN 80
                        ELSE 0
                    END +
                    CASE 
                        WHEN p.tags::text ILIKE '%' || :exact_query || '%' THEN 50
                        ELSE 0
                    END as relevance
                FROM products p
                WHERE p.business_id = :business_id
                AND p.available = true
                AND (
                    LOWER(p.name) LIKE '%' || :query || '%'
                    OR LOWER(p.description) LIKE '%' || :query || '%'
                    OR p.tags::text ILIKE '%' || :query || '%'
                    OR p.category ILIKE '%' || :query || '%'
                )
                ORDER BY relevance DESC, p.price ASC
                LIMIT :limit
            """)
            
            # Try with full query first
            results = db.execute(sql, {
                'business_id': business_id,
                'query': query_lower,
                'exact_query': query_lower,
                'limit': limit
            }).fetchall()
            
            # If no results, try with individual terms
            if not results and search_terms:
                for term in search_terms:
                    results = db.execute(sql, {
                        'business_id': business_id,
                        'query': term,
                        'exact_query': term,
                        'limit': limit
                    }).fetchall()
                    if results:
                        break
            
            # Convert to dict format
            products = []
            for row in results:
                product = {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'price': row[3],
                    'category': row[4],
                    'product_type': row[5],
                    'duration': row[6],
                    'similarity': row[10] / 100.0  # Convert relevance to 0-1 scale
                }
                
                # Add requirements if available
                if row[7]:
                    try:
                        import json
                        product['requirements'] = json.loads(row[7])
                    except:
                        pass
                
                # Add features if available
                if row[8]:
                    try:
                        import json
                        product['features'] = json.loads(row[8])
                    except:
                        pass
                
                products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Text search failed: {e}")
            return []

# Create singleton
text_search_service = TextSearchService()