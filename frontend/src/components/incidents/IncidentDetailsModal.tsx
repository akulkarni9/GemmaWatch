import React, { useState, useEffect } from 'react';
import { 
  X, Clock, MapPin, MessageSquare, 
  Send, CheckCircle2, ShieldAlert, Loader2,
  AlertTriangle
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuth } from '../../contexts/AuthContext';

interface IncidentNote {
  id: string;
  user_id: string;
  user_name?: string;
  note: string;
  created_at: string;
}

interface IncidentDetail {
  id: string;
  title: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'resolved';
  affected_site_ids: string[];
  affected_site_names?: string[];
  probable_shared_cause?: string;
  created_at: string;
  resolved_at?: string;
  notes?: IncidentNote[];
}

interface IncidentDetailsModalProps {
  incidentId: string;
  onClose: () => void;
  onStatusChange?: () => void;
}

const API_BASE_URL = 'http://localhost:8002';

const IncidentDetailsModal: React.FC<IncidentDetailsModalProps> = ({ 
  incidentId, 
  onClose,
  onStatusChange 
}) => {
  const { user, isAdmin } = useAuth();
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [newNote, setNewNote] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchDetails = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE_URL}/incidents/${incidentId}`, {
        credentials: 'include'
      });
      if (res.ok) {
        const data = await res.json();
        setIncident(data);
      }
    } catch (err) {
      console.error('Failed to fetch incident details:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [incidentId]);

  const addNote = async () => {
    if (!newNote.trim() || submitting) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/incidents/${incidentId}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: newNote }),
        credentials: 'include'
      });
      if (res.ok) {
        setNewNote('');
        fetchDetails();
      }
    } catch (err) {
      console.error('Failed to add note:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const resolveIncident = async () => {
    if (!isAdmin || submitting) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/incidents/${incidentId}/resolve`, {
        method: 'POST',
        credentials: 'include'
      });
      if (res.ok) {
        fetchDetails();
        onStatusChange?.();
      }
    } catch (err) {
      console.error('Failed to resolve incident:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const getSeverityColor = (sev: string) => {
    switch (sev) {
      case 'critical': return 'text-red-400 bg-red-400/10 border-red-400/20';
      case 'high': return 'text-orange-400 bg-orange-400/10 border-orange-400/20';
      case 'medium': return 'text-blue-400 bg-blue-400/10 border-blue-400/20';
      default: return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-8">
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-[#050510]/80 backdrop-blur-md"
        onClick={onClose}
      />
      
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="relative w-full max-w-4xl max-h-[90vh] bg-[#0a0a1a] border border-white/10 rounded-[2rem] shadow-2xl overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="p-6 md:p-8 flex items-center justify-between border-b border-white/5 bg-white/[0.02]">
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-2xl ${incident ? getSeverityColor(incident.severity) : 'bg-white/5'}`}>
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight">
                {incident ? incident.title : 'Incident Analysis'}
              </h2>
              <div className="flex items-center gap-3 mt-1">
                 <span className={`px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase tracking-wider border ${incident ? getSeverityColor(incident.severity) : 'bg-white/5'}`}>
                   {incident?.severity || 'Loading'}
                 </span>
                 <span className={`px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase tracking-wider border ${incident?.status === 'open' ? 'text-blue-400 bg-blue-400/10 border-blue-400/20' : 'text-slate-400 bg-slate-400/10 border-slate-400/20'}`}>
                   {incident?.status || '---'}
                 </span>
              </div>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 rounded-xl bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 custom-scrollbar bg-gradient-to-b from-[#0a0a1a] to-[#050510]">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 min-h-[300px]">
              <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
              <p className="text-slate-400 font-medium">Synthesizing incident context...</p>
            </div>
          ) : incident && (
            <>
              {/* Gemma Analysis Summary */}
              {incident.probable_shared_cause && (
                <section className="bg-blue-600/10 border border-blue-500/20 rounded-3xl p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-1.5 bg-blue-500 rounded-lg">
                      <MessageSquare className="w-4 h-4 text-white" />
                    </div>
                    <h3 className="font-bold text-blue-400 uppercase tracking-widest text-xs">Gemma-Correlated Cause</h3>
                  </div>
                  <p className="text-lg text-slate-200 italic leading-relaxed font-medium">
                    "{incident.probable_shared_cause}"
                  </p>
                </section>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Side: Impacted Sites */}
                <div className="lg:col-span-1 space-y-6">
                   <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Impacted Perimeter</h4>
                   <div className="space-y-2">
                     {incident.affected_site_names?.map((site, i) => (
                       <div key={i} className="flex items-center gap-3 p-4 bg-white/5 border border-white/10 rounded-2xl group hover:border-blue-500/30 transition-all">
                         <div className="p-2 bg-slate-500/10 rounded-xl text-slate-400 group-hover:text-blue-400 transition-colors">
                           <MapPin className="w-4 h-4" />
                         </div>
                         <span className="text-sm font-semibold text-slate-200">{site}</span>
                       </div>
                     ))}
                   </div>
                   
                   <div className="pt-6 border-t border-white/5">
                      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Timeline</h4>
                      <div className="flex items-center gap-3 text-slate-400">
                        <Clock className="w-5 h-5 text-indigo-400" />
                        <div>
                          <p className="text-xs font-bold text-slate-300">Detected</p>
                          <p className="text-sm">{new Date(incident.created_at).toLocaleString()}</p>
                        </div>
                      </div>
                      {incident.resolved_at && (
                        <div className="flex items-center gap-3 text-slate-400 mt-4">
                          <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                          <div>
                            <p className="text-xs font-bold text-slate-300">Resolved</p>
                            <p className="text-sm">{new Date(incident.resolved_at).toLocaleString()}</p>
                          </div>
                        </div>
                      )}
                   </div>
                </div>

                {/* Right Side: Analyst Notes */}
                <div className="lg:col-span-2 space-y-6">
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Analyst Log</h4>
                  
                  <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                    {(!incident.notes || incident.notes.length === 0) ? (
                      <div className="py-10 text-center border border-dashed border-white/10 rounded-3xl">
                        <MessageSquare className="w-8 h-8 text-slate-600 mx-auto mb-2 opacity-50" />
                        <p className="text-slate-500 text-sm">No analyst notes yet.</p>
                      </div>
                    ) : (
                      incident.notes.map((note) => (
                        <div key={note.id} className="p-4 bg-white/5 border border-white/10 rounded-3xl">
                          <div className="flex items-center justify-between mb-2">
                             <div className="flex items-center gap-2">
                               <div className="w-6 h-6 rounded-lg bg-blue-500/20 flex items-center justify-center text-[10px] text-blue-400 font-bold border border-blue-500/30">
                                 {note.user_name?.[0].toUpperCase() || 'U'}
                               </div>
                               <span className="text-xs font-bold text-slate-300">{note.user_name || 'Unknown Analyst'}</span>
                             </div>
                             <span className="text-[10px] text-slate-600 font-mono italic">{new Date(note.created_at).toLocaleTimeString()}</span>
                          </div>
                          <p className="text-sm text-slate-300 leading-relaxed font-outfit">{note.note}</p>
                        </div>
                      ))
                    )}
                  </div>

                  {/* Add Note Input */}
                  {user && (
                    <div className="pt-4 border-t border-white/5 space-y-4">
                      <div className="relative">
                        <textarea 
                          value={newNote}
                          onChange={(e) => setNewNote(e.target.value)}
                          placeholder="Add incident observations..."
                          rows={3}
                          className="w-full bg-white/5 border border-white/10 rounded-2xl p-4 text-sm focus:outline-none focus:border-blue-500 transition-all placeholder:text-slate-600 resize-none"
                        />
                        <button 
                          onClick={addNote}
                          disabled={!newNote.trim() || submitting}
                          className="absolute bottom-4 right-4 flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-500 disabled:opacity-50 disabled:bg-slate-700 transition-all font-bold text-xs"
                        >
                          Post Note
                          <Send className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  )}

                  {!user && (
                    <div className="p-4 bg-white/2 rounded-2xl border border-white/5 text-center">
                      <p className="text-xs text-slate-500">Sign in to add analyst notes.</p>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer / Resolve Action */}
        <div className="p-6 md:p-8 bg-white/[0.01] border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-6">
           <div className="flex items-center gap-2 text-slate-500">
             <AlertTriangle className="w-4 h-4" />
             <span className="text-xs font-medium tracking-tight">Incident affects {incident?.affected_site_ids.length || 0} monitored locations</span>
           </div>

           <div className="flex items-center gap-4 w-full md:w-auto">
              {isAdmin && incident?.status === 'open' && (
                <button 
                  onClick={resolveIncident}
                  disabled={submitting}
                  className="w-full md:w-auto flex items-center justify-center gap-2 px-8 py-4 bg-emerald-600 shadow-xl shadow-emerald-900/20 text-white rounded-2xl font-bold hover:bg-emerald-500 transition-all active:scale-95 disabled:opacity-50"
                >
                  {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                  <CheckCircle2 className="w-5 h-5" />
                  Mark as Resolved
                </button>
              )}
              
              {incident?.status === 'resolved' && (
                <div className="flex items-center gap-2 text-emerald-400 font-bold px-6 py-3 bg-emerald-500/10 rounded-2xl border border-emerald-500/20">
                  <CheckCircle2 className="w-5 h-5" />
                  Resolved
                </div>
              )}
           </div>
        </div>
      </motion.div>
    </div>
  );
};

export default IncidentDetailsModal;
