import React, { useState, useEffect, useRef } from 'react';
import { Business } from '../../types/business';
import { getBusinessConfig, getIconComponent } from '../../config/businessConfigs';
import { MdSend, MdPerson, MdSupportAgent } from 'react-icons/md';
import { v4 as uuidv4 } from 'uuid';

interface BusinessChatInterfaceProps {
  business: Business;
  clientId?: string;
  onClose?: () => void;
}

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

export const BusinessChatInterface: React.FC<BusinessChatInterfaceProps> = ({
  business,
  clientId = uuidv4(),
  onClose
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<null | HTMLDivElement>(null);
  
  const config = getBusinessConfig(business.business_type);
  const BusinessIcon = getIconComponent(config.icon);

  // Initial welcome message
  useEffect(() => {
    const welcomeMessage: Message = {
      id: uuidv4(),
      text: `Welcome to ${business.name}! ${config.chatContext}`,
      sender: 'bot',
      timestamp: new Date()
    };
    setMessages([welcomeMessage]);
  }, [business, config]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage: Message = {
      id: uuidv4(),
      text: inputText,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          restaurant_id: business.business_id, // Backend expects restaurant_id
          message: inputText,
          client_id: clientId
        })
      });

      const data = await response.json();
      
      const botMessage: Message = {
        id: uuidv4(),
        text: data.answer || 'I apologize, but I\'m having trouble processing your request. Please try again.',
        sender: 'bot',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: uuidv4(),
        text: 'I\'m sorry, I\'m having connection issues. Please try again later.',
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Get suggested questions based on business type
  const getSuggestedQuestions = () => {
    const suggestions: Record<string, string[]> = {
      restaurant: [
        "What's on your menu today?",
        "Do you have vegetarian options?",
        "What are your opening hours?",
        "Do you have any specials?"
      ],
      legal_visa: [
        "What visa services do you offer?",
        "How much does a work visa cost?",
        "What documents do I need?",
        "How long does the process take?"
      ],
      salon: [
        "What services do you offer?",
        "How much is a haircut?",
        "Do I need an appointment?",
        "What are your hours?"
      ],
      hotel: [
        "What rooms are available?",
        "What amenities do you have?",
        "How much per night?",
        "Do you have a pool?"
      ],
      repair: [
        "Can you fix my phone screen?",
        "How much for laptop repair?",
        "How long does repair take?",
        "Do you offer warranty?"
      ],
      medical: [
        "What services do you offer?",
        "Do you accept insurance?",
        "How do I book an appointment?",
        "What are your hours?"
      ],
      retail: [
        "What products do you have?",
        "Are there any promotions?",
        "What are your store hours?",
        "Do you offer delivery?"
      ]
    };

    return suggestions[business.business_type] || suggestions.restaurant;
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div 
        className="flex items-center justify-between p-4 border-b"
        style={{ backgroundColor: config.primaryColor }}
      >
        <div className="flex items-center gap-3 text-white">
          <BusinessIcon className="text-2xl" />
          <div>
            <h3 className="font-semibold">{business.name}</h3>
            <p className="text-sm opacity-90">{config.displayName}</p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-white hover:bg-white hover:bg-opacity-20 rounded-full p-2"
          >
            ✕
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`
                max-w-[70%] rounded-lg p-3 
                ${message.sender === 'user' 
                  ? 'bg-blue-500 text-white' 
                  : 'bg-gray-100 text-gray-800'
                }
              `}
            >
              <div className="flex items-start gap-2">
                {message.sender === 'bot' && (
                  <MdSupportAgent className="text-lg mt-1 flex-shrink-0" />
                )}
                <div>
                  <p className="whitespace-pre-wrap">{message.text}</p>
                  <p className={`text-xs mt-1 ${
                    message.sender === 'user' ? 'text-blue-100' : 'text-gray-500'
                  }`}>
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
                {message.sender === 'user' && (
                  <MdPerson className="text-lg mt-1 flex-shrink-0" />
                )}
              </div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-3">
              <div className="flex gap-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Questions (shown when no user messages) */}
      {messages.filter(m => m.sender === 'user').length === 0 && (
        <div className="px-4 pb-2">
          <p className="text-sm text-gray-500 mb-2">Suggested questions:</p>
          <div className="flex flex-wrap gap-2">
            {getSuggestedQuestions().map((question, idx) => (
              <button
                key={idx}
                onClick={() => setInputText(question)}
                className="text-sm px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700"
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={`Ask about our ${config.productLabel.toLowerCase()}...`}
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 text-black"
            style={{ focusRingColor: config.primaryColor }}
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={!inputText.trim() || isLoading}
            className={`
              px-4 py-2 rounded-lg text-white font-medium
              ${!inputText.trim() || isLoading 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'hover:opacity-90'
              }
            `}
            style={{ 
              backgroundColor: !inputText.trim() || isLoading 
                ? undefined 
                : config.primaryColor 
            }}
          >
            <MdSend className="text-xl" />
          </button>
        </div>
      </div>
    </div>
  );
};