import requests
import json
from typing import List, Dict
import os

# Restaurant data with 50+ menu items
restaurant_data = {
    "restaurant_id": "bella_vista_restaurant",
    "password": "BellaVista2024!",
    "restaurant_data": {
        "name": "Bella Vista Gourmet",
        "restaurant_story": "Welcome to Bella Vista Gourmet, where culinary excellence meets warm hospitality. Founded in 2010, our restaurant has been serving the community with passion and dedication. Our chefs combine traditional techniques with modern innovation to create unforgettable dining experiences. Every dish tells a story, crafted with locally sourced ingredients and international flavors.",
        "whatsapp_number": "+1234567890",
        "contact_info": {
            "phone": "+1 (555) 123-4567",
            "email": "info@bellavistagourmet.com",
            "address": "123 Gourmet Street, Culinary District, Food City, FC 12345",
            "website": "www.bellavistagourmet.com"
        },
        "opening_hours": {
            "monday": "11:00 AM - 10:00 PM",
            "tuesday": "11:00 AM - 10:00 PM",
            "wednesday": "11:00 AM - 10:00 PM",
            "thursday": "11:00 AM - 11:00 PM",
            "friday": "11:00 AM - 12:00 AM",
            "saturday": "10:00 AM - 12:00 AM",
            "sunday": "10:00 AM - 10:00 PM"
        },
        "faq": [
            {
                "question": "Do you take reservations?",
                "answer": "Yes! We highly recommend making reservations, especially for weekends. You can book online or call us directly."
            },
            {
                "question": "Do you accommodate dietary restrictions?",
                "answer": "Absolutely! We offer gluten-free, vegan, and vegetarian options. Please inform us of any allergies when ordering."
            },
            {
                "question": "Is there parking available?",
                "answer": "Yes, we have a dedicated parking lot with 50 spaces, plus valet parking on Friday and Saturday evenings."
            },
            {
                "question": "Do you offer catering services?",
                "answer": "Yes, we provide full catering services for events of all sizes. Contact us for a custom quote."
            },
            {
                "question": "Can I host private events at your restaurant?",
                "answer": "Yes! We have a private dining room that seats up to 40 guests, perfect for celebrations and business dinners."
            }
        ],
        "menu": [
            # APPETIZERS (10 items)
            {
                "dish": "Truffle Arancini",
                "price": "$12.99",
                "description": "Golden-fried risotto balls filled with truffle oil and parmesan, served with marinara sauce",
                "ingredients": ["arborio rice", "truffle oil", "parmesan", "breadcrumbs", "marinara sauce"],
                "allergens": ["gluten", "dairy"],
                "category": "Appetizers",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1541014741259-de529411b96a?w=400"
            },
            {
                "dish": "Caprese Skewers",
                "price": "$10.99",
                "description": "Fresh mozzarella, cherry tomatoes, and basil drizzled with balsamic glaze",
                "ingredients": ["mozzarella", "cherry tomatoes", "fresh basil", "balsamic glaze"],
                "allergens": ["dairy"],
                "category": "Appetizers",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1529928520614-7c76e2d99740?w=400"
            },
            {
                "dish": "Calamari Fritti",
                "price": "$14.99",
                "description": "Crispy fried calamari rings with spicy aioli and lemon wedges",
                "ingredients": ["calamari", "flour", "spices", "aioli", "lemon"],
                "allergens": ["seafood", "gluten"],
                "category": "Appetizers",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?w=400"
            },
            {
                "dish": "Bruschetta Trio",
                "price": "$11.99",
                "description": "Three varieties: classic tomato, mushroom & goat cheese, and olive tapenade",
                "ingredients": ["baguette", "tomatoes", "mushrooms", "goat cheese", "olives"],
                "allergens": ["gluten", "dairy"],
                "category": "Appetizers",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1572695157366-5e585ab2b69f?w=400"
            },
            {
                "dish": "Stuffed Mushrooms",
                "price": "$13.99",
                "description": "Button mushrooms filled with herbs, garlic, and three cheeses",
                "ingredients": ["mushrooms", "garlic", "parmesan", "mozzarella", "ricotta", "herbs"],
                "allergens": ["dairy"],
                "category": "Appetizers",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=400"
            },
            {
                "dish": "Shrimp Cocktail",
                "price": "$16.99",
                "description": "Jumbo shrimp served chilled with house-made cocktail sauce",
                "ingredients": ["jumbo shrimp", "cocktail sauce", "lemon", "herbs"],
                "allergens": ["shellfish"],
                "category": "Appetizers",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1625943553852-781c6dd46faa?w=400"
            },
            {
                "dish": "Spinach Artichoke Dip",
                "price": "$12.99",
                "description": "Creamy blend of spinach, artichokes, and cheese served with tortilla chips",
                "ingredients": ["spinach", "artichokes", "cream cheese", "parmesan", "tortilla chips"],
                "allergens": ["dairy", "gluten"],
                "category": "Appetizers",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=400"
            },
            {
                "dish": "Beef Carpaccio",
                "price": "$18.99",
                "description": "Thinly sliced raw beef with arugula, capers, and shaved parmesan",
                "ingredients": ["beef tenderloin", "arugula", "capers", "parmesan", "olive oil"],
                "allergens": ["dairy"],
                "category": "Appetizers",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1625937286074-9ca519d5d9df?w=400"
            },
            {
                "dish": "Mezze Platter",
                "price": "$15.99",
                "description": "Hummus, baba ganoush, falafel, olives, and warm pita bread",
                "ingredients": ["chickpeas", "tahini", "eggplant", "pita bread", "olives"],
                "allergens": ["gluten", "sesame"],
                "category": "Appetizers",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1593001872095-7d5b3868fb1d?w=400"
            },
            {
                "dish": "Oysters Rockefeller",
                "price": "$19.99",
                "description": "Fresh oysters baked with spinach, herbs, and hollandaise sauce",
                "ingredients": ["oysters", "spinach", "hollandaise", "breadcrumbs", "herbs"],
                "allergens": ["shellfish", "dairy", "gluten"],
                "category": "Appetizers",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1606850780554-b55ea4dd0b70?w=400"
            },
            
            # SOUPS & SALADS (8 items)
            {
                "dish": "French Onion Soup",
                "price": "$9.99",
                "description": "Classic soup with caramelized onions, topped with gruyere cheese and croutons",
                "ingredients": ["onions", "beef broth", "gruyere cheese", "baguette"],
                "allergens": ["dairy", "gluten"],
                "category": "Soups",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=400"
            },
            {
                "dish": "Lobster Bisque",
                "price": "$14.99",
                "description": "Rich, creamy soup with chunks of fresh lobster and a touch of sherry",
                "ingredients": ["lobster", "cream", "sherry", "herbs", "butter"],
                "allergens": ["shellfish", "dairy"],
                "category": "Soups",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1594756202469-9ff9799b2e4e?w=400"
            },
            {
                "dish": "Caesar Salad",
                "price": "$11.99",
                "description": "Crisp romaine lettuce with parmesan, croutons, and house-made Caesar dressing",
                "ingredients": ["romaine lettuce", "parmesan", "croutons", "caesar dressing", "anchovies"],
                "allergens": ["dairy", "gluten", "fish"],
                "category": "Salads",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1550304943-4f24f54ddde9?w=400"
            },
            {
                "dish": "Greek Salad",
                "price": "$12.99",
                "description": "Fresh vegetables with feta cheese, olives, and oregano vinaigrette",
                "ingredients": ["cucumbers", "tomatoes", "feta", "olives", "red onions", "oregano"],
                "allergens": ["dairy"],
                "category": "Salads",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=400"
            },
            {
                "dish": "Roasted Beet Salad",
                "price": "$13.99",
                "description": "Roasted beets with goat cheese, candied walnuts, and balsamic reduction",
                "ingredients": ["beets", "goat cheese", "walnuts", "mixed greens", "balsamic"],
                "allergens": ["dairy", "nuts"],
                "category": "Salads",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1609501676725-7186f017a4b7?w=400"
            },
            {
                "dish": "Minestrone Soup",
                "price": "$8.99",
                "description": "Hearty Italian vegetable soup with beans and pasta",
                "ingredients": ["vegetables", "beans", "pasta", "tomatoes", "herbs"],
                "allergens": ["gluten"],
                "category": "Soups",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1613844237701-8f3664fc2eff?w=400"
            },
            {
                "dish": "Quinoa Power Bowl",
                "price": "$14.99",
                "description": "Quinoa with roasted vegetables, avocado, chickpeas, and tahini dressing",
                "ingredients": ["quinoa", "avocado", "chickpeas", "vegetables", "tahini"],
                "allergens": ["sesame"],
                "category": "Salads",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400"
            },
            {
                "dish": "Tom Yum Soup",
                "price": "$12.99",
                "description": "Spicy Thai soup with shrimp, lemongrass, and mushrooms",
                "ingredients": ["shrimp", "lemongrass", "mushrooms", "chili", "lime"],
                "allergens": ["shellfish"],
                "category": "Soups",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1562565652-a0d8f0c59eb4?w=400"
            },
            
            # PASTA & RISOTTO (8 items)
            {
                "dish": "Spaghetti Carbonara",
                "price": "$18.99",
                "description": "Classic Roman pasta with guanciale, egg yolk, and pecorino romano",
                "ingredients": ["spaghetti", "guanciale", "eggs", "pecorino romano", "black pepper"],
                "allergens": ["gluten", "dairy", "eggs"],
                "category": "Pasta",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1612874742237-6526221588e3?w=400"
            },
            {
                "dish": "Lobster Ravioli",
                "price": "$28.99",
                "description": "Handmade ravioli filled with lobster in a light tomato cream sauce",
                "ingredients": ["pasta", "lobster", "ricotta", "tomatoes", "cream"],
                "allergens": ["gluten", "dairy", "shellfish"],
                "category": "Pasta",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1587740908075-9e245070dfaa?w=400"
            },
            {
                "dish": "Mushroom Risotto",
                "price": "$22.99",
                "description": "Creamy arborio rice with wild mushrooms and truffle oil",
                "ingredients": ["arborio rice", "mushrooms", "parmesan", "truffle oil", "white wine"],
                "allergens": ["dairy"],
                "category": "Risotto",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1595908129746-57ca1a63dd4d?w=400"
            },
            {
                "dish": "Penne Arrabbiata",
                "price": "$16.99",
                "description": "Penne pasta in a spicy tomato sauce with garlic and red chilies",
                "ingredients": ["penne", "tomatoes", "garlic", "chili", "olive oil"],
                "allergens": ["gluten"],
                "category": "Pasta",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=400"
            },
            {
                "dish": "Seafood Linguine",
                "price": "$32.99",
                "description": "Linguine with shrimp, scallops, mussels in white wine sauce",
                "ingredients": ["linguine", "shrimp", "scallops", "mussels", "white wine"],
                "allergens": ["gluten", "shellfish"],
                "category": "Pasta",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1563379926898-05f4575a45d8?w=400"
            },
            {
                "dish": "Gnocchi Gorgonzola",
                "price": "$19.99",
                "description": "Potato gnocchi in a creamy gorgonzola sauce with walnuts",
                "ingredients": ["potato gnocchi", "gorgonzola", "cream", "walnuts"],
                "allergens": ["gluten", "dairy", "nuts"],
                "category": "Pasta",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1609501676725-7186f017a4b7?w=400"
            },
            {
                "dish": "Lasagna Bolognese",
                "price": "$20.99",
                "description": "Traditional lasagna with meat sauce, bechamel, and mozzarella",
                "ingredients": ["pasta sheets", "beef", "tomatoes", "bechamel", "mozzarella"],
                "allergens": ["gluten", "dairy"],
                "category": "Pasta",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1574894709920-11b28e7367e3?w=400"
            },
            {
                "dish": "Saffron Risotto",
                "price": "$24.99",
                "description": "Milanese-style risotto with saffron and parmesan",
                "ingredients": ["arborio rice", "saffron", "parmesan", "white wine", "butter"],
                "allergens": ["dairy"],
                "category": "Risotto",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1476124369491-e7addf5db371?w=400"
            },
            
            # MAIN COURSES - MEAT (8 items)
            {
                "dish": "Filet Mignon",
                "price": "$45.99",
                "description": "8oz center-cut beef tenderloin with red wine reduction",
                "ingredients": ["beef tenderloin", "red wine", "butter", "herbs"],
                "allergens": ["dairy"],
                "category": "Meat",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=400"
            },
            {
                "dish": "Rack of Lamb",
                "price": "$42.99",
                "description": "Herb-crusted lamb rack with mint chimichurri",
                "ingredients": ["lamb", "herbs", "breadcrumbs", "mint", "garlic"],
                "allergens": ["gluten"],
                "category": "Meat",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1595777216528-071e0127ccbf?w=400"
            },
            {
                "dish": "Osso Buco",
                "price": "$38.99",
                "description": "Braised veal shanks with gremolata over saffron risotto",
                "ingredients": ["veal", "vegetables", "white wine", "saffron", "gremolata"],
                "allergens": ["dairy"],
                "category": "Meat",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1432139555190-58524dae6a55?w=400"
            },
            {
                "dish": "Duck Confit",
                "price": "$36.99",
                "description": "Classic French duck leg with crispy skin and cherry sauce",
                "ingredients": ["duck", "duck fat", "cherries", "thyme", "garlic"],
                "allergens": [],
                "category": "Meat",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1623428187969-5da2dcea5ebf?w=400"
            },
            {
                "dish": "Beef Short Ribs",
                "price": "$34.99",
                "description": "Slow-braised short ribs with red wine and root vegetables",
                "ingredients": ["beef ribs", "red wine", "carrots", "celery", "onions"],
                "allergens": [],
                "category": "Meat",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1544025162-d76694265947?w=400"
            },
            {
                "dish": "Pork Tenderloin",
                "price": "$28.99",
                "description": "Maple-glazed pork tenderloin with apple compote",
                "ingredients": ["pork", "maple syrup", "apples", "cinnamon", "butter"],
                "allergens": ["dairy"],
                "category": "Meat",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1606850780554-b55ea4dd0b70?w=400"
            },
            {
                "dish": "Veal Piccata",
                "price": "$32.99",
                "description": "Pan-seared veal with lemon, capers, and white wine sauce",
                "ingredients": ["veal", "flour", "lemon", "capers", "white wine"],
                "allergens": ["gluten"],
                "category": "Meat",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1632778149955-e80f8ceca2e8?w=400"
            },
            {
                "dish": "Ribeye Steak",
                "price": "$39.99",
                "description": "12oz ribeye with herb butter and roasted garlic",
                "ingredients": ["ribeye", "herbs", "butter", "garlic"],
                "allergens": ["dairy"],
                "category": "Meat",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1558030006-450675393462?w=400"
            },
            
            # MAIN COURSES - SEAFOOD (6 items)
            {
                "dish": "Grilled Salmon",
                "price": "$26.99",
                "description": "Atlantic salmon with lemon dill sauce and asparagus",
                "ingredients": ["salmon", "lemon", "dill", "asparagus", "olive oil"],
                "allergens": ["fish"],
                "category": "Seafood",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1485921325833-c519f76c4927?w=400"
            },
            {
                "dish": "Sea Bass",
                "price": "$32.99",
                "description": "Pan-seared sea bass with miso glaze and bok choy",
                "ingredients": ["sea bass", "miso", "bok choy", "ginger", "sesame"],
                "allergens": ["fish", "soy", "sesame"],
                "category": "Seafood",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=400"
            },
            {
                "dish": "Lobster Thermidor",
                "price": "$48.99",
                "description": "Whole lobster with brandy cream sauce, gratinated",
                "ingredients": ["lobster", "brandy", "cream", "egg yolk", "cheese"],
                "allergens": ["shellfish", "dairy", "eggs"],
                "category": "Seafood",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=400"
            },
            {
                "dish": "Seared Scallops",
                "price": "$36.99",
                "description": "Pan-seared scallops with cauliflower puree and pancetta",
                "ingredients": ["scallops", "cauliflower", "pancetta", "butter"],
                "allergens": ["shellfish", "dairy"],
                "category": "Seafood",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1626201642492-15d1b4c0cd75?w=400"
            },
            {
                "dish": "Tuna Steak",
                "price": "$34.99",
                "description": "Sesame-crusted ahi tuna with wasabi aioli",
                "ingredients": ["tuna", "sesame seeds", "wasabi", "soy sauce"],
                "allergens": ["fish", "sesame", "soy"],
                "category": "Seafood",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1567479938401-f265a66ba382?w=400"
            },
            {
                "dish": "Mixed Seafood Grill",
                "price": "$42.99",
                "description": "Grilled lobster tail, shrimp, and fish with garlic butter",
                "ingredients": ["lobster", "shrimp", "fish", "garlic", "butter"],
                "allergens": ["shellfish", "fish", "dairy"],
                "category": "Seafood",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1623961990059-7d9d7e2f6fdd?w=400"
            },
            
            # VEGETARIAN/VEGAN (5 items)
            {
                "dish": "Eggplant Parmigiana",
                "price": "$18.99",
                "description": "Breaded eggplant layered with marinara and mozzarella",
                "ingredients": ["eggplant", "breadcrumbs", "marinara", "mozzarella", "parmesan"],
                "allergens": ["gluten", "dairy"],
                "category": "Vegetarian",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1573821663912-6df460f9c684?w=400"
            },
            {
                "dish": "Vegetable Curry",
                "price": "$16.99",
                "description": "Mixed vegetables in coconut curry sauce with jasmine rice",
                "ingredients": ["vegetables", "coconut milk", "curry", "rice"],
                "allergens": [],
                "category": "Vegan",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?w=400"
            },
            {
                "dish": "Stuffed Bell Peppers",
                "price": "$17.99",
                "description": "Bell peppers filled with quinoa, vegetables, and herbs",
                "ingredients": ["bell peppers", "quinoa", "vegetables", "herbs"],
                "allergens": [],
                "category": "Vegan",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1583278171230-7cde103c5935?w=400"
            },
            {
                "dish": "Mushroom Wellington",
                "price": "$22.99",
                "description": "Puff pastry wrapped mushroom duxelles with spinach",
                "ingredients": ["mushrooms", "puff pastry", "spinach", "herbs"],
                "allergens": ["gluten"],
                "category": "Vegetarian",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1511690078903-71dc5a49f5e3?w=400"
            },
            {
                "dish": "Buddha Bowl",
                "price": "$15.99",
                "description": "Brown rice with roasted vegetables, tofu, and tahini dressing",
                "ingredients": ["brown rice", "tofu", "vegetables", "tahini", "seeds"],
                "allergens": ["soy", "sesame"],
                "category": "Vegan",

                "subcategory": "main",
                "image_url": "https://images.unsplash.com/photo-1540914124281-342587941389?w=400"
            },
            
            # DESSERTS (5 items)
            {
                "dish": "Tiramisu",
                "price": "$9.99",
                "description": "Classic Italian dessert with espresso-soaked ladyfingers and mascarpone",
                "ingredients": ["ladyfingers", "mascarpone", "espresso", "cocoa", "eggs"],
                "allergens": ["gluten", "dairy", "eggs"],
                "category": "Dessert",

                "subcategory": "dessert",
                "image_url": "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=400"
            },
            {
                "dish": "Chocolate Lava Cake",
                "price": "$10.99",
                "description": "Warm chocolate cake with molten center, served with vanilla ice cream",
                "ingredients": ["chocolate", "flour", "eggs", "butter", "ice cream"],
                "allergens": ["gluten", "dairy", "eggs"],
                "category": "Dessert",

                "subcategory": "dessert",
                "image_url": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=400"
            },
            {
                "dish": "Crème Brûlée",
                "price": "$8.99",
                "description": "Classic French custard with caramelized sugar top",
                "ingredients": ["cream", "eggs", "sugar", "vanilla"],
                "allergens": ["dairy", "eggs"],
                "category": "Dessert",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1470124182917-cc6e71b22ecc?w=400"
            },
            {
                "dish": "New York Cheesecake",
                "price": "$9.99",
                "description": "Rich and creamy cheesecake with berry compote",
                "ingredients": ["cream cheese", "graham crackers", "eggs", "berries"],
                "allergens": ["gluten", "dairy", "eggs"],
                "category": "Dessert",

                "subcategory": "dessert",
                "image_url": "https://images.unsplash.com/photo-1524351199678-941a58a3df50?w=400"
            },
            {
                "dish": "Gelato Trio",
                "price": "$7.99",
                "description": "Three scoops of artisanal gelato: vanilla, chocolate, and pistachio",
                "ingredients": ["milk", "cream", "sugar", "various flavors"],
                "allergens": ["dairy", "nuts"],
                "category": "Dessert",

                "subcategory": "starter",
                "image_url": "https://images.unsplash.com/photo-1567206563064-6f60f40a2b57?w=400"
            }
        ]
    }
}

def download_image(url: str, filename: str) -> str:
    """Download image from URL and save it locally"""
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        filepath = f"test_images/{filename}"
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return filepath
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
        return None

def create_restaurant_with_images():
    """Create restaurant using multipart/form-data with images"""
    
    # Create test_images directory if it doesn't exist
    os.makedirs("test_images", exist_ok=True)
    
    # Download images for menu items
    print("Downloading images for menu items...")
    menu_images = {}
    
    for idx, item in enumerate(restaurant_data["restaurant_data"]["menu"][:10]):  # Limit to first 10 items for images
        if "image_url" in item:
            filename = f"menu_{idx}_{item['dish'].lower().replace(' ', '_')}.jpg"
            filepath = download_image(item["image_url"], filename)
            if filepath:
                menu_images[idx] = filepath
                print(f"Downloaded image for {item['dish']}")
    
    # Prepare the multipart form data
    files = []
    
    # Add the JSON data
    data_json = json.dumps({
        "restaurant_id": restaurant_data["restaurant_id"],
        "password": restaurant_data["password"],
        "restaurant_data": restaurant_data["restaurant_data"]
    })
    
    files.append(('data', (None, data_json, 'application/json')))
    
    # Add image files
    for idx, filepath in menu_images.items():
        with open(filepath, 'rb') as f:
            files.append((f'menu_photo_{idx}', (os.path.basename(filepath), f.read(), 'image/jpeg')))
    
    # Make the API request
    url = "https://restaurantchat-production.up.railway.app/restaurant/register/multipart"
    
    print("\nCreating restaurant with images...")
    try:
        response = requests.post(url, files=files)
        
        if response.status_code == 200:
            print("✅ Restaurant created successfully!")
            print(f"Restaurant ID: {restaurant_data['restaurant_id']}")
            print(f"Password: {restaurant_data['password']}")
            print(f"Total menu items: {len(restaurant_data['restaurant_data']['menu'])}")
            print(f"Images uploaded: {len(menu_images)}")
            return True
        else:
            print(f"❌ Error creating restaurant: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return False

if __name__ == "__main__":
    print("Creating Bella Vista Gourmet test restaurant...")
    print(f"Total menu items: {len(restaurant_data['restaurant_data']['menu'])}")
    
    success = create_restaurant_with_images()
    
    if success:
        print("\n🎉 Test restaurant created successfully!")
        print("\nYou can now login with:")
        print(f"Restaurant ID: {restaurant_data['restaurant_id']}")
        print(f"Password: {restaurant_data['password']}")
    else:
        print("\n❌ Failed to create test restaurant")