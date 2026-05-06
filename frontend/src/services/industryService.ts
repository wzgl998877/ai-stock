import api from './api';

const BASE = '/api/v1/industries';

export const industryService = {
  getIndustries: () => api.get(BASE),

  getIndustryStocks: (industryCode: string, params?: {
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    page?: number;
    page_size?: number;
  }) => api.get(`${BASE}/${industryCode}/stocks`, { params }),
};
