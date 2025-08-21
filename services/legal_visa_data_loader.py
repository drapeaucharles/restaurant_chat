"""
Data loader for legal/visa services
Example of how to structure services for Bali Business Consulting
"""

LEGAL_VISA_SERVICES = {
    "visa_services": [
        {
            "id": "remote_worker_kitas",
            "name": "Remote Worker KITAS",
            "description": "Work legally in Indonesia as a remote worker or digital nomad. This visa allows you to live in Indonesia while working for a foreign company.",
            "price": 1500,
            "category": "Visa Services",
            "product_type": "service",
            "duration": "2-3 weeks processing",
            "requirements": {
                "documents": [
                    "Valid passport (6+ months)",
                    "Employment letter from foreign company",
                    "Bank statements (3 months)",
                    "Health insurance",
                    "Passport photos"
                ],
                "eligibility": [
                    "Employed by foreign company",
                    "Minimum salary requirement",
                    "Remote work arrangement"
                ]
            },
            "features": [
                "6 months initial stay",
                "Extendable up to 2 years",
                "Work permit included",
                "Tax consultation",
                "24/7 support"
            ],
            "tags": ["visa", "work", "remote", "digital nomad", "kitas", "long term"]
        },
        {
            "id": "retirement_kitas",
            "name": "Retirement KITAS",
            "description": "Enjoy your retirement in the tropical paradise of Indonesia. This visa is perfect for retirees looking to make Indonesia their home.",
            "price": 1200,
            "category": "Visa Services",
            "product_type": "service",
            "duration": "2-3 weeks processing",
            "requirements": {
                "documents": [
                    "Valid passport (6+ months)",
                    "Proof of pension/retirement income",
                    "Bank statements",
                    "Health insurance",
                    "Police clearance certificate"
                ],
                "eligibility": [
                    "Age 55+",
                    "Minimum monthly income $1,500",
                    "Cannot work in Indonesia"
                ]
            },
            "features": [
                "1 year initial stay",
                "Renewable annually",
                "Multiple entry permit",
                "Spouse can be included",
                "Property rental assistance"
            ],
            "tags": ["visa", "retirement", "kitas", "long term", "senior", "expat"]
        },
        {
            "id": "second_home_visa",
            "name": "Second Home Visa",
            "description": "Indonesia's new 5-10 year visa for investors and high net worth individuals who want to make Indonesia their second home.",
            "price": 3000,
            "category": "Visa Services",
            "product_type": "service",
            "duration": "4-6 weeks processing",
            "requirements": {
                "documents": [
                    "Valid passport",
                    "Proof of funds ($130,000)",
                    "Bank statements",
                    "Investment plan",
                    "Health insurance"
                ],
                "eligibility": [
                    "Proof of $130,000 in Indonesian bank",
                    "Cannot work for Indonesian company",
                    "Valid for property purchase"
                ]
            },
            "features": [
                "5 or 10 year visa options",
                "Multiple entry",
                "Family members included",
                "Property ownership rights",
                "VIP immigration services"
            ],
            "tags": ["visa", "second home", "investment", "long term", "property", "luxury"]
        },
        {
            "id": "business_visa_d2",
            "name": "Multiple-Entry Business Visa D2",
            "description": "Perfect for business travelers who need to visit Indonesia frequently for meetings, conferences, or business development.",
            "price": 500,
            "category": "Visa Services",
            "product_type": "service",
            "duration": "5-7 business days",
            "requirements": {
                "documents": [
                    "Valid passport",
                    "Company letter",
                    "Invitation letter from Indonesian company",
                    "Return ticket",
                    "Passport photos"
                ],
                "eligibility": [
                    "Business purpose only",
                    "Cannot receive payment in Indonesia",
                    "Valid company affiliation"
                ]
            },
            "features": [
                "Multiple entries",
                "60 days per visit",
                "Valid for 1 year",
                "Fast processing",
                "Airport assistance available"
            ],
            "tags": ["visa", "business", "short term", "multiple entry", "meetings"]
        }
    ],
    "legal_services": [
        {
            "id": "pt_pma_formation",
            "name": "PT PMA Company Formation",
            "description": "Establish a foreign-owned company (PT PMA) in Indonesia. Full service from incorporation to operational licenses.",
            "price": 3500,
            "category": "Legal Services",
            "product_type": "service",
            "duration": "4-6 weeks",
            "requirements": {
                "documents": [
                    "Passport copies of shareholders",
                    "Company name (3 options)",
                    "Business plan",
                    "Proof of funds",
                    "Office lease agreement"
                ],
                "minimum_requirements": [
                    "Minimum investment IDR 10 billion",
                    "Minimum 2 shareholders",
                    "Local director required"
                ]
            },
            "features": [
                "Company registration",
                "Tax registration (NPWP)",
                "Business licenses (NIB)",
                "Bank account opening",
                "Annual compliance support"
            ],
            "tags": ["company", "formation", "pt pma", "foreign investment", "business setup"]
        },
        {
            "id": "property_due_diligence",
            "name": "Land & Property Due Diligence",
            "description": "Comprehensive legal review of property titles and documentation to ensure safe property transactions in Indonesia.",
            "price": 800,
            "category": "Legal Services",
            "product_type": "service",
            "duration": "3-5 business days",
            "requirements": {
                "documents": [
                    "Property certificates",
                    "Land title documents",
                    "Previous sale agreements",
                    "Tax payment receipts"
                ]
            },
            "features": [
                "Title verification",
                "Zoning check",
                "Tax status review",
                "Encumbrance search",
                "Legal opinion letter"
            ],
            "tags": ["property", "due diligence", "real estate", "legal review", "investment"]
        },
        {
            "id": "trademark_registration",
            "name": "Trademark Registration",
            "description": "Protect your brand in Indonesia with official trademark registration. Full service from search to certificate.",
            "price": 600,
            "category": "Legal Services",
            "product_type": "service",
            "duration": "6-8 months",
            "requirements": {
                "documents": [
                    "Logo/brand name",
                    "List of goods/services",
                    "Power of attorney",
                    "Priority documents (if any)"
                ]
            },
            "features": [
                "Trademark search",
                "Application filing",
                "Government liaison",
                "Certificate delivery",
                "10-year protection"
            ],
            "tags": ["trademark", "intellectual property", "brand", "registration", "protection"]
        },
        {
            "id": "alcohol_license",
            "name": "Alcohol License",
            "description": "Obtain the necessary licenses to sell alcohol in your restaurant, hotel, or retail business in Indonesia.",
            "price": 1200,
            "category": "Legal Services",
            "product_type": "service",
            "duration": "4-8 weeks",
            "requirements": {
                "documents": [
                    "Company registration",
                    "Business license",
                    "Location permit",
                    "Floor plan",
                    "Tourism registration (if applicable)"
                ],
                "restrictions": [
                    "Not in residential areas",
                    "Minimum distance from schools/religious sites",
                    "Tourism area preferred"
                ]
            },
            "features": [
                "License application",
                "Location assessment",
                "Government liaison",
                "Annual renewal support",
                "Compliance guidance"
            ],
            "tags": ["alcohol", "license", "restaurant", "bar", "hospitality", "permit"]
        }
    ],
    "consultation_services": [
        {
            "id": "initial_consultation",
            "name": "Initial Consultation",
            "description": "Free 30-minute consultation to discuss your visa or legal needs in Indonesia.",
            "price": 0,
            "category": "Consultation",
            "product_type": "consultation",
            "duration": "30 minutes",
            "requirements": {
                "booking": "Appointment required"
            },
            "features": [
                "Needs assessment",
                "Service recommendations",
                "Cost estimation",
                "Timeline overview"
            ],
            "tags": ["consultation", "free", "advice", "planning"]
        },
        {
            "id": "premium_consultation",
            "name": "Premium Legal Consultation",
            "description": "In-depth legal consultation with our senior consultants for complex matters.",
            "price": 150,
            "category": "Consultation",
            "product_type": "consultation",
            "duration": "1 hour",
            "requirements": {
                "booking": "Appointment required",
                "preparation": "Documents review included"
            },
            "features": [
                "Senior consultant",
                "Written legal opinion",
                "Action plan",
                "Follow-up support"
            ],
            "tags": ["consultation", "legal advice", "premium", "expert"]
        }
    ]
}

def get_legal_visa_metadata():
    """Get metadata for a legal/visa consulting business"""
    return {
        "specialties": ["visa services", "company formation", "property law", "trademark", "licensing"],
        "languages": ["English", "Indonesian", "Mandarin"],
        "experience_years": 13,
        "certifications": ["Indonesian Bar Association", "Immigration Consultant License"],
        "office_locations": ["Bali", "Jakarta"],
        "consultation_available": True,
        "emergency_support": True,
        "payment_methods": ["Bank Transfer", "Credit Card", "Crypto"],
        "office_hours": {
            "monday-friday": "9:00 AM - 6:00 PM",
            "saturday": "9:00 AM - 1:00 PM",
            "sunday": "Closed"
        }
    }

def format_service_for_ai(service):
    """Format service data for AI understanding"""
    formatted = f"{service['name']} - ${service['price']}\n"
    formatted += f"Description: {service['description']}\n"
    formatted += f"Processing Time: {service.get('duration', 'Contact us')}\n"
    
    if service.get('requirements'):
        if 'documents' in service['requirements']:
            formatted += f"Required Documents: {', '.join(service['requirements']['documents'])}\n"
        if 'eligibility' in service['requirements']:
            formatted += f"Eligibility: {', '.join(service['requirements']['eligibility'])}\n"
    
    if service.get('features'):
        formatted += f"Includes: {', '.join(service['features'])}\n"
    
    return formatted