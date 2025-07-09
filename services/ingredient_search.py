"""
Ingredient-based search service for menu items.
This module provides functionality to search menu items based on specific ingredients,
ensuring accurate results for dietary preferences and restrictions.
"""

from typing import List, Dict, Set, Optional
from sqlalchemy.orm import Session
import models

# Common cheese types and cheese-related terms
CHEESE_TERMS = {
    'cheese', 'cheddar', 'mozzarella', 'parmesan', 'feta', 'goat cheese', 
    'ricotta', 'gorgonzola', 'brie', 'camembert', 'swiss', 'provolone',
    'gruyere', 'pecorino', 'romano', 'mascarpone', 'cream cheese',
    'blue cheese', 'cottage cheese', 'halloumi', 'manchego', 'asiago',
    'fontina', 'gouda', 'edam', 'raclette', 'taleggio', 'burrata'
}

# Common meat types and meat-related terms
MEAT_TERMS = {
    'meat', 'beef', 'chicken', 'pork', 'lamb', 'turkey', 'duck', 'veal',
    'steak', 'bacon', 'ham', 'sausage', 'prosciutto', 'salami', 'pepperoni',
    'ribeye', 'sirloin', 'tenderloin', 'filet', 'brisket', 'ribs', 'chops',
    'ground beef', 'meatball', 'burger', 'poultry', 'venison', 'rabbit',
    'quail', 'goose', 'pheasant', 'wild boar', 'chorizo', 'pancetta',
    'guanciale', 'bresaola', 'mortadella', 'coppa', 'beef broth', 'chicken broth'
}

# Common seafood types
SEAFOOD_TERMS = {
    'fish', 'seafood', 'salmon', 'tuna', 'cod', 'halibut', 'bass', 'trout',
    'tilapia', 'mahi mahi', 'swordfish', 'anchovies', 'sardines', 'mackerel',
    'shrimp', 'prawns', 'lobster', 'crab', 'scallops', 'oysters', 'mussels',
    'clams', 'calamari', 'squid', 'octopus', 'shellfish', 'crustacean',
    'caviar', 'roe', 'sea bass', 'red snapper', 'grouper', 'monkfish'
}

# Common allergens
ALLERGEN_TERMS = {
    'nuts': {'nuts', 'peanuts', 'almonds', 'cashews', 'walnuts', 'pecans', 
             'hazelnuts', 'pistachios', 'macadamia', 'brazil nuts', 'pine nuts'},
    'gluten': {'gluten', 'wheat', 'flour', 'bread', 'pasta', 'breadcrumbs',
               'croutons', 'baguette', 'pita', 'tortilla', 'couscous', 'barley', 'rye'},
    'dairy': {'dairy', 'milk', 'cream', 'butter', 'yogurt', 'whey', 'lactose'} | CHEESE_TERMS,
    'eggs': {'eggs', 'egg', 'mayonnaise', 'aioli', 'hollandaise', 'meringue'},
    'soy': {'soy', 'soya', 'tofu', 'tempeh', 'edamame', 'miso', 'soy sauce'},
    'shellfish': {'shellfish', 'shrimp', 'lobster', 'crab', 'prawns', 'crawfish',
                  'crayfish', 'langostino', 'scampi'},
    'sesame': {'sesame', 'tahini', 'sesame oil', 'sesame seeds'}
}


def normalize_ingredient(ingredient: str) -> str:
    """Normalize ingredient string for comparison."""
    return ingredient.lower().strip()


def contains_ingredient_term(ingredients: List[str], search_terms: Set[str]) -> bool:
    """
    Check if any ingredient contains any of the search terms.
    
    Args:
        ingredients: List of ingredients from menu item
        search_terms: Set of terms to search for
        
    Returns:
        True if any search term is found in ingredients
    """
    if not ingredients:
        return False
        
    # Normalize all ingredients
    normalized_ingredients = [normalize_ingredient(ing) for ing in ingredients]
    
    # Check each ingredient against search terms
    for ingredient in normalized_ingredients:
        for term in search_terms:
            if term in ingredient:
                return True
    
    # Also check the full ingredients string
    full_ingredients_text = ' '.join(normalized_ingredients)
    for term in search_terms:
        if term in full_ingredients_text:
            return True
            
    return False


def search_items_by_ingredient(
    menu_items: List[Dict],
    ingredient_type: str,
    find_with: bool = True
) -> List[Dict]:
    """
    Search menu items based on specific ingredient types.
    
    Args:
        menu_items: List of menu item dictionaries
        ingredient_type: Type of ingredient to search for ('cheese', 'meat', 'seafood', etc.)
        find_with: If True, find items WITH the ingredient. If False, find items WITHOUT.
        
    Returns:
        List of menu items that match the criteria
    """
    # Determine which terms to search for
    search_terms = set()
    
    if ingredient_type.lower() == 'cheese':
        search_terms = CHEESE_TERMS
    elif ingredient_type.lower() in ['meat', 'meats']:
        search_terms = MEAT_TERMS
    elif ingredient_type.lower() in ['seafood', 'fish']:
        search_terms = SEAFOOD_TERMS
    elif ingredient_type.lower() in ALLERGEN_TERMS:
        search_terms = ALLERGEN_TERMS[ingredient_type.lower()]
    else:
        # Single ingredient search
        search_terms = {ingredient_type.lower()}
    
    matching_items = []
    
    for item in menu_items:
        # Get ingredients list
        ingredients = item.get('ingredients', [])
        
        # Also check description and title for ingredient mentions
        title = (item.get('title') or item.get('dish') or '').lower()
        description = (item.get('description') or '').lower()
        
        # Check if item contains the ingredient
        has_ingredient = contains_ingredient_term(ingredients, search_terms)
        
        # Also check in title and description
        if not has_ingredient:
            for term in search_terms:
                if term in title or term in description:
                    has_ingredient = True
                    break
        
        # Add to results based on find_with parameter
        if (find_with and has_ingredient) or (not find_with and not has_ingredient):
            matching_items.append(item)
    
    return matching_items


def get_items_avoiding_ingredients(
    menu_items: List[Dict],
    avoid_ingredients: List[str]
) -> List[Dict]:
    """
    Get menu items that don't contain any of the specified ingredients.
    
    Args:
        menu_items: List of menu item dictionaries
        avoid_ingredients: List of ingredients to avoid
        
    Returns:
        List of menu items that don't contain any avoided ingredients
    """
    safe_items = []
    
    for item in menu_items:
        is_safe = True
        
        # Check each ingredient to avoid
        for avoid_ing in avoid_ingredients:
            items_with_ing = search_items_by_ingredient(
                [item], 
                avoid_ing, 
                find_with=True
            )
            
            if items_with_ing:  # Item contains this ingredient
                is_safe = False
                break
        
        if is_safe:
            safe_items.append(item)
    
    return safe_items


def categorize_menu_items_by_dietary_preference(
    menu_items: List[Dict]
) -> Dict[str, List[Dict]]:
    """
    Categorize menu items by common dietary preferences.
    
    Args:
        menu_items: List of menu item dictionaries
        
    Returns:
        Dictionary with categories as keys and lists of items as values
    """
    categories = {
        'vegetarian': [],  # No meat or seafood
        'vegan': [],       # No animal products
        'gluten_free': [], # No gluten
        'dairy_free': [],  # No dairy
        'nut_free': [],    # No nuts
        'pescatarian': [], # No meat but seafood ok
        'contains_cheese': [],  # Has cheese
        'meat_dishes': [],      # Contains meat
        'seafood_dishes': []    # Contains seafood
    }
    
    for item in menu_items:
        # Check for meat
        has_meat = bool(search_items_by_ingredient([item], 'meat', find_with=True))
        
        # Check for seafood
        has_seafood = bool(search_items_by_ingredient([item], 'seafood', find_with=True))
        
        # Check for cheese/dairy
        has_cheese = bool(search_items_by_ingredient([item], 'cheese', find_with=True))
        has_dairy = bool(search_items_by_ingredient([item], 'dairy', find_with=True))
        
        # Check for gluten
        has_gluten = bool(search_items_by_ingredient([item], 'gluten', find_with=True))
        
        # Check for nuts
        has_nuts = bool(search_items_by_ingredient([item], 'nuts', find_with=True))
        
        # Check for eggs
        has_eggs = bool(search_items_by_ingredient([item], 'eggs', find_with=True))
        
        # Categorize
        if has_cheese:
            categories['contains_cheese'].append(item)
            
        if has_meat:
            categories['meat_dishes'].append(item)
            
        if has_seafood:
            categories['seafood_dishes'].append(item)
            
        if not has_meat and not has_seafood:
            categories['vegetarian'].append(item)
            
            if not has_dairy and not has_eggs:
                categories['vegan'].append(item)
                
        if not has_gluten:
            categories['gluten_free'].append(item)
            
        if not has_dairy:
            categories['dairy_free'].append(item)
            
        if not has_nuts:
            categories['nut_free'].append(item)
            
        if not has_meat and has_seafood:
            categories['pescatarian'].append(item)
    
    return categories


def enhance_search_with_ingredients(
    restaurant_id: str,
    query: str,
    menu_items: List[Dict],
    semantic_results: List[Dict]
) -> List[Dict]:
    """
    Enhance semantic search results with ingredient-based filtering.
    This ensures we don't miss items that contain specific ingredients.
    
    Args:
        restaurant_id: Restaurant identifier
        query: User's search query
        menu_items: All menu items
        semantic_results: Results from semantic search
        
    Returns:
        Enhanced list of relevant menu items
    """
    query_lower = query.lower()
    
    # Check if query mentions specific ingredients
    ingredient_based_results = []
    
    # Check for cheese preferences
    if any(term in query_lower for term in ['cheese', 'cheesy', 'fromage']):
        if any(neg in query_lower for neg in ["don't", "no", "without", "avoid", "allerg"]):
            # User wants to avoid cheese
            ingredient_based_results = search_items_by_ingredient(
                menu_items, 'cheese', find_with=False
            )
        else:
            # User likes cheese
            ingredient_based_results = search_items_by_ingredient(
                menu_items, 'cheese', find_with=True
            )
    
    # Check for meat preferences
    elif any(term in query_lower for term in ['meat', 'beef', 'chicken', 'pork', 'lamb']):
        if any(neg in query_lower for neg in ["don't", "no", "without", "avoid", "vegetarian"]):
            ingredient_based_results = search_items_by_ingredient(
                menu_items, 'meat', find_with=False
            )
        else:
            ingredient_based_results = search_items_by_ingredient(
                menu_items, 'meat', find_with=True
            )
    
    # Check for seafood preferences
    elif any(term in query_lower for term in ['seafood', 'fish', 'shrimp', 'lobster']):
        if any(neg in query_lower for neg in ["don't", "no", "without", "avoid", "allerg"]):
            ingredient_based_results = search_items_by_ingredient(
                menu_items, 'seafood', find_with=False
            )
        else:
            ingredient_based_results = search_items_by_ingredient(
                menu_items, 'seafood', find_with=True
            )
    
    # If we found ingredient-based results, merge with semantic results
    if ingredient_based_results:
        # Create a set of item names from semantic results
        semantic_item_names = {
            item.get('title') or item.get('dish', '') 
            for item in semantic_results
        }
        
        # Add ingredient-based results that aren't already in semantic results
        for item in ingredient_based_results:
            item_name = item.get('title') or item.get('dish', '')
            if item_name and item_name not in semantic_item_names:
                # Add with a relevance score indicating it's from ingredient search
                item_copy = item.copy()
                item_copy['relevance_score'] = 0.8  # Lower than semantic matches
                semantic_results.append(item_copy)
        
        # Sort by relevance score (semantic matches first, then ingredient matches)
        semantic_results.sort(
            key=lambda x: x.get('relevance_score', 0.5), 
            reverse=True
        )
    
    return semantic_results