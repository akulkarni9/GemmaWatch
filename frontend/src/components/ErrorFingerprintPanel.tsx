import React from 'react';
import { ShieldAlert, Info, ShieldQuestion, Globe, Terminal } from 'lucide-react';

interface Fingerprint {
  id: string;
  fingerprint_hash: string;
  title: string;
  description: string;
  severity: string;
  error_type: string;
}

interface ErrorFingerprintPanelProps {
  fingerprints: Fingerprint[];
}

const ErrorFingerprintPanel: React.FC<ErrorFingerprintPanelProps> = ({ fingerprints }) => {
  if (!fingerprints || fingerprints.length === 0) return null;

  const getSeverityStyles = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'high':
        return 'bg-red-500/10 border-red-500/20 text-red-400';
      case 'medium':
        return 'bg-orange-500/10 border-orange-500/20 text-orange-400';
      default:
        return 'bg-blue-500/10 border-blue-500/20 text-blue-400';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'high':
        return <ShieldAlert className="w-4 h-4" />;
      case 'medium':
        return <Info className="w-4 h-4" />;
      default:
        return <ShieldQuestion className="w-4 h-4" />;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-indigo-500/10 rounded-xl">
          <ShieldAlert className="w-5 h-5 text-indigo-400" />
        </div>
        <div>
          <h4 className="font-bold text-indigo-400 uppercase tracking-widest text-xs">Identified Error Patterns</h4>
          <p className="text-[10px] text-slate-500 font-bold uppercase">Collapsing {fingerprints.length} recurring failures</p>
        </div>
      </div>

      <div className="grid gap-4">
        {fingerprints.map((fp) => (
          <div key={fp.id} className="p-5 bg-white/[0.03] backdrop-blur-sm rounded-3xl border border-white/5 hover:border-white/10 transition-all group">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-tighter border ${getSeverityStyles(fp.severity)}`}>
                  {getSeverityIcon(fp.severity)}
                  {fp.severity}
                </span>
                <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-slate-400 text-[10px] font-bold uppercase tracking-tighter">
                  {fp.error_type === 'network' ? <Globe className="w-3 h-3" /> : <Terminal className="w-3 h-3" />}
                  {fp.error_type}
                </span>
              </div>
              <span className="text-[9px] font-mono text-slate-600 group-hover:text-slate-500 transition-colors">
                HASH: {fp.fingerprint_hash.substring(0, 8)}
              </span>
            </div>
            
            <h5 className="text-white font-bold text-sm mb-2 group-hover:text-indigo-300 transition-colors">
              {fp.title}
            </h5>
            <p className="text-slate-400 text-xs leading-relaxed">
              {fp.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ErrorFingerprintPanel;
