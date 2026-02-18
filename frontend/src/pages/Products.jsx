import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  Search, 
  Edit3, 
  Trash2, 
  Package, 
  RefreshCw, 
  AlertCircle, 
  Plus, 
  X,
  Save,
  ListFilter
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Products() {
  const { token, logout } = useAuth();
  const [products, setProducts] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  
  // --- NEW: Category Filter State ---
  const [selectedCategory, setSelectedCategory] = useState('All');
  
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState({ text: '', type: '' });
  
  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newProduct, setNewProduct] = useState({
    sku: '', name: '', category: '', price: 0, stock_quantity: 0, description: '', image_url: ''
  });

  // Edit Modal State
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editProduct, setEditProduct] = useState(null);

  const authFetch = async (endpoint, options = {}) => {
    const headers = { 
      ...options.headers, 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
      if (res.status === 401) { logout(); return null; }
      return res;
    } catch (error) {
      console.error(error);
      return null;
    }
  };

  const fetchProducts = async () => {
    setLoading(true);
    const res = await authFetch('/admin/products');
    if (res && res.ok) {
      const data = await res.json();
      setProducts(data);
    } else {
      const errorStatus = res ? res.status : 'Network Error';
      setStatusMsg({ text: `Failed to load catalog. Error Code: ${errorStatus}`, type: 'error' });
    }
    setLoading(false);
  };

  useEffect(() => { fetchProducts(); }, []);

  const handleAddProduct = async (e) => {
    e.preventDefault();
    setLoading(true);
    const res = await authFetch('/admin/products', {
      method: 'POST',
      body: JSON.stringify(newProduct)
    });

    if (res && res.ok) {
      const savedProduct = await res.json();
      setProducts([...products, savedProduct]);
      setIsModalOpen(false);
      setNewProduct({ sku: '', name: '', category: '', price: 0, stock_quantity: 0, description: '', image_url: '' });
      setStatusMsg({ text: 'Product added and synced to Neo4j!', type: 'success' });
    } else {
      setStatusMsg({ text: 'Failed to add product. Check if SKU is unique.', type: 'error' });
    }
    setLoading(false);
  };

  const openEditModal = (product) => {
    setEditProduct({ ...product });
    setIsEditModalOpen(true);
  };

  const handleEditProduct = async (e) => {
    e.preventDefault();
    setLoading(true);
    const res = await authFetch(`/admin/products/${editProduct.sku}`, {
      method: 'PATCH',
      body: JSON.stringify(editProduct)
    });

    if (res && res.ok) {
      const updatedProduct = await res.json();
      setProducts(products.map(p => p.sku === updatedProduct.sku ? updatedProduct : p));
      setIsEditModalOpen(false);
      setStatusMsg({ text: 'Product updated and synced to AI Agent.', type: 'success' });
    } else {
      setStatusMsg({ text: 'Failed to update product.', type: 'error' });
    }
    setLoading(false);
  };

  const deleteProduct = async (sku) => {
    if (!window.confirm(`Delete product ${sku}?`)) return;
    const res = await authFetch(`/admin/products/${sku}`, { method: 'DELETE' });
    if (res && res.ok) {
      setProducts(products.filter(p => p.sku !== sku));
      setStatusMsg({ text: 'Product deleted successfully.', type: 'success' });
    }
  };

  // --- NEW: Dynamic Categories Extraction ---
  // This looks at all products and extracts unique categories. "All" is added at the beginning.
  const uniqueCategories = ['All', ...new Set(products.map(p => p.category).filter(Boolean))];

  // --- UPDATED: Filter Logic ---
  // Now filters by BOTH the search bar AND the category dropdown
  const filteredProducts = products.filter(p => {
    const matchesSearch = p.sku.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          p.name.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCategory = selectedCategory === 'All' || p.category === selectedCategory;
    
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6">
      {/* Header Area */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Package className="text-blue-600" /> Inventory
          </h1>
          <p className="text-sm text-gray-500 mt-1">Manage PostgreSQL items and Neo4j Graph nodes.</p>
        </div>

        {/* --- UPDATED: Controls Area --- */}
        <div className="flex flex-wrap items-center gap-3">
          
          {/* 1. Category Dropdown Filter */}
          <div className="relative flex items-center border border-gray-300 rounded-md bg-gray-50 hover:bg-white transition-colors">
            <ListFilter className="absolute left-3 text-gray-400" size={16} />
            <select 
              className="appearance-none pl-9 pr-8 py-2 w-full md:w-auto bg-transparent text-sm font-medium text-gray-700 outline-none cursor-pointer focus:ring-2 focus:ring-blue-500 rounded-md"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              {uniqueCategories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            {/* Custom dropdown arrow */}
            <div className="pointer-events-none absolute right-3 flex items-center text-gray-400">
              <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
            </div>
          </div>

          {/* 2. Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
            <input 
              type="text" 
              placeholder="Search SKU or Name..." 
              className="pl-10 pr-4 py-2 border rounded-md text-sm outline-none focus:ring-2 focus:ring-blue-500 w-full md:w-48 lg:w-64"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          {/* 3. Add Button */}
          <button 
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 shadow-md whitespace-nowrap"
          >
            <Plus size={18} /> Add Product
          </button>
        </div>
      </div>

      {statusMsg.text && (
        <div className={`p-4 rounded-md flex items-center gap-2 ${statusMsg.type === 'error' ? 'bg-red-50 text-red-800 border border-red-100' : 'bg-green-50 text-green-800 border border-green-100'}`}>
          <AlertCircle size={18} />
          <span className="text-sm font-medium">{statusMsg.text}</span>
          <button onClick={() => setStatusMsg({text:'', type:''})} className="ml-auto text-xs opacity-50 hover:opacity-100 uppercase tracking-wider font-bold">Dismiss</button>
        </div>
      )}

      {/* Product Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-gray-200 text-xs uppercase font-bold text-slate-600">
              <th className="p-4">SKU</th>
              <th className="p-4">Name</th>
              <th className="p-4">Category</th>
              <th className="p-4">Price (LKR)</th>
              <th className="p-4">Stock</th>
              <th className="p-4 text-center">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading && products.length === 0 ? (
              <tr><td colSpan="6" className="p-10 text-center text-gray-400">Loading catalog...</td></tr>
            ) : filteredProducts.length === 0 ? (
               <tr><td colSpan="6" className="p-10 text-center text-gray-400 italic">No products found matching your search or category.</td></tr>
            ) : filteredProducts.map((p) => (
              <tr key={p.sku} className="hover:bg-slate-50 transition-colors">
                <td className="p-4 font-mono text-xs font-bold text-blue-700">{p.sku}</td>
                <td className="p-4 text-sm font-medium text-slate-800">{p.name}</td>
                <td className="p-4 text-sm text-slate-500">
                   {/* Styled category pill */}
                   <span className="bg-gray-100 px-2 py-1 rounded-md border border-gray-200 text-xs">{p.category}</span>
                </td>
                <td className="p-4 text-sm font-bold text-slate-900">{p.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                <td className={`p-4 text-sm font-bold ${p.stock_quantity < 10 ? 'text-red-500' : 'text-green-600'}`}>
                  {p.stock_quantity}
                </td>
                <td className="p-4 flex justify-center gap-2">
                  <button onClick={() => openEditModal(p)} className="p-2 text-blue-600 hover:bg-blue-50 rounded-full" title="Edit"><Edit3 size={16} /></button>
                  <button onClick={() => deleteProduct(p.sku)} className="p-2 text-red-600 hover:bg-red-50 rounded-full" title="Delete"><Trash2 size={16} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* --- ADD PRODUCT MODAL --- */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-in zoom-in duration-200">
            <div className="bg-slate-900 text-white p-4 flex justify-between items-center">
              <h3 className="font-bold flex items-center gap-2"><Plus size={18}/> New Product</h3>
              <button onClick={() => setIsModalOpen(false)}><X size={20}/></button>
            </div>
            <form onSubmit={handleAddProduct} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase">SKU Code*</label>
                  <input required className="w-full mt-1 p-2 border rounded" value={newProduct.sku} onChange={e => setNewProduct({...newProduct, sku: e.target.value})} />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase">Category</label>
                  <input required className="w-full mt-1 p-2 border rounded" value={newProduct.category} onChange={e => setNewProduct({...newProduct, category: e.target.value})} />
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase">Product Name*</label>
                <input required className="w-full mt-1 p-2 border rounded" value={newProduct.name} onChange={e => setNewProduct({...newProduct, name: e.target.value})} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase">Price (Rs)*</label>
                  <input required type="number" className="w-full mt-1 p-2 border rounded" value={newProduct.price} onChange={e => setNewProduct({...newProduct, price: e.target.value})} />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase">Stock Qty*</label>
                  <input required type="number" className="w-full mt-1 p-2 border rounded" value={newProduct.stock_quantity} onChange={e => setNewProduct({...newProduct, stock_quantity: e.target.value})} />
                </div>
              </div>
              <button type="submit" disabled={loading} className="w-full bg-blue-600 text-white py-3 rounded-lg font-bold flex items-center justify-center gap-2 hover:bg-blue-700 disabled:opacity-50">
                <Save size={18}/> {loading ? 'Saving...' : 'Save Product & Sync AI'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* --- EDIT PRODUCT MODAL --- */}
      {isEditModalOpen && editProduct && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-in zoom-in duration-200">
            <div className="bg-slate-900 text-white p-4 flex justify-between items-center">
              <h3 className="font-bold flex items-center gap-2"><Edit3 size={18}/> Edit Product</h3>
              <button onClick={() => setIsEditModalOpen(false)}><X size={20}/></button>
            </div>
            <form onSubmit={handleEditProduct} className="p-6 space-y-4">
              <div className="bg-gray-50 p-3 rounded border border-gray-200 mb-4">
                <span className="text-xs font-bold text-gray-500 uppercase block">Editing SKU</span>
                <span className="font-mono font-bold text-blue-700">{editProduct.sku}</span>
              </div>
              
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase">Product Name</label>
                <input required className="w-full mt-1 p-2 border rounded" value={editProduct.name} onChange={e => setEditProduct({...editProduct, name: e.target.value})} />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase">Category</label>
                <input required className="w-full mt-1 p-2 border rounded" value={editProduct.category} onChange={e => setEditProduct({...editProduct, category: e.target.value})} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase">Price (Rs)</label>
                  <input required type="number" className="w-full mt-1 p-2 border rounded" value={editProduct.price} onChange={e => setEditProduct({...editProduct, price: parseFloat(e.target.value)})} />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase">Stock Qty</label>
                  <input required type="number" className="w-full mt-1 p-2 border rounded" value={editProduct.stock_quantity} onChange={e => setEditProduct({...editProduct, stock_quantity: parseInt(e.target.value)})} />
                </div>
              </div>
              <button type="submit" disabled={loading} className="w-full bg-blue-600 text-white py-3 rounded-lg font-bold flex items-center justify-center gap-2 hover:bg-blue-700 disabled:opacity-50">
                <Save size={18}/> {loading ? 'Updating...' : 'Update Product & Sync AI'}
              </button>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}