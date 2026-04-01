import React from 'react';
import { AlertTriangle, CheckCircle, Zap, AlertCircle, Eye } from 'lucide-react';
import RepairPipeline from './RepairPipeline';
import ErrorFingerprintPanel from './ErrorFingerprintPanel';

interface MonitoringResult {
  site_id: string;
  check_id: string;
  name: string;
  url: string;
  status: 'SUCCESS' | 'FAILED';
  status_code?: number;
  timestamp: string;
  screenshot?: string;
  console_log_count?: number;
  network_error_count?: number;
  console_logs?: Array<{ level: string; message: string; timestamp?: string }>;
  network_errors?: Array<{ message: string; status?: number; url?: string }>;
  rca?: {
    probable_cause?: string;
    confidence: number;
    repair_action: string;
    category: string;
  };
  fingerprints?: Array<{
    id: string;
    fingerprint_hash: string;
    title: string;
    description: string;
    severity: string;
    error_type: string;
  }>;
}

interface SiteDetailsProps {
  selectedResult: MonitoringResult | null;
  onViewScreenshot: (url: string) => void;
  onViewConsoleLogs: (logs: any[]) => void;
  onViewNetworkErrors: (errors: any[]) => void;
}

const SiteDetails: React.FC<SiteDetailsProps> = ({
  selectedResult,
  onViewScreenshot,
  onViewConsoleLogs,
  onViewNetworkErrors,
}) => {
  if (!selectedResult) {
    return (
      <div className="bg-white/5 backdrop-blur rounded-xl p-8 border border-white/10 h-full flex items-center justify-center">
        <div className="text-center text-gray-400">
          <Zap className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>Select a site to view detailed results</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/5 backdrop-blur rounded-xl p-6 border border-white/10 space-y-8">
      {/* Header */}
      <div className="border-b border-white/10 pb-6">
        <h3 className="text-xl font-bold text-white mb-2 tracking-tight">{selectedResult.name}</h3>
        <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest bg-white/5 inline-block px-2 py-0.5 rounded-lg mb-4">{selectedResult.url}</p>
        <div className="flex items-center gap-4 flex-wrap">
          <div className={`flex items-center gap-2 px-4 py-2 rounded-2xl border ${
            selectedResult.status === 'SUCCESS'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
              : 'bg-red-500/10 border-red-500/20 text-red-400'
          }`}>
            {selectedResult.status === 'SUCCESS' ? (
              <CheckCircle className="w-4 h-4" />
            ) : (
              <AlertTriangle className="w-4 h-4" />
            )}
            <span className="text-xs font-bold uppercase tracking-wider">{selectedResult.status}</span>
          </div>
          {selectedResult.status_code && (
            <div className="px-4 py-2 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-bold font-mono">
              HTTP {selectedResult.status_code}
            </div>
          )}
          <div className="text-xs font-mono text-slate-500 italic bg-white/2 px-3 py-2 rounded-xl">
            {new Date(selectedResult.timestamp).toLocaleString()}
          </div>
        </div>
      </div>

      {/* Error Fingerprints */}
      {selectedResult.fingerprints && selectedResult.fingerprints.length > 0 && (
        <ErrorFingerprintPanel fingerprints={selectedResult.fingerprints} />
      )}

      {/* RCA Analysis */}
      {selectedResult.rca && (
        <div className="space-y-8">
          <div className="flex items-center gap-3">
             <div className="p-2 bg-red-500/10 rounded-xl">
               <AlertCircle className="w-5 h-5 text-red-400" />
             </div>
             <div>
               <h4 className="font-bold text-red-400 uppercase tracking-widest text-xs">Root Cause Analysis</h4>
               <p className="text-[10px] text-slate-500 font-bold uppercase">Confidence: {Math.round(selectedResult.rca.confidence * 100)}%</p>
             </div>
          </div>

          <div className="grid gap-6">
            {selectedResult.rca.probable_cause && (
              <div className="p-6 bg-white/[0.03] rounded-3xl border border-white/5 space-y-3">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Probable Cause Identification</p>
                <p className="text-lg text-slate-100 font-medium leading-relaxed italic">
                  "{selectedResult.rca.probable_cause}"
                </p>
              </div>
            )}

            <RepairPipeline 
              steps={(selectedResult.rca as any).repair_steps || []} 
              fallbackAction={selectedResult.rca.repair_action}
            />

            <div className="flex gap-2">
              <span className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-3 py-1 rounded-xl text-[10px] font-bold uppercase tracking-wider">
                {selectedResult.rca.category || 'System'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Error Details */}
      <div className="grid grid-cols-2 gap-3">
        {/* Console Logs */}
        <button
          onClick={() => onViewConsoleLogs(selectedResult.console_logs || [])}
          disabled={(selectedResult.console_log_count ?? 0) === 0}
          className={`p-3 rounded-lg border transition ${
            (selectedResult.console_log_count ?? 0) > 0
              ? 'bg-amber-500/10 border-amber-500/20 hover:bg-amber-500/20 cursor-pointer'
              : 'bg-gray-500/5 border-gray-500/20 opacity-50 cursor-not-allowed'
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            <AlertCircle className="w-4 h-4 text-amber-400" />
            <span className="text-xs uppercase tracking-wider font-bold text-amber-400">Console Errors</span>
          </div>
          <p className="text-2xl font-bold text-amber-300">{selectedResult.console_log_count ?? 0}</p>
          {(selectedResult.console_log_count ?? 0) > 0 && (
            <p className="text-xs text-amber-400/60 mt-1">Click to view</p>
          )}
        </button>

        {/* Network Errors */}
        <button
          onClick={() => onViewNetworkErrors(selectedResult.network_errors || [])}
          disabled={(selectedResult.network_error_count ?? 0) === 0}
          className={`p-3 rounded-lg border transition ${
            (selectedResult.network_error_count ?? 0) > 0
              ? 'bg-red-500/10 border-red-500/20 hover:bg-red-500/20 cursor-pointer'
              : 'bg-gray-500/5 border-gray-500/20 opacity-50 cursor-not-allowed'
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            <Zap className="w-4 h-4 text-red-400" />
            <span className="text-xs uppercase tracking-wider font-bold text-red-400">Network Errors</span>
          </div>
          <p className="text-2xl font-bold text-red-300">{selectedResult.network_error_count ?? 0}</p>
          {(selectedResult.network_error_count ?? 0) > 0 && (
            <p className="text-xs text-red-400/60 mt-1">Click to view</p>
          )}
        </button>
      </div>

      {/* Screenshot */}
      {selectedResult.screenshot && (
        <button
          onClick={() => onViewScreenshot(selectedResult.screenshot!)}
          className="w-full p-3 rounded-lg border border-blue-500/20 bg-blue-500/10 hover:bg-blue-500/20 transition flex items-center gap-2 text-blue-400 uppercase tracking-wider text-xs font-bold"
        >
          <Eye className="w-4 h-4" />
          View Screenshot
        </button>
      )}
    </div>
  );
};

export default SiteDetails;
