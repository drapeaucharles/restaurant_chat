# 🚨 DEVELOPMENT RULES - NO HARDCODING

## ❌ **NEVER HARDCODE PRODUCT DATA**

### **RULE 1: ALWAYS USE DATABASE AS SOURCE OF TRUTH**
- **NEVER** hardcode product names, prices, or details
- **ALWAYS** query the database for actual products
- **NEVER** create generic/placeholder product recommendations
- **ALWAYS** use real product data from the database

### **RULE 2: NO GENERIC PRODUCT TYPES**
- **NEVER** recommend "E-KIT", "B211A", "KITAS" as generic types
- **ALWAYS** use actual product names from database like "Electronic Visa (E-KIT)"
- **NEVER** hardcode pricing like "500,000 IDR" without database source
- **ALWAYS** get pricing from actual product records

### **RULE 3: FALLBACK SYSTEMS MUST USE DATABASE**
- **NEVER** create fallback responses with hardcoded products
- **ALWAYS** query database even in fallback scenarios
- **NEVER** assume product details - always fetch from database
- **ALWAYS** maintain database connection in fallback logic

## ✅ **CORRECT PATTERNS**

### **GOOD: Database-Driven Recommendations**
```python
# ✅ CORRECT - Always use database
def get_recommendation(profile):
    products = get_visa_products_from_database()
    recommended = find_best_match(profile, products)
    return f"I recommend {recommended['name']} for {profile['duration']} days. Cost: {recommended['price']} IDR."
```

### **BAD: Hardcoded Generic Types**
```python
# ❌ WRONG - Never hardcode generic types
def get_recommendation(profile):
    if profile['duration'] <= 30:
        return "I recommend E-KIT for 30 days. Cost: 500,000 IDR."  # WRONG!
```

## 🎯 **LANGUAGE CONSISTENCY RULES**

### **RULE 4: TRANSLATE REAL PRODUCTS, NOT GENERIC TYPES**
- **NEVER** hardcode generic visa types for language support
- **ALWAYS** translate actual product names from database
- **NEVER** create language-specific hardcoded responses
- **ALWAYS** use database products + translation system

### **CORRECT LANGUAGE APPROACH:**
```python
# ✅ CORRECT - Translate real products
def get_recommendation_multilingual(profile, language):
    products = get_visa_products_from_database()  # Real products
    recommended = find_best_match(profile, products)
    translated_name = translate_product_name(recommended['name'], language)
    return f"I recommend {translated_name} for {profile['duration']} days."
```

## 🚫 **ANTI-PATTERNS TO AVOID**

### **NEVER DO THIS:**
1. **Hardcode product names** in fallback responses
2. **Use generic visa types** instead of database products
3. **Hardcode pricing** without database source
4. **Create language-specific hardcoded responses**
5. **Assume product details** without database query
6. **Use placeholder product data** in any scenario

### **ALWAYS DO THIS:**
1. **Query database** for all product information
2. **Use actual product names** from database
3. **Get pricing from product records**
4. **Translate real products** for language support
5. **Validate product existence** before recommending
6. **Maintain database connection** in all scenarios

## 🔍 **VALIDATION CHECKLIST**

Before any code change, ask:
- [ ] Am I using actual database products?
- [ ] Am I hardcoding any product names or prices?
- [ ] Am I using generic types instead of real products?
- [ ] Will this break database recommendation matching?
- [ ] Am I maintaining the database as source of truth?

## 🎯 **CORE PRINCIPLE**

**THE DATABASE IS THE SINGLE SOURCE OF TRUTH FOR ALL PRODUCT DATA**

- No hardcoded products
- No generic types
- No assumed pricing
- No placeholder data
- Always query, never assume

---

**Remember: Hardcoding product data breaks the core functionality and makes the system useless. Always use the database.**
