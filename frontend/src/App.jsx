import React, { useState, useRef, useEffect } from 'react';
import { Send, Trash2, Bot, User, Loader2, AlertCircle, Plus, Minus, X } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const [error, setError] = useState(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [inlineFormStates, setInlineFormStates] = useState({});
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
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

    try {
      const response = await fetch(`${API_BASE_URL}/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          question: userMessage.content
        })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

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
      inputRef.current?.focus();
    }
  };

  const requestClearHistory = () => {
    setShowClearConfirm(true);
  };

  const confirmClearHistory = async () => {
    setShowClearConfirm(false);
    try {
      await fetch(`${API_BASE_URL}/v1/chat/clear`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId
        })
      });

      setMessages([]);
      setError(null);
    } catch (err) {
      console.error('Error clearing history:', err);
      setError('Failed to clear chat history');
    }
  };


  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };


  // Function to handle successful order submission
  const handleOrderSuccess = (requestId) => {
    setInlineFormStates(prev => ({
      ...prev,
      [requestId]: {
        ...prev[requestId],
        submissionStatus: 'success'
      }
    }));
  };


  // Inline Order Form Component
  const InlineOrderForm = ({ requestId, initialMessage, savedState, onOrderSuccess, onSubmitError, prefillProduct }) => {
    const [items, setItems] = useState([
        { 
          productId: savedState?.items?.[0]?.productId || prefillProduct || '', 
          quantity: savedState?.items?.[0]?.quantity || 1 
        }
    ]);
    const [customerDetails, setCustomerDetails] = useState({ name: '', email: '', phone: '', address: '', notes: '' });
    const [formError, setFormError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Initialize status based on parent state
    const [submissionStatus, setSubmissionStatus] = useState(savedState?.submissionStatus || '');

    const [products, setProducts] = useState([]);
    const [loadingProducts, setLoadingProducts] = useState(true);

    // Fetch products when the component mounts
    useEffect(() => {
      const fetchProductsForForm = async () => {
        try {
          console.log("InlineOrderForm: Fetching products from Neo4j...");
          const response = await fetch(`${API_BASE_URL}/db/graph/products-for-order-form`);
          if (!response.ok) {
            throw new Error(`Failed to fetch products: ${response.status}`);
          }
          const data = await response.json();
          setProducts(data.products);
          setLoadingProducts(false);
          console.log(`InlineOrderForm: Fetched ${data.products.length} products from Neo4j.`);
        } catch (err) {
          console.error("Error fetching products for order form:", err);
          setProducts([]); // Set to empty array on error
          setLoadingProducts(false);
          setFormError(`Failed to load products: ${err.message}. Please try again later.`);
        }
      };

      fetchProductsForForm();
    }, []); // Empty dependency array means this runs once on mount

    const handleItemChange = (index, field, value) => {
      setItems(prevItems => {
        const newItems = [...prevItems];
        newItems[index][field] = value;
        return newItems;
      });
    };

    const handleCustomerDetailChange = (field, value) => {
      setCustomerDetails(prev => ({ ...prev, [field]: value }));
    };

    const addProductLine = () => {
      setItems(prevItems => [...prevItems, { productId: '', quantity: 1 }]);
    };

    const removeProductLine = (index) => {
      if (items.length > 1) { // Only allow removal if there's more than one item
        setItems(prevItems => prevItems.filter((_, i) => i !== index));
      }
    };

    const handleSubmit = async () => {
      setFormError('');
      setSubmissionStatus('');

      // Basic validation
      if (items.some(item => !item.productId.trim())) {
        setFormError('Please select a product for all lines.');
        return;
      }
      if (!customerDetails.name.trim() || !customerDetails.email.trim() || !customerDetails.phone.trim()) {
        setFormError('Please fill in your name, email, and phone number.');
        return;
      }

      // Email validation
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(customerDetails.email.trim())) {
        setFormError('Please enter a valid email address.');
        return;
      }

      // Phone number validation (assuming 10 digits)
      const phoneNumber = customerDetails.phone.trim().replace(/\D/g, '');
      if (phoneNumber.length !== 10) {
        setFormError('Phone number must be 10 digits long.');
        return;
      }

      setIsSubmitting(true);

      const payload = {
        items: items.map(item => ({
          product_name: item.productId,
          quantity: item.quantity
        })),
        customer_name: customerDetails.name.trim(),
        customer_email: customerDetails.email.trim(),
        customer_phone: customerDetails.phone.trim(),
        customer_address: customerDetails.address.trim(),
        notes: customerDetails.notes.trim()
      };

      try {
        const response = await fetch(`${API_BASE_URL}/email/order-request`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `Server error: ${response.status}`);
        }

        const data = await response.json();
        console.log('Order submitted successfully: ', data);
        setSubmissionStatus('success');
        if (onOrderSuccess) onOrderSuccess(requestId);

      } catch (err) {
        console.error('Error submitting order:', err);
        setFormError(err.message || 'An error occurred while submitting your order.');
        setSubmissionStatus('error');
        if (onSubmitError) onSubmitError(requestId, err.message);
      } finally {
        setIsSubmitting(false);
      }
    };

    if (submissionStatus === 'success' || savedState?.submissionStatus === 'success') {
      return (
        <div className="mt-3 p-4 bg-green-50 border border-green-200 rounded-xl">
          <div className="flex items-center gap-2">
            {/* ... keep your success SVG and text ... */}
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-green-600" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="text-green-800 font-medium">Order Request Sent!</span>
          </div>
          <p className="text-green-600 text-sm mt-1">Thank you for your request. You will receive a confirmation email shortly. We will contact you soon.</p>
        </div>
      );
    }

    return (
      <div className="mt-3 space-y-4">
        {initialMessage && <p className="text-sm text-slate-700">{initialMessage}</p>}
        {formError && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-3 py-2">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600" />
              <p className="text-xs text-red-800 font-medium">{formError}</p>
            </div>
          </div>
        )}

        <div>
          <h4 className="text-xs font-semibold text-slate-600 mb-1">Items</h4>
          {loadingProducts ? (
            <div className="text-xs text-slate-500 italic">Loading products...</div>
          ) : (
            items.map((item, index) => (
              <div key={index} className="flex gap-1 mb-2">
                <select
                  value={item.productId}
                  onChange={(e) => handleItemChange(index, 'productId', e.target.value)}
                  className="flex-1 px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500/20 focus:border-blue-500"
                  disabled={isSubmitting}
                >
                  <option value="">Select a product...</option>
                  {/* Group products by category */}
                  {(() => {
                    const categories = {};
                    products.forEach(p => {
                      if (!categories[p.category_name]) categories[p.category_name] = [];
                      categories[p.category_name].push(p);
                    });

                    return Object.entries(categories).map(([category, prods]) => (
                      <optgroup key={category} label={category}>
                        {prods.map(p => (
                          <option key={`${p.sku}-${p.name}`} value={p.name}> {/* Use name or SKU as value */}
                            {p.name} (Rs. {p.price.toFixed(2)})
                          </option>
                        ))}
                      </optgroup>
                    ));
                  })()}
                </select>
                <input
                  type="number"
                  min="1"
                  value={item.quantity}
                  onChange={(e) => handleItemChange(index, 'quantity', parseInt(e.target.value) || 1)}
                  className="w-16 px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500/20 focus:border-blue-500"
                  disabled={isSubmitting}
                />
                {items.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeProductLine(index)}
                    className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={isSubmitting}
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            ))
          )}
          {!loadingProducts && (
            <button
              type="button"
              onClick={addProductLine}
              className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium mt-1 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isSubmitting}
            >
              <Plus className="w-3 h-3" /> Add Item
            </button>
          )}
        </div>

        <div>
          <h4 className="text-xs font-semibold text-slate-600 mb-1">Your Details</h4>
          <div className="grid grid-cols-1 gap-2">
            <div>
              <input
                type="text"
                placeholder="Name *"
                value={customerDetails.name}
                onChange={(e) => handleCustomerDetailChange('name', e.target.value)}
                className="w-full px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500/20 focus:border-blue-500"
                disabled={isSubmitting}
              />
            </div>
            <div>
              <input
                type="email"
                placeholder="Email *"
                value={customerDetails.email}
                onChange={(e) => handleCustomerDetailChange('email', e.target.value)}
                className="w-full px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500/20 focus:border-blue-500"
                disabled={isSubmitting}
              />
            </div>
            <div>
              <input
                type="tel"
                placeholder="Phone * (10 digits)"
                value={customerDetails.phone}
                onChange={(e) => handleCustomerDetailChange('phone', e.target.value.replace(/\D/g, ''))}
                maxLength="10"
                className="w-full px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500/20 focus:border-blue-500"
                disabled={isSubmitting}
              />
            </div>
            <div>
              <textarea
                placeholder="Address (optional)"
                value={customerDetails.address}
                onChange={(e) => handleCustomerDetailChange('address', e.target.value)}
                rows="1"
                className="w-full px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500/20 focus:border-blue-500 resize-none"
                disabled={isSubmitting}
              ></textarea>
            </div>
            <div>
              <textarea
                placeholder="Notes (optional)"
                value={customerDetails.notes}
                onChange={(e) => handleCustomerDetailChange('notes', e.target.value)}
                rows="1"
                className="w-full px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500/20 focus:border-blue-500 resize-none"
                disabled={isSubmitting}
              ></textarea>
            </div>
          </div>
        </div>

        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="mt-3 px-3 py-1.5 bg-gradient-to-br from-blue-500 to-indigo-600 text-white text-xs font-medium rounded-lg hover:from-blue-600 hover:to-indigo-700 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-3 h-3 animate-spin" /> Submitting...
            </>
          ) : 'Submit Order'}
        </button>
      </div>
    );
  };


  const formatMessageContent = (content) => {
    if (!content) return '';

    let formatted = content;

    // 1. Handle Markdown Links: [Text](URL)
    const markdownLinkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    formatted = formatted.replace(markdownLinkRegex, (match, text, url) => {
      return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 underline transition-colors font-medium">${text}</a>`;
    });

    // 2. Handle Bold (**text**) -> <strong>text</strong>
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // 3. Handle Newlines (\n) -> <br />
    formatted = formatted.replace(/\n/g, '<br />');

    // 4. Handle Raw Links
    const rawUrlRegex = /(?<!href=")(https?:\/\/[^\s<]+)/g;
    formatted = formatted.replace(rawUrlRegex, (url) => {
      const punctuation = /[.,;!?)]$/;
      let cleanUrl = url;
      let suffix = '';

      if (punctuation.test(url)) {
        suffix = url.slice(-1);
        cleanUrl = url.slice(0, -1);
      }
      return `<a href="${cleanUrl}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 underline transition-colors break-all">${cleanUrl}</a>${suffix}`;
    });

    return formatted;
  };

  // Return
  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-50 to-slate-100">

      {/* Existing Clear Confirmation Modal */}
      {showClearConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-xl max-w-sm w-full p-6 transform scale-100 animate-in zoom-in-95 duration-200 border border-slate-100">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center flex-shrink-0">
                <Trash2 className="w-5 h-5 text-slate-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-800">Clear History?</h3>
              </div>
            </div>

            <p className="text-slate-600 mb-6 leading-relaxed">
              Are you sure you want to delete all chat history? This action cannot be undone.
            </p>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowClearConfirm(false)}
                className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-50 hover:text-slate-900 rounded-xl transition-colors border border-transparent hover:border-slate-200"
              >
                Cancel
              </button>
              <button
                onClick={confirmClearHistory}
                className="px-4 py-2 bg-slate-500 text-white font-medium rounded-xl hover:bg-slate-700 transition-colors shadow-sm flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                Yes, Clear Chat
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="bg-white border-b border-slate-200 shadow-sm relative z-10">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-sm">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-800 tracking-tight">AI Enterprise Agent</h1>
              <p className="text-xs text-slate-500 font-medium">SLT Knowledge Assistant</p>
            </div>
          </div>
          <div className="flex gap-2"> {/* Wrap buttons in a flex container */}
            <button
              onClick={requestClearHistory}
              disabled={messages.length === 0}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
              title="Clear chat history"
            >
              <Trash2 className="w-4 h-4 group-hover:scale-110 transition-transform" />
              <span className="hidden sm:inline">Clear</span>
            </button>
          </div>
        </div>
      </header>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-4 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-12">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center mb-6 shadow-lg shadow-blue-500/20">
                <Bot className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-slate-800 mb-2">Welcome to AI Enterprise Agent</h2>
              <p className="text-slate-600 mb-8 max-w-md leading-relaxed">
                Ask me anything about SLT's products, services, or company information. I can help you with product prices, specifications, and more.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl w-full">
                <button
                  onClick={() => setInputValue("I want to order a product")}
                  className="p-4 bg-white border border-slate-200 rounded-xl hover:border-blue-400 hover:shadow-md transition-all text-left group"
                >
                  <p className="text-sm font-semibold text-slate-800 group-hover:text-blue-600 transition-colors">Product Ordering</p>
                  <p className="text-xs text-slate-500 mt-1">Order products from us</p>
                </button>
                <button
                  onClick={() => setInputValue("What are available product categories?")}
                  className="p-4 bg-white border border-slate-200 rounded-xl hover:border-blue-400 hover:shadow-md transition-all text-left group"
                >
                  <p className="text-sm font-semibold text-slate-800 group-hover:text-blue-600 transition-colors">Product Categories</p>
                  <p className="text-xs text-slate-500 mt-1">Explore product categories</p>
                </button>
                <button
                  onClick={() => setInputValue("Tell me about SLT's services")}
                  className="p-4 bg-white border border-slate-200 rounded-xl hover:border-blue-400 hover:shadow-md transition-all text-left group"
                >
                  <p className="text-sm font-semibold text-slate-800 group-hover:text-blue-600 transition-colors">Company Information</p>
                  <p className="text-xs text-slate-500 mt-1">Learn about services</p>
                </button>
                <button
                  onClick={() => setInputValue("What security cameras do you offer?")}
                  className="p-4 bg-white border border-slate-200 rounded-xl hover:border-blue-400 hover:shadow-md transition-all text-left group"
                >
                  <p className="text-sm font-semibold text-slate-800 group-hover:text-blue-600 transition-colors">Product Search</p>
                  <p className="text-xs text-slate-500 mt-1">Find specific products</p>
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message) => {
                // --- INLINE FORM LOGIC
                let contentToRender = message.content; 
                let orderFormSignal = null;
                let requestId = null;
                let prefillProduct = '';

                // Check if the message content contains the special order form marker
                const orderFormMarkerMatch = message.content.match(/\[SHOW_ORDER_FORM:([^|\]]+)(?:\|([^\]]+))?\]/);
                if (orderFormMarkerMatch) {
                  requestId = orderFormMarkerMatch[1];
                  prefillProduct = orderFormMarkerMatch[2] || '';
                  contentToRender = message.content.replace(orderFormMarkerMatch[0], '').trim();
                  // Set the signal flag
                  orderFormSignal = { type: 'order_form', request_id: requestId, message: contentToRender, prefill_product: prefillProduct };
                }

                return (
                  <div
                    key={message.id} // Ensure each message has a stable key
                    className={`flex gap-3 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {/* ... existing icon logic ... */}

                    <div className={`flex flex-col max-w-3xl ${message.type === 'user' ? 'items-end' : 'items-start'}`}>
                      {/* --- MESSAGE BUBBLE CONTENT --- */}
                      <div
                        className={`rounded-2xl px-5 py-3.5 ${message.type === 'user'
                          ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-md'
                          : message.type === 'error'
                            ? 'bg-red-50 text-red-800 border border-red-200'
                            : 'bg-white text-slate-800 shadow-sm border border-slate-200'
                          }`}
                      >
                        <>
                          {/* Render the main message content if it exists (after removing the marker) */}
                          {contentToRender && (
                            <div
                              className="text-sm leading-relaxed whitespace-pre-wrap"
                              dangerouslySetInnerHTML={{ __html: formatMessageContent(contentToRender) }}
                            />
                          )}
                          {/* Conditionally render the inline form if the signal is present */}
                          {requestId && (
                            <InlineOrderForm
                              requestId={requestId}  
                              prefillProduct={orderFormSignal.prefill_product}                   
                              savedState={inlineFormStates[requestId]}
                              onOrderSuccess={handleOrderSuccess}
                              onSubmitError={(reqId, errorMsg) => console.error(errorMsg)}
                            />
                          )}
                        </>
                      </div>
                      {/* --- END MESSAGE BUBBLE CONTENT --- */}
                      <span className="text-xs text-slate-400 mt-1.5 px-1 font-medium">
                        {formatTime(message.timestamp)}
                      </span>
                    </div>

                    {message.type === 'user' && (
                      <div className="w-8 h-8 bg-gradient-to-br from-slate-600 to-slate-700 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm">
                        <User className="w-5 h-5 text-white" />
                      </div>
                    )}
                  </div>
                );
              })}

              {isLoading && (
                <div className="flex gap-3 justify-start animate-pulse">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center flex-shrink-0 opacity-80">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div className="bg-white rounded-2xl px-4 py-3 shadow-sm border border-slate-200">
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                      <span className="text-sm text-slate-600 font-medium">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="max-w-5xl mx-auto w-full px-4">
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 mb-4 shadow-sm">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <p className="text-sm text-red-800 font-medium">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Input Form */}
      <div className="border-t border-slate-200 bg-white">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <form onSubmit={sendMessage} className="flex gap-3">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask about products, prices, or company information..."
              disabled={isLoading}
              className="flex-1 px-5 py-3.5 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 disabled:bg-slate-50 disabled:cursor-not-allowed text-slate-800 placeholder-slate-400 transition-all shadow-sm"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isLoading}
              className="px-6 py-3.5 bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-xl hover:from-blue-600 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 font-medium shadow-md shadow-blue-500/20"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  <span className="hidden sm:inline">Send</span>
                </>
              )}
            </button>
          </form>
          <p className="text-xs text-slate-400 mt-3 text-center font-medium">
            Session ID: {sessionId} • AI Enterprise Agent
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;
