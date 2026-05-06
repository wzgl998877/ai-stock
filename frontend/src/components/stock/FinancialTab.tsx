import React from 'react';
import { Descriptions, Empty } from 'antd';

interface FinancialTabProps {
  financial: {
    revenue?: number;
    revenue_growth_pct?: number;
    net_profit?: number;
    profit_growth_pct?: number;
    pe_ttm?: number;
    pb?: number;
  } | null;
}

const FinancialTab: React.FC<FinancialTabProps> = ({ financial }) => {
  if (!financial) return <Empty description="暂无财务数据" />;

  const formatAmount = (v: number | undefined) => {
    if (v === undefined || v === null) return '--';
    if (v >= 100000000) return (v / 100000000).toFixed(2) + ' 亿';
    if (v >= 10000) return (v / 10000).toFixed(2) + ' 万';
    return v.toFixed(2);
  };

  const growthStyle = (v: number | undefined) => {
    if (v === undefined || v === null) return {};
    return { color: v >= 0 ? '#f5222d' : '#52c41a' };
  };

  return (
    <Descriptions bordered size="small" column={2}>
      <Descriptions.Item label="PE（市盈率TTM）">
        {financial.pe_ttm?.toFixed(2) ?? '--'}
      </Descriptions.Item>
      <Descriptions.Item label="PB（市净率）">
        {financial.pb?.toFixed(2) ?? '--'}
      </Descriptions.Item>
      <Descriptions.Item label="最近一年营收">
        {formatAmount(financial.revenue)}
      </Descriptions.Item>
      <Descriptions.Item label="营收同比增长">
        <span style={growthStyle(financial.revenue_growth_pct)}>
          {financial.revenue_growth_pct !== undefined
            ? `${financial.revenue_growth_pct > 0 ? '+' : ''}${financial.revenue_growth_pct.toFixed(2)}%`
            : '--'}
        </span>
      </Descriptions.Item>
      <Descriptions.Item label="最近一年净利润">
        {formatAmount(financial.net_profit)}
      </Descriptions.Item>
      <Descriptions.Item label="净利润同比增长">
        <span style={growthStyle(financial.profit_growth_pct)}>
          {financial.profit_growth_pct !== undefined
            ? `${financial.profit_growth_pct > 0 ? '+' : ''}${financial.profit_growth_pct.toFixed(2)}%`
            : '--'}
        </span>
      </Descriptions.Item>
    </Descriptions>
  );
};

export default FinancialTab;
