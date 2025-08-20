"""
Context formatting service to clearly separate context from conversation
"""
from typing import List, Dict, Optional
from enum import Enum

class ContextSection(Enum):
    """Types of context sections"""
    MENU_ITEMS = "menu_items"
    RESTAURANT_INFO = "restaurant_info"
    DIETARY_INFO = "dietary_info"
    CONVERSATION_HISTORY = "conversation_history"
    PREFERENCES = "preferences"
    INSTRUCTIONS = "instructions"
    PERSONALIZATION = "personalization"

class ContextFormatter:
    """Formats context clearly for AI understanding"""
    
    def __init__(self):
        self.section_markers = {
            ContextSection.MENU_ITEMS: "📋 AVAILABLE MENU ITEMS",
            ContextSection.RESTAURANT_INFO: "🏪 RESTAURANT INFORMATION",
            ContextSection.DIETARY_INFO: "🥗 DIETARY INFORMATION",
            ContextSection.CONVERSATION_HISTORY: "💬 PREVIOUS CONVERSATION",
            ContextSection.PREFERENCES: "⭐ CUSTOMER PREFERENCES",
            ContextSection.INSTRUCTIONS: "📌 INSTRUCTIONS",
            ContextSection.PERSONALIZATION: "👤 CUSTOMER INFORMATION"
        }
    
    def format_context(self, sections: Dict[ContextSection, str]) -> str:
        """Format multiple context sections with clear separation"""
        if not sections:
            return ""
        
        formatted_parts = []
        
        # Add clear context header
        formatted_parts.append("=== CONTEXT START ===")
        formatted_parts.append("(This is background information, not part of the conversation)")
        formatted_parts.append("")
        
        # Add each section with clear markers
        for section_type, content in sections.items():
            if content and content.strip():
                marker = self.section_markers.get(section_type, "📄 INFORMATION")
                formatted_parts.append(f"--- {marker} ---")
                formatted_parts.append(content)
                formatted_parts.append("")
        
        # Add clear context footer
        formatted_parts.append("=== CONTEXT END ===")
        formatted_parts.append("")
        
        return "\n".join(formatted_parts)
    
    def format_menu_items(self, items: List[Dict], show_descriptions: bool = False) -> str:
        """Format menu items clearly"""
        if not items:
            return "No specific items to display."
        
        formatted = []
        for item in items:
            name = item.get('name', item.get('title', 'Unknown'))
            price = item.get('price', '')
            category = item.get('category', '')
            
            # Basic format
            line = f"• {name}"
            if price:
                line += f" - {price}"
            if category and category != 'Unknown':
                line += f" [{category}]"
            
            # Add description if requested
            if show_descriptions and item.get('description'):
                line += f"\n  Description: {item['description'][:100]}"
            
            formatted.append(line)
        
        return "\n".join(formatted)
    
    def format_conversation_history(self, history: List[Dict]) -> str:
        """Format conversation history clearly"""
        if not history:
            return ""
        
        formatted = []
        for turn in history[-3:]:  # Last 3 turns only
            formatted.append(f"Customer: {turn.get('query', '')}")
            formatted.append(f"You: {turn.get('response', '')[:100]}...")
            formatted.append("")
        
        return "\n".join(formatted).strip()
    
    def format_dietary_info(self, dietary_items: Dict[str, List]) -> str:
        """Format dietary information clearly"""
        if not dietary_items:
            return ""
        
        formatted = []
        for restriction, items in dietary_items.items():
            if items:
                formatted.append(f"{restriction.title()} options:")
                for item in items[:5]:  # Limit to 5 items per category
                    formatted.append(f"  • {item['name']} - {item.get('price', '')}")
        
        return "\n".join(formatted)
    
    def format_prompt_with_context(self, 
                                  system_prompt: str,
                                  context_sections: Dict[ContextSection, str],
                                  customer_message: str,
                                  assistant_name: str = "Assistant") -> str:
        """Format complete prompt with clear separation"""
        parts = []
        
        # 1. System prompt (personality/role)
        parts.append(system_prompt)
        parts.append("")
        
        # 2. Context (clearly marked)
        if context_sections:
            context = self.format_context(context_sections)
            parts.append(context)
        
        # 3. Conversation (clearly marked)
        parts.append("=== CURRENT CONVERSATION ===")
        parts.append(f"Customer: {customer_message}")
        parts.append(f"{assistant_name}:")
        
        return "\n".join(parts)
    
    def create_clear_instructions(self, query_type: str, constraints: List[str] = None) -> str:
        """Create clear instructions for the AI"""
        instructions = []
        
        # Base instruction
        instructions.append("Important guidelines:")
        instructions.append("• Use ONLY the information provided in the context sections above")
        instructions.append("• The customer's message is what you need to respond to")
        instructions.append("• The context provides background information to help you respond accurately")
        
        # Query-specific instructions
        if query_type == "menu_query":
            instructions.append("• List only items from the AVAILABLE MENU ITEMS section")
            instructions.append("• If asked about items not in the context, politely say they're not available")
        elif query_type == "recommendation":
            instructions.append("• Recommend only from the items in the context")
            instructions.append("• Explain briefly why each recommendation suits the customer")
        elif query_type == "dietary":
            instructions.append("• Focus on the DIETARY INFORMATION section")
            instructions.append("• Be clear about allergens and dietary restrictions")
        
        # Add any additional constraints
        if constraints:
            for constraint in constraints:
                instructions.append(f"• {constraint}")
        
        return "\n".join(instructions)

# Singleton instance
context_formatter = ContextFormatter()