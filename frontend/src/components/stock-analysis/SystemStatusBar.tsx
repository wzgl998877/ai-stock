import React from "react";
import { CheckCircleFilled } from "@ant-design/icons";

/** 系统状态栏：系统在线 | 市场状态 | 数据已同步 */
const SystemStatusBar: React.FC = () => {
  const marketStatus = getMarketStatus();

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        height: 36,
        padding: "0 16px",
        background: "linear-gradient(90deg, #f8f9fa 0%, #f0f2f5 100%)",
        borderRadius: 8,
        fontSize: 13,
        color: "#666",
        marginBottom: 16,
      }}
    >
      {/* 系统在线 */}
      <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: "#52c41a",
            display: "inline-block",
            animation: "pulse 2s infinite",
          }}
        />
        系统在线
      </span>

      <span style={{ color: "#d9d9d9" }}>|</span>

      {/* 市场状态 */}
      <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {marketStatus === "open" ? (
          <>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#52c41a", display: "inline-block" }} />
            <span style={{ color: "#52c41a" }}>交易中</span>
          </>
        ) : (
          <>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#bfbfbf", display: "inline-block" }} />
            <span>已收盘</span>
          </>
        )}
      </span>

      <span style={{ color: "#d9d9d9" }}>|</span>

      {/* 数据已同步 */}
      <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <CheckCircleFilled style={{ color: "#bfbfbf", fontSize: 12 }} />
        数据已同步
      </span>

      {/* CSS animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
};

/** 根据 A 股交易时间判断市场状态 */
function getMarketStatus(): "open" | "closed" {
  const now = new Date();
  const hours = now.getHours();
  const minutes = now.getMinutes();
  const time = hours * 60 + minutes;

  // A 股交易日：周一至周五 9:30-11:30, 13:00-15:00
  const day = now.getDay();
  if (day === 0 || day === 6) return "closed";

  if ((time >= 570 && time <= 690) || (time >= 780 && time <= 900)) {
    return "open";
  }
  return "closed";
}

export default SystemStatusBar;
