import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Plus, Trash2, Save, RefreshCw, Database, Globe, ShoppingBag, Mail } from 'lucide-react'; 

// Uses the VITE_ variable if it exists (Docker), otherwise falls back to localhost (Local)
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Dashboard() {
  const { token, logout } = useAuth();
  
  // State for Configuration
  const [websiteUrls, setWebsiteUrls] = useState(['']);
  const [productUrls, setProductUrls] = useState(['']);
  const [socials, setSocials] = useState({ linkedin: '', facebook: '', tiktok: '' });
  const [targetEmail, setTargetEmail] = useState(''); // NEW STATE
  
  // State for Status & Results
  const [statusMsg, setStatusMsg] = useState({ text: '', type: '' });
  const [apiResult, setApiResult] = useState(null);
  const [loadingAction, setLoadingAction] = useState(null);

  // --- Helpers ---
  const authFetch = async (endpoint, options = {}) => {
    const headers = { ...options.headers, 'Authorization': `Bearer ${token}` };
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
      if (res.status === 401) {
        logout(); 
        return null;
      }
      return res;
    } catch (error) {
      console.error(error);
      setStatusMsg({ text: 'Network Error', type: 'error' });
      return null;
    }
  };

  // --- Actions ---
  const loadConfig = async () => {
    setLoadingAction('loadConfig');
    const res = await authFetch('/admin/config');
    if (res && res.ok) {
      const data = await res.json();
      const webs = Array.isArray(data.website_urls) ? data.website_urls : (data.website_url ? [data.website_url] : []);
      const prods = Array.isArray(data.product_urls) ? data.product_urls : (data.products_url ? [data.products_url] : []);
      
      setWebsiteUrls(webs.length ? webs : ['']);
      setProductUrls(prods.length ? prods : ['']);
      setSocials({
        linkedin: data.linkedin_url || '',
        facebook: data.facebook_url || '',
        tiktok: data.tiktok_url || ''
      });
      // Load email setting
      setTargetEmail(data.target_email || '');
      
      setStatusMsg({ text: 'Configuration loaded!', type: 'success' });
    }
    setLoadingAction(null);
  };

  const saveConfig = async () => {
    setLoadingAction('saveConfig');
    const config = {
      website_urls: websiteUrls.filter(u => u.trim()),
      product_urls: productUrls.filter(u => u.trim()),
      linkedin_url: socials.linkedin || null,
      facebook_url: socials.facebook || null,
      tiktok_url: socials.tiktok || null,
      target_email: targetEmail || null 
    };

    const res = await authFetch('/admin/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });

    if (res && res.ok) {
      setStatusMsg({ text: 'Configuration saved!', type: 'success' });
    } else {
      setStatusMsg({ text: 'Failed to save config', type: 'error' });
    }
    setLoadingAction(null);
  };

  const triggerAction = async (endpoint, actionId, method = 'POST') => {
    setLoadingAction(actionId);
    setStatusMsg({ text: 'Processing...', type: 'success' });
    setApiResult(null);

    const res = await authFetch(`/admin/${endpoint}`, { method });
    if (res && res.ok) {
      const data = await res.json();
      setApiResult(data);
      setStatusMsg({ text: 'Action completed!', type: 'success' });
    } else {
      setStatusMsg({ text: 'Action failed', type: 'error' });
    }
    setLoadingAction(null);
  };

  useEffect(() => { loadConfig(); }, []);

  const updateUrlList = (setter, list, index, value) => {
    const newList = [...list];
    newList[index] = value;
    setter(newList);
  };

  const addUrlRow = (setter, list) => setter([...list, '']);
  const removeUrlRow = (setter, list, index) => setter(list.filter((_, i) => i !== index));

  return (
    <div className="font-sans space-y-6">
       
       {/* Status Message Area */}
       {statusMsg.text && (
        <div className={`p-4 rounded-md ${statusMsg.type === 'error' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
            {statusMsg.text}
        </div>
       )}

       {/* Configuration Section */}
       <section className="border border-gray-200 rounded-lg p-6 bg-white shadow-sm">
        <h2 className="text-xl font-semibold text-gray-700 border-b pb-2 mb-4">Primary Configuration</h2>
        
        {/* Website URLs */}
        <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Website URLs</label>
            <div className="space-y-2">
            {websiteUrls.map((url, idx) => (
                <div key={idx} className="flex gap-2">
                <input 
                    type="url" 
                    placeholder="https://..." 
                    className="flex-1 rounded-md border border-gray-300 p-2 focus:ring-blue-500 focus:border-blue-500"
                    value={url}
                    onChange={(e) => updateUrlList(setWebsiteUrls, websiteUrls, idx, e.target.value)}
                />
                <button onClick={() => removeUrlRow(setWebsiteUrls, websiteUrls, idx)} className="p-2 text-red-500 hover:bg-red-100 rounded">
                    <Trash2 size={18} />
                </button>
                </div>
            ))}
            <button onClick={() => addUrlRow(setWebsiteUrls, websiteUrls)} className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800">
                <Plus size={16} /> Add URL
            </button>
            </div>
        </div>

        {/* Product URLs */}
        <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Product Page URLs</label>
            <div className="space-y-2">
            {productUrls.map((url, idx) => (
                <div key={idx} className="flex gap-2">
                <input 
                    type="url" 
                    placeholder="https://..." 
                    className="flex-1 rounded-md border border-gray-300 p-2 focus:ring-blue-500 focus:border-blue-500"
                    value={url}
                    onChange={(e) => updateUrlList(setProductUrls, productUrls, idx, e.target.value)}
                />
                <button onClick={() => removeUrlRow(setProductUrls, productUrls, idx)} className="p-2 text-red-500 hover:bg-red-100 rounded">
                    <Trash2 size={18} />
                </button>
                </div>
            ))}
            <button onClick={() => addUrlRow(setProductUrls, productUrls)} className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800">
                <Plus size={16} /> Add URL
            </button>
            </div>
        </div>
        
        {/* Socials */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
            <div>
                <label className="block text-sm font-medium text-gray-700">LinkedIn URL</label>
                <input className="w-full mt-1 p-2 border rounded" value={socials.linkedin} onChange={(e) => setSocials({...socials, linkedin: e.target.value})} />
            </div>
            <div>
                <label className="block text-sm font-medium text-gray-700">Facebook URL</label>
                <input className="w-full mt-1 p-2 border rounded" value={socials.facebook} onChange={(e) => setSocials({...socials, facebook: e.target.value})} />
            </div>
            <div>
                <label className="block text-sm font-medium text-gray-700">TikTok URL</label>
                <input className="w-full mt-1 p-2 border rounded" value={socials.tiktok} onChange={(e) => setSocials({...socials, tiktok: e.target.value})} />
            </div>
        </div>

        {/* Email Settings */}
        <div className="mb-4 border-t pt-4">
             <div className="flex items-center gap-2 mb-2 text-gray-800 font-medium">
                <Mail size={18} className="text-gray-600" />
                <h3>Email Notification Settings</h3>
             </div>
             <div>
                <label className="block text-sm font-medium text-gray-700">Order Recipient Email</label>
                <div className="text-xs text-gray-500 mb-1">New orders will be sent to this address (Leave empty to use system default).</div>
                <input 
                    type="email" 
                    className="w-full md:w-1/2 mt-1 p-2 border rounded focus:ring-blue-500 focus:border-blue-500" 
                    placeholder="sales@example.com"
                    value={targetEmail} 
                    onChange={(e) => setTargetEmail(e.target.value)} 
                />
            </div>
        </div>

        <div className="flex gap-4 pt-4 border-t mt-4">
            <button 
            onClick={loadConfig} 
            disabled={loadingAction === 'loadConfig'}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
            >
            <RefreshCw size={16} className={loadingAction === 'loadConfig' ? 'animate-spin' : ''}/> Reload
            </button>
            <button 
            onClick={saveConfig} 
            disabled={loadingAction === 'saveConfig'}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 shadow-sm"
            >
            <Save size={16} /> Save Changes
            </button>
        </div>
       </section>

       {/* Actions Section */}
       <section className="border border-gray-200 rounded-lg p-6 bg-white shadow-sm">
        <h2 className="text-xl font-semibold text-gray-700 mb-6">Data Management</h2>
        
        {/* GROUP 1: General Knowledge (Vector DB) */}
        <div className="mb-8">
            <div className="flex items-center gap-2 mb-4 text-gray-800 font-medium pb-2 border-b border-gray-100">
                <Globe size={18} className="text-indigo-600" />
                <h3>General Knowledge (Vector DB)</h3>
            </div>
            <div className="flex flex-wrap gap-3">
                <ActionButton 
                    label="Trigger Scraping" 
                    onClick={() => triggerAction('trigger-scraper', 'scrape')} 
                    loading={loadingAction === 'scrape'} 
                />
                <ActionButton 
                    label="Ingest Vector DB" 
                    onClick={() => triggerAction('ingest-chroma', 'chroma')} 
                    loading={loadingAction === 'chroma'} 
                />
                <button 
                    onClick={() => triggerAction('clear-chroma', 'clear-vector', 'DELETE')}
                    disabled={loadingAction === 'clear-vector'}
                    className="px-4 py-2 bg-red-50 text-red-700 border border-red-200 rounded hover:bg-red-100 disabled:opacity-50 text-sm font-medium transition-colors"
                >
                    {loadingAction === 'clear-vector' ? 'Clearing...' : 'Clear Vector DB Data'}
                </button>
            </div>
        </div>

        {/* GROUP 2: Product Catalog (Graph DB) */}
        <div>
            <div className="flex items-center gap-2 mb-4 text-gray-800 font-medium pb-2 border-b border-gray-100">
                <ShoppingBag size={18} className="text-indigo-600" />
                <h3>Product Catalog (Graph DB)</h3>
            </div>
            <div className="flex flex-wrap gap-3">
                <ActionButton 
                    label="Scrape Products" 
                    onClick={() => triggerAction('scrape-products', 'prod')} 
                    loading={loadingAction === 'prod'} 
                />
                <ActionButton 
                    label="Ingest Graph DB" 
                    onClick={() => triggerAction('ingest-neo4j', 'neo4j')} 
                    loading={loadingAction === 'neo4j'} 
                />
                <button 
                    onClick={() => triggerAction('clear-neo4j', 'clear-graph', 'DELETE')}
                    disabled={loadingAction === 'clear-graph'}
                    className="px-4 py-2 bg-red-50 text-red-700 border border-red-200 rounded hover:bg-red-100 disabled:opacity-50 text-sm font-medium transition-colors"
                >
                    {loadingAction === 'clear-graph' ? 'Clearing...' : 'Clear Graph DB Data'}
                </button>
            </div>
        </div>

        {/* Results Console */}
        {apiResult && (
            <div className="mt-8 bg-gray-900 text-green-400 p-4 rounded-md font-mono text-sm overflow-auto max-h-64 shadow-inner border border-gray-800">
                <div className="flex justify-between items-center mb-2 border-b border-gray-700 pb-1">
                    <span className="text-gray-500 text-xs uppercase tracking-wider">Console Output</span>
                    <button onClick={() => setApiResult(null)} className="text-xs text-gray-500 hover:text-white">Clear</button>
                </div>
                <pre>{JSON.stringify(apiResult, null, 2)}</pre>
            </div>
        )}
       </section>
    </div>
  );
}

function ActionButton({ label, onClick, loading }) {
  return (
    <button 
      onClick={onClick} 
      disabled={loading}
      className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded shadow-sm hover:bg-gray-50 hover:border-gray-400 disabled:opacity-50 text-sm font-medium transition-all"
    >
      {loading ? 'Processing...' : label}
    </button>
  );
}