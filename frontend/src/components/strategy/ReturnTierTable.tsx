/**
 * 回测收益分档分布表（纯 UI，T048 页面化）。
 *
 * 六档（信号视角）：≥+20% / +10~20% / 0~10% / -10~0 / -20~-10% / <-20%。
 * 每档一行：档位 + 内嵌比例条（按最大档归一化）+ 笔数 + 占比；
 * 盈利侧红条、亏损侧绿条（A 股习惯）。口径见 ``domain/backtestStats``。
 */

import React from "react";
import { Empty } from "antd";
import type { ReturnTierStat } from "../../domain/backtestStats";

const RED = "#ea2261";
const GREEN = "#16c79a";
const MUTED = "#64748d";

interface ReturnTierTableProps {
  tiers: ReturnTierStat[];
  /** 最大档计数（比例条宽度归一化基准） */
  maxCount: number;
}

export const ReturnTierTable: React.FC<ReturnTierTableProps> = ({ tiers, maxCount }) => {
  if (maxCount === 0) {
    return <Empty description="暂无样本，无法统计分档" style={{ padding: 24 }} />;
  }

  return (
    <div>
      {tiers.map((t) => {
        const width = maxCount > 0 ? Math.round((t.count / maxCount) * 100) : 0;
        const barColor = t.positive ? RED : GREEN;
        return (
          <div
            key={t.label}
            style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}
          >
            <span
              style={{
                width: 104,
                flexShrink: 0,
                fontSize: 12,
                color: "#273951",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {t.label}
            </span>
            <div
              style={{
                flex: 1,
                height: 16,
                background: "#f5f7fa",
                borderRadius: 3,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${width}%`,
                  height: "100%",
                  background: barColor,
                  opacity: t.count === 0 ? 0 : 0.85,
                  transition: "width 0.2s",
                }}
              />
            </div>
            <span
              style={{
                width: 52,
                flexShrink: 0,
                textAlign: "right",
                fontSize: 13,
                color: "#061b31",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {t.count} 笔
            </span>
            <span
              style={{
                width: 52,
                flexShrink: 0,
                textAlign: "right",
                fontSize: 12,
                color: MUTED,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {t.pct != null ? `${(t.pct * 100).toFixed(1)}%` : "—"}
            </span>
          </div>
        );
      })}
    </div>
  );
};

export default ReturnTierTable;
