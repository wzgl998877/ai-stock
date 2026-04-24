import api from "./api";

export interface DataSourceConfig {
  source_type: string;
  api_key_masked: string | null;
  is_enabled: boolean;
  priority: number;
  has_configured: boolean;
}

export interface SaveDataSourceRequest {
  source_type: string;
  api_key?: string;
  is_enabled: boolean;
  priority?: number;
}

export const datasourceService = {
  async listDatasources(): Promise<DataSourceConfig[]> {
    const res = await api.get("/api/v1/datasources");
    return res.data.data;
  },

  async saveDatasource(config: SaveDataSourceRequest): Promise<DataSourceConfig> {
    const res = await api.post("/api/v1/datasources", config);
    return res.data.data;
  },

  async deleteDatasource(sourceType: string): Promise<void> {
    await api.delete(`/api/v1/datasources/${sourceType}`);
  },
};
