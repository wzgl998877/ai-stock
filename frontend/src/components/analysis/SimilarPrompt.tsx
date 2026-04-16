/** SimilarPrompt — 相似问题提示卡（非阻断式） */

import React, { useState, useEffect, useRef } from "react";
import { Typography, Space } from "antd";
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
    <div
      style={{
        marginTop: 10,
        padding: "10px 14px",
        background: "#f0fdf4",
        borderRadius: 10,
        border: "1px solid #dcfce7",
      }}
    >
      <Space>
        <HistoryOutlined style={{ color: "#07C160" }} />
        <Text type="secondary" style={{ fontSize: 13 }}>
          你之前分析过类似问题 →{" "}
          <Link strong style={{ color: "#07C160" }}>
            {similar.title}
          </Link>
          ，要对比吗？
        </Text>
      </Space>
    </div>
  );
};

export default SimilarPrompt;
