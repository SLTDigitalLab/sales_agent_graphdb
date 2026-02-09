import React, { useState, useRef, useEffect } from 'react';
import { Send, Trash2, Bot, User, Loader2, AlertCircle, Plus, X, LogOut } from 'lucide-react';
import SEO from '../components/SEO';
import ProductCanvas from '../components/ProductCanvas';
import { useAuth } from '../context/AuthContext'; // [NEW IMPORT]

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function Chat() {
  const { logout, token } = useAuth(); // [CONNECT TO AUTH]
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const [error, setError] = useState(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [inlineFormStates, setInlineFormStates] = useState({});

  const [canvasData, setCanvasData] = useState(null);
  const [canvasLoading, setCanvasLoading] = useState(false);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchProductDetails = async (productName) => {
    if (!productName) return;

    setCanvasLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/products/search?query=${encodeURIComponent(productName)}`, {
        headers: { 'Authorization': `Bearer ${token}` } // [AUTH HEADER]
      });

      if (!response.ok) {
        console.log(`Product '${productName}' not found in DB.`);
        setCanvasData(null);
        return;
      }

      const data = await response.json();
      setCanvasData(data);
    } catch (err) {
      console.error("Error fetching product details:", err);
    } finally {
      setCanvasLoading(false);
    }
  };

  useEffect(() => {
    if (messages.length === 0) return;
    const lastMsg = messages[messages.length - 1];

    if (lastMsg.type === 'assistant') {
      const text = lastMsg.content;
      const linkMatch = text.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        const firstProductName = linkMatch[1];
        fetchProductDetails(firstProductName);
      }
      else if (!text.includes("Rs.")) {
        setCanvasData(null);
      }
    }
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();

    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);
    setCanvasLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` // [AUTH HEADER]
        },
        body: JSON.stringify({
          session_id: sessionId,
          question: userMessage.content
        })
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);

      const data = await response.json();

      const botMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: data.answer,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      console.error('Error sending message:', err);
      setError(err.message || 'Failed to get response from server');

      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setCanvasLoading(false);
      inputRef.current?.focus();
    }
  };

  const confirmClearHistory = async () => {
    setShowClearConfirm(false);
    setCanvasData(null);
    try {
      await fetch(`${API_BASE_URL}/v1/chat/clear`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` // [AUTH HEADER]
        },
        body: JSON.stringify({ session_id: sessionId })
      });

      setMessages([]);
      setError(null);
    } catch (err) {
      console.error('Error clearing history:', err);
      setError('Failed to clear chat history');
    }
  };

  const InlineOrderForm = ({ requestId, initialMessage, savedState, onOrderSuccess, onSubmitError, prefillProduct }) => {
    const [items, setItems] = useState([{ productId: prefillProduct || '', quantity: 1 }]);
    const [customerDetails, setCustomerDetails] = useState({ name: '', email: '', phone: '', address: '', notes: '' });
    const [formError, setFormError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submissionStatus, setSubmissionStatus] = useState(savedState?.submissionStatus || '');
    const [products, setProducts] = useState([]);
    const [loadingProducts, setLoadingProducts] = useState(true);

    useEffect(() => {
      const fetchProductsForForm = async () => {
        try {
          const response = await fetch(`${API_BASE_URL}/db/graph/products-for-order-form`, {
            headers: { 'Authorization': `Bearer ${token}` } // [AUTH HEADER]
          });
          if (!response.ok) throw new Error(`Failed to fetch products: ${response.status}`);
          const data = await response.json();
          setProducts(data.products);
          setLoadingProducts(false);
        } catch (err) {
          console.error("Error fetching products for order form:", err);
          setLoadingProducts(false);
          setFormError(`Failed to load products.`);
        }
      };
      fetchProductsForForm();
    }, []);

    const handleSubmit = async () => {
      setIsSubmitting(true);
      try {
        const response = await fetch(`${API_BASE_URL}/email/order-request`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}` // [AUTH HEADER]
          },
          body: JSON.stringify({
            items: items.map(item => ({ product_name: item.productId, quantity: item.quantity })),
            customer_name: customerDetails.name,
            customer_email: customerDetails.email,
            customer_phone: customerDetails.phone,
            customer_address: customerDetails.address,
            notes: customerDetails.notes
          })
        });

        if (!response.ok) throw new Error('Failed to submit order');
        setSubmissionStatus('success');
        if (onOrderSuccess) onOrderSuccess(requestId);
      } catch (err) {
        setFormError(err.message);
      } finally {
        setIsSubmitting(false);
      }
    };

    if (submissionStatus === 'success') {
      return (
        <div className="mt-3 p-4 bg-green-50 border border-green-200 rounded-xl text-green-800 text-sm">
          <strong>Order Request Sent!</strong> We will contact you shortly.
        </div>
      );
    }

    return (
      <div className="mt-3 space-y-4 border p-3 rounded-xl bg-slate-50">
        <h4 className="text-xs font-bold text-slate-700">Quick Order Form</h4>
        <input type="text" placeholder="Name" className="w-full p-2 text-xs rounded border" onChange={(e) => setCustomerDetails({...customerDetails, name: e.target.value})} />
        <input type="email" placeholder="Email" className="w-full p-2 text-xs rounded border" onChange={(e) => setCustomerDetails({...customerDetails, email: e.target.value})} />
        <button onClick={handleSubmit} disabled={isSubmitting} className="w-full bg-blue-600 text-white py-2 text-xs rounded-lg">
          {isSubmitting ? 'Processing...' : 'Submit Order'}
        </button>
      </div>
    );
  };

  const formatMessageContent = (content) => {
    if (!content) return '';
    let formatted = content;
    formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
      return `<a href="${url}" data-product-name="${text}" class="product-link text-blue-600 underline font-medium cursor-pointer">${text}</a>`;
    });
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\n/g, '<br />');
    return formatted;
  };

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-50 to-slate-100 overflow-hidden">
      <SEO title="Chat Assistant" description="Ask our AI Agent about SLT products and services." />

      {showClearConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full shadow-xl">
            <h3 className="text-lg font-bold mb-4">Clear History?</h3>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowClearConfirm(false)} className="px-4 py-2 text-slate-600">Cancel</button>
              <button onClick={confirmClearHistory} className="px-4 py-2 bg-red-500 text-white rounded-xl">Clear</button>
            </div>
          </div>
        </div>
      )}

      <header className="bg-white border-b border-slate-200 shadow-sm relative z-10">
        <div className="w-full px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-sm">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-800">AI Enterprise Agent</h1>
              <p className="text-xs text-slate-500">Logged in Session</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowClearConfirm(true)} className="flex items-center gap-2 px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">
              <Trash2 className="w-4 h-4" /> <span className="hidden sm:inline">Clear</span>
            </button>
            <button onClick={logout} className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg font-medium">
              <LogOut className="w-4 h-4" /> <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <div className="flex flex-col flex-1 relative min-w-0">
          <div className="flex-1 overflow-y-auto px-4 py-6">
            <div className="max-w-4xl mx-auto space-y-6">
              {messages.map((message) => (
                <div key={message.id} className={`flex gap-3 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-2xl rounded-2xl px-5 py-3 ${message.type === 'user' ? 'bg-blue-600 text-white' : 'bg-white border text-slate-800'}`}>
                    <div className="text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: formatMessageContent(message.content) }} />
                  </div>
                </div>
              ))}
              {isLoading && <div className="text-xs text-slate-500 animate-pulse">Assistant is typing...</div>}
              <div ref={messagesEndRef} />
            </div>
          </div>

          <div className="border-t bg-white p-4">
            <form onSubmit={sendMessage} className="max-w-4xl mx-auto flex gap-3">
              <input value={inputValue} onChange={(e) => setInputValue(e.target.value)} placeholder="Type your question..." className="flex-1 p-3 border rounded-xl focus:ring-2 focus:ring-blue-500/20" />
              <button type="submit" disabled={isLoading} className="bg-blue-600 text-white px-6 py-3 rounded-xl hover:bg-blue-700 shadow-md">
                <Send className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chat;