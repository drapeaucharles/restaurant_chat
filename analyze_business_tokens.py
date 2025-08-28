"""
Analyze token usage for different business types
"""

def estimate_tokens(text):
    """Rough token estimation: ~4 chars = 1 token"""
    return len(text) // 4

# Restaurant example (50 items)
restaurant_item = "• Spaghetti Carbonara ($18.99) [eggs, guanciale, pecorino] {eggs, dairy, gluten}"
restaurant_tokens = estimate_tokens(restaurant_item) * 50
print("RESTAURANT (50 items):")
print(f"  Per item: ~{estimate_tokens(restaurant_item)} tokens")
print(f"  Total menu: ~{restaurant_tokens} tokens")
print(f"  Full context: ~{restaurant_tokens + 300} tokens (with prompt)\n")

# Legal/Visa business example (100 services)
legal_examples = [
    "• Tourist Visa Extension ($150) - 30-60 days [Requires: passport, photo, proof of funds]",
    "• Business Visa (KITAS) ($1,200) - 6 months [Requires: sponsor letter, work permit, medical]",
    "• Retirement Visa ($800) - 1 year [Requires: age 55+, pension proof, health insurance]",
    "• Social/Cultural Visa ($350) - 60 days [Requires: sponsor, purpose letter]",
    "• Visa Run Service ($200) - Same day [Requires: passport, return ticket]",
    "• Document Translation ($50/page) - 1-2 days [Requires: original document]",
    "• Company Registration ($2,500) - 2-4 weeks [Requires: business plan, capital proof]",
    "• Work Permit Application ($500) - 1-2 weeks [Requires: employment contract, qualifications]"
]

print("LEGAL/VISA BUSINESS:")
for service in legal_examples[:3]:
    print(f"  {service}")
    print(f"  Tokens: ~{estimate_tokens(service)}")

total_legal = sum(estimate_tokens(s) for s in legal_examples) * 12  # ~100 services
print(f"\n  Total for 100 services: ~{total_legal} tokens")
print(f"  Full context: ~{total_legal + 500} tokens (with legal disclaimers)\n")

# Token usage comparison
print("TOKEN USAGE COMPARISON (8K limit):")
print("─" * 50)
print(f"Restaurant (50 items):    {restaurant_tokens:4d} tokens ({restaurant_tokens/80:.0f}% of 8K)")
print(f"Restaurant (200 items):   {restaurant_tokens*4:4d} tokens ({restaurant_tokens*4/80:.0f}% of 8K)")
print(f"Legal (100 services):     {total_legal:4d} tokens ({total_legal/80:.0f}% of 8K)")
print(f"Legal (200 services):     {total_legal*2:4d} tokens ({total_legal*2/80:.0f}% of 8K)")
print("─" * 50)

# Detailed legal service token breakdown
print("\n\nDETAILED VISA SERVICE BREAKDOWN:")
print("Basic listing (name + price + requirements): ~25 tokens")
print("With full legal details: ~100-150 tokens per service")
print("\nExample with full details:")
visa_with_details = """
• Business Visa (KITAS) ($1,200) - 6 months processing time
  Requirements: Company sponsor letter, work permit approval, medical certificate, 
  police clearance, CV, diplomas, passport photos (6x), proof of accommodation
  
  Important: Must apply from outside Indonesia. Company must have foreign worker 
  allocation (RPTKA). Process includes immigration approval, work permit (IMTA), 
  limited stay permit (ITAS). Valid for 6 months, extendable up to 2 years.
  Subject to annual reporting requirements (LKPM).
"""
print(visa_with_details)
print(f"Tokens for detailed service: ~{estimate_tokens(visa_with_details)}")

print("\n\nRECOMMENDATION:")
print("1. For restaurants: Send full compact menu (no issue up to 200 items)")
print("2. For legal/visa: Send service list + load details on demand")
print("3. For complex businesses: Use category-based loading")
print("4. Consider different modes based on business type")