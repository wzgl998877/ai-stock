import api from './api';

const BASE = '/api/v1/watchlist/groups';

export const watchlistService = {
  getGroups: () => api.get(BASE),

  createGroup: (name: string) =>
    api.post(BASE, { name }),

  renameGroup: (groupId: number, name: string) =>
    api.put(`${BASE}/${groupId}`, { name }),

  deleteGroup: (groupId: number) =>
    api.delete(`${BASE}/${groupId}`),

  addStock: (groupId: number, stockCode: string, stockName: string) =>
    api.post(`${BASE}/${groupId}/stocks`, {
      stock_code: stockCode,
      stock_name: stockName,
    }),

  removeStock: (groupId: number, stockCode: string) =>
    api.delete(`${BASE}/${groupId}/stocks/${stockCode}`),
};
