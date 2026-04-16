/** SimilarPrompt — 相似问题提示卡（非阻断式） */

import React, { useState, useEffect, useRef } from "react";
import { Card, Typography, Space } from "antd";
import { HistoryOutlined } from "@ant-design/icons";
import { checkSimilarity } from "../../services/analysisService";
import { SIMILARITY_DEBOUNCE_MS } from "../../domain/constants";

const { Text, Link } = Typography;

interface Props {
  question: string;
}

interface SimilarItem {
  id: string;
  title: string;
  similarity: number;
}

const SimilarPrompt: React.FC<Props> = ({ question }) => {
  const [similar, setSimilar] = useState<SimilarItem | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!question || question.trim().length < 5) {
      setSimilar(null);
      return;
    }

    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(async () => {
      try {
        const res = await checkSimilarity(question, 1);
        if (res.similar_articles.length > 0) {
          setSimilar(res.similar_articles[0] as unknown as SimilarItem);
        } else {
          setSimilar(null);
        }
      } catch {
        setSimilar(null);
      }
    }, SIMILARITY_DEBOUNCE_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [question]);

  if (!similar) return null;

  return (
    <Card
      size="small"
      style={{ marginTop: 8 }}
      styles={{ body: { padding: "8px 12px" } }}
    >
      <Space>
        <HistoryOutlined style={{ color: "#faad14" }} />
        <Text type="secondary">
          你之前分析过类似问题 → <Link strong>{similar.title}</Link>，要对比吗？
        </Text>
      </Space>
    </Card>
  );
};

export default SimilarPrompt;
