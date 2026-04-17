/** IndustryTag — 行业标签展示 + 增删交互 */

import React from "react";
import { Tag } from "antd";

interface IndustryTagProps {
  industries: string[];
  editable?: boolean;
  onRemove?: (index: number) => void;
  chainLevels?: Map<string, number>; // 行业名 → 产业链层级（仅产业链分析）
}

const IndustryTag: React.FC<IndustryTagProps> = ({
  industries,
  editable = false,
  onRemove,
  chainLevels,
}) => {
  // 如果有产业链层级信息，按层级分组显示
  if (chainLevels && chainLevels.size > 0) {
    const groups = new Map<number, string[]>();
    industries.forEach((ind) => {
      const level = chainLevels.get(ind) ?? 0;
      if (!groups.has(level)) groups.set(level, []);
      groups.get(level)!.push(ind);
    });

    const sortedLevels = Array.from(groups.keys()).sort((a, b) => a - b);

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {sortedLevels.map((level) => (
          <div key={level} style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
            {level > 0 && (
              <span style={{ fontSize: 11, color: "#64748d", marginRight: 4 }}>
                第{level}层:
              </span>
            )}
            {groups.get(level)!.map((ind, idx) => (
              <Tag
                key={`${level}-${idx}`}
                closable={editable}
                onClose={() => {
                  const globalIdx = industries.indexOf(ind);
                  onRemove?.(globalIdx);
                }}
                style={{
                  margin: 0,
                  borderRadius: 4,
                  border: "1px solid #d6d9fc",
                  background: "rgba(83,58,253,0.05)",
                  color: "#533afd",
                  fontSize: 12,
                }}
              >
                {ind}
              </Tag>
            ))}
          </div>
        ))}
      </div>
    );
  }

  // 普通模式：平铺展示
  return (
    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
      {industries.map((ind, idx) => (
        <Tag
          key={idx}
          closable={editable}
          onClose={() => onRemove?.(idx)}
          style={{
            margin: 0,
            borderRadius: 4,
            border: "1px solid #d6d9fc",
            background: "rgba(83,58,253,0.05)",
            color: "#533afd",
            fontSize: 12,
          }}
        >
          {ind}
        </Tag>
      ))}
    </div>
  );
};

export default IndustryTag;
