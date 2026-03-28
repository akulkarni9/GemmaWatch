import React from 'react';
import { TrendingUp } from 'lucide-react';

interface UptimeDisplayProps {
  uptime: number; // percentage 0-100
  days: number;
  loading?: boolean;
}

const UptimeDisplay: React.FC<UptimeDisplayProps> = ({ uptime, days, loading = false }) => {
  // Color based on uptime percentage
  let color = '#ef4444'; // red
  if (uptime >= 95) color = '#10b981'; // green
  else if (uptime >= 90) color = '#f59e0b'; // amber
  else if (uptime >= 99.5) color = '#06b6d4'; // cyan

  // Calculate circumference for SVG circle
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (uptime / 100) * circumference;

  return (
    <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Uptime Status</h3>
        <span className="text-xs text-gray-500">{days}d</span>
      </div>

      <div className="flex flex-col items-center justify-center">
        {loading ? (
          <div className="animate-spin rounded-full h-32 w-32 border border-blue-500/30 border-t-blue-500" />
        ) : (
          <>
            {/* Circular progress */}
            <div className="relative w-40 h-40 flex items-center justify-center mb-4">
              <svg className="transform -rotate-90" width="160" height="160">
                {/* Background circle */}
                <circle
                  cx="80"
                  cy="80"
                  r="45"
                  fill="none"
                  stroke="rgba(255,255,255,0.1)"
                  strokeWidth="8"
                />
                {/* Progress circle */}
                <circle
                  cx="80"
                  cy="80"
                  r="45"
                  fill="none"
                  stroke={color}
                  strokeWidth="8"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  style={{ transition: 'stroke-dashoffset 0.5s ease' }}
                />
              </svg>
              {/* Center text */}
              <div className="absolute text-center">
                <div className="text-4xl font-bold text-white">{uptime.toFixed(2)}%</div>
                <div className="text-xs text-gray-400 mt-1">uptime</div>
              </div>
            </div>

            {/* Status badge */}
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10">
              <TrendingUp className="w-4 h-4" style={{ color }} />
              <span className="text-sm text-gray-300">
                {uptime >= 99.5 && 'Excellent'}
                {uptime >= 95 && uptime < 99.5 && 'Good'}
                {uptime >= 90 && uptime < 95 && 'Fair'}
                {uptime < 90 && 'Poor'}
              </span>
            </div>

            {/* Info text */}
            <p className="text-xs text-gray-500 mt-4 text-center">
              {uptime >= 99.5 ? '🚀 Highly reliable' : ''}
              {uptime >= 95 && uptime < 99.5 ? '✓ Acceptable performance' : ''}
              {uptime >= 90 && uptime < 95 ? '⚠️ Needs improvement' : ''}
              {uptime < 90 ? '🔴 Critical issues detected' : ''}
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default UptimeDisplay;
