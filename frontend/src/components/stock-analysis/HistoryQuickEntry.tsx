import React, { useEffect, useState } from "react";
import { RightOutlined, ClockCircleOutlined } from "@ant-design/icons";
import { listAnalysisRecords } from "../../services/stockAnalysisService";
import type { AnalysisRecordListItem } from "../../domain/types";

interface Props {
  stockCode: string;
  onSelect: (recordId: string) => void;
}

/** 历史3条快捷入口 */
const HistoryQuickEntry: React.FC<Props> = ({ stockCode, onSelect }) => {
  const [records, setRecords] = useState<AnalysisRecordListItem[]>([]);

  useEffect(() => {
    if (!stockCode) return;
    let cancelled = false;
    listAnalysisRecords({ page: 1, pageSize: 3 })
      .then((res) => {
        if (cancelled) return;
        // 过滤出当前股票的记录
        const filtered = res.items.filter(
          (item) => item.stocks?.some((s) => s.code === stockCode)
        );
        setRecords(filtered.slice(0, 3));
      })
      .catch(() => {
        if (!cancelled) setRecords([]);
      });
    return () => { cancelled = true; };
  }, [stockCode]);

  if (!stockCode || records.length === 0) return null;

  return (
    <div style={{ marginTop: 20 }}>
      <div
        style={{
          fontSize: 13,
          fontWeight: 500,
          color: "#8c8c8c",
          marginBottom: 10,
        }}
      >
        最近分析
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {records.map((record) => (
          <div
            key={record.id}
            onClick={() => onSelect(record.id)}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "10px 14px",
              borderRadius: 8,
              background: "#fafafa",
              border: "1px solid #f0f0f0",
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  color: "#333",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {record.title}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
                <ClockCircleOutlined style={{ fontSize: 11, color: "#bfbfbf" }} />
                <span style={{ fontSize: 11, color: "#bfbfbf" }}>
                  {formatDate(record.updated_at)}
                </span>
                <span
                  style={{
                    fontSize: 11,
                    padding: "0 6px",
                    borderRadius: 4,
                    background: record.status === "completed" ? "#f6ffed" : record.status === "in_progress" ? "#fffbe6" : "#f5f5f5",
                    color: record.status === "completed" ? "#52c41a" : record.status === "in_progress" ? "#faad14" : "#bfbfbf",
                  }}
                >
                  {record.status === "completed" ? "已完成" : record.status === "in_progress" ? "进行中" : "已停止"}
                </span>
              </div>
            </div>
            <RightOutlined style={{ fontSize: 12, color: "#d9d9d9" }} />
          </div>
        ))}
      </div>
    </div>
  );
};

function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hours = String(d.getHours()).padStart(2, "0");
  const mins = String(d.getMinutes()).padStart(2, "0");
  return `${month}-${day} ${hours}:${mins}`;
}

export default HistoryQuickEntry;
