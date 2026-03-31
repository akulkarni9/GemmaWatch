import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { 
  Mail, Save, 
  Loader2, CheckCircle2,
  Settings2, Sliders
} from 'lucide-react';
import { motion } from 'framer-motion';

const API_BASE_URL = 'http://localhost:8002';

const SettingsPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/settings/alerts`, { credentials: 'include' });
      const data = await response.json();
      setConfig(data);
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) fetchSettings();
  }, [isAdmin]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      await fetch(`${API_BASE_URL}/settings/alerts`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
        credentials: 'include'
      });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to save settings:', err);
    } finally {
      setSaving(false);
    }
  };

  if (!isAdmin) return <div className="p-10 text-white">Access Denied</div>;
  if (loading) return (
    <div className="min-h-screen bg-[#050510] flex items-center justify-center">
      <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
    </div>
  );

  return (
    <div className="p-6 lg:p-10 max-w-4xl mx-auto min-h-screen">
      <div className="flex items-center gap-4 mb-12">
        <div className="p-3 bg-blue-500/10 rounded-2xl">
          <Settings2 className="w-8 h-8 text-blue-400" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-white">System Settings</h1>
          <p className="text-slate-400">Configure global intelligence and alerting parameters.</p>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-8">
        {/* Email / SMTP Config */}
        <section className="bg-white/[0.03] border border-white/10 rounded-3xl p-8">
          <div className="flex items-center gap-3 mb-8">
            <Mail className="w-5 h-5 text-blue-400" />
            <h2 className="text-xl font-bold text-white">Email Alerting (SMTP)</h2>
          </div>
          
          <div className="grid md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-400">Recipient Email</label>
              <input 
                type="email" 
                value={config.recipient_email || ''} 
                onChange={e => setConfig({...config, recipient_email: e.target.value})}
                placeholder="alerts@company.com"
                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500/50 transition-colors"
                required
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-400">SMTP Host</label>
              <input 
                type="text" 
                value={config.smtp_host || ''} 
                onChange={e => setConfig({...config, smtp_host: e.target.value})}
                placeholder="smtp.gmail.com"
                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500/50"
              />
            </div>

            <div className="grid grid-cols-[1fr_2fr] gap-4">
               <div className="space-y-2">
                <label className="text-sm font-semibold text-slate-400">Port</label>
                <input 
                  type="number" 
                  value={config.smtp_port || 587} 
                  onChange={e => setConfig({...config, smtp_port: parseInt(e.target.value)})}
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500/50"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-semibold text-slate-400">SMTP User</label>
                <input 
                  type="text" 
                  value={config.smtp_user || ''} 
                  onChange={e => setConfig({...config, smtp_user: e.target.value})}
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500/50"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-400">SMTP Password</label>
              <input 
                type="password" 
                autoComplete="new-password"
                onChange={e => setConfig({...config, smtp_password: e.target.value})}
                placeholder="••••••••••••"
                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500/50"
              />
              <p className="text-[10px] text-slate-500 italic">Leave blank to keep current password.</p>
            </div>
          </div>
        </section>

        {/* Intelligence Thresholds */}
        <section className="bg-white/[0.03] border border-white/10 rounded-3xl p-8">
          <div className="flex items-center gap-3 mb-8">
            <Sliders className="w-5 h-5 text-blue-400" />
            <h2 className="text-xl font-bold text-white">Alerting Thresholds</h2>
          </div>

          <div className="space-y-6">
            <div className="flex items-center justify-between p-4 bg-white/5 rounded-2xl">
              <div>
                <h4 className="font-bold text-white mb-1">Status Alerts</h4>
                <p className="text-xs text-slate-500">Enable email notifications on monitoring failures.</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input 
                  type="checkbox" 
                  checked={!!config.enabled} 
                  onChange={e => setConfig({...config, enabled: e.target.checked ? 1 : 0})}
                  className="sr-only peer" 
                />
                <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              <div className="space-y-3">
                <label className="text-sm font-semibold text-slate-400">Min. Alert Severity</label>
                <select 
                  value={config.min_severity || 'medium'}
                  onChange={e => setConfig({...config, min_severity: e.target.value})}
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none"
                >
                  <option value="low">Low+</option>
                  <option value="medium">Medium+</option>
                  <option value="high">High+</option>
                  <option value="critical">Critical Only</option>
                </select>
              </div>

              <div className="space-y-3">
                <label className="text-sm font-semibold text-slate-400">Cooldown (Minutes)</label>
                <input 
                  type="number" 
                  value={config.cooldown_minutes || 30} 
                  onChange={e => setConfig({...config, cooldown_minutes: parseInt(e.target.value)})}
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none"
                />
              </div>
            </div>
          </div>
        </section>

        <div className="flex items-center justify-end gap-4 p-8 bg-white/[0.03] border border-white/10 rounded-3xl">
          {success && (
            <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="text-emerald-400 flex items-center gap-2 font-semibold">
              <CheckCircle2 className="w-5 h-5" />
              Settings Saved
            </motion.div>
          )}
          <button
            type="submit"
            disabled={saving}
            className="h-14 px-10 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 text-white font-bold rounded-2xl flex items-center justify-center gap-3 transition-all shadow-xl shadow-blue-600/20"
          >
            {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
            Save Configuration
          </button>
        </div>
      </form>
    </div>
  );
};

export default SettingsPage;
