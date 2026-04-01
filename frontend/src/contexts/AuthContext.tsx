import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { AlertTriangle, LogIn } from 'lucide-react';

interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string;
  role: 'admin' | 'viewer';
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAdmin: boolean;
  login: (provider: 'google' | 'github') => void;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE_URL = 'http://localhost:8002';

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSessionExpired, setSessionExpired] = useState(false);

  // Global Interceptor to catch 401 Unauthorized errors from anywhere
  useEffect(() => {
    const originalFetch = window.fetch;
    
    window.fetch = async (...args) => {
      const response = await originalFetch(...args);
      
      const url = typeof args[0] === 'string' ? args[0] : (args[0] instanceof Request ? args[0].url : '');
      
      // If the backend revokes the token, trigger the modal immediately (except on the /me or /logout endpoints)
      if (response.status === 401 && !url.includes('/auth/me') && !url.includes('/auth/logout')) {
        setSessionExpired(true);
      }
      return response;
    };

    return () => {
      window.fetch = originalFetch; // Cleanup on unmount
    };
  }, []);

  const checkAuth = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          'Accept': 'application/json',
        },
        // Credentials (cookies) are handled by the browser
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.authenticated) {
          setUser(data.user);
        } else {
          setUser(null);
        }
      } else {
        setUser(null);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = (provider: 'google' | 'github') => {
    window.location.href = `${API_BASE_URL}/auth/${provider}/login`;
  };

  const logout = async () => {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, { 
        method: 'POST',
        credentials: 'include'
      });
      setUser(null);
      window.location.href = '/login';
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const isAdmin = user?.role === 'admin';

  return (
    <AuthContext.Provider value={{ user, loading, isAdmin, login, logout, checkAuth }}>
      {children}
      {isSessionExpired && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="bg-slate-900 border border-white/10 rounded-2xl p-8 max-w-sm w-full shadow-2xl flex flex-col items-center text-center animate-in zoom-in-95 duration-300">
            <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mb-6">
              <AlertTriangle className="w-8 h-8 text-red-400" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Session Expired</h3>
            <p className="text-sm text-slate-400 mb-8">
              Your session has expired due to inactivity. For your security, please log in again to continue.
            </p>
            <button 
              onClick={() => {
                setSessionExpired(false);
                logout();
              }}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 px-6 rounded-xl transition-all shadow-lg shadow-blue-600/20"
            >
              <LogIn className="w-5 h-5" />
              Log In Again
            </button>
          </div>
        </div>
      )}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
