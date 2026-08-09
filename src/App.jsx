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

const UT_KNOWLEDGE = {
  pricing: {
    text: "Our micro-cleaning services start at just ₹249. We handle the chores so you don't have to.",
    card: {
      type: 'pricing',
      title: "Sweep & Mop",
      price: "₹249",
      unit: "/room",
      action: "Book Service",
      icon: <Sparkles size={24} />
    },
    options: ["Monthly Plan", "Coverage Area", "Other Services"]
  },
  other_services: {
    text: "We offer specialized cleaning to keep every corner pristine:",
    options: ["Fan Cleaning (₹149)", "Bathroom (₹349)", "Car Cleaning (₹299)", "Go Back"]
  },
  coverage: {
    text: "Our verified professionals are active in key South Chennai communities.",
    card: {
      type: 'location',
      title: "Active Hubs",
      price: "OMR & ECR",
      unit: " Corridor",
      action: "Check My Pincode",
      icon: <MapPin size={24} />
    },
    options: ["Perungudi", "Thoraipakkam", "Kandanchavadi", "Go Back"]
  },
  subscription: {
    text: "Set it and forget it. A dedicated Guild team arrives automatically on schedule.",
    card: {
      type: 'subscription',
      title: "Recurrent Plan",
      price: "₹4,499",
      unit: "/mo",
      action: "Build My Plan",
      icon: <Calendar size={24} />
    },
    options: ["Trust & Safety", "Pricing"]
  },
  trust: {
    text: "Every Utservio professional is background-verified. We guarantee 100% service continuity with seamless replacements.",
    options: ["Monthly Plan", "Coverage Area"]
  },
  default: {
    text: "I'm the Utservio AI assistant! I can help you with pricing, coverage areas, or setting up a recurrent cleaning plan.",
    options: ["Pricing", "Coverage Area", "Monthly Plan", "Trust & Safety"]
  }
};

function App() {
  const [hasStarted, setHasStarted] = useState(false);
  const initialMessages = [
    {
      id: 1,
      sender: 'bot',
      text: "Hi there! Welcome to Utservio. How can I help you keep your home spotless today?",
      options: ["Pricing", "Coverage Area", "Monthly Plan", "Trust & Safety"]
    }
  ];

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

  const handleSend = (text) => {
    if (!text.trim()) return;

    const newUserMsg = { id: Date.now(), sender: 'user', text };
    setMessages(prev => [...prev, newUserMsg]);
    setInputValue('');
    setIsTyping(true);

    setTimeout(() => {
      let botResponse = UT_KNOWLEDGE.default;
      const lowerText = text.toLowerCase();

      if (lowerText.includes('price') || lowerText.includes('cost') || lowerText.includes('₹') || lowerText.includes('sweep')) {
        botResponse = UT_KNOWLEDGE.pricing;
      } else if (lowerText.includes('other') || lowerText.includes('fan') || lowerText.includes('bath') || lowerText.includes('car')) {
        botResponse = UT_KNOWLEDGE.other_services;
      } else if (lowerText.includes('cover') || lowerText.includes('area') || lowerText.includes('chennai') || lowerText.includes('perungudi') || lowerText.includes('thoraipakkam')) {
        botResponse = UT_KNOWLEDGE.coverage;
      } else if (lowerText.includes('month') || lowerText.includes('subscript') || lowerText.includes('plan') || lowerText.includes('recurrent')) {
        botResponse = UT_KNOWLEDGE.subscription;
      } else if (lowerText.includes('trust') || lowerText.includes('safe') || lowerText.includes('verify') || lowerText.includes('who')) {
        botResponse = UT_KNOWLEDGE.trust;
      }

      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'bot',
        text: botResponse.text,
        card: botResponse.card,
        options: botResponse.options
      }]);
      setIsTyping(false);
    }, 1500); // More realistic thinking delay
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
