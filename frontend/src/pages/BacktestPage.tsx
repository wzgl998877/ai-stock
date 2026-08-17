/**
 * 回测页（T046）。
 *
 * 选区间（1/3/5y）+ 周期 → 发起回测（SSE 进度）→ 完成展示汇总表（T047）→
 * 点击单元格跳转报告详情页（T048，``/strategy/backtest/report/:id``）；并支持切换历史报告。
 * 所有网络经 ``strategyService``（宪章前端红线）。
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card, Radio, Checkbox, Button, Progress, Alert, Empty, Spin, Typography, message, Tag,
} from "antd";
import {
  runBacktest,
  getReports,
  getReport,
  type BacktestParams,
} from "../services/strategyService";
import {
  BACKTEST_RANGES,
  STRATEGY_DISCLAIMER_LONG,
} from "../domain/constants";
import type {
  BacktestRange,
  BacktestReportDetail,
  BacktestReportListItem,
  ChanlunPeriod,
  StrategySSEEvent,
} from "../domain/types";
import BacktestSummaryTable from "../components/strategy/BacktestSummaryTable";

const { Text, Title } = Typography;

const PERIOD_OPTS = [
  { label: "日 K", value: "daily" as ChanlunPeriod },
  { label: "30 分钟", value: "m30" as ChanlunPeriod },
];

const BacktestPage: React.FC = () => {
  const navigate = useNavigate();
  const [range, setRange] = useState<BacktestRange>("3y");
  const [periods, setPeriods] = useState<ChanlunPeriod[]>(["daily", "m30"]);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(0);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<BacktestReportDetail | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reports, setReports] = useState<BacktestReportListItem[]>([]);
  const [lastReportId, setLastReportId] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchReports = useCallback(async (): Promise<BacktestReportListItem[]> => {
    try {
      const res = await getReports({ page_size: 10 });
      setReports(res.items);
      return res.items;
    } catch {
      setReports([]);
      return [];
    }
  }, []);

  useEffect(() => {
    // 进入页面：拉取历史报告，若有则直接展示最新一条（无需手动点）
    fetchReports().then((items) => {
      if (items.length > 0) loadReport(items[0].report_id);
    });
    // loadReport 由 useCallback 稳定引用，仅首屏自动加载一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchReports]);

  const loadReport = useCallback(async (id: number) => {
    setReportLoading(true);
    setLastReportId(id);
    try {
      const r = await getReport(id);
      setReport(r);
    } catch (e: any) {
      message.error(e?.message || "加载报告失败");
    } finally {
      setReportLoading(false);
    }
  }, []);

  const start = async () => {
    if (running) return;
    if (periods.length === 0) {
      message.warning("请至少选择一个周期");
      return;
    }
    setRunning(true);
    setError(null);
    setDone(0);
    setTotal(0);
    setReport(null);
    abortRef.current = new AbortController();

    const onEvent = (evt: StrategySSEEvent) => {
      switch (evt.event) {
        case "backtest_started":
          setTotal(evt.data.stock_count);
          setDone(0);
          break;
        case "backtest_progress":
          setDone((d) => d + 1);
          break;
        case "backtest_completed":
          loadReport(evt.data.report_id).then(() => fetchReports());
          break;
        case "backtest_error":
          setError(evt.data.message);
          break;
        default:
          break;
      }
    };

    const params: BacktestParams = { range, periods };
    try {
      await runBacktest(params, onEvent, abortRef.current.signal);
    } catch (e: any) {
      if (e?.name !== "AbortError") setError(e?.message || "回测失败");
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  };

  const stop = () => {
    abortRef.current?.abort();
    setRunning(false);
  };

  const onCellClick = (period: ChanlunPeriod, signal_type: any, window: any) => {
    if (lastReportId == null) return;
    navigate(
      `/strategy/backtest/report/${lastReportId}?period=${period}&signal_type=${signal_type}&window=${window}`,
    );
  };

  const progressPct = total > 0 ? Math.round((done / total) * 100) : running ? 0 : 0;

  return (
    <div style={{ padding: 16, maxWidth: 1200, margin: "0 auto" }}>
      <Title level={4} style={{ marginBottom: 16 }}>缠论信号历史回测</Title>

      <Card size="small" style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "center" }}>
          <div>
            <Text type="secondary" style={{ marginRight: 8 }}>回测区间</Text>
            <Radio.Group value={range} onChange={(e) => setRange(e.target.value)} optionType="button" buttonStyle="solid" size="small">
              {BACKTEST_RANGES.map((r) => (
                <Radio.Button key={r.value} value={r.value}>{r.label}</Radio.Button>
              ))}
            </Radio.Group>
          </div>
          <div>
            <Text type="secondary" style={{ marginRight: 8 }}>周期</Text>
            <Checkbox.Group options={PERIOD_OPTS} value={periods} onChange={(v) => setPeriods(v as ChanlunPeriod[])} />
          </div>
          <div>
            {running ? (
              <Button danger size="small" onClick={stop}>停止</Button>
            ) : (
              <Button type="primary" size="small" onClick={start}>发起回测</Button>
            )}
          </div>
        </div>

        {running && (
          <div style={{ marginTop: 16 }}>
            <Progress percent={progressPct} size="small" status="active"
              format={() => `${done} / ${total} 只`} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              正在对自选股逐只重算区间信号并统计窗口收益，请稍候…
            </Text>
          </div>
        )}
        {error && <Alert style={{ marginTop: 12 }} type="error" message={error} showIcon />}
      </Card>

      <Card size="small" title="回测汇总" style={{ marginBottom: 12 }}>
        {reportLoading ? (
          <div style={{ textAlign: "center", padding: 24 }}><Spin /></div>
        ) : report ? (
          <BacktestSummaryTable
            summary={report.summary}
            benchmarkReturn={report.meta.benchmark_return}
            onCellClick={onCellClick}
          />
        ) : (
          <Empty description="尚未生成回测报告，选择区间后点击「发起回测」" />
        )}
      </Card>

      <Card size="small" title="历史报告" style={{ marginBottom: 12 }}>
        {reports.length > 0 ? (
          <>
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                点击任一条目切换查看；列表按生成时间倒序，最新在最上。
              </Text>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {reports.map((r) => {
                const active = r.report_id === lastReportId;
                const statusTag = (
                  r.status === "failed" ? { color: "error", text: "失败" } :
                  r.status === "running" ? { color: "processing", text: "进行中" } :
                  { color: "success", text: "完成" }
                );
                return (
                  <div
                    key={r.report_id}
                    onClick={() => loadReport(r.report_id)}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      gap: 12, padding: "8px 12px", borderRadius: 6, cursor: "pointer",
                      border: `1px solid ${active ? "#533afd" : "#e5edf5"}`,
                      background: active ? "#f3f1ff" : "#fafbfc",
                      transition: "background 0.15s",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
                      <Tag color="purple" style={{ margin: 0 }}>{r.range_label}</Tag>
                      <span style={{ fontSize: 13, color: "#061b31", fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>
                        {r.create_time ? r.create_time.replace("T", " ").slice(0, 16) : "—"}
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
                      <span style={{ fontSize: 12, color: "#64748d", fontVariantNumeric: "tabular-nums" }}>
                        {r.stock_count} 股 · {r.signal_total} 信号
                      </span>
                      <Tag color={statusTag.color} style={{ margin: 0 }}>{statusTag.text}</Tag>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <Empty description="暂无历史报告，发起回测后将自动生成并展示最新结果" />
        )}
      </Card>

      <div style={{ textAlign: "center", color: "#999", fontSize: 12, marginTop: 16 }}>
        {STRATEGY_DISCLAIMER_LONG}
      </div>
    </div>
  );
};

export default BacktestPage;
