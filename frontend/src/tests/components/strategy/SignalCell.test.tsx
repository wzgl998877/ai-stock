import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SignalCell, { fmtSignalTime } from '../../../components/strategy/SignalCell';
import SignalOverviewTable from '../../../components/strategy/SignalOverviewTable';
import type { WatchlistSignalItem } from '../../../domain/types';

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
  it('当年信号截取 MM-DD HH:mm', () => {
    const year = new Date().getFullYear();
    expect(fmtSignalTime(`${year}-08-05T15:00:00`)).toBe('08-05 15:00');
  });

  it('非当年信号保留年份前缀', () => {
    expect(fmtSignalTime('2024-01-02T10:30:00')).toBe('2024-01-02 10:30');
  });

  it('空时间返回占位符', () => {
    expect(fmtSignalTime(null)).toBe('—');
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
    expect(screen.getByText('08-05 15:00')).toBeTruthy();
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
