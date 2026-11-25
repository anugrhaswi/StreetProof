import { useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Shield, LogIn } from 'lucide-react';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import { useToast } from '../../components/Toast';
import { ApiError } from '../../services/api';

export default function AdminLogin() {
  const { login, admin } = useAdminAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const from = (location.state as { from?: string } | null)?.from || '/admin';

  if (admin?.authenticated) {
    navigate(from, { replace: true });
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      toast.error('Username and password are required.');
      return;
    }
    setSubmitting(true);
    try {
      await login(username.trim(), password);
      toast.success('Signed in successfully.');
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 429) toast.error('Too many login attempts. Please try again later.');
        else if (err.status === 401) toast.error('Invalid username or password.');
        else toast.error('Unable to sign in. Please try again.');
      } else {
        toast.error('Unable to sign in. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-md bg-gray-900/60 border border-gray-800 rounded-2xl p-8 shadow-xl">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-brand-500/10 border border-brand-500/20">
            <Shield size={22} className="text-brand-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-white">Admin Login</h1>
            <p className="text-sm text-gray-400">Sign in to manage StreetProof</p>
          </div>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label htmlFor="admin-username" className="block text-sm text-gray-300 mb-1.5">Username</label>
            <input
              id="admin-username"
              name="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg bg-gray-950 border border-gray-700 text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500"
              disabled={submitting}
              required
            />
          </div>
          <div>
            <label htmlFor="admin-password" className="block text-sm text-gray-300 mb-1.5">Password</label>
            <input
              id="admin-password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg bg-gray-950 border border-gray-700 text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500"
              disabled={submitting}
              required
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-brand-500 hover:bg-brand-400 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium transition-colors"
          >
            <LogIn size={16} />
            {submitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  );
}
