import React, { useCallback, useEffect, useRef, useState } from "react";
import { Layout, Typography, Alert, Tabs, Space, message } from "antd";
import { useSyncStore } from "../store/syncStore";
import DataSourceSelector, { type SyncFormData } from "../components/sync/DataSourceSelector";
import SyncProgress from "../components/sync/SyncProgress";
import SyncHistory from "../components/sync/SyncHistory";
import { syncService } from "../services/syncService";

const { Content } = Layout;
const { Title } = Typography;

const SyncPanel: React.FC = () => {
  const {
    currentSync,
    syncStatus,
    resetSync,
    startSync,
    updateProgress,
    completeSync,
    failSync,
    loadHistory,
  } = useSyncStore();

  const [availableSources] = useState<string[]>(["tushare", "akshare", "baostock", "sina"]);
  const abortRef = useRef<AbortController | null>(null);

  const handleSync = useCallback(
    (data: SyncFormData) => {
      startSync(data.sourceType, data.dataType);

      const controller = syncService.executeSync(
        data,
        (eventType: string, eventData: any) => {
          switch (eventType) {
            case "sync_started":
              break; // Already set state via startSync
            case "sync_progress":
              updateProgress(eventData);
              break;
            case "sync_completed":
              completeSync(eventData);
              message.success(`同步完成: 成功 ${eventData.success} / 失败 ${eventData.failed}`);
              loadHistory(1);
              break;
            case "sync_failed":
              failSync(eventData.error || "同步执行失败");
              message.error(`同步失败: ${eventData.error || "未知错误"}`);
              break;
            case "sync_error":
              failSync(eventData.message || "请求错误");
              message.error(eventData.message || "请求错误");
              break;
            default:
              break;
          }
        },
        (err: Error) => {
          failSync(err.message);
          message.error(`同步连接失败: ${err.message}`);
        },
      );

      abortRef.current = controller;
    },
    [startSync, updateProgress, completeSync, failSync, loadHistory],
  );

  const handleCancel = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    resetSync();
  }, [resetSync]);

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, []);

  return (
    <Content style={{ padding: 24 }}>
      <Title level={4}>数据同步</Title>
      <Alert
        message="数据同步说明"
        description="选择数据源和数据类型，点击同步按钮将数据从外部数据源拉取到本地数据库。全市场同步可能需要数分钟。"
        type="info"
        showIcon
        closable
        style={{ marginBottom: 24 }}
      />

      <DataSourceSelector
        onSync={handleSync}
        isSyncing={syncStatus === "running"}
        availableSources={availableSources}
      />

      <SyncProgress
        status={syncStatus}
        processed={currentSync?.processed || 0}
        total={currentSync?.total || 0}
        success={currentSync?.success || 0}
        failed={currentSync?.failed || 0}
        errorMessage={currentSync?.errorMessage || null}
        sourceType={currentSync?.sourceType || ""}
        dataType={currentSync?.dataType || ""}
        durationMs={currentSync?.durationMs || null}
      />

      {syncStatus === "running" && (
        <Space style={{ marginBottom: 16 }}>
          <Alert type="warning" message="同步正在进行中，请勿关闭页面" showIcon />
        </Space>
      )}

      <Tabs
        defaultActiveKey="history"
        items={[
          {
            key: "history",
            label: "同步历史",
            children: <SyncHistory />,
          },
        ]}
      />

      <div style={{ textAlign: "center", padding: "24px 0 16px", marginTop: 16, borderTop: "1px solid #f6f9fc" }}>
        <Typography.Text style={{ fontSize: 12, color: "#d0d5dd" }}>
          本工具仅供投研参考，不构成任何投资建议
        </Typography.Text>
      </div>
    </Content>
  );
};

export default SyncPanel;
