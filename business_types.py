"""
Business type definitions and configurations
"""

BUSINESS_TYPES = {
    "restaurant": {
        "name": "Restaurant",
        "icon": "🍽️",
        "item_type": "dish",
        "item_types": ["dish", "beverage", "dessert"],
        "service_verb": "serve",
        "fields": {
            "menu": {
                "label": "Menu",
                "type": "items_list",
                "item_fields": {
                    "title": {"label": "Dish Name", "required": True},
                    "description": {"label": "Description", "required": True},
                    "price": {"label": "Price", "required": True},
                    "category": {"label": "Category", "options": ["Breakfast", "Lunch", "Dinner", "Appetizer", "Main", "Dessert", "Beverage"]},
                    "ingredients": {"label": "Ingredients", "type": "list"},
                    "allergens": {"label": "Allergens", "type": "list"},
                    "photo_url": {"label": "Photo", "type": "image"}
                }
            },
            "cuisine_type": {"label": "Cuisine Type", "type": "select", "options": ["Italian", "French", "Asian", "Mexican", "American", "Mediterranean", "Other"]},
            "dining_options": {"label": "Dining Options", "type": "multiselect", "options": ["Dine-in", "Takeout", "Delivery", "Catering"]},
            "opening_hours": {"label": "Opening Hours", "type": "hours"}
        }
    },
    "salon": {
        "name": "Hair & Beauty Salon",
        "icon": "💇",
        "item_type": "service",
        "item_types": ["hair_service", "beauty_service", "nail_service"],
        "service_verb": "offer",
        "fields": {
            "services": {
                "label": "Services",
                "type": "items_list",
                "item_fields": {
                    "title": {"label": "Service Name", "required": True},
                    "description": {"label": "Description", "required": True},
                    "price": {"label": "Price", "required": True},
                    "duration": {"label": "Duration (minutes)", "type": "number"},
                    "category": {"label": "Category", "options": ["Haircut", "Coloring", "Styling", "Treatment", "Manicure", "Pedicure", "Facial", "Massage"]},
                    "photo_url": {"label": "Photo", "type": "image"}
                }
            },
            "specialties": {"label": "Specialties", "type": "multiselect", "options": ["Hair Cutting", "Hair Coloring", "Extensions", "Nails", "Skincare", "Makeup"]},
            "booking_required": {"label": "Appointment Required", "type": "boolean", "default": True}
        }
    },
    "retail": {
        "name": "Retail Store",
        "icon": "🛍️",
        "item_type": "product",
        "item_types": ["product", "accessory", "sale_item"],
        "service_verb": "sell",
        "fields": {
            "products": {
                "label": "Products",
                "type": "items_list",
                "item_fields": {
                    "title": {"label": "Product Name", "required": True},
                    "description": {"label": "Description", "required": True},
                    "price": {"label": "Price", "required": True},
                    "category": {"label": "Category", "required": True},
                    "brand": {"label": "Brand"},
                    "sku": {"label": "SKU"},
                    "in_stock": {"label": "In Stock", "type": "boolean", "default": True},
                    "sizes": {"label": "Available Sizes", "type": "list"},
                    "colors": {"label": "Available Colors", "type": "list"},
                    "photo_url": {"label": "Photo", "type": "image"}
                }
            },
            "store_type": {"label": "Store Type", "type": "select", "options": ["Clothing", "Electronics", "Home Goods", "Sports", "Books", "Other"]},
            "shipping_available": {"label": "Shipping Available", "type": "boolean"},
            "return_policy": {"label": "Return Policy", "type": "textarea"}
        }
    },
    "medical": {
        "name": "Medical Practice",
        "icon": "⚕️",
        "item_type": "service",
        "item_types": ["consultation", "procedure", "treatment"],
        "service_verb": "provide",
        "fields": {
            "services": {
                "label": "Medical Services",
                "type": "items_list",
                "item_fields": {
                    "title": {"label": "Service Name", "required": True},
                    "description": {"label": "Description", "required": True},
                    "price": {"label": "Price (if applicable)"},
                    "duration": {"label": "Duration (minutes)", "type": "number"},
                    "category": {"label": "Category", "options": ["Consultation", "Examination", "Procedure", "Vaccination", "Testing"]},
                    "preparation": {"label": "Preparation Instructions", "type": "textarea"}
                }
            },
            "specialties": {"label": "Medical Specialties", "type": "multiselect"},
            "insurance_accepted": {"label": "Insurance Plans Accepted", "type": "list"},
            "emergency_hours": {"label": "Emergency Hours Available", "type": "boolean"}
        }
    },
    "fitness": {
        "name": "Fitness & Gym",
        "icon": "🏋️",
        "item_type": "service",
        "item_types": ["membership", "class", "training"],
        "service_verb": "offer",
        "fields": {
            "services": {
                "label": "Services & Classes",
                "type": "items_list",
                "item_fields": {
                    "title": {"label": "Service/Class Name", "required": True},
                    "description": {"label": "Description", "required": True},
                    "price": {"label": "Price", "required": True},
                    "duration": {"label": "Duration (minutes)", "type": "number"},
                    "category": {"label": "Category", "options": ["Membership", "Personal Training", "Group Class", "Yoga", "Pilates", "Cardio", "Strength"]},
                    "difficulty": {"label": "Difficulty Level", "options": ["Beginner", "Intermediate", "Advanced"]},
                    "max_participants": {"label": "Max Participants", "type": "number"},
                    "equipment_needed": {"label": "Equipment Needed", "type": "list"}
                }
            },
            "amenities": {"label": "Amenities", "type": "multiselect", "options": ["Pool", "Sauna", "Locker Rooms", "Showers", "Parking", "Juice Bar", "Personal Training"]},
            "membership_required": {"label": "Membership Required", "type": "boolean"}
        }
    },
    "hotel": {
        "name": "Hotel & Accommodation",
        "icon": "🏨",
        "item_type": "room",
        "item_types": ["room", "suite", "amenity"],
        "service_verb": "offer",
        "fields": {
            "rooms": {
                "label": "Rooms & Suites",
                "type": "items_list",
                "item_fields": {
                    "title": {"label": "Room Type", "required": True},
                    "description": {"label": "Description", "required": True},
                    "price": {"label": "Price per Night", "required": True},
                    "capacity": {"label": "Max Occupancy", "type": "number"},
                    "beds": {"label": "Bed Configuration"},
                    "size": {"label": "Room Size (sq ft)", "type": "number"},
                    "amenities": {"label": "Room Amenities", "type": "list"},
                    "view": {"label": "View Type"},
                    "photo_url": {"label": "Photo", "type": "image"}
                }
            },
            "hotel_amenities": {"label": "Hotel Amenities", "type": "multiselect", "options": ["Pool", "Spa", "Gym", "Restaurant", "Bar", "Conference Rooms", "Parking", "WiFi", "Pet Friendly"]},
            "check_in_time": {"label": "Check-in Time"},
            "check_out_time": {"label": "Check-out Time"},
            "cancellation_policy": {"label": "Cancellation Policy", "type": "textarea"}
        }
    },
    "automotive": {
        "name": "Automotive Service",
        "icon": "🚗",
        "item_type": "service",
        "item_types": ["repair", "maintenance", "diagnostic"],
        "service_verb": "provide",
        "fields": {
            "services": {
                "label": "Services",
                "type": "items_list",
                "item_fields": {
                    "title": {"label": "Service Name", "required": True},
                    "description": {"label": "Description", "required": True},
                    "price": {"label": "Starting Price", "required": True},
                    "duration": {"label": "Estimated Duration (hours)", "type": "number"},
                    "category": {"label": "Category", "options": ["Oil Change", "Tire Service", "Brake Service", "Engine Repair", "Transmission", "Diagnostic", "Body Work"]},
                    "warranty": {"label": "Warranty Period"}
                }
            },
            "brands_serviced": {"label": "Car Brands Serviced", "type": "list"},
            "certifications": {"label": "Certifications", "type": "list"},
            "shuttle_service": {"label": "Shuttle Service Available", "type": "boolean"}
        }
    },
    "education": {
        "name": "Education & Training",
        "icon": "🎓",
        "item_type": "course",
        "item_types": ["course", "workshop", "certification"],
        "service_verb": "offer",
        "fields": {
            "courses": {
                "label": "Courses & Programs",
                "type": "items_list",
                "item_fields": {
                    "title": {"label": "Course Name", "required": True},
                    "description": {"label": "Description", "required": True},
                    "price": {"label": "Price", "required": True},
                    "duration": {"label": "Duration"},
                    "category": {"label": "Category", "options": ["Language", "Technology", "Business", "Arts", "Science", "Professional Development"]},
                    "level": {"label": "Level", "options": ["Beginner", "Intermediate", "Advanced"]},
                    "format": {"label": "Format", "options": ["In-Person", "Online", "Hybrid"]},
                    "certification": {"label": "Certification Provided", "type": "boolean"},
                    "prerequisites": {"label": "Prerequisites", "type": "list"}
                }
            },
            "accreditation": {"label": "Accreditation", "type": "list"},
            "financial_aid": {"label": "Financial Aid Available", "type": "boolean"}
        }
    },
    "real_estate": {
        "name": "Real Estate",
        "icon": "🏠",
        "item_type": "property",
        "item_types": ["sale", "rental", "commercial"],
        "service_verb": "list",
        "fields": {
            "properties": {
                "label": "Properties",
                "type": "items_list",
                "item_fields": {
                    "title": {"label": "Property Title", "required": True},
                    "description": {"label": "Description", "required": True},
                    "price": {"label": "Price", "required": True},
                    "type": {"label": "Property Type", "options": ["House", "Apartment", "Condo", "Land", "Commercial"]},
                    "bedrooms": {"label": "Bedrooms", "type": "number"},
                    "bathrooms": {"label": "Bathrooms", "type": "number"},
                    "size": {"label": "Size (sq ft)", "type": "number"},
                    "year_built": {"label": "Year Built", "type": "number"},
                    "amenities": {"label": "Amenities", "type": "list"},
                    "address": {"label": "Address"},
                    "photo_url": {"label": "Photo", "type": "image"}
                }
            },
            "services_offered": {"label": "Services", "type": "multiselect", "options": ["Buying", "Selling", "Renting", "Property Management", "Consultation"]},
            "areas_served": {"label": "Areas Served", "type": "list"}
        }
    }
}

def get_business_types():
    """Get list of available business types"""
    return [
        {
            "id": key,
            "name": value["name"],
            "icon": value["icon"],
            "description": f"Manage {value['item_type']}s and related information"
        }
        for key, value in BUSINESS_TYPES.items()
    ]

def get_business_config(business_type):
    """Get configuration for a specific business type"""
    return BUSINESS_TYPES.get(business_type, BUSINESS_TYPES["restaurant"])