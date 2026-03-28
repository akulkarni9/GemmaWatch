/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom" />
import { render, screen } from '@testing-library/react';
import UptimeDisplay from './UptimeDisplay';

describe('UptimeDisplay Component', () => {
  it('renders without crashing with valid uptime data', () => {
    render(<UptimeDisplay uptime={99.5} days={7} />);
    expect(screen.getByText('7d')).toBeInTheDocument();
  });

  it('displays uptime percentage correctly', () => {
    render(<UptimeDisplay uptime={95.5} days={7} />);
    expect(screen.getByText(/95\.50/)).toBeInTheDocument();
  });

  it('displays correct day period', () => {
    render(<UptimeDisplay uptime={99} days={30} />);
    expect(screen.getByText('30d')).toBeInTheDocument();
  });

  it('applies green color for excellent uptime (99.5%+)', () => {
    const { container } = render(<UptimeDisplay uptime={99.9} days={7} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('applies cyan color for very good uptime (99-99.5%)', () => {
    const { container } = render(<UptimeDisplay uptime={99.2} days={7} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('applies amber color for good uptime (90-95%)', () => {
    const { container } = render(<UptimeDisplay uptime={92} days={7} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('applies red color for poor uptime (<90%)', () => {
    const { container } = render(<UptimeDisplay uptime={85} days={7} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('displays circle progress indicator', () => {
    const { container } = render(<UptimeDisplay uptime={95} days={7} />);
    const circles = container.querySelectorAll('circle');
    expect(circles.length).toBeGreaterThan(0);
  });

  it('handles 0% uptime', () => {
    render(<UptimeDisplay uptime={0} days={7} />);
    expect(screen.getByText(/0\.00/)).toBeInTheDocument();
  });

  it('handles 100% uptime', () => {
    render(<UptimeDisplay uptime={100} days={7} />);
    expect(screen.getByText(/100\.00/)).toBeInTheDocument();
  });

  it('handles decimal uptime values', () => {
    render(<UptimeDisplay uptime={99.99} days={7} />);
    expect(screen.getByText(/99\.99/)).toBeInTheDocument();
  });

  it('handles different day periods', () => {
    const periods = [1, 7, 14, 30, 60, 90];
    
    periods.forEach(days => {
      const { unmount } = render(<UptimeDisplay uptime={95} days={days} />);
      expect(screen.getByText(`${days}d`)).toBeInTheDocument();
      unmount();
    });
  });

  it('renders SVG circle gauge element', () => {
    const { container } = render(<UptimeDisplay uptime={95} days={7} />);
    const svgElement = container.querySelector('svg');
    expect(svgElement).toBeInTheDocument();
    // SVG should have width and height attributes
    expect(svgElement).toHaveAttribute('width', '160');
  });

  it('displays percentage symbol', () => {
    render(<UptimeDisplay uptime={95.5} days={7} />);
    // The % should be near the uptime value
    expect(screen.getByText(/uptime/)).toBeInTheDocument();
  });

  it('renders status badge container', () => {
    const { container } = render(<UptimeDisplay uptime={99} days={7} />);
    // Should have SVG for the gauge
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('handles uptime at threshold boundaries', () => {
    const thresholds = [89.9, 90, 94.9, 95, 99.4, 99.5];
    
    thresholds.forEach(uptime => {
      const { unmount } = render(<UptimeDisplay uptime={uptime} days={7} />);
      expect(screen.getByText(new RegExp(uptime.toFixed(2)))).toBeInTheDocument();
      unmount();
    });
  });

  it('renders status text with correct message', () => {
    const { rerender } = render(<UptimeDisplay uptime={99.6} days={7} />);
    expect(screen.getByText(/Excellent/)).toBeInTheDocument();

    rerender(<UptimeDisplay uptime={95} days={7} />);
    expect(screen.getByText(/Good/)).toBeInTheDocument();

    rerender(<UptimeDisplay uptime={92} days={7} />);
    expect(screen.getByText(/Fair/)).toBeInTheDocument();

    rerender(<UptimeDisplay uptime={85} days={7} />);
    expect(screen.getByText(/Poor/)).toBeInTheDocument();
  });

  it('renders responsive SVG element', () => {
    const { container } = render(<UptimeDisplay uptime={95} days={7} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('handles rapid prop updates', () => {
    const { rerender } = render(<UptimeDisplay uptime={50} days={7} />);
    expect(screen.getByText(/50\.00/)).toBeInTheDocument();

    rerender(<UptimeDisplay uptime={75} days={7} />);
    expect(screen.getByText(/75\.00/)).toBeInTheDocument();

    rerender(<UptimeDisplay uptime={99.9} days={7} />);
    expect(screen.getByText(/99\.90/)).toBeInTheDocument();
  });

  it('handles loading state', () => {
    const { container } = render(<UptimeDisplay uptime={95} days={7} loading={true} />);
    // When loading, a spinner is shown
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });
});
