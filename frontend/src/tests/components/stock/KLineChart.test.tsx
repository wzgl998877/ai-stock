import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import KLineChart from '../../../components/stock/KLineChart';

// ---------- echarts mock ----------
// The component uses `import * as echarts from 'echarts'` then calls echarts.init().
// We mock the module to avoid real chart rendering in the test environment.
const mockSetOption = vi.fn();
const mockResize = vi.fn();
const mockDispose = vi.fn();

const mockChartInstance = {
  setOption: mockSetOption,
  resize: mockResize,
  dispose: mockDispose,
};

vi.mock('echarts', () => ({
  init: vi.fn(() => mockChartInstance),
}));

// ---------- test data fixtures ----------
const klineData = [
  {
    trade_date: '2026-01-02',
    open: 10.5,
    close: 11.2,
    high: 11.5,
    low: 10.3,
    volume: 5000000,
  },
  {
    trade_date: '2026-01-03',
    open: 11.2,
    close: 10.8,
    high: 11.6,
    low: 10.6,
    volume: 6200000,
  },
  {
    trade_date: '2026-01-06',
    open: 10.9,
    close: 11.5,
    high: 11.8,
    low: 10.7,
    volume: 4800000,
  },
];

const indicatorsData = [
  { ma5: 10.8, ma10: 10.6, ma20: 10.2, macd_dif: 0.12, macd_dea: 0.08, macd_bar: 0.04, kdj_k: 65, kdj_d: 58, kdj_j: 79 },
  { ma5: 10.9, ma10: 10.7, ma20: 10.3, macd_dif: 0.15, macd_dea: 0.10, macd_bar: 0.05, kdj_k: 70, kdj_d: 62, kdj_j: 86 },
  { ma5: 11.0, ma10: 10.8, ma20: 10.4, macd_dif: 0.18, macd_dea: 0.12, macd_bar: 0.06, kdj_k: 72, kdj_d: 65, kdj_j: 86 },
];

const minuteData = [
  { time: '09:30', price: 11.0, volume: 100000, avg_price: 11.0 },
  { time: '09:31', price: 11.1, volume: 120000, avg_price: 11.05 },
  { time: '09:32', price: 11.2, volume: 80000, avg_price: 11.1 },
];

// ---------- tests ----------
describe('KLineChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeleton when loading=true', () => {
    const { container } = render(<KLineChart data={[]} loading={true} />);

    // Ant Design Skeleton.Image renders an element with class ant-skeleton
    const skeleton = container.querySelector('.ant-skeleton');
    expect(skeleton).toBeInTheDocument();
  });

  it('renders the chart container when data is provided', () => {
    const { container } = render(
      <KLineChart data={klineData} indicators={indicatorsData} />,
    );

    // The chart is rendered as a div with inline style containing the height
    const chartDiv = container.querySelector('div[style]');
    expect(chartDiv).toBeInTheDocument();
    expect(chartDiv).toHaveStyle({ width: '100%', height: '500px' });
  });

  it('calls echarts.setOption with daily options when data is provided', () => {
    render(<KLineChart data={klineData} indicators={indicatorsData} />);

    expect(mockSetOption).toHaveBeenCalled();
    const optionArg = mockSetOption.mock.calls[0][0];
    // Verify the option contains candlestick series data
    const candlestickSeries = optionArg.series?.find(
      (s: any) => s.type === 'candlestick',
    );
    expect(candlestickSeries).toBeDefined();
    expect(candlestickSeries.data).toHaveLength(3);
  });

  it('handles empty data gracefully', () => {
    const { container } = render(<KLineChart data={[]} />);

    // Even with empty data, the chart div should still be rendered
    const chartDiv = container.querySelector('div[style]');
    expect(chartDiv).toBeInTheDocument();

    // setOption should be called with an empty object (since data is empty)
    expect(mockSetOption).toHaveBeenCalledWith({}, true);
  });

  it('shows minute chart when period is "minute" and minuteData is provided', () => {
    render(
      <KLineChart data={klineData} period="minute" minuteData={minuteData} />,
    );

    expect(mockSetOption).toHaveBeenCalled();
    const optionArg = mockSetOption.mock.calls[0][0];

    // Minute chart should have a 'line' type series for price, not candlestick
    const lineSeries = optionArg.series?.find(
      (s: any) => s.name === '价格' && s.type === 'line',
    );
    expect(lineSeries).toBeDefined();
    expect(lineSeries.data).toEqual([11.0, 11.1, 11.2]);

    // Should also have average price line
    const avgSeries = optionArg.series?.find(
      (s: any) => s.name === '均价',
    );
    expect(avgSeries).toBeDefined();
    expect(avgSeries.data).toEqual([11.0, 11.05, 11.1]);

    // Should have volume bar series
    const volumeSeries = optionArg.series?.find(
      (s: any) => s.name === '成交量' && s.type === 'bar',
    );
    expect(volumeSeries).toBeDefined();
    expect(volumeSeries.data).toEqual([100000, 120000, 80000]);

    // Should NOT have candlestick series
    const candlestickSeries = optionArg.series?.find(
      (s: any) => s.type === 'candlestick',
    );
    expect(candlestickSeries).toBeUndefined();
  });

  it('falls back to daily chart when period is "minute" but minuteData is empty', () => {
    render(
      <KLineChart data={klineData} period="minute" minuteData={[]} />,
    );

    expect(mockSetOption).toHaveBeenCalled();
    const optionArg = mockSetOption.mock.calls[0][0];

    // Since minuteData is empty, it should fall back to daily chart (candlestick)
    const candlestickSeries = optionArg.series?.find(
      (s: any) => s.type === 'candlestick',
    );
    expect(candlestickSeries).toBeDefined();
  });

  it('uses custom height when provided', () => {
    const { container } = render(
      <KLineChart data={klineData} height={600} />,
    );

    const chartDiv = container.querySelector('div[style]');
    expect(chartDiv).toHaveStyle({ height: '600px' });
  });

  it('cleans up chart instance on unmount', () => {
    const { unmount } = render(<KLineChart data={klineData} />);

    unmount();

    // dispose should be called during cleanup
    expect(mockDispose).toHaveBeenCalled();
  });
});
