"""
Restaurant categories endpoint for getting predefined categories.
"""

from fastapi import APIRouter
from typing import List

router = APIRouter(tags=["restaurant_categories"])

# Predefined common restaurant categories
PREDEFINED_CATEGORIES = [
    "Italian",
    "Pizza",
    "Pasta",
    "Chinese",
    "Japanese",
    "Thai",
    "Indian",
    "Mexican",
    "American",
    "French",
    "Mediterranean",
    "Greek",
    "Spanish",
    "Korean",
    "Vietnamese",
    "Middle Eastern",
    "Seafood",
    "Steakhouse",
    "BBQ",
    "Vegetarian",
    "Vegan",
    "Fast Food",
    "Cafe",
    "Bakery",
    "Desserts",
    "Brunch",
    "Fine Dining",
    "Casual Dining",
    "Food Truck",
    "Bar & Grill",
    "Pub",
    "Fusion",
    "Healthy",
    "Organic",
    "Gluten-Free",
    "Halal",
    "Kosher"
]

@router.get("/restaurant/categories", response_model=List[str])
def get_restaurant_categories():
    """
    Get all available predefined restaurant categories.
    Each restaurant can choose from these or enter their own custom value.
    """
    # Return only predefined categories to keep the list clean and manageable
    return PREDEFINED_CATEGORIES