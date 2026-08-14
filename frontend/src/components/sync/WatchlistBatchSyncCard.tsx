import React, { useCallback, useEffect, useState } from "react";
import { Card, Select, Button, Typography, Space, message } from "antd";
import { SyncOutlined } from "@ant-design/icons";
import { useWatchlistStore, type WatchlistGroup } from "../../store/watchlistStore";

const { Text } = Typography;

/**
 * 自选分组批量同步卡片。
 *
 * 与 ``DataSourceSelector`` 的「单股 / 全市场」同步并列：
 * 这里按「自选分组」批量勾选，复用后端 ``POST /api/v1/watchlist/sync``
 * （异步后台任务，日K + 30m），落库后缠论分析即可读到新数据。
 *
 * 交互：点「同步」→ 接口毫秒级返回 → 提示「已开始后台同步，可关闭」。
 */
const WatchlistBatchSyncCard: React.FC = () => {
  const { groups, fetchGroups, syncGroups, syncing } = useWatchlistStore();
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([]);

  // 进入页面时拉一次分组列表（带股票数量）
  useEffect(() => {
    fetchGroups();
  }, [fetchGroups]);

  const handleSync = useCallback(async () => {
    if (selectedGroupIds.length === 0) {
      message.warning("请先选择至少一个分组");
      return;
    }
    try {
      const data = await syncGroups(selectedGroupIds);
      message.success({
        content: `已开始后台同步：${data.total} 只股票（已跨分组去重），日K + 30m，预计数分钟完成，可在下方「同步历史」查看。`,
        duration: 6,
      });
      setSelectedGroupIds([]);
    } catch (e: any) {
      message.error(e?.message || "启动同步失败");
    }
  }, [selectedGroupIds, syncGroups]);

  const totalStocks = groups
    .filter((g: WatchlistGroup) => selectedGroupIds.includes(g.id))
    .reduce((sum: number, g: WatchlistGroup) => sum + (g.stock_count || 0), 0);

  return (
    <Card
      size="small"
      title="自选分组批量同步"
      style={{ marginBottom: 16 }}
      extra={<Text type="secondary" style={{ fontSize: 12 }}>日K + 30m · 异步后台</Text>}
    >
      <Space wrap size="middle" style={{ width: "100%" }}>
        <Select
          mode="multiple"
          placeholder="选择要同步的自选分组"
          style={{ minWidth: 320 }}
          value={selectedGroupIds}
          onChange={setSelectedGroupIds}
          maxTagCount="responsive"
          options={groups.map((g: WatchlistGroup) => ({
            value: g.id,
            label: `${g.name}（${g.stock_count}）`,
          }))}
          disabled={syncing}
        />
        <Text type="secondary" style={{ fontSize: 12 }}>
          选中分组合计 {totalStocks} 只（同步前会跨分组去重）
        </Text>
        <Button
          type="primary"
          icon={<SyncOutlined spin={syncing} />}
          onClick={handleSync}
          loading={syncing}
          disabled={selectedGroupIds.length === 0}
        >
          {syncing ? "提交中..." : "同步数据"}
        </Button>
      </Space>
    </Card>
  );
};

export default WatchlistBatchSyncCard;
