import React, { useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Shield } from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const LoginPage: React.FC = () => {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) {
      navigate('/dashboard', { replace: true });
    }
  }, [user, loading, navigate]);

  if (loading) {
    return null; // Or a subtle loader
  }

  return (
    <div className="min-h-screen bg-premium-bg flex items-center justify-center p-4 relative overflow-hidden font-outfit">
      {/* Background Orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-blue-600/5 blur-[140px] rounded-full animate-pulse-slow" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-premium-accent/5 blur-[140px] rounded-full animate-pulse-slow" />

      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="max-w-md w-full glass-medium rounded-[2.5rem] p-12 shadow-2xl relative z-10 border-white/5"
      >
        <div className="text-center mb-10">
          <motion.div 
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="inline-flex items-center justify-center p-5 bg-premium-accent/10 rounded-2xl mb-8 shadow-inner-glow"
          >
            <Shield className="w-10 h-10 text-premium-accent" />
          </motion.div>
          <h1 className="text-4xl font-bold text-white mb-2 tracking-tight">GemmaWatch <span className="text-premium-accent italic">AI</span></h1>
          <p className="text-slate-500 font-medium">Autonomous Observability Platform</p>
        </div>

        <div className="space-y-4">
          <button
            onClick={() => login('google')}
            className="w-full h-14 bg-white text-slate-900 font-semibold rounded-xl flex items-center justify-center gap-3 hover:bg-slate-100 transition-all active:scale-[0.98] shadow-lg shadow-white/5"
          >
            <img 
              src="https://www.gstatic.com/images/branding/product/1x/gsa_512dp.png" 
              alt="Google" 
              className="w-6 h-6"
            />
            Continue with Google
          </button>

          <button
            onClick={() => login('github')}
            className="w-full h-14 bg-[#24292e] text-white font-semibold rounded-xl flex items-center justify-center gap-3 hover:bg-[#2b3137] transition-all active:scale-[0.98] border border-white/10 shadow-lg shadow-black/20"
          >
            <Shield className="w-6 h-6" />
            Continue with GitHub
          </button>
        </div>

        <div className="mt-10 pt-8 border-t border-white/5 text-center">
          <p className="text-xs text-slate-500 leading-relaxed">
            By signing in, you agree to our Terms of Service.<br />
            Sign-in is required for administrative actions and RCA verification.
          </p>
        </div>
      </motion.div>
    </div>
  );
};

export default LoginPage;
