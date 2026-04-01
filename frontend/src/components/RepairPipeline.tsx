import React, { useState } from 'react';
import { 
  CheckCircle2, Search, Terminal, 
  Copy, Check, AlertCircle,
  ShieldCheck, ArrowRight
} from 'lucide-react';
import { motion } from 'framer-motion';

export interface RepairStep {
  id: string;
  type: 'investigate' | 'command' | 'verify';
  summary: string;
  content: string;
}

interface RepairPipelineProps {
  steps: RepairStep[];
  fallbackAction?: string;
}

const RepairPipeline: React.FC<RepairPipelineProps> = ({ steps, fallbackAction }) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getStepIcon = (type: string) => {
    switch (type) {
      case 'command': return <Terminal className="w-4 h-4 text-emerald-400" />;
      case 'verify': return <ShieldCheck className="w-4 h-4 text-blue-400" />;
      case 'investigate': return <Search className="w-4 h-4 text-amber-400" />;
      default: return <AlertCircle className="w-4 h-4 text-slate-400" />;
    }
  };

  const getStepColor = (type: string) => {
    switch (type) {
      case 'command': return 'border-emerald-500/20 bg-emerald-500/5';
      case 'verify': return 'border-blue-500/20 bg-blue-500/5';
      case 'investigate': return 'border-amber-500/20 bg-amber-500/5';
      default: return 'border-slate-500/20 bg-slate-500/5';
    }
  };

  // If no steps, but we have a fallback action (legacy data)
  if ((!steps || steps.length === 0) && fallbackAction) {
    return (
      <div className="space-y-4">
        <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Recommended Repair Pipeline</h4>
        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
           <div className="flex items-center gap-2 mb-3">
             <Terminal className="w-4 h-4 text-emerald-400" />
             <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Automated Fix Recommendation</span>
           </div>
           <div className="relative group">
             <pre className="p-4 bg-[#050510] rounded-xl border border-white/10 text-emerald-300 font-mono text-sm overflow-x-auto whitespace-pre-wrap break-words">
                <span className="text-emerald-500/50 mr-2">$</span>
                {fallbackAction}
             </pre>
             <button 
               onClick={() => copyToClipboard(fallbackAction, 'legacy')}
               className="absolute top-3 right-3 p-2 rounded-lg bg-white/5 text-slate-400 opacity-0 group-hover:opacity-100 transition-all hover:bg-white/10 hover:text-white"
             >
               {copiedId === 'legacy' ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
             </button>
           </div>
        </div>
      </div>
    );
  }

  if (!steps || steps.length === 0) return null;

  return (
    <div className="space-y-4">
      <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">Recommended Repair Pipeline</h4>
      
      <div className="relative">
        {/* Connecting Line */}
        <div className="absolute left-[19px] top-6 bottom-6 w-0.5 bg-gradient-to-b from-white/10 via-white/10 to-transparent" />
        
        <div className="space-y-6">
          {steps.map((step, index) => (
            <motion.div 
              key={step.id || index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="relative flex gap-4 pl-1"
            >
              {/* Step Circle */}
              <div className="relative z-10 w-9 h-9 rounded-full bg-[#0a0a1a] border border-white/10 flex items-center justify-center shadow-xl">
                {getStepIcon(step.type)}
                {index === steps.length - 1 && (
                   <div className="absolute inset-0 rounded-full animate-ping bg-white/5 pointer-events-none" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider border ${getStepColor(step.type)}`}>
                    {step.type}
                  </span>
                  <h5 className="text-sm font-bold text-white truncate tracking-tight">{step.summary}</h5>
                </div>

                <div className={`p-4 rounded-2xl border ${getStepColor(step.type)} transition-all group relative`}>
                  {step.type === 'command' ? (
                    <>
                      <pre className="font-mono text-xs text-emerald-300 break-words whitespace-pre-wrap">
                        <span className="text-emerald-500/50 mr-2">$</span>
                        {step.content}
                      </pre>
                      <button 
                        onClick={() => copyToClipboard(step.content, step.id)}
                        className="absolute top-2 right-2 p-1.5 rounded-lg bg-white/5 text-slate-400 opacity-0 group-hover:opacity-100 transition-all hover:bg-white/10 hover:text-white"
                      >
                        {copiedId === step.id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      </button>
                    </>
                  ) : (
                    <p className="text-sm text-slate-300 leading-relaxed font-medium capitalize-first">
                      {step.content}
                    </p>
                  )}
                </div>

                {index < steps.length - 1 && (
                  <div className="mt-4 flex items-center gap-2 justify-center py-2 text-slate-600/30">
                     <ArrowRight className="w-4 h-4 rotate-90" />
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2 p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-2xl mt-6">
        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        <p className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest">
          Pipeline generated by Gemma 3 12B
        </p>
      </div>
    </div>
  );
};

export default RepairPipeline;
