"""
Confidence scoring system to help AI gauge response quality
"""
from typing import Dict, List, Tuple
import re

class ConfidenceScorer:
    """Scores AI confidence in responses to improve quality"""
    
    def score_menu_match(self, query: str, matched_items: List[Dict]) -> float:
        """Score how well menu items match the query"""
        if not matched_items:
            return 0.0
        
        query_lower = query.lower()
        total_score = 0.0
        
        for item in matched_items:
            score = 0.0
            item_name = item.get('title', '').lower()
            
            # Exact name match
            if item_name in query_lower or query_lower in item_name:
                score += 0.5
            
            # Category match
            if item.get('category', '').lower() in query_lower:
                score += 0.3
            
            # Ingredient match
            ingredients = item.get('ingredients', [])
            matching_ingredients = sum(1 for ing in ingredients if ing.lower() in query_lower)
            if matching_ingredients > 0:
                score += 0.2 * min(matching_ingredients / len(ingredients), 1.0)
            
            total_score += score
        
        return min(total_score / len(matched_items), 1.0)
    
    def analyze_response_confidence(self, response: str, context: Dict) -> Dict:
        """Analyze response and provide confidence metrics"""
        metrics = {
            "overall_confidence": 0.0,
            "factual_accuracy": 0.0,
            "completeness": 0.0,
            "suggestions": []
        }
        
        # Check for uncertainty markers
        uncertainty_phrases = [
            "might be", "possibly", "perhaps", "i think", "maybe",
            "not sure", "could be", "approximately"
        ]
        uncertainty_count = sum(1 for phrase in uncertainty_phrases if phrase in response.lower())
        
        # Check for specific menu items mentioned
        menu_items = context.get('menu_items', [])
        items_mentioned = sum(1 for item in menu_items if item.get('title', '').lower() in response.lower())
        
        # Calculate confidence scores
        if items_mentioned > 0:
            metrics["factual_accuracy"] = min(items_mentioned / max(len(menu_items), 1), 1.0)
        
        metrics["completeness"] = 1.0 - (uncertainty_count * 0.2)
        metrics["overall_confidence"] = (metrics["factual_accuracy"] + metrics["completeness"]) / 2
        
        # Add suggestions based on confidence
        if metrics["overall_confidence"] < 0.5:
            metrics["suggestions"].append("Consider asking clarifying questions")
        if metrics["factual_accuracy"] < 0.3:
            metrics["suggestions"].append("Focus on specific menu items you're certain about")
        
        return metrics
    
    def suggest_improvements(self, query: str, response: str, confidence: float) -> List[str]:
        """Suggest improvements based on confidence level"""
        suggestions = []
        
        if confidence < 0.7:
            # Low confidence suggestions
            if "?" not in response:
                suggestions.append("Consider asking a clarifying question")
            
            if len(response) < 50:
                suggestions.append("Provide more detailed information")
            
            # Check if response directly addresses the query
            query_keywords = set(query.lower().split())
            response_keywords = set(response.lower().split())
            overlap = len(query_keywords & response_keywords) / len(query_keywords)
            
            if overlap < 0.3:
                suggestions.append("Ensure response directly addresses the customer's question")
        
        return suggestions
    
    def adaptive_temperature(self, query_type: str, confidence: float) -> float:
        """Suggest temperature based on confidence and query type"""
        base_temps = {
            "greeting": 0.7,      # More creative for greetings
            "menu_query": 0.3,    # More factual for menu queries
            "recommendation": 0.5, # Balanced for recommendations
            "specific_item": 0.2, # Very factual for specific items
            "other": 0.5
        }
        
        base_temp = base_temps.get(query_type, 0.5)
        
        # Adjust based on confidence
        if confidence < 0.5:
            # Low confidence: be more conservative
            return max(base_temp - 0.2, 0.1)
        elif confidence > 0.8:
            # High confidence: can be slightly more creative
            return min(base_temp + 0.1, 0.8)
        
        return base_temp

# Singleton instance
confidence_scorer = ConfidenceScorer()