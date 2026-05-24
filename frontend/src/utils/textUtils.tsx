import React from "react";

/**
 * 将文本中的关键数字高亮渲染为 React 节点
 * 识别模式：百分比(含正负)、价格(带小数点)
 */
const NUMBER_PATTERN = /([-+]?\s?\d+\.?\d*\s?%|¥?\s?\d+\.\d{2}(?=[^\d]|$))/g;

/** 首句提取：以中文句号、英文句号、问号、感叹号分割，取第一句 */
export function extractFirstSentence(text: string): string {
  if (!text) return "";
  const match = text.match(/^[^。？！.!?\n]+[。？！.!?]?/);
  return match ? match[0].trim() : text;
}

/** 首句之外的剩余内容 */
export function extractRemainingText(text: string): string {
  if (!text) return "";
  const first = extractFirstSentence(text);
  if (!first || first.length >= text.length) return "";
  return text.slice(first.length).trim();
}

/**
 * 百分比值归一化：0-1 → 0-100；已经是 0-100 的不转换。
 * 后端 AI 模型输出 0-100，但部分历史数据可能为 0-1，需自适应。
 */
export function toPercent(val: number): number {
  return val > 1 ? val : val * 100;
}

/** 高亮数字：返回 React 节点数组 */
export function highlightNumbers(text: string): React.ReactNode {
  if (!text) return text;

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;

  // 重置正则的 lastIndex
  const regex = new RegExp(NUMBER_PATTERN.source, "g");
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push(
      <strong
        key={`hl-${key++}`}
        style={{
          color: "#533afd",
          fontWeight: 600,
          fontFeatureSettings: "'tnum' on",
        }}
      >
        {match[0]}
      </strong>
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 1 ? parts : text;
}
