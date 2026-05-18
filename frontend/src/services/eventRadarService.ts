/** 事件雷达 API 服务 */

import api from "./api";

const BASE = "/api/v1/event-radar";

export const eventRadarService = {
  /** 获取影响事件列表 */
  getImpacts: async (params?: {
    status?: string;
    start_date?: string;
    end_date?: string;
    sentiment?: string;
    limit?: number;
    offset?: number;
  }) => {
    const res = await api.get(`${BASE}/impacts`, { params });
    return res.data;
  },

  /** 获取影响事件详情 */
  getImpactDetail: async (impactId: number) => {
    const res = await api.get(`${BASE}/impacts/${impactId}`);
    return res.data;
  },

  /** 获取影响统计 */
  getStats: async () => {
    const res = await api.get(`${BASE}/stats`);
    return res.data;
  },

  /** 生成 AI 解读 */
  generateAiInsight: async (impactId: number) => {
    const res = await api.post(`${BASE}/impacts/${impactId}/ai-insight`);
    return res.data;
  },

  /** 获取未读预警 */
  getAlerts: async (limit: number = 10) => {
    const res = await api.get(`${BASE}/alerts`, { params: { limit } });
    return res.data;
  },

  /** 获取未读预警数量 */
  getUnreadCount: async () => {
    const res = await api.get(`${BASE}/alerts/unread-count`);
    return res.data;
  },

  /** 标记预警已读 */
  markAlertRead: async (alertId: number) => {
    const res = await api.put(`${BASE}/alerts/${alertId}/read`);
    return res.data;
  },

  /** 获取今日晨报 */
  getTodayBriefing: async () => {
    const res = await api.get(`${BASE}/briefing/today`);
    return res.data;
  },

  /** 获取晨报历史 */
  getBriefingHistory: async () => {
    const res = await api.get(`${BASE}/briefing/history`);
    return res.data;
  },

  /** 标记晨报已读 */
  markBriefingRead: async (briefingId: number) => {
    const res = await api.put(`${BASE}/briefing/${briefingId}/read`);
    return res.data;
  },

  /** 获取雷达配置 */
  getConfig: async () => {
    const res = await api.get(`${BASE}/config`);
    return res.data;
  },

  /** 更新雷达配置 */
  updateConfig: async (config: any) => {
    const res = await api.put(`${BASE}/config`, config);
    return res.data;
  },

  /** 获取自选股影响状态 */
  getStockImpacts: async () => {
    const res = await api.get(`${BASE}/stock-impacts`);
    return res.data;
  },
};
