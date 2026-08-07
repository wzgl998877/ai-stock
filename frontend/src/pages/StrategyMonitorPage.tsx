/**
 * 策略监控页（T053）。
 *
 * 计算状态卡片（日线 / 30m 最近一次运行：时间、耗时、总数/成功/失败、失败明细）+
 * 「立即重算」按钮（SSE 进度，复用 strategyStore.recalculate）+ 算法版本 +
 * 回测入口。所有网络经 ``strategyStore`` → ``strategyService``（宪章前端分层）。
 */

import React, { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Card, Radio, Button, Progress, Statistic, Row, Col, Tag, Empty, Spin, Alert, Typography, message,
} from "antd";
import {
  STRATEGY_DISCLAIMER_LONG,
} from "../domain/constants";
import type { RunStatusItem } from "../domain/types";
import { useStrategyStore } from "../store/strategyStore";
import SignalOverviewTable from "../components/strategy/SignalOverviewTable";

const { Title, Text } = Typography;

const PERIOD_OPTS = [
  { label: "日 K", value: "daily" as const },
  { label: "30 分钟", value: "m30" as const },
  { label: "双周期", value: "both" as const },
];

const PERIOD_LABEL: Record<string, string> = { daily: "日 K", m30: "30 分钟" };

function fmtTime(t: string | null): string {
  if (!t) return "—";
  return t.replace("T", " ").slice(0, 16);
}

const StatusCard: React.FC<{ title: string; item: RunStatusItem | null; loading: boolean }> = ({
  title, item, loading,
}) => {
  if (loading && !item) {
    return (
      <Card size="small" title={title}>
        <div style={{ textAlign: "center", padding: 24 }}><Spin /></div>
      </Card>
    );
  }
  if (!item || item.last_run_at == null) {
    return (
      <Card size="small" title={title}>
        <Empty description="尚未运行" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </Card>
    );
  }
  return (
    <Card size="small" title={title}>
      <Row gutter={[16, 8]}>
        <Col span={12}>
          <Statistic title="最近运行" valueRender={
            () => <span style={{ fontSize: 14, fontVariantNumeric: "tabular-nums" }}>{fmtTime(item.last_run_at)}</span>
          } />
        </Col>
        <Col span={12}>
          <Statistic title="耗时" valueRender={
            () => <span style={{ fontVariantNumeric: "tabular-nums" }}>{item.duration_ms != null ? `${(item.duration_ms / 1000).toFixed(1)}s` : "—"}</span>
          } />
        </Col>
        <Col span={8}>
          <Statistic title="总数" value={item.total ?? 0} valueStyle={{ fontVariantNumeric: "tabular-nums" }} />
        </Col>
        <Col span={8}>
          <Statistic title="成功" value={item.success ?? 0} valueStyle={{ color: "#16c79a", fontVariantNumeric: "tabular-nums" }} />
        </Col>
        <Col span={8}>
          <Statistic title="失败" value={item.failed ?? 0} valueStyle={{ color: item.failed ? "#ea2261" : undefined, fontVariantNumeric: "tabular-nums" }} />
        </Col>
      </Row>
      {item.failed_detail && item.failed_detail.length > 0 && (
        <div style={{ marginTop: 8, maxHeight: 96, overflowY: "auto" }}>
          {item.failed_detail.slice(0, 20).map((f, i) => (
            <Tag key={i} color="red" style={{ marginBottom: 4 }}>
              {f.stock_code}: {f.reason}
            </Tag>
          ))}
        </div>
      )}
    </Card>
  );
};

const StrategyMonitorPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    runStatus, runStatusLoading, fetchRunStatus,
    watchlistSignals, signalsLoading, fetchWatchlistSignals,
    recalcRunning, recalcPeriod, recalcTotal, recalcDone, recalcFailed, recalcSkipped, recalcError,
    recalculate, stopRecalc,
  } = useStrategyStore();
  const [period, setPeriod] = React.useState<"daily" | "m30" | "both">("both");

  useEffect(() => {
    fetchRunStatus();
    fetchWatchlistSignals();
  }, [fetchRunStatus, fetchWatchlistSignals]);

  const start = () => {
    recalculate({ period }).catch(() => message.error("重算失败"));
  };

  const progressPct = recalcTotal > 0 ? Math.round((recalcDone / recalcTotal) * 100) : 0;
  const algoVersion = runStatus?.algo_version || runStatus?.daily?.algo_version || "";

  return (
    <div style={{ padding: 16, maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>缠论策略监控</Title>
        <Link to="/strategy/backtest">
          <Button size="small">信号历史回测 →</Button>
        </Link>
      </div>

      <Card size="small" style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "center" }}>
          <div>
            <Text type="secondary" style={{ marginRight: 8 }}>重算周期</Text>
            <Radio.Group
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              optionType="button"
              buttonStyle="solid"
              size="small"
              disabled={recalcRunning}
            >
              {PERIOD_OPTS.map((o) => (
                <Radio.Button key={o.value} value={o.value}>{o.label}</Radio.Button>
              ))}
            </Radio.Group>
          </div>
          <div>
            {recalcRunning ? (
              <Button danger size="small" onClick={stopRecalc}>停止</Button>
            ) : (
              <Button type="primary" size="small" onClick={start}>立即重算</Button>
            )}
          </div>
          {algoVersion && (
            <Text type="secondary" style={{ fontSize: 12 }}>算法版本：{algoVersion}</Text>
          )}
        </div>

        {recalcRunning && (
          <div style={{ marginTop: 16 }}>
            <Progress
              percent={progressPct}
              size="small"
              status="active"
              format={() => `${recalcDone} / ${recalcTotal} 只`}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {recalcPeriod ? `正在重算 ${PERIOD_LABEL[recalcPeriod] || recalcPeriod}：` : ""}
              成功 {recalcDone} · 失败 {recalcFailed} · 跳过 {recalcSkipped}
            </Text>
          </div>
        )}
        {recalcError && <Alert style={{ marginTop: 12 }} type="error" message={recalcError} showIcon />}
      </Card>

      <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
        <Col xs={24} md={12}>
          <StatusCard title="日 K 计算状态" item={runStatus?.daily ?? null} loading={runStatusLoading} />
        </Col>
        <Col xs={24} md={12}>
          <StatusCard title="30 分钟计算状态" item={runStatus?.m30 ?? null} loading={runStatusLoading} />
        </Col>
      </Row>

      <Card size="small" title="信号总览（自选股 × 双周期）" style={{ marginBottom: 12 }}>
        <SignalOverviewTable
          items={watchlistSignals}
          loading={signalsLoading}
          onAnalyze={(code) => navigate(`/stock-analysis?code=${code}`)}
        />
      </Card>

      <div style={{ textAlign: "center", color: "#999", fontSize: 12, marginTop: 16 }}>
        {STRATEGY_DISCLAIMER_LONG}
      </div>
    </div>
  );
};

export default StrategyMonitorPage;
