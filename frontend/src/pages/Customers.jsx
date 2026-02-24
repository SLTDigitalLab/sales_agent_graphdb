import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  Users, 
  Eye, 
  AlertCircle, 
  X,
  Mail,
  Calendar,
  ShoppingBag,
  Shield
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Customers() {
  const { token, logout } = useAuth();
  const [customers, setCustomers] = useState([]);
  const [allOrders, setAllOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState({ text: '', type: '' });
  
  // Modal State
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [customerOrders, setCustomerOrders] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);

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

  const fetchData = async () => {
    setLoading(true);
    // Fetch both customers and orders so we can match them up in the modal
    const [custRes, ordRes] = await Promise.all([
      authFetch('/admin/customers'),
      authFetch('/admin/orders')
    ]);

    if (custRes?.ok && ordRes?.ok) {
      setCustomers(await custRes.json());
      setAllOrders(await ordRes.json());
    } else {
      setStatusMsg({ text: 'Failed to load customer data.', type: 'error' });
    }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  const openCustomerModal = (customer) => {
    setSelectedCustomer(customer);
    // Find all orders that belong to this specific customer
    const history = allOrders.filter(o => o.customer_id === customer.id);
    setCustomerOrders(history);
    setIsModalOpen(true);
  };

  const formatDate = (dateString) => {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  const getStatusBadge = (status) => {
    switch(status?.toUpperCase()) {
      case 'PENDING': return <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-md text-[10px] font-bold">PENDING</span>;
      case 'SHIPPED': return <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded-md text-[10px] font-bold">SHIPPED</span>;
      case 'DELIVERED': return <span className="px-2 py-1 bg-green-100 text-green-800 rounded-md text-[10px] font-bold">DELIVERED</span>;
      case 'CANCELLED': return <span className="px-2 py-1 bg-red-100 text-red-800 rounded-md text-[10px] font-bold">CANCELLED</span>;
      default: return <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-md text-[10px] font-bold">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Area */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Users className="text-blue-600" /> User Management
          </h1>
          <p className="text-sm text-gray-500 mt-1">View registered customers and their order histories.</p>
        </div>
      </div>

      {statusMsg.text && (
        <div className="p-4 rounded-md bg-red-50 text-red-800 border border-red-100 flex items-center gap-2">
          <AlertCircle size={18} />
          <span className="text-sm font-medium">{statusMsg.text}</span>
          <button onClick={() => setStatusMsg({text:'', type:''})} className="ml-auto text-xs uppercase font-bold">Dismiss</button>
        </div>
      )}

      {/* Customers Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-gray-200 text-xs uppercase font-bold text-slate-600">
              <th className="p-4">ID</th>
              <th className="p-4">Full Name</th>
              <th className="p-4">Email</th>
              <th className="p-4">Role</th>
              <th className="p-4">Joined</th>
              <th className="p-4 text-center">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan="6" className="p-10 text-center text-gray-400">Loading customers...</td></tr>
            ) : customers.length === 0 ? (
               <tr><td colSpan="6" className="p-10 text-center text-gray-400 italic">No customers found.</td></tr>
            ) : customers.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                <td className="p-4 font-mono text-sm font-bold text-blue-700">#{c.id}</td>
                <td className="p-4 text-sm font-medium text-slate-800">{c.full_name || 'N/A'}</td>
                <td className="p-4 text-sm text-slate-600">{c.email}</td>
                <td className="p-4">
                  <span className={`px-2 py-1 rounded-md text-xs font-bold ${c.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'}`}>
                    {c.role}
                  </span>
                </td>
                <td className="p-4 text-sm text-slate-500">{formatDate(c.created_at)}</td>
                <td className="p-4 flex justify-center">
                  <button 
                    onClick={() => openCustomerModal(c)} 
                    className="flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded transition-colors"
                  >
                    <Eye size={14} /> View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* --- CUSTOMER DETAILS MODAL --- */}
      {isModalOpen && selectedCustomer && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl overflow-hidden animate-in zoom-in duration-200">
            {/* Modal Header */}
            <div className="bg-slate-900 text-white p-5 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-lg flex items-center gap-2">Customer Profile</h3>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white"><X size={24}/></button>
            </div>
            
            <div className="p-6">
              {/* Profile Card */}
              <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded-lg border border-gray-200 mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-lg">
                    {selectedCustomer.full_name ? selectedCustomer.full_name.charAt(0).toUpperCase() : 'U'}
                  </div>
                  <div>
                    <p className="text-sm font-bold text-slate-800">{selectedCustomer.full_name || 'Unknown User'}</p>
                    <p className="text-xs text-slate-500 flex items-center gap-1"><Mail size={12}/> {selectedCustomer.email}</p>
                  </div>
                </div>
                <div className="flex flex-col justify-center items-end gap-1">
                  <p className="text-xs text-slate-500 flex items-center gap-1"><Calendar size={12}/> Joined {formatDate(selectedCustomer.created_at)}</p>
                  <p className="text-xs text-slate-500 flex items-center gap-1"><Shield size={12}/> Role: <span className="font-bold uppercase">{selectedCustomer.role}</span></p>
                </div>
              </div>

              {/* Order History Table */}
              <h4 className="font-bold text-slate-800 mb-3 border-b pb-2 flex items-center gap-2">
                <ShoppingBag size={18} className="text-blue-600"/> Order History
                <span className="ml-auto text-xs font-normal text-slate-500 bg-slate-100 px-2 py-1 rounded-full">
                  {customerOrders.length} Orders
                </span>
              </h4>
              
              <div className="overflow-x-auto border border-gray-200 rounded-lg max-h-60 overflow-y-auto">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-gray-50 text-xs uppercase font-bold text-gray-500 sticky top-0">
                    <tr>
                      <th className="p-3">Order ID</th>
                      <th className="p-3">Date</th>
                      <th className="p-3 text-right">Amount (LKR)</th>
                      <th className="p-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {customerOrders.length > 0 ? (
                      customerOrders.map((order) => (
                        <tr key={order.id} className="hover:bg-gray-50">
                          <td className="p-3 font-mono text-xs font-bold text-blue-700">#{order.id}</td>
                          <td className="p-3 text-sm text-slate-600">{formatDate(order.created_at)}</td>
                          <td className="p-3 text-sm font-bold text-slate-800 text-right">
                            {order.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                          <td className="p-3 text-center">
                            {getStatusBadge(order.status)}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr><td colSpan="4" className="p-6 text-center text-sm text-gray-400">No previous orders found for this user.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
            
          </div>
        </div>
      )}
    </div>
  );
}