import React from 'react';
import { List, Empty, Typography } from 'antd';

interface RelatedArticle {
  article_id: string;
  title: string;
  summary: string;
  saved_at: string;
}

interface RelatedAnalysisTabProps {
  articles: RelatedArticle[];
  onClick: (articleId: string) => void;
}

const RelatedAnalysisTab: React.FC<RelatedAnalysisTabProps> = ({ articles, onClick }) => {
  if (!articles || articles.length === 0) {
    return <Empty description="暂无相关分析" />;
  }

  return (
    <List
      dataSource={articles}
      renderItem={(item) => (
        <List.Item
          style={{ cursor: 'pointer', padding: '8px 12px' }}
          onClick={() => onClick(item.article_id)}
        >
          <List.Item.Meta
            title={
              <Typography.Text style={{ color: '#533afd' }}>
                {item.title}
              </Typography.Text>
            }
            description={
              <div>
                <div style={{ color: '#666', fontSize: 14 }}>
                  {item.summary?.length > 80 ? item.summary.slice(0, 80) + '...' : item.summary}
                </div>
                <div style={{ color: '#999', fontSize: 12, marginTop: 4 }}>
                  {item.saved_at?.slice(0, 10)}
                </div>
              </div>
            }
          />
        </List.Item>
      )}
    />
  );
};

export default RelatedAnalysisTab;
