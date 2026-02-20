import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  ListOrdered, 
  Eye, 
  AlertCircle, 
  X,
  Package,
  Clock,
  CheckCircle,
  Truck
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Orders() {
  const { token, logout } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState({ text: '', type: '' });
  
  // Modal State
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);

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

  const fetchOrders = async () => {
    setLoading(true);
    const res = await authFetch('/admin/orders');
    if (res && res.ok) {
      const data = await res.json();
      setOrders(data);
    } else {
      const errorStatus = res ? res.status : 'Network Error';
      setStatusMsg({ text: `Failed to load orders. Error Code: ${errorStatus}`, type: 'error' });
    }
    setLoading(false);
  };

  useEffect(() => { fetchOrders(); }, []);

  const handleUpdateStatus = async (orderId, newStatus) => {
    setUpdatingStatus(true);
    const res = await authFetch(`/admin/orders/${orderId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus })
    });

    if (res && res.ok) {
      const updatedOrder = await res.json();
      // Update the specific order in our state array
      setOrders(orders.map(o => o.id === updatedOrder.id ? updatedOrder : o));
      // Update the modal's selected order so the UI refreshes immediately
      setSelectedOrder(updatedOrder);
      setStatusMsg({ text: `Order #${orderId} status updated to ${newStatus}.`, type: 'success' });
    } else {
      setStatusMsg({ text: 'Failed to update order status.', type: 'error' });
    }
    setUpdatingStatus(false);
  };

  const openOrderModal = (order) => {
    setSelectedOrder(order);
    setIsModalOpen(true);
  };

  // Utility to format the date
  const formatDate = (dateString) => {
    const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  // Utility to get a nice color badge for the status
  const getStatusBadge = (status) => {
    switch(status?.toUpperCase()) {
      case 'PENDING': return <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-md text-xs font-bold flex items-center gap-1 w-max"><Clock size={12}/> PENDING</span>;
      case 'PROCESSING': return <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-md text-xs font-bold flex items-center gap-1 w-max"><Package size={12}/> PROCESSING</span>;
      case 'SHIPPED': return <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded-md text-xs font-bold flex items-center gap-1 w-max"><Truck size={12}/> SHIPPED</span>;
      case 'DELIVERED': return <span className="px-2 py-1 bg-green-100 text-green-800 rounded-md text-xs font-bold flex items-center gap-1 w-max"><CheckCircle size={12}/> DELIVERED</span>;
      case 'CANCELLED': return <span className="px-2 py-1 bg-red-100 text-red-800 rounded-md text-xs font-bold flex items-center gap-1 w-max"><X size={12}/> CANCELLED</span>;
      default: return <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded-md text-xs font-bold">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Area */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <ListOrdered className="text-blue-600" /> Order Management
          </h1>
          <p className="text-sm text-gray-500 mt-1">View customer orders, manage statuses, and track fulfillment.</p>
        </div>
      </div>

      {statusMsg.text && (
        <div className={`p-4 rounded-md flex items-center gap-2 ${statusMsg.type === 'error' ? 'bg-red-50 text-red-800 border border-red-100' : 'bg-green-50 text-green-800 border border-green-100'}`}>
          <AlertCircle size={18} />
          <span className="text-sm font-medium">{statusMsg.text}</span>
          <button onClick={() => setStatusMsg({text:'', type:''})} className="ml-auto text-xs opacity-50 hover:opacity-100 uppercase tracking-wider font-bold">Dismiss</button>
        </div>
      )}

      {/* Orders Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-gray-200 text-xs uppercase font-bold text-slate-600">
              <th className="p-4">Order ID</th>
              <th className="p-4">Date</th>
              <th className="p-4">Customer ID</th>
              <th className="p-4">Total Amount (LKR)</th>
              <th className="p-4">Status</th>
              <th className="p-4 text-center">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading && orders.length === 0 ? (
              <tr><td colSpan="6" className="p-10 text-center text-gray-400">Loading orders...</td></tr>
            ) : orders.length === 0 ? (
               <tr><td colSpan="6" className="p-10 text-center text-gray-400 italic">No orders found.</td></tr>
            ) : orders.map((o) => (
              <tr key={o.id} className="hover:bg-slate-50 transition-colors">
                <td className="p-4 font-mono text-sm font-bold text-blue-700">#{o.id}</td>
                <td className="p-4 text-sm text-slate-500">{formatDate(o.created_at)}</td>
                <td className="p-4 text-sm font-medium text-slate-800">{o.customer_id}</td>
                <td className="p-4 text-sm font-bold text-slate-900">{o.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                <td className="p-4">{getStatusBadge(o.status)}</td>
                <td className="p-4 flex justify-center">
                  <button 
                    onClick={() => openOrderModal(o)} 
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

      {/* --- ORDER DETAILS MODAL --- */}
      {isModalOpen && selectedOrder && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl overflow-hidden animate-in zoom-in duration-200">
            {/* Modal Header */}
            <div className="bg-slate-900 text-white p-5 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-lg flex items-center gap-2">Order #{selectedOrder.id}</h3>
                <p className="text-xs text-slate-400 mt-1">{formatDate(selectedOrder.created_at)} | Customer ID: {selectedOrder.customer_id}</p>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white"><X size={24}/></button>
            </div>
            
            <div className="p-6">
              {/* Status Updater */}
              <div className="flex items-center justify-between bg-gray-50 p-4 rounded-lg border border-gray-200 mb-6">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-bold text-gray-500 uppercase">Current Status:</span>
                  {getStatusBadge(selectedOrder.status)}
                </div>
                <div className="flex items-center gap-2">
                  <select 
                    className="p-2 border border-gray-300 rounded text-sm outline-none focus:border-blue-500"
                    defaultValue=""
                    onChange={(e) => {
                      if(e.target.value) handleUpdateStatus(selectedOrder.id, e.target.value);
                      e.target.value = ""; // Reset dropdown after selection
                    }}
                    disabled={updatingStatus}
                  >
                    <option value="" disabled>Change Status...</option>
                    <option value="PENDING">Pending</option>
                    <option value="PROCESSING">Processing</option>
                    <option value="SHIPPED">Shipped</option>
                    <option value="DELIVERED">Delivered</option>
                    <option value="CANCELLED">Cancelled</option>
                  </select>
                </div>
              </div>

              {/* Items Table */}
              <h4 className="font-bold text-slate-800 mb-3 border-b pb-2">Order Items</h4>
              <div className="overflow-x-auto border border-gray-200 rounded-lg max-h-60 overflow-y-auto">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-gray-50 text-xs uppercase font-bold text-gray-500 sticky top-0">
                    <tr>
                      <th className="p-3">SKU</th>
                      <th className="p-3 text-center">Qty</th>
                      <th className="p-3 text-right">Unit Price</th>
                      <th className="p-3 text-right">Subtotal</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {selectedOrder.items && selectedOrder.items.length > 0 ? (
                      selectedOrder.items.map((item, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="p-3 font-mono text-xs text-blue-700">{item.sku || `Prod ID: ${item.product_id}`}</td>
                          <td className="p-3 text-sm text-center">{item.quantity}</td>
                          <td className="p-3 text-sm text-right text-gray-600">{(item.unit_price || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                          <td className="p-3 text-sm font-bold text-slate-800 text-right">
                            {((item.unit_price || 0) * item.quantity).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr><td colSpan="4" className="p-4 text-center text-sm text-gray-400">No items found for this order.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Total */}
              <div className="mt-4 text-right">
                <span className="text-gray-500 font-bold uppercase text-xs mr-4">Total Amount</span>
                <span className="text-2xl font-black text-slate-900">
                  Rs. {selectedOrder.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>
            
          </div>
        </div>
      )}

    </div>
  );
}