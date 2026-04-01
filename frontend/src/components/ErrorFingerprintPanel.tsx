import React from 'react';
import { ShieldAlert, Globe, Terminal, Cpu } from 'lucide-react';

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

const severityBorder: Record<string, string> = {
  high:   'border-l-red-500',
  medium: 'border-l-orange-400',
  low:    'border-l-blue-400',
};

const severityBadge: Record<string, string> = {
  high:   'bg-red-500/10 border-red-500/20 text-red-400',
  medium: 'bg-orange-500/10 border-orange-500/20 text-orange-400',
  low:    'bg-blue-500/10 border-blue-500/20 text-blue-400',
};

const isAnalyzing = (fp: Fingerprint) =>
  !fp.title || fp.title === 'Unnamed Pattern' || fp.title === '';

const FingerprintCard: React.FC<{ fp: Fingerprint }> = ({ fp }) => {
  const sev = (fp.severity || 'low').toLowerCase();
  const pending = isAnalyzing(fp);

  return (
    <div
      className={`relative p-4 bg-white/[0.03] rounded-2xl border border-white/5 border-l-2 ${severityBorder[sev] || severityBorder.low} hover:border-white/10 hover:bg-white/[0.05] transition-all group overflow-hidden`}
    >
      {pending && (
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.02] to-transparent animate-pulse rounded-2xl pointer-events-none" />
      )}

      {/* Top row: severity badge + hash */}
      <div className="flex items-center justify-between mb-3 gap-2">
        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider border ${severityBadge[sev] || severityBadge.low}`}>
          {sev}
        </span>
        <span className="font-mono text-[8px] text-slate-600 group-hover:text-slate-500 transition-colors shrink-0">
          #{fp.fingerprint_hash.substring(0, 8)}
        </span>
      </div>

      {/* Title or analyzing skeleton */}
      {pending ? (
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-indigo-400">
            <Cpu className="w-3 h-3 animate-spin" style={{ animationDuration: '3s' }} />
            <span className="text-[10px] font-bold uppercase tracking-widest animate-pulse">Gemma Analyzing…</span>
          </div>
          <div className="h-2 w-3/4 bg-white/5 rounded-full animate-pulse" />
          <div className="h-2 w-1/2 bg-white/5 rounded-full animate-pulse" />
        </div>
      ) : (
        <div>
          <h5 className="text-white font-semibold text-sm mb-1 leading-snug group-hover:text-indigo-300 transition-colors">
            {fp.title}
          </h5>
          {fp.description && (
            <p className="text-slate-500 text-[11px] leading-relaxed line-clamp-2">
              {fp.description}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

const PatternGroup: React.FC<{
  label: string;
  icon: React.ReactNode;
  items: Fingerprint[];
}> = ({ label, icon, items }) => {
  if (items.length === 0) return null;
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-3">
        <span className="text-slate-600">{icon}</span>
        <span className="text-[9px] font-bold uppercase tracking-widest text-slate-600">{label}</span>
        <span className="ml-auto text-[9px] font-bold text-slate-700 bg-white/5 px-1.5 py-0.5 rounded-md">{items.length}</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {items.map(fp => <FingerprintCard key={fp.id} fp={fp} />)}
      </div>
    </div>
  );
};

const ErrorFingerprintPanel: React.FC<ErrorFingerprintPanelProps> = ({ fingerprints }) => {
  if (!fingerprints || fingerprints.length === 0) return null;

  const consolePatterns = fingerprints.filter(fp => fp.error_type === 'console');
  const networkPatterns = fingerprints.filter(fp => fp.error_type === 'network');

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-indigo-500/10 rounded-xl">
          <ShieldAlert className="w-5 h-5 text-indigo-400" />
        </div>
        <div className="flex-1">
          <h4 className="font-bold text-indigo-400 uppercase tracking-widest text-xs">Identified Error Patterns</h4>
          <p className="text-[10px] text-slate-500 font-bold uppercase">
            Collapsing {fingerprints.length} recurring failure{fingerprints.length !== 1 ? 's' : ''}
          </p>
        </div>
        <span className="px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-bold">
          {fingerprints.length}
        </span>
      </div>

      {/* Groups */}
      <div className="space-y-5">
        <PatternGroup
          label="Console Patterns"
          icon={<Terminal className="w-3 h-3" />}
          items={consolePatterns}
        />
        <PatternGroup
          label="Network Patterns"
          icon={<Globe className="w-3 h-3" />}
          items={networkPatterns}
        />
      </div>
    </div>
  );
};

export default ErrorFingerprintPanel;
