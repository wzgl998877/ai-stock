import React from 'react';
import { Switch, Space } from 'antd';

interface IndicatorToggleProps {
  showMACD: boolean;
  showKDJ: boolean;
  showChanlun?: boolean;
  onToggleMACD: () => void;
  onToggleKDJ: () => void;
  onToggleChanlun?: () => void;
}

const IndicatorToggle: React.FC<IndicatorToggleProps> = ({
  showMACD, showKDJ, showChanlun, onToggleMACD, onToggleKDJ, onToggleChanlun,
}) => (
  <Space size="middle">
    <span style={{ fontSize: 13, color: '#666' }}>
      MACD <Switch size="small" checked={showMACD} onChange={onToggleMACD} />
    </span>
    <span style={{ fontSize: 13, color: '#666' }}>
      KDJ <Switch size="small" checked={showKDJ} onChange={onToggleKDJ} />
    </span>
    {onToggleChanlun && showChanlun !== undefined && (
      <span style={{ fontSize: 13, color: '#666' }} title="缠论买卖点标注（规则参考信号，不构成投资建议）">
        缠论 <Switch size="small" checked={showChanlun} onChange={onToggleChanlun} />
      </span>
    )}
  </Space>
);

export default IndicatorToggle;
