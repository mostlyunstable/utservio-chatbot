import { useState, useRef, useEffect } from 'react';
import { 
  Send, RotateCcw, MessageSquare, MapPin, 
  CreditCard, ShieldCheck, Sparkles, Calendar, ChevronRight 
} from 'lucide-react';
import './App.css';

const getIconForOption = (text) => {
  const lower = text.toLowerCase();
  if (lower.includes('price') || lower.includes('plan')) return <CreditCard size={16} />;
  if (lower.includes('cover') || lower.includes('area') || lower.includes('perungudi')) return <MapPin size={16} />;
  if (lower.includes('trust') || lower.includes('safe')) return <ShieldCheck size={16} />;
  if (lower.includes('other') || lower.includes('fan')) return <Sparkles size={16} />;
  return <MessageSquare size={16} />;
};

const SYSTEM_PROMPT = `
You are the Utservio AI assistant. You help customers with pricing, coverage, and recurrent subscriptions for home cleaning services in Chennai. 
Keep your answers very brief, friendly, and highly professional. Never invent prices or services.
Use the following knowledge base to answer questions:
1. Pricing: Micro-cleaning starts at ₹249. Fan cleaning from ₹149, sweep & mop from ₹249 per room, bathroom from ₹349, car from ₹299.
2. Coverage: Perungudi, Thoraipakkam, Kandanchavadi, Sholinganallur, Karapakkam, OMR and ECR corridors.
3. Subscription: Recurrent daily plans start at ₹4,499/month for sweep, mop, dust, and bathroom cleaning. Dedicated rotating team, zero no-shows.
4. Trust: All pros are background verified.

If a user asks a complex question, do your best to answer it helpfully based on this knowledge. Do not format your response with markdown headers, just simple paragraphs.
`;

function App() {
  const [hasStarted, setHasStarted] = useState(false);
  const initialMessages = [
    {
      id: 1,
      sender: 'bot',
      text: "Hi there! Welcome to Utservio. I'm your AI assistant—how can I help you keep your home spotless today?",
      options: ["Pricing", "Coverage Area", "Monthly Plan", "Trust & Safety"]
    }
  ];

  const [chatHistory, setChatHistory] = useState([
    { role: 'system', content: SYSTEM_PROMPT }
  ]);
  const [messages, setMessages] = useState(initialMessages);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatMessagesRef = useRef(null);

  const scrollToBottom = () => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTo({
        top: chatMessagesRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  };

  useEffect(() => {
    if (hasStarted) {
      scrollToBottom();
    }
  }, [messages, isTyping, hasStarted]);

  const handleReset = () => {
    setMessages(initialMessages);
    setInputValue('');
  };

  const handleSend = async (text) => {
    if (!text.trim()) return;

    const newUserMsg = { id: Date.now(), sender: 'user', text };
    setMessages(prev => [...prev, newUserMsg]);
    setInputValue('');
    setIsTyping(true);

    const newHistory = [...chatHistory, { role: 'user', content: text }];
    setChatHistory(newHistory);

    try {
      // The proxy expects a single string input, so we format the history
      const promptString = newHistory.map(msg => 
        `${msg.role === 'system' ? 'System Instructions' : msg.role === 'assistant' ? 'Assistant' : 'User'}: ${msg.content}`
      ).join('\n') + '\nAssistant: ';

      const response = await fetch('/api/llm', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${import.meta.env.VITE_LLM_API_KEY}`
        },
        body: JSON.stringify({
          input: promptString
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      
      // Parse the custom proxy response format
      const messageObj = data.output?.find(o => o.type === 'message');
      const aiText = messageObj?.content?.[0]?.text || "Sorry, I'm having trouble connecting right now.";

      setChatHistory([...newHistory, { role: 'assistant', content: aiText }]);
      
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'bot',
        text: aiText
      }]);
    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'bot',
        text: "I'm sorry, I'm having trouble reaching the Utservio servers right now. Please try again later."
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  const formatTime = () => {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="app-container">
      <div className="chat-widget">
        
        {/* Welcome Screen Overlay */}
        <div className={`welcome-overlay ${hasStarted ? 'hidden' : ''}`}>
          <div className="welcome-logo">
            <img src="https://utservio.com/images/op-1/u-logo.png" alt="Utservio Logo" style={{ width: '50%', height: '50%', objectFit: 'contain', filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))' }} />
          </div>
          <h1>Utservio AI</h1>
          <p>Your premium home cleaning assistant</p>
          <button className="start-chat-btn" onClick={() => setHasStarted(true)}>
            Start Chat <ChevronRight size={20} />
          </button>
        </div>

        {/* Dynamic Background Orbs */}
        <div className="chat-bg-orb-1"></div>
        <div className="chat-bg-orb-2"></div>
        
        {/* Header */}
        <div className="chat-header">
          <div className="header-left">
            <div className="avatar">
              <img src="https://utservio.com/images/op-1/u-logo.png" alt="Utservio Logo" style={{ width: '60%', height: '60%', objectFit: 'contain', filter: 'drop-shadow(0 2px 2px rgba(0,0,0,0.2))' }} />
            </div>
            <div className="header-info">
              <h2>Utservio Support</h2>
              <p><span className="status-dot"></span> AI Assistant Online</p>
            </div>
          </div>
          <button onClick={handleReset} className="reset-btn" title="Restart Chat">
            <RotateCcw size={20} />
          </button>
        </div>

        {/* Chat Area */}
        <div className="chat-messages" ref={chatMessagesRef}>
          {messages.map((msg) => (
            <div key={msg.id} className={`message-wrapper ${msg.sender}`}>
              <div className="message-bubble">
                {msg.text}
              </div>
              
              {/* Stunning Glass Ticket Card */}
              {msg.card && (
                <div className="rich-card">
                  <div className="rich-card-header">
                    <div className="rich-card-icon">{msg.card.icon}</div>
                    <div className="rich-card-badge">Verified</div>
                  </div>
                  <div>
                    <div className="rich-card-title">{msg.card.title}</div>
                    <div className="rich-card-price">
                      {msg.card.price} <span>{msg.card.unit}</span>
                    </div>
                  </div>
                  <button className="rich-card-btn" onClick={() => handleSend(msg.card.action)}>
                    {msg.card.action} <ChevronRight size={16} />
                  </button>
                </div>
              )}

              <div className="message-time">
                {msg.sender === 'bot' ? 'Utservio AI' : 'You'} • {formatTime()}
              </div>
              
              {/* Animated Quick Replies */}
              {msg.options && msg.sender === 'bot' && (
                <div className="quick-replies">
                  {msg.options.map((opt, idx) => (
                    <button 
                      key={idx} 
                      className="quick-reply-btn"
                      style={{ animationDelay: `${idx * 0.1}s` }}
                      onClick={() => handleSend(opt)}
                    >
                      {getIconForOption(opt)} {opt}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          
          {isTyping && (
            <div className="message-wrapper bot">
              <div className="message-bubble typing-indicator">
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="chat-input-container">
          <form 
            className="input-wrapper"
            onSubmit={(e) => {
              e.preventDefault();
              handleSend(inputValue);
            }}
          >
            <input 
              type="text" 
              className="chat-input"
              placeholder="Message Utservio AI..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={isTyping || !hasStarted}
            />
            <button 
              type="submit" 
              className="send-btn" 
              disabled={!inputValue.trim() || isTyping || !hasStarted}
            >
              <Send size={20} className="send-icon" />
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}

export default App;
