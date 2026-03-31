import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, CheckCircle2, Clock, ChevronRight, 
  MapPin, MessageSquare, ShieldAlert, Loader2, RefreshCw
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Incident {
  id: string;
  title: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'resolved';
  affected_site_ids: string[];
  affected_site_names?: string[];
  probable_shared_cause?: string;
  created_at: string;
  resolved_at?: string;
}

const API_BASE_URL = 'http://localhost:8002';

const IncidentsView: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchIncidents = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/incidents`);
      const data = await response.json();
      setIncidents(data.incidents || []);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch incidents:', err);
      setError('Failed to load incidents. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  const getSeverityColor = (sev: string) => {
    switch (sev) {
      case 'critical': return 'text-red-400 bg-red-400/10 border-red-400/20';
      case 'high': return 'text-orange-400 bg-orange-400/10 border-orange-400/20';
      case 'medium': return 'text-blue-400 bg-blue-400/10 border-blue-400/20';
      default: return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
    }
  };

  return (
    <div className="p-6 lg:p-10 max-w-7xl mx-auto min-h-screen">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <ShieldAlert className="w-6 h-6 text-blue-400" />
            </div>
            <h1 className="text-3xl font-bold text-white">Cross-Site Incidents</h1>
          </div>
          <p className="text-slate-400">GemmaWatch automatically correlates simultaneous failures across your monitored estate.</p>
        </div>
        <button 
          onClick={fetchIncidents}
          className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-white hover:bg-white/10 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {loading && incidents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
          <p className="text-slate-400">Correlating patterns...</p>
        </div>
      ) : error ? (
        <div className="p-8 bg-red-500/10 border border-red-500/20 rounded-2xl text-center">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Error</h3>
          <p className="text-slate-400">{error}</p>
        </div>
      ) : incidents.length === 0 ? (
        <div className="text-center py-32 bg-white/[0.02] border border-dashed border-white/10 rounded-3xl">
          <CheckCircle2 className="w-16 h-16 text-emerald-400/30 mx-auto mb-6" />
          <h3 className="text-xl font-bold text-white mb-2">All systems operating within parameters</h3>
          <p className="text-slate-500 max-w-md mx-auto">No cross-site correlations detected in the last 24 hours.</p>
        </div>
      ) : (
        <div className="grid gap-6">
          <AnimatePresence mode="popLayout">
            {incidents.map((incident, idx) => (
              <motion.div
                key={incident.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="group relative bg-white/[0.03] border border-white/10 rounded-3xl p-8 hover:bg-white/[0.05] transition-all"
              >
                <div className="flex flex-col lg:flex-row gap-8">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-3 mb-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${getSeverityColor(incident.severity)}`}>
                        {incident.severity}
                      </span>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${incident.status === 'open' ? 'text-blue-400 bg-blue-400/10 border-blue-400/20' : 'text-slate-400 bg-slate-400/10 border-slate-400/20'}`}>
                        {incident.status}
                      </span>
                      <div className="flex items-center gap-2 text-slate-500 text-sm ml-auto">
                        <Clock className="w-4 h-4" />
                        {new Date(incident.created_at).toLocaleString()}
                      </div>
                    </div>

                    <h2 className="text-2xl font-bold text-white mb-4 group-hover:text-blue-400 transition-colors">
                      {incident.title}
                    </h2>

                    {incident.probable_shared_cause && (
                      <div className="mb-6 p-4 bg-blue-500/5 rounded-2xl border border-blue-500/10">
                        <div className="flex items-center gap-2 text-blue-400 text-sm font-semibold mb-2">
                          <MessageSquare className="w-4 h-4" />
                          Gemma Analysis: Shared Cause
                        </div>
                        <p className="text-slate-300 italic">"{incident.probable_shared_cause}"</p>
                      </div>
                    )}

                    <div className="flex flex-wrap gap-2">
                      {incident.affected_site_names?.map((site, i) => (
                        <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-slate-300 text-sm">
                          <MapPin className="w-3.5 h-3.5" />
                          {site}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="lg:w-48 flex items-center justify-end">
                    <button className="flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 rounded-2xl text-white group-hover:bg-blue-600 group-hover:border-blue-500 transition-all font-semibold">
                      Details
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
};

export default IncidentsView;
