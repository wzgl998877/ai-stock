import React, { useEffect, useCallback, useState } from "react";
import {
  Card,
  Form,
  Input,
  Switch,
  Button,
  Space,
  Typography,
  message,
  Descriptions,
  Divider,
  Popconfirm,
} from "antd";
import { SaveOutlined, DeleteOutlined, LoadingOutlined } from "@ant-design/icons";
import {
  datasourceService,
  type DataSourceConfig,
  type SaveDataSourceRequest,
} from "../../services/datasourceService";

const { Title, Text } = Typography;

interface DataSourceConfigFormProps {
  config: DataSourceConfig;
  onSave: (data: SaveDataSourceRequest) => void;
  onDelete: (sourceType: string) => void;
  saving: boolean;
}

const SOURCE_DESCRIPTIONS: Record<string, { label: string; desc: string; needKey: boolean }> = {
  tushare: {
    label: "Tushare",
    desc: "国内权威金融数据平台，覆盖A股/港股/美股，数据质量高。需要注册获取 Token。",
    needKey: true,
  },
  akshare: {
    label: "AKShare",
    desc: "开源免费数据源，覆盖A股全市场行情，无需 API Key。",
    needKey: false,
  },
  baostock: {
    label: "BaoStock",
    desc: "证券宝，提供免费历史K线和财务数据，需注册账号。",
    needKey: false,
  },
};

const DataSourceConfigCard: React.FC<DataSourceConfigFormProps> = ({
  config,
  onSave,
  onDelete,
  saving,
}) => {
  const [form] = Form.useForm<SaveDataSourceRequest>();
  const info = SOURCE_DESCRIPTIONS[config.source_type];

  useEffect(() => {
    form.setFieldsValue({
      is_enabled: config.is_enabled,
      api_key: undefined, // Don't pre-fill encrypted key
    });
  }, [config, form]);

  const handleSave = () => {
    form.validateFields().then((values) => {
      onSave({
        source_type: config.source_type,
        is_enabled: values.is_enabled,
        ...(values.api_key ? { api_key: values.api_key } : {}),
      });
    });
  };

  return (
    <Card size="small" style={{ marginBottom: 16 }}>
      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        <div>
          <Title level={5}>{info.label}</Title>
          <Text type="secondary">{info.desc}</Text>
        </div>

        <Descriptions size="small" column={2}>
          <Descriptions.Item label="优先级">{config.priority}</Descriptions.Item>
          <Descriptions.Item label="已配置">
            {config.has_configured ? (
              <Text type="success">是 {config.api_key_masked && `(${config.api_key_masked})`}</Text>
            ) : (
              <Text type="danger">否</Text>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="启用状态">
            <Switch checked={config.is_enabled} disabled />
          </Descriptions.Item>
        </Descriptions>

        <Divider style={{ margin: "8px 0" }} />

        <Form form={form} layout="inline">
          {info.needKey && (
            <Form.Item
              name="api_key"
              label="API Key"
              rules={
                config.has_configured
                  ? []
                  : [{ required: true, message: "请输入 API Key" }]
              }
            >
              <Input.Password
                placeholder={config.has_configured ? "留空则不修改" : "请输入 Tushare Token"}
                style={{ width: 300 }}
              />
            </Form.Item>
          )}

          <Form.Item name="is_enabled" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                icon={saving ? <LoadingOutlined /> : <SaveOutlined />}
                onClick={handleSave}
                loading={saving}
              >
                保存
              </Button>
              {config.has_configured && (
                <Popconfirm
                  title="确认删除"
                  description="确定要删除此数据源配置吗？"
                  onConfirm={() => onDelete(config.source_type)}
                >
                  <Button danger icon={<DeleteOutlined />}>
                    删除
                  </Button>
                </Popconfirm>
              )}
            </Space>
          </Form.Item>
        </Form>
      </Space>
    </Card>
  );
};

const DataSourceConfigPage: React.FC = () => {
  const [configs, setConfigs] = useState<DataSourceConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingType, setSavingType] = useState<string | null>(null);

  const loadConfigs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await datasourceService.listDatasources();
      setConfigs(data);
    } catch (err) {
      message.error("加载数据源配置失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  const handleSave = async (data: SaveDataSourceRequest) => {
    setSavingType(data.source_type);
    try {
      await datasourceService.saveDatasource(data);
      message.success("配置保存成功");
      loadConfigs();
    } catch (err: any) {
      message.error(err.message || "保存失败");
    } finally {
      setSavingType(null);
    }
  };

  const handleDelete = async (sourceType: string) => {
    try {
      await datasourceService.deleteDatasource(sourceType);
      message.success("配置已删除");
      loadConfigs();
    } catch {
      message.error("删除失败");
    }
  };

  if (loading) {
    return <div style={{ padding: 24 }}>加载中...</div>;
  }

  return (
    <div style={{ padding: 24, maxWidth: 800 }}>
      <Title level={4}>数据源配置</Title>
      <Text type="secondary" style={{ display: "block", marginBottom: 24 }}>
        配置各数据源的 API 凭证，用于股票数据的同步。
      </Text>

      {configs.map((cfg) => (
        <DataSourceConfigCard
          key={cfg.source_type}
          config={cfg}
          onSave={handleSave}
          onDelete={handleDelete}
          saving={savingType === cfg.source_type}
        />
      ))}
    </div>
  );
};

export default DataSourceConfigPage;
