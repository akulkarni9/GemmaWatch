import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { 
  CheckCircle2, XCircle, Database, 
  Trash2, ShieldCheck, Loader2,
  Zap, Info
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface CatalogueEntry {
  id: string;
  check_id: string;
  rca_json: string;
  confidence: number;
  category: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
}

const API_BASE_URL = 'http://localhost:8002';

const CatalogueReview: React.FC = () => {
  const { isAdmin } = useAuth();
  const [entries, setEntries] = useState<CatalogueEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'pending' | 'approved' | 'shadow'>('pending');
  const [selectedEntry, setSelectedEntry] = useState<CatalogueEntry | null>(null);
  const [reviewNote, setReviewNote] = useState('');

  const fetchEntries = async () => {
    try {
      setLoading(true);
      const endpoint = activeTab === 'pending' ? '/catalogue/pending' : 
                       activeTab === 'approved' ? '/catalogue/approved' : '/catalogue/shadow';
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: { 'Accept': 'application/json' },
        credentials: 'include'
      });
      const data = await response.json();
      setEntries(data.entries || []);
    } catch (err) {
      console.error('Failed to fetch catalogue:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) fetchEntries();
  }, [activeTab, isAdmin]);

  const handleApprove = async (id: string, editedRca?: any) => {
    try {
      await fetch(`${API_BASE_URL}/catalogue/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edited_rca: editedRca }),
        credentials: 'include'
      });
      setEntries(prev => prev.filter(e => e.id !== id));
      setSelectedEntry(null);
    } catch (err) {
      console.error('Approval failed:', err);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await fetch(`${API_BASE_URL}/catalogue/${id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: reviewNote }),
        credentials: 'include'
      });
      setEntries(prev => prev.filter(e => e.id !== id));
      setSelectedEntry(null);
      setReviewNote('');
    } catch (err) {
      console.error('Rejection failed:', err);
    }
  };

  if (!isAdmin) return <div className="p-10 text-white">Access Denied</div>;

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-6 lg:p-10 max-w-7xl mx-auto min-h-screen relative z-10"
    >
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
        <motion.div
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex items-center gap-4 mb-3">
            <div className="p-3 bg-premium-accent/10 rounded-2xl shadow-inner-glow">
              <Database className="w-8 h-8 text-premium-accent" />
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-white font-outfit">Intelligence Catalogue</h1>
          </div>
          <p className="text-slate-400 max-w-2xl leading-relaxed">Review and approve AI-generated Root Cause Analyses to seed the global knowledge base with verified patterns.</p>
        </motion.div>

        {/* Global Statistics (Optional Enhancement) */}
        <div className="flex gap-4">
          <div className="glass-thin px-5 py-3 rounded-2xl border-white/5">
            <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">Total Patterns</div>
            <div className="text-xl font-bold text-white font-mono">1,284</div>
          </div>
        </div>
      </header>

      {/* Tabs with Animated Indicator */}
      <div className="relative flex gap-1 mb-10 bg-white/[0.03] p-1.5 rounded-2xl w-fit border border-white/5 backdrop-blur-md">
        {(['pending', 'approved', 'shadow'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`relative px-8 py-2.5 rounded-xl text-sm font-bold capitalize transition-all z-10 ${
              activeTab === tab ? 'text-white' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            <span className="relative z-10 flex items-center gap-2">
              {tab}
              {tab === 'pending' && entries.length > 0 && (
                <span className="bg-premium-accent/20 text-premium-accent px-2 py-0.5 rounded-full text-[10px] tabular-nums">
                  {entries.length}
                </span>
              )}
            </span>
            {activeTab === tab && (
              <motion.div
                layoutId="tab-highlight"
                className="absolute inset-0 bg-premium-accent rounded-xl shadow-lg shadow-premium-accent/25"
                transition={{ type: "spring", bounce: 0.25, duration: 0.5 }}
              />
            )}
          </button>
        ))}
      </div>

      <div className="grid lg:grid-cols-[1fr_420px] gap-10 items-start">
        {/* List View */}
        <motion.div 
          className="space-y-4"
          initial="hidden"
          animate="visible"
          variants={{
            visible: { transition: { staggerChildren: 0.05 } }
          }}
        >
          {loading ? (
            <div className="flex flex-col items-center justify-center py-32 glass-thin rounded-[2.5rem] border-dashed">
              <Loader2 className="w-12 h-12 text-premium-accent animate-spin mb-6 opacity-50" />
              <p className="text-slate-500 font-medium tracking-wide">Synthesizing intelligence data...</p>
            </div>
          ) : entries.length === 0 ? (
            <motion.div 
              variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
              className="text-center py-24 glass-thin border-dashed border-white/10 rounded-[2.5rem]"
            >
              <ShieldCheck className="w-16 h-16 text-slate-800 mx-auto mb-6" />
              <h3 className="text-xl font-bold text-slate-500 capitalize tracking-tight">No {activeTab} entries found</h3>
              <p className="text-slate-600 mt-2">All patterns are currently synchronized.</p>
            </motion.div>
          ) : (
            entries.map((entry) => {
              let rca;
              try {
                rca = JSON.parse(entry.rca_json);
              } catch (e) {
                console.error('Failed to parse RCA JSON for entry:', entry.id);
                rca = { probable_cause: 'Data parsing error', repair_action: 'N/A' };
              }
              const isSelected = selectedEntry?.id === entry.id;
              return (
                <motion.div
                  key={entry.id}
                  variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
                  whileHover={{ y: -2, scale: 1.005 }}
                  onClick={() => setSelectedEntry(entry)}
                  className={`group relative overflow-hidden rounded-3xl p-6 cursor-pointer transition-all duration-300 ${
                    isSelected 
                      ? 'glass-thick border-premium-accent/30 bg-premium-accent/[0.05] shadow-2xl shadow-premium-accent/10' 
                      : 'glass-medium border-white/5 hover:border-white/10 hover:bg-white/[0.06]'
                  }`}
                >
                  <div className="flex items-center justify-between relative z-10">
                    <div className="flex items-center gap-5">
                      <div className={`w-12 h-12 flex items-center justify-center rounded-2xl transition-transform group-hover:scale-110 ${
                        entry.confidence > 0.8 ? 'bg-premium-accent/10 text-premium-accent' : 'bg-orange-500/10 text-orange-400'
                      }`}>
                        <Zap className="w-6 h-6" />
                      </div>
                      <div>
                        <div className="flex items-center gap-3 mb-1.5">
                          <span className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">{entry.category || 'PATTERN'}</span>
                          <span className="w-1 h-1 bg-slate-700 rounded-full" />
                          <span className="text-[10px] font-bold text-slate-600 font-mono italic">#{entry.check_id.substring(0, 8)}</span>
                        </div>
                        <h4 className="text-white font-semibold text-lg line-clamp-1 group-hover:text-premium-accent transition-colors">
                          {rca.probable_cause}
                        </h4>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className="text-[10px] uppercase font-black text-slate-600 tracking-tighter">Confidence Score</span>
                      <span className={`text-xl font-black font-mono ${entry.confidence > 0.8 ? 'text-premium-accent' : 'text-orange-400'}`}>
                        {(entry.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  
                  {/* Subtle progress bar at bottom */}
                  <div className="absolute bottom-0 left-0 h-[2px] bg-white/[0.05] w-full">
                    <motion.div 
                      className={`h-full ${entry.confidence > 0.8 ? 'bg-premium-accent' : 'bg-orange-400'}`}
                      initial={{ width: 0 }}
                      animate={{ width: `${entry.confidence * 100}%` }}
                      transition={{ duration: 1, delay: 0.5 }}
                    />
                  </div>
                </motion.div>
              );
            })
          )}
        </motion.div>

        {/* Sidebar Detail / Action View */}
        <AnimatePresence mode="wait">
          {selectedEntry ? (
            <motion.div
              key="detail"
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="glass-thick border-premium-accent/20 rounded-[2.5rem] p-10 sticky top-10 shadow-[0_20px_50px_rgba(0,0,0,0.5)] overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-premium-accent/10 blur-3xl rounded-full translate-x-1/2 -translate-y-1/2" />
              
              <div className="flex items-center justify-between mb-10 relative z-10">
                <div>
                  <h3 className="text-2xl font-bold text-white tracking-tight">Pattern Review</h3>
                  <p className="text-slate-500 text-sm">Verify and commit to knowledge base</p>
                </div>
                <button 
                  onClick={() => setSelectedEntry(null)} 
                  className="p-3 rounded-full hover:bg-white/10 transition-colors text-slate-500 hover:text-white"
                >
                  <XCircle className="w-6 h-6" />
                </button>
              </div>

              <div className="space-y-8 relative z-10">
                <section>
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest block mb-4">Probable Cause Analysis</label>
                  <div className="bg-black/40 p-6 rounded-3xl text-slate-200 border border-white/5 leading-relaxed font-medium">
                    {(() => {
                      try {
                        return JSON.parse(selectedEntry.rca_json).probable_cause;
                      } catch (e) {
                        return 'Data parsing error';
                      }
                    })()}
                  </div>
                </section>

                <section>
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest block mb-4">Recommended Repair Pipeline</label>
                  <div className="bg-premium-accent/[0.03] p-6 rounded-3xl text-premium-accent font-mono text-sm border border-premium-accent/10 leading-relaxed">
                    <span className="text-premium-accent/50 mr-2">$</span>
                    {(() => {
                      try {
                        return JSON.parse(selectedEntry.rca_json).repair_action;
                      } catch (e) {
                        return 'N/A';
                      }
                    })()}
                  </div>
                </section>

                {activeTab === 'pending' && (
                  <div className="pt-8 border-t border-white/10 grid grid-cols-2 gap-5">
                    <button
                      onClick={() => handleApprove(selectedEntry.id)}
                      className="h-14 bg-premium-accent hover:bg-emerald-400 text-white font-bold rounded-2xl flex items-center justify-center gap-3 transition-all shadow-xl shadow-premium-accent/20 active:scale-95"
                    >
                      <CheckCircle2 className="w-5 h-5" />
                      Commit
                    </button>
                    <button
                      onClick={() => handleReject(selectedEntry.id)}
                      className="h-14 bg-red-600/10 border border-red-500/20 text-red-500 hover:bg-red-500/20 font-bold rounded-2xl flex items-center justify-center gap-3 transition-all active:scale-95"
                    >
                      <Trash2 className="w-5 h-5" />
                      Discard
                    </button>
                  </div>
                )}
              </div>
            </motion.div>
          ) : (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="hidden lg:flex flex-col items-center justify-center h-80 glass-thin border-dashed border-white/5 rounded-[2.5rem] text-slate-700"
            >
              <Info className="w-12 h-12 mb-5 opacity-20" />
              <p className="font-medium tracking-wide">Select an intelligence item to verify</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};

export default CatalogueReview;
