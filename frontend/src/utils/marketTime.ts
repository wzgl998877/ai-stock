/**
 * A 股市场时间工具（北京时区，全局复用）。
 *
 * - {@link isMarketOpen}：当前是否在 A 股交易时段（9:30-11:30、13:00-15:00，周一至五）；
 * - {@link isTradingDay}：当前是否为交易日（周一至五）。
 *
 * 所有判断基于**北京时间（UTC+8）**，与用户浏览器本地时区无关——
 * 海外用户也能正确判断 A 股是否开盘。
 */

/**
 * 取「当前北京时间」对应的 Date（字段值为北京时刻）。
 *
 * 利用 `getTimezoneOffset` 抹掉本地时区，再加 UTC+8 偏移。
 * 返回的 Date 其 `getHours()` 等方法返回的是北京时刻。
 */
export function beijingNow(now: Date = new Date()): Date {
  const utc = now.getTime() + now.getTimezoneOffset() * 60000;
  return new Date(utc + 8 * 3600000);
}

/**
 * 是否为交易日（周一至周五）。
 *
 * ⚠️ 节假日（国庆/春节等）需交易日历精确判断，当前仅排除周末；
 * 后续可接入 AKShare `tool_trade_date_hist_sina` 补全。
 */
export function isTradingDay(now: Date = new Date()): boolean {
  const day = beijingNow(now).getDay();
  // 周日(0)、周六(6)休市
  return day !== 0 && day !== 6;
}

/**
 * 是否在 A 股交易时段（上午 9:30-11:30，下午 13:00-15:00，仅交易日）。
 */
export function isMarketOpen(now: Date = new Date()): boolean {
  if (!isTradingDay(now)) return false;
  const bj = beijingNow(now);
  const t = bj.getHours() * 60 + bj.getMinutes();
  return (t >= 570 && t <= 690) || (t >= 780 && t <= 900);
}
