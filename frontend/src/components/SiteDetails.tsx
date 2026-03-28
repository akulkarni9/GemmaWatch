import React from 'react';
import { AlertTriangle, CheckCircle, Zap, AlertCircle, Eye } from 'lucide-react';

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
    <div className="bg-white/5 backdrop-blur rounded-xl p-6 border border-white/10 space-y-6">
      {/* Header */}
      <div className="border-b border-white/10 pb-4">
        <h3 className="text-lg font-bold text-white mb-2">{selectedResult.name}</h3>
        <p className="text-xs text-gray-400 mb-3">{selectedResult.url}</p>
        <div className="flex items-center gap-3 flex-wrap">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
            selectedResult.status === 'SUCCESS'
              ? 'bg-green-500/20 text-green-400'
              : 'bg-red-500/20 text-red-400'
          }`}>
            {selectedResult.status === 'SUCCESS' ? (
              <CheckCircle className="w-4 h-4" />
            ) : (
              <AlertTriangle className="w-4 h-4" />
            )}
            <span className="text-xs font-medium">{selectedResult.status}</span>
          </div>
          {selectedResult.status_code && (
            <div className="px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-400 text-xs font-medium">
              HTTP {selectedResult.status_code}
            </div>
          )}
          <div className="text-xs text-gray-500">
            {new Date(selectedResult.timestamp).toLocaleString()}
          </div>
        </div>
      </div>

      {/* RCA Analysis */}
      {selectedResult.rca && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <h4 className="font-bold text-red-400 uppercase tracking-wider text-sm">Root Cause Analysis</h4>
            <span className="ml-auto text-xs text-gray-500">
              {Math.round(selectedResult.rca.confidence * 100)}% confidence
            </span>
          </div>

          {selectedResult.rca.probable_cause && (
            <div className="p-3 bg-red-500/10 rounded-lg border border-red-500/20">
              <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">Probable Cause:</p>
              <p className="text-sm text-red-300">{selectedResult.rca.probable_cause}</p>
            </div>
          )}

          <div className="p-3 bg-amber-500/10 rounded-lg border border-amber-500/20">
            <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">Suggested Fix:</p>
            <p className="text-sm text-amber-300 font-medium">{selectedResult.rca.repair_action}</p>
          </div>

          <div className="flex gap-2">
            <span className="bg-blue-500/20 text-blue-400 px-3 py-1 rounded text-xs font-medium">
              {selectedResult.rca.category}
            </span>
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
