import React from 'react';
import { Radio } from 'antd';
import type { KlinePeriod } from '../../store/stockDetailStore';

interface PeriodSelectorProps {
  activePeriod: KlinePeriod;
  onChange: (period: KlinePeriod) => void;
}

const PeriodSelector: React.FC<PeriodSelectorProps> = ({ activePeriod, onChange }) => (
  <Radio.Group
    value={activePeriod}
    onChange={(e) => onChange(e.target.value)}
    size="small"
    buttonStyle="solid"
  >
    <Radio.Button value="minute">分时</Radio.Button>
    <Radio.Button value="daily">日K</Radio.Button>
    <Radio.Button value="weekly">周K</Radio.Button>
    <Radio.Button value="monthly">月K</Radio.Button>
  </Radio.Group>
);

export default PeriodSelector;
