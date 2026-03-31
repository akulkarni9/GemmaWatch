import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import ChatDrawer from '../chat/ChatDrawer';

const Layout: React.FC = () => {
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <div className="min-h-screen bg-premium-bg selection:bg-premium-accent/30 selection:text-premium-accent font-outfit relative overflow-hidden">
      <Navbar onChatToggle={() => setIsChatOpen(true)} />
      
      <main className="relative z-10 pt-4">
        <Outlet />
      </main>

      <ChatDrawer 
        isOpen={isChatOpen} 
        onClose={() => setIsChatOpen(false)} 
      />

      {/* Global Background Elements */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        {/* Ambient Glows */}
        <div className="absolute top-[-10%] right-[-10%] w-[60%] h-[60%] bg-blue-600/5 blur-[140px] rounded-full opacity-50 animate-pulse-slow" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[60%] h-[60%] bg-emerald-600/5 blur-[140px] rounded-full opacity-50 animate-pulse-slow" />
        <div className="absolute top-[20%] left-[10%] w-[30%] h-[30%] bg-purple-600/3 blur-[120px] rounded-full opacity-30 animate-float" />
        
        {/* Fine Noise Texture */}
        <div className="absolute inset-0 bg-[#000] opacity-[0.015] mix-blend-overlay" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-premium-bg/50 to-premium-bg" />
      </div>
    </div>
  );
};

export default Layout;
