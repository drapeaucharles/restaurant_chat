#!/usr/bin/env python3
"""
Generate report from partial test results
"""

import json
import glob
from datetime import datetime
from comprehensive_customer_test import generate_report

def load_partial_results():
    """Load all temp files"""
    results = []
    files = glob.glob("/tmp/customer_*.json")
    
    print(f"Found {len(files)} customer test results")
    
    for f in files:
        try:
            with open(f, 'r') as file:
                result = json.load(file)
                results.append(result)
                print(f"  ✓ Loaded {result['customer']['name']}")
        except Exception as e:
            print(f"  ❌ Error loading {f}: {e}")
    
    return results

def main():
    print("📊 GENERATING PARTIAL TEST REPORT")
    print("="*60)
    
    # Load results
    results = load_partial_results()
    
    if not results:
        print("No results found!")
        return
    
    # Generate report
    report = generate_report(results)
    
    # Save full results
    output_file = f"partial_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Full results saved to: {output_file}")
    
    # Print summary
    print("\n📊 TEST SUMMARY (PARTIAL)")
    print("="*60)
    print(f"Total Customers Tested: {report['test_summary']['total_customers']} / 41")
    print(f"Total Messages: {report['test_summary']['total_messages']}")
    print(f"Success Rate: {report['technical_metrics']['success_rate']:.1f}%")
    print(f"Avg Response Length: {report['technical_metrics']['avg_response_length']:.0f} chars")
    print(f"Tool Usage Rate: {report['technical_metrics']['tool_usage_rate']:.1f}%")
    if report['technical_metrics']['context_maintenance_rate'] > 0:
        print(f"Context Maintenance: {report['technical_metrics']['context_maintenance_rate']:.1f}%")
    
    print("\n🍽️ DIETARY HANDLING")
    print(f"Customers with dietary needs: {report['dietary_performance']['total_dietary_customers']}")
    print(f"Handled correctly: {report['dietary_performance']['handled_correctly']}")
    if report['dietary_performance']['violations']:
        print(f"Violations found: {len(report['dietary_performance']['violations'])}")
        for v in report['dietary_performance']['violations'][:5]:
            print(f"  - {v}")
    
    print("\n🌍 LANGUAGE SUPPORT")
    if report['language_support']:
        for lang, count in report['language_support'].items():
            print(f"{lang.capitalize()}: {count} customers")
    else:
        print("No multilingual customers tested yet")
    
    print("\n😊 CUSTOMER SATISFACTION")
    print(f"Satisfied: {report['customer_satisfaction']['satisfied']}")
    print(f"Unsatisfied: {report['customer_satisfaction']['unsatisfied']}")
    print(f"Neutral: {report['customer_satisfaction']['neutral']}")
    
    print("\n📈 SCENARIO BREAKDOWN")
    sorted_scenarios = sorted(
        report['scenario_breakdown'].items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )[:10]
    
    for scenario, data in sorted_scenarios:
        print(f"{scenario}: {data['count']} customers, avg {data['avg_messages']:.1f} messages")
    
    # Show which profiles are still missing
    tested_names = {r['customer']['name'] for r in results}
    all_names = {
        "Sarah_General", "Mike_Hours", "Lisa_Location", "Tom_Ambiance", "Emma_Groups",
        "David_Newbie", "Rachel_Prices", "John_Payment", "Anna_Kids", "Chris_Quick",
        "Sophia_Appetizers", "Oliver_Pasta", "Mia_Seafood", "Lucas_Meat", "Ava_Desserts",
        "Noah_Wine", "Isabella_Specials", "Ethan_Curious", "Vegan_Victoria", "GF_George",
        "Allergic_Alice", "Dairy_Daniel", "Keto_Katherine", "Multi_Marcus", "Checking_Chelsea",
        "Birthday_Blake", "Business_Brianna", "Wedding_William", "LastMin_Laura", "Romantic_Ryan",
        "Unhappy_Uma", "Feedback_Frank", "Suggest_Sally", "French_Francois", "Spanish_Sofia",
        "Italian_Giovanni", "German_Greta", "Japanese_Yuki", "Confused_Carl", "Detailed_Diana",
        "Chatty_Charles"
    }
    
    missing = all_names - tested_names
    if missing:
        print(f"\n⏳ CUSTOMERS NOT YET TESTED ({len(missing)}):")
        for name in sorted(missing):
            print(f"  - {name}")

if __name__ == "__main__":
    main()