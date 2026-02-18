import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import DashboardLayout from './components/DashboardLayout'; 

import Chat from './pages/Chat';
import AdminLogin from './pages/AdminLogin';
import UserLogin from './pages/UserLogin'; 
import Register from './pages/Register';   
import Dashboard from './pages/Dashboard';
import Products from './pages/Products';

const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { token } = useAuth();
  
  if (!token) {
    return <Navigate to={adminOnly ? "/admin/login" : "/login"} replace />;
  }
  return children;
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Landing (Optional: can redirect to login or chat) */}
          <Route path="/" element={<Navigate to="/chat" replace />} />

          {/* User Auth Routes */}
          <Route path="/login" element={<UserLogin />} />
          <Route path="/register" element={<Register />} />

          {/* User Protected Chat */}
          <Route path="/chat" element={
            <ProtectedRoute>
              <Chat />
            </ProtectedRoute>
          } />

          {/* Admin Auth */}
          <Route path="/admin/login" element={<AdminLogin/>} />

          {/* Admin Protected Routes */}
          <Route path="/admin" element={
            <ProtectedRoute adminOnly={true}>
              <DashboardLayout />
            </ProtectedRoute>
          }>
            <Route index element={<Dashboard />} />
            <Route path="products" element={<Products />} />
          </Route>

          {/* Fallback for 404s */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}