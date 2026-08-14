import api from './api';

const BASE = '/api/v1/watchlist/groups';

export const watchlistService = {
  getGroups: () => api.get(BASE).then((res) => res.data),

  createGroup: (name: string) =>
    api.post(BASE, { name }).then((res) => res.data),

  renameGroup: (groupId: number, name: string) =>
    api.put(`${BASE}/${groupId}`, { name }).then((res) => res.data),

  deleteGroup: (groupId: number) =>
    api.delete(`${BASE}/${groupId}`).then((res) => res.data),

  addStock: (groupId: number, stockCode: string, stockName: string, addPrice?: number) =>
    api.post(`${BASE}/${groupId}/stocks`, {
      stock_code: stockCode,
      stock_name: stockName,
      add_price: addPrice,
    }).then((res) => res.data),

  removeStock: (groupId: number, stockCode: string) =>
    api.delete(`${BASE}/${groupId}/stocks/${stockCode}`).then((res) => res.data),

  /** 按自选分组批量同步日K + 30m 行情（异步后台任务）。
   *  端点毫秒级返回任务 id；进度在「数据同步页」查看。 */
  syncByGroups: (groupIds: number[]) =>
    api.post('/api/v1/watchlist/sync', { group_ids: groupIds }).then((res) => res.data),
};

export const stockQuoteService = {
  getQuotesBatch: (codes: string[]) =>
    api.post('/api/v1/stocks/quotes/batch', { codes }).then((res) => res.data),
};
