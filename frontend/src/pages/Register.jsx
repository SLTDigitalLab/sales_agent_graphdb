import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Register() {
  const [formData, setFormData] = useState({ full_name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Registration failed');
      }

      setSuccess(true);
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100">
      <div className="w-full max-w-md bg-white p-8 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold text-center mb-6">Create Account</h2>
        {success ? (
          <p className="text-green-600 text-center">Account Created! Redirecting to login...</p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="text"
              placeholder="Full Name"
              required
              className="w-full px-3 py-2 border rounded-md"
              onChange={(e) => setFormData({...formData, full_name: e.target.value})}
            />
            <input
              type="email"
              placeholder="Email"
              required
              className="w-full px-3 py-2 border rounded-md"
              onChange={(e) => setFormData({...formData, email: e.target.value})}
            />
            <input
              type="password"
              placeholder="Password"
              required
              className="w-full px-3 py-2 border rounded-md"
              onChange={(e) => setFormData({...formData, password: e.target.value})}
            />
            {error && <p className="text-red-600 text-sm">{error}</p>}
            <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700">
              Register
            </button>
          </form>
        )}
        <p className="mt-4 text-center text-sm">
          Already have an account? <Link label="Login here" to="/login" className="text-blue-600">Login here</Link>
        </p>
      </div>
    </div>
  );
}