import React, { useEffect, useState } from 'react';
import { Table, Spin } from 'antd';
import { useNavigate } from 'react-router-dom';
import { industryService } from '../../services/industryService';

interface IndustryComparisonProps {
  industryCode: string;
}

const IndustryComparison: React.FC<IndustryComparisonProps> = ({ industryCode }) => {
  const navigate = useNavigate();
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!industryCode) return;
    setLoading(true);
    industryService
      .getIndustryStocks(industryCode, { page_size: 20 })
      .then((res) => setData(res.data?.items || []))
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [industryCode]);

  const columns = [
    {
      title: '股票',
      dataIndex: 'name',
      render: (name: string, r: any) => (
        <a onClick={() => navigate(`/market/stock/${r.code}`)}>{name} ({r.code})</a>
      ),
    },
    {
      title: '涨跌幅',
      dataIndex: 'change_pct',
      render: (v: number) => {
        if (v === null || v === undefined) return '--';
        return <span style={{ color: v >= 0 ? '#f5222d' : '#52c41a' }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</span>;
      },
    },
    { title: 'PE', dataIndex: 'pe_ttm', render: (v: number) => v?.toFixed(2) ?? '--' },
    { title: 'PB', dataIndex: 'pb', render: (v: number) => v?.toFixed(2) ?? '--' },
  ];

  return (
    <Spin spinning={loading}>
      <Table columns={columns} dataSource={data} rowKey="code" size="small" pagination={false} />
    </Spin>
  );
};

export default IndustryComparison;
