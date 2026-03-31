import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { 
  X, Send, Bot, User, 
  Loader2, Sparkles
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  query_type?: 'structured' | 'semantic';
  sources?: any[];
  created_at?: string;
}

const API_BASE_URL = 'http://localhost:8002';

interface ChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

const ChatDrawer: React.FC<ChatDrawerProps> = ({ isOpen, onClose }) => {
  const {  } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => Math.random().toString(36).substring(7));
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input, session_id: sessionId }),
        credentials: 'include'
      });
      const data = await response.json();
      
      const assistantMsg: Message = { 
        role: 'assistant', 
        content: data.answer, 
        query_type: data.query_type,
        sources: data.sources
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      console.error('Chat failed:', err);
      setMessages(prev => [...prev, { role: 'assistant', content: 'I encountered an error connecting to the intelligence engine. Please try again later.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60]"
          />
          
          {/* Drawer */}
          <motion.div 
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 h-full w-full max-w-lg bg-[#0a0a1a] border-l border-white/10 z-[70] shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="p-6 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/10 rounded-xl">
                  <Sparkles className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Gemma Analysis</h3>
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Scoped Intelligence Engine</p>
                </div>
              </div>
              <button 
                onClick={onClose}
                className="p-2 hover:bg-white/5 rounded-full text-slate-400 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Messages Area */}
            <div 
              ref={scrollRef}
              className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-white/10"
            >
              {messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-center px-10">
                  <div className="w-20 h-20 bg-blue-500/5 rounded-full flex items-center justify-center mb-6">
                    <Bot className="w-10 h-10 text-blue-500/30" />
                  </div>
                  <h4 className="text-white font-bold mb-2">How can I help you today?</h4>
                  <p className="text-slate-500 text-sm mb-8">Ask about system performance, recent incidents, or specific site root causes.</p>
                  
                  <div className="grid gap-3 w-full">
                    {[
                      "Summarize incidents in the last 24h",
                      "Which sites have the worst response time?",
                      "What are the most common repair actions?",
                      "Are there any anomalous patterns right now?"
                    ].map((q, i) => (
                      <button 
                        key={i}
                        onClick={() => setInput(q)}
                        className="p-3 bg-white/5 border border-white/10 rounded-xl text-left text-xs text-slate-400 hover:border-blue-500/30 hover:text-white transition-all"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg, idx) => (
                <div 
                  key={idx}
                  className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                    msg.role === 'user' ? 'bg-blue-600' : 'bg-white/10'
                  }`}>
                    {msg.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-blue-400" />}
                  </div>
                  
                  <div className={`max-w-[85%] space-y-2`}>
                    <div className={`p-4 rounded-2xl text-sm leading-relaxed ${
                      msg.role === 'user' 
                        ? 'bg-blue-600 text-white rounded-tr-none' 
                        : 'bg-white/5 text-slate-200 border border-white/10 rounded-tl-none'
                    }`}>
                      {msg.content}
                    </div>

                    {msg.role === 'assistant' && msg.query_type && (
                      <div className="flex items-center gap-2 px-2">
                        <span className="text-[10px] font-bold text-slate-600 uppercase">
                          {msg.query_type === 'structured' ? 'SQL Analysis' : 'Semantic RAG'}
                        </span>
                        {msg.sources && msg.sources.length > 0 && (
                          <div className="flex gap-1">
                            {msg.sources.map((_, i) => (
                              <div key={i} className="w-1 h-1 bg-blue-500/50 rounded-full" />
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex gap-4">
                  <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center shrink-0">
                    <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  </div>
                  <div className="bg-white/5 text-slate-500 p-4 rounded-2xl rounded-tl-none text-sm animate-pulse">
                    Thinking...
                  </div>
                </div>
              )}
            </div>

            {/* Input Area */}
            <form 
              onSubmit={handleSend}
              className="p-6 bg-white/[0.02] border-t border-white/10"
            >
              <div className="relative group">
                <input 
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder="Ask GemmaWatch anything..."
                  disabled={loading}
                  className="w-full h-14 bg-white/5 border border-white/10 rounded-2xl px-6 pr-14 text-white placeholder:text-slate-600 focus:outline-none focus:border-blue-500/50 transition-all focus:ring-4 focus:ring-blue-500/5"
                />
                <button 
                  type="submit"
                  disabled={!input.trim() || loading}
                  className="absolute right-2 top-2 h-10 w-10 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl flex items-center justify-center transition-all shadow-lg shadow-blue-600/20 active:scale-95"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
              <p className="text-[10px] text-center text-slate-600 mt-4">
                Chat scoped to monitoring data and Approved Catalogue.
              </p>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default ChatDrawer;
