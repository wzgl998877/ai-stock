/** 雷达配置弹窗 */

import React, { useEffect, useState } from "react";
import {
  Modal,
  Form,
  Checkbox,
  Radio,
  message,
} from "antd";
import { eventRadarService } from "../../services/eventRadarService";

const INDUSTRY_OPTIONS = [
  "电力设备", "石油石化", "有色金属", "基础化工", "钢铁",
  "煤炭", "食品饮料", "医药生物", "汽车", "房地产",
  "银行", "非银金融", "电子", "计算机", "通信",
  "传媒", "军工", "农林牧渔", "建筑装饰", "机械设备",
  "轻工制造", "商贸零售", "纺织服饰", "社会服务", "公用事业",
  "交通运输", "环保", "综合", "美容护理", "建筑材料", "家用电器",
];

const EVENT_TYPE_OPTIONS = [
  { label: "地缘政治", value: "geopolitical" },
  { label: "政策法规", value: "policy" },
  { label: "业绩财报", value: "earnings" },
  { label: "行业动态", value: "industry" },
  { label: "宏观经济", value: "macro" },
];

interface RadarConfigModalProps {
  visible: boolean;
  onClose: () => void;
}

const RadarConfigModal: React.FC<RadarConfigModalProps> = ({ visible, onClose }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (visible) {
      eventRadarService.getConfig().then((config) => {
        form.setFieldsValue({
          focused_industries: config.focused_industries || [],
          event_types: config.event_types || EVENT_TYPE_OPTIONS.map((o) => o.value),
          alert_sensitivity: config.alert_sensitivity || "medium",
        });
      });
    }
  }, [visible, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      await eventRadarService.updateConfig(values);
      message.success("配置已保存");
      onClose();
    } catch {
      // validation error
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="雷达配置"
      open={visible}
      onCancel={onClose}
      onOk={handleSave}
      confirmLoading={loading}
      okText="保存"
      cancelText="取消"
      width={560}
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item name="focused_industries" label="关注行业">
          <Checkbox.Group options={INDUSTRY_OPTIONS} />
        </Form.Item>

        <Form.Item name="event_types" label="事件类型">
          <Checkbox.Group options={EVENT_TYPE_OPTIONS} />
        </Form.Item>

        <Form.Item name="alert_sensitivity" label="预警灵敏度">
          <Radio.Group>
            <Radio value="high">高（更多预警）</Radio>
            <Radio value="medium">中</Radio>
            <Radio value="low">低（仅紧急）</Radio>
          </Radio.Group>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default RadarConfigModal;
