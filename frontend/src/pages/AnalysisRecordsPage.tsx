import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, DatePicker, Empty, Input, Spin, Tooltip } from "antd";
import { SearchOutlined, SyncOutlined, ThunderboltOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import { listAnalysisRecords } from "../services/stockAnalysisService";
import type { AnalysisRecordListItem } from "../domain/types";

const RangePicker = DatePicker.RangePicker;

// ── 筛选 Tab 配置 ──
const STATUS_TABS: { label: string; value: string }[] = [
  { label: "全部", value: "all" },
  { label: "已完成", value: "completed" },
  { label: "分析中", value: "in_progress" },
  { label: "已停止", value: "stopped" },
];

const ACTION_OPTIONS: { label: string; value: string; color: string }[] = [
  { label: "全部", value: "all", color: "#64748b" },
  { label: "看多", value: "buy", color: "#ef4444" },
  { label: "看空", value: "sell", color: "#00A86B" },
  { label: "观望", value: "hold", color: "#94a3b8" },
];

const MODE_OPTIONS: { label: string; value: string; color: string }[] = [
  { label: "全部", value: "all", color: "#64748b" },
  { label: "快速", value: "quick", color: "#533afd" },
  { label: "深度", value: "full", color: "#2A6DFF" },
];

// ── 卡片内使用的配置 ──
const STATUS_CFG: Record<string, { color: string; label: string; bg: string }> = {
  completed: { color: "#00A86B", label: "已完成", bg: "rgba(0,168,107,0.1)" },
  in_progress: { color: "#2A6DFF", label: "分析中", bg: "rgba(42,109,255,0.1)" },
  stopped: { color: "#94a3b8", label: "已停止", bg: "rgba(148,163,184,0.1)" },
  failed: { color: "#E74C3C", label: "失败", bg: "rgba(231,76,60,0.1)" },
  pending: { color: "#94a3b8", label: "待处理", bg: "rgba(148,163,184,0.1)" },
};

const MODE_CFG: Record<string, { label: string; color: string; bg: string }> = {
  quick: { label: "快速", color: "#533afd", bg: "rgba(83,58,253,0.1)" },
  full: { label: "深度", color: "#2A6DFF", bg: "rgba(42,109,255,0.1)" },
};

const ACTION_CFG: Record<string, { label: string; color: string; bg: string }> = {
  buy: { label: "看多", color: "#E74C3C", bg: "rgba(231,76,60,0.1)" },
  sell: { label: "看空", color: "#00A86B", bg: "rgba(0,168,107,0.1)" },
  hold: { label: "观望", color: "#94a3b8", bg: "rgba(148,163,184,0.1)" },
  "买入": { label: "看多", color: "#E74C3C", bg: "rgba(231,76,60,0.1)" },
  "卖出": { label: "看空", color: "#00A86B", bg: "rgba(0,168,107,0.1)" },
  "持有": { label: "观望", color: "#94a3b8", bg: "rgba(148,163,184,0.1)" },
};

/** 将后端返回的 action（中文/英文）统一映射为标准化 key */
function normalizeAction(action: string | undefined | null): string | null {
  if (!action) return null;
  const map: Record<string, string> = {
    buy: "buy", sell: "sell", hold: "hold",
    "买入": "buy", "卖出": "sell", "持有": "hold",
  };
  return map[action] ?? null;
}

// ── 页面 ──
const AnalysisRecordsPage: React.FC = () => {
  const navigate = useNavigate();
  const [allRecords, setAllRecords] = useState<AnalysisRecordListItem[]>([]);
  const [loading, setLoading] = useState(true);

  // 筛选状态
  const [keyword, setKeyword] = useState("");
  const [statusTab, setStatusTab] = useState("all");
  const [actionPill, setActionPill] = useState("all");
  const [modePill, setModePill] = useState("all");
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);

  // Tab 下划线
  const tabsRef = useRef<HTMLDivElement>(null);
  const [underline, setUnderline] = useState({ left: 0, width: 0 });

  const fetchRecords = useCallback(() => {
    setLoading(true);
    listAnalysisRecords({ pageSize: 100 })
      .then((res) => setAllRecords(res.items))
      .catch(() => setAllRecords([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchRecords(); }, [fetchRecords]);

  // Tab 下划线跟随
  useEffect(() => {
    requestAnimationFrame(() => {
      if (!tabsRef.current) return;
      const els = tabsRef.current.querySelectorAll("[data-tab]");
      const idx = STATUS_TABS.findIndex((t) => t.value === statusTab);
      if (idx >= 0 && els[idx]) {
        const el = els[idx] as HTMLElement;
        setUnderline({ left: el.offsetLeft, width: el.offsetWidth });
      }
    });
  }, [statusTab]);

  // 客户端筛选
  const filtered = useMemo(() => {
    let r = allRecords;
    if (keyword.trim()) {
      const kw = keyword.trim().toLowerCase();
      r = r.filter(
        (rec) =>
          rec.stocks?.some((s) => s.code.toLowerCase().includes(kw) || s.name.toLowerCase().includes(kw)) ||
          rec.title.toLowerCase().includes(kw)
      );
    }
    if (statusTab !== "all") r = r.filter((rec) => rec.status === statusTab);
    if (actionPill !== "all") r = r.filter((rec) => normalizeAction(rec.decision?.action) === actionPill);
    if (modePill !== "all") r = r.filter((rec) => rec.analysis_mode === modePill);
    if (dateRange) {
      const s = dateRange[0].startOf("day"), e = dateRange[1].endOf("day");
      r = r.filter((rec) => { const d = dayjs(rec.created_at); return d.isAfter(s) && d.isBefore(e); });
    }
    return r;
  }, [allRecords, keyword, statusTab, actionPill, modePill, dateRange]);

  const rangePickerValue: [Dayjs, Dayjs] | null = dateRange;

  return (
    <div style={{ background: "#F7F9FC", padding: 24, minHeight: "100vh", overflowY: "auto" }}>
      <div style={{ maxWidth: 1400, margin: "0 auto" }}>

        {/* ── Header ── */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <div>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#0f172a" }}>分析记录</div>
            <div style={{ fontSize: 13, color: "#94a3b8", marginTop: 2 }}>
              {`共 ${filtered.length} 条${filtered.length !== allRecords.length ? ` / 总 ${allRecords.length} 条` : ""}`}
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <Input
              placeholder="搜索股票代码 / 名称"
              prefix={<SearchOutlined style={{ color: "#bfbfbf", fontSize: 13 }} />}
              allowClear
              size="small"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              style={{ width: 200, borderRadius: 8 }}
            />
            <Button icon={<SyncOutlined />} size="small" onClick={fetchRecords} loading={loading}>
              刷新
            </Button>
          </div>
        </div>

        {/* ── 第一行：状态 Tab + 日期 ── */}
        <div style={{ display: "flex", alignItems: "center", borderBottom: "2px solid #e5edf5", position: "relative" }}>
          <div ref={tabsRef} style={{ display: "flex" }}>
            {STATUS_TABS.map((tab) => (
              <div
                key={tab.value}
                data-tab={tab.value}
                onClick={() => setStatusTab(tab.value)}
                style={{
                  padding: "12px 24px",
                  cursor: "pointer",
                  fontSize: 14,
                  fontWeight: statusTab === tab.value ? 600 : 400,
                  color: statusTab === tab.value ? "#2A6DFF" : "#64748b",
                  transition: "color 0.2s",
                  userSelect: "none",
                }}
              >
                {tab.label}
              </div>
            ))}
          </div>
          <div style={{ flex: 1 }} />
          <RangePicker
            value={rangePickerValue}
            onChange={(dates) => {
              if (dates && dates[0] && dates[1]) setDateRange([dates[0], dates[1]]);
              else setDateRange(null);
            }}
            placeholder={["开始日期", "结束日期"]}
            allowClear
            size="small"
            style={{ width: 240 }}
          />
          <div style={{
            position: "absolute", bottom: -2, height: 2,
            background: "#2A6DFF", borderRadius: 1,
            transition: "left 0.3s ease, width 0.3s ease",
            left: underline.left, width: underline.width,
          }} />
        </div>

        {/* ── 第二行：胶囊筛选 ── */}
        <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "12px 0 16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 13, color: "#94a3b8" }}>决策：</span>
            {ACTION_OPTIONS.map((opt) => (
              <span
                key={opt.value}
                onClick={() => setActionPill(opt.value)}
                style={{
                  display: "inline-block", padding: "2px 12px", borderRadius: 12,
                  fontSize: 13, cursor: "pointer", userSelect: "none",
                  fontWeight: actionPill === opt.value ? 600 : 400,
                  color: actionPill === opt.value ? "#fff" : opt.color,
                  background: actionPill === opt.value ? opt.color : "transparent",
                  border: `1px solid ${opt.color}`,
                  transition: "all 0.2s",
                }}
              >
                {opt.label}
              </span>
            ))}
          </div>
          <div style={{ width: 1, height: 16, background: "#e5edf5" }} />
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 13, color: "#94a3b8" }}>模式：</span>
            {MODE_OPTIONS.map((opt) => (
              <span
                key={opt.value}
                onClick={() => setModePill(opt.value)}
                style={{
                  display: "inline-block", padding: "2px 12px", borderRadius: 12,
                  fontSize: 13, cursor: "pointer", userSelect: "none",
                  fontWeight: modePill === opt.value ? 600 : 400,
                  color: modePill === opt.value ? "#fff" : opt.color,
                  background: modePill === opt.value ? opt.color : "transparent",
                  border: `1px solid ${opt.color}`,
                  transition: "all 0.2s",
                }}
              >
                {opt.label}
              </span>
            ))}
          </div>
        </div>

        {/* ── 卡片网格 ── */}
        {loading && !allRecords.length ? (
          <div style={{ textAlign: "center", padding: "80px 0" }}>
            <Spin size="large" />
            <div style={{ marginTop: 16, color: "#2A6DFF", fontSize: 13, fontWeight: 500 }}>加载分析记录...</div>
          </div>
        ) : filtered.length === 0 ? (
          <Empty
            description={keyword || actionPill !== "all" || statusTab !== "all" || dateRange ? "没有符合条件的记录" : "暂无分析记录，去开始你的第一次分析"}
            style={{ padding: "60px 0" }}
          >
            {!keyword && actionPill === "all" && statusTab === "all" && !dateRange && (
              <Button type="primary" onClick={() => navigate("/stock-analysis")} style={{ borderRadius: 8 }}>
                去分析
              </Button>
            )}
          </Empty>
        ) : (
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 480px), 1fr))",
            gap: 16,
            alignItems: "stretch",
          }}>
            {filtered.map((record) => (
              <AnalysisCard key={record.id} record={record} onClick={() => navigate(`/stock-analysis?recordId=${record.id}`)} />
            ))}
          </div>
        )}

        {/* 免责声明 */}
        <div style={{
          marginTop: 24, padding: "10px 16px",
          background: "#ffffff", borderRadius: 16,
          boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)",
          textAlign: "center", fontSize: 12, color: "#94a3b8",
        }}>
          以上为 AI 分析参考，不构成投资建议
        </div>
      </div>
    </div>
  );
};

// ── 单张分析记录卡片（完全复刻 ImpactEventCard 布局） ──
const AnalysisCard: React.FC<{ record: AnalysisRecordListItem; onClick: () => void }> = ({ record, onClick }) => {
  const stock = record.stocks?.[0];
  const statusCfg = STATUS_CFG[record.status] || STATUS_CFG.stopped;
  const modeCfg = MODE_CFG[record.analysis_mode] || MODE_CFG.full;
  const decision = record.decision;
  const actionCfg = decision?.action ? ACTION_CFG[decision.action] || ACTION_CFG[normalizeAction(decision.action)!] : null;
  const progress = record.progress || { completed: 0, total: 2 };
  const pct = progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0;

  const formatTime = (dateStr: string) => {
    if (!dateStr) return { short: "", full: "" };
    const d = new Date(dateStr);
    const now = new Date();
    const diffMin = Math.floor((now.getTime() - d.getTime()) / 60000);
    const full = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
    if (diffMin < 60) return { short: `${diffMin}分钟前`, full };
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return { short: `${diffH}小时前`, full };
    return { short: `${d.getMonth() + 1}月${d.getDate()}日`, full };
  };

  const time = formatTime(record.created_at);

  const normAction = normalizeAction(decision?.action);

  const verdict = normAction === "buy"
    ? `建议买入，置信度 ${decision!.confidence}%`
    : normAction === "sell"
    ? `建议卖出，置信度 ${decision!.confidence}%`
    : normAction === "hold"
    ? `建议观望，置信度 ${decision!.confidence}%`
    : record.status === "in_progress"
    ? `分析进行中 (${pct}%)`
    : "分析完成，等待决策";

  const verdictColor = actionCfg?.color || "#94a3b8";

  return (
    <div
      style={{
        background: "#ffffff",
        borderRadius: 16,
        padding: "16px 20px",
        boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)",
        cursor: "pointer",
        transition: "all 0.25s ease",
        display: "flex",
        gap: 16,
      }}
      onClick={onClick}
      onMouseEnter={(e) => {
        const el = e.currentTarget;
        el.style.transform = "translateY(-2px)";
        el.style.boxShadow = "0 8px 24px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)";
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget;
        el.style.transform = "none";
        el.style.boxShadow = "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)";
      }}
    >
      {/* 左侧内容 */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* 第一行：股票名 + 标签 + 时间 */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          {stock && (
            <span style={{ fontWeight: 600, fontSize: 14, color: "#0f172a", whiteSpace: "nowrap" }}>
              {stock.name}{" "}
              <span style={{ fontWeight: 400, color: "#94a3b8", fontSize: 12 }}>{stock.code}</span>
            </span>
          )}
          <span style={{ padding: "2px 10px", borderRadius: 12, fontSize: 12, fontWeight: 500, background: modeCfg.bg, color: modeCfg.color, whiteSpace: "nowrap" }}>
            {modeCfg.label}
          </span>
          <span style={{ padding: "2px 10px", borderRadius: 12, fontSize: 12, fontWeight: 500, background: statusCfg.bg, color: statusCfg.color, whiteSpace: "nowrap" }}>
            {statusCfg.label}
          </span>
          {actionCfg && (
            <span style={{ padding: "2px 10px", borderRadius: 12, fontSize: 12, fontWeight: 600, background: actionCfg.bg, color: actionCfg.color, whiteSpace: "nowrap" }}>
              {actionCfg.label}
            </span>
          )}
          <span style={{ marginLeft: "auto", flexShrink: 0 }}>
            <Tooltip title={time.full}>
              <span style={{ fontSize: 12, color: "#94a3b8", whiteSpace: "nowrap", cursor: "default" }}>
                {time.short}
              </span>
            </Tooltip>
          </span>
        </div>

        {/* 第二行：标题 */}
        <Tooltip title={record.title.length > 40 ? record.title : undefined}>
          <div style={{
            fontSize: 14, fontWeight: 600, color: "#0f172a", lineHeight: 1.5,
            marginBottom: record.summary ? 4 : 8,
            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
          }}>
            {record.title}
          </div>
        </Tooltip>

        {/* 第二行b：摘要 */}
        {record.summary && (
          <div style={{
            fontSize: 13, color: "#64748b", lineHeight: 1.5,
            display: "-webkit-box", WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical", overflow: "hidden",
            marginBottom: 8,
          }}>
            {record.summary}
          </div>
        )}

        {/* 第三行：AI 判断 */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: verdictColor, flexShrink: 0 }} />
          <span style={{ fontSize: 13, color: verdictColor, fontWeight: 500 }}>{verdict}</span>
        </div>
      </div>

      {/* 右侧：操作 */}
      <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", flexShrink: 0 }}>
        <Button
          type="primary"
          size="small"
          icon={<ThunderboltOutlined />}
          onClick={(e) => { e.stopPropagation(); onClick(); }}
          style={{ borderRadius: 8, background: "#2A6DFF", borderColor: "#2A6DFF", fontSize: 12 }}
        >
          查看详情
        </Button>
      </div>
    </div>
  );
};

export default AnalysisRecordsPage;
