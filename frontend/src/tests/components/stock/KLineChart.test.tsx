import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
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
    render(<KLineChart data={[]} />);

    // 空数据走 Empty 占位，不渲染图表、不调用 setOption（优雅降级）
    expect(mockSetOption).not.toHaveBeenCalled();
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

  it('renders signal markPoints when signalMarks provided', () => {
    render(
      <KLineChart
        data={klineData}
        signalMarks={[
          { signal_type: 'buy1', time: '2026-01-02', price: 10.5, confirmed_at: '2026-01-02', level: 1 },
          { signal_type: 'sell2', time: '2026-01-06', price: 11.5, confirmed_at: '2026-01-06', level: 2 },
        ]}
      />,
    );

    expect(mockSetOption).toHaveBeenCalled();
    const optionArg = mockSetOption.mock.calls[0][0];
    const candlestickSeries = optionArg.series?.find((s: any) => s.type === 'candlestick');
    expect(candlestickSeries.markPoint).toBeDefined();
    expect(candlestickSeries.markPoint.data).toHaveLength(2);
    // 买绿 ▲ / 卖红 ▼
    expect(candlestickSeries.markPoint.data[0].itemStyle.color).toBe('#16c79a');
    expect(candlestickSeries.markPoint.data[1].itemStyle.color).toBe('#ea2261');
    // 卖点箭头翻转 180°
    expect(candlestickSeries.markPoint.data[1].symbolRotate).toBe(180);
    // coord 取日期前 10 字符对齐 x 轴
    expect(candlestickSeries.markPoint.data[0].coord[0]).toBe('2026-01-02');
  });

  it('hides markPoints when showChanlun=false', () => {
    render(
      <KLineChart
        data={klineData}
        signalMarks={[
          { signal_type: 'buy1', time: '2026-01-02', price: 10.5, confirmed_at: '2026-01-02', level: 1 },
        ]}
        showChanlun={false}
      />,
    );

    const optionArg = mockSetOption.mock.calls[0][0];
    const candlestickSeries = optionArg.series?.find((s: any) => s.type === 'candlestick');
    expect(candlestickSeries.markPoint).toBeUndefined();
  });

  // ---------- T038：缠论结构图层（笔/线段 markLine + 中枢 markArea） ----------
  const structureData = {
    strokes: [
      { start: { time: '2026-01-02', price: 10.5 }, end: { time: '2026-01-03', price: 10.8 }, direction: 'up' as const, confirmed: true },
    ],
    segments: [
      { start: { time: '2026-01-02', price: 10.5 }, end: { time: '2026-01-06', price: 11.5 }, direction: 'up' as const, confirmed: false },
    ],
    zhongshu: [
      { zd: 10.6, zg: 11.0, dd: 10.5, gg: 11.2, enter_time: '2026-01-02', exit_time: '2026-01-06' },
    ],
    last_kline_time: '2026-01-06',
    algo_version: '1.0.0',
  };

  it('renders structure markLine (strokes+segments) and markArea (zhongshu)', () => {
    render(<KLineChart data={klineData} structure={structureData} />);

    const optionArg = mockSetOption.mock.calls[0][0];
    const candlestickSeries = optionArg.series?.find((s: any) => s.type === 'candlestick');
    // 1 笔 + 1 线段 = 2 条 markLine（实现中线段在前、笔在后）
    expect(candlestickSeries.markLine).toBeDefined();
    expect(candlestickSeries.markLine.data).toHaveLength(2);
    // 线段在前：未确认 → dashed
    const segLine = candlestickSeries.markLine.data[0];
    expect(segLine[1].lineStyle.type).toBe('dashed');
    // 笔在后：已确认 → solid
    const strokeLine = candlestickSeries.markLine.data[1];
    expect(strokeLine[1].lineStyle.type).toBe('solid');
    // 1 个中枢矩形
    expect(candlestickSeries.markArea).toBeDefined();
    expect(candlestickSeries.markArea.data).toHaveLength(1);
    // 中枢矩形以 [enter_time, zd] → [exit_time, zg] 圈定
    const area = candlestickSeries.markArea.data[0];
    expect(area[0].xAxis).toBe('2026-01-02');
    expect(area[0].yAxis).toBe(10.6);
    expect(area[1].yAxis).toBe(11.0);
  });

  it('omits markLine/markArea when structure is null', () => {
    render(<KLineChart data={klineData} structure={null} />);

    const optionArg = mockSetOption.mock.calls[0][0];
    const candlestickSeries = optionArg.series?.find((s: any) => s.type === 'candlestick');
    expect(candlestickSeries.markLine).toBeUndefined();
    expect(candlestickSeries.markArea).toBeUndefined();
  });

  // ---------- T038：highlightDate 经 dataZoom startValue/endValue 定位 ----------
  it('positions dataZoom via startValue/endValue when highlightDate hits a trading day', () => {
    render(<KLineChart data={klineData} highlightDate="2026-01-03" />);

    const optionArg = mockSetOption.mock.calls[0][0];
    expect(optionArg.dataZoom[0].startValue).toBe('2026-01-02'); // 窗口左端（idx-40 截到 0）
    expect(optionArg.dataZoom[0].endValue).toBe('2026-01-06'); // 窗口右端（idx+20 截到末尾）
    expect(optionArg.dataZoom[0].start).toBeUndefined();
  });

  it('falls back to percentage dataZoom when highlightDate is absent', () => {
    render(<KLineChart data={klineData} />);

    const optionArg = mockSetOption.mock.calls[0][0];
    expect(optionArg.dataZoom[0].start).toBeDefined();
    expect(optionArg.dataZoom[0].startValue).toBeUndefined();
  });

  it('falls back to percentage dataZoom when highlightDate misses the range', () => {
    render(<KLineChart data={klineData} highlightDate="2099-12-31" />);

    const optionArg = mockSetOption.mock.calls[0][0];
    expect(optionArg.dataZoom[0].start).toBeDefined();
    expect(optionArg.dataZoom[0].startValue).toBeUndefined();
  });

  // ---------- T041：周/月 K 隐藏缠论图层 + 提示 ----------
  it('hides chanlun marks on weekly period even when signalMarks/structure provided', () => {
    render(
      <KLineChart
        data={klineData}
        period="weekly"
        signalMarks={[
          { signal_type: 'buy1', time: '2026-01-02', price: 10.5, confirmed_at: '2026-01-02', level: 1 },
        ]}
        structure={structureData}
      />,
    );

    const optionArg = mockSetOption.mock.calls[0][0];
    const candlestickSeries = optionArg.series?.find((s: any) => s.type === 'candlestick');
    expect(candlestickSeries.markPoint).toBeUndefined();
    expect(candlestickSeries.markLine).toBeUndefined();
    expect(candlestickSeries.markArea).toBeUndefined();
  });

  it('shows "unsupported" notice on monthly period when chanlun enabled', () => {
    const { queryByText } = render(<KLineChart data={klineData} period="monthly" />);
    expect(queryByText('当前周期暂不支持缠论分析')).toBeInTheDocument();
  });

  it('does not show "unsupported" notice on daily period', () => {
    const { queryByText } = render(<KLineChart data={klineData} period="daily" />);
    expect(queryByText('当前周期暂不支持缠论分析')).not.toBeInTheDocument();
  });

  it('cleans up chart instance on unmount', () => {
    const { unmount } = render(<KLineChart data={klineData} />);

    unmount();

    // dispose should be called during cleanup
    expect(mockDispose).toHaveBeenCalled();
  });
});
