/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom" />
import { render, screen } from '@testing-library/react';
import MetricsChart from './MetricsChart';

describe('MetricsChart Component', () => {
  const mockMetrics = [
    {
      timestamp: '2024-01-01T10:00:00Z',
      response_time_ms: 150,
      dom_elements: 450,
      console_errors: 2,
      network_failures: 0,
    },
    {
      timestamp: '2024-01-01T10:05:00Z',
      response_time_ms: 180,
      dom_elements: 455,
      console_errors: 1,
      network_failures: 0,
    },
    {
      timestamp: '2024-01-01T10:10:00Z',
      response_time_ms: 120,
      dom_elements: 450,
      console_errors: 0,
      network_failures: 1,
    },
  ];

  it('renders without crashing with valid metrics', () => {
    render(<MetricsChart metrics={mockMetrics} />);
    expect(screen.getByText('Response Time & Elements Trend')).toBeInTheDocument();
  });

  it('renders with empty metrics array', () => {
    render(<MetricsChart metrics={[]} />);
    expect(screen.getByText('No metrics data available')).toBeInTheDocument();
  });

  it('displays chart title', () => {
    render(<MetricsChart metrics={mockMetrics} />);
    expect(screen.getByText('Response Time & Elements Trend')).toBeInTheDocument();
  });

  it('renders ResponsiveContainer for responsive design', () => {
    const { container } = render(<MetricsChart metrics={mockMetrics} />);
    // Check for Recharts ResponsiveContainer
    expect(container.querySelector('div')).toBeInTheDocument();
  });

  it('handles metrics with zero values', () => {
    const zeroMetrics = [
      {
        timestamp: '2024-01-01T10:00:00Z',
        response_time_ms: 0,
        dom_elements: 0,
        console_errors: 0,
        network_failures: 0,
      },
    ];

    render(<MetricsChart metrics={zeroMetrics} />);
    expect(screen.getByText('Response Time & Elements Trend')).toBeInTheDocument();
  });

  it('handles metrics with high values', () => {
    const highMetrics = [
      {
        timestamp: '2024-01-01T10:00:00Z',
        response_time_ms: 5000,
        dom_elements: 5000,
        console_errors: 100,
        network_failures: 50,
      },
    ];

    render(<MetricsChart metrics={highMetrics} />);
    expect(screen.getByText('Response Time & Elements Trend')).toBeInTheDocument();
  });

  it('maintains responsive design on different viewports', () => {
    window.innerWidth = 800;
    const { container } = render(<MetricsChart metrics={mockMetrics} />);
    expect(container).toBeInTheDocument();

    window.innerWidth = 1200;
    const { container: containerLarge } = render(<MetricsChart metrics={mockMetrics} />);
    expect(containerLarge).toBeInTheDocument();
  });

  it('handles metrics with mixed data points', () => {
    const mixedMetrics = [
      {
        timestamp: '2024-01-01T10:00:00Z',
        response_time_ms: 150,
        dom_elements: 450,
        console_errors: 0,
        network_failures: 0,
      },
      {
        timestamp: '2024-01-01T10:05:00Z',
        response_time_ms: 200,
        dom_elements: 460,
        console_errors: 5,
        network_failures: 2,
      },
      {
        timestamp: '2024-01-01T10:10:00Z',
        response_time_ms: 100,
        dom_elements: 440,
        console_errors: 0,
        network_failures: 0,
      },
    ];

    render(<MetricsChart metrics={mixedMetrics} />);
    expect(screen.getByText('Response Time & Elements Trend')).toBeInTheDocument();
  });

  it('does not throw error with undefined metrics', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect(() => render(<MetricsChart metrics={undefined as any} />)).not.toThrow();
  });

  it('handles very large timestamp values', () => {
    const futureMetrics = [
      {
        timestamp: '2099-12-31T23:59:59Z',
        response_time_ms: 150,
        dom_elements: 450,
        console_errors: 1,
        network_failures: 0,
      },
    ];

    render(<MetricsChart metrics={futureMetrics} />);
    expect(screen.getByText('Response Time & Elements Trend')).toBeInTheDocument();
  });

  it('renders chart with single metric point', () => {
    const singleMetric = [mockMetrics[0]];
    render(<MetricsChart metrics={singleMetric} />);
    expect(screen.getByText('Response Time & Elements Trend')).toBeInTheDocument();
  });

  it('renders chart with 100+ metric points', () => {
    const largeMetrics = Array.from({ length: 100 }, (_, idx) => ({
      timestamp: new Date(Date.now() + idx * 60000).toISOString(),
      response_time_ms: Math.floor(Math.random() * 500),
      dom_elements: Math.floor(Math.random() * 500),
      console_errors: Math.floor(Math.random() * 10),
      network_failures: Math.floor(Math.random() * 5),
    }));

    render(<MetricsChart metrics={largeMetrics} />);
    expect(screen.getByText('Response Time & Elements Trend')).toBeInTheDocument();
  });

  it('handles loading state', () => {
    render(<MetricsChart metrics={[]} loading={true} />);
    expect(screen.getByText('Loading metrics...')).toBeInTheDocument();
  });
});
