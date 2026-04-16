/** EventTypeSelector — 5种事件类型按钮组 */

import React from "react";
import { Radio } from "antd";
import { EVENT_TYPES } from "../../domain/constants";
import type { EventType } from "../../domain/types";

interface Props {
  value: EventType;
  onChange: (value: EventType) => void;
  disabled?: boolean;
}

const EventTypeSelector: React.FC<Props> = ({ value, onChange, disabled }) => {
  return (
    <Radio.Group
      value={value}
      onChange={(e) => onChange(e.target.value)}
      optionType="button"
      buttonStyle="solid"
      disabled={disabled}
      style={{ marginBottom: 16, gap: 6 }}
    >
      {EVENT_TYPES.map((t) => (
        <Radio.Button key={t.value} value={t.value}>
          {t.label}
        </Radio.Button>
      ))}
    </Radio.Group>
  );
};

export default EventTypeSelector;
