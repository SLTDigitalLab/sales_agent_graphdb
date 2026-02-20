import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  LayoutDashboard, 
  Settings, 
  Database, 
  LogOut, 
  MessageSquare, 
  Menu,
  X,
  ShoppingBag,
  ListOrdered
} from 'lucide-react';
import { useState } from 'react';

export default function DashboardLayout() {
  const { logout } = useAuth();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Navigation Items
  const navItems = [
    { name: 'Overview', path: '/admin', icon: <LayoutDashboard size={20} /> },
    { name: 'Products', path: '/admin/products', icon: <ShoppingBag size={20} /> },
    { name: 'Orders', path: '/admin/orders', icon: <ListOrdered size={20} /> }

    // { name: 'Chat History', path: '/admin/chats', icon: <MessageSquare size={20} /> },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      
      {/* --- SIDEBAR (Desktop) --- */}
      <aside className="hidden md:flex w-64 flex-col bg-slate-900 text-white transition-all duration-300">
        <div className="h-16 flex items-center px-6 border-b border-slate-700">
          <span className="text-xl font-bold tracking-wider">Admin<span className="text-blue-400">Panel</span></span>
        </div>

        <nav className="flex-1 py-6 px-3 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                location.pathname === item.path 
                  ? 'bg-blue-600 text-white shadow-lg' 
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              {item.icon}
              <span className="font-medium">{item.name}</span>
            </Link>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-700">
          <button 
            onClick={logout} 
            className="flex w-full items-center gap-3 px-4 py-2 text-slate-300 hover:text-white hover:bg-red-500/20 rounded-lg transition-all"
          >
            <LogOut size={20} />
            <span className="font-medium">Sign Out</span>
          </button>
        </div>
      </aside>

      {/* --- MAIN CONTENT AREA --- */}
      <div className="flex-1 flex flex-col overflow-hidden">
        
        {/* Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shadow-sm">
          <button 
            className="md:hidden p-2 text-gray-600" 
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X /> : <Menu />}
          </button>
          
          <h2 className="text-lg font-semibold text-gray-700">
            {navItems.find(i => i.path === location.pathname)?.name || 'Dashboard'}
          </h2>

          <div className="flex items-center gap-4">
             {/* Link back to the public chatbot */}
            <Link to="/" target="_blank" className="text-sm text-blue-600 hover:underline flex items-center gap-1">
              Live Chat <MessageSquare size={14}/>
            </Link>
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-xs">
              AD
            </div>
          </div>
        </header>

        {/* Content (Scrollable) */}
        <main className="flex-1 overflow-auto p-6">
          {/* Outlet is where React Router renders 'Dashboard.jsx' */}
          <Outlet />
        </main>
      </div>

    </div>
  );
}