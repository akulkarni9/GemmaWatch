import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

interface Metric {
  response_time_ms: number;
  dom_elements: number;
  console_errors: number;
  network_failures: number;
  timestamp: string;
}

interface MetricsChartProps {
  metrics: Metric[];
  loading?: boolean;
}

const MetricsChart: React.FC<MetricsChartProps> = ({ metrics, loading = false }) => {
  if (loading) {
    return (
      <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10 h-96 flex items-center justify-center">
        <p className="text-gray-500">Loading metrics...</p>
      </div>
    );
  }

  if (!metrics || metrics.length === 0) {
    return (
      <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10 h-96 flex items-center justify-center">
        <p className="text-gray-500">No metrics data available</p>
      </div>
    );
  }

  // Format data for chart - reverse to show chronological order (oldest first)
  const chartData = [...metrics].reverse().map((m) => ({
    timestamp: new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    response_time: m.response_time_ms || 0,
    dom_elements: m.dom_elements || 0,
    errors: (m.console_errors || 0) + (m.network_failures || 0),
  }));

  return (
    <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10">
      <h3 className="text-lg font-semibold mb-4">Response Time & Elements Trend</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis 
            dataKey="timestamp" 
            stroke="rgba(255,255,255,0.5)"
            style={{ fontSize: '12px' }}
          />
          <YAxis 
            stroke="rgba(255,255,255,0.5)"
            style={{ fontSize: '12px' }}
          />
          <Tooltip 
            contentStyle={{
              backgroundColor: '#1a1a2e',
              border: '1px solid rgba(255,255,255,0.2)',
              borderRadius: '8px'
            }}
            labelStyle={{ color: '#fff' }}
          />
          <Legend />
          <Line 
            type="monotone" 
            dataKey="response_time" 
            stroke="#3b82f6" 
            dot={false}
            name="Response Time (ms)"
            strokeWidth={2}
          />
          <Line 
            type="monotone" 
            dataKey="dom_elements" 
            stroke="#10b981" 
            dot={false}
            name="DOM Elements"
            strokeWidth={2}
          />
          <Line 
            type="monotone" 
            dataKey="errors" 
            stroke="#ef4444" 
            dot={false}
            name="Total Errors"
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default MetricsChart;
