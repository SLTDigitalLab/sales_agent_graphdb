import React, { useState, useRef, useEffect } from 'react';
import { Send, Trash2, Bot, User, Loader2, AlertCircle } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000'; 

function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const [error, setError] = useState(null);
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

  const clearHistory = async () => {
    if (window.confirm('Are you sure you want to clear the chat history?')) {
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
    }
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // --- UPDATED FORMATTER FUNCTION ---
  const formatMessageContent = (content) => {
    if (!content) return '';

    let formatted = content;

    // 1. Handle Markdown Links: [Text](URL)
    // Regex explanation: \[([^\]]+)\] captures the text inside brackets
    // \(([^)]+)\) captures the URL inside parentheses
    // This replaces [Title](Link) with <a href="Link">Title</a>
    const markdownLinkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    formatted = formatted.replace(markdownLinkRegex, (match, text, url) => {
      return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800 underline transition-colors font-medium">${text}</a>`;
    });

    // 2. Handle Bold (**text**) -> <strong>text</strong>
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // 3. Handle Newlines (\n) -> <br />
    formatted = formatted.replace(/\n/g, '<br />');

    // 4. Handle Raw Links (http://... that are NOT part of a markdown link)
    // This uses a "negative lookbehind" (?<!href=") to ensure we don't double-replace links 
    // that we already fixed in Step 1.
    const rawUrlRegex = /(?<!href=")(https?:\/\/[^\s<]+)/g;
    formatted = formatted.replace(rawUrlRegex, (url) => {
      // Clean trailing punctuation
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
      {/* Header */}
      <header className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-800">AI Enterprise Agent</h1>
              <p className="text-xs text-slate-500">SLT Knowledge Assistant</p>
            </div>
          </div>
          <button
            onClick={clearHistory}
            disabled={messages.length === 0}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Clear chat history"
          >
            <Trash2 className="w-4 h-4" />
            <span className="hidden sm:inline">Clear</span>
          </button>
        </div>
      </header>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-4 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-12">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center mb-4">
                <Bot className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-slate-800 mb-2">Welcome to AI Enterprise Agent</h2>
              <p className="text-slate-600 mb-6 max-w-md">
                Ask me anything about SLT's products, services, or company information. I can help you with product prices, specifications, and more.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl w-full">
                <button
                  onClick={() => setInputValue("What is the price of the eMark GM4 Mini UPS?")}
                  className="p-4 bg-white border border-slate-200 rounded-lg hover:border-blue-400 hover:shadow-md transition-all text-left"
                >
                  <p className="text-sm font-medium text-slate-800">Product Pricing</p>
                  <p className="text-xs text-slate-500 mt-1">Ask about product prices</p>
                </button>
                <button
                  onClick={() => setInputValue("What are available product categories?")}
                  className="p-4 bg-white border border-slate-200 rounded-lg hover:border-blue-400 hover:shadow-md transition-all text-left"
                >
                  <p className="text-sm font-medium text-slate-800">Product Categories</p>
                  <p className="text-xs text-slate-500 mt-1">Explore product categories</p>
                </button>
                <button
                  onClick={() => setInputValue("Tell me about SLT's services")}
                  className="p-4 bg-white border border-slate-200 rounded-lg hover:border-blue-400 hover:shadow-md transition-all text-left"
                >
                  <p className="text-sm font-medium text-slate-800">Company Information</p>
                  <p className="text-xs text-slate-500 mt-1">Learn about services</p>
                </button>
                <button
                  onClick={() => setInputValue("What security cameras do you offer?")}
                  className="p-4 bg-white border border-slate-200 rounded-lg hover:border-blue-400 hover:shadow-md transition-all text-left"
                >
                  <p className="text-sm font-medium text-slate-800">Product Search</p>
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
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
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
                    <div className={`rounded-2xl px-4 py-3 ${
                      message.type === 'user'
                        ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white'
                        : message.type === 'error'
                        ? 'bg-red-50 text-red-800 border border-red-200'
                        : 'bg-white text-slate-800 shadow-sm border border-slate-200'
                    }`}>
                      <div 
                          className="text-sm leading-relaxed whitespace-pre-wrap"
                          dangerouslySetInnerHTML={{ __html: formatMessageContent(message.content) }}
                      />
                    </div>
                    <span className="text-xs text-slate-400 mt-1 px-2">
                      {formatTime(message.timestamp)}
                    </span>
                  </div>

                  {message.type === 'user' && (
                    <div className="w-8 h-8 bg-gradient-to-br from-slate-600 to-slate-700 rounded-full flex items-center justify-center flex-shrink-0">
                      <User className="w-5 h-5 text-white" />
                    </div>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center flex-shrink-0">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div className="bg-white rounded-2xl px-4 py-3 shadow-sm border border-slate-200">
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                      <span className="text-sm text-slate-600">Thinking...</span>
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
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <p className="text-sm text-red-800">{error}</p>
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
              className="flex-1 px-4 py-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-slate-50 disabled:cursor-not-allowed text-slate-800 placeholder-slate-400"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isLoading}
              className="px-6 py-3 bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-xl hover:from-blue-600 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 font-medium"
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
          <p className="text-xs text-slate-500 mt-2 text-center">
            Session ID: {sessionId} • Powered by LangGraph & Neo4j
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;