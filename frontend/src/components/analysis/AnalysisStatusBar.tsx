/** AnalysisStatusBar — 轻量化状态指示（已整合到 AnalysisResult） */

import React from "react";
import { useAnalysisStore } from "../../store/analysisStore";
import { AnalysisStatus } from "../../domain/types";

/**
 * 此组件已被简化。
 * 状态指示（分析进行中/完成/失败）已整合到 AnalysisResult 组件中。
 * 保留此文件以避免导入错误，但不再渲染独立 Alert。
 */
const AnalysisStatusBar: React.FC = () => {
  const { status } = useAnalysisStore();

  // 状态指示已整合到 AnalysisResult，此组件不再独立渲染
  if (status === AnalysisStatus.IDLE) return null;

  return null;
};

export default AnalysisStatusBar;
