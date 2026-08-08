/**
 * 策略监控配置页：逐股逐周期监控启停（独立页面）。
 *
 * 自选股页仅展示信号；监控开关统一在此管理。
 * 关闭某周期后，定时调度与手动重算均跳过该股的该周期（后端 t_strategy_monitor_config）。
 */

import React, { useEffect } from "react";
import { Card, Typography } from "antd";
import SignalMonitorConfigTable from "../components/strategy/SignalMonitorConfigTable";
import { STRATEGY_DISCLAIMER_LONG } from "../domain/constants";
import { useStrategyStore } from "../store/strategyStore";

const { Title, Text } = Typography;

const StrategyMonitorConfigPage: React.FC = () => {
  const { watchlistSignals, signalsLoading, fetchWatchlistSignals } = useStrategyStore();

  useEffect(() => {
    fetchWatchlistSignals();
  }, [fetchWatchlistSignals]);

  return (
    <div style={{ padding: 16, maxWidth: 900, margin: "0 auto" }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>监控配置</Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          逐股逐周期启停：关闭后定时计算与手动重算均跳过该股的对应周期
        </Text>
      </div>

      <Card size="small" style={{ marginBottom: 12 }}>
        <SignalMonitorConfigTable items={watchlistSignals} loading={signalsLoading} />
      </Card>

      <div style={{ textAlign: "center", color: "#999", fontSize: 12, marginTop: 16 }}>
        {STRATEGY_DISCLAIMER_LONG}
      </div>
    </div>
  );
};

export default StrategyMonitorConfigPage;
