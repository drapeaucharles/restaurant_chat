"""
Context enrichment service to improve AI responses without restrictions
"""
from typing import Dict, List, Optional
from datetime import datetime
import re

class ContextEnrichmentService:
    """Enriches context with helpful information without being restrictive"""
    
    def enrich_menu_context(self, menu_items: List[Dict], query: str) -> str:
        """Add helpful context about menu items"""
        context_parts = []
        
        # Group items by category for better understanding
        categories = {}
        for item in menu_items:
            cat = item.get('category', 'Other')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        # Add category summaries
        context_parts.append("Menu Overview:")
        for cat, items in categories.items():
            context_parts.append(f"- {cat}: {len(items)} options available")
        
        # Add popular combinations hint
        if "pasta" in query.lower() and "wine" in query.lower():
            context_parts.append("\nHelpful tip: When discussing pairings, consider the sauce type")
        
        # Add dietary options summary
        veg_count = sum(1 for item in menu_items if item.get('vegetarian'))
        if veg_count > 0:
            context_parts.append(f"\nDietary info: {veg_count} vegetarian options available")
        
        return "\n".join(context_parts)
    
    def add_conversational_hints(self, query_type: str, language: str) -> str:
        """Add natural conversation hints based on query type"""
        hints = {
            "menu_query": {
                "en": "Feel free to ask about ingredients, preparation methods, or recommendations",
                "es": "Puedes preguntar sobre ingredientes, métodos de preparación o recomendaciones",
                "fr": "N'hésitez pas à demander des informations sur les ingrédients ou des recommandations"
            },
            "recommendation": {
                "en": "Consider the customer's preferences and dietary needs when suggesting",
                "es": "Considera las preferencias y necesidades dietéticas del cliente",
                "fr": "Tenez compte des préférences et des besoins alimentaires du client"
            },
            "greeting": {
                "en": "Be warm and welcoming, mention any specials if relevant",
                "es": "Sé cálido y acogedor, menciona especiales si es relevante",
                "fr": "Soyez chaleureux et accueillant, mentionnez les spéciaux si pertinent"
            }
        }
        
        return hints.get(query_type, {}).get(language, "")
    
    def add_time_context(self) -> str:
        """Add time-based context for more natural responses"""
        hour = datetime.now().hour
        
        if 6 <= hour < 12:
            return "Morning context: Breakfast/brunch items might be more relevant"
        elif 12 <= hour < 17:
            return "Lunch time: Focus on lunch specials and quick options"
        elif 17 <= hour < 22:
            return "Dinner time: Full menu and wine pairings are appropriate"
        else:
            return "Late hours: Check if kitchen is still open"
    
    def extract_preferences(self, conversation_history: List[str]) -> Dict:
        """Extract implicit preferences from conversation"""
        preferences = {
            "spice_level": None,
            "dietary": [],
            "allergies": [],
            "budget": None
        }
        
        history_text = " ".join(conversation_history).lower()
        
        # Detect spice preference
        if "not spicy" in history_text or "mild" in history_text:
            preferences["spice_level"] = "mild"
        elif "very spicy" in history_text or "extra hot" in history_text:
            preferences["spice_level"] = "hot"
        
        # Detect dietary preferences
        if "vegetarian" in history_text:
            preferences["dietary"].append("vegetarian")
        if "vegan" in history_text:
            preferences["dietary"].append("vegan")
        
        # Detect budget consciousness
        if "budget" in history_text or "cheap" in history_text or "affordable" in history_text:
            preferences["budget"] = "conscious"
        elif "special occasion" in history_text or "celebrate" in history_text:
            preferences["budget"] = "flexible"
        
        return preferences
    
    def generate_smart_examples(self, query_type: str, menu_items: List[Dict]) -> str:
        """Generate relevant examples to guide the AI"""
        examples = []
        
        if query_type == "menu_query" and menu_items:
            # Pick 2-3 diverse items as examples
            if len(menu_items) >= 3:
                examples.append("Example responses for similar queries:")
                examples.append(f"- 'Our {menu_items[0]['title']} is {menu_items[0].get('description', 'a customer favorite')}'")
                examples.append(f"- 'You might enjoy the {menu_items[1]['title']}, which features {menu_items[1].get('ingredients', ['fresh ingredients'])[0]}'")
        
        return "\n".join(examples)

# Singleton instance
context_enrichment = ContextEnrichmentService()