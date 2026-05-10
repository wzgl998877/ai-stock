/** EventTypeSelector — 彩色事件类型标签（输入框下方） */

import React from "react";
import { EVENT_TYPES } from "../../domain/constants";
import type { EventType } from "../../domain/types";

/** 每个事件类型独立配色 */
const TAG_COLORS: Record<string, { bg: string; bgHover: string; bgActive: string; text: string; textActive: string }> = {
  geopolitical: { bg: "rgba(37,99,235,0.08)", bgHover: "rgba(37,99,235,0.16)", bgActive: "#2563eb", text: "#2563eb", textActive: "#ffffff" },
  policy:       { bg: "rgba(234,88,12,0.08)",  bgHover: "rgba(234,88,12,0.16)",  bgActive: "#ea580c", text: "#ea580c", textActive: "#ffffff" },
  earnings:     { bg: "rgba(22,163,74,0.08)",   bgHover: "rgba(22,163,74,0.16)",   bgActive: "#16a34a", text: "#16a34a", textActive: "#ffffff" },
  supply_chain: { bg: "rgba(124,58,237,0.08)", bgHover: "rgba(124,58,237,0.16)", bgActive: "#7c3aed", text: "#7c3aed", textActive: "#ffffff" },
};

interface Props {
  value: EventType | null;
  onChange: (value: EventType | null) => void;
  disabled?: boolean;
}

const EventTypeSelector: React.FC<Props> = ({ value, onChange, disabled }) => {
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        gap: 10,
        marginTop: 16,
        opacity: disabled ? 0.5 : 1,
        pointerEvents: disabled ? "none" : "auto",
      }}
    >
      {EVENT_TYPES.map((t) => {
        const isSelected = t.value === value;
        const colors = TAG_COLORS[t.value];
        return (
          <span
            key={t.value}
            onClick={() => onChange(isSelected ? null : t.value)}
            style={{
              padding: "6px 16px",
              fontSize: 14,
              borderRadius: 20,
              border: "none",
              background: isSelected ? colors.bgActive : colors.bg,
              color: isSelected ? colors.textActive : colors.text,
              cursor: "pointer",
              transition: "all 0.2s",
              userSelect: "none",
              fontFeatureSettings: "'ss01' on",
              fontWeight: isSelected ? 500 : 400,
            }}
            onMouseEnter={(e) => {
              if (!isSelected) {
                (e.currentTarget as HTMLElement).style.background = colors.bgHover;
              }
            }}
            onMouseLeave={(e) => {
              if (!isSelected) {
                (e.currentTarget as HTMLElement).style.background = colors.bg;
              }
            }}
          >
            {t.label}
          </span>
        );
      })}
    </div>
  );
};

export default EventTypeSelector;
