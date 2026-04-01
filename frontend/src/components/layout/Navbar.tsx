import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { 
  BarChart3, ShieldAlert, Database, 
  Settings, LogIn, LogOut, User,
  Sparkles, Menu, X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface NavbarProps {
  onChatToggle: () => void;
}

const Navbar: React.FC<NavbarProps> = ({ onChatToggle }) => {
  const { user, isAdmin, logout } = useAuth();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navLinks = [
    { name: 'Dashboard', path: '/', icon: BarChart3, public: true },
    { name: 'Incidents', path: '/incidents', icon: ShieldAlert, public: true },
    { name: 'Catalogue', path: '/catalogue', icon: Database, adminOnly: true },
    { name: 'Settings', path: '/settings', icon: Settings, adminOnly: true },
  ];

  const filteredLinks = navLinks.filter(link => {
    if (link.adminOnly) return isAdmin;
    return true;
  });

  return (
    <nav className="sticky top-0 z-50 bg-[#050510]/80 backdrop-blur-xl border-b border-white/10">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-20">
          <div className="flex items-center">
            <Link to="/" className="flex items-center gap-3 group">
              <div className="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-600/30 group-hover:scale-110 transition-transform">
                <BarChart3 className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold text-white tracking-tight">GemmaWatch <span className="text-blue-500">AI</span></span>
            </Link>
            
            <div className="hidden md:ml-10 md:flex md:space-x-4">
              {filteredLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                    location.pathname === link.path
                      ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <link.icon className="w-4 h-4" />
                    {link.name}
                  </div>
                </Link>
              ))}
            </div>
          </div>

          <div className="hidden md:flex items-center gap-4">
            <button
              onClick={onChatToggle}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl text-sm font-bold shadow-lg shadow-blue-600/20 hover:shadow-blue-600/40 transition-all active:scale-95"
            >
              <Sparkles className="w-4 h-4" />
              Ask Gemma
            </button>

            <div className="h-8 w-px bg-white/10 mx-2" />

            {user ? (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-3 px-3 py-1.5 bg-white/5 rounded-full border border-white/10">
                  <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center border border-blue-500/30 overflow-hidden">
                    {user.avatar_url ? (
                      <img src={user.avatar_url} alt={user.name} className="w-full h-full object-cover" />
                    ) : (
                      <User className="w-4 h-4 text-blue-400" />
                    )}
                  </div>
                  <div className="text-left hidden lg:block">
                    <p className="text-xs font-bold text-white leading-none">{user.name}</p>
                    <p className="text-[10px] text-slate-500 capitalize">{user.role}</p>
                  </div>
                </div>
                <button 
                  onClick={logout}
                  className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded-xl transition-all"
                  title="Logout"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <Link 
                to="/login"
                className="flex items-center gap-2 px-5 py-2 bg-white text-slate-900 rounded-xl text-sm font-bold hover:bg-slate-100 transition-all"
              >
                <LogIn className="w-4 h-4" />
                Sign In
              </Link>
            )}
          </div>

          <div className="-mr-2 flex items-center md:hidden">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 transition-all"
            >
              {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-[#0a0a1a] border-b border-white/10 overflow-hidden"
          >
            <div className="px-4 pt-4 pb-6 space-y-2">
              {filteredLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold ${
                    location.pathname === link.path
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <link.icon className="w-5 h-5" />
                  {link.name}
                </Link>
              ))}
              <div className="pt-4 mt-4 border-t border-white/10">
                <button
                  onClick={() => {
                    onChatToggle();
                    setIsMobileMenuOpen(false);
                  }}
                  className="flex w-full items-center gap-3 px-4 py-3 bg-blue-600 text-white rounded-xl text-sm font-bold"
                >
                  <Sparkles className="w-5 h-5" />
                  Ask Gemma
                </button>
                {!user && (
                   <Link
                      to="/login"
                      onClick={() => setIsMobileMenuOpen(false)}
                      className="flex w-full items-center gap-3 px-4 py-3 bg-white text-slate-900 rounded-xl text-sm font-bold mt-2"
                    >
                    <LogIn className="w-5 h-5" />
                    Sign In
                  </Link>
                )}
                {user && (
                   <button
                    onClick={() => {
                      logout();
                      setIsMobileMenuOpen(false);
                    }}
                    className="flex w-full items-center gap-3 px-4 py-3 text-red-400 hover:bg-red-400/10 rounded-xl text-sm font-bold mt-2"
                  >
                    <LogOut className="w-5 h-5" />
                    Sign Out
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
};

export default Navbar;
