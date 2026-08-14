import { useState, useRef, useEffect } from 'react';
import { 
  Send, RotateCcw, MessageSquare, MapPin, 
  CreditCard, ShieldCheck, Sparkles, ChevronRight,
  Camera
} from 'lucide-react';
import './App.css';

const BotIcon = () => {
  return <MessageSquare size={16} />;
};

const getIconForOption = (text) => {
  const lower = text.toLowerCase();
  if (lower.includes('price') || lower.includes('plan')) return <CreditCard size={16} />;
  if (lower.includes('cover') || lower.includes('area') || lower.includes('perungudi')) return <MapPin size={16} />;
  if (lower.includes('trust') || lower.includes('safe')) return <ShieldCheck size={16} />;
  if (lower.includes('other') || lower.includes('fan')) return <Sparkles size={16} />;
  return <MessageSquare size={16} />;
};

const initialMessages = [
  {
    id: 1,
    sender: 'bot',
    text: "Hi! Welcome to UTservio. How can I help you today?",
    type: "options",
    options: ["Book a Service", "Explore Services", "Check Pricing", "Service Areas"]
  }
];

function App() {
  const [hasStarted, setHasStarted] = useState(false);

  const [sessionId] = useState(() => {
    const saved = localStorage.getItem('utservio_session_id');
    if (saved) return saved;
    const newSession = crypto.randomUUID();
    localStorage.setItem('utservio_session_id', newSession);
    return newSession;
  });
  const [messages, setMessages] = useState(initialMessages);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatMessagesRef = useRef(null);
  const fileInputRef = useRef(null);

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

  useEffect(() => {
    // Load history on mount
    const fetchHistory = async () => {
      try {
        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${baseUrl}/api/chat/${sessionId}/history`);
        if (response.ok) {
          const data = await response.json();
          if (data.messages && data.messages.length > 0) {
            const restoredMessages = data.messages.map((msg, idx) => ({
              id: Date.now() + idx,
              sender: msg.role === 'assistant' ? 'bot' : 'user',
              text: msg.content
            }));
            setMessages([...initialMessages, ...restoredMessages]);
          }
        }
      } catch (err) {
        console.error("Failed to load chat history:", err);
      }
    };
    fetchHistory();
  }, [sessionId]);

  const handleReset = () => {
    setMessages(initialMessages);
    setInputValue('');
    const newSession = crypto.randomUUID();
    localStorage.setItem('utservio_session_id', newSession);
    window.location.reload();
  };

  const handleImageUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result;
        const newUserMsg = { id: Date.now(), sender: 'user', text: '', image: base64 };
        setMessages(prev => [...prev, newUserMsg]);
        handleSend('Analyze this image to estimate cleaning costs.', base64);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSend = async (text, imageData = null) => {
    if (!text.trim() && !imageData) return;

    if (!imageData) {
      const newUserMsg = { id: Date.now(), sender: 'user', text };
      setMessages(prev => [...prev, newUserMsg]);
    }
    
    setInputValue('');
    setIsTyping(true);

    const promptText = imageData ? `[User uploaded an image for analysis]. ${text}` : text;

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: promptText
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      let aiText = data.message || "Sorry, I'm having trouble connecting right now.";

      const botMsgId = Date.now() + 1;
      setMessages(prev => [...prev, {
        id: botMsgId,
        sender: 'bot',
        text: aiText,
        type: data.type || 'text',
        options: data.options || null,
        data: data.data || null
      }]);
      setIsTyping(false);

    } catch (error) {
      console.error("Chat error:", error);
      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'bot',
        text: "I'm sorry, I'm having trouble reaching the Utservio servers right now. Please try again later.",
        type: 'error'
      }]);
    }
  };

  const formatTime = () => {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="app-container">
      <div className="chat-widget">
        
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

        <div className="chat-bg-orb-1"></div>
        <div className="chat-bg-orb-2"></div>
        
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

        <div className="chat-messages" ref={chatMessagesRef}>
          {messages.map((msg) => {
            let formattedText = msg.text.replace(/\[Source: (.*?)\]/g, '<span class="citation">Source: $1</span>');
            // Ensure newlines render correctly if AI outputs plain text \n
            formattedText = formattedText.replace(/\n/g, '<br/>');
            
            return (
              <div key={msg.id} className={`message-wrapper ${msg.sender}`}>
                <div className="message-bubble">
                  {msg.sender === 'bot' && <div className="bot-icon"><BotIcon /></div>}
                  {msg.image && <img src={msg.image} alt="Upload" className="uploaded-image" style={{ maxWidth: '100%', borderRadius: '8px' }} />}
                  {msg.text && <p dangerouslySetInnerHTML={{ __html: formattedText }}></p>}
                  
                  {/* Service Cards Component */}
                  {msg.type === 'service_cards' && msg.data?.services && (
                    <div className="services-grid">
                      {msg.data.services.map((svc) => (
                        <div key={svc.id} className="rich-card premium-service-card">
                          <h4>{svc.name}</h4>
                          <p className="service-desc">{svc.description || "Premium home service"}</p>
                          <div className="service-price">
                            <span className="price-label">
                              {svc.pricing_type === 'starting_from' ? 'Starts at ' : ''}
                            </span>
                            <span className="price-val">₹{svc.price_amount}</span>
                            <span className="price-unit"> / {svc.price_unit}</span>
                          </div>
                          <button 
                            className="select-btn card-action" 
                            onClick={() => handleSend(svc.name)}
                          >
                            Select
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Price Detail Card Component */}
                  {msg.type === 'price_card' && msg.data && (
                    <div className="rich-card price-details-card holographic">
                      <h3>{msg.data.service_name}</h3>
                      <div className="price-display">
                        <span className="price-amount">₹{msg.data.price_amount}</span>
                        <span className="price-unit">/ {msg.data.price_unit}</span>
                      </div>
                      <p className="price-type">
                        Type: <strong>{msg.data.pricing_type === 'starting_from' ? 'Starting From' : 'Fixed'}</strong>
                      </p>
                      <p className="location-info">
                        Location: <strong>{msg.data.location_name}</strong>
                      </p>
                      <div className="provenance-tag">
                        <span>✓ Verified UTservio Data</span>
                      </div>
                    </div>
                  )}

                  {/* Date Picker Component */}
                  {msg.type === 'date_picker' && (
                    <div className="date-picker-container">
                      <div className="quick-replies" style={{ marginTop: 0 }}>
                        <button className="quick-reply-btn" onClick={() => handleSend('Today')}>Today</button>
                        <button className="quick-reply-btn" onClick={() => handleSend('Tomorrow')}>Tomorrow</button>
                      </div>
                      <div className="custom-date-picker">
                        <label htmlFor="custom-date">Or choose date: </label>
                        <input 
                          type="date" 
                          id="custom-date"
                          className="date-input"
                          min={new Date().toISOString().split('T')[0]}
                          onChange={(e) => {
                            if (e.target.value) {
                              handleSend(e.target.value);
                            }
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Confirmation / Booking Summary Component */}
                  {msg.type === 'confirmation_card' && msg.data && (
                    <div className={`rich-card confirmation-card ${msg.data.status.toLowerCase()}`}>
                      <div className="confirmation-header">
                        <span className={`status-badge ${msg.data.status.toLowerCase()}`}>
                          {msg.data.status}
                        </span>
                        {msg.data.booking_id && (
                          <span className="booking-id">ID: {msg.data.booking_id}</span>
                        )}
                      </div>
                      <div className="confirmation-details">
                        <p>Service: <strong>{msg.data.service_name}</strong></p>
                        <p>Location: <strong>{msg.data.location_name}</strong></p>
                        <p>Date: <strong>{msg.data.date}</strong></p>
                        <p>Time: <strong>{msg.data.time_slot}</strong></p>
                        <p>Price: <strong>
                          {msg.data.pricing_type === 'starting_from' ? 'Starts at ' : ''}
                          ₹{msg.data.price_amount} / {msg.data.price_unit}
                        </strong></p>
                      </div>
                    </div>
                  )}

                  {/* Options Chips / Quick Replies */}
                  {msg.options && msg.sender === 'bot' && (
                    <div className="quick-replies">
                      {msg.options.map((opt, idx) => (
                        <button 
                          key={idx} 
                          className="quick-reply-btn"
                          onClick={() => handleSend(opt)}
                          style={{ animationDelay: `${idx * 0.05}s` }}
                        >
                          {getIconForOption(opt)} {opt}
                        </button>
                      ))}
                    </div>
                  )}
                  <div className="message-time">
                    {msg.sender === 'bot' ? 'Utservio AI' : 'You'} • {formatTime()}
                  </div>
                </div>
              </div>
            );
          })}
          
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
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept="image/*"
              onChange={handleImageUpload}
            />
            <button 
              type="button" 
              className="camera-btn" 
              onClick={() => fileInputRef.current?.click()}
              disabled={isTyping || !hasStarted}
              style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.7)', cursor: 'pointer', padding: '8px' }}
            >
              <Camera size={20} />
            </button>
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
