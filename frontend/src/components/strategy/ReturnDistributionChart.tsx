/**
 * 20 日窗口收益分布直方图（T049）。
 *
 * 把明细的 ``ret_{window}`` 序列分箱为直方图（ECharts 命令式，沿用 ``KLineChart`` 风格）。
 * 正收益柱绿、负收益柱红（A 股习惯）；样本不足或全空时降级 Empty。
 */

import React, { useEffect, useMemo, useRef } from "react";
import * as echarts from "echarts";
import { Empty } from "antd";

interface ReturnDistributionChartProps {
  returns: number[];
  window: number;
  height?: number;
}

const BIN_COUNT = 11; // 居中分箱（含 0 点）

export const ReturnDistributionChart: React.FC<ReturnDistributionChartProps> = ({
  returns,
  window: win,
  height = 220,
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const instRef = useRef<echarts.ECharts | null>(null);

  const { bins, counts, colors } = useMemo(() => {
    const vals = returns.filter((v) => v != null && Number.isFinite(v));
    if (vals.length === 0) return { bins: [] as number[], counts: [] as number[], colors: [] as string[] };
    const lo = Math.min(...vals);
    const hi = Math.max(...vals);
    if (lo === hi) {
      return { bins: [lo], counts: [vals.length], colors: [lo >= 0 ? "#16c79a" : "#ea2261"] };
    }
    const step = (hi - lo) / BIN_COUNT;
    const edges = Array.from({ length: BIN_COUNT + 1 }, (_, i) => lo + i * step);
    const centers = edges.slice(0, BIN_COUNT).map((e, i) => (e + edges[i + 1]) / 2);
    const cs = new Array(BIN_COUNT).fill(0);
    for (const v of vals) {
      let idx = Math.floor((v - lo) / step);
      if (idx >= BIN_COUNT) idx = BIN_COUNT - 1;
      if (idx < 0) idx = 0;
      cs[idx] += 1;
    }
    const cols = centers.map((c) => (c >= 0 ? "#16c79a" : "#ea2261"));
    return { bins: centers, counts: cs, colors: cols };
  }, [returns]);

  useEffect(() => {
    if (!ref.current || bins.length === 0) return;
    if (instRef.current) {
      instRef.current.dispose();
      instRef.current = null;
    }
    instRef.current = echarts.init(ref.current);
    instRef.current.setOption({
      animation: false,
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: (params: any) => {
          const p = params[0];
          if (!p) return "";
          const pct = ((p.value as number) / Math.max(1, counts.reduce((a, b) => a + b, 0)) * 100).toFixed(0);
          return `收益 ${(p.name as number) * 100 >= 0 ? "+" : ""}${((p.name as number) * 100).toFixed(1)}%<br/>${p.value} 笔 (${pct}%)`;
        },
      },
      grid: { left: 40, right: 16, top: 16, bottom: 28 },
      xAxis: {
        type: "category",
        data: bins.map((b) => `${(b * 100).toFixed(1)}%`),
        axisLabel: { fontSize: 10, fontVariantNumeric: "tabular-nums" },
      },
      yAxis: {
        type: "value",
        minInterval: 1,
        axisLabel: { fontSize: 10, fontVariantNumeric: "tabular-nums" },
        splitLine: { lineStyle: { color: "#f0f0f0" } },
      },
      series: [
        {
          type: "bar",
          data: counts.map((v, i) => ({ value: v, itemStyle: { color: colors[i] } })),
          barMaxWidth: 32,
        },
      ],
    });
    const handleResize = () => instRef.current?.resize();
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      instRef.current?.dispose();
      instRef.current = null;
    };
  }, [bins, counts, colors]);

  if (bins.length === 0) {
    return (
      <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Empty description={`暂无 ${win} 日窗口收益样本`} />
      </div>
    );
  }

  return <div ref={ref} style={{ width: "100%", height }} />;
};

export default ReturnDistributionChart;
