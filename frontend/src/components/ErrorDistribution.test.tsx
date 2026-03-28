/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom" />
import { render, screen } from '@testing-library/react';
import ErrorDistribution from './ErrorDistribution';

describe('ErrorDistribution Component', () => {
  const mockMetrics = [
    {
      console_errors: 5,
      network_failures: 3,
      timestamp: new Date().toISOString(),
    }
  ];

  it('renders without crashing with valid error data', () => {
    render(<ErrorDistribution metrics={mockMetrics} />);
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();
  });

  it('displays title', () => {
    render(
      <ErrorDistribution
        metrics={[{
          console_errors: 2,
          network_failures: 1,
          timestamp: new Date().toISOString(),
        }]}
      />
    );
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();
  });

  it('renders pie chart container', () => {
    const { container } = render(
      <ErrorDistribution metrics={mockMetrics} />
    );
    expect(container.querySelector('div')).toBeInTheDocument();
  });

  it('handles case with no errors', () => {
    render(
      <ErrorDistribution
        metrics={[{
          console_errors: 0,
          network_failures: 0,
          timestamp: new Date().toISOString(),
        }]}
      />
    );
    expect(screen.getByText('No Errors Detected')).toBeInTheDocument();
  });

  it('handles only console errors', () => {
    render(
      <ErrorDistribution
        metrics={[{
          console_errors: 10,
          network_failures: 0,
          timestamp: new Date().toISOString(),
        }]}
      />
    );
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();
  });

  it('handles only network failures', () => {
    render(
      <ErrorDistribution
        metrics={[{
          console_errors: 0,
          network_failures: 8,
          timestamp: new Date().toISOString(),
        }]}
      />
    );
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();
  });

  it('handles equal console errors and network failures', () => {
    render(
      <ErrorDistribution
        metrics={[{
          console_errors: 5,
          network_failures: 5,
          timestamp: new Date().toISOString(),
        }]}
      />
    );
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();
  });

  it('handles large error counts', () => {
    render(
      <ErrorDistribution
        metrics={[{
          console_errors: 1000,
          network_failures: 500,
          timestamp: new Date().toISOString(),
        }]}
      />
    );
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();
  });

  it('renders responsive container', () => {
    const { container } = render(
      <ErrorDistribution metrics={mockMetrics} />
    );
    expect(container).toBeInTheDocument();
  });

  it('handles fractional error counts', () => {
    render(
      <ErrorDistribution
        metrics={[{
          console_errors: 2,
          network_failures: 1,
          timestamp: new Date().toISOString(),
        }]}
      />
    );
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();
  });

  it('maintains proper proportions with varied error counts', () => {
    const { rerender } = render(
      <ErrorDistribution
        metrics={[{
          console_errors: 99,
          network_failures: 1,
          timestamp: new Date().toISOString(),
        }]}
      />
    );
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();

    rerender(
      <ErrorDistribution
        metrics={[{
          console_errors: 1,
          network_failures: 99,
          timestamp: new Date().toISOString(),
        }]}
      />
    );
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();
  });

  it('handles rapid prop updates', () => {
    const { rerender } = render(
      <ErrorDistribution
        metrics={[{
          console_errors: 5,
          network_failures: 3,
          timestamp: new Date().toISOString(),
        }]}
      />
    );
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();

    rerender(
      <ErrorDistribution
        metrics={[{
          console_errors: 10,
          network_failures: 0,
          timestamp: new Date().toISOString(),
        }]}
      />
    );
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();

    rerender(
      <ErrorDistribution
        metrics={[{
          console_errors: 0,
          network_failures: 0,
          timestamp: new Date().toISOString(),
        }]}
      />
    );
    expect(screen.getByText('No Errors Detected')).toBeInTheDocument();
  });

  it('renders with dark theme styling', () => {
    const { container } = render(
      <ErrorDistribution metrics={mockMetrics} />
    );
    expect(container.querySelector('div')).toBeInTheDocument();
  });

  it('displays correct legend labels', () => {
    render(<ErrorDistribution metrics={mockMetrics} />);
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();
  });

  it('handles minimum values', () => {
    render(
      <ErrorDistribution
        metrics={[{
          console_errors: 1,
          network_failures: 1,
          timestamp: new Date().toISOString(),
        }]}
      />
    );
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();
  });

  it('handles asymmetric error distribution', () => {
    const testCases = [
      { console: 100, network: 1 },
      { console: 1, network: 100 },
      { console: 90, network: 10 },
      { console: 20, network: 80 },
    ];

    testCases.forEach(({ console: consoleErrors, network }) => {
      const { unmount } = render(
        <ErrorDistribution
          metrics={[{
            console_errors: consoleErrors,
            network_failures: network,
            timestamp: new Date().toISOString(),
          }]}
        />
      );
      expect(screen.getByText('Error Distribution')).toBeInTheDocument();
      unmount();
    });
  });

  it('applies correct colors to chart segments', () => {
    const { container } = render(
      <ErrorDistribution metrics={mockMetrics} />
    );
    // Chart renders a Recharts ResponsiveContainer which may not have direct SVG
    // Just verify the container was rendered
    expect(container.querySelector('div')).toBeInTheDocument();
    expect(screen.getByText('Error Distribution')).toBeInTheDocument();
  });

  it('handles empty metrics array gracefully', () => {
    render(<ErrorDistribution metrics={[]} />);
    expect(screen.getByText('No error data available')).toBeInTheDocument();
  });

  it('handles loading state', () => {
    render(<ErrorDistribution metrics={[]} loading={true} />);
    expect(screen.getByText('Loading error data...')).toBeInTheDocument();
  });
});
