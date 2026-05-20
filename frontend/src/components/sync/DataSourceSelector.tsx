import React, { useCallback } from "react";
import { Select, Button, DatePicker, Input, Space, Typography, Form } from "antd";
import { SyncOutlined } from "@ant-design/icons";

const { Text } = Typography;

export interface SyncFormData {
  sourceType: string;
  dataType: string;
  symbol?: string;
  startDate?: string;
  endDate?: string;
}

interface DataSourceSelectorProps {
  onSync: (data: SyncFormData) => void;
  isSyncing: boolean;
  availableSources: string[];
}

const DATA_TYPES = [
  { value: "basic_info", label: "股票基础信息" },
  { value: "market_quote", label: "实时行情" },
  { value: "daily_quote", label: "历史K线" },
  { value: "financial", label: "财务数据" },
];

const SOURCE_LABELS: Record<string, string> = {
  tushare: "Tushare",
  akshare: "AKShare",
  baostock: "BaoStock",
  sina: "新浪财经",
};

const DataSourceSelector: React.FC<DataSourceSelectorProps> = ({
  onSync,
  isSyncing,
  availableSources,
}) => {
  const [form] = Form.useForm<SyncFormData>();
  const dataType = Form.useWatch("dataType", form);

  const handleSubmit = useCallback(() => {
    form.validateFields().then((values) => {
      onSync({
        sourceType: values.sourceType,
        dataType: values.dataType,
        symbol: values.symbol,
        startDate: values.startDate?.format("YYYY-MM-DD"),
        endDate: values.endDate?.format("YYYY-MM-DD"),
      });
    });
  }, [form, onSync]);

  const showDateRange = dataType === "daily_quote";

  return (
    <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
      <Form.Item
        name="sourceType"
        label="数据源"
        rules={[{ required: true, message: "请选择数据源" }]}
      >
        <Select
          style={{ width: 150 }}
          placeholder="选择数据源"
          options={availableSources.map((s) => ({
            value: s,
            label: SOURCE_LABELS[s] || s,
          }))}
          disabled={isSyncing}
        />
      </Form.Item>

      <Form.Item
        name="dataType"
        label="数据类型"
        rules={[{ required: true, message: "请选择数据类型" }]}
      >
        <Select
          style={{ width: 160 }}
          placeholder="选择数据类型"
          options={DATA_TYPES}
          disabled={isSyncing}
        />
      </Form.Item>

      <Form.Item name="symbol" label="股票代码">
        <Input
          style={{ width: 140 }}
          placeholder="留空=全市场"
          maxLength={10}
          disabled={isSyncing}
        />
      </Form.Item>

      {showDateRange && (
        <>
          <Form.Item name="startDate" label="起始日期">
            <DatePicker disabled={isSyncing} />
          </Form.Item>
          <Form.Item name="endDate" label="结束日期">
            <DatePicker disabled={isSyncing} />
          </Form.Item>
        </>
      )}

      <Form.Item>
        <Button
          type="primary"
          icon={<SyncOutlined spin={isSyncing} />}
          onClick={handleSubmit}
          loading={isSyncing}
        >
          {isSyncing ? "同步中..." : "同步"}
        </Button>
      </Form.Item>
    </Form>
  );
};

export default DataSourceSelector;
