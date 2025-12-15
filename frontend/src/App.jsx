// frontend/src/app.jsx
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


  // Handlers for managing inline form state per message
  const updateInlineFormState = (requestId, newState) => {
    setInlineFormStates(prev => ({
      ...prev,
      [requestId]: { ...prev[requestId], ...newState }
    }));
  };

  const initializeInlineFormState = (requestId) => {
    if (!inlineFormStates[requestId]) {
      setInlineFormStates(prev => ({
        ...prev,
        [requestId]: {
          items: [{ productId: '', quantity: 1 }],
          customerDetails: { name: '', email: '', phone: '', address: '', notes: '' },
          formError: '',
          submissionStatus: '', // '', 'success', 'error'
          isSubmitting: false
        }
      }));
    }
  };

  const handleInlineItemChange = (requestId, itemIndex, field, value) => {
    updateInlineFormState(requestId, {
      items: inlineFormStates[requestId]?.items.map((item, idx) =>
        idx === itemIndex ? { ...item, [field]: value } : item
      )
    });
  };

  const handleInlineCustomerDetailChange = (requestId, field, value) => {
    updateInlineFormState(requestId, {
      customerDetails: { ...inlineFormStates[requestId]?.customerDetails, [field]: value }
    });
  };

  const handleInlineAddItem = (requestId) => {
    updateInlineFormState(requestId, {
      items: [...inlineFormStates[requestId]?.items, { productId: '', quantity: 1 }]
    });
  };

  const handleInlineRemoveItem = (requestId, itemIndex) => {
    setInlineFormStates(prevStates => {
      const currentState = prevStates[requestId];
      if (!currentState || currentState.items.length <= 1) {
        return prevStates;
      }
      const newItems = currentState.items.filter((_, idx) => idx !== itemIndex);
      return {
        ...prevStates,
        [requestId]: {
          ...currentState,
          items: newItems
        }
      };
    });
  };

  // Handle inline form submission
  const handleInlineFormSubmit = async (requestId) => {
    const currentState = inlineFormStates[requestId];
    if (!currentState) return;

    const { items, customerDetails } = currentState;
    let newFormError = '';

    // Validation
    if (items.some(item => !item.productId.trim())) {
      newFormError = 'Please select a product for all lines.';
    } else if (!customerDetails.name.trim()) {
      newFormError = 'Please fill in your name.';
    } else {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!customerDetails.email.trim() || !emailRegex.test(customerDetails.email.trim())) {
        newFormError = 'Please enter a valid email address.';
      } else {
        const phoneNumber = customerDetails.phone.trim();
        if (!phoneNumber) {
          newFormError = 'Please enter your phone number.';
        } else {
          const cleanedNumber = phoneNumber.replace(/\D/g, '');
          if (cleanedNumber.length !== 10) {
            newFormError = 'Phone number must be 10 digits.';
          }
        }
      }
    }

    if (newFormError) {
      updateInlineFormState(requestId, { formError: newFormError, isSubmitting: false });
      return;
    }

    updateInlineFormState(requestId, { formError: '', isSubmitting: true, submissionStatus: '' });

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
        throw new Error(errorData.detail || `Server Error: ${response.status}`);
      }

      const data = await response.json();
      console.log('Inline order submitted successfully:', data);
      // Update state to show success message within the message bubble
      updateInlineFormState(requestId, { submissionStatus: 'success', isSubmitting: false });

      // Optionally, add a success message to the main chat history as well
      // setMessages(prev => [...prev, {
      //   id: Date.now(),
      //   type: 'assistant', // Or 'system'?
      //   content: 'Your order request has been submitted successfully!',
      //   timestamp: new Date().toISOString()
      // }]);

    } catch (err) {
      console.error('Error submitting inline order:', err);
      updateInlineFormState(requestId, { formError: err.message || 'An error occurred.', submissionStatus: 'error', isSubmitting: false });
    }
  };


  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Inline Order Form Component
  const InlineOrderForm = ({ requestId, initialMessage, onSubmit, initialFormState = {} }) => {
    const [items, setItems] = useState(initialFormState.items || [{ productId: '', quantity: 1 }]);
    const [customerDetails, setCustomerDetails] = useState(initialFormState.customerDetails || { name: '', email: '', phone: '', address: '', notes: '' });
    const [formError, setFormError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submissionStatus, setSubmissionStatus] = useState(initialFormState.submissionStatus || '');

    // If already submitted successfully, just show the success message
    if (submissionStatus === 'success') {
      return (
        <div className="mt-3 p-4 bg-green-50 border border-green-200 rounded-xl">
          <div className="flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-green-600" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="text-green-800 font-medium">Order Request Sent!</span>
          </div>
          <p className="text-green-600 text-sm mt-1">Thank you for your request.</p>
        </div>
      );
    }

    // Handler functions using local state
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
      setItems(prev => [...prev, { productId: '', quantity: 1 }]);
    };

    const removeProductLine = (index) => {
      if (items.length > 1) {
        setItems(prev => prev.filter((_, i) => i !== index));
      }
    };

    const handleSubmit = async () => {
      // Validation logic
      if (items.some(item => !item.productId.trim())) {
        setFormError('Please select a product for all lines.');
        return;
      }
      if (!customerDetails.name.trim()) {
        setFormError('Please fill in your name.');
        return;
      }
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!customerDetails.email.trim() || !emailRegex.test(customerDetails.email.trim())) {
        setFormError('Please enter a valid email address.');
        return;
      }
      const phoneNumber = customerDetails.phone.trim();
      if (!phoneNumber) {
        setFormError('Please enter your phone number.');
        return;
      }
      const cleanedPhoneNumber = phoneNumber.replace(/\D/g, '');
      if (cleanedPhoneNumber.length !== 10) {
        setFormError('Phone number must be 10 digits long.');
        return;
      }

      // Prepare payload
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

      setIsSubmitting(true);
      setFormError('');

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
        console.log('Order submitted successfully:', data);
        setSubmissionStatus('success');
        onSubmitSuccess && onSubmitSuccess(requestId, data);
      } catch (err) {
        console.error('Error submitting order:', err);
        setFormError(err.message || 'An error occurred while submitting your order.');
      } finally {
        setIsSubmitting(false);
      }
    };

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
          {items.map((item, index) => (
            <div key={index} className="flex gap-1 mb-2"> {/* Key on the item container */}
              <select
                value={item.productId}
                onChange={(e) => handleItemChange(index, 'productId', e.target.value)}
                className="flex-1 px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500/20 focus:border-blue-500"
                disabled={isSubmitting}
              >
                <option value="">Select a product...</option>
                {/* Render options from products if available */}
                <option value="Product A">Product A</option>
                <option value="Product B">Product B</option>
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
          ))}
          <button
            type="button"
            onClick={addProductLine}
            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium mt-1 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isSubmitting}
          >
            <Plus className="w-3 h-3" /> Add Item
          </button>
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
                onChange={(e) => handleCustomerDetailChange('phone', e.target.value.replace(/\D/g, ''))} // Allow only numbers
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
                  onClick={() => setInputValue("What is the price of the eMark GM4 Mini UPS?")}
                  className="p-4 bg-white border border-slate-200 rounded-xl hover:border-blue-400 hover:shadow-md transition-all text-left group"
                >
                  <p className="text-sm font-semibold text-slate-800 group-hover:text-blue-600 transition-colors">Product Pricing</p>
                  <p className="text-xs text-slate-500 mt-1">Ask about product prices</p>
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
                // --- INLINE FORM LOGIC: Parse message content for the special marker ---
                let contentToRender = message.content; // Start with the raw content
                let orderFormSignal = null;
                let requestId = null;

                // Check if the message content contains the special order form marker
                const orderFormMarkerMatch = message.content.match(/\[SHOW_ORDER_FORM:(req_[^\]]+)\]/);
                if (orderFormMarkerMatch) {
                  requestId = orderFormMarkerMatch[1]; // Extract the request_id
                  // Remove the marker from the content to render
                  contentToRender = message.content.replace(orderFormMarkerMatch[0], '').trim();
                  // Set the signal flag
                  orderFormSignal = { type: 'order_form', request_id: requestId, message: contentToRender };
                }

                // Initialize form state if this is the first time seeing this requestId (could be done once per message render)
                if (requestId && !inlineFormStates[requestId]) {
                  initializeInlineFormState(requestId); // Make sure this function exists in your main App component
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
                              initialMessage={orderFormSignal.message} // Pass the message part (without marker)
                              initialFormState={inlineFormStates[requestId] || { items: [], customerDetails: {}, formError: '', submissionStatus: '', isSubmitting: false }} // Pass initial state
                            // onSubmit={handleInlineFormSubmit} // Pass the submit handler if needed for parent-side updates
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
          <div className="flex gap-3"> {/* Changed form to div to add button next to input */}
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
              onClick={sendMessage} // Changed to onClick to work with div
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
          </div>
          <p className="text-xs text-slate-400 mt-3 text-center font-medium">
            Session ID: {sessionId} • Powered by LangGraph & Neo4j
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;
