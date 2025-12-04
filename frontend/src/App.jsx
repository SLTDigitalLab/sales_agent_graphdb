import React, { useState, useRef, useEffect } from 'react';
import { Send, Trash2, Bot, User, Loader2, AlertCircle, X } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000'; 

function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const [error, setError] = useState(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false); // New state for modal
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

  // Updated: Just opens the modal
  const requestClearHistory = () => {
    setShowClearConfirm(true);
  };

  // Updated: Performs the actual clear action
  const confirmClearHistory = async () => {
    setShowClearConfirm(false); // Close modal immediately
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
      
      {/* --- CUSTOM MODAL (Updated Colors) --- */}
      {showClearConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-xl max-w-sm w-full p-6 transform scale-100 animate-in zoom-in-95 duration-200 border border-slate-100">
            <div className="flex items-center gap-3 mb-4">
              {/* Changed from bg-red-100 to bg-slate-100 */}
              <div className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center flex-shrink-0">
                {/* Changed from text-red-600 to text-slate-600 */}
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
              {/* Changed from bg-red-600 to bg-slate-800 and hover:bg-red-700 to hover:bg-slate-900 */}
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
          <button
            onClick={requestClearHistory}
            disabled={messages.length === 0}
            // Changed hover:text-red-600 to hover:text-slate-900 and hover:bg-red-50 to hover:bg-slate-100
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
            title="Clear chat history"
          >
            <Trash2 className="w-4 h-4 group-hover:scale-110 transition-transform" />
            <span className="hidden sm:inline">Clear</span>
          </button>
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
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm ${
                      message.type === 'error' ? 'bg-red-100' : 'bg-gradient-to-br from-blue-500 to-indigo-600'
                    }`}>
                      {message.type === 'error' ? (
                        <AlertCircle className="w-5 h-5 text-red-600" />
                      ) : (
                        <Bot className="w-5 h-5 text-white" />
                      )}
                    </div>
                  )}
                  
                  <div className={`flex flex-col max-w-3xl ${message.type === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className={`rounded-2xl px-5 py-3.5 ${
                      message.type === 'user'
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
            Session ID: {sessionId} • Powered by LangGraph & Neo4j
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;