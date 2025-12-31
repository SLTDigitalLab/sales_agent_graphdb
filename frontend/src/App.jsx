import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import DashboardLayout from './components/DashboardLayout'; // Import Layout

import Chat from './pages/Chat';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

const ProtectedRoute = ({ children }) => {
  const { token } = useAuth();
  if (!token) return <Navigate to="/admin/login" replace />;
  return children;
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Chat */}
          <Route path="/" element={<Chat />} />

          {/* Admin Login */}
          <Route path="/admin/login" element={<Login />} />

          {/* Admin Protected Routes (Wrapped in Layout) */}
          <Route path="/admin" element={
            <ProtectedRoute>
              <DashboardLayout /> {/* Layout wraps the routes inside */}
            </ProtectedRoute>
          }>
            {/* The index route renders Dashboard.jsx inside the Layout's <Outlet /> */}
            <Route index element={<Dashboard />} />
            
            {/* Future: You can add more admin pages here effortlessly */}
            {/* <Route path="settings" element={<SettingsPage />} /> */}
          </Route>

        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}