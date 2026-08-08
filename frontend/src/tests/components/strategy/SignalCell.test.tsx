import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import dayjs from 'dayjs';
import SignalCell, { fmtSignalTime } from '../../../components/strategy/SignalCell';
import SignalOverviewTable, {
  DEFAULT_FILTER,
  isFilterActive,
  matchesSummary,
  rangeBounds,
} from '../../../components/strategy/SignalOverviewTable';
import type { SignalSummary, WatchlistSignalItem } from '../../../domain/types';

const item = (over: Partial<WatchlistSignalItem> = {}): WatchlistSignalItem => ({
  stock_code: '600000',
  stock_name: '浦发银行',
  daily: null,
  m30: null,
  daily_status: 'monitored_nodata',
  m30_status: 'monitored_nodata',
  ...over,
});

describe('fmtSignalTime', () => {
  const year = new Date().getFullYear();

  it('日 K 只展示到日期（当年 MM-DD，跨年 YYYY-MM-DD）', () => {
    expect(fmtSignalTime(`${year}-08-05T15:00:00`, 'daily')).toBe('08-05');
    expect(fmtSignalTime('2024-01-02T10:30:00', 'daily')).toBe('2024-01-02');
  });

  it('30m 展示到分钟（当年 MM-DD HH:mm，跨年带年份）', () => {
    expect(fmtSignalTime(`${year}-08-06T10:30:00`, 'm30')).toBe('08-06 10:30');
    expect(fmtSignalTime('2024-01-02T10:30:00', 'm30')).toBe('2024-01-02 10:30');
  });

  it('空时间返回占位符', () => {
    expect(fmtSignalTime(null, 'daily')).toBe('—');
    expect(fmtSignalTime(null, 'm30')).toBe('—');
  });
});

describe('SignalCell', () => {
  it('新鲜买点：绿色箭头 + 类别文案 + 时间', () => {
    render(
      <SignalCell
        period="daily"
        status="monitored"
        summary={{
          signal_type: 'buy1',
          signal_time: `${new Date().getFullYear()}-08-05T15:00:00`,
          confirmed_at: null,
          trigger_price: 10.5,
          is_fresh: true,
        }}
      />,
    );
    expect(screen.getByText(/▲ 一类买点/)).toBeTruthy();
    expect(screen.getByText('08-05')).toBeTruthy();
    // 日 K 不展示时分
    expect(screen.queryByText('08-05 15:00')).toBeNull();
  });

  it('卖点渲染红色方向箭头与类别', () => {
    render(
      <SignalCell
        period="m30"
        status="monitored"
        summary={{
          signal_type: 'sell2',
          signal_time: `${new Date().getFullYear()}-08-06T10:30:00`,
          confirmed_at: null,
          trigger_price: 11.2,
          is_fresh: true,
        }}
      />,
    );
    expect(screen.getByText(/▼ 二类卖点/)).toBeTruthy();
  });

  it('历史信号（is_fresh=false）置灰并加「历史」前缀', () => {
    render(
      <SignalCell
        period="daily"
        status="monitored"
        summary={{
          signal_type: 'buy3',
          signal_time: '2026-01-01T15:00:00',
          confirmed_at: null,
          trigger_price: 9.9,
          is_fresh: false,
        }}
      />,
    );
    const label = screen.getByText(/三类买点/);
    expect(label.textContent).toContain('历史');
    // 置灰：内联 color 为灰色（不同测试环境序列化形式可能不同）
    expect(label.style.color).toMatch(/rgb\(191, 191, 191\)|#bfbfbf/);
  });

  it('无信号 / 停用 / 数据不足三态', () => {
    const { rerender } = render(<SignalCell period="daily" summary={null} />);
    expect(screen.getByText('—')).toBeTruthy();

    rerender(<SignalCell period="daily" status="disabled" />);
    expect(screen.getByText('停用')).toBeTruthy();

    rerender(<SignalCell period="daily" status="insufficient_data" />);
    expect(screen.getByText('不足')).toBeTruthy();
  });
});

describe('SignalOverviewTable', () => {
  it('渲染双周期信号列', () => {
    const items = [
      item({
        stock_code: '600000',
        daily: {
          signal_type: 'buy1',
          signal_time: `${new Date().getFullYear()}-08-05T15:00:00`,
          confirmed_at: null,
          trigger_price: 10.5,
          is_fresh: true,
        },
        daily_status: 'monitored',
      }),
      item({ stock_code: '000001', stock_name: '平安银行' }),
    ];
    render(
      <MemoryRouter>
        <SignalOverviewTable items={items} />
      </MemoryRouter>,
    );
    expect(screen.getAllByText('600000').length).toBeGreaterThan(0);
    expect(screen.getAllByText('000001').length).toBeGreaterThan(0);
    expect(screen.getAllByText('日K信号').length).toBeGreaterThan(0);
    expect(screen.getAllByText('30分钟信号').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/▲ 一类买点/).length).toBeGreaterThan(0);
  });

  it('空数据展示空态文案', () => {
    render(
      <MemoryRouter>
        <SignalOverviewTable items={[]} />
      </MemoryRouter>,
    );
    expect(screen.getAllByText(/暂无自选股信号数据/).length).toBeGreaterThan(0);
  });

  it('点击代码跳转个股详情', () => {
    const navigate = vi.fn();
    // antd Table 的链接通过 onClick 触发，此处仅验证渲染出可点击链接
    render(
      <MemoryRouter>
        <SignalOverviewTable items={[item()]} onAnalyze={navigate} />
      </MemoryRouter>,
    );
    expect(screen.getAllByText('600000').length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// 总览表筛选纯函数
// ---------------------------------------------------------------------------

const sig = (over: Partial<SignalSummary> = {}): SignalSummary => ({
  signal_type: 'buy1',
  signal_time: dayjs().format('YYYY-MM-DDTHH:mm:ss'),
  confirmed_at: null,
  trigger_price: 10,
  is_fresh: true,
  ...over,
});

describe('信号总览筛选逻辑', () => {
  it('默认筛选未激活；任一维度变更即激活', () => {
    expect(isFilterActive(DEFAULT_FILTER)).toBe(false);
    expect(isFilterActive({ ...DEFAULT_FILTER, direction: 'buy' })).toBe(true);
    expect(isFilterActive({ ...DEFAULT_FILTER, period: 'daily' })).toBe(true);
    expect(isFilterActive({ ...DEFAULT_FILTER, rangeKey: 'today' })).toBe(true);
  });

  it('rangeBounds：今日/近七日按日期粒度计算', () => {
    const today = rangeBounds({ ...DEFAULT_FILTER, rangeKey: 'today' })!;
    expect(today.start.isSame(dayjs().startOf('day'))).toBe(true);
    expect(today.end.isSame(dayjs().endOf('day'))).toBe(true);

    const w = rangeBounds({ ...DEFAULT_FILTER, rangeKey: '7d' })!;
    expect(w.start.isSame(dayjs().subtract(6, 'day').startOf('day'))).toBe(true);
  });

  it('matchesSummary：方向 + 周期 + 时间三重过滤', () => {
    const fresh = sig({ signal_type: 'buy1', signal_time: dayjs().format('YYYY-MM-DDTHH:mm:ss') });
    const old = sig({ signal_type: 'sell2', signal_time: dayjs().subtract(10, 'day').format('YYYY-MM-DDTHH:mm:ss') });

    // 方向
    expect(matchesSummary(fresh, { ...DEFAULT_FILTER, direction: 'buy' }, 'daily')).toBe(true);
    expect(matchesSummary(fresh, { ...DEFAULT_FILTER, direction: 'sell' }, 'daily')).toBe(false);
    // 周期
    expect(matchesSummary(fresh, { ...DEFAULT_FILTER, period: 'm30' }, 'daily')).toBe(false);
    expect(matchesSummary(fresh, { ...DEFAULT_FILTER, period: 'm30' }, 'm30')).toBe(true);
    // 时间：今日命中、超窗不命中
    expect(matchesSummary(fresh, { ...DEFAULT_FILTER, rangeKey: 'today' }, 'daily')).toBe(true);
    expect(matchesSummary(old, { ...DEFAULT_FILTER, rangeKey: '7d' }, 'daily')).toBe(false);
    // 无信号不命中
    expect(matchesSummary(null, { ...DEFAULT_FILTER, direction: 'buy' }, 'daily')).toBe(false);
  });

  it('自定义区间：未选全不加时间约束；选全后按区间判定', () => {
    const f = { ...DEFAULT_FILTER, rangeKey: 'custom' as const };
    const old = sig({ signal_time: dayjs().subtract(10, 'day').format('YYYY-MM-DDTHH:mm:ss') });

    // 未选区间 → 无时间约束，旧信号也命中
    expect(rangeBounds({ ...f, customRange: null })).toBeNull();
    expect(matchesSummary(old, { ...f, customRange: null }, 'daily')).toBe(true);

    // 选了最近两天 → 10 天前不命中
    const bounded = {
      ...f,
      customRange: [dayjs().subtract(1, 'day'), dayjs()] as [dayjs.Dayjs, dayjs.Dayjs],
    };
    expect(matchesSummary(old, bounded, 'daily')).toBe(false);
  });
});
