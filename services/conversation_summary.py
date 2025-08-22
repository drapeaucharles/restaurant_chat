"""
Conversation summary service for long-term memory
Summarizes conversations for better context retention
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConversationSummaryService:
    """Service for creating and managing conversation summaries"""
    
    def __init__(self):
        self.summary_cache = {}  # In-memory cache
    
    def create_conversation_summary(
        self,
        messages: List[Dict[str, Any]],
        business_type: str = "restaurant"
    ) -> Dict[str, Any]:
        """Create a summary of a conversation"""
        summary = {
            'message_count': len(messages),
            'topics_discussed': [],
            'items_mentioned': [],
            'actions_requested': [],
            'questions_asked': [],
            'sentiment': 'neutral',
            'key_points': []
        }
        
        if not messages:
            return summary
        
        # Analyze messages
        for msg in messages:
            if msg.get('sender_type') == 'client':
                message_text = msg.get('message', '').lower()
                
                # Extract topics
                if any(word in message_text for word in ['menu', 'price', 'cost']):
                    summary['topics_discussed'].append('pricing')
                if any(word in message_text for word in ['deliver', 'pickup', 'takeout']):
                    summary['topics_discussed'].append('service_options')
                if any(word in message_text for word in ['hour', 'open', 'close', 'time']):
                    summary['topics_discussed'].append('hours')
                if any(word in message_text for word in ['allerg', 'diet', 'vegan', 'gluten']):
                    summary['topics_discussed'].append('dietary')
                
                # Extract questions
                if '?' in msg.get('message', ''):
                    summary['questions_asked'].append(msg.get('message', ''))
                
                # Extract actions
                if any(word in message_text for word in ['order', 'book', 'reserve']):
                    summary['actions_requested'].append('ordering')
                if any(word in message_text for word in ['recommend', 'suggest', 'what should']):
                    summary['actions_requested'].append('recommendation')
                
                # Simple sentiment analysis
                positive_words = ['love', 'great', 'excellent', 'amazing', 'perfect', 'wonderful']
                negative_words = ['bad', 'terrible', 'awful', 'disgusting', 'horrible', 'worst']
                
                pos_count = sum(1 for word in positive_words if word in message_text)
                neg_count = sum(1 for word in negative_words if word in message_text)
                
                if pos_count > neg_count:
                    summary['sentiment'] = 'positive'
                elif neg_count > pos_count:
                    summary['sentiment'] = 'negative'
            
            elif msg.get('sender_type') in ['ai', 'restaurant']:
                # Extract items mentioned by AI
                ai_message = msg.get('message', '')
                # Look for menu items (basic pattern matching)
                if business_type == 'restaurant':
                    # Look for capitalized words that might be dish names
                    import re
                    potential_items = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', ai_message)
                    summary['items_mentioned'].extend(potential_items[:5])  # Limit to 5
        
        # Remove duplicates
        summary['topics_discussed'] = list(set(summary['topics_discussed']))
        summary['items_mentioned'] = list(set(summary['items_mentioned']))
        summary['actions_requested'] = list(set(summary['actions_requested']))
        
        # Create key points
        if summary['topics_discussed']:
            summary['key_points'].append(f"Discussed: {', '.join(summary['topics_discussed'][:3])}")
        if summary['actions_requested']:
            summary['key_points'].append(f"Requested: {', '.join(summary['actions_requested'])}")
        if summary['sentiment'] != 'neutral':
            summary['key_points'].append(f"Customer sentiment: {summary['sentiment']}")
        
        return summary
    
    def save_conversation_summary(
        self,
        db: Session,
        client_id: str,
        business_id: str,
        summary: Dict[str, Any]
    ):
        """Save conversation summary to database"""
        try:
            # Create table if not exists
            create_table = text("""
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                    client_id UUID,
                    business_id VARCHAR(255),
                    summary JSONB,
                    conversation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_summaries_client_business 
                ON conversation_summaries(client_id, business_id);
            """)
            db.execute(create_table)
            db.commit()
            
            # Insert summary
            insert_query = text("""
                INSERT INTO conversation_summaries 
                (client_id, business_id, summary)
                VALUES (:client_id::uuid, :business_id, :summary)
            """)
            
            db.execute(insert_query, {
                "client_id": client_id,
                "business_id": business_id,
                "summary": json.dumps(summary)
            })
            db.commit()
            
            # Update cache
            cache_key = f"{client_id}:{business_id}"
            if cache_key not in self.summary_cache:
                self.summary_cache[cache_key] = []
            self.summary_cache[cache_key].append(summary)
            
        except Exception as e:
            logger.error(f"Error saving conversation summary: {str(e)}")
            db.rollback()
    
    def get_recent_summaries(
        self,
        db: Session,
        client_id: str,
        business_id: str,
        days: int = 30,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recent conversation summaries"""
        # Check cache first
        cache_key = f"{client_id}:{business_id}"
        if cache_key in self.summary_cache:
            return self.summary_cache[cache_key][-limit:]
        
        try:
            query = text("""
                SELECT summary, conversation_date
                FROM conversation_summaries
                WHERE client_id = :client_id::uuid
                AND business_id = :business_id
                AND conversation_date > CURRENT_TIMESTAMP - INTERVAL :days DAY
                ORDER BY conversation_date DESC
                LIMIT :limit
            """)
            
            results = db.execute(query, {
                "client_id": client_id,
                "business_id": business_id,
                "days": f"{days} days",
                "limit": limit
            }).fetchall()
            
            summaries = []
            for row in results:
                summary_data = row[0]
                summary_data['date'] = row[1].isoformat() if row[1] else None
                summaries.append(summary_data)
            
            # Cache results
            self.summary_cache[cache_key] = summaries
            
            return summaries
            
        except Exception as e:
            logger.error(f"Error getting conversation summaries: {str(e)}")
            return []
    
    def get_conversation_history_context(
        self,
        db: Session,
        client_id: str,
        business_id: str
    ) -> str:
        """Get conversation history context for AI"""
        summaries = self.get_recent_summaries(db, client_id, business_id)
        
        if not summaries:
            return ""
        
        context_parts = []
        
        # Aggregate information from summaries
        all_topics = []
        all_items = []
        all_actions = []
        sentiment_counts = defaultdict(int)
        
        for summary in summaries:
            all_topics.extend(summary.get('topics_discussed', []))
            all_items.extend(summary.get('items_mentioned', []))
            all_actions.extend(summary.get('actions_requested', []))
            sentiment_counts[summary.get('sentiment', 'neutral')] += 1
        
        # Count frequencies
        topic_counts = defaultdict(int)
        for topic in all_topics:
            topic_counts[topic] += 1
        
        item_counts = defaultdict(int)
        for item in all_items:
            item_counts[item] += 1
        
        # Build context
        if len(summaries) > 1:
            context_parts.append(f"Previous {len(summaries)} conversations")
        
        # Most discussed topics
        if topic_counts:
            top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            topics_str = ", ".join([t[0] for t in top_topics])
            context_parts.append(f"Often discusses: {topics_str}")
        
        # Frequently mentioned items
        if item_counts:
            top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            if top_items:
                items_str = ", ".join([i[0] for i in top_items if i[1] > 1])
                if items_str:
                    context_parts.append(f"Previously interested in: {items_str}")
        
        # Overall sentiment
        if sentiment_counts:
            dominant_sentiment = max(sentiment_counts.items(), key=lambda x: x[1])[0]
            if dominant_sentiment != 'neutral':
                context_parts.append(f"Generally {dominant_sentiment} interactions")
        
        return " | ".join(context_parts) if context_parts else ""
    
    def should_summarize_conversation(
        self,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """Determine if a conversation should be summarized"""
        # Summarize if:
        # - More than 5 messages
        # - Conversation lasted more than 5 minutes
        # - Customer asked questions or made requests
        
        if len(messages) < 5:
            return False
        
        has_questions = any(
            '?' in msg.get('message', '') 
            for msg in messages 
            if msg.get('sender_type') == 'client'
        )
        
        has_requests = any(
            any(word in msg.get('message', '').lower() for word in ['order', 'book', 'recommend', 'suggest'])
            for msg in messages 
            if msg.get('sender_type') == 'client'
        )
        
        return has_questions or has_requests or len(messages) > 10
    
    def merge_summaries(
        self,
        summaries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge multiple summaries into one overview"""
        merged = {
            'total_conversations': len(summaries),
            'total_messages': sum(s.get('message_count', 0) for s in summaries),
            'all_topics': [],
            'all_items': [],
            'all_actions': [],
            'overall_sentiment': 'neutral',
            'key_insights': []
        }
        
        # Aggregate data
        sentiment_scores = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for summary in summaries:
            merged['all_topics'].extend(summary.get('topics_discussed', []))
            merged['all_items'].extend(summary.get('items_mentioned', []))
            merged['all_actions'].extend(summary.get('actions_requested', []))
            sentiment_scores[summary.get('sentiment', 'neutral')] += 1
        
        # Determine overall sentiment
        if sentiment_scores['positive'] > sentiment_scores['negative']:
            merged['overall_sentiment'] = 'positive'
        elif sentiment_scores['negative'] > sentiment_scores['positive']:
            merged['overall_sentiment'] = 'negative'
        
        # Count frequencies for insights
        topic_counts = defaultdict(int)
        for topic in merged['all_topics']:
            topic_counts[topic] += 1
        
        # Generate insights
        if topic_counts:
            most_common = max(topic_counts.items(), key=lambda x: x[1])
            merged['key_insights'].append(f"Most discussed: {most_common[0]} ({most_common[1]} times)")
        
        if merged['overall_sentiment'] != 'neutral':
            merged['key_insights'].append(f"Customer is generally {merged['overall_sentiment']}")
        
        return merged


# Global instance
conversation_summary = ConversationSummaryService()