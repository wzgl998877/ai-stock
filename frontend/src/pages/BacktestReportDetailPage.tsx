/**
 * 回测报告详情页（T048，由 Drawer 页面化）。
 *
 * 路由 ``/strategy/backtest/report/:reportId?period=&signal_type=&window=``。
 * 一次拉全该周期明细（page_size=2000），页内切换信号类型/窗口为纯前端聚合：
 * 盈亏概览卡（T047 汇总同源）→ 收益分档分布 → 收益分布直方图 → 明细表
 * （盈利/亏损筛选 + 排序 + 分页 + 跳转 K 线）。统计口径见 ``domain/backtestStats``：
 * 按信号笔数；卖点为卖方视角（跌=卖对），红=信号方向正确。
 * 所有网络经 ``strategyService``（宪章前端红线）。
 */

import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  Alert, Button, Card, Col, Descriptions, Empty, Row, Segmented, Skeleton, Table, Tag, Typography, message,
} from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import {
  getReport,
  getReportDetails,
  getWatchlistSignals,
} from "../services/strategyService";
import {
  BACKTEST_DISCLAIMER,
  BACKTEST_RANGES,
  BACKTEST_WINDOWS,
  SIGNAL_TYPE_LABELS,
} from "../domain/constants";
import {
  filterByView,
  signalViewReturn,
  tierDistribution,
  winLossStats,
  type DetailFilter,
} from "../domain/backtestStats";
import type {
  BacktestReportDetail,
  BacktestSignalDetailItem,
  BacktestWindow,
  ChanlunPeriod,
  SignalType,
} from "../domain/types";
import BacktestStatCards from "../components/strategy/BacktestStatCards";
import ReturnTierTable from "../components/strategy/ReturnTierTable";
import ReturnDistributionChart from "../components/strategy/ReturnDistributionChart";

const { Text, Title } = Typography;

const ALL_SIGNAL_TYPES: SignalType[] = ["buy1", "buy2", "buy3", "sell1", "sell2", "sell3"];
const PERIOD_LABELS: Record<ChanlunPeriod, string> = { daily: "日 K", m30: "30 分钟" };
const FILTER_OPTS: { label: string; value: DetailFilter }[] = [
  { label: "全部", value: "all" },
  { label: "仅盈利", value: "win" },
  { label: "仅亏损", value: "loss" },
];

const BacktestReportDetailPage: React.FC = () => {
  const { reportId } = useParams();
  const id = Number(reportId);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [report, setReport] = useState<BacktestReportDetail | null>(null);
  const [reportLoading, setReportLoading] = useState(true);
  const [reportError, setReportError] = useState<string | null>(null);
  const [details, setDetails] = useState<BacktestSignalDetailItem[]>([]);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [nameMap, setNameMap] = useState<Map<string, string>>(new Map());
  const [detailFilter, setDetailFilter] = useState<DetailFilter>("all");

  // --- 报告与股票名称（名称仅辅助展示，失败静默降级为只显代码） ---
  useEffect(() => {
    if (!Number.isFinite(id) || id <= 0) {
      setReportError("无效的报告 ID");
      setReportLoading(false);
      return;
    }
    setReportLoading(true);
    getReport(id)
      .then(setReport)
      .catch((e: any) => setReportError(e?.message || "加载报告失败"))
      .finally(() => setReportLoading(false));
    getWatchlistSignals()
      .then((res) => {
        const m = new Map<string, string>();
        for (const it of res.items) m.set(it.stock_code, it.stock_name);
        setNameMap(m);
      })
      .catch(() => undefined);
  }, [id]);

  // --- 维度解析：query 优先，缺失/非法时回退（周期取报告内首个，信号类型取样本最大） ---
  const periods = useMemo(
    () => [...new Set((report?.summary ?? []).map((c) => c.period))],
    [report],
  );
  const periodParam = searchParams.get("period") as ChanlunPeriod | null;
  const period: ChanlunPeriod =
    periodParam && periods.includes(periodParam) ? periodParam : periods[0] ?? "daily";

  const signalTypes = useMemo(
    () => ALL_SIGNAL_TYPES.filter((st) =>
      (report?.summary ?? []).some((c) => c.period === period && c.signal_type === st && c.sample > 0),
    ),
    [report, period],
  );
  const defaultSignalType = useMemo(() => {
    const cells = (report?.summary ?? [])
      .filter((c) => c.period === period && c.sample > 0)
      .sort((a, b) => b.sample - a.sample);
    return cells[0]?.signal_type ?? null;
  }, [report, period]);

  const stParam = searchParams.get("signal_type") as SignalType | null;
  const signalType: SignalType =
    stParam && signalTypes.includes(stParam) ? stParam : defaultSignalType ?? "buy1";

  const winParam = Number(searchParams.get("window"));
  const window: BacktestWindow = BACKTEST_WINDOWS.includes(winParam as BacktestWindow)
    ? (winParam as BacktestWindow)
    : 20;

  const updateParams = (patch: Record<string, string>) => {
    const next = new URLSearchParams(searchParams);
    for (const [k, v] of Object.entries(patch)) next.set(k, v);
    setSearchParams(next, { replace: true });
  };

  // --- 明细：随周期拉全量（不按信号类型过滤，页内切换纯前端聚合） ---
  useEffect(() => {
    if (!report || !period) return;
    setDetailsLoading(true);
    getReportDetails(id, { period, page_size: 2000 })
      .then((res) => setDetails(res.items))
      .catch((e: any) => {
        setDetails([]);
        message.error(e?.message || "加载明细失败");
      })
      .finally(() => setDetailsLoading(false));
  }, [id, report, period]);

  // --- 当前 (period, signal_type, window) 的派生统计 ---
  const curItems = useMemo(
    () => details.filter((d) => d.signal_type === signalType),
    [details, signalType],
  );
  const stats = useMemo(() => winLossStats(curItems, window), [curItems, window]);
  const viewReturns = useMemo(
    () =>
      curItems
        .map((it) => signalViewReturn(it, window))
        .filter((v): v is number => v != null),
    [curItems, window],
  );
  const tier = useMemo(() => tierDistribution(viewReturns), [viewReturns]);
  const cell = useMemo(
    () =>
      (report?.summary ?? []).find(
        (c) => c.period === period && c.signal_type === signalType && c.window === window,
      ),
    [report, period, signalType, window],
  );
  const tableItems = useMemo(
    () => filterByView(curItems, window, detailFilter),
    [curItems, window, detailFilter],
  );

  const rangeLabel =
    BACKTEST_RANGES.find((r) => r.value === report?.meta.range_label)?.label ??
    report?.meta.range_label ??
    "—";

  const columns = [
    {
      title: "代码", dataIndex: "stock_code", width: 130,
      render: (c: string) => (
        <div style={{ fontVariantNumeric: "tabular-nums" }}>
          <span style={{ color: "#061b31" }}>{c}</span>
          <div style={{ fontSize: 11, color: "#64748d" }}>{nameMap.get(c) ?? "—"}</div>
        </div>
      ),
    },
    {
      title: "信号时间", dataIndex: "signal_time", width: 140,
      render: (t: string) => (t ? t.replace("T", " ").slice(0, 16) : "—"),
    },
    {
      title: "触发价", dataIndex: "trigger_price", width: 90, align: "right" as const,
      render: (v: number | null) => (v != null ? v.toFixed(2) : "—"),
    },
    {
      title: `${window}日涨跌`, key: "ret", width: 110, align: "right" as const,
      sorter: (a: BacktestSignalDetailItem, b: BacktestSignalDetailItem) => {
        const va = (a as any)[`ret_${window}`] as number | null;
        const vb = (b as any)[`ret_${window}`] as number | null;
        if (va == null) return 1;
        if (vb == null) return -1;
        return va - vb;
      },
      render: (_: unknown, r: BacktestSignalDetailItem) => {
        const raw = (r as any)[`ret_${window}`] as number | null;
        if (raw == null) return <Text type="secondary">—</Text>;
        // 颜色按信号视角（红=信号方向正确，绿=错误）；数字保留真实涨跌
        const view = signalViewReturn(r, window);
        const color = view != null && view > 0 ? "#ea2261" : view != null && view < 0 ? "#16c79a" : "#061b31";
        return (
          <span style={{ color, fontVariantNumeric: "tabular-nums" }}>
            {raw > 0 ? "+" : ""}{(raw * 100).toFixed(2)}%
          </span>
        );
      },
    },
    {
      title: "窗口状态", dataIndex: "window_complete", width: 90,
      render: (ok: boolean) =>
        ok ? (
          <Tag style={{ margin: 0 }}>已走完</Tag>
        ) : (
          <Tag color="warning" style={{ margin: 0 }}>未走完</Tag>
        ),
    },
    {
      title: "操作", width: 130,
      render: (_: unknown, r: BacktestSignalDetailItem) => (
        <a
          style={{ fontSize: 12 }}
          onClick={() =>
            navigate(
              `/market/stock/${r.stock_code}?signalDate=${String(r.signal_time).slice(0, 10)}&period=${period}`,
            )
          }
        >
          在 K 线图中查看
        </a>
      ),
    },
  ];

  if (reportError) {
    return (
      <div style={{ padding: 16, maxWidth: 1200, margin: "0 auto" }}>
        <Alert
          type="error"
          message={reportError}
          showIcon
          action={<Link to="/strategy/backtest">返回回测页</Link>}
        />
      </div>
    );
  }

  return (
    <div style={{ padding: 16, maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
        <Button
          type="text"
          size="small"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate("/strategy/backtest")}
        >
          返回回测
        </Button>
        <Title level={4} style={{ margin: 0 }}>
          回测报告 #{Number.isFinite(id) ? id : "—"}
        </Title>
      </div>

      {reportLoading ? (
        <Skeleton active paragraph={{ rows: 4 }} />
      ) : report ? (
        <>
          <Card size="small" style={{ marginBottom: 12 }}>
            <Descriptions
              size="small"
              column={{ xs: 2, sm: 3, lg: 6 }}
              items={[
                { key: "range", label: "回测区间", children: rangeLabel },
                { key: "stocks", label: "自选股票", children: `${report.meta.stock_count} 只` },
                { key: "signals", label: "信号总数", children: `${report.meta.signal_total} 笔` },
                {
                  key: "bench",
                  label: "同期基准(沪深300)",
                  children:
                    report.meta.benchmark_return != null
                      ? `${(report.meta.benchmark_return * 100).toFixed(2)}%`
                      : "暂无",
                },
                { key: "algo", label: "算法版本", children: report.meta.algo_version || "—" },
                {
                  key: "time",
                  label: "生成时间",
                  children: report.meta.finished_at
                    ? report.meta.finished_at.replace("T", " ").slice(0, 16)
                    : "—",
                },
              ]}
            />
          </Card>

          <Card size="small" title="维度" style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "center" }}>
              <div>
                <Text type="secondary" style={{ marginRight: 8, fontSize: 12 }}>周期</Text>
                <Segmented
                  size="small"
                  value={period}
                  onChange={(v) => updateParams({ period: String(v) })}
                  options={periods.map((p) => ({ label: PERIOD_LABELS[p], value: p }))}
                />
              </div>
              <div>
                <Text type="secondary" style={{ marginRight: 8, fontSize: 12 }}>信号类型</Text>
                <Segmented
                  size="small"
                  value={signalType}
                  onChange={(v) => updateParams({ signal_type: String(v) })}
                  options={signalTypes.map((st) => ({
                    label: SIGNAL_TYPE_LABELS[st],
                    value: st,
                  }))}
                />
              </div>
              <div>
                <Text type="secondary" style={{ marginRight: 8, fontSize: 12 }}>观察窗口</Text>
                <Segmented
                  size="small"
                  value={window}
                  onChange={(v) => updateParams({ window: String(v) })}
                  options={BACKTEST_WINDOWS.map((w) => ({ label: `${w} 日`, value: w }))}
                />
              </div>
            </div>
            <Alert
              style={{ marginTop: 12 }}
              type="info"
              showIcon
              banner
              message="统计按信号笔数（同一股票可能多笔信号）；卖点为卖方视角——信号后下跌视为「卖对」，红=信号方向正确，绿=方向错误。"
            />
          </Card>

          <Card size="small" title="盈亏概览" style={{ marginBottom: 12 }}>
            <BacktestStatCards stats={stats} cell={cell} loading={detailsLoading} />
          </Card>

          <Row gutter={12} style={{ marginBottom: 12 }}>
            <Col xs={24} lg={12}>
              <Card size="small" title={`收益分档分布（${window} 日窗口，信号视角）`} style={{ height: "100%" }}>
                <ReturnTierTable tiers={tier.tiers} maxCount={tier.maxCount} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card size="small" title={`收益分布直方图（${window} 日窗口，信号视角）`} style={{ height: "100%" }}>
                <ReturnDistributionChart returns={viewReturns} window={window} height={240} />
              </Card>
            </Col>
          </Row>

          <Card
            size="small"
            title="信号明细"
            extra={
              <Segmented
                size="small"
                value={detailFilter}
                onChange={(v) => setDetailFilter(v as DetailFilter)}
                options={FILTER_OPTS}
              />
            }
          >
            {curItems.length === 0 && !detailsLoading ? (
              <Empty description="该信号类型在本周期无样本" />
            ) : (
              <Table<BacktestSignalDetailItem>
                rowKey={(r) => `${r.stock_code}-${r.signal_time}`}
                size="small"
                loading={detailsLoading}
                dataSource={tableItems}
                columns={columns as any}
                pagination={{ pageSize: 20, showSizeChanger: true, size: "small", showTotal: (t) => `共 ${t} 笔` }}
                scroll={{ x: "max-content" }}
              />
            )}
          </Card>

          <div style={{ textAlign: "center", color: "#999", fontSize: 12, marginTop: 16 }}>
            {BACKTEST_DISCLAIMER}
          </div>
        </>
      ) : (
        <Empty description="报告不存在或已被删除" />
      )}
    </div>
  );
};

export default BacktestReportDetailPage;
