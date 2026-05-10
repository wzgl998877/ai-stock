import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Empty, Progress, Tag, Typography } from "antd";
import { FileSearchOutlined, RightOutlined } from "@ant-design/icons";
import { listAnalysisRecords } from "../services/stockAnalysisService";
import type { AnalysisRecordListItem } from "../domain/types";

const { Text, Title } = Typography;

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  completed: { color: "#52c41a", label: "已完成" },
  in_progress: { color: "#faad14", label: "进行中" },
  stopped: { color: "#bfbfbf", label: "已停止" },
};

const MODE_MAP: Record<string, { color: string; label: string }> = {
  quick: { color: "#533afd", label: "快速" },
  full: { color: "#1677ff", label: "深度" },
};

const AnalysisRecordsPage: React.FC = () => {
  const navigate = useNavigate();
  const [records, setRecords] = useState<AnalysisRecordListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    listAnalysisRecords({ page: 1, pageSize: 50 })
      .then((res) => {
        setRecords(res.items);
        setTotal(res.total);
      })
      .catch(() => {
        setRecords([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleViewDetail = (recordId: string) => {
    navigate(`/stock-analysis?recordId=${recordId}`);
  };

  return (
    <div style={{ padding: "24px 32px", minHeight: "100vh" }}>
      <Title level={4} style={{ fontWeight: 400, marginBottom: 24 }}>
        <FileSearchOutlined style={{ marginRight: 8, color: "#533afd" }} />
        分析记录
        <Text style={{ fontSize: 13, color: "#8c8c8c", marginLeft: 12 }}>
          共 {total} 条
        </Text>
      </Title>

      {records.length === 0 && !loading ? (
        <Empty
          description={
            <div>
              <Text style={{ fontSize: 14, color: "#8c8c8c" }}>暂无分析记录</Text>
              <br />
              <Text style={{ fontSize: 12, color: "#bfbfbf" }}>开始你的第一次个股深度分析</Text>
            </div>
          }
          style={{ marginTop: 80 }}
        >
          <Button type="primary" onClick={() => navigate("/stock-analysis")}>
            去分析
          </Button>
        </Empty>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {records.map((record) => {
            const statusInfo = STATUS_MAP[record.status] || STATUS_MAP.stopped;
            const modeInfo = MODE_MAP[record.analysis_mode] || MODE_MAP.full;
            const stockInfo = record.stocks?.[0];
            const progress = record.progress || { completed: 0, total: 2 };
            const progressPct = progress.total > 0
              ? Math.round((progress.completed / progress.total) * 100)
              : 0;

            return (
              <Card
                key={record.id}
                size="small"
                style={{
                  borderRadius: 8,
                  border: "1px solid #f0f0f0",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
                styles={{ body: { padding: "16px 20px" } }}
                hoverable
                onClick={() => handleViewDetail(record.id)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  {/* 左侧信息 */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                      <Text style={{ fontSize: 16, fontWeight: 500, color: "#061b31" }} ellipsis>
                        {stockInfo
                          ? `${stockInfo.name}(${stockInfo.code})`
                          : record.title}
                      </Text>
                      <Tag
                        style={{
                          fontSize: 11,
                          borderRadius: 4,
                          margin: 0,
                          color: modeInfo.color,
                          background: `${modeInfo.color}10`,
                          border: `1px solid ${modeInfo.color}30`,
                        }}
                      >
                        {modeInfo.label}
                      </Tag>
                      <Tag
                        style={{
                          fontSize: 11,
                          borderRadius: 4,
                          margin: 0,
                          color: statusInfo.color,
                          background: `${statusInfo.color}10`,
                          border: `1px solid ${statusInfo.color}30`,
                        }}
                      >
                        {statusInfo.label}
                      </Tag>
                    </div>

                    {/* 微型进度条 */}
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <Progress
                        percent={progressPct}
                        size="small"
                        strokeColor={record.status === "completed" ? "#52c41a" : "#4096ff"}
                        showInfo={false}
                        style={{ width: 120, marginBottom: 0 }}
                      />
                      <Text style={{ fontSize: 11, color: "#bfbfbf" }}>
                        {progress.completed}/{progress.total} 完成
                      </Text>
                      <Text style={{ fontSize: 11, color: "#bfbfbf" }}>
                        {formatDateTime(record.updated_at)}
                      </Text>
                    </div>
                  </div>

                  {/* 右侧操作 */}
                  <Button
                    type="link"
                    size="small"
                    icon={<RightOutlined />}
                    style={{ color: "#8c8c8c" }}
                  >
                    查看详情
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

function formatDateTime(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hours = String(d.getHours()).padStart(2, "0");
  const mins = String(d.getMinutes()).padStart(2, "0");
  return `${month}-${day} ${hours}:${mins}`;
}

export default AnalysisRecordsPage;
