"""
Dynamic response length management based on context and query type
"""
from enum import Enum
from typing import Dict

class ResponseLength(Enum):
    """Response length categories"""
    MINIMAL = "minimal"      # 50-100 tokens (Yes/No, prices, hours)
    SHORT = "short"          # 100-150 tokens (Simple queries)
    MEDIUM = "medium"        # 150-250 tokens (Most queries)
    DETAILED = "detailed"    # 250-350 tokens (Menu overviews)
    COMPREHENSIVE = "comprehensive"  # 350-500 tokens (Special requests)

class ResponseLengthManager:
    """Manages appropriate response length based on context"""
    
    @staticmethod
    def determine_length(query: str, query_type: str) -> Dict:
        """Determine appropriate response length and parameters"""
        
        query_lower = query.lower()
        
        # Quick answers (minimal reading)
        if any(word in query_lower for word in ['price', 'cost', 'how much', 'open', 'close', 'hours']):
            return {
                "length": ResponseLength.MINIMAL,
                "max_tokens": 100,
                "instruction": "Answer directly and concisely."
            }
        
        # Yes/No questions
        if query_lower.startswith(('do you', 'is there', 'can i', 'are you')):
            return {
                "length": ResponseLength.SHORT,
                "max_tokens": 150,
                "instruction": "Answer the question directly, then add one helpful detail."
            }
        
        # Specific item queries
        if any(word in query_lower for word in ['tell me about', 'describe', 'what is']):
            return {
                "length": ResponseLength.MEDIUM,
                "max_tokens": 200,
                "instruction": "Describe the item clearly but keep it conversational."
            }
        
        # Overview requests
        if any(word in query_lower for word in ['show me', 'what do you have', 'menu', 'options']):
            return {
                "length": ResponseLength.DETAILED,
                "max_tokens": 300,
                "instruction": "List items clearly. Offer to provide more details if needed."
            }
        
        # Special dietary/comprehensive requests
        if any(word in query_lower for word in ['allergies', 'special', 'event', 'party', 'recommendation']):
            return {
                "length": ResponseLength.COMPREHENSIVE,
                "max_tokens": 400,
                "instruction": "Be thorough but organized. Use bullet points if listing multiple items."
            }
        
        # Default
        return {
            "length": ResponseLength.MEDIUM,
            "max_tokens": 200,
            "instruction": "Be helpful but concise."
        }
    
    @staticmethod
    def format_response_instruction(length_config: Dict) -> str:
        """Create instruction for AI based on desired length"""
        
        base_instruction = length_config["instruction"]
        
        # Add length-specific formatting hints
        if length_config["length"] == ResponseLength.MINIMAL:
            base_instruction += " No need for pleasantries."
        elif length_config["length"] == ResponseLength.COMPREHENSIVE:
            base_instruction += " Use clear sections or bullet points for readability."
        
        return base_instruction

# Usage example in prompts:
"""
length_config = ResponseLengthManager.determine_length(query, query_type)
prompt += f"\n{length_config['instruction']}"
params['max_tokens'] = length_config['max_tokens']
"""