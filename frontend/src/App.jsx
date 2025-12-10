// frontend/src/app.jsx
import React, { useState, useRef, useEffect } from 'react';
import { Send, Trash2, Bot, User, Loader2, AlertCircle, Plus, Minus, X } from 'lucide-react'; // Added icons

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const [error, setError] = useState(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [showOrderForm, setShowOrderForm] = useState(false); // NEW: State for order form modal visibility
  const [products, setProducts] = useState([]); // NEW: State to hold fetched products
  const [selectedItems, setSelectedItems] = useState([{ productId: '', quantity: 1 }]); // NEW: State for items in the form
  const [customerDetails, setCustomerDetails] = useState({ // NEW: State for customer details
    name: '',
    email: '',
    phone: '',
    address: '',
    notes: ''
  });
  const [formError, setFormError] = useState(''); // NEW: State for form-specific errors
  const [isSubmitting, setIsSubmitting] = useState(false); // NEW: State for submission loading
  const [submissionStatus, setSubmissionStatus] = useState(''); // NEW: State for submission status ('', 'success', 'error')
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // NEW: Fetch products from Neo4j (or wherever your product API is)
  const fetchProducts = async () => {
    try {
      // This is a placeholder. You'll need to implement an endpoint in your backend
      // that retrieves product data from Neo4j for the form.
      // Example: fetch(`${API_BASE_URL}/api/products-for-order-form`)
      console.log("Fetching products for order form...");
      // Simulate fetching products - Replace this with actual API call
      // Example API call:
      /*
      const response = await fetch(`${API_BASE_URL}/path/to/your/product/api`); // Replace with your actual endpoint
      if (!response.ok) {
        throw new Error('Failed to fetch products');
      }
      const data = await response.json();
      setProducts(data.products); // Assuming the API returns {products: [...]}
      */
      // For now, just log and set an empty array or mock data
      setProducts([]); // Or set to mock data if needed for testing
    } catch (err) {
      console.error('Error fetching products:', err);
      setFormError('Failed to load products. Please try again later.');
    }
  };

  // NEW: Handle opening the order form modal
  const openOrderForm = () => {
    setFormError(''); // Clear previous errors
    setSubmissionStatus(''); // Reset submission status when opening the modal
    fetchProducts(); // Fetch products when modal opens
    setShowOrderForm(true); // Show the modal
  };

  // NEW: Handle closing the order form modal
  const closeOrderForm = () => {
    setShowOrderForm(false);
    setFormError(''); // Clear errors when closing
    setSubmissionStatus(''); // Reset submission status when closing the modal
    setSelectedItems([{ productId: '', quantity: 1 }]); // Reset items
    setCustomerDetails({ name: '', email: '', phone: '', address: '', notes: '' }); // Reset customer details
  };

  // NEW: Handle adding a new product line item
  const addProductLine = () => {
    setSelectedItems([...selectedItems, { productId: '', quantity: 1 }]);
  };

  // NEW: Handle removing a product line item
  const removeProductLine = (index) => {
    if (selectedItems.length > 1) { // Ensure at least one item line exists
      const newItems = [...selectedItems];
      newItems.splice(index, 1);
      setSelectedItems(newItems);
    }
  };

  // NEW: Handle changing a product selection in a specific line item
  const handleProductChange = (index, value) => {
    const newItems = [...selectedItems];
    newItems[index].productId = value;
    setSelectedItems(newItems);
  };

  // NEW: Handle changing the quantity in a specific line item
  const handleQuantityChange = (index, value) => {
    const newItems = [...selectedItems];
    const numValue = Math.max(1, parseInt(value) || 1); // Ensure minimum quantity is 1
    newItems[index].quantity = numValue;
    setSelectedItems(newItems);
  };

  // NEW: Handle changes in customer detail fields
  const handleCustomerDetailChange = (field, value) => {
    setCustomerDetails({ ...customerDetails, [field]: value });
  };

  // NEW: Handle phone number input, allowing only numbers
  const handlePhoneChange = (value) => {
    // Remove any non-digit characters
    const numericValue = value.replace(/\D/g, '');
    // Update the customerDetails state with the cleaned number
    setCustomerDetails(prev => ({ ...prev, phone: numericValue }));
  };

  // NEW: Handle form submission
  const submitOrderForm = async () => {
    setFormError(''); // Clear previous errors
    setSubmissionStatus(''); // Reset submission status
    setIsSubmitting(true); // Show loading state on submit button

    // Basic validation
    if (selectedItems.some(item => !item.productId.trim())) {
      setFormError('Please select a product for all lines.');
      setIsSubmitting(false);
      return;
    }

    // NEW: Validate Customer Details
    if (!customerDetails.name.trim()) {
      setFormError('Please fill in your name.');
      setIsSubmitting(false);
      return;
    }

    // NEW: Validate Email Format (Basic check)
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/; // Simple regex for email validation
    if (!customerDetails.email.trim() || !emailRegex.test(customerDetails.email.trim())) {
      setFormError('Please enter a valid email address.');
      setIsSubmitting(false);
      return;
    }

    // NEW: Validate Phone Number Length
    const phoneNumber = customerDetails.phone.trim();
    if (!phoneNumber) {
      setFormError('Please enter your phone number.');
      setIsSubmitting(false);
      return;
    }

    // Assuming phone number should be exactly 10 digits
    // Remove non-digit characters for length check (optional: could add more complex validation)
    const cleanedPhoneNumber = phoneNumber.replace(/\D/g, '');
    if (cleanedPhoneNumber.length !== 10) {
      setFormError('Phone number must be 10 digits long.');
      setIsSubmitting(false);
      return;
    }

    // Prepare the payload (only if validation passes)
    const payload = {
      items: selectedItems.map(item => ({
        product_name: item.productId, // Assuming productId holds the name or an ID that maps to the name
        quantity: item.quantity
      })),
      customer_name: customerDetails.name.trim(), // Trim whitespace
      customer_email: customerDetails.email.trim(), // Trim whitespace
      customer_phone: customerDetails.phone.trim(), // Trim whitespace
      customer_address: customerDetails.address.trim(), // Trim whitespace
      notes: customerDetails.notes.trim() // Trim whitespace
    };

    try {
      console.log("Sending order request:", payload); // Log the payload for debugging
      const response = await fetch(`${API_BASE_URL}/email/order-request`, { // Use the correct endpoint
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      console.log('Order submitted successfully:', data);
      // Set the status to success to show the success message in the modal
      setSubmissionStatus('success');
      // Optionally clear the form fields here if desired, though keeping them filled might be useful for confirmation
      // setCustomerDetails({ name: '', email: '', phone: '', address: '', notes: '' });
      // setSelectedItems([{ productId: '', quantity: 1 }]);

    } catch (err) {
      console.error('Error submitting order:', err);
      setFormError(err.message || 'An error occurred while submitting your order.');
      setSubmissionStatus('error'); // Set status to error if needed for UI
    } finally {
      setIsSubmitting(false); // Hide loading state
    }
  };

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

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-50 to-slate-100">

      {/* --- ORDER FORM MODAL --- */}
      {showOrderForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 border border-slate-200">
            {/* --- Conditional Rendering based on submission status --- */}
            {submissionStatus === 'success' ? (
              // Success Message View
              <div className="flex flex-col items-center justify-center py-12">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-6">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 text-green-600" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <h2 className="text-2xl font-bold text-slate-800 mb-2">Order Request Sent!</h2>
                <p className="text-slate-600 text-center mb-8">
                  Thank you for your request. We will contact you shortly regarding your order.
                </p>
                <button
                  onClick={closeOrderForm}
                  className="px-6 py-3 bg-gradient-to-br from-blue-500 to-indigo-600 text-white font-medium rounded-xl hover:from-blue-600 hover:to-indigo-700 transition-all shadow-md shadow-blue-500/20"
                >
                  Close
                </button>
              </div>
            ) : (
              // Main Form View
              <>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-bold text-slate-800">Place an Order</h2>
                  <button
                    onClick={closeOrderForm}
                    className="text-slate-400 hover:text-slate-600 transition-colors"
                    disabled={isSubmitting} // Disable during submission
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                {formError && (
                  <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 mb-4">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-5 h-5 text-red-600" />
                      <p className="text-sm text-red-800 font-medium">{formError}</p>
                    </div>
                  </div>
                )}

                <div className="space-y-6">
                  <div>
                    <h3 className="font-medium text-slate-700 mb-2">Items</h3>
                    {selectedItems.map((item, index) => (
                      <div key={index} className="flex gap-2 mb-3">
                        <select
                          value={item.productId}
                          onChange={(e) => handleProductChange(index, e.target.value)}
                          className="flex-1 px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm"
                          disabled={isSubmitting} // Disable during submission
                        >
                          <option value="">Select a product...</option>
                          {/* Render options from the 'products' state fetched from backend */}
                          {/* Example: products.map(p => <option key={p.id} value={p.name}>{p.name}</option>) */}
                          {/* For now, using a placeholder option */}
                          <option value="Placeholder Product">Placeholder Product</option>
                          <option value="Another Placeholder">Another Placeholder</option>
                        </select>
                        <input
                          type="number"
                          min="1"
                          value={item.quantity}
                          onChange={(e) => handleQuantityChange(index, e.target.value)}
                          className="w-20 px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm"
                          disabled={isSubmitting} // Disable during submission
                        />
                        {selectedItems.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeProductLine(index)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            disabled={isSubmitting} // Disable during submission
                          >
                            <Minus className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={addProductLine}
                      className="flex items-center gap-1 text-blue-600 hover:text-blue-800 text-sm font-medium mt-1 disabled:opacity-50 disabled:cursor-not-allowed"
                      disabled={isSubmitting} // Disable during submission
                    >
                      <Plus className="w-4 h-4" /> Add another product
                    </button>
                  </div>

                  <div>
                    <h3 className="font-medium text-slate-700 mb-2">Customer Details</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label htmlFor="customerName" className="block text-sm font-medium text-slate-600 mb-1">Name *</label>
                        <input
                          type="text"
                          id="customerName"
                          value={customerDetails.name}
                          onChange={(e) => handleCustomerDetailChange('name', e.target.value)}
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm"
                          placeholder="Enter your name"
                          disabled={isSubmitting} // Disable during submission
                        />
                      </div>
                      <div>
                        <label htmlFor="customerEmail" className="block text-sm font-medium text-slate-600 mb-1">Email *</label>
                        <input
                          type="email"
                          id="customerEmail"
                          value={customerDetails.email}
                          onChange={(e) => handleCustomerDetailChange('email', e.target.value)}
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm"
                          placeholder="Enter your email"
                          disabled={isSubmitting} // Disable during submission
                        />
                      </div>
                      <div>
                        <label htmlFor="customerPhone" className="block text-sm font-medium text-slate-600 mb-1">Phone *</label>
                        <input
                          type="tel"
                          id="customerPhone"
                          value={customerDetails.phone}
                          onChange={(e) => handlePhoneChange(e.target.value)} 
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm"
                          placeholder="Enter your phone number"
                          disabled={isSubmitting}
                        />
                      </div>
                      <div>
                        <label htmlFor="customerAddress" className="block text-sm font-medium text-slate-600 mb-1">Address</label>
                        <input
                          type="text"
                          id="customerAddress"
                          value={customerDetails.address}
                          onChange={(e) => handleCustomerDetailChange('address', e.target.value)}
                          className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm"
                          placeholder="Enter your address (optional)"
                          disabled={isSubmitting} // Disable during submission
                        />
                      </div>
                    </div>
                    <div className="mt-4">
                      <label htmlFor="orderNotes" className="block text-sm font-medium text-slate-600 mb-1">Notes (Optional)</label>
                      <textarea
                        id="orderNotes"
                        rows="3"
                        value={customerDetails.notes}
                        onChange={(e) => handleCustomerDetailChange('notes', e.target.value)}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm"
                        placeholder="Any special instructions or notes..."
                        disabled={isSubmitting} // Disable during submission
                      ></textarea>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-3 mt-8">
                  <button
                    onClick={closeOrderForm}
                    disabled={isSubmitting}
                    className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-50 hover:text-slate-900 rounded-xl transition-colors border border-transparent hover:border-slate-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={submitOrderForm}
                    disabled={isSubmitting}
                    className="px-4 py-2 bg-gradient-to-br from-blue-500 to-indigo-600 text-white font-medium rounded-xl hover:from-blue-600 hover:to-indigo-700 transition-all shadow-md shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Submitting...
                      </>
                    ) : 'Submit Order'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

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
              onClick={openOrderForm} // NEW: Click handler for the order form
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-all border border-slate-200 hover:border-slate-300 group"
              title="Place an Order"
            >
              <span>Place an Order</span>
            </button>
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
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {message.type !== 'user' && (
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm ${message.type === 'error' ? 'bg-red-100' : 'bg-gradient-to-br from-blue-500 to-indigo-600'
                      }`}>
                      {message.type === 'error' ? (
                        <AlertCircle className="w-5 h-5 text-red-600" />
                      ) : (
                        <Bot className="w-5 h-5 text-white" />
                      )}
                    </div>
                  )}

                  <div className={`flex flex-col max-w-3xl ${message.type === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className={`rounded-2xl px-5 py-3.5 ${message.type === 'user'
                      ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-md'
                      : message.type === 'error'
                        ? 'bg-red-50 text-red-800 border border-red-200'
                        : 'bg-white text-slate-800 shadow-sm border border-slate-200'
                      }`}>
                      <div
                        className="text-sm leading-relaxed whitespace-pre-wrap"
                        dangerouslySetInnerHTML={{ __html: formatMessageContent(message.content) }}
                      />
                    </div>
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
              ))}

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
              onClick={openOrderForm} // NEW: Also add the button next to the input field
              disabled={isLoading}
              className="px-4 py-3.5 bg-gradient-to-br from-green-500 to-emerald-600 text-white rounded-xl hover:from-green-600 hover:to-emerald-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-1 font-medium shadow-md shadow-green-500/20"
            >
              <Plus className="w-5 h-5" /> {/* Optional: Add an icon */}
              Order
            </button>
            <button
              type="submit"
              onClick={sendMessage} // NEW: Changed to onClick to work with div
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