import { describe, it, expect } from 'vitest';
import { isMarketOpen, isTradingDay, beijingNow } from '../../utils/marketTime';

// 辅助：用 Date.UTC 构造「北京时间某日某时」对应的绝对时刻（北京 = UTC+8）。
// 例如北京 周一 10:00 = UTC 周一 02:00。
const bj = (y: number, m: number, d: number, h: number, min = 0) =>
  new Date(Date.UTC(y, m - 1, d, h - 8, min));  // 北京 h 点 = UTC (h-8) 点

// 2026-08-10 为周一（2026-08-05 周三 +5 天）；08-09 周日；08-08 周六。
describe('marketTime', () => {
  it('isTradingDay：周一为交易日，周末非交易日', () => {
    expect(isTradingDay(bj(2026, 8, 10, 10))).toBe(true);   // 周一
    expect(isTradingDay(bj(2026, 8, 14, 10))).toBe(true);   // 周五
    expect(isTradingDay(bj(2026, 8, 9, 10))).toBe(false);   // 周日
    expect(isTradingDay(bj(2026, 8, 8, 10))).toBe(false);   // 周六
  });

  it('isMarketOpen：交易时段内为 true（上午+下午）', () => {
    expect(isMarketOpen(bj(2026, 8, 10, 10, 0))).toBe(true);   // 周一 10:00
    expect(isMarketOpen(bj(2026, 8, 10, 11, 30))).toBe(true);  // 周一 11:30（含端点）
    expect(isMarketOpen(bj(2026, 8, 10, 14, 0))).toBe(true);   // 周一 14:00
    expect(isMarketOpen(bj(2026, 8, 10, 15, 0))).toBe(true);   // 周一 15:00（含端点）
  });

  it('isMarketOpen：交易时段外为 false', () => {
    expect(isMarketOpen(bj(2026, 8, 10, 9, 0))).toBe(false);   // 周一 09:00 未开盘
    expect(isMarketOpen(bj(2026, 8, 10, 9, 29))).toBe(false);  // 开盘前 1 分钟
    expect(isMarketOpen(bj(2026, 8, 10, 12, 0))).toBe(false);  // 周一 12:00 午休
    expect(isMarketOpen(bj(2026, 8, 10, 16, 0))).toBe(false);  // 周一 16:00 已收盘
  });

  it('isMarketOpen：周末全天为 false', () => {
    expect(isMarketOpen(bj(2026, 8, 9, 10, 0))).toBe(false);   // 周日 10:00
    expect(isMarketOpen(bj(2026, 8, 8, 14, 0))).toBe(false);   // 周六 14:00
  });

  it('beijingNow：返回北京小时，与输入时区无关', () => {
    // 同一绝对时刻（北京周一 10:00）应得到 getHours()==10
    const t = bj(2026, 8, 10, 10, 0);
    expect(beijingNow(t).getHours()).toBe(10);
    expect(beijingNow(bj(2026, 8, 10, 14, 30)).getMinutes()).toBe(30);
  });
});
