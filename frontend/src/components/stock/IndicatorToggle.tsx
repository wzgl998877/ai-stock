import React from 'react';
import { Switch, Space } from 'antd';

interface IndicatorToggleProps {
  showMACD: boolean;
  showKDJ: boolean;
  onToggleMACD: () => void;
  onToggleKDJ: () => void;
}

const IndicatorToggle: React.FC<IndicatorToggleProps> = ({
  showMACD, showKDJ, onToggleMACD, onToggleKDJ,
}) => (
  <Space size="middle">
    <span style={{ fontSize: 12, color: '#666' }}>
      MACD <Switch size="small" checked={showMACD} onChange={onToggleMACD} />
    </span>
    <span style={{ fontSize: 12, color: '#666' }}>
      KDJ <Switch size="small" checked={showKDJ} onChange={onToggleKDJ} />
    </span>
  </Space>
);

export default IndicatorToggle;
