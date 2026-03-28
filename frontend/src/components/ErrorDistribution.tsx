import React from 'react';
import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts';

interface Metric {
  console_errors: number;
  network_failures: number;
  timestamp: string;
}

interface ErrorDistributionProps {
  metrics: Metric[];
  loading?: boolean;
}

const ErrorDistribution: React.FC<ErrorDistributionProps> = ({ metrics, loading = false }) => {
  if (loading) {
    return (
      <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10 h-80 flex items-center justify-center">
        <p className="text-gray-500">Loading error data...</p>
      </div>
    );
  }

  if (!metrics || metrics.length === 0) {
    return (
      <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10 h-80 flex items-center justify-center">
        <p className="text-gray-500">No error data available</p>
      </div>
    );
  }

  // Calculate totals
  const totalConsoleErrors = metrics.reduce((sum, m) => sum + (m.console_errors || 0), 0);
  const totalNetworkFailures = metrics.reduce((sum, m) => sum + (m.network_failures || 0), 0);

  const data = [
    { name: 'Console Errors', value: totalConsoleErrors, fill: '#f59e0b' },
    { name: 'Network Failures', value: totalNetworkFailures, fill: '#ef4444' },
  ];

  // If both are 0, show a "no errors" message
  if (totalConsoleErrors === 0 && totalNetworkFailures === 0) {
    return (
      <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10 h-80 flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-2">✓</div>
          <p className="text-green-400 font-semibold">No Errors Detected</p>
          <p className="text-gray-500 text-sm mt-2">All checks passed without errors</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10">
      <h3 className="text-lg font-semibold mb-4">Error Distribution</h3>
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={true}
            label={({ name, value }) => `${name}: ${value}`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1a2e',
              border: '1px solid rgba(255,255,255,0.2)',
              borderRadius: '8px'
            }}
            labelStyle={{ color: '#fff' }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ErrorDistribution;
