import { describe, it, expect } from 'vitest';
import {
  signalViewReturn,
  winLossStats,
  tierDistribution,
  filterByView,
  RETURN_TIERS,
} from '../../domain/backtestStats';
import type { BacktestSignalDetailItem } from '../../domain/types';

const item = (over: Partial<BacktestSignalDetailItem> = {}): BacktestSignalDetailItem => ({
  stock_code: '600000',
  signal_type: 'buy1',
  signal_time: '2025-01-06T10:00:00',
  trigger_price: 10.0,
  ret_5: null,
  ret_10: null,
  ret_20: null,
  ret_60: null,
  window_complete: true,
  ...over,
});

describe('signalViewReturn', () => {
  it('买点返回真实涨跌', () => {
    expect(signalViewReturn(item({ signal_type: 'buy2', ret_20: 0.05 }), 20)).toBe(0.05);
    expect(signalViewReturn(item({ signal_type: 'buy3', ret_20: -0.05 }), 20)).toBe(-0.05);
  });

  it('卖点取反（跌 = 卖对 = 赢）', () => {
    expect(signalViewReturn(item({ signal_type: 'sell1', ret_20: -0.05 }), 20)).toBe(0.05);
    expect(signalViewReturn(item({ signal_type: 'sell2', ret_20: 0.05 }), 20)).toBe(-0.05);
  });

  it('窗口越界（null）与缺失值返回 null', () => {
    expect(signalViewReturn(item({ window_complete: false }), 20)).toBeNull();
    expect(signalViewReturn(item({ ret_20: Number.NaN }), 20)).toBeNull();
  });
});

describe('winLossStats', () => {
  it('按信号视角统计盈亏笔数、平局、涉及股票数与胜率', () => {
    const items = [
      item({ stock_code: '600000', ret_20: 0.05 }),          // 赢
      item({ stock_code: '600000', ret_20: 0.02 }),          // 赢（同股第二笔）
      item({ stock_code: '000001', ret_20: -0.03 }),         // 亏
      item({ stock_code: '000002', ret_20: 0 }),             // 平局
      item({ stock_code: '000003', window_complete: false }), // 越界剔除
    ];
    const s = winLossStats(items, 20);
    expect(s.total).toBe(4);
    expect(s.win).toBe(2);
    expect(s.loss).toBe(1);
    expect(s.flat).toBe(1);
    expect(s.stockCount).toBe(3);
    expect(s.winRate).toBeCloseTo(0.5); // 分母含平局，与后端一致
  });

  it('卖点跌为赢：与买点口径统一', () => {
    const s = winLossStats([item({ signal_type: 'sell1', ret_20: -0.08 })], 20);
    expect(s.win).toBe(1);
    expect(s.loss).toBe(0);
  });

  it('空样本返回 total=0 / winRate=null', () => {
    const s = winLossStats([], 20);
    expect(s.total).toBe(0);
    expect(s.winRate).toBeNull();
  });
});

describe('tierDistribution', () => {
  it('分档边界为左闭右开：0.10 归 +10~20%，0.2 归 ≥+20%，0 归 0~+10%', () => {
    const { tiers } = tierDistribution([0.1, 0.2, 0, 0.05]);
    expect(tiers.find((t) => t.label === '+10% ~ +20%')!.count).toBe(1);
    expect(tiers.find((t) => t.label === '≥ +20%')!.count).toBe(1);
    expect(tiers.find((t) => t.label === '0 ~ +10%')!.count).toBe(2);
  });

  it('负值边界：-0.1 归 -10~0，-0.2 归 -20~-10，<-20% 单独一档', () => {
    const { tiers } = tierDistribution([-0.1, -0.2, -0.5]);
    expect(tiers.find((t) => t.label === '-10% ~ 0')!.count).toBe(1);
    expect(tiers.find((t) => t.label === '-20% ~ -10%')!.count).toBe(1);
    expect(tiers.find((t) => t.label === '< -20%')!.count).toBe(1);
  });

  it('占比与 maxCount 归一化基准', () => {
    const { tiers, maxCount } = tierDistribution([0.05, 0.05, -0.3]);
    expect(tiers.find((t) => t.label === '0 ~ +10%')!.pct).toBeCloseTo(2 / 3);
    expect(maxCount).toBe(2);
  });

  it('空序列返回全 0 档与 null 占比', () => {
    const { tiers, maxCount } = tierDistribution([]);
    expect(tiers).toHaveLength(RETURN_TIERS.length);
    expect(tiers.every((t) => t.count === 0 && t.pct === null)).toBe(true);
    expect(maxCount).toBe(0);
  });
});

describe('filterByView', () => {
  const items = [
    item({ stock_code: '600000', ret_20: 0.05 }),
    item({ stock_code: '000001', ret_20: -0.03 }),
    item({ stock_code: '000002', ret_20: 0 }),
    item({ stock_code: '000003', window_complete: false }),
  ];

  it('all 返回原数组（含越界样本）', () => {
    expect(filterByView(items, 20, 'all')).toHaveLength(4);
  });

  it('win 只保留信号视角为正的样本', () => {
    const r = filterByView(items, 20, 'win');
    expect(r).toHaveLength(1);
    expect(r[0].stock_code).toBe('600000');
  });

  it('loss 只保留信号视角为负的样本', () => {
    const r = filterByView(items, 20, 'loss');
    expect(r).toHaveLength(1);
    expect(r[0].stock_code).toBe('000001');
  });

  it('卖点跌被 win 保留', () => {
    const r = filterByView([item({ signal_type: 'sell1', ret_20: -0.08 })], 20, 'win');
    expect(r).toHaveLength(1);
  });
});
